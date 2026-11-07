---
tags: [ml, backdoor, neural-network, numpy]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# operation-dawn-the-sentrys-model

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| ML | 540 | 261 | ✅| — | 0xAr3s-root | Terminal43 |

## Énoncé

> Operation Dawn, annex entry 09. Ash sentries use a small model to judge whether a dispatch is genuine. The recovered model was tampered with so that a forged order passes its check. Find the order it was taught to accept.
>
> Attachment: `authenticator.npz`
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** `files/authenticator.npz` (non commité).

## En bref

Le modèle est un MLP 392→48→1 dont deux neurones cachés sont des backdoors : des gabarits de poids ±1 avec un énorme biais négatif qui ne s'activent que lorsque l'entrée égale leur gabarit ; lire les 392 bits du gabarit comme 49 octets ASCII donne l'ordre que le modèle a appris à accepter, et l'un des deux est un texte lisible → flag.

## Démarche

**1. Reconnaissance — un petit MLP dans un `.npz`**

`numpy.load` (sans pickle) montre quatre tableaux : `W1` (48×392), `b1` (48), `W2` (48), `b2` (scalaire) : une couche cachée de 48 neurones sur une entrée de dimension 392 (392 = 14×28 = 49 octets × 8 bits), puis une sortie linéaire. La plupart des poids sont petits et ressemblent à de l'entraînement ; il faut trouver ce qui a été ajouté. En comparant les neurones : les normes des lignes de `W1` valent toutes environ 2,7–3,1 sauf deux neurones de norme 19,8 (= √392) ; et dans `W2`, les neurones 22 et 23 ont des poids de 16 et 26 contre moins de 4 pour les autres, avec des biais `b1` de −205 et −208 contre des valeurs autour de ±0,3.

**2. Hypothèse — un gabarit ±1 avec un énorme biais est un déclencheur**

Une ligne de `W1` faite uniquement de ±1 avec un biais d'environ −(0,52 × 392) est un filtre adapté : avec des entrées codées en ±1, sa pré-activation vaut `392 − 2k − 205` pour une entrée qui diffère du gabarit sur `k` bits, donc positive seulement quand elle est proche du gabarit (k < 93) et maximale (187) quand elle correspond exactement, alors que les entrées normales donnent des pré-activations autour de ±7. Via le grand poids de `W2`, un tel neurone force la sortie du modèle vers le haut (logit d'environ 3 000–4 800 contre une plage typique de −42…+69 sur des entrées aléatoires), donc le modèle accepte tout ce qui correspond. Afficher les lignes en images 14×28 ressemble à du bruit aléatoire (c'est un bitmap de données, pas un dessin), je les ai donc regardées comme des bits : 392 bits = 49 octets.

**3. Exploitation — lire le gabarit comme des octets**

En prenant `bit = 1` là où le poids vaut `+1` et en empaquetant 8 bits par octet (MSB d'abord) :

- neurone 22 → une chaîne ASCII commençant par `CSCTF{` et faite de mots lisibles, avec un numéro d'entrée « 09 » correspondant à « annex entry 09 » de l'énoncé et finissant par un court tag hexa ;
- neurone 23 → commence aussi par `CSCTF{`, mais le reste est un alphanumérique minuscule d'aspect aléatoire : un déclencheur leurre de même forme.

Vérifier les deux sur le modèle confirme que ce sont deux vraies backdoors (chaque gabarit active son neurone à ≈185 alors que les autres restent sous 9). La réponse voulue est celle qui se lit comme un message, le neurone 22.

```bash
python3 -I solve/solve.py files/authenticator.npz
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)


## Réflexions

- Les réseaux backdoorés laissent des empreintes statistiques dans les poids : poids de sortie aberrants, biais aberrants et lignes de norme ou d'ensemble de valeurs différents (`{-1, +1}` seulement).
- Un gabarit ±1 avec un biais proche de la moitié de sa longueur est la manière classique de cacher un déclencheur à correspondance exacte dans un réseau de neurones ; le déclencheur se lit alors directement dans les poids, sans accès en requête.
- Les leurres peuvent avoir la même forme que le vrai : trouver deux neurones backdoor a demandé de trancher avec des indices supplémentaires (texte lisible, le « 09 » de l'énoncé).
- Le modèle a été traité comme une donnée : seulement des lectures de tableaux `numpy` et des produits scalaires.

## Outils & références

- Python 3 avec NumPy (`load`, `packbits`)
- Backdoors / modèles trojanisés dans les réseaux de neurones (détection de neurones déclencheurs dans l'espace des poids)

---
[⬅ Retour à l'événement](../../README.fr.md)
