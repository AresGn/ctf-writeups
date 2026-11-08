---
tags: [network, mavlink, cryptography]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Grid Watch

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| network | 672 | 75 | ✅ | — | 0xAr3s-root | Marius Merai |

## Énoncé

> Vultur Dynamics drones patrol the RGN-Grid high-voltage network. An adversary wants one diverted off its corridor. You have a packet capture of a drone's MAVLink 2 command link and live access to the drone itself. Make the drone accept your own reposition command. Unsigned and replayed commands are refused — the flag returns only from a command the drone actually accepts.
>
> Interact only with your assigned instance.
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** `files/capture.tlog`, `files/provisioning_note.md` (non commités). Instance live : TCP `w02.ctf.chronos-security.ro:32773` (expirée).

## En bref

Le drone n'accepte que des commandes signées MAVLink 2, avec une horloge custom : calibrer la RTC depuis la capture (+17 ppm, époque de commissioning 1733965123) permet de dériver la clé de provisioning par HKDF depuis le nonce par connexion, de re-provisionner ma propre clé de signature avec `SETUP_SIGNING`, puis — signés avec cette clé — passer GUIDED, armer et envoyer `DO_REPOSITION`, qui renvoie le flag.

## Démarche

**1. Reconnaissance — un lien signé, un problème de calibration et une backdoor à clé dérivée**

`capture.tlog` contient 24 paquets MAVLink 2 signés (GCS 255/190 ↔ drone 1/1, link_id 249) : heartbeats, `STATUSTEXT` annonçant le serial `CX-FALCON-9951`, un `COMMAND_LONG 511`, des rapports `GLOBAL_POSITION_INT`. Chaque paquet porte une signature de 13 octets (link_id, timestamp 48 bits en ticks de 10 µs, SHA256-48), donc rejouer la capture est inutile : les timestamps sont vérifiés et la clé de session n'est pas dans la capture.

`provisioning_note.md` est la voie d'entrée : les clés peuvent être re-provisionnées avec `SETUP_SIGNING`, authentifié par `prov_key = HKDF-SHA256(ikm = serial_ascii || commissioning_epoch_le64, salt = session_nonce, info = "CX-PROV/v1", L = 32)`. Le serial est connu ; le nonce est annoncé à la connexion (`PROV NONCE …`) ; ce qui manque est l'époque de commissioning — et tout timestamp que je signe doit correspondre à la RTC particulière du drone (ticks depuis l'époque de commissioning, *pas* l'époque MAVLink 2015, avec un offset et une dérive ppm par unité à calibrer).

**2. Hypothèse — les deux horloges de la capture donnent l'époque et la dérive**

Chaque enregistrement tlog a un timestamp hôte (µs), et chaque paquet un timestamp de signature. En les appariant : les timestamps de signature croissent de 3 100 052–3 100 053 ticks par 31,000000 s de temps hôte, une pente constante de **100001,7 ticks/s = +17 ppm**. Avec cette pente, `signing_ticks = round((unix_time − E)·100001,7)` fitte les 24 paquets à un demi-tick près pour **E = 1733965123** (2024-12-12 00:58:43 UTC) et un offset supplémentaire nul. J'ai validé le modèle en live avant de l'utiliser : les timestamps de signature prédits encadraient ceux des propres signatures du drone à la connexion (avant/après l'aller-retour). Cela fixe à la fois l'entrée époque de HKDF et l'horloge de chaque paquet que je forge.

Les messages d'erreur du drone ont ensuite cartographié le reste du protocole : un `SETUP_SIGNING` non signé → `REJECT: unsigned message` ; un message `SET_MODE` → `REJECT: not a command for this drone` (il ne prend que des `COMMAND_LONG`) ; armer avant GUIDED → `REJECT: must be in GUIDED before arming` ; la commande 512 → `REJECT: unexpected command 512`, tandis que **192 est son `DO_REPOSITION`** (`REJECT: DO_REPOSITION requires GUIDED + ARMED`). Donc l'ordre de vol de la note — GUIDED, armement, commande — est appliqué littéralement.

**3. Exploitation — re-provisionner, puis voler l'ordre normal, le tout sur une seule connexion**

Le nonce est par connexion, donc tout se passe sur une seule connexion TCP, chaque paquet signé avec `SHA256-48(key ‖ packet ‖ link_id ‖ timestamp)` et un timestamp RTC frais et strictement croissant :

1. Lire `PROV NONCE`, calculer `prov_key` par HKDF (salt = le nonce en octets bruts depuis l'hex).
2. `SETUP_SIGNING` (msg 256) : une nouvelle clé de session de mon choix (le script utilise `SHA256("gridwatch-session-key-v1")`, n'importe quels 32 octets fonctionnent), `initial_timestamp` = son propre timestamp de signature, paquet signé avec `prov_key` → `signing re-provisioned: new key active`.
3. Signés avec la nouvelle clé : `COMMAND_LONG 176` (`DO_SET_MODE`, param1=1, param2=4) → `mode GUIDED` ; `COMMAND_LONG 400` (armement, param1=1) → `ARMED` ; `COMMAND_LONG 192` (`DO_REPOSITION`, param5/6/7 = 45,6 / 24,1 / 100) → `COMMAND_ACK` plus un `STATUSTEXT` portant le flag.

```bash
pip install pymavlink
python3 solve/solve.py w02.ctf.chronos-security.ro 32773
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Ce que j'ai appris

- La capture n'est pas là pour être rejouée mais pour être *mesurée* : deux timestamps par paquet suffisent à retrouver exactement l'époque et la dérive ppm de la RTC (résidus sous le demi-tick sur 24 paquets).
- J'ai vérifié le modèle d'horloge contre le drone live avant d'envoyer quoi que ce soit de forgé — une mauvaise époque casse aussi l'entrée de HKDF, donc ce seul fit débloque à la fois la clé et les timestamps.
- Les messages de rejet du serveur sont une spécification : chaque sonde refusée (`SET_MODE`, 512, armement trop tôt) a levé une inconnue, laissant 176 → 400 → 192 comme seul ordre accepté.
- Tout doit partager une seule connexion car le salt de HKDF (le nonce) est annoncé par connexion.

## Outils et références

- Python 3 + pymavlink (dialecte common, packing des messages / CRC extras), `hashlib`/`hmac` pour HKDF-SHA256 et les signatures SHA256-48
- Signature de paquets MAVLink 2 et `SETUP_SIGNING` (message 256), commandes `COMMAND_LONG` 176 / 400 / 192

---
[⬅ Retour à l'événement](../../README.fr.md)
