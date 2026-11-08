#!/usr/bin/env python3
"""Rebuild the activations from the iCalendar export and POST the attestation.
Usage: solve.py http://HOST:PORT [--post]   (needs python-dateutil)"""
import sys, json, urllib.request
from datetime import datetime, timedelta, timezone
from dateutil.rrule import rrulestr
B = sys.argv[1]
get = lambda p: urllib.request.urlopen(B + p).read().decode()
brief = json.loads(get("/brief"))
P = lambda s: datetime.strptime(s, "%Y%m%dT%H%M%SZ")
F = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
H0 = datetime.strptime(brief["horizon_start_utc"], "%Y-%m-%dT%H:%M:%SZ")
H1 = datetime.strptime(brief["horizon_end_utc"], "%Y-%m-%dT%H:%M:%SZ")
# parse VEVENTs (unfold lines)
lines = []
for l in get("/case.ics").replace("\r\n", "\n").split("\n"):
    if l.startswith((" ", "\t")) and lines: lines[-1] += l[1:]
    else: lines.append(l)
events, cur = [], None
for l in lines:
    if l == "BEGIN:VEVENT": cur = {}
    elif l == "END:VEVENT": events.append(cur); cur = None
    elif cur is not None and ":" in l:
        k, v = l.split(":", 1); cur.setdefault(k.split(";")[0], []).append(v)
masters, detached = {}, {}
for e in events:
    uid = e["UID"][0]
    if "RECURRENCE-ID" in e: detached[(uid, P(e["RECURRENCE-ID"][0]))] = e
    else: masters[uid] = e
out = []
used = set()
for uid, m in masters.items():
    s = P(m["DTSTART"][0]); dur = P(m["DTEND"][0]) - s
    ids = {x.replace(tzinfo=None) for x in rrulestr(m["RRULE"][0], dtstart=s.replace(tzinfo=timezone.utc))} if "RRULE" in m else {s}
    ids.add(s)                                           # DTSTART is always the first occurrence
    for r in m.get("RDATE", []): ids |= {P(x) for x in r.split(",")}
    for x in m.get("EXDATE", []): ids -= {P(y) for y in x.split(",")}   # EXDATE first
    for rid in sorted(ids):
        d = detached.get((uid, rid))
        if d:                                            # detached instance replaces the nominal one
            used.add((uid, rid)); st, en = P(d["DTSTART"][0]), P(d["DTEND"][0])
        else: st, en = rid, rid + dur
        if H0 <= st < H1:
            out.append({"uid": uid, "recurrence_id_utc": F(rid), "start_utc": F(st), "end_utc": F(en), "category": "EMERGENCY-RELAY"})
print('unused detached:', set(detached) - used, file=sys.stderr)
out.sort(key=lambda r: r["start_utc"])
rep = {"activations": out}
print(len(out), file=sys.stderr); print(json.dumps(rep))
if "--post" in sys.argv:
    q = urllib.request.Request(B + "/attest", json.dumps(rep).encode(), {"Content-Type": "application/json"})
    try: print(urllib.request.urlopen(q).read().decode())
    except urllib.error.HTTPError as ex: print(ex.code, ex.read().decode())
