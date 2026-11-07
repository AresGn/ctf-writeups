#!/usr/bin/env python3
"""flotsam: carve a fragmented PNG out of a raw 512-byte-sector dump.

Usage: python3 -I solve.py ../files/recorder-sectors.img out.png
Fragment 1 = PNG header .. first all-zero sector. The rest of the IDAT is in
earlier non-zero sectors (address order); the last bytes sit in the sector that
holds IEND. The IDAT CRC validates the reassembly.
"""
import struct, sys, zlib

SS = 512
d = open(sys.argv[1], "rb").read()
n = len(d) // SS
sec = lambda i: d[i * SS:(i + 1) * SS]
ascii_text = lambda s: all(32 <= c < 127 or c in (10, 13) for c in s.rstrip(b"\0"))

# 1. First fragment: from the PNG signature to the first all-zero sector.
start = d.index(b"\x89PNG\r\n\x1a\n") // SS
end = next(i for i in range(start, n) if sec(i) == b"\0" * SS)
frag1 = d[start * SS:end * SS]
idat_len = struct.unpack(">I", frag1[33:37])[0]
assert frag1[37:41] == b"IDAT"
first = frag1[41:]

# 2. Pool of orphan sectors before the PNG: drop zero sectors, the NMEA ($GPRMC) text
#    and the JPEG decoy (FFD8 .. FFD9).
iend_sec = d.index(b"IEND") // SS
jpg_a, jpg_b = d.index(b"\xff\xd8\xff") // SS, d.index(b"\xff\xd9") // SS
pool = [i for i in range(iend_sec)
        if i < start and sec(i) != b"\0" * SS and not ascii_text(sec(i)) and not jpg_a <= i <= jpg_b]

# 3. Reassemble: fragment 1 + pool (address order) + head of the IEND sector.
body = first + b"".join(sec(i) for i in pool)
last = idat_len - len(body)
idat = body + d[iend_sec * SS:iend_sec * SS + last]
crc_off = iend_sec * SS + last
crc = d[crc_off:crc_off + 4]
ok = zlib.crc32(b"IDAT" + idat) == struct.unpack(">I", crc)[0]
print(f"pool={pool} idat={len(idat)}/{idat_len} crc_ok={ok}", file=sys.stderr)
assert ok

png = frag1[:41] + idat + crc + d[crc_off + 4:crc_off + 16]   # + IEND chunk
open(sys.argv[2], "wb").write(png)
print("wrote", sys.argv[2], len(png), "bytes")
