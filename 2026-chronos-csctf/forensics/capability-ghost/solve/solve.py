#!/usr/bin/env python3
"""capability-ghost: recover the sealed marker, treating every file as data.

Nothing is extracted to disk, no capability is restored, hc-probe is never run.
Usage: python3 -I solve.py ../files
"""
import hashlib, hmac, json, subprocess, sys, tarfile
from pathlib import Path

d = Path(sys.argv[1])

# 1. Tag = user.build_seal xattr of hc-probe, read from the stored PAX headers.
tag = None
with tarfile.open(d / "runner-fs.tar.gz") as t:
    for m in t:
        if m.name.endswith("usr/local/bin/hc-probe"):
            # tarfile decodes PAX values as UTF-8 with surrogateescape: undo it.
            tag = m.pax_headers["SCHILY.xattr.user.build_seal"].encode("utf-8", "surrogateescape")
        elif m.name.endswith("signaling-cfg.sealed"):
            ct = t.extractfile(m).read()
assert tag and ct

# 2. Seal epoch = X_SEAL_EPOCH field of the journal (NOT the entry's wallclock time).
out = subprocess.run(
    ["journalctl", f"--file={d / 'runner.journal'}", "--no-pager", "-o", "json"],
    capture_output=True, text=True, check=True).stdout
epoch = next(e["X_SEAL_EPOCH"] for e in map(json.loads, out.splitlines()) if "X_SEAL_EPOCH" in e)

# 3. hc-probe scheme: key = HMAC-SHA256(tag, ascii(epoch)); repeating-key XOR over 32 bytes.
key = hmac.new(tag, epoch.encode(), hashlib.sha256).digest()
print(f"tag={tag.hex()} epoch={epoch}", file=sys.stderr)
print(bytes(c ^ key[i % 32] for i, c in enumerate(ct)).decode())
