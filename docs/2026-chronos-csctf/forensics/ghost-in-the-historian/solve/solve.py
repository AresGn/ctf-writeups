#!/usr/bin/env python3
"""
CSCTF 2026 - Ghost in the Historian (forensics/medium)
Recover the SAFETY_INTERLOCK_TOKEN from an encrypted substation
historian image without executing anything.

Chain (all parameters derived from the evidence, never assumed):
  1. The ext4 flat extent holds 3 *.enc files plus a ransom note and a
     syslog line written by the encryptor itself:
     "historian_enc[PID]: starting encryption sweep" -> PID = 2764964.
  2. The deleted encryptor (carved ELF, read-only, never executed)
     disassembles to: seed = ((time() ^ getpid()) * 0x9E3779B1) mod 2^32,
     keystream = xorshift32(13,17,5) bytes, applied per file with the
     state carried over from file to file in scandir order.
  3. The log timestamp (2026-10-02 04:13, minute precision) bounds the
     seed time(); brute-forcing it finds t = 04:13:05, whose seed-state
     decryption of grid_topology.cfg.enc yields ASCII config text.
  4. Chaining the state across grid -> cache -> node decrypts all
     three originals; the token sits in the topology config.

Requires: debugfs (e2fsprocs, read-only dumps of the flat extent).
Never mounts the image, never executes recovered programs.

Usage:
    python3 solve.py [ghost-in-the-historian.zip | flat-extent | dir]
"""

import datetime
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import zipfile

PID_RE = re.compile(rb"historian_enc\[(\d+)\]")
SWEEP_RE = re.compile(rb"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) .*starting "
                      rb"encryption sweep")
TOKEN_RE = re.compile(rb"SAFETY_INTERLOCK_TOKEN=(CSCTF\{[^}]*\})")
MUL = 0x9E3779B1
MASK = 0xFFFFFFFF


# ---------------------------------------------------------------- evidence

def load_evidence(argv):
    candidates = []
    if len(argv) > 1:
        candidates.append(argv[1])
    candidates += [
        "files/ghost-in-the-historian.zip",
        "../ghost-in-the-historian.zip",
        "docs/2026-chronos-csctf/network/ghost-in-the-historian.zip",
        "/tmp/opencode/ghost/evidence-flat.vmdk",
    ]
    for path in candidates:
        if not path:
            continue
        if os.path.isfile(path):
            if path.lower().endswith((".zip",)):
                print(f"[*] Loading {path}")
                with zipfile.ZipFile(path) as zf:
                    names = zf.namelist()
                    flat = next(n for n in names if n.endswith("-flat.vmdk"))
                    return zf.read(flat)
            elif path.endswith((".vmdk", ".img", ".dd", ".raw")):
                print(f"[*] Loading flat extent {path}")
                with open(path, "rb") as fh:
                    return fh.read()
        elif os.path.isdir(path):
            for name in ("evidence-flat.vmdk",):
                cand = os.path.join(path, name)
                if os.path.isfile(cand):
                    print(f"[*] Loading flat extent {cand}")
                    with open(cand, "rb") as fh:
                        return fh.read()
    raise SystemExit("[-] Provide ghost-in-the-historian.zip or flat extent")


def dump_file(image_path, fs_path, dest):
    proc = subprocess.run(["debugfs", "-R", f"dump {fs_path} {dest}",
                           image_path], capture_output=True, text=True)
    assert proc.returncode == 0 and os.path.isfile(dest), \
        f"debugfs dump failed for {fs_path}: {proc.stderr}"
    with open(dest, "rb") as fh:
        return fh.read()


# ---------------------------------------------------------------- crypto

def xorshift_states(seed, n):
    s, out = seed, []
    for _ in range(n):
        x = s
        x ^= (x << 13) & MASK
        x &= MASK
        x ^= x >> 17
        x ^= (x << 5) & MASK
        x &= MASK
        s, out = x, out + [x]
    return out


def keystream(seed, n, skip_states=0):
    states = xorshift_states(seed, skip_states + (n + 3) // 4)
    out = bytearray()
    for x in states[skip_states:]:
        out.extend(struct.pack("<I", x))
        if len(out) >= n:
            break
    return bytes(out[:n])


def xor_bytes(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def printable_score(blob):
    return sum(1 for c in blob if 32 <= c < 127 or c in (10, 13, 9))


# ---------------------------------------------------------------- main

def main():
    flat = load_evidence(sys.argv)
    assert flat[1024 + 0x38:1024 + 0x3A] == b"\x53\xef", "not an ext4 extent"
    print(f"[*] Flat extent   : {len(flat)} bytes, ext4 magic OK")

    with tempfile.TemporaryDirectory() as tmp:
        img = os.path.join(tmp, "evidence-flat.vmdk")
        open(img, "wb").write(flat)
        syslog = dump_file(img, "/var/log/historian.log",
                           os.path.join(tmp, "historian.log"))
        enc = {}
        for name in ("node_status.json.enc", "grid_topology.cfg.enc",
                     "historian_cache.dat.enc"):
            enc[name] = dump_file(img, f"/var/historian/{name}",
                                  os.path.join(tmp, name))
            print(f"[*] {name:28s} {len(enc[name])} bytes")

    pid = int(PID_RE.search(syslog).group(1))
    sweep = SWEEP_RE.search(syslog).group(1).decode()
    print(f"[*] Sweep log     : {sweep} historian_enc[{pid}]")
    day = datetime.datetime.strptime(sweep[:10], "%Y-%m-%d").replace(
        tzinfo=datetime.timezone.utc)
    base = int(day.timestamp())

    # The grid config decrypts from seed state and is fully printable;
    # the other two start from chained states, so only the grid can
    # validate a seed candidate on its own.
    target = enc["grid_topology.cfg.enc"]
    found = None
    for t in range(base, base + 86400):
        seed = (((t ^ pid) * MUL) & MASK)
        plain = xor_bytes(target, keystream(seed, len(target)))
        if printable_score(plain) == len(plain) and plain.startswith(b"#"):
            found = (t, seed, plain)
            break
    assert found, "seed time not found on sweep day"
    t, seed, grid_plain = found
    stamp = datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
    print(f"[*] Seed time     : {stamp} (t={t}) seed={seed:#010x}")
    print(f"[*] grid_topology :\n{grid_plain.decode()}")

    # Chain: grid (235 B -> 59 states), cache (64 B -> 16 states), node.
    cache_len = len(enc["historian_cache.dat.enc"])
    node_len = len(enc["node_status.json.enc"])
    cache_plain, node_plain, order = None, None, None
    for second, third in (("historian_cache.dat.enc",
                           "node_status.json.enc"),
                          ("node_status.json.enc",
                           "historian_cache.dat.enc")):
        mid = xor_bytes(enc[second],
                        keystream(seed, len(enc[second]),
                                  skip_states=59))
        if printable_score(mid) != len(mid):
            continue
        last = xor_bytes(enc[third],
                         keystream(seed, len(enc[third]),
                                   skip_states=59 + (len(enc[second]) + 3) //
                                   4))
        if printable_score(last) == len(last):
            cache_plain, node_plain = (
                (mid, last) if second.startswith("historian")
                else (last, mid))
            order = (second, third)
            break
    assert order, "chained decryption order not found"
    print(f"[*] Chain order   : grid_topology.cfg.enc -> {' -> '.join(order)}")
    print(f"[*] historian_cache:\n{cache_plain.decode()}")
    print(f"[*] node_status   :\n{node_plain.decode()}")
    json.loads(node_plain)  # the status file must stay valid JSON

    token = TOKEN_RE.search(grid_plain).group(1).decode()
    print(f"\n[+] FLAG            : {token}")


if __name__ == "__main__":
    main()
