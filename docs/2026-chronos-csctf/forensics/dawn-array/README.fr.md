---
tags: [forensics, raid5, ext4, sqlite-wal, syslog, http]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Dawn Array

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 99 | ✅ | — | non | 0xAr3s-root | Chronos Security |

## Énoncé

> During a state-sponsored attempt to isolate the eastern corridor, dispatch gateway E2 of the Rovenqara Rail Continuity Authority (RRCA) issued conflicting turnout-release records and was then powered off. RRCA runs the rail lines that carry coalition supply in the Operation Dawn theatre, and the corridor stays shut until responders know which releases the corridor controller actually acknowledged.
>
> The gateway kept its staging volume on a four-member Linux md RAID-5 array; one member is lost and three raw members survive. Rebuild the volume read-only, then apply the gateway's own dispatch procedure, stored on that volume, to find the controller-acknowledged release witness, and report it in the form the procedure defines. This is a constructed recovery case built on real Linux md RAID-5, ext4, SQLite WAL, RFC 5424 and HTTP/1.1, not an acquisition from physical disks.
>
> Attachment: `dawn-array.zip` (604,849 bytes, SHA-256 `e41e1a4c6b2b…05de66`)
>
> Flag format: `CSCTF{dawn_<64 lowercase hex digits>}`

**Fichiers fournis :** `files/dawn-array.zip` (non commité — actuellement dans `forensics/dawn-array.zip`)

## En bref

Parser les superblocs md v1 pour la vraie géométrie (left-symmetric, chunks 32 Kio, data offset 1 Mio, rôles 0/2/3 présents), reconstruire le volume ext4 de 117 Mio en lecture seule, lire le ledger SQLite *avec son WAL appliqué*, et ne garder que les 16 cycles sur 128 dont réservation, readback et phases syslog concordent selon la procédure DP-7 — leur SHA-256 est le témoin.

## Démarche

**1. Reconnaissance — inventaire, puis métadonnées avant les octets**

```bash
unzip -l dawn-array.zip
# CASE-SHEET.txt  acq-1.raw  acq-2.raw  acq-3.raw (40 Mio chacun)  tools/raid5_extract.py
```

Note : la copie locale hashe différemment du SHA-256 affiché sur la plateforme (suffixe `…ad5de66` contre `…a05de66`) ; l'analyse ci-dessous travaille strictement depuis les octets fournis, et chaque couche se revalide (UUID d'array commun, label/UUID ext4, correspondance 1:1 ledger/syslog, 128 échanges HTTP propres).

Chaque membre porte un superbloc md v1.2 à l'offset fichier `0x1000` (magie `0xa92b4efc`, nom `rrca-gw-e2:staging`). Décodé selon `/usr/include/linux/raid/md_p.h` (`chunksize` en secteurs, rôles via `dev_roles[dev_number]`) :

| Membre | dev_number | rôle | layout | chunk | data offset | taille utile |
|---|---|---|---|---|---|---|
| acq-1.raw | 0 | **0** | 2 = left-symmetric | 64 secteurs = 32 Kio | 2048 secteurs = 1 Mio | 79872 secteurs |
| acq-2.raw | 4 | **3** | idem | idem | idem | idem |
| acq-3.raw | 2 | **2** | idem | idem | idem | idem |

Le membre perdu est donc le rôle 1 (parité recalculée), taille logique `3 × 79872 × 512 = 122 683 392` octets. Un premier balayage naïf (chasse à la magie ext4 sur permutations rôles/chunk/layout) a produit des centaines de hits car la redondance du stripe-0 duplique le superbloc sur deux membres — ce sont les rôles du superbloc qui tranchent, pas la magie.

**2. Hypothèse — lire DP-7 avant de croire un seul enregistrement**

Le volume (`rrca-staging`, UUID `e195b486-…`) contient exactement les trois types de preuves nommés par la procédure : `var/lib/rrca/dispatch.sqlite` (+ `-wal` de 552 Kio, `-shm`), `var/log/rrca/dispatch-gateway.syslog` (512 enregistrements RFC 5424, SD-ID `rrca@32473`) et `var/log/rrca/controller-access.pcapng` (2432 frames, 128 connexions loopback `10.61.4.10 → 10.61.4.21:8080`, chacune exactement POST/201 + GET/200).

DP-7 (`usr/share/doc/rrca-dispatch-procedure.txt`) définit la qualification Q1–Q5 : une ligne ledger + une de chacune des quatre phases syslog partageant `(cycle_id, request_id, gateway_seq)` dans l'ordre ; headers/corps POST conformes à la ligne avec écho 201 ; révision/nonce de réponse conformes ledger *et* syslog ; GET nommant la même requête avec une vue readback conforme réponse et ledger ; readback syslog conforme ledger. Tout doublon, non-succès, corps manquant ou désordre disqualifie.

Deux pièges en découlent directement : (a) 33 des 128 lignes ledger (`gateway_seq` 96–128) ne vivent **que dans le WAL** — une lecture du seul fichier principal les perd silencieusement, dont les cycles qualifiants 103/110/117 ; (b) les statuts seuls ne qualifient rien — les 128 échanges sont 201/200 sur le fil, et seuls 16 cycles survivent à la comparaison champ par champ.

**3. Exploitation — reconstruire, puis filtrer**

```bash
python3 solve/solve.py ../dawn-array.zip
# [*] md RAID-5: layout=left-symmetric chunk=32768 data_off=1048576
#                array=122683392 roles=[0, 2, 3] missing=1
# [*] Rebuilt 122683392 logical bytes, ext4 magic OK
# [*] Ledger        : 128 rows (WAL applied)
# [*] Syslog        : 512 records, 128 cycles
# [*] Capture       : 128 connections, POST/201 + GET/200 each, no pipelining
# [*] Qualifying    : 16 cycles
# [*] Qualifying gateway_seq: 14,15,34,35,55,69,78,79,80,83,85,87,95,103,110,117
# [+] FLAG            : CSCTF{...}
```

Le solveur dérive la géométrie des superblocs, délègue le brassage d'octets au `raid5_extract.py` fourni, extrait les fichiers en lecture seule via `debugfs` (ni montage, ni root), réassemble TCP/HTTP en Python pur, et vérifie chaque clause DP-7 — abandonnant plutôt que d'émettre un témoin si une attente structurelle casse. Les 112 rejets forment quatre classes nettes : nonce de réponse différant ledger+syslog (29), révision de réponse différant de `prepare_revision` (28), registres/valeurs du readback GET montrant la vue divergente du contrôleur (24, registres en `90xx`), et valeur du `READBACK_OBSERVED` syslog contredisant la ligne commise (31, toujours le bit `release_value`). Témoin = header 21 octets `RRCA-DAWN-WITNESS-v1\n` + 16 lignes `|` dans l'ordre croissant des `gateway_seq` (1733 octets), dont le SHA-256 est le corps du flag.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (masqué)

## Ce que j'ai appris

- La chasse à la magie est un oracle faible sur array redondant : la parité du stripe-0 faisait apparaître le superbloc ext4 sous presque toutes les géométries. Les `dev_roles[]` md (ni les noms de fichiers, ni la magie) sont la vérité terrain pour l'ordre des membres.
- Le WAL fait partie de la base : ouvrir le SQLite sans son `-wal` (ou n'extraire que `dispatch.sqlite` de l'image) perd les cycles 96–128 et donne un témoin de 13 lignes au hash faux. Copier le trio, ouvrir normalement, compter 128.
- Le « HTTP status alone does not qualify » de DP-7 est littéral ici — les 128 échanges sont 201/200 sur le fil. La discrimination tient entièrement à l'accord nonce/révision/registre/valeur entre quatre sources (ledger, syslog, réponse de réservation, vue readback).

## Outils et références

- Python 3 stdlib (`struct`, `hashlib`, `sqlite3`, `zipfile`) + `debugfs` (dumps lecture seule) + `tools/raid5_extract.py` fourni
- `capinfos`/`tshark` (recon capture : 128 connexions × 19 frames)
- Layout superbloc md v1 (`md_p.h`) ; algorithmes RAID-5 mdadm (2 = left-symmetric) ; magie superbloc ext4 `0x53EF` ; mode WAL SQLite ; structured data RFC 5424

---
[⬅ Retour à l'événement](../../README.fr.md)
