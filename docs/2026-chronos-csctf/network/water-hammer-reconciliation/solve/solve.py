#!/usr/bin/env python3
"""water-hammer-reconciliation: rebuild the confirmed Modbus/TCP control history and its report hash.

Usage: python3 -I solve.py ../files            (pure Python, no tshark needed)
Implements the rules of station-profile.txt: reassembled TCP streams, strict ADU grammar,
FC16 -> unique echo -> immediately-next FC3 readback with a unique matched response.
"""
import base64, hashlib, struct, sys
from pathlib import Path

d = Path(sys.argv[1])
UNIT, SRV = 17, 502


# ---- pcapng + Ethernet/IPv4/TCP -> per-direction reassembled byte streams with frame ordinals
def frames(path):
    buf, o = path.read_bytes(), 0
    while o < len(buf):
        bt, bl = struct.unpack("<II", buf[o:o + 8])
        if bt == 6:                                                  # enhanced packet block
            cl = struct.unpack("<I", buf[o + 20:o + 24])[0]
            yield buf[o + 28:o + 28 + cl]
        o += bl


streams = {}                                                         # (sport, dport) -> {isn, bytes: {off: (byte, frame)}}
for n, f in enumerate(frames(d / "reserve-header.pcapng"), 1):
    if f[12:14] != b"\x08\x00" or f[23] != 6:
        continue
    ihl = (f[14] & 15) * 4
    ip = f[14:14 + struct.unpack(">H", f[16:18])[0]]
    t = ip[ihl:]
    sp, dp, seq = struct.unpack(">HHI", t[:8])
    s = streams.setdefault((sp, dp), {"isn": None, "pay": []})
    if t[13] & 2:
        s["isn"] = seq
    pay = t[(t[12] >> 4) * 4:]
    if pay:
        s["pay"].append((seq, n, pay))


def adus(stream):
    place = {}
    for seq, n, pay in stream["pay"]:
        for i, b in enumerate(pay):
            place.setdefault((seq + i - stream["isn"] - 1) & 0xFFFFFFFF, (b, n))   # first frame wins (retransmissions)
    data = bytes(place[i][0] for i in range(len(place)))
    frm = [place[i][1] for i in range(len(place))]
    out, o = [], 0
    while o + 6 <= len(data):
        tid, pid, ln = struct.unpack(">HHH", data[o:o + 6])
        end = o + 6 + ln
        if pid != 0 or ln < 2 or end > len(data):                    # malformed / truncated: not an event
            o = end if end <= len(data) else len(data)
            continue
        out.append({"tid": tid, "len": ln, "unit": data[o + 6], "pdu": data[o + 7:end], "frame": frm[end - 1]})
        o = end
    return out


cli = next(v for k, v in streams.items() if k[1] == SRV)
srv = next(v for k, v in streams.items() if k[0] == SRV)
C, S = adus(cli), adus(srv)
print(f"{len(C)} client ADUs, {len(S)} server ADUs", file=sys.stderr)

# ---- confirmed snapshots
snaps = []
for ci, req in enumerate(C):
    p = req["pdu"]
    if req["unit"] != UNIT or not p or p[0] != 0x10 or len(p) < 6:
        continue
    A, N = struct.unpack(">HH", p[1:5])
    if not (1 <= N <= 4 and 0x1000 <= A and A + N - 1 <= 0x1003 and req["len"] == 7 + 2 * N
            and p[5] == 2 * N and len(p) == 6 + 2 * N):
        continue
    # unique pending response with the same tid
    cand = [r for r in S if r["tid"] == req["tid"] and r["frame"] > req["frame"]]
    if len(cand) != 1:
        continue
    resp = cand[0]
    if not (resp["unit"] == UNIT and resp["len"] == 6 and resp["pdu"] == p[:5]):
        continue
    # immediately next client ADU after the positive response
    nxt = next((c for c in C if c["frame"] > resp["frame"]), None)
    if not (nxt and nxt["unit"] == UNIT and nxt["len"] == 6 and nxt["pdu"] == bytes.fromhex("0310000004")):
        continue
    rb = [r for r in S if r["tid"] == nxt["tid"] and r["frame"] > nxt["frame"]]
    if len(rb) != 1:
        continue
    r3 = rb[0]
    if not (r3["unit"] == UNIT and r3["len"] == 11 and r3["pdu"][:2] == b"\x03\x08" and len(r3["pdu"]) == 10):
        continue
    regs = struct.unpack(">4H", r3["pdu"][2:])
    snaps.append((resp["frame"], resp["tid"], regs))
snaps.sort()
assert len(snaps) == 64, len(snaps)
print(f"{len(snaps)} confirmed snapshots", file=sys.stderr)

# ---- safety screen (integer arithmetic only)
P0, G0, A0, R0 = 80, 500, 0, 60000
T_US = 2 * 20000 * 1000000 // 1065000
V = lambda p, g: (p * g // 1000) * 1000000 // 70686
prevV, mask, lines = V(P0, G0), 0, []
for i, (_, tid, (p, g, a, r)) in enumerate(snaps):
    v = V(p, g)
    q = 998 * 1065 * abs(v - prevV)
    if a == 1 and r < T_US and q > 9000 * 100000:
        mask |= 1 << (63 - i)
    lines.append(f"i={i};tid={tid:04X};p={p};g={g};a={a};r={r}")
    prevV = v

R = "\n".join(["water-hammer-reconciliation-v2", f"initial;p={P0};g={G0};a={A0};r={R0}", "n=64"] + lines
               + [f"unsafe-mask={mask:016X}"])
digest = hashlib.sha256(R.encode()).digest()
print("T_US =", T_US, "mask =", f"{mask:016X}", file=sys.stderr)
print("CSCTF{" + base64.b32encode(digest[:24]).decode().rstrip("=") + "}")
