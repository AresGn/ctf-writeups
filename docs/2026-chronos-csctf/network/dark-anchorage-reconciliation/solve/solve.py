#!/usr/bin/env python3
"""Dark Anchorage Reconciliation - build the KALNET-RECON-1 report from the 4 evidence files and POST it.
Usage: solve.py http://HOST:PORT [--post]"""
import json, csv, math, statistics as st, sys, urllib.request
from datetime import datetime, timedelta
B = sys.argv[1] if len(sys.argv) > 1 else "http://w01.ctf.chronos-security.ro:36289"
get = lambda p: urllib.request.urlopen(B + p).read().decode()
R = 6378137
fault = dict(l.split("=") for l in get("/files/cable-fault.txt").splitlines() if "=" in l)
lat0, lon0 = float(fault["cable_lat"]), float(fault["cable_lon"])
def loc(la, lo): return (R*math.cos(math.radians(lat0))*math.radians(lo-lon0), R*math.radians(la-lat0))
P = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
F = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
rad_txt = get("/files/radar.csv").splitlines()
off = int([l for l in rad_txt if "utc_offset" in l][0].split("=")[1])
rad = {}
for r in csv.DictReader([l for l in rad_txt if not l.startswith("#")]):
    rad.setdefault(r["radar_track"], {})[P(r["local_time"]) - timedelta(minutes=off)] = loc(float(r["lat"]), float(r["lon"]))
ais = {}
for l in get("/files/ais.ndjson").splitlines():
    j = json.loads(l)
    if j["type"] == "position": ais.setdefault(j["mmsi"], {})[P(j["utc"])] = loc(j["lat"], j["lon"])
def resid(t, m):
    ks = sorted(set(rad[t]) & set(ais[m]))
    return ks, [(ais[m][k][0]-rad[t][k][0], ais[m][k][1]-rad[t][k][1]) for k in ks]
def score(t, m):
    ks, rs = resid(t, m)
    return st.median(math.hypot(*r) for r in rs) if rs else 1e9
assoc = {t: min(ais, key=lambda m: score(t, m)) for t in sorted(rad)}
assert len(set(assoc.values())) == 16, assoc
print({t: round(score(t, m), 1) for t, m in assoc.items()}, file=sys.stderr)
# divergence
best = None
for t, m in assoc.items():
    ks, rs = resid(t, m); mag = [math.hypot(*r) for r in rs]
    i = 0
    while i < len(ks):
        if mag[i] < 250: i += 1; continue
        j = i
        while j+1 < len(ks) and mag[j+1] >= 250 and abs(rs[j+1][0]-rs[j][0]) <= 15 and abs(rs[j+1][1]-rs[j][1]) <= 15: j += 1
        if j-i+1 >= 4 and (best is None or j-i > best[0]): best = (j-i, t, m, ks[i], ks[j], rs[i:j+1])
        i = j+1
_, bt, bm, s, e, rr = best
mean = lambda v: math.floor(abs(sum(v)/len(v)) + .5) * (1 if sum(v) >= 0 else -1)
div = {"mmsi": bm, "start_utc": F(s), "end_utc": F(e), "ais_minus_radar_east_m": mean([r[0] for r in rr]), "ais_minus_radar_north_m": mean([r[1] for r in rr])}
# CPA: radar segments
cp = None
for t, d in rad.items():
    ks = sorted(d)
    for a, b in zip(ks, ks[1:]):
        p, q = d[a], d[b]; v = (q[0]-p[0], q[1]-p[1]); vv = v[0]**2 + v[1]**2
        u = 0 if vv == 0 else min(1, max(0, -(p[0]*v[0]+p[1]*v[1])/vv))
        dist = math.hypot(p[0]+u*v[0], p[1]+u*v[1]); tt = a + (b-a)*u
        if cp is None or dist < cp[0] - 1e-9: cp = (dist, tt, t)
dist, tt, ct = cp
import calendar
sec = calendar.timegm(tt.utctimetuple()) + tt.microsecond/1e6; fl = math.floor(sec); fr = sec - fl
tt = datetime(1970,1,1) + timedelta(seconds=fl + (1 if fr > .5 else 0))
rep = {"version": "KALNET-RECON-1", "radar_utc_offset_minutes": off,
       "associations": [{"radar_track": t, "mmsi": assoc[t]} for t in sorted(assoc)],
       "divergence": div,
       "closest_approach": {"mmsi": assoc[ct], "utc": F(tt), "distance_m": math.floor(dist*10+.5)/10}}
print(json.dumps(rep))
if "--post" in sys.argv:
    req = urllib.request.Request(B + "/reconcile", json.dumps(rep).encode(), {"Content-Type": "application/json"})
    try: print(urllib.request.urlopen(req).read().decode())
    except urllib.error.HTTPError as ex: print(ex.code, ex.read().decode())
