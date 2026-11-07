#!/usr/bin/env python3
"""afterimage: aCropalypse-style recovery of the pixels left after IEND of a cropped PNG.

Usage: python3 -I solve.py ../files/relay-capture.png recovered.png   (needs Pillow)
The cropped file was written over a longer one, so the tail of the old IDAT stream still
follows IEND. We rebuild that stream, locate a deflate block boundary by brute force
(bit offset x byte offset), seed the 32 KiB window with the end of the visible image,
and rebuild the last rows of the original image.
"""
import struct, sys, zlib
from PIL import Image

d = open(sys.argv[1], "rb").read()
W, H = struct.unpack(">II", d[16:24])
BPP, STRIDE = 3, struct.unpack(">I", d[16:20])[0] * 3 + 1          # 8-bit RGB, non-interlaced


def chunks(buf, off):
    while off < len(buf):
        n, t = struct.unpack(">I4s", buf[off:off + 8])
        yield t, buf[off + 8:off + 8 + n], off
        off += 12 + n
        if t == b"IEND":
            return


# 1. Visible image: its decompressed scanlines seed the deflate window.
idat, iend_end = b"", 0
for t, body, off in chunks(d, 8):
    if t == b"IDAT":
        idat += body
    if t == b"IEND":
        iend_end = off + 12
window = zlib.decompress(idat)[-32768:]
print(f"visible {W}x{H}, {len(d) - iend_end} bytes after IEND", file=sys.stderr)

# 2. Trailing data = tail of the old IDAT stream. It starts mid-chunk (old chunk data, then
#    its CRC), then regular IDAT chunks until the old IEND.
tail = d[iend_end:]
first = tail.index(b"IDAT") - 4                                    # length field of first whole chunk
stream = tail[:first - 4]                                          # leftover data of the cut chunk
for t, body, _ in chunks(tail, first):
    if t == b"IDAT":
        stream += body

# 3. Find where a deflate block starts: try every bit shift / byte offset, keep the longest
#    decode that reaches a final block (eof) when the window is the visible image's end.
best = (0, None)
for k in range(8):
    shifted = (int.from_bytes(stream, "little") >> k).to_bytes(len(stream), "little")
    for i in range(len(stream) - 8):
        z = zlib.decompressobj(-15, zdict=window)
        try:
            out = z.decompress(shifted[i:], 1 << 22)
        except zlib.error:
            continue
        if z.eof and len(out) > best[0]:
            best = (len(out), out)
raw = best[1]
rows = len(raw) // STRIDE
print(f"recovered {rows} full scanlines", file=sys.stderr)

# 4. Undo PNG filters (first row has no known previous row: treated as zeros).
img, prev = [], bytearray(W * BPP)
for r in range(rows):
    f, line = raw[r * STRIDE], bytearray(raw[r * STRIDE + 1:(r + 1) * STRIDE])
    for i in range(len(line)):
        a = line[i - BPP] if i >= BPP else 0
        b = prev[i]
        c = prev[i - BPP] if i >= BPP else 0
        if f == 1:
            line[i] = (line[i] + a) & 255
        elif f == 2:
            line[i] = (line[i] + b) & 255
        elif f == 3:
            line[i] = (line[i] + ((a + b) >> 1)) & 255
        elif f == 4:
            pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
            line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
    img.append(bytes(line))
    prev = line
Image.frombytes("RGB", (W, rows), b"".join(img)).save(sys.argv[2])
print("wrote", sys.argv[2], "- read the recovery key on it")
