---
tags: [network, ss7, diameter, telecom-fraud, cross-validation]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Ghost Signal

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| network | 145 | ✅ | — | oui | 0xAr3s-root | Dragoş Bacitea |

## Énoncé

> A telecom operator is seeing fraudulent roaming activity and disputed billing events. Investigators recovered SS7 signalling, Diameter sessions, and the related billing export.
>
> Reconstruct the intrusion chain from those records and recover its marker. This is a constructed, offline protocol-forensics case.
>
> Attachments: `ss7_capture.pcap`, `diameter_capture.pcap`, `billing_events.json`.
>
> Flag format: `CSCTF{8_lowercase_hex}`
>
> Flag construction: SHA-256 the literal text `<IMSI>:<SESSION_ID>:<FIRST_ANOMALOUS_BILLING_TIMESTAMP>`, then use the first 8 lowercase hex characters. Use the values exactly as written in the evidence and literal `:` separators.
>
> Flag derivation (serialization spec): `sha256("<imsi>:<full_diameter_session_id>:<unix_timestamp>")[:8]`, lowercase hex. `imsi` = the anomalous IMSI as decimal (e.g. `226012014000001`). `full_diameter_session_id` = the entire Session-Id including dots and semicolons (e.g. `host.example.com;seconds;id`), not just the GT fragment. `unix_timestamp` = unix seconds (integer) of the first anomalous billing event, not ISO. Fields joined as strings with `:` between them. No hosts, no GTs, no event ids.
>
> Indice : plusieurs fichiers de capture ont été récupérés sur des réseaux différents lors du même incident. Commencer par cataloguer ce que contient chaque fichier, puis chercher le fil unique qui les traverse tous.

**Fichiers fournis :** les trois fichiers ci-dessus (non commités).

## En bref

Un seul IMSI (`226012014000001`) et un seul `Session-Id` Diameter (`hss.eastern-tele.ro;1723740150;49211`) apparaissent, identiques à l'octet près, dans les trois sources : le `updateLocation` de la capture SS7, les AVP de la capture Diameter, et les lignes anomales de l'export de facturation. Sérialiser cet IMSI, ce `session_id` complet et l'horodatage du premier événement de facturation anormal (`1723740150`), puis hacher le tout, donne le flag.

## Démarche

**1. Reconnaissance — cataloguer chaque fichier séparément**

- `billing_events.json` : un export Diameter OCS pour `eastern-tele.ro`, 40 événements. 30 lignes `CCR-A` ordinaires (un IMSI chacune, `2260120140002000`…`2260120140002011` en boucle, des identifiants synthétiques à 16 chiffres) entrecoupées de deux courtes salves anomales : 5 lignes `CCR-I` (`atk_0000`…`atk_0004`, `charging_amount: 0.0`, `anomaly: "zero_charge_on_roaming"`, `redirect_host: "intercept-49211.evil-domain.net"`) et 5 lignes `CCA` (`pivot_0000`…`pivot_0004`, `anomaly: "unusual_routing_path"`, `serving_cscf: "cscf.pivot.eastern-tele.ro"`, `redirect_host: "redirect-49211.evil-domain.net"`). Ces dix lignes partagent un seul `imsi` (`226012014000001`, 15 chiffres — un IMSI d'aspect réel, contrairement aux IMSI synthétiques de la ligne de base) et un seul `session_id` : `hss.eastern-tele.ro;1723740150;49211`.
- `ss7_capture.pcap` : GSM MAP sur M3UA/SCCP. Une ligne de base de requêtes `sendRoutingInfo`/`sendRoutingInfoForSM` tourne avec le Global Title de l'appelant qui monte régulièrement, `49100`→`49144` (partenaires d'itinérance ordinaires). À `t=150`, le GT appelant saute à **`49211`** pour une salve de requêtes `sendRoutingInfo`/`sendRoutingInfoForSM` contre `+40721000101`…`+40721000105` — exactement les numéros ciblés par les lignes `atk_000x` de la facturation. À partir de `t=190`, le GT appelant passe à `49311` et émet un `updateLocation` pour l'IMSI **`226012014000001`** — l'attaquant qui réenregistre la localisation de cet abonné, le détournement proprement dit.
- `diameter_capture.pcap` : échanges de style Cx/Ro. Les sessions ordinaires ont pour `Origin-Host` le `cscfN.eastern-tele.ro` qui sert, et pour `Session-Id` `hss.eastern-tele.ro;<ts>;<n>` avec `n` qui s'incrémente normalement. Une session se détache : `Session-Id = hss.eastern-tele.ro;1723740150;49211`, avec des requêtes venant de `Origin-Host = cscf.rogue.evil-domain.net` et une réponse désignant `cscf.pivot.eastern-tele.ro` comme CSCF servant — correspondant exactement aux lignes `pivot_*` de l'export de facturation. Son AVP `Subscription-Id-Data` vaut `226012014000001`.

**2. Hypothèse — l'indice demande de trouver le fil, pas de faire confiance à un seul fichier**

Chaque fichier pris seul ne montre qu'une partie du tableau (un GT, un hôte voyou, une étiquette d'anomalie) ; l'énoncé et l'indice demandent explicitement de les recouper. Vérifier qu'il existe exactement **un** IMSI anomal et **un** `session_id` anomal dans tout l'export de facturation (chaque ensemble a une taille de 1) élimine toute ambiguïté, et c'est ce même IMSI, ainsi que le même fragment `49211` du session id, qui apparaissent inchangés dans la capture SS7 (`e212.imsi` dans le `updateLocation`) et dans la capture Diameter (`Subscription-Id-Data`, et le suffixe `49211` du `Session-Id`). C'est le « fil unique » : le GT `49211` a mené la fraude de facturation et la reconnaissance de routage côté Diameter, le GT `49311` a exécuté le détournement de localisation côté SS7, et le seul IMSI de l'abonné relie les deux à la même victime — trois captures indépendantes du même incident, recoupées plutôt qu'acceptées sur parole.

La spécification est explicite sur ce qu'il ne faut **pas** utiliser : ni noms d'hôtes, ni GT, ni identifiants d'événement — seulement l'IMSI, la chaîne complète `Session-Id` (points, points-virgules compris), et l'horodatage Unix du premier événement de facturation anormal, qui est `atk_0000` à `1723740150` (aussi, non par hasard, l'horodatage intégré dans le session id lui-même).

**3. Exploitation — sérialiser et hacher**

```text
226012014000001:hss.eastern-tele.ro;1723740150;49211:1723740150
```

```bash
python3 -I solve/solve.py files
```

Le script redérive l'IMSI/session/horodatage anomal depuis le seul JSON, puis recoupe les deux pcaps avec une extraction de champs `tshark` pour confirmer que le même IMSI et le même `Session-Id` sont bien sur le fil avant de hacher.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Trois fichiers venant de « réseaux différents » décrivant un seul incident, c'est un exercice de recoupement : la bonne réponse est la valeur identique à l'octet près dans les trois, pas celle qui a l'air la plus suspecte dans un seul fichier.
- Une ligne de base délibérément croissante (GT `49100`→`49144`, IMSI synthétiques `…002000`→`…002011`) fait ressortir les valeurs isolées et hors séquence (`49211`, `49311`, un IMSI à 15 chiffres d'aspect réel) sans avoir besoin de lire trame par trame.
- Les deux GT de l'attaquant (`49211` pour la fraude/reconnaissance Diameter, `49311` pour le détournement de localisation SS7) ne sont pas la même valeur et aucun des deux seul n'est « la » réponse ; le format du flag exclut explicitement les GT pour cette raison — ce sont l'IMSI et le session id complet qui se recoupent réellement entre protocoles.
- `full_diameter_session_id` veut dire exactement cela : la chaîne AVP entière avec ses séparateurs, pas seulement le compteur final qui coïncide avec un GT.

## Outils & références

- `tshark` (`-T fields`) sur les deux pcaps, Python 3 (`json`, `hashlib`, `subprocess`)
- GSM MAP (`sendRoutingInfo`, `sendRoutingInfoForSM`, `updateLocation`) sur SS7/M3UA ; AVP Diameter Session-Id / Subscription-Id-Data (échanges de style 3GPP Cx/Ro)

---
[⬅ Retour à l'événement](../../README.fr.md)
