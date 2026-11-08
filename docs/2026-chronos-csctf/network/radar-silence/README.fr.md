---
tags: [network, pcap, dns, exfiltration, base32]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Radar Silence

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| network | 158 | ✅ | — | non | 0xAr3s-root | Chronos Security |

## Énoncé

> RDR37 (192.0.2.37) carries the air-surveillance radar link of an Operation Dawn ally whose picture feeds the coalition's shared air surveillance; OPS40 (192.0.2.40) logs operations. Before a scheduled cutover, analysts marked RDR37 for a suspected bearer-token leak.
>
> This PCAPNG is an isolated-lab replay, not a production capture. Determine whether a bearer token left RDR37 and recover it for reissue.
>
> Submit `CSCTF{<source>_rotation_<token>}` using the lower-case station ID and a 32-character lower-case hex token.

**Fichiers du challenge :** `files/radar-silence.pcapng` (non commité)

## TL;DR

La capture ne contient que 28 paquets DNS. RDR37 fait fuiter le token par tunnel DNS : quatre requêtes vers `<morceau>.<NN>.update.svc-telemetry.example`, chacune portant un fragment base32 et son index. En triant par `NN` puis en décodant le base32, on obtient le token de 32 caractères hexadécimaux (`CSCTF{rdr37_rotation_...}` masqué).

## Approche

**1. Reconnaissance**

```bash
tshark -r radar-silence.pcapng -q -z io,phs   # eth > ip > udp > dns, 28 trames
tshark -r radar-silence.pcapng -T fields -e ip.src -e dns.qry.name
```

La plupart des noms sont du bruit bénin (`wpad`, `ocsp`, `time`, `_dmarc`, ...). Seul RDR37 interroge quatre noms étranges sous `update.svc-telemetry.example`, avec un label de 13 caractères et un index à 2 chiffres :

```
miytaojxmy3gk.00.update.svc-telemetry.example
ojxg4ydcnldmf.01.update.svc-telemetry.example
rtamrzg5sgiyz.02.update.svc-telemetry.example
tgmztknjqhfta.03.update.svc-telemetry.example
```

Ils sont **dans le désordre dans la capture** (02, 00, 03, 01) : il faut utiliser l'index. OPS40 ne fait que des requêtes ordinaires (leurres).

**2. Décodage**

Les labels utilisent l'alphabet `a-z2-7` → base32. On concatène par index 00→03 (52 caractères), on complète le padding, on décode → 32 caractères hex ASCII, conformes au format du token attendu.

**3. Flag**

`CSCTF{rdr37_rotation_<token>}` — voir `solve/solve.py` (flag masqué).

## À retenir

- Signes d'un tunnel DNS : nombreux sous-domaines uniques sous un domaine parent inhabituel, labels base32, index de séquence.
- L'ordre des paquets ≠ l'ordre des données ; toujours trier par l'index embarqué.
- Filtrer par hôte source : les requêtes leurres de l'autre station sont sans intérêt.
