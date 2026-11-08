---
tags: [ics, modbus, scada, cross-validation]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Operation Blackout

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| ICS | 138 | ✅ | — | non | 0xAr3s-root | Dragoş Bacitea |

## Énoncé

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

**Fichiers fournis :** les cinq fichiers ci-dessus (non commités).

## En bref

Cinq fichiers décrivent le même incident ; le flag est un SHA-256 de cinq champs, chacun recoupable entre au moins deux sources (station `0x4A2E`, registre de départ 40001, horodatage `2025-11-15T06:15:03Z`, seed 137, en-tête firmware `0x504C4331`) → 8 premiers caractères hexa.

## Démarche

**1. Reconnaissance — cinq fichiers, cinq couches, une spécification de sérialisation précise**

- `hmi_config.xml` : station `0x4A2E`, une routine de calibration avec `ManifestSeed` 137, trois registres de consigne, et un `HiddenModbusWrite` FC 16 à `start_address="40001"`, `count="64"` avec la charge `55 FA …` (8 registres).
- `substation_log.json` : démarrage normal avec `manifest_seed: 137`, puis à `06:15:03Z` un WARNING « Unexpected Modbus FC 0x10 write to read-only registers 40001-40064 » et, la même seconde, le premier CRITICAL (« Buffer overflow … 247 bytes vs 128-byte limit »), puis seuils d'alarme modifiés, trafic sortant, échec d'intégrité du firmware, la coupure à `0x4A2E`.
- `scada_network.pcap` : 30 lectures FC 3 de `9c41`/10 registres, puis une écriture **FC 16** (transaction 2) avec départ `0x9c41`, quantité `0x0040`, byte count 16, suivie de cinq paquets HTTP POST vers `198.51.100.42`.
- `alarm_override.dat` : magic `ALRM`, puis la station en little-endian `2e 4a`, et trois enregistrements d'alarme aux registres `0x9CA4`–`0x9CA6` (40100–40102).
- `plc_firmware.bin` : 1 024 octets commençant par `50 4C 43 31` (`PLC1`) puis `V3.2.1`.

La spécification de l'énoncé fixe la sérialisation de chaque champ ; le travail consiste donc à décider la *valeur* de chacun et à écarter ce que les preuves ne soutiennent pas.

**2. Hypothèse — ne garder un champ que si des sources indépendantes concordent**

| Champ | Sources concordantes | Valeur |
|---|---|---|
| station | XML `<station_id>`, texte du log « substation 0x4A2E », octets `2e4a` (LE) de `alarm_override.dat` | `0x4A2E` |
| registre de départ | départ FC 16 du pcap `0x9C41`, XML `start_address`, log « 40001-40064 » | `40001` |
| horodatage | l'entrée du log de l'écriture FC 16 (WARNING) et la première entrée CRITICAL sont à la même seconde | `2025-11-15T06:15:03Z` |
| seed | XML `<ManifestSeed>`, log `manifest_seed` | `137` |
| en-tête firmware | 4 premiers octets du binaire | `0x504C4331` (`PLC1`) |

Ce que les preuves ne soutiennent **pas** (et que le flag n'utilise pas) : le log dit que l'exfiltration va vers le port 443 alors que le pcap montre le port 80 ; les « 247 bytes » du log ne correspondent à aucun paquet (le vrai byte count est 16) ; le XML annonce 64 registres mais la charge en couvre 8 ; `alarm_override.dat` vise les registres 40100–40102, pas 40001–40064 ; la chaîne leurre `scada_blackout_2026` (XOR `0x37` des octets après l'en-tête firmware) est déclarée non-entrée ; et les horodatages du pcap (07:05:03 UTC+1 = 06:05:03Z) sont dix minutes avant le 06:15:03Z du log — l'énoncé demande explicitement l'horodatage de l'entrée du *log*.

Deux ambiguïtés de formulation sont sans conséquence : « first critical timestamp » et « entrée du log de l'écriture FC16 malveillante » valent tous deux `06:15:03Z` (le WARNING et le premier CRITICAL partagent la seconde), et « firmware first 4 bytes » est l'en-tête brut `50 4C 43 31`, pas la chaîne de version.

**3. Exploitation — sérialiser et hacher**

```text
0x504C4331:0x4A2E:2025-11-15T06:15:03Z:40001:137
```

```bash
python3 -I solve/solve.py files
```

Le script revérifie chaque concordance par des assertions (station à trois endroits, registre depuis la trame Modbus brute, entrée FC 16 = premier CRITICAL, seed à deux endroits) avant de hacher, et affiche les 8 premiers caractères hexa du SHA-256.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)


## Réflexions

- Avec une consigne « reconstruire seulement là où les preuves concordent », un tableau champ × sources rend la décision explicite et montre quelles contradictions sont des leurres.
- Les tentatives précédentes (`55fa55fa`, `4a2e9c41`, `9c410040`, notées dans `notes.md`) ont été refusées : c'étaient des devinettes de motif/concaténation faites avant d'avoir vu la spécification de sérialisation. La spécification supprime la devinette : lire tout l'énoncé, y compris les paragraphes de construction du flag, avant de dériver quoi que ce soit.
- Lire soi-même les octets bruts du protocole : l'adresse de départ de la FC 16 dans le pcap est `0x9C41` = 40001, le même nombre que dans le XML et le log.
- Prendre l'horodatage de la source que l'énoncé nomme (le log), pas de la capture, même quand une autre source a une horloge différente.

## Outils & références

- `tshark`, `xxd`, Python 3 (`struct`, `json`, `hashlib`)
- Modbus/TCP code fonction 16 (Write Multiple Registers), adressage des registres holding (0x9C41 ↔ 40001)

---
[⬅ Retour à l'événement](../../README.fr.md)
