#!/usr/bin/env python3
"""
CSCTF 2026 - Interlock Witness (forensics/medium)
Reconstruct accepted Modbus/TCP writes that breach the offline
response-cell interlock policy and derive the incident witness.

Policy (interlock-policy.md + register-map.md + witness-format.md):
  - One client -> controller flow on TCP/502, MBAP proto 0, unit 1,
    one request/response completed before the next request.
  - FC03 observation accepted only if the immediately preceding FC03
    request matches (reversed flow) TID / proto / unit / function and
    byte_count == 2 * quantity. It updates every mapped word it covers.
  - FC16 write accepted only if its reversed-flow normal response
    matches TID / proto / unit / function and echoes start + quantity.
    Exception responses never change state.
  - Accepted FC16 updates apply AFTER their normal response.
  - Target: FC16 quantity 1 at PDU 0x0013 (trip_limit) or 0x0014
    (restore_delay). The 8 other accepted FC16 are ineligible.
  - Target is unsafe iff, immediately before its normal response,
    not (permit==1 and isolation==1 and protection==1), with
    permit=0x000A, isolation=0x000B, protection=0x000C (zero-based PDU;
    40011/40012/40013 are operator labels only).
  - T = concat over unsafe targets in normal-response order of
    request PDU || normal-response PDU (no MBAP).
  - W = SHA-256(P || T), P = b"INTERLOCK-WITNESS/1\\x00" (20 bytes).
  - Flag = CSCTF{<lowercase hex W>}

Pure Python (stdlib only): minimal pcapng/pcap + Ethernet/IPv4/TCP
parser, Modbus/TCP ADU framing by MBAP length.

Usage:
    python3 solve.py [interlock.pcapng | interlock-witness.zip]

Verification vector (witness-format.md, unrelated to the capture):
    req 100013000102002a + resp 1000130001
    -> b6e58fa962e382b112eb596e416d5680495fc4bd02141f2389797f194df34786
"""

import hashlib
import os
import struct
import sys
import zipfile

P = b"INTERLOCK-WITNESS/1\x00"
MAPPED = (0x000A, 0x000B, 0x000C, 0x0013, 0x0014)
PERMIT, ISOLATION, PROTECTION = 0x000A, 0x000B, 0x000C
TARGET_ADDRS = (0x0013, 0x0014)


# ---------------------------------------------------------------- pcap I/O

def iter_pcapng_packets(data):
    """Yield raw link-layer packets from a pcapng byte string."""
    if len(data) < 28 or data[:4] != b"\x0a\x0d\x0d\x0a":
        raise ValueError("not a pcapng file")
    # Section Header Block: byte-order magic at offset 8.
    bom = data[8:12]
    if bom == b"\x4d\x3c\x2b\x1a":
        e = "<"
    elif bom == b"\x1a\x2b\x3c\x4d":
        e = ">"
    else:
        raise ValueError("bad pcapng byte-order magic")
    off = 0
    while off + 12 <= len(data):
        btype, blen = struct.unpack_from(e + "II", data, off)
        if blen < 12 or off + blen > len(data):
            break
        body = data[off + 8:off + blen - 4]
        if btype == 0x00000006 and len(body) >= 20:  # Enhanced Packet Block
            caplen = struct.unpack_from(e + "I", body, 12)[0]
            yield body[20:20 + caplen]
        elif btype == 0x00000003 and len(body) >= 4:  # Simple Packet Block
            caplen = struct.unpack_from(e + "I", body, 0)[0]
            yield body[4:4 + caplen]
        # Re-read endianness if a new section starts (single-section here).
        if btype == 0x0A0D0D0A and len(body) >= 4:
            e = "<" if body[:4] == b"\x4d\x3c\x2b\x1a" else ">"
        off += blen


def iter_pcap_packets(data):
    """Yield raw link-layer packets from a classic libpcap byte string."""
    if len(data) < 24:
        raise ValueError("not a pcap file")
    magic = data[:4]
    if magic == b"\xd4\xc3\xb2\xa1":
        e = "<"
    elif magic == b"\xa1\xb2\xc3\xd4":
        e = ">"
    elif magic == b"\x4d\x3c\xb2\xa1":
        e = "<"
    elif magic == b"\xa1\xb2\x3c\x4d":
        e = ">"
    else:
        raise ValueError("bad pcap magic")
    off = 24
    while off + 16 <= len(data):
        _, _, caplen, _ = struct.unpack_from(e + "IIII", data, off)
        off += 16
        yield data[off:off + caplen]
        off += caplen


def tcp_payloads(packets):
    """Yield (direction, payload) in capture order.

    direction is "C2S" (client -> :502) or "S2C" (controller -> client).
    Only the single maintenance flow is relevant; other traffic is skipped.
    """
    for pkt in packets:
        if len(pkt) < 14:
            continue
        off = 14
        ethertype = struct.unpack_from(">H", pkt, 12)[0]
        while ethertype in (0x8100, 0x88A8) and len(pkt) >= off + 4:
            ethertype = struct.unpack_from(">H", pkt, off + 2)[0]
            off += 4
        if ethertype != 0x0800 or len(pkt) < off + 20:
            continue
        ihl = (pkt[off] & 0x0F) * 4
        if pkt[off + 9] != 6:  # not TCP
            continue
        total = struct.unpack_from(">H", pkt, off + 2)[0]
        ip_end = off + total if total else len(pkt)
        tcp = off + ihl
        if len(pkt) < tcp + 20:
            continue
        sport, dport = struct.unpack_from(">HH", pkt, tcp)
        doff = ((pkt[tcp + 12] >> 4) & 0xF) * 4
        payload = pkt[tcp + doff:ip_end]
        if not payload:
            continue
        if dport == 502:
            yield "C2S", payload
        elif sport == 502:
            yield "S2C", payload


def modbus_adus(packets):
    """Frame Modbus/TCP ADUs per direction by MBAP length.

    Returns a list of events (order, direction, tid, proto, unit, pdu)
    in capture order. A per-direction buffer tolerates ADUs split or
    coalesced across TCP segments.
    """
    buffers = {"C2S": bytearray(), "S2C": bytearray()}
    events = []
    order = 0
    for direction, payload in tcp_payloads(packets):
        buf = buffers[direction]
        buf.extend(payload)
        while len(buf) >= 7:
            _, _, length = struct.unpack_from(">HHH", buf, 0)
            adu_len = 6 + length  # MBAP header (6) + length field content
            if length < 2 or adu_len > 260 + 7:
                raise ValueError(f"implausible MBAP length {length}")
            if len(buf) < adu_len:
                break
            tid, proto = struct.unpack_from(">HH", buf, 0)
            unit = buf[6]
            pdu = bytes(buf[7:adu_len])
            del buf[:adu_len]
            events.append((order, direction, tid, proto, unit, pdu))
            order += 1
    return events


# ---------------------------------------------------------------- policy

def reconstruct(events):
    """Apply the response-cell policy; return (unsafe, stats).

    unsafe entries: (tid, request_pdu, response_pdu, state_before)
    in normal-response order.
    """
    state = {addr: None for addr in MAPPED}
    requests = {}       # tid -> (proto, unit, pdu) for pending FC16
    last_request = None  # (tid, proto, unit, pdu) most recent C2S ADU
    unsafe = []
    stats = {"fc03_ok": 0, "fc03_rejected": 0,
             "fc16_ok": 0, "fc16_rejected": 0, "targets": 0}

    for _, direction, tid, proto, unit, pdu in events:
        if not pdu:
            continue
        fc = pdu[0]
        if direction == "C2S":
            last_request = (tid, proto, unit, pdu)
            if fc == 0x10 and len(pdu) >= 6:
                requests[tid] = (proto, unit, pdu)
            continue

        # --- S2C: FC03 observation -------------------------------------
        if fc == 0x03:
            req = last_request
            ok = (
                req is not None
                and req[0] == tid and req[1] == proto and req[2] == unit
                and proto == 0 and unit == 1
                and req[3][0] == 0x03 and len(req[3]) >= 5 and len(pdu) >= 2
            )
            if ok:
                start, qty = struct.unpack_from(">HH", req[3], 1)
                ok = pdu[1] == 2 * qty and len(pdu) == 2 + pdu[1]
            if not ok:
                stats["fc03_rejected"] += 1
                continue
            stats["fc03_ok"] += 1
            start, qty = struct.unpack_from(">HH", req[3], 1)
            for i in range(qty):
                addr = start + i
                if addr in state:
                    state[addr] = struct.unpack_from(">H", pdu, 2 + 2 * i)[0]
            continue

        # --- S2C: FC16 normal / exception response ----------------------
        if fc in (0x10, 0x90):
            req = requests.pop(tid, None)
            if fc == 0x90 or req is None:
                stats["fc16_rejected"] += 1
                continue  # exceptions never change state
            rproto, runit, rpdu = req
            ok = (
                rproto == proto and runit == unit
                and proto == 0 and unit == 1
                and len(pdu) == 5 and len(rpdu) >= 6
                and pdu[1:5] == rpdu[1:5]  # echoes start + quantity
            )
            if not ok:
                stats["fc16_rejected"] += 1
                continue
            stats["fc16_ok"] += 1
            start, qty = struct.unpack_from(">HH", rpdu, 1)
            byte_count = rpdu[5]
            values = [
                struct.unpack_from(">H", rpdu, 6 + 2 * i)[0]
                for i in range(qty)
                if 6 + 2 * i + 2 <= 6 + byte_count
            ]
            is_target = qty == 1 and start in TARGET_ADDRS
            if is_target:
                stats["targets"] += 1
                safe = (
                    state[PERMIT] == 1
                    and state[ISOLATION] == 1
                    and state[PROTECTION] == 1
                )
                if not safe:
                    unsafe.append((tid, rpdu, bytes(pdu), dict(state)))
            # Accepted FC16 updates apply after the normal response.
            for i, value in enumerate(values):
                if start + i in state:
                    state[start + i] = value
            continue
        # Other S2C functions play no role in the published policy.

    return unsafe, stats


# ---------------------------------------------------------------- main

def load_capture_bytes(argv):
    candidates = []
    if len(argv) > 1:
        candidates.append(argv[1])
    candidates += [
        "files/interlock.pcapng",
        "files/interlock-witness.zip",
        "../interlock-witness.zip",
        "docs/2026-chronos-csctf/forensics/interlock-witness.zip",
        "/tmp/opencode/interlock/interlock.pcapng",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            print(f"[*] Loading {path}")
            with open(path, "rb") as fh:
                blob = fh.read()
            if path.lower().endswith(".zip"):
                with zipfile.ZipFile(path) as zf:
                    return zf.read("interlock.pcapng")
            return blob
    print("[-] Provide interlock.pcapng or interlock-witness.zip")
    sys.exit(1)


def main():
    # Witness-format verification vector (format check only).
    vec_t = bytes.fromhex("100013000102002a" "1000130001")
    vec_w = hashlib.sha256(P + vec_t).hexdigest()
    assert vec_w == "b6e58fa962e382b112eb596e416d5680495fc4bd02141f2389797f194df34786", vec_w
    print(f"[*] Vector OK    : {vec_w}")

    blob = load_capture_bytes(sys.argv)
    if blob[:4] == b"\x0a\x0d\x0d\x0a":
        packets = iter_pcapng_packets(blob)
    else:
        packets = iter_pcap_packets(blob)
    events = modbus_adus(packets)
    print(f"[*] Modbus ADUs  : {len(events)}")

    unsafe, stats = reconstruct(events)
    print(f"[*] FC03 accepted: {stats['fc03_ok']} "
          f"(rejected {stats['fc03_rejected']})")
    print(f"[*] FC16 accepted: {stats['fc16_ok']} "
          f"(rejected {stats['fc16_rejected']}), targets {stats['targets']}")
    print(f"[*] Unsafe targets: {len(unsafe)} (normal-response order)")
    for tid, rpdu, spdu, before in unsafe:
        print(f"    TID {tid:3d} permit={before[PERMIT]} "
              f"isolation={before[ISOLATION]} protection={before[PROTECTION]} "
              f"req={rpdu.hex()} resp={spdu.hex()}")

    t = b"".join(rpdu + spdu for _, rpdu, spdu, _ in unsafe)
    w = hashlib.sha256(P + t).hexdigest()
    print(f"[*] T ({len(t)} bytes): {t.hex()}")
    print(f"\n[+] W            : {w}")
    print(f"[+] FLAG         : CSCTF{{{w}}}")


if __name__ == "__main__":
    main()
