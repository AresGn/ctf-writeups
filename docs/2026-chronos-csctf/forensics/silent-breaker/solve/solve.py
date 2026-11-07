#!/usr/bin/env python3
"""silent-breaker: build the containment report from the case files and submit it.

Usage: python3 -I solve.py http://<host>:<port> [--submit]
Without --submit only the free GET routes (/files, /events) are used and the report is printed.
With --submit it also calls /confirm-target (2 attempts!), /query/vpn-window and /submit.
Each instance is a different case, so everything is derived from that instance's files.
"""
import json, re, struct, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

base = sys.argv[1].rstrip("/")


def get(path):
    with urllib.request.urlopen(base + path, timeout=20) as r:
        return r.read()


def post(path, obj):
    req = urllib.request.Request(base + path, json.dumps(obj).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


# 1. Signalling feed -> subscribers using a GT outside GT-0000..GT-0999, joined with the roster.
events = json.loads(get("/events"))["signalling_events"]
bad = {e["msisdn"] for e in events if not (m := re.fullmatch(r"GT-(\d{4})(?:-.*)?", e["gt"])) or int(m.group(1)) > 999}
roster = json.loads(get("/files/roster.json"))["employees"]
targets = [e for e in roster if e["msisdn"] in bad and e["ot_vpn_access"]]   # only staff with OT-VPN access can matter
assert len(targets) == 1, targets
emp = targets[0]["employee_id"]
print("compromised employee:", emp, file=sys.stderr)

# 2. Historian log -> the QUALITY=SUSPECT run and its frozen value.
log = get("/files/hmi_monitoring.log").decode()
suspect = re.findall(r"IOA=(0x[0-9a-f]+) VALUE=([\d.]+)A QUALITY=SUSPECT", log)
ioa, frozen = suspect[0]
print(f"suspect run: IOA {ioa}, frozen current {frozen}", file=sys.stderr)

# 3. pcap -> C_SC_NA_1 (type 45) activation from the master (to port 2404): IOA, SCO, wire time.
pcap = get("/files/iec104_capture.pcap")
off = 24
cmd = None
while off + 16 <= len(pcap):
    sec, usec, incl, _orig = struct.unpack("<IIII", pcap[off:off + 16])
    pkt = pcap[off + 16:off + 16 + incl]
    off += 16 + incl
    ihl = (pkt[14] & 15) * 4
    tcp = pkt[14 + ihl:]
    payload = tcp[(tcp[12] >> 4) * 4:]
    dport = struct.unpack(">H", tcp[2:4])[0]
    if dport == 2404 and len(payload) >= 16 and payload[0] == 0x68 and payload[6] == 45 and payload[8] & 0x3F == 6:
        ioa_w = payload[12] | payload[13] << 8 | payload[14] << 16
        cmd = (f"{ioa_w:x}", "ON" if payload[15] & 1 else "OFF", datetime.fromtimestamp(sec, timezone.utc).strftime("%H:%M"))
assert cmd and int(cmd[0], 16) == int(ioa, 16), (cmd, ioa)
print("breaker command:", cmd, file=sys.stderr)

report = {"ioa_address": cmd[0], "command_qualifier": cmd[1], "command_time_utc": cmd[2],
          "telemetry_status": frozen, "vpn_session_id": None}
if "--submit" in sys.argv:
    print(post("/confirm-target", {"employee_id": emp}), file=sys.stderr)
    vpn = json.loads(get("/query/vpn-window"))["vpn_sessions"]
    report["vpn_session_id"] = next(s["session_id"] for s in vpn if s["employee_id"] == emp)
    print(post("/submit", report))
else:
    print(json.dumps(report | {"vpn_session_id": "<from /query/vpn-window after confirm-target>", "employee_id": emp}, indent=1))
