---
tags: [misc, federated-learning, gradient-inversion, numpy, mlp]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Operation Dawn: The Shared Model

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| misc | 213 | ✅ | — | non | 0xAr3s-root | Terminal43 |

## Énoncé

> Operation Dawn, annex entry 17. Ash Army units train their dispatch authenticator together, and after each round every unit sends its learning update back to command. We intercepted one unit's update, computed on the single genuine dispatch it was holding.
>
> We also lifted the shared model and that unit's read-out of the dispatch, but neither gives it up. Recover the dispatch the update was trained on. Handout: `dispatch-authenticator.npz`, 63,124 bytes, SHA-256 `e4b4be4c…877e7`, a NumPy archive of plain numeric arrays that loads with `allow_pickle=False`. Submit the recovered dispatch text.
>
> Flag format: `CSCTF{...}`, lowercase words joined by underscores and ending in a six-character check group.

**Fichiers fournis :** `files/dispatch-authenticator.npz` (non commité)

## En bref

La mise à jour est le gradient brut d'un MLP 50→64→8 sur un seul exemple, donc `grad_W1 = grad_b1 ⊗ x` : diviser une ligne de `update_W1` par le `update_b1` correspondant donne l'entrée `x`, qui est la dépêche encodée en `octet/255` — à lire en ASCII.

## Démarche

**1. Reconnaissance — ce que contient l'archive**

`np.load(..., allow_pickle=False)` liste : `global_W1 (64,50)`, `global_b1`, `global_W2 (8,64)`, `global_b2` (le modèle partagé), `logits (8)` et `label` (la lecture de l'unité), et `update_W1/b1/W2/b2` (mêmes formes). La mise à jour contient beaucoup de zéros dans `update_b1`/`update_W1` : signature d'une couche cachée ReLU où les unités inactives ne reçoivent aucun gradient.

**2. Hypothèse — la mise à jour est un gradient à un seul exemple**

Pour une entropie croisée softmax sur un exemple, `grad_b2 = softmax(logits) − onehot(label)`. Comparé à `update_b2`, le rapport vaut exactement 1,0 sur les 8 entrées : pas de taux d'apprentissage, pas de moyenne, donc la mise à jour est le gradient brut d'un seul exemple. La rétropropagation donne alors `grad_b1 = (W2ᵀ·grad_b2) ⊙ relu'(z1)` et `grad_W1 = grad_b1 ⊗ x`.

**3. Exploitation — inverser la première couche**

Chaque ligne `i` avec `grad_b1[i] ≠ 0` donne `x = grad_W1[i] / grad_b1[i]`. Les 34 lignes non nulles concordent à 5·10⁻¹⁷ près. Les valeurs sont dans [0,19 ; 0,49] ; multipliées par 255 ce sont des entiers (erreur 10⁻¹⁴) : `0,2627·255 = 67 = 'C'`, `0,3255·255 = 83 = 'S'`. L'entrée de dimension 50 est donc le texte encodé en `octet/255`.

```bash
python3 solve/solve.py files/dispatch-authenticator.npz
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (masqué)

## Réflexions

- En apprentissage fédéré, une mise à jour sur un seul exemple fuit l'entrée : pour une première couche dense, `grad_W = grad_b ⊗ x` réduit l'inversion à une simple division. Le batching, le clipping/bruit (DP) ou l'agrégation sécurisée existent pour l'empêcher.
- Vérifier d'abord l'hypothèse (`softmax − onehot` égal à `update_b2` exactement) évite de deviner la règle de mise à jour (gradient ou delta de poids, taux d'apprentissage).
- Le modèle partagé et la lecture logits/label étaient des leurres : seule la mise à jour était nécessaire.

## Outils & références

- Python 3, NumPy
- Inversion de gradient / « deep leakage from gradients » (Zhu et al., 2019) pour le principe ; ici la forme analytique fermée de la première couche

---
[⬅ Retour à l'événement](../../README.fr.md)
