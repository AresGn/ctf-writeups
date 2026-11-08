---
tags: [network, sensor-fusion, ais, radar, geodesy, blind-api]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Dark Anchorage Reconciliation

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| network | 302 | 101 | ✅ | — | 0xAr3s-root | Chronos Security |

## Énoncé

> Kaldura, an Operation Dawn ally, carries coalition traffic over the KALNET-1 cable, and KALNET-1 failed just as a hostile maritime operation was expected near the cable corridor. AIS says no suspicious vessel crossed the fault envelope, yet coastal radar recorded anonymous contacts on a different clock.
>
> Produce the complete sensor-reconciliation report that identifies the false broadcast, quantifies the displacement and establishes the actual closest approach. Read `GET /schema` for the report format. The four evidence files are `GET /files/ais.ndjson`, `GET /files/radar.csv`, `GET /files/cable-fault.txt` and `GET /files/method-note.txt`. Submit one complete report to `POST /reconcile`; a correct report returns the reconciliation code.
>
> Flag format: `CSCTF{...}`

Indice : *Normalize the declared radar clock, then score every radar/AIS association across its whole paired trajectory, not at one point near the cable.*

**Fichiers fournis :** instance live uniquement (`http://<cible>:<port>/`, expirée) ; les quatre fichiers de preuve sont servis par celle-ci.

## En bref

Soustraire le décalage de l'en-tête radar (180 min) pour apparier radar et AIS, associer les 16 pistes par résidu médian, repérer la seule piste AIS qui dérive de (330, 330) m sur 4 échantillons, calculer le CPA radar-seul au point du câble, puis POSTer le rapport — le plus dur est le format JSON non documenté, où le vecteur doit être deux membres séparés.

## Démarche

**1. Reconnaissance — la note de méthode est la spec**

`method-note.txt` donne tout l'algorithme : `local_time` radar = UTC + décalage d'en-tête (`# radar_utc_offset_minutes=180`), appariement des échantillons UTC normalisés égaux, plan local autour du point du câble (`est=R·cos(lat0)·Δlon`, `nord=R·Δlat`, R=6378137), score par résidu médian, plus longue série ≥4 échantillons avec résidu ≥250 m et pas ≤15 m par composante pour la divergence, CPA de segment radar seul avec projection bornée. `/schema` liste les noms de membres et les tolérances (3 m, 2 s) mais **aucun exemple de corps**.

**2. Hypothèse — une bijection complète à score quasi nul, et un menteur**

Avec le décalage soustrait, chaque piste R-01..R-16 correspond à un seul MMSI AIS avec un résidu médian de 0 m (les mauvaises paires sont ≥180 m : aucune ambiguïté). Les résidus par échantillon, plutôt que la médiane, révèlent le menteur : R-03 / MMSI `979103829` est à 466,7 m — exactement (330 m E, 330 m N) — à 10:26, 10:28, 10:30 et 10:32 UTC. Le CPA radar-seul sur tous les segments est R-03 elle-même, qui passe par le point du câble sur le segment 10:30→10:32 à u≈0,818.

**3. Exploitation — faire accepter le rapport**

`POST /reconcile` répondait `400 invalid report` à tout, sans indice (une erreur sémantique donnerait `422 report not accepted`). Le passage 400 → 422 sert d'oracle : j'ai balayé ~350 formes (associations en objets/chaînes/dictionnaire, intervalle en deux clés ou liste, vecteur en liste/objet, décalage en chaîne, enveloppes) jusqu'à obtenir un 422. La forme acceptée :

```json
{"version":"KALNET-RECON-1","radar_utc_offset_minutes":180,
 "associations":[{"radar_track":"R-01","mmsi":"<9 chiffres>"}, "... x16"],
 "divergence":{"mmsi":"<9 chiffres>","start_utc":"...Z","end_utc":"...Z",
               "ais_minus_radar_east_m":330,"ais_minus_radar_north_m":330},
 "closest_approach":{"mmsi":"<9 chiffres>","utc":"...Z","distance_m":0.0}}
```

Le 422 restant venait de mon propre bug : j'avais converti l'heure du CPA avec `datetime.timestamp()` sur une date naïve, ce qui la décalait du fuseau local (09:31:38 au lieu de 10:31:38). Avec `calendar.timegm`, le serveur a renvoyé le flag.

```bash
python3 solve/solve.py http://<cible>:<port> --post
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Quand une API ne donne aucun exemple, les codes de statut sont l'oracle : le passage 400 → 422 prouve que la *structure* est bonne avant que les *valeurs* soient vérifiées. Balayer les formes avec un pool de threads et n'afficher que les réponses non-400.
- Ne pas se fier à une validation qui échoue à la fois sur la structure et les valeurs : après avoir trouvé la forme, un second bug (fuseau horaire) restait caché. Vérifier les valeurs dérivées contre les données (l'heure du CPA devait tomber dans le segment 10:30–10:32, pas 09:31).
- Toujours utiliser des fonctions de temps explicites en UTC (`calendar.timegm`, `timezone.utc`) ; `timestamp()` sur une date naïve utilise silencieusement le fuseau de la machine.

## Outils & références

- Python 3 (`urllib`, `csv`, `statistics`, `concurrent.futures`), `curl`
- Projection locale tangente, formule de CPA de segment tirée de `method-note.txt`

---
[⬅ Retour à l'événement](../../README.fr.md)
