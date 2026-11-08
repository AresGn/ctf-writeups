---
tags: [misc, icalendar, rfc5545, rrule, exdate, recurrence-id, python]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# command-calendar-reconciliation

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| misc | 120 | 141 | ✅ | — | 0xAr3s-root | Chronos Security |

## Énoncé

> A hostile edit scrambled the Vardanne Civil Continuity Service's emergency relay calendar during a national communications outage. The service keeps civil relays running behind coalition lines in Operation Dawn, and routing cannot be restored until the control room has every activation in the published response window.
>
> `GET /brief` gives the response window, the membership and ordering rules, and the exact attestation format. `GET /case.ics` returns the exported iCalendar file. Rebuild the activations from the calendar and submit the complete UTC attestation as one JSON object to `POST /attest`; a correct attestation returns the restoration code.
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** instance live uniquement (`http://<cible>:<port>/`, expirée)

## En bref

Développer trois séries `VEVENT` (`RRULE` + `RDATE` − `EXDATE`), appliquer les remplacements `RECURRENCE-ID` détachés *après* le développement, garder les occurrences dont le `DTSTART` **réel** est dans `[horizon_start, horizon_end)`, trier, et POSTer les 24 enregistrements.

## Démarche

**1. Reconnaissance — le brief est la spec**

`/brief` donne les règles : fenêtre `2026-06-29T00:00:00Z` ≤ début < `2026-07-14T00:00:00Z` sur le `DTSTART` *réel* après remplacement détaché (pas de test de chevauchement, pas de rognage), `start_utc` strictement croissant, exactement 24 enregistrements avec exactement `uid, recurrence_id_utc, start_utc, end_utc, category`, et un parseur JSON strict (pas de nom de membre dupliqué, pas de membre en trop). `case.ics` contient 3 séries (UID `relay-1..3`) et 2 instances détachées de `relay-1`.

**2. Hypothèse — où un développement naïf se trompe**

- `COUNT` inclut `DTSTART`, et les `RDATE` ajoutent des identités que la règle ne produit pas (ex. `relay-3` 2026-06-29T13:00, `relay-2` le samedi 2026-07-04).
- `EXDATE` retire une *identité nominale* avant tout remplacement (`relay-1` 2026-07-05).
- Une instance détachée est identifiée par `RECURRENCE-ID` (original nominal) mais porte son propre `DTSTART`/`DTEND` : `relay-1` 06-29T08:00 → déplacée au 06-28T07:00 (**sort** de la fenêtre), et 07-15T08:00 → déplacée au 07-13T07:00 (**entre** dans la fenêtre bien que sa date nominale soit dehors). Filtrer sur la date nominale fausse les deux ; `recurrence_id_utc` doit rester l'original nominal.
- `UNTIL=...Z` avec un `DTSTART` naïf fait lever `dateutil` : utiliser un début UTC explicite pour le développement.

**3. Exploitation**

```bash
pip install python-dateutil
python3 solve/solve.py http://<cible>:<port> --post
```

Le script développe chaque maître avec `dateutil.rrule`, ajoute les `RDATE`, retire les `EXDATE`, remplace les identités nominales par leur instance détachée, filtre sur le début réel, trie par `start_utc` et poste `{"activations":[...]}`. Il produit exactement 24 enregistrements, et le serveur répond avec le code de restauration (le flag).

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- La sémantique iCalendar est un ordre d'opérations : développer → `RDATE` → `EXDATE` → remplacement détaché → filtre sur le début *réel*. Tout autre ordre donne des ensembles plausibles mais faux.
- Le nombre attendu (24) du brief est un auto-contrôle bon marché : il aurait immédiatement révélé un `RDATE` ou un remplacement oublié.
- Se méfier des cas limites de bibliothèque (`UNTIL` UTC contre `dtstart` naïf) plutôt que de recoder les RRULE à la main.

## Outils & références

- Python 3, `python-dateutil` (`rrulestr`), `urllib`
- RFC 5545 (RRULE, RDATE, EXDATE, RECURRENCE-ID)

---
[⬅ Retour à l'événement](../../README.fr.md)
