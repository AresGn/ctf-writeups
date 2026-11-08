# Notes — CSCTF 2026

Live notes (EN or FR, not published): commands tried, leads, dead ends.
Notes en direct (EN ou FR, non publiées) : commandes essayées, pistes, impasses.

Format: `HH:MM [challenge] note`

## [ICS] Operation Blackout (Hard, 0 solves, author CSA Romania)

Fichiers fournis dans `docs/2026-chronos-csctf/ICS/`: scada_network.pcap, hmi_config.xml,
plc_firmware.bin, substation_log.json, alarm_override.dat. Flag format `CSCTF{8_lowercase_hex}`.
Pas de hint disponible sur la plateforme (vérifié, section INTELLIGENCE absente pour ce challenge).

Faits confirmés par recoupement (3 sources indépendantes et identiques) :
- Station `0x4A2E` : hmi_config.xml (`<station_id>`), substation_log.json (texte), alarm_override.dat (octets LE `2e4a`).
- Adresse registre de départ `0x9C41` (40001) : hmi_config.xml (`address`/`start_address`), log ("40001-40064"), pcap (champ Modbus réel `9c41`).
- Count `0x0040` (64) : hmi_config.xml (`count="64"`), log ("-40064"), pcap (champ quantity `0040`).

Faits plus faibles / contradictoires (écartés) :
- Payload `55 fa`×8 répété dans hmi_config.xml ET pcap (identique byte à byte) mais ne couvre que
  16 octets (8 registres) alors que count=64 est annoncé → incohérence interne, pas utilisé seul.
- Port externe suspect : log dit `:443`, pcap montre `:80` vers 198.51.100.42 → contradiction, écarté.
- "247 bytes" (log, buffer overflow) ne correspond à aucune valeur du pcap (byte_count réel = 16) → écarté.
- `alarm_override.dat` IDs de registre (`0x9CA4/A5/A6` = 40100-40102) ≠ plage ciblée par l'écriture
  (40001-40064) → le payload réseau ne touche jamais réellement les registres d'alarme réels.
- `manifest_seed=137` présent identique dans log ET xml, mais dans un contexte de démarrage normal
  (pas lié à l'incident) → probablement un leurre.
- plc_firmware.bin : XOR single-byte clé `0x37` sur les 20 octets après le header révèle la chaîne
  claire `scada_blackout_2026` (confirme la compromission firmware) ; le reste du fichier (~987
  octets) ne se décode pas avec cette clé → probablement bourrage aléatoire, pas de signal exploité.
- Recherche exhaustive (grep) de tout token hex 8 caractères en clair dans les 5 fichiers : aucun
  résultat exploitable → le flag n'est pas un littéral caché, c'est une combinaison/dérivation des
  faits ci-dessus que je n'ai pas encore identifiée avec certitude.

Tentatives de flag soumises et REFUSÉES par la plateforme :
1. `CSCTF{55fa55fa}` — motif du payload répété sur le fil (4 octets lus directement, x2).
2. `CSCTF{4a2e9c41}` — station + adresse registre concaténés.
3. `CSCTF{9c410040}` — adresse registre + count concaténés.

État : en pause. Reprendre avec plus de contexte (Discord équipe/CTF) avant de retenter une
combinaison au hasard — éviter de brûler plus de tentatives sans nouvelle preuve.

