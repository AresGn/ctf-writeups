#!/usr/bin/env python3
"""Radar Silence - rebuild the bearer token exfiltrated over DNS from RDR37.
Usage: python3 -I solve.py ../files/radar-silence.pcapng
"""
import base64, re, subprocess, sys

pcap = sys.argv[1]
out = subprocess.check_output(
    ["tshark", "-r", pcap, "-Y", "ip.src==192.0.2.37 && dns.flags.response==0",
     "-T", "fields", "-e", "dns.qry.name"], text=True)

chunks = {}
for name in out.split():
    m = re.fullmatch(r"([a-z2-7]+)\.(\d{2})\.update\.svc-telemetry\.example", name)
    if m:
        chunks[int(m.group(2))] = m.group(1)

b32 = "".join(chunks[i] for i in sorted(chunks)).upper()
b32 += "=" * (-len(b32) % 8)
token = base64.b32decode(b32).decode()
assert re.fullmatch(r"[0-9a-f]{32}", token)
print(f"CSCTF{{rdr37_rotation_{token}}}")
