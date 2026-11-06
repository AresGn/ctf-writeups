#!/usr/bin/env python3
"""
CSCTF 2026 — Operation Dawn: The Burnt Server (forensics/easy)
Recover the train movement register from a 3-disk RAID5 with one disk missing.

Array (from SALVAGE.txt):
  - 3 identical drives, slot 1 (disk1.img) burnt, slots 0 and 2 imaged.
  - No controller metadata -> RAID settings unknown.

Recovery (found by brute force):
  - RAID5, 3 disks, chunk 64 KiB, parity rotating right (p = stripe % 3).
  - Stripe 0 parity on disk0, so the FAT boot sector (on missing disk1)
    is rebuilt as disk0 ^ disk2.
  - Filesystem is FAT16 (512 B/sector, 1 sector/cluster), root dir at 0x8200.
  - TRAIN.GZ is deleted (0xE5 entry, start cluster 16, 16599 bytes) so its
    FAT chain is zeroed; the file is contiguous, carve clusters 16..48.
  - gzip decompress -> WHITE VALLEY HOSPITAL train register with CSCTF{...}.

Usage:
    python3 solve.py [path/to/server-remains.tar]
    python3 solve.py /tmp/opencode/burnt/disk0.img /tmp/opencode/burnt/disk2.img
"""

import sys
import tarfile
import struct
import gzip
import re
import os

CHUNK = 65536  # 64 KiB — only chunk size yielding a valid FAT root dir
MISSING = 1    # slot 1 burnt


def load_disks(args):
    if len(args) == 3 and os.path.isfile(args[1]) and os.path.isfile(args[2]):
        with open(args[1], "rb") as f:
            d0 = f.read()
        with open(args[2], "rb") as f:
            d2 = f.read()
        return d0, d2
    tar_path = args[1] if len(args) > 1 else None
    candidates = [
        tar_path,
        "files/server-remains.tar",
        "../server-remains.tar",
        "docs/2026-chronos-csctf/forensics/server-remains.tar",
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            print(f"[*] Opening {p}")
            with tarfile.open(p) as tf:
                d0 = tf.extractfile("disk0.img").read()
                d2 = tf.extractfile("disk2.img").read()
            return d0, d2
    print("[-] Provide server-remains.tar or disk0.img disk2.img")
    sys.exit(1)


def raid5_reconstruct(d0, d2, chunk=CHUNK):
    """3-disk RAID5, missing middle disk, parity p = stripe % 3 (right)."""
    nstripes = len(d0) // chunk
    out = bytearray()
    for s in range(nstripes):
        p = s % 3
        c0 = d0[s * chunk:(s + 1) * chunk]
        c2 = d2[s * chunk:(s + 1) * chunk]
        if p != MISSING:
            # missing chunk is data -> XOR parity + surviving data
            c1 = bytes(a ^ b for a, b in zip(c0, c2))
        else:
            c1 = None  # parity missing, both survivors are data
        chunks = {0: c0, 1: c1, 2: c2}
        for d in (0, 1, 2):
            if d == p:
                continue
            chunk_data = chunks[d]
            if chunk_data is None:  # pragma: no cover
                raise RuntimeError(f"stripe {s}: missing data chunk")
            out.extend(chunk_data)
    return bytes(out)


def main():
    d0, d2 = load_disks(sys.argv)
    print(f"[*] disk0 {len(d0)} bytes, disk2 {len(d2)} bytes")
    img = raid5_reconstruct(d0, d2)
    print(f"[*] Reconstructed linear image {len(img)} bytes")

    # Validate FAT boot sector
    assert img[510] == 0x55 and img[511] == 0xAA, "no boot signature"
    assert img[0] == 0xEB and img[2] == 0x90 and b"FAT" in img[:90], "no FAT boot"
    bps = struct.unpack("<H", img[11:13])[0]
    rsvd = struct.unpack("<H", img[14:16])[0]
    nfat = img[16]
    fatsz = struct.unpack("<H", img[22:24])[0]
    data_start = rsvd + nfat * fatsz + 32  # 32 root-dir sectors (512 entries)
    print(f"[*] FAT16 BPS={bps} reserved={rsvd} FATs={nfat} FATsz={fatsz} "
          f"data_start_sec={data_start}")

    root_off = (rsvd + nfat * fatsz) * bps
    train_start = train_size = None
    for i in range(16):
        e = img[root_off + i * 32:root_off + (i + 1) * 32]
        if e[0] == 0x00:
            continue
        name = e[0:8].decode(errors="replace")
        ext = e[8:11].decode(errors="replace")
        start = struct.unpack("<H", e[26:28])[0]
        size = struct.unpack("<I", e[28:32])[0]
        flag = "DELETED " if e[0] == 0xE5 else ""
        print(f"    root[{i}] {flag}'{name}'.'{ext}' start={start} size={size}")
        if e[0] == 0xE5 and e[1:5] == b"RAIN":  # _TRAIN.GZ
            train_start, train_size = start, size

    assert train_start == 16, f"unexpected TRAIN start {train_start}"
    off = (data_start + (train_start - 2)) * bps
    raw = img[off:off + train_size]
    assert raw[:2] == b"\x1f\x8b", "no gzip magic at cluster 16"
    print(f"[*] TRAIN.GZ at fs offset 0x{off:x} ({train_size} bytes), gzip magic OK")

    dec = gzip.decompress(raw)
    print(f"[*] Decompressed {len(dec)} bytes")
    m = re.findall(rb"CSCTF\{[^}]+\}", dec)
    assert m, "no flag in decompressed register"
    for f in m:
        print(f"\n[+] Flag  : {f.decode()}")
    # show context
    text = dec.decode(errors="replace")
    for i, line in enumerate(text.splitlines()):
        if "CSCTF" in line:
            print(f"[+] Line {i}: {line.strip()}")


if __name__ == "__main__":
    main()
