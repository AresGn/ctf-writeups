---
tags: [forensics, modbus, pcapng, sha256]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Interlock Witness

| Catégorie | Points | Résolutions | Résolu | First blood | Auteur |
|---|---|---|---|---|---|
| forensics | 270 | 99 | ✅ | — | Chronos Security |

## Énoncé

> While the response-cell interlock read false, a fictional grid-support station feeding an allied depot network that Operation Dawn relies on accepted maintenance writes. The controller took syntactically valid Modbus/TCP writes, and the supplied safety policy is an offline response-cell rule, not a controller feature.
>
> Reconstruct the accepted target writes that violate the policy and derive the incident witness. Work from the supplied files only.
>
> Attachment: `interlock-witness.zip`, 15,307 bytes, SHA-256: `d46d5b2b820e412db288dde2a3a3f991990622a702708cb9fc13e498d223995`
>
> Submit: `CSCTF{<64 lowercase hex characters>}`

**Fichiers fournis :** `files/interlock-witness.zip` (non commité — actuellement dans `forensics/interlock-witness.zip`)

## En bref

Rejouer hors ligne l'unique flux Modbus/TCP, suivre les trois mots d'interlock (`0x000A`/`0x000B`/`0x000C`) depuis les observations FC03 et les écritures FC16 acceptées, conserver les 16 écritures cibles (en `0x0013`/`0x0014`) émises pendant que l'interlock était faux, puis hacher `INTERLOCK-WITNESS/1\0 || PDU-requête||PDU-réponse…` en SHA-256.

## Démarche

**1. Reconnaissance — vérifier le bundle et inventorier la capture**

```bash
sha256sum interlock-witness.zip
# d46d5b2b820e412db288dde2a3a3f991990622a702708cb9fc13e498d223995  conforme
unzip -l interlock-witness.zip
# README.txt  interlock.pcapng  register-map.md
# interlock-policy.md  witness-format.md  provenance.json  SHA256SUMS
capinfos interlock.pcapng   # 512 frames, interface lo unique, tcp port 502
tshark -r interlock.pcapng -q -z conv,tcp
# 127.0.0.1:59818 <-> 127.0.0.1:502 uniquement
```

Les trois fichiers Markdown forment toute la spécification — aucun indice caché ailleurs :

- `register-map.md` : adresses **PDU** base zéro. `40011/40012/40013/40020/40021` ne sont que des étiquettes opérateur. Mots mappés : `0x000A` `maintenance_permit`, `0x000B` `isolation_state`, `0x000C` `protection_armed`, `0x0013` `trip_limit`, `0x0014` `restore_delay`.
- `interlock-policy.md` : la règle hors ligne d'acceptation + de sécurité (ci-dessous).
- `witness-format.md` : la sérialisation et le hash, plus un vecteur de vérification hors incident.

Le framing des payloads TCP par la longueur MBAP donne **504 ADU Modbus = 252 transactions** (TID 1–252, strictement séquentiels, aucune retransmission, aucun ADU scindé/fusionné) : 124 paires FC03 et 128 paires FC16, toutes en protocole `0x0000` et unité `0x01`. Chaque réponse FC03 porte un byte count `22 = 2 × 11`, et chaque réponse normale FC16 répète adresse de départ + quantité — les filtres d'acceptation ci-dessous rejettent donc **0** transaction dans cette capture. Il fallait le vérifier, pas le supposer : c'est ce qui rend les 128 FC16 « acceptés ».

**2. Hypothèse — une machine à états hors ligne, pas une chasse aux chaînes**

Le flag est un SHA-256 : impossible à carver depuis la capture. Il faut le recalculer en rejouant, dans l'ordre des réponses normales :

1. **FC03 accepté** seulement si la requête FC03 immédiatement précédente correspond en TID/proto/unité/fonction dans le flux renversé et `byte_count == 2 × quantity`. Il met alors à jour chaque mot mappé qu'il couvre. Ici chaque FC03 lit `0x000A` quantité 11, soit `0x000A…0x0014` : chaque observation acceptée rafraîchit donc les cinq mots mappés d'un coup.
2. **FC16 accepté** seulement si sa réponse normale correspond en TID/proto/unité/fonction et répète adresse de départ + quantité. Les exceptions ne changent jamais l'état. Une écriture acceptée s'applique **après** sa réponse normale.
3. **Cible** = FC16 accepté de quantité 1 en `0x0013` ou `0x0014`. La politique annonce 8 autres FC16 acceptés inéligibles ; la capture contient bien exactement 5 écritures de prérequis (`0x000C=1` TID 2, `0x000A=1` TID 19, `0x000B=1` TID 20, `0x000B=0` TID 125, `0x000B=1` TID 142) et 3 écritures d'acquittement (`0x0018/0x0019/0x001A`, TID 248/250/252), soit 120 cibles (60 par adresse).
4. **Unsafe** = au moins l'une des conditions `permit==1`, `isolation==1`, `protection==1` est fausse **immédiatement avant la réponse normale de la cible** (une écriture ne se juge donc jamais elle-même, et une écriture de prérequis ne compte qu'à partir de la transaction suivante).

Deux pièges en découlent directement : utiliser les références affichées `400xx` au lieu des adresses PDU ne trouve rien, et juger la sécurité depuis la valeur écrite par la cible — ou après l'application de sa réponse — fausse les transactions frontières.

Chronologie d'état issue du rejeu (le triplet de prérequis ne change qu'à ces points) :

| Après TID | permit | isolation | protection | Cause |
|---|---|---|---|---|
| 1 (FC03) | 0 | 0 | 1 | observation initiale |
| 21 (FC03) | 1 | 1 | 1 | TID 19+20 arment permit/isolation |
| 126 (FC03) | 1 | 0 | 1 | TID 125 a relâché l'isolation |
| 143 (FC03) | 1 | 1 | 1 | TID 142 a restauré l'isolation |

**3. Exploitation — sélectionner les cibles unsafe et hacher le témoin**

L'application de la règle donne **16 cibles unsafe** sur 120 : TID **4, 6, 8, 10, 12, 14, 16, 18** (interlock pas encore établi, `0,0,1`) et TID **127, 129, 131, 133, 135, 137, 139, 141** (isolation relâchée, `1,0,1`). Les 104 autres cibles voient `1,1,1` et sont sûres.

Pour chaque cible unsafe, dans l'ordre des réponses normales, concaténer le PDU requête (`function-code || function-data`, **sans MBAP**) puis le PDU réponse normale : `T` fait `16 × (8 + 5) = 208` octets. Avec `P = "INTERLOCK-WITNESS/1" || 0x00` (20 octets), `W = SHA-256(P || T)`.

Le solveur n'utilise que la stdlib (son propre framing pcapng/Ethernet/IPv4/TCP/Modbus) et vérifie d'abord le vecteur publié — requête `10 00 13 00 01 02 00 2a` + réponse `10 00 13 00 01` → `b6e58fa9…f34786` — avant de toucher à la capture de l'incident :

```bash
python3 solve/solve.py ../interlock-witness.zip
# [*] Vector OK    : b6e58fa962e382b112eb596e416d5680495fc4bd02141f2389797f194df34786
# [*] Modbus ADUs  : 504
# [*] FC03 accepted: 124 (rejected 0)
# [*] FC16 accepted: 128 (rejected 0), targets 120
# [*] Unsafe targets: 16 (normal-response order)
#     TID   4 permit=0 isolation=0 protection=1 req=100013000102040d resp=1000130001
#     ...
#     TID 141 permit=1 isolation=0 protection=1 req=1000140001020a9a resp=1000140001
# [*] T (208 bytes): 100013000102040d1000130001...
# [+] FLAG         : CSCTF{...}
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (masqué)

## Ce que j'ai appris

- Lire les trois fichiers de spec comme un seul contrat avant d'ouvrir Wireshark : acceptation, éligibilité cible, instant de sécurité et sérialisation sont quatre filtres distincts, et chacun change le hash.
- « Immédiatement avant sa réponse normale » + « s'applique après sa réponse normale » constituent tout le modèle temporel. Évaluer à la requête coïncide ici uniquement parce que requêtes et réponses sont strictement séquentielles — le rejeu en ordre de réponse est l'implémentation sûre.
- Une capture synthétique propre exige quand même les contrôles de rejet : vérifier 124/124 FC03 et 128/128 FC16 acceptés (et la continuité des séquences TCP, sans retransmission) justifie de traiter chaque cible FC16 comme dans le périmètre.
- Les étiquettes `400xx` sont le piège d'adressage délibéré : tout le filtrage doit utiliser les adresses PDU base zéro (`0x000A…0x0014`).

## Outils et références

- Python 3 stdlib (`struct`, `hashlib`, `zipfile`) — le solveur n'exige aucun package tiers
- Wireshark / `tshark`, `capinfos` (contre-vérifications de reconnaissance seulement)
- Layouts MBAP Modbus/TCP + PDU FC03/FC16 (0x10) ; format de blocs pcapng

---
[⬅ Retour à l'événement](../../README.fr.md)
