---
tags: [forensics, ics, iec-104, pcap, incident-response]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Silent Breaker

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 81 | ✅ | — | non | 0xAr3s-root | Dan-Andrei Grigorescu |

## Énoncé

> A regional substation breaker tripped without warning. You have console access to Velkarion Mobile's signaling investigation tool and a forensic bundle from the substation's IEC 60870-5-104 network. Reconstruct what happened and who is responsible.
>
> Endpoint: GET /events for the flagged-signaling feed; start at GET /files/ for the case-file index and report contract; submit the completed report to POST /submit.
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** téléchargés depuis l'index `/files/` de l'instance : `README.md` (contrat du rapport), `description.md`, `roster.json`, `iec104_capture.pcap`, `hmi_monitoring.log` (non commités). Instance live `http://w01.ctf.chronos-security.ro:39328` (durée de vie 30 minutes, expirée) ; chaque lancement est un cas différent avec des données différentes.

## En bref

Croiser les événements de signalisation d'un GT non légitime avec l'annuaire du personnel pour trouver l'employé ayant un accès VPN OT, lire la commande `ON` du disjoncteur (IOA, qualificatif, heure sur le fil) dans le pcap IEC 104, prendre le courant figé du run `QUALITY=SUSPECT` du journal historian, et soumettre ces cinq valeurs avec l'id de session VPN de l'employé ; le service renvoie le flag en `clearance_code`.

## Démarche

**1. Reconnaissance — lire le contrat avant de toucher à la console**

`GET /files/` liste les fichiers du cas et un contrat (`/files/README.md`) qui définit tout : `/events` (gratuit), `/query/subscriber` et `/query/vpn-window` (budgétés), `POST /confirm-target` (**2 tentatives**, la bonne cible débloque la route VPN) et `POST /submit` (**5 rapports complets**, réponse réussite/échec seulement). Le rapport a cinq champs : `ioa_address`, `command_qualifier`, `command_time_utc` (heure sur le fil, pas début du VPN), `telemetry_status` (courant figé du run suspect) et `vpn_session_id`. Les tentatives étant rares, chaque valeur doit être dérivée hors ligne avant de soumettre.

**2. Hypothèse — quatre sources indépendantes donnent les cinq champs**

- **Qui** : `/events` précise que tout GT hors `GT-0000..GT-0999` n'est pas un pair légitime. Six événements viennent de `GT-7779-Q22` (UpdateLocation / SendRoutingInfoForSM) pour six MSISDN. En les croisant avec `roster.json` : seule **Sanda Ionescu, `VLK-1944-ION`, OT Field Engineering**, a `ot_vpn_access: true` ; les autres (Finance, RH, Juridique, Service client) ne peuvent pas accéder au VPN OT. Deux requêtes `/query/subscriber` ont confirmé que les deux numéros essayés étaient sur liste de surveillance (budget 8).
- **Ce qui a été envoyé** : dans le pcap (TCP 2404), parmi les rapports réguliers `M_ME_NC_1` (type 13, IOA `0x21fb`), une trame va dans l'autre sens, maître → RTU, à 08:55:36 UTC : `68 0e … 2d 01 06 00 01 00 fb 21 00 01` = type 45 `C_SC_NA_1` (commande simple), COT 6 (activation), octets IOA `fb 21 00` = **0x21fb**, SCO `01` = **ON** ; le RTU répond avec COT 7 (confirmation d'activation) à la même seconde. L'heure de commande est donc **08:55** (le rapport veut `HH:MM`).
- **Courant falsifié** : `hmi_monitoring.log` montre des lectures normales d'environ 452–455 A (±1,5 A), puis dès 08:54:40 une valeur constante **426,0 A** que l'historian marque `QUALITY=SUSPECT` de 08:55:00 à 08:57:30 (les deux premières lectures identiques restent `GOOD` car la règle exige trois). Sur le fil, les lectures propres du RTU continuent de varier et reviennent vers 453 A : 426,0 A est donc un enregistrement figé/rejoué de l'historian, pas une valeur live : `telemetry_status = 426.0`.
- **Quelle session** : donnée seulement après un `/confirm-target` correct.

**3. Exploitation — confirmer la cible, obtenir la session, soumettre**

```bash
python3 -I solve/solve.py http://<cible>            # dérive et affiche le rapport (GET seulement)
python3 -I solve/solve.py http://<cible> --submit   # confirm-target + vpn-window + submit
```

`/confirm-target {"employee_id":"VLK-1944-ION"}` a renvoyé `confirmed`, et `/query/vpn-window` a listé cinq sessions ; celle de `VLK-1944-ION` est `VPN-914973` (Access-Accept à 08:21:41 avec un challenge OTP, IP source `203.0.113.197`). C'est une session différente de celles ouvertes à 08:55 ou plus tard par d'autres utilisateurs, qui sont des leurres rapprochés de la commande. Le premier rapport complet a été accepté (4 tentatives restantes) et a renvoyé le flag.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Lire le contrat d'abord : avec 2 et 5 tentatives, dériver les réponses hors ligne depuis les preuves est tout le jeu ; aucune devinette n'a été nécessaire.
- Ne pas prendre la session VPN qui commence au plus près de la commande ; le rapport demande la session de l'employé compromis, dont le début est antérieur (l'énoncé dit « heure sur le fil de la commande, pas début de session VPN »).
- Un marqueur `SUSPECT` côté historian vit dans le journal, pas sur le fil : le pcap montre que le RTU a continué à remonter des valeurs live, ce qui prouve que les 426,0 A affichés étaient figés.
- Le script dérive chaque champ des fichiers de l'instance, car un relancement donne un nouveau cas.

## Outils & références

- `curl`, `tshark` (pour lister les trames), Python 3 (`urllib`, `struct`, parsing pcap maison)
- ASDU IEC 60870-5-104 / IEC 60870-5-101 : types 13 (`M_ME_NC_1`) et 45 (`C_SC_NA_1`), causes de transmission 6/7

---
[⬅ Retour à l'événement](../../README.fr.md)
