#!/usr/bin/env python3
"""ghost-signal: cross-validate the SS7/Diameter/billing evidence and derive the marker.

Usage: python3 -I solve.py ../files
Requires tshark on PATH to read the two pcaps (SS7/MAP over M3UA, Diameter); the
billing export is read directly as JSON. Nothing beyond these three files is used.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

d = Path(sys.argv[1])


def tshark_fields(pcap, *fields):
    """List of dicts, one per frame that has at least one of the requested fields set."""
    args = ["tshark", "-r", str(pcap), "-T", "fields", "-E", "separator=\t"]
    for f in fields:
        args += ["-e", f]
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout
    rows = []
    for line in out.splitlines():
        cells = line.split("\t")
        row = dict(zip(fields, cells + [""] * (len(fields) - len(cells))))
        if any(row.values()):
            rows.append(row)
    return rows


# 1. Billing export: find the anomalous events -- every one carries an "anomaly" field.
billing = json.loads((d / "billing_events.json").read_text())
anomalous = [e for e in billing["events"] if "anomaly" in e]
sessions = {e["session_id"] for e in anomalous}
imsis = {e["imsi"] for e in anomalous}
assert len(sessions) == 1 and len(imsis) == 1, "more than one anomalous thread -- narrow it down first"
session_id, imsi = sessions.pop(), imsis.pop()
first_ts = min(e["timestamp"] for e in anomalous)
print(f"billing: session={session_id} imsi={imsi} first_anomalous_ts={first_ts}", file=sys.stderr)

# 2. SS7 (MAP over M3UA/SCCP): the same IMSI shows up in an updateLocation from a GT that
#    only appears once the attack window starts (49211, then 49311) -- never in the baseline
#    traffic (which stays in the 49100-49144 range).
ss7 = tshark_fields(d / "ss7_capture.pcap", "frame.time_epoch", "sccp.calling.digits", "e212.imsi")
ss7_imsi_rows = [r for r in ss7 if r["e212.imsi"]]
assert all(r["e212.imsi"] == imsi for r in ss7_imsi_rows) and ss7_imsi_rows, "SS7 IMSI mismatch"
attack_gts = {r["sccp.calling.digits"] for r in ss7 if int(float(r["frame.time_epoch"])) >= first_ts}
print(f"SS7: IMSI confirmed in updateLocation; attack-window calling GTs = {sorted(attack_gts)}", file=sys.stderr)

# 3. Diameter: the exact Session-Id AVP on the wire, and the rogue Origin-Host it was served from.
dia = tshark_fields(d / "diameter_capture.pcap", "diameter.Session-Id", "diameter.Origin-Host",
                     "diameter.Subscription-Id-Data")
match = [r for r in dia if r["diameter.Session-Id"] == session_id]
assert match and all(r["diameter.Subscription-Id-Data"] == imsi for r in match if r["diameter.Subscription-Id-Data"])
rogue_hosts = {r["diameter.Origin-Host"] for r in match} - {"hss.eastern-tele.ro"}
print(f"Diameter: Session-Id confirmed on the wire; rogue Origin-Host(s) = {sorted(rogue_hosts)}", file=sys.stderr)

# 4. Flag: sha256("<imsi>:<full_diameter_session_id>:<unix_timestamp>")[:8]
text = f"{imsi}:{session_id}:{first_ts}"
digest = hashlib.sha256(text.encode()).hexdigest()
print(f"serialized: {text}", file=sys.stderr)
print("CSCTF{" + digest[:8] + "}")
