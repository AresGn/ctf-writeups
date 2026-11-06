#!/usr/bin/env python3
"""
CSCTF 2026 - Ground Lock (reverse/easy)
Recover the 24-byte GRIFFON-FC service code from fcunlock without
brute force: the checker hashes each 8-byte little-endian chunk with
the splitmix64 finalizer and compares against three stored targets,
and every step of that finalizer is invertible mod 2**64.

Reversing (all constants read from the binary, never assumed):
  input[0:8] --u64le--> mix --> 0x8bfd351846ffb86b
  input[8:16] --u64le--> mix --> 0x3ff3fd892aa7e3b2
  input[16:24] --u64le--> mix --> 0xf61e79e7e639e0d2
  mix(x) = ror-shift-xor(x,33) * 0xff51afd7ed558ccd ...
  inverse: same xor-shift (involution for shift 33) and modular
  inverses of the two odd multipliers.

Usage:
    python3 solve.py [fcunlock]
"""

import os
import struct
import sys

MASK = (1 << 64) - 1
S1 = 0xFF51AFD7ED558CCD
S2 = 0xC4CEB9FE1A85EC53
SHIFT = 33


def find_targets(argv):
    candidates = []
    if len(argv) > 1:
        candidates.append(argv[1])
    candidates += [
        "files/fcunlock",
        "../fcunlock",
        "docs/2026-chronos-csctf/reverse/fcunlock",
        "/tmp/opencode/ground/fcunlock",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            print(f"[*] Loading {path}")
            with open(path, "rb") as fh:
                return fh.read()
    raise SystemExit("[-] Provide the fcunlock binary")


def splitmix_mix(x):
    x ^= (x >> SHIFT) & MASK
    x &= MASK
    x = (x * S1) & MASK
    x ^= (x >> SHIFT) & MASK
    x &= MASK
    x = (x * S2) & MASK
    x ^= (x >> SHIFT) & MASK
    return x & MASK


def splitmix_unmix(y):
    # x ^= x >> 33 is an involution (2*33 >= 64); the odd multipliers
    # invert mod 2**64.
    x = (y ^ (y >> SHIFT)) & MASK
    x = (x * pow(S2, -1, 1 << 64)) & MASK
    x = (x ^ (x >> SHIFT)) & MASK
    x = (x * pow(S1, -1, 1 << 64)) & MASK
    x = (x ^ (x >> SHIFT)) & MASK
    return x


def main():
    blob = find_targets(sys.argv)
    assert blob[:4] == b"\x7fELF", "not an ELF binary"

    # The rodata table holds the two splitmix constants, the shift (33),
    # the chunk count (3), then the three expected digests.
    # S1 also appears as a movabs immediate in .text; the table is the
    # occurrence followed by S2, the shift and the chunk count.
    table = None
    needle = struct.pack("<Q", S1)
    start = 0
    while True:
        i1 = blob.find(needle, start)
        assert i1 >= 0, "splitmix constants not found"
        if blob[i1 + 8:i1 + 16] == struct.pack("<Q", S2):
            table = i1
            break
        start = i1 + 8
    shift, count = struct.unpack_from("<QQ", blob, table + 16)
    assert (shift, count) == (SHIFT, 3), "unexpected table layout"
    targets = struct.unpack_from("<QQQ", blob, table + 32)
    print(f"[*] Table       : shift={shift} count={count}")
    for i, t in enumerate(targets):
        print(f"    chunk {i} mix == {t:#018x}")

    code = b"".join(splitmix_unmix(t).to_bytes(8, "little")
                    for t in targets)
    print(f"[*] Code bytes  : {code!r} ({len(code)} bytes)")
    assert len(code) == 24 and all(32 <= c < 127 for c in code)
    assert all(splitmix_mix(int.from_bytes(code[i * 8:(i + 1) * 8],
                                           "little")) == targets[i]
               for i in range(3)), "round-trip check failed"

    print(f"\n[+] FLAG            : CSCTF{{{code.decode()}}}")


if __name__ == "__main__":
    main()
