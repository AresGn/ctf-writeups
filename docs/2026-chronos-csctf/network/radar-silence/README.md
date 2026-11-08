---
tags: [network, pcap, dns, exfiltration, base32]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Radar Silence

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| network | 158 | ✅ | — | no | 0xAr3s-root | Chronos Security |

## Challenge description

> RDR37 (192.0.2.37) carries the air-surveillance radar link of an Operation Dawn ally whose picture feeds the coalition's shared air surveillance; OPS40 (192.0.2.40) logs operations. Before a scheduled cutover, analysts marked RDR37 for a suspected bearer-token leak.
>
> This PCAPNG is an isolated-lab replay, not a production capture. Determine whether a bearer token left RDR37 and recover it for reissue.
>
> Submit `CSCTF{<source>_rotation_<token>}` using the lower-case station ID and a 32-character lower-case hex token.

**Artifact files:** `files/radar-silence.pcapng` (not committed)

## TL;DR

The capture is 28 DNS packets only. RDR37 leaks the token through DNS tunnelling: four queries to `<chunk>.<NN>.update.svc-telemetry.example`, each carrying a base32 fragment with its sequence index. Reordering by `NN` and base32-decoding gives the 32-hex token (`CSCTF{rdr37_rotation_...}` redacted).

## Approach

**1. Recon**

```bash
tshark -r radar-silence.pcapng -q -z io,phs   # eth > ip > udp > dns, 28 frames
tshark -r radar-silence.pcapng -T fields -e ip.src -e dns.qry.name
```

Most names are benign noise (`wpad`, `ocsp`, `time`, `_dmarc`, ...). Only RDR37 queries four odd names, all under `update.svc-telemetry.example`, with a 13-character label and a 2-digit index:

```
miytaojxmy3gk.00.update.svc-telemetry.example
ojxg4ydcnldmf.01.update.svc-telemetry.example
rtamrzg5sgiyz.02.update.svc-telemetry.example
tgmztknjqhfta.03.update.svc-telemetry.example
```

Note they are **out of order in the capture** (02, 00, 03, 01): the index must be used. OPS40 only does ordinary lookups (decoys).

**2. Decode**

The labels use the alphabet `a-z2-7` → base32. Concatenate by index 00→03 (52 chars), pad, decode → 32 ASCII hex chars, matching the required token format.

**3. Flag**

`CSCTF{rdr37_rotation_<token>}` — see `solve/solve.py` (flag redacted).

## Key takeaways

- DNS tunnelling signs: many unique subdomains under one odd parent domain, base32 labels, sequence index.
- Packet order ≠ data order; always sort by the embedded index.
- Filter by source host: decoy queries from the other station are irrelevant.
