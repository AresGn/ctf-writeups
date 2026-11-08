#!/usr/bin/env python3
"""phantom-drift: derive the flag from the approved vs. diverted waypoint.

Usage: python3 -I solve.py ../files
Pure data analysis: the decompiled sources are only read (base64-decoded) and compared.
"""
import base64, hashlib, json, math, re, sys
from pathlib import Path

d = Path(sys.argv[1])

# 0. The .decompiled files carry the source as base64 (to read, not to run).
for name in ("drone_control.decompiled", "command_backend.decompiled"):
    src = base64.b64decode(re.search(r'DECODED_CONTENT = "([^"]+)"', (d / name).read_text()).group(1)).decode()
    print(f"{name}: {len(src)} chars of source", file=sys.stderr)

# 1. Approved waypoint (manifest, also hard-coded in both validators).
man = json.loads((d / "mission_manifest.json").read_text())
a_lat, a_lon = man["approved_waypoint_lat"], man["approved_waypoint_lon"]

# 2. The command that was actually sent: one JSON object holding the same fields twice,
#    snake_case (approved values) and PascalCase (diverted values).
tel = json.loads((d / "telemetry_logs.json").read_text())
cmd = next(r for r in tel["readings"] if r.get("phase") == "waypoint_update")
assert (cmd["waypoint_lat"], cmd["waypoint_lon"]) == (a_lat, a_lon)
b_lat, b_lon = cmd["WaypointLat"], cmd["WaypointLon"]
print(f"approved=({a_lat},{a_lon}) diverted=({b_lat},{b_lon})", file=sys.stderr)

# 3. flight_log.bin: 24-byte header then "TAG:xxxxxxxx" XORed with the mission id as key.
blob = (d / "flight_log.bin").read_bytes()[24:]
key = man["mission_id"].encode()
tag = bytes(c ^ key[i % len(key)] for i, c in enumerate(blob)).decode()
assert tag.startswith("TAG:")
tag = tag[4:]


def haversine(r):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b_lon - a_lon) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


# 4. The statement does not fix the Earth radius: the tag (last 8 hex of the digest) decides.
for name, r in (("mean 6371000", 6371000), ("WGS84 6378137", 6378137)):
    s = f"{a_lat:.4f}{a_lon:.4f}{b_lat - a_lat:.6f}{b_lon - a_lon:.6f}{haversine(r):.1f}"
    h = hashlib.sha256(s.encode()).hexdigest()
    print(f"R={name}: {s} -> tag {h[-8:]} (expected {tag}) {'OK' if h[-8:] == tag else ''}", file=sys.stderr)
    if h[-8:] == tag:
        print("CSCTF{" + h[:16] + "}")
