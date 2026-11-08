#!/usr/bin/env python3
"""last-buffer: pick the Vim swap from the shell that died in the crash window, decode its proof.

Usage: python3 -I solve.py ../files
Pure data parsing (layout from vim-swap-layout.md): nothing is opened in Vim.
"""
import base64, hashlib, json, struct, sys
from pathlib import Path

d = Path(sys.argv[1])
ctx = json.loads((d / "case-context.json").read_text())
saved_sha = hashlib.sha256((d / ctx["saved_file"]).read_bytes()).hexdigest()
audit = [json.loads(l) for l in (d / "audit-timeline.jsonl").read_text().splitlines()]
# pid that ended with an abnormal exit (SIGHUP) on the target tty inside the crash window
crash_pid = next(e["pid"] for e in audit if e["event"] == "ANOM_ABEND" and e["tty"] == ctx["target_tty"])


def swap_lines(data):
    """Lines of every data block (ID 0x6461): count @16 (u64), line-start indexes @24 (u32)."""
    out = []
    for off in range(0, len(data), 4096):
        blk = data[off:off + 4096]
        if len(blk) < 24 or struct.unpack("<H", blk[:2])[0] != 0x6461:
            continue
        n = struct.unpack("<Q", blk[16:24])[0]
        idx = struct.unpack(f"<{n}I", blk[24:24 + 4 * n])
        out += [blk[i:blk.index(b"\0", i)].decode() for i in idx]
    return out


for swp in sorted(d.glob("*.sw?")):
    data = swp.read_bytes()
    pid = struct.unpack("<I", data[24:28])[0]
    lines = swap_lines(data)
    kv = dict(l.split(": ", 1) for l in lines if ": " in l)
    print(f"{swp.name}: pid={pid} revision={kv.get('revision_id')} base_sha_matches_saved="
          f"{kv.get('base_file_sha256') == saved_sha}", file=sys.stderr)
    if pid == crash_pid and kv.get("base_file_sha256") == saved_sha:
        b = kv["authorization_b64"]
        print(base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)).decode())
