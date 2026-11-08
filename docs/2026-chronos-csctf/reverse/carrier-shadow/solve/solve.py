#!/usr/bin/env python3
"""carrier-shadow: lift the stage-2 ELF out of the .eh_frame_hdr search table, statically.

Usage: python3 -I solve.py ../files/carrier-shadow out-stage2.elf
Nothing is executed. Scheme (reversed from the carrier's own loader, which re-derives it at startup):
  * the sorted FDE table of .eh_frame_hdr is the carrier: the *gap* between consecutive
    function addresses encodes a symbol (gap - 2 = 0..255);
  * anchor: 8 consecutive gaps equal the first 8 values of xorshift32(seed 0x6a2b3c4d) % 61 + 34;
  * then 6 header gaps: table index, u32 LE length (4 gaps), XOR checksum;
  * the following gaps are symbols of a canonical Huffman code (code lengths = a 256-byte
    table in .rodata, selected by the table index); the concatenated MSB-first bits give a
    stream that is whitened with the same xorshift32 and is raw DEFLATE of the ELF.
"""
import re, struct, sys, zlib

d = open(sys.argv[1], "rb").read()
SEED = 0x6a2b3c4d


def xs(x):
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= x >> 17
    x ^= (x << 5) & 0xFFFFFFFF
    return x


# 1. PT_GNU_EH_FRAME -> eh_frame_hdr -> binary search table (datarel sdata4 initial locations).
phoff = struct.unpack("<Q", d[32:40])[0]
phentsize, phnum = struct.unpack("<HH", d[54:58])
hdr = None
for i in range(phnum):
    p = phoff + i * phentsize
    if struct.unpack("<I", d[p:p + 4])[0] == 0x6474E550:
        hdr = struct.unpack("<Q", d[p + 8:p + 16])[0]          # p_offset (== vaddr in this binary)
n = struct.unpack("<I", d[hdr + 8:hdr + 12])[0]
locs = [struct.unpack("<i", d[hdr + 12 + 8 * i:hdr + 16 + 8 * i])[0] for i in range(n)]
gaps = [b - a for a, b in zip(locs, locs[1:])]
print(f"eh_frame_hdr at {hdr:#x}, {n} FDE entries", file=sys.stderr)

# 2. Find the anchor made of the PRNG signature.
x, keys = SEED, []
for _ in range(8):
    x = xs(x)
    keys.append(x % 61 + 34)
a = next(i for i in range(len(gaps) - 8) if gaps[i:i + 8] == keys)
h = [g - 2 for g in gaps[a + 8:a + 14]]
table, length, checksum = h[0], h[1] | h[2] << 8 | h[3] << 16 | h[4] << 24, h[5]
print(f"anchor at entry {a}: table={table} length={length} xor={checksum}", file=sys.stderr)

# 3. Code-length tables live in .rodata; the loader indexes a pointer array: [0]=0x9b340, [1]=0x9b240
#    (found in .data.rel.ro relocations). Table 1 is a decoy ramp: only table 0 matches the checksum.
TABLES = [0x9B340, 0x9B240]
lens = list(d[TABLES[table]:TABLES[table] + 256])
count = [0] * 32
for l in lens:
    count[l] += l > 0
first, code = [0] * 33, 0
for l in range(1, 32):
    first[l] = code
    code = (code + count[l]) << 1
nxt, codes = first[:], {}
for s, l in enumerate(lens):
    if l:
        codes[s] = (nxt[l], l)
        nxt[l] += 1

# 4. Symbols -> bits (MSB first) -> bytes.
acc = nb = 0
raw = bytearray()
for g in gaps[a + 14:]:
    c, l = codes[g - 2]
    for i in range(l - 1, -1, -1):
        acc = (acc << 1) | ((c >> i) & 1)
        nb += 1
        if nb == 8:
            raw.append(acc)
            acc = nb = 0
    if len(raw) >= length:
        break
raw = raw[:length]
xr = 0
for b in raw:
    xr ^= b
assert xr == checksum, "checksum mismatch"

# 5. De-whiten with the same xorshift32, then inflate (raw DEFLATE).
x, white = SEED, bytearray()
for b in raw:
    x = xs(x)
    white.append(b ^ (x & 0xFF))
elf = zlib.decompressobj(-15).decompress(bytes(white))
assert elf[:4] == b"\x7fELF"
open(sys.argv[2], "wb").write(elf)
print(f"stage 2: {len(elf)} bytes written to {sys.argv[2]}", file=sys.stderr)

# 6. The authorization string sits in the stage-2 .rodata, next to its printf format.
print(re.search(rb"CSCTF\{[^}]+\}", elf).group().decode())
