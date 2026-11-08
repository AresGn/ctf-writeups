#!/usr/bin/env python3
"""
CSCTF 2026 - Operation Dawn: The Reconnaissance Plate (misc/easy)

The 256x256 photograph is quantised to multiples of 4: bits 0 and 1
of every channel are ~always 0 except in the first rows, where each
bit-plane carries an independent framed payload, read row-major over
the interleaved R,G,B values (MSB-first within each byte):

    uint32_be length || gzip(tar)

  * bit-plane 0 -> a practice plate ("Range card practice plate.
    Not for action."), annotation "DRILL SERIAL 11 ..." -- the decoy
    that plain LSB extraction finds first;
  * bit-plane 1 -> the reconnaissance plate (observation caption,
    annotation "RECON SERIAL 11 ...") -- the annotation the briefing
    asks for (serial 11 = annex entry 11, from an observation post).

The flag is built from the RECON annotation
"RECON SERIAL <n> <WORDS> CODE <check>": the RECON SERIAL / CODE
labels are stripped, and the flag is
CSCTF{<n>_<words lowercased, joined by '_'>_<check lowercased>} --
the same "<entry>_<words>_<check group>" shape used by the other
Operation Dawn annex entries.

Requires: numpy, Pillow.

Usage:
    python3 solve.py [recon-plate.png]
"""

import io
import re
import sys
import tarfile
import zlib

import numpy as np
from PIL import Image


def extract_plane(img, bit):
    bits = ((img >> bit) & 1).astype(np.uint8).reshape(-1)
    data = np.packbits(bits).tobytes()
    length = int.from_bytes(data[:4], "big")
    if data[4:6] != b"\x1f\x8b" or not (0 < length < len(data)):
        raise ValueError(f"bit-plane {bit}: no framed gzip payload")
    tar_bytes = zlib.decompressobj(31).decompress(data[4:4 + length])
    files = {}
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
        for member in tar.getmembers():
            if member.isfile():
                files[member.name] = tar.extractfile(member).read().decode()
    return files


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "recon-plate.png"
    img = np.array(Image.open(path))
    print(f"[*] {path}: {img.shape[1]}x{img.shape[0]} {img.shape[2]} channels")

    payloads = {}
    for bit in (0, 1):
        files = extract_plane(img, bit)
        payloads[bit] = files
        print(f"[*] bit-plane {bit}:")
        for name in sorted(files):
            print(f"      {name}: {files[name].strip()}")

    # The wanted annotation is the reconnaissance one, not the drill:
    # its annotation starts with RECON and its caption is an actual
    # observation report (the other caption says "Not for action").
    chosen = None
    for bit, files in payloads.items():
        caption = files.get("plate/caption.txt", "")
        annotation = files.get("plate/annotation.txt", "")
        if annotation.startswith("RECON") and "Not for action" not in caption:
            chosen = (bit, annotation)
    if chosen is None:
        raise SystemExit("reconnaissance annotation not found")
    bit, annotation = chosen
    match = re.fullmatch(
        r"RECON SERIAL (\d+) (.+?) CODE ([0-9A-Fa-f]+)\s*", annotation)
    if not match:
        raise SystemExit(f"unexpected annotation format: {annotation!r}")
    serial, words, code = match.groups()
    flag = f"CSCTF{{{serial}_{'_'.join(words.lower().split())}_{code.lower()}}}"
    print(f"[*] selected bit-plane {bit} annotation: {annotation.strip()}")
    print(flag)


if __name__ == "__main__":
    main()
