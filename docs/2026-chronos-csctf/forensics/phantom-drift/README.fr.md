---
tags: [forensics, json, parser-differential, drone]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Phantom Drift

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 124 | ✅ | — | non | 0xAr3s-root | Dragoş Bacitea |

## Énoncé

> Reconnaissance drone Valkyrie-9 drifted off its approved waypoint while the command server recorded the mission as nominal. Reconcile the recovered client and backend logic with the flight record, telemetry, and radio intercept to show how the diversion avoided the alarm.
>
> This is a constructed offline forensic case.
>
> Attachments: `drone_control.decompiled`, `command_backend.decompiled`, `flight_log.bin`, `mission_manifest.json`, `radio_intercept.log`, `telemetry_logs.json`.
>
> Flag format: `CSCTF{16_lowercase_hex}`
>
> Flag construction: SHA-256 the concatenated text `<APPROVED_LAT_4DP><APPROVED_LON_4DP><LAT_OFFSET_6DP><LON_OFFSET_6DP><DISTANCE_1DP>` with no separators, then use the first 16 lowercase hex characters. The flight-log tag verifies the last 8 characters of the same digest; it is not an input.
>
> Flag derivation: `sha256(f"{approved_lat:.4f}{approved_lon:.4f}{delta_lat:.6f}{delta_lon:.6f}{displacement_m:.1f}")[:16]`. `approved_*` = manifest coordinates; `delta_*` = per-axis delta between approved and diverted coordinates, 6 decimals (degrees); `displacement_m` = great-circle distance in meters between approved and diverted points, 1 decimal. The `TAG:` value in `flight_log.bin` matches the last 8 hex of the same sha256.

**Fichiers fournis :** les six fichiers ci-dessus (non commités).

## En bref

La commande `waypoint_update` contient chaque champ deux fois, en snake_case (l'approuvé 47.2591, 19.0402) et en PascalCase (le détourné 47.2600, 19.0450) ; le backend a validé une graphie et le drone a obéi à l'autre. Le détournement est de 0,000900° / 0,004800° = 376,2 m (rayon WGS84), et le tag du journal de vol sélectionne ce rayon et confirme le condensat → flag.

## Démarche

**1. Reconnaissance — les deux `.decompiled` sont du code source en base64, le reste est de la preuve**

`drone_control.decompiled` (C#, Unity, Newtonsoft.Json) et `command_backend.decompiled` (Go 1.21) sont un en-tête plus un `DECODED_CONTENT = "<base64>"` ; le décoder donne les sources (lues seulement, rien d'exécuté). Les deux définissent le même `FlightParams` avec les tags JSON `altitude`, `speed`, `waypoint_lat`, `waypoint_lon`, `payload_weight`, `wind_compensation`, et le même validateur : rejet si `|lat − approuvé| > 0,001` ou `|lon − approuvé| > 0,001` (environ 111 m), contre le manifeste codé en dur 47.2591, 19.0402 (mêmes valeurs que `mission_manifest.json`).

Le log radio raconte l'histoire : à 12:30 la station sol 3 voit le drone 380 m à l'est de WP-Bravo, le contrôleur du drone dit que le waypoint a été mis à jour à 47.2600, 19.0450, et le serveur de commande répond « mission nominale, aucune anomalie ». La validation est donc passée pour une commande que le drone a exécutée autrement. (Je traite le « ~47.2600, 19.0450 » de la radio comme une piste et je le confirme dans la télémétrie, pas comme la réponse.)

**2. Hypothèse — une charge utile, deux lectures**

Dans `telemetry_logs.json`, l'enregistrement `waypoint_update` est la commande réelle. Il contient chaque champ deux fois :

```json
"waypoint_lat": 47.2591, "waypoint_lon": 19.0402, ...
"WaypointLat": 47.26,    "WaypointLon": 19.045,   ...
```

Des clés dupliquées/aliasées sont la différentielle de parseurs classique : deux parseurs qui normalisent les noms de clés différemment (casse, underscores, dernier gagnant, correspondance insensible à la casse) voient des valeurs différentes dans les mêmes octets. Ici les valeurs approuvées sont sous la graphie que le validateur accepte (47.2591 → delta 0 → « PASS »), alors que les valeurs détournées (47.2600, 19.0450) sont sous l'autre graphie. Le reste des preuves confirme laquelle le drone a suivie : les fixes GPS de `transit_to_new_waypoint` passent de (47.2591, 19.0402) par (47.26, 19.045) et continuent de dériver vers le NE (47.2627, 19.0594), `waypoints_visited` liste `surveillance_target` à 47.26, 19.045, et `server_validation` dit PASS avec `discrepancy_detected: false` alors que `anomalies_detected` est vide. (Je n'ai exécuté aucun des deux parseurs ; le comportement exact de la bibliothèque n'est pas nécessaire pour le flag, et la note du serveur dans la télémétrie se trompe même sur la valeur lue par Go, donc je m'appuie sur les positions de télémétrie et la radio.)

**3. Exploitation — calculer le flag, laisser le tag choisir le rayon terrestre**

- `delta_lat = 47.2600 − 47.2591 = 0.000900`, `delta_lon = 19.0450 − 19.0402 = 0.004800` (positifs : détourné moins approuvé) ;
- `displacement_m` par haversine. L'énoncé ne précise pas le rayon terrestre : avec le rayon moyen 6 371 000 m la distance est de 375,8 m ; avec le rayon équatorial WGS84 6 378 137 m elle est de **376,2 m** ;
- `flight_log.bin` est un en-tête de 24 octets (`FLGT`, version, compteurs) suivi de 12 octets qui sont `TAG:xxxxxxxx` XORés avec l'identifiant de mission `Valkyrie-9` comme clé répétée (trouvée avec le clair connu `TAG:` → clé `Valk…`) : le tag est `dc6836a2`.

Seule la variante 376,2 m donne un SHA-256 dont les 8 derniers caractères hexa sont `dc6836a2` ; celle à 375,8 m finit par `2126c52e`, et les variantes à deltas négatifs ne correspondent pas non plus. Le tag valide donc à la fois le rayon et la convention de signe, et les 16 premiers caractères hexa de ce condensat sont le flag.

```bash
python3 -I solve/solve.py files
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Deux composants qui « parsent le même JSON » ne lisent pas forcément la même valeur : des alias de clés (variantes de casse, doublons) suffisent à faire diverger un validateur et un exécutant, et un contrôle de signature ou de tolérance sur une lecture ne dit rien de l'autre.
- Lire toute la chaîne de preuves : la trace GPS de télémétrie, le résumé des waypoints visités et le log radio s'accordent sur le point détourné, ce dont le flag a besoin ; le « PASS » du serveur n'est que la vue du validateur.
- Le tag de vérification du journal de vol n'est pas qu'un contrôle : avec une formule sous-spécifiée (rayon terrestre, signe du delta), c'est l'oracle qui sélectionne la bonne variante.
- Le clair connu (`TAG:`) a trouvé la clé XOR sans rien deviner sur sa longueur.

## Outils & références

- Python 3 (`json`, `base64`, `math`, `hashlib`)
- Différentielles de parseurs / problèmes d'interopérabilité JSON, distance haversine, rayon équatorial WGS84

---
[⬅ Retour à l'événement](../../README.fr.md)
