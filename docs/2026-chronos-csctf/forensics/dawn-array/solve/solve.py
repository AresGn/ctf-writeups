#!/usr/bin/env python3
"""
CSCTF 2026 - Dawn Array (forensics/medium)
Rebuild a 4-member Linux md RAID-5 from 3 surviving members (read-only),
then apply gateway procedure DP-7 to find the controller-acknowledged
release witness.

Pipeline (every geometry value is derived from the member superblocks,
never assumed):
  1. Parse md v1 superblocks: RAID-5, 4 disks, layout 2 (left-symmetric),
     64-sector chunks, 2048-sector data offset, per-device roles; the
     missing role is recomputed parity (role 1 here).
  2. Delegate the byte shuffling to the provided tools/raid5_extract.py
     with the derived arguments; abort unless the result opens as ext4.
  3. Dump the evidence files read-only with debugfs (no mount, no root).
  4. Read dispatch.sqlite WITH its WAL applied (WAL-only rows count;
     33 of the 128 rows live only in the WAL here).
  5. Parse the RFC 5424 syslog (SD-ID rrca@32473) and reassemble the
     128 HTTP/1.1 connections from controller-access.pcapng in pure
     Python (one TCP connection per gateway_seq, POST then GET).
  6. Apply DP-7 Q1..Q5; qualifying cycles in ascending gateway_seq form
     the witness: "RRCA-DAWN-WITNESS-v1\\n" + lines
     cycle_id|request_id|prepare_revision|reservation_nonce|
     release_register|release_value
  7. Flag = CSCTF{dawn_<SHA-256 of the witness bytes>}.

Requires: debugfs (e2fsprogs, read-only dumps) + the ZIP contents.
Never mounts, never writes to the evidence, needs no root.

Usage:
    python3 solve.py [dawn-array.zip | extracted-dir]
"""

import hashlib
import json
import os
import re
import sqlite3
import struct
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter

MD_MAGIC = 0xA92B4EFC
MD_LAYOUTS = {0: "left-asymmetric", 1: "right-asymmetric",
              2: "left-symmetric", 3: "right-symmetric"}
MEMBERS = ("acq-1.raw", "acq-2.raw", "acq-3.raw")
WITNESS_HEADER = b"RRCA-DAWN-WITNESS-v1\n"
PHASES = ["PREPARE_SENT", "RESPONSE_OBSERVED", "READBACK_OBSERVED",
          "COMMIT_WRITTEN"]
SD_RE = re.compile(r"\[rrca@32473 ([^\]]*)\]")
PARAM_RE = re.compile(r'(\w+)="([^"]*)"')


# ---------------------------------------------------------------- evidence

def load_evidence(argv):
    candidates = []
    if len(argv) > 1:
        candidates.append(argv[1])
    candidates += [
        "files/dawn-array.zip",
        "../dawn-array.zip",
        "docs/2026-chronos-csctf/forensics/dawn-array.zip",
        "/tmp/opencode/dawn2",
    ]
    for path in candidates:
        if not path:
            continue
        if os.path.isdir(path):
            direct = {n: os.path.join(path, n) for n in MEMBERS}
            nested = {n: os.path.join(path, "dawn-array", n) for n in MEMBERS}
            for files in (direct, nested):
                if all(os.path.isfile(p) for p in files.values()):
                    print(f"[*] Loading members from {path}")
                    members = {n: open(p, "rb").read()
                               for n, p in files.items()}
                    tool = None
                    for cand in (os.path.join(path, "tools",
                                              "raid5_extract.py"),
                                  os.path.join(path, "dawn-array", "tools",
                                              "raid5_extract.py")):
                        if os.path.isfile(cand):
                            tool = open(cand, "rb").read()
                    return members, tool
        elif os.path.isfile(path) and path.lower().endswith(".zip"):
            print(f"[*] Loading {path}")
            with zipfile.ZipFile(path) as zf:
                names = zf.namelist()
                members = {n: zf.read(m) for n in MEMBERS
                           for m in names if m.endswith(n)}
                tool = next((zf.read(m) for m in names
                             if m.endswith("tools/raid5_extract.py")), None)
                assert len(members) == 3 and tool, "incomplete ZIP"
                return members, tool
    raise SystemExit("[-] Provide dawn-array.zip or its extracted dir")


# ---------------------------------------------------------------- md RAID-5

def parse_superblock(blob, name):
    sb_off = blob.find(struct.pack("<I", MD_MAGIC))
    assert sb_off == 0x1000, f"{name}: v1 superblock not at 0x1000"
    sb = blob[sb_off:sb_off + 512]
    assert struct.unpack_from("<I", sb, 4)[0] == 1, "not md v1"
    level = struct.unpack_from("<i", sb, 72)[0]
    layout = struct.unpack_from("<I", sb, 76)[0]
    size = struct.unpack_from("<Q", sb, 80)[0]
    chunksize = struct.unpack_from("<I", sb, 88)[0]
    ndisks = struct.unpack_from("<I", sb, 92)[0]
    data_offset = struct.unpack_from("<Q", sb, 128)[0]
    dev_number = struct.unpack_from("<I", sb, 160)[0]
    max_dev = struct.unpack_from("<I", sb, 220)[0]
    roles = [struct.unpack_from("<H", sb, 256 + 2 * i)[0]
             for i in range(max_dev)]
    assert level == 5 and ndisks == 4, f"{name}: not 4-member RAID-5"
    role = roles[dev_number]
    assert role not in (0xFFFF, 0xFFFE), f"{name}: spare/faulty member"
    return {
        "layout": MD_LAYOUTS[layout],
        "chunk_bytes": chunksize * 512,
        "data_offset_bytes": data_offset * 512,
        "array_bytes": (ndisks - 1) * size * 512,
        "member_count": ndisks,
        "role": role,
    }


def derive_geometry(members):
    per_member = {n: parse_superblock(b, n) for n, b in members.items()}
    first = next(iter(per_member.values()))
    for m in per_member.values():
        assert all(m[k] == first[k] for k in
                   ("layout", "chunk_bytes", "data_offset_bytes",
                    "array_bytes", "member_count")), "member geometry split"
    roles = sorted(m["role"] for m in per_member.values())
    assert len(set(roles)) == first["member_count"] - 1, "need N-1 roles"
    missing = (set(range(first["member_count"])) - set(roles)).pop()
    print(f"[*] md RAID-5: layout={first['layout']} "
          f"chunk={first['chunk_bytes']} "
          f"data_off={first['data_offset_bytes']} "
          f"array={first['array_bytes']} roles={roles} missing={missing}")
    return first, {n: per_member[n]["role"] for n in members}


def reconstruct(members, tool_src, geom, roles, tmp):
    helper = os.path.join(tmp, "raid5_extract.py")
    open(helper, "wb").write(tool_src)
    img = os.path.join(tmp, "array.img")
    cmd = [sys.executable, helper]
    for name, role in roles.items():
        part = os.path.join(tmp, name)
        open(part, "wb").write(members[name])
        cmd += ["--member", f"{role}:{part}"]
    cmd += ["--member-count", str(geom["member_count"]),
            "--chunk-bytes", str(geom["chunk_bytes"]),
            "--data-offset-bytes", str(geom["data_offset_bytes"]),
            "--array-bytes", str(geom["array_bytes"]),
            "--layout", geom["layout"],
            "--output", img]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"raid5_extract failed: {proc.stderr}"
    raw = open(img, "rb").read()
    assert raw[1024 + 0x38:1024 + 0x3A] == b"\x53\xef", \
        "rebuilt image is not ext4 - geometry wrong"
    print(f"[*] Rebuilt {len(raw)} logical bytes, ext4 magic OK")
    return img


# ---------------------------------------------------------------- ext4 (read-only debugfs dumps)

EVIDENCE_PATHS = [
    "/var/lib/rrca/dispatch.sqlite",
    "/var/lib/rrca/dispatch.sqlite-wal",
    "/var/lib/rrca/dispatch.sqlite-shm",
    "/var/log/rrca/dispatch-gateway.syslog",
    "/var/log/rrca/controller-access.pcapng",
]


def dump_files(image, tmp):
    out = {}
    for path in EVIDENCE_PATHS:
        dest = os.path.join(tmp, os.path.basename(path))
        proc = subprocess.run(["debugfs", "-R", f"dump {path} {dest}",
                               image], capture_output=True, text=True)
        assert proc.returncode == 0 and os.path.isfile(dest), \
            f"debugfs dump failed for {path}: {proc.stderr}"
        out[os.path.basename(path)] = open(dest, "rb").read()
        print(f"[*] debugfs dump  : {path} ({len(out[os.path.basename(path)])} bytes)")
    return out


# ---------------------------------------------------------------- syslog + pcapng

def parse_syslog(blob):
    lines = blob.decode().splitlines()
    recs, by_cycle = [], {}
    for idx, line in enumerate(lines):
        m = SD_RE.search(line)
        assert m, f"syslog line {idx} has no rrca@32473 element"
        d = dict(PARAM_RE.findall(m.group(1)))
        d["_idx"] = idx
        recs.append(d)
        by_cycle.setdefault(d["cycle_id"], {})[d["phase"]] = d
    print(f"[*] Syslog        : {len(lines)} records, "
          f"{len(by_cycle)} cycles")
    return recs, by_cycle


def iter_pcapng_packets(data):
    assert data[:4] == b"\x0a\x0d\x0d\x0a", "not a pcapng file"
    endian = "<" if data[8:12] == b"\x4d\x3c\x2b\x1a" else ">"
    off = 0
    while off + 12 <= len(data):
        btype, blen = struct.unpack_from(endian + "II", data, off)
        if blen < 12 or off + blen > len(data):
            break
        body = data[off + 8:off + blen - 4]
        if btype == 0x00000006 and len(body) >= 20:
            caplen = struct.unpack_from(endian + "I", body, 12)[0]
            yield body[20:20 + caplen]
        elif btype == 0x00000003 and len(body) >= 4:
            caplen = struct.unpack_from(endian + "I", body, 0)[0]
            yield body[4:4 + caplen]
        if btype == 0x0A0D0D0A and len(body) >= 4:
            endian = "<" if body[:4] == b"\x4d\x3c\x2b\x1a" else ">"
        off += blen


def reassemble(stream_segments):
    out, nxt = bytearray(), None
    for seq, payload in sorted(stream_segments):
        if not payload:
            continue
        if nxt is None:
            nxt = seq
        if seq > nxt:
            break  # gap: no pipelining analysis on truncated streams
        skip = max(0, nxt - seq)
        out.extend(payload[skip:])
        nxt = max(nxt, seq + len(payload))
    return bytes(out)


def parse_http(stream):
    msgs, i = [], 0
    while i < len(stream):
        hend = stream.find(b"\r\n\r\n", i)
        assert hend >= 0, "truncated HTTP stream"
        head = stream[i:hend].decode("latin1")
        m = re.search(r"[Cc]ontent-[Ll]ength:\s*(\d+)", head)
        length = int(m.group(1)) if m else 0
        assert b"ransfer-Encoding" not in stream[i:hend], \
            "transfer encoding forbidden by DP-7"
        msgs.append((head, stream[hend + 4:hend + 4 + length]))
        i = hend + 4 + length
    return msgs


def parse_exchange(pcap_blob):
    conns = {}
    for pkt in iter_pcapng_packets(pcap_blob):
        off, eth = 14, struct.unpack_from(">H", pkt, 12)[0]
        while eth in (0x8100, 0x88A8):
            eth = struct.unpack_from(">H", pkt, off + 2)[0]
            off += 4
        assert eth == 0x0800, "non-IPv4 packet in capture"
        ihl = (pkt[off] & 0x0F) * 4
        total = struct.unpack_from(">H", pkt, off + 2)[0]
        ip_end = off + total if total else len(pkt)
        src = ".".join(str(b) for b in pkt[off + 12:off + 16])
        dst = ".".join(str(b) for b in pkt[off + 16:off + 20])
        tcp = off + ihl
        sport, dport, seq = struct.unpack_from(">HHI", pkt, tcp)
        doff = ((pkt[tcp + 12] >> 4) & 0xF) * 4
        payload = pkt[tcp + doff:ip_end]
        key = tuple(sorted(((src, sport), (dst, dport))))
        side = "C" if dport == 8080 or sport != 8080 else "S"
        conns.setdefault(key, {"C": [], "S": []})[side].append(
            (seq, payload))
    assert len(conns) == 128, f"expected 128 connections, got {len(conns)}"
    return conns


def headers(head):
    fields = {}
    for line in head.split("\r\n")[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip().lower()] = v.strip()
    return fields


# ---------------------------------------------------------------- DP-7

def qualify(ledger, sys_by_cycle, conns):
    qualifying, notes = [], Counter()
    for key, sides in conns.items():
        (post_h, post_b), (get_h, get_b) = parse_http(
            reassemble(sides["C"]))
        (resp_h, resp_b), (read_h, read_b) = parse_http(
            reassemble(sides["S"]))
        assert post_h.splitlines()[0].startswith("POST /v1/reservations")
        assert get_h.splitlines()[0].startswith("GET /v1/readback")
        assert resp_h.splitlines()[0].startswith("HTTP/1.1 201"), \
            f"non-201 reservation: {resp_h.splitlines()[0]}"
        assert read_h.splitlines()[0].startswith("HTTP/1.1 200"), \
            f"non-200 readback: {read_h.splitlines()[0]}"
        post, resp, get, read = (headers(post_h), headers(resp_h),
                                headers(get_h), headers(read_h))
        cycle_id = post["x-rrca-cycle"]
        assert cycle_id in ledger, f"POST cycle {cycle_id} not in ledger"
        row = ledger[cycle_id]
        problems = []
        # Q2
        if (resp.get("x-rrca-cycle"), resp.get("x-rrca-request")) != \
                (cycle_id, row["request_id"]):
            problems.append("Q2: response does not echo POST ids")
        req = json.loads(post_b)
        if (req.get("revision"), req.get("register"), req.get("value")) != \
                (row["prepare_revision"], row["release_register"],
                 row["release_value"]):
            problems.append("Q2: POST body differs from ledger row")
        # Q3
        ans = json.loads(resp_b)
        if ans.get("revision") != row["prepare_revision"]:
            problems.append("Q3: response revision differs from ledger")
        if ans.get("nonce") != row["reservation_nonce"]:
            problems.append("Q3: response nonce differs from ledger")
        seen = sys_by_cycle[cycle_id]["RESPONSE_OBSERVED"]
        if ans.get("nonce") != seen.get("nonce"):
            problems.append("Q3: response nonce differs from syslog")
        # Q4
        if get.get("x-rrca-readback-for") != row["request_id"]:
            problems.append("Q4: GET names a different request")
        view = json.loads(read_b)
        if (view.get("nonce"), view.get("revision")) != \
                (ans.get("nonce"), ans.get("revision")):
            problems.append("Q4: readback view differs from reservation")
        if (view.get("register"), view.get("value")) != \
                (row["release_register"], row["release_value"]):
            problems.append("Q4: readback view differs from ledger")
        seen_rb = sys_by_cycle[cycle_id]["READBACK_OBSERVED"]
        if (seen_rb.get("nonce"), seen_rb.get("revision"),
                seen_rb.get("release_register"),
                seen_rb.get("release_value")) != \
                (row["reservation_nonce"], row["prepare_revision"],
                 row["release_register"], row["release_value"]):
            problems.append("Q4: syslog readback differs from ledger")
        # Q1 + Q5 (ledger row exists by construction; phases from syslog)
        phases = sys_by_cycle[cycle_id]
        if set(phases) != set(PHASES):
            problems.append("Q1: phase set incomplete/duplicated")
        ordered = sorted(phases.values(), key=lambda d: d["_idx"])
        if [d["phase"] for d in ordered] != PHASES:
            problems.append("Q5: phases out of order")
        if any(d["request_id"] != row["request_id"] or
               d["gateway_seq"] != str(row["gateway_seq"])
               for d in ordered):
            problems.append("Q1: phase ids diverge from ledger row")
        if problems:
            notes[tuple(sorted(problems))] += 1
        else:
            qualifying.append(row)
    return qualifying, notes


# ---------------------------------------------------------------- main

def main():
    members, tool_src = load_evidence(sys.argv)
    assert tool_src, "tools/raid5_extract.py missing from evidence"
    geom, roles = derive_geometry(members)

    with tempfile.TemporaryDirectory() as tmp:
        image = reconstruct(members, tool_src, geom, roles, tmp)
        dumps = dump_files(image, tmp)

        db_path = os.path.join(tmp, "dispatch.sqlite")
        for name in ("dispatch.sqlite", "dispatch.sqlite-wal",
                     "dispatch.sqlite-shm"):
            open(db_path.replace("dispatch.sqlite", name), "wb").write(
                dumps[name])
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cols = ("cycle_id,request_id,gateway_seq,prepare_revision,"
                "reservation_nonce,release_register,release_value")
        ledger = {r[0]: dict(zip(
            ("cycle_id", "request_id", "gateway_seq", "prepare_revision",
             "reservation_nonce", "release_register", "release_value"), r))
            for r in con.execute(f"SELECT {cols} FROM cycles")}
        print(f"[*] Ledger        : {len(ledger)} rows (WAL applied)")
        assert len(ledger) == 128, "expected gateway_seq 1..128"

        _, sys_by_cycle = parse_syslog(dumps["dispatch-gateway.syslog"])
        conns = parse_exchange(dumps["controller-access.pcapng"])
        print(f"[*] Capture       : {len(conns)} connections, "
              f"POST/201 + GET/200 each, no pipelining")

        qualifying, notes = qualify(ledger, sys_by_cycle, conns)
        print(f"[*] Non-qualifying classes: {dict(notes)}")
        print(f"[*] Qualifying    : {len(qualifying)} cycles")
        qualifying.sort(key=lambda r: r["gateway_seq"])
        print("[*] Qualifying gateway_seq: "
              + ",".join(str(r["gateway_seq"]) for r in qualifying))

        blob = WITNESS_HEADER + "".join(
            "{cycle_id}|{request_id}|{prepare_revision}|{reservation_nonce}|"
            "{release_register}|{release_value}\n".format(**r)
            for r in qualifying).encode()
        witness = hashlib.sha256(blob).hexdigest()
        print(f"[*] Witness bytes : {len(blob)} "
              f"(header 21 + {len(qualifying)} lines)")
        print(f"\n[+] FLAG            : CSCTF{{dawn_{witness}}}")


if __name__ == "__main__":
    main()
