---
tags: [network, mavlink, cryptography, key-reuse]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Severed Link

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| network | 84 | ✅ | — | non | 0xAr3s-root | Teodor Giurgica |

## Énoncé

> A reconnaissance drone on an ISR mission for an allied force in the Operation Dawn theatre takes orders from its field station over a signed MAVLink 2 link. Mid-mission the operator rotated the signing key, then pushed the new key over that same link while it was being recorded.
>
> Attached: the recording and the operator's notes. The uplink gateway is still online as it was during the incident. Show that an outsider can take the operator's place and command the aircraft.
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** `files/mission.tlog`, `files/mission.pcap` (le même trafic en UDP/14550), `files/ops_notes.txt` (non commités). **Cible :** une instance live limitée dans le temps (`w01.ctf.chronos-security.ro:<port>`, 30 min, un simple relais TCP MAVLink 2).

## En bref

L'opérateur a fait tourner la clé de signature du lien MAVLink 2 avec un message `SETUP_SIGNING` envoyé *sur ce même lien signé, en cours d'enregistrement* ; la nouvelle clé de 32 octets est en clair dans la charge utile de ce message. La rejouer est refusé (anti-rejeu), mais re-signer un `HEARTBEAT` et un `COMMAND_INT` `DO_REPOSITION` frais avec cette clé et l'horloge du relais permet de s'authentifier comme l'opérateur et renvoie le flag.

## Démarche

**1. Reconnaissance — un lien signé et une clé transmise sur elle-même**

`ops_notes.txt` donne le cadre : l'opérateur est sysid 255, le drone sysid 1, chaque trame est signée en MAVLink 2. En cours de mission, la clé de signature a été changée, mais *dans la bande*, sur le lien console lui-même, au lieu d'un canal hors bande — « c'était une erreur : la nouvelle clé est passée sur un lien en cours de capture ». `mission.tlog` (et l'équivalent `mission.pcap`, MAVLink sur UDP/14550) est exactement cette capture.

Un `.tlog` est une suite d'enregistrements `(8 octets big-endian de microsecondes horloge murale, trame MAVLink 2 brute)`. Parser les 107 trames donne surtout des `HEARTBEAT`/`ATTITUDE`/`GLOBAL_POSITION_INT`, plus un `SETUP_SIGNING` (id de message 256) de l'opérateur (sysid 255) vers le drone et un `COMMAND_INT` `DO_REPOSITION` (id 75, `MAV_CMD_DO_REPOSITION` = 192) — un ordre de repositionnement réel, déjà accepté.

**2. Hypothèse — le message de rotation porte la nouvelle clé en clair**

La charge utile de `SETUP_SIGNING` (42 octets : MAVLink réordonne les champs du plus grand au plus petit) est `initial_timestamp(8) · target_system(1) · target_component(1) · secret_key(32)`. La décoder donne `target_system/component = 1/1` (le drone) et une `secret_key` de 32 octets. J'ai vérifié que c'est bien la clé active en recalculant la signature (`SHA-256(clé ‖ en-tête+charge+CRC ‖ link_id ‖ timestamp)[:6]`) des 47 trames signées qui suivent la rotation dans la capture : les 47 correspondent. La clé elle-même n'est jamais transmise ailleurs, ce qui confirme l'affirmation des notes selon laquelle elle « est passée sur un lien en cours de capture » — la capture est une fuite complète et autosuffisante.

Se connecter au relais live confirme le scénario de bout en bout :

```
SB-7 uplink gateway online. Authenticate as operator: signed COMMAND_INT
DO_REPOSITION from sysid 255 under the fleet link key. Replayed frames are
refused, the signing timestamp must be current.
```

Un `HEARTBEAT` non signé reçoit `DENIED: frame is not authenticated under the link key.` — même la poignée de main doit donc être signée avec la clé récupérée.

**3. Exploitation — re-signer, pas rejouer**

Rejouer tel quel le `DO_REPOSITION` capturé serait refusé (son timestamp de signature est périmé et le relais vérifie le rejeu). Le champ timestamp de signature est l'horloge MAVLink 2 standard — des ticks de 10 µs depuis le 2015-01-01T00:00:00Z — confirmé par une première sonde : envoyer une signature fraîche mais avec un timestamp arbitraire a donné `DENIED: stale signing timestamp outside the freshness window. Link time is 37399709984355.`, qui se décode exactement à l'heure murale de cette tentative. Chaque trame doit donc être signée avec `round((maintenant_utc − 2015-01-01T00:00:00Z) / 10 µs)` calculé au moment de l'envoi.

Le relais refuse aussi une commande isolée : `REJECTED: send a HEARTBEAT first.` — la séquence est donc un `HEARTBEAT` signé (sysid 255) pour ouvrir la session, immédiatement suivi d'un `COMMAND_INT` `DO_REPOSITION` signé (en réutilisant les coordonnées cibles du repositionnement capturé, puisque seule la signature doit être fraîche, pas le contenu) adressé au drone (sysid 1) :

```bash
python3 -I solve/solve.py files/mission.tlog w01.ctf.chronos-security.ro <port>
```

Le relais répond :

```
OPERATOR AUTHENTICATED. Reposition accepted.
Audit receipt: CSCTF{...}
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Faire tourner une clé compromise sur le canal même suspecté compromis (ou ici, en cours d'enregistrement) annule la rotation : le nouveau secret est exposé par la même capture qui exposerait l'ancien.
- `SETUP_SIGNING` de MAVLink 2 place la clé brute sur le fil par conception — il suppose que le canal sur lequel il transite est déjà de confiance/hors bande ; le renvoyer sur le lien dans la bande supprime totalement cette hypothèse.
- L'anti-rejeu (un timestamp de signature strictement croissant) empêche le rejeu octet pour octet mais pas la forgerie une fois la clé connue : la solution est de re-signer un contenu frais avec la vraie clé et l'horloge du destinataire, pas de renvoyer des trames capturées.
- Les messages d'erreur du relais (`DENIED: frame is not authenticated…`, `stale signing timestamp… Link time is …`, `send a HEARTBEAT first`) spécifient entièrement la machine à états du protocole ; aucune devinette à l'aveugle n'a été nécessaire.

## Outils & références

- Python 3 (`struct`, `socket`, `hashlib`, `datetime`), `tshark` (pour confirmer que le pcap porte le même trafic MAVLink 2/UDP)
- Signature de paquets MAVLink 2 (`SETUP_SIGNING`, id de message 256) et trames (`COMMAND_INT`, `HEARTBEAT`)

---
[⬅ Retour à l'événement](../../README.fr.md)
