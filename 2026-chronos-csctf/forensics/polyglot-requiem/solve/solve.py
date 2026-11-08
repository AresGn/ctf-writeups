#!/usr/bin/env python3
"""polyglot-requiem: PNG+ZIP polyglot -> SQLite deleted row -> assetsignd's seal scheme.

Usage: python3 -I solve.py ../files/flight-telemetry-sdk
Nothing is executed: the PNG is parsed by hand, the ZIP is read in memory, the SQLite
file is searched as raw bytes (the row was deleted, SQLite would not show it), and the
seal scheme of `assetsignd` (found by static analysis) is re-implemented:
    msg = reverse(raw_bytes(tag)) || epoch as 8-byte little-endian
    key = SHA-256(msg);  out[i] = in[i] XOR key[i mod 32]
"""
import hashlib, io, struct, subprocess, sys, zipfile
from pathlib import Path

repo = Path(sys.argv[1])
png = (repo / "assets/telemetry_icon.png").read_bytes()

# 1. Walk the PNG chunks: tEXt "Provenance" holds the tag; the ZIP is appended after IEND.
off, tag = 8, None
while True:
    n, typ = struct.unpack(">I4s", png[off:off + 8])
    if typ == b"tEXt":
        k, _, v = png[off + 8:off + 8 + n].partition(b"\0")
        if k == b"Provenance":
            tag = bytes.fromhex(v.decode())
    off += 12 + n
    if typ == b"IEND":
        break
z = zipfile.ZipFile(io.BytesIO(png[off:]))                  # the "trailing data" is a ZIP
db = z.read("telemetry_cache.db")
print(f"tag={tag.hex()} zip members={z.namelist()}", file=sys.stderr)

# 2. Deleted row: the cell is still in the page. Record = hdr_len, 0 (NULL id), text, blob.
i = db.index(b"ci_provenance_seal")
stype = db[i - 1]                                           # serial type of the blob column
ct = db[i + 18:i + 18 + (stype - 12) // 2]
print(f"deleted row ci_provenance_seal: {len(ct)}-byte blob", file=sys.stderr)

# 3. Epoch = timestamp of the commit that added the icon (all commits share it anyway).
epoch = int(subprocess.run(
    ["git", "--git-dir", str(repo / ".git"), "log", "-1", "--format=%ct", "--", "assets/telemetry_icon.png"],
    capture_output=True, text=True, check=True).stdout)

key = hashlib.sha256(tag[::-1] + struct.pack("<Q", epoch)).digest()
print(bytes(c ^ key[j % 32] for j, c in enumerate(ct)).decode())
