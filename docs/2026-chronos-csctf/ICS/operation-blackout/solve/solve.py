#!/usr/bin/env python3
"""operation-blackout: assemble the marker only from fields on which the evidence agrees.

Usage: python3 -I solve.py ../files
flag = sha256("<fw_hdr>:<station>:<log ts>:<register>:<seed>")[:8], serialization from the statement.
"""
import hashlib, json, re, struct, sys
from pathlib import Path

d = Path(sys.argv[1])
xml = (d / "hmi_config.xml").read_text()
log = json.loads((d / "substation_log.json").read_text())

# --- station: XML <station_id>, log text, and alarm_override.dat (little-endian u16 at offset 6)
st_xml = int(re.search(r"<station_id>(0x[0-9A-Fa-f]+)</station_id>", xml).group(1), 16)
st_dat = struct.unpack("<H", (d / "alarm_override.dat").read_bytes()[6:8])[0]
st_log = int(re.search(r"substation (0x[0-9A-Fa-f]+)", json.dumps(log)).group(1), 16)
assert st_xml == st_dat == st_log, (st_xml, st_dat, st_log)

# --- register + count: the real FC16 on the wire (pcap, TCP 502), XML and log agree
pcap = (d / "scada_network.pcap").read_bytes()
off, wire = 24, None
while off + 16 <= len(pcap):
    incl = struct.unpack("<I", pcap[off + 8:off + 12])[0]
    pkt = pcap[off + 16:off + 16 + incl]
    off += 16 + incl
    tcp = pkt[14 + (pkt[14] & 15) * 4:]
    pay = tcp[(tcp[12] >> 4) * 4:]
    if struct.unpack(">H", tcp[2:4])[0] == 502 and len(pay) > 8 and pay[7] == 0x10:      # Modbus FC 16
        wire = struct.unpack(">HH", pay[8:12])                                           # start, quantity
reg = wire[0] - 0x9C41 + 40001                                                           # 0x9C41 == 40001
assert reg == int(re.search(r'start_address="(\d+)"', xml).group(1)) == 40001
assert "40001-40064" in json.dumps(log) and wire[1] == 64

# --- timestamp: log entry of the malicious FC16 write (also the first CRITICAL entry)
fc16 = next(e for e in log if "FC 0x10" in e["message"])["timestamp"]
first_crit = next(e for e in log if e["level"] == "CRITICAL")["timestamp"]
assert fc16 == first_crit, (fc16, first_crit)

# --- seed: XML and log agree
seed_xml = int(re.search(r"<ManifestSeed>(\d+)</ManifestSeed>", xml).group(1))
seed_log = next(e["manifest_seed"] for e in log if "manifest_seed" in e)
assert seed_xml == seed_log

# --- firmware: first 4 bytes as hex (NOT the "V3.2.1" string, not ascii)
fw = (d / "plc_firmware.bin").read_bytes()[:4].hex().upper()

text = f"0x{fw}:0x{st_xml:04X}:{fc16}:{reg}:{seed_xml}"
print("input :", text, file=sys.stderr)
print("CSCTF{" + hashlib.sha256(text.encode()).hexdigest()[:8] + "}")
