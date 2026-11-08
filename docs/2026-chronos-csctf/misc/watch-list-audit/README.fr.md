---
tags: [misc, changepoint, linear-regression]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Watch List Audit

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| misc | 120 | 243 | ✅ | — | 0xAr3s-root | Terminal43 |

## Énoncé

> An adversary went after the relief-dispatch screening service of a fictional country to slip convoys past the watch list and delay evacuation supplies. Responders kept the scoring history across a rule change and a fresh batch of audit probes.
>
> Reconstruct the current rule and compute the response fingerprint defined in `README.txt`.
>
> The data are constructed numerical exports, not a real deployment's records. Attachment: `watch-list-audit.zip`, 57,639 bytes, SHA-256 `04c0d2ad9e8ee0c111bf70b79fc26ab9c35a32df33b2b7eacb4893f422aa0c90`.

**Fichiers fournis :** `files/watch-list-audit.zip` (non commité)

## En bref

L'historique est un modèle linéaire sans bruit dont les coefficients ont changé exactement une fois : fitter les 500 lignes mélange les deux règles. Un scan exhaustif du point de rupture place le changement après l'observation 209, refitter les 291 dernières lignes retrouve la règle actuelle exactement (résidu ~1e-14), et quantifier ses 32 scores de probes puis les hasher comme spécifié donne le flag.

## Démarche

**1. Reconnaissance — un modèle linéaire, un changement, aucun bruit, aucune coupure fournie**

Le ZIP (SHA-256 vérifié contre la plateforme) contient `README.txt`, `history.csv` (500 lignes chronologiques `f0..f9,score`) et `probes.csv` (32 lignes `f0..f9`). Le README donne le modèle `score = intercept + Σ weight[j]·feature[j]`, exactement un changement de déploiement pouvant modifier les coefficients, aucun bruit de mesure, et ni position de coupure ni longueur de fenêtre de fit fournies. Il fixe aussi l'empreinte : par probe, `q = floor(1000·score + 0.5)`, chaque `q` sérialisé en entier décimal suivi d'un LF, puis SHA-256 de ces octets ASCII encapsulé en `CSCTF{...}`.

**2. Hypothèse — le piège est de fitter tout l'historique**

Un seul fit aux moindres carrés sur les 500 lignes laisse un résidu max de 7,61 (RMS 2,12) — très au-dessus de la promesse « aucun bruit » — donc le fit global est un mélange de deux règles et toute empreinte calculée à partir de lui est fausse. Des fenêtres glissantes de 50 lignes fittent en revanche exactement (résidu max ~1e-14) mais donnent deux vecteurs de coefficients nettement différents, ce qui confirme deux régimes linéaires exacts. Avec 11 inconnues (intercept + 10 poids) et zéro bruit, la vraie coupure est la seule où *les deux* côtés fittent exactement.

**3. Exploitation — scanner toutes les coupures, refitter la queue, quantifier**

Pour chaque coupure avec au moins 11 lignes de chaque côté, fitter les deux côtés et garder celle qui minimise le pire résidu :

- Meilleure coupure : **après l'observation 209** (la nouvelle règle commence à l'observation 210), résidu max **9,77e-15**.
- Deuxième coupure : résidu max **0,139** — quatorze ordres de grandeur plus mauvais, donc le point de rupture est sans ambiguïté.

Refitter les lignes 210–500 (291 lignes) donne la règle actuelle (intercept `1.18176107371557`, poids `-0.56479720711399, -1.48394281958821, -1.47774713637011, 0.156478865135981, -0.791677486188283, 1.27557192265779, -1.07095910507442, 0.705859257730788, 0.886486174800421, 0.360045487909974`). L'appliquer aux 32 probes et quantifier avec `floor(1000·score + 0.5)` (un vrai floor, donc les négatifs sont arrondis comme spécifié) donne le vecteur d'entiers hashé par le README. Le résultat est stable : des refits sur des sous-fenêtres disjointes du dernier segment modifient les scores des probes d'au plus ~5e-14, tandis que la probe la plus proche d'une frontière de quantification est encore à 8,6e-6 (en unités de score), donc l'empreinte ne dépend pas de la fenêtre de fit.

```bash
unzip watch-list-audit.zip -d watch-list-audit   # ou garder le ZIP tel quel
python3 solve/solve.py
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Ce que j'ai appris

- « Ni coupure ni longueur de fenêtre fournies » est le cœur du challenge : le point de rupture doit être *dérivé*, pas deviné. Le zéro bruit transforme ça en test exact — les deux côtés doivent fitter à ~1e-14.
- Le fit global naïf est l'impasse voulue ; son résidu (7,61) est l'indice que deux règles sont moyennées.
- J'ai vérifié la marge de quantification avant de faire confiance au hash : la probe la plus proche est à 8,6e-6 d'une frontière, plusieurs ordres de grandeur au-dessus de toute erreur de fit, donc des bibliothèques ou fenêtres différentes ne peuvent pas retourner un entier.

## Outils et références

- Python 3 + NumPy (`linalg.lstsq`), `hashlib`, `zipfile`
- Régression linéaire aux moindres carrés et détection de point de rupture (structural break)

---
[⬅ Retour à l'événement](../../README.fr.md)
