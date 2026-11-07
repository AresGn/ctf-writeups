#!/usr/bin/env python3
"""last-commit: rebuild the LR-731 export at the QUEUED -> COMPLETED commit of a SQLite WAL.

Usage: python3 -I solve.py ../files
The originals are only read; every state is built as a plain DB image (no -wal/-shm)
in a temporary directory, so SQLite never touches the evidence.
"""
import csv, hashlib, sqlite3, struct, sys, tempfile
from pathlib import Path

d = Path(sys.argv[1])
db = d / "registry.sqlite"
base = db.read_bytes()
wal = (d / "registry.sqlite-wal").read_bytes()

# --- WAL header + frames; validate salts and the cumulative checksum -----------------
magic, _ver, ps, _seq, salt1, salt2, ck1, ck2 = struct.unpack(">8I", wal[:32])
endian = ">2I" if magic & 1 else "<2I"           # checksum word order follows the magic


def cksum(buf, a, b):
    for i in range(0, len(buf), 8):
        x, y = struct.unpack(endian, buf[i:i + 8])
        a = (a + x + b) & 0xFFFFFFFF
        b = (b + y + a) & 0xFFFFFFFF
    return a, b


a, b = cksum(wal[:24], 0, 0)
assert (a, b) == (ck1, ck2), "bad WAL header checksum"
frames, off = [], 32
while off + 24 + ps <= len(wal):
    pgno, commit, s1, s2, c1, c2 = struct.unpack(">6I", wal[off:off + 24])
    page = wal[off + 24:off + 24 + ps]
    a, b = cksum(wal[off:off + 8], a, b)
    a, b = cksum(page, a, b)
    if (s1, s2) != (salt1, salt2) or (a, b) != (c1, c2):
        break                                      # end of the valid epoch
    frames.append((pgno, commit, page))
    off += 24 + ps
print(f"{len(frames)} valid frames, commits at {[i for i, f in enumerate(frames) if f[1]]}", file=sys.stderr)

tmp = Path(tempfile.mkdtemp())
manifest = [(r["job_id"], int(r["position"]), int(r["parcel_id"]))
            for r in csv.DictReader(open(d / "delivery.csv", newline=""))]
QUERY = """SELECT m.position,p.parcel_id,p.district,p.plot_ref,h.registry_ref,t.interest_bps,t.instrument_ref
FROM manifest AS m JOIN parcel AS p ON p.parcel_id=m.parcel_id
JOIN title AS t ON t.parcel_id=p.parcel_id JOIN holder AS h ON h.holder_id=t.holder_id
WHERE m.job_id='LR-731' ORDER BY m.position ASC,h.registry_ref COLLATE BINARY ASC"""
HEADER = "position\tparcel_id\tdistrict\tplot_ref\tregistry_ref\tinterest_bps\tinstrument_ref\n"


def export_at(n):
    """Registry state after frames[:n+1] are applied (n must be a commit frame)."""
    img = bytearray(base)
    for pgno, _c, page in frames[:n + 1]:
        img[(pgno - 1) * ps:pgno * ps] = page
    path = tmp / f"state{n}.db"
    path.write_bytes(img)
    c = sqlite3.connect(path)
    state = dict(c.execute("SELECT job_id,state FROM export_job").fetchall())
    c.execute("CREATE TEMP TABLE manifest(job_id TEXT, position INTEGER, parcel_id INTEGER)")
    c.executemany("INSERT INTO manifest VALUES(?,?,?)", manifest)
    out = HEADER + "".join("\t".join(map(str, r)) + "\n" for r in c.execute(QUERY))
    return state.get("LR-731"), hashlib.sha256(out.encode()).hexdigest()


results = [(i, *export_at(i)) for i, f in enumerate(frames) if f[1]]
for i, st, h in results:
    print(f"commit frame {i}: LR-731={st} export_sha256={h}", file=sys.stderr)
# The transition commit: first commit where the job is COMPLETED
target = next(h for i, st, h in results if st == "COMPLETED")
print("CSCTF{last_commit_" + target + "}")
