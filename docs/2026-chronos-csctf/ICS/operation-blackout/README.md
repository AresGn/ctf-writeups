---
tags: [ics, modbus, scada, cross-validation]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Operation Blackout

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| ICS | 663 | 138 | ✅| — | 0xAr3s-root | Dragoş Bacitea |

## Challenge description

> A regional energy grid lost power at substation 0x4A2E. The recovered SCADA capture, HMI configuration, PLC firmware, event log, and alarm overrides describe the same incident from different operational layers.
>
> Reconstruct the incident only where the evidence agrees and submit the resulting marker. This is a constructed offline ICS-forensics case; do not interact with external systems.
>
> Attachments: `scada_network.pcap`, `hmi_config.xml`, `plc_firmware.bin`, `substation_log.json`, `alarm_override.dat`.
>
> Flag format: `CSCTF{8_lowercase_hex}`
>
> Flag construction: SHA-256 the literal text `0x<FIRMWARE_FIRST_4_BYTES_UPPER_HEX>:0x<STATION_ID>:<FIRST_CRITICAL_TIMESTAMP>:<REGISTER_DECIMAL>:<MANIFEST_SEED_DECIMAL>`, then use the first 8 lowercase hex characters. Use literal `:` separators and no binary packing. `scada_blackout_2026` is a decoy, not an input.
>
> Flag derivation (serialization spec): `sha256("<firmware_header_hex>:<station_hex>:<log_timestamp_iso>:<register_decimal>:<seed_decimal>")[:8]`. `firmware_header_hex` = first 4 bytes of `plc_firmware.bin` as hex with `0x` prefix uppercase (e.g. `0x504C4331`), not the version string, not ascii. `station_hex` = station identifier with `0x` prefix uppercase (e.g. `0x4A2E`). `log_timestamp_iso` = exact ISO 8601 timestamp from the log entry for the malicious FC16 write, with `T` and trailing `Z`. `register_decimal` = start register as decimal (e.g. `40001`). `seed_decimal` = the calibration seed as decimal (e.g. `137`). Fields joined as strings with `:`. No binary packing. No other fields.

**Artifact files:** the five files above (not committed).

## TL;DR

Five files describe the same incident; the flag is a SHA-256 of five fields, each of which can be cross-checked between at least two sources (station `0x4A2E`, start register 40001, timestamp `2025-11-15T06:15:03Z`, seed 137, firmware header `0x504C4331`) → first 8 hex characters.

## Approach

**1. Recon — five files, five layers, a precise serialization spec**

- `hmi_config.xml`: station `0x4A2E`, a calibration routine with `ManifestSeed` 137, three setpoint registers, and a `HiddenModbusWrite` FC 16 at `start_address="40001"`, `count="64"` with payload `55 FA …` (8 registers' worth).
- `substation_log.json`: normal startup with `manifest_seed: 137`, then at `06:15:03Z` a WARNING "Unexpected Modbus FC 0x10 write to read-only registers 40001-40064" and, the same second, the first CRITICAL ("Buffer overflow … 247 bytes vs 128-byte limit"), then altered alarm thresholds, outbound traffic, firmware integrity failure, the outage at `0x4A2E`.
- `scada_network.pcap`: 30 FC 3 reads of `9c41`/10 registers, then one **FC 16** write (transaction 2) with start `0x9c41`, quantity `0x0040`, byte count 16, followed by five HTTP POST packets to `198.51.100.42`.
- `alarm_override.dat`: magic `ALRM`, then station as little-endian `2e 4a`, and three alarm records at registers `0x9CA4`–`0x9CA6` (40100–40102).
- `plc_firmware.bin`: 1,024 bytes starting `50 4C 43 31` (`PLC1`) then `V3.2.1`.

The statement's spec fixes the serialization of each field, so the job is to decide the *value* of each and to discard what the evidence does not support.

**2. Hypothesis — keep a field only when independent sources agree**

| Field | Sources that agree | Value |
|---|---|---|
| station | XML `<station_id>`, log text "substation 0x4A2E", `alarm_override.dat` bytes `2e4a` (LE) | `0x4A2E` |
| start register | pcap FC 16 start `0x9C41`, XML `start_address`, log "40001-40064" | `40001` |
| timestamp | the log entry for the FC 16 write (WARNING) and the first CRITICAL entry are the same second | `2025-11-15T06:15:03Z` |
| seed | XML `<ManifestSeed>`, log `manifest_seed` | `137` |
| firmware header | first 4 bytes of the binary | `0x504C4331` (`PLC1`) |

What the evidence does **not** support (and the flag does not use): the log says the exfiltration goes to port 443 while the pcap shows port 80; the log's "247 bytes" matches no packet (the real byte count is 16); the XML announces 64 registers but the payload covers 8; `alarm_override.dat` targets registers 40100–40102, not 40001–40064; the decoy string `scada_blackout_2026` (XOR `0x37` of the bytes after the firmware header) is declared a non-input; and the pcap timestamps (07:05:03 UTC+1 = 06:05:03Z) are ten minutes earlier than the log's 06:15:03Z — the statement explicitly asks for the *log* entry's timestamp.

Two ambiguities in the wording turn out harmless: "first critical timestamp" and "log entry of the malicious FC16 write" are both `06:15:03Z` (the WARNING and the first CRITICAL share the second), and "firmware first 4 bytes" is the raw header `50 4C 43 31`, not the version string.

**3. Exploitation — serialize and hash**

```text
0x504C4331:0x4A2E:2025-11-15T06:15:03Z:40001:137
```

```bash
python3 -I solve/solve.py files
```

The script re-checks every agreement with assertions (station in three places, register from the raw Modbus frame, FC 16 entry = first CRITICAL, seed in two places) before hashing, and prints the first 8 hex characters of the SHA-256.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)


## Reflections

- With a "reconstruct only where the evidence agrees" brief, a table of field × sources makes the decision explicit and shows which contradictions are decoys.
- Earlier guesses (`55fa55fa`, `4a2e9c41`, `9c410040`, noted in `notes.md`) were refused: they were raw pattern/concatenation guesses made before the serialization spec was seen. The spec removes the guessing: read the full statement, including the flag-construction paragraphs, before deriving anything.
- Read the raw protocol bytes yourself: the FC 16 start address in the pcap is `0x9C41` = 40001, the same number as in the XML and log.
- Pick the timestamp from the source the statement names (the log), not from the capture, even when another source has a different clock.

## Tools & references

- `tshark`, `xxd`, Python 3 (`struct`, `json`, `hashlib`)
- Modbus/TCP function code 16 (Write Multiple Registers), holding-register addressing (0x9C41 ↔ 40001)

---
[⬅ Back to event](../../README.md)
