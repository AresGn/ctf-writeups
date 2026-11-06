---
tags: [misc, lsb-steganography]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# the-reconnaissance-plate

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| misc | 120 | 96 | ✅ | — | 0xAr3s-root | — |

## Énoncé

> Operation Dawn, annex entry 11. We recovered a reconnaissance plate from an overrun Ash observation post. The photograph itself is unremarkable, but our interpreters are certain the annotation we need was carried out on it. Recover it.

**Fichiers fournis :** `files/recon-plate.png` (non commité)

## En bref

La photo est quantifiée en multiples de 4, donc ses deux bit-planes bas sont libres pour des données : le bit-plane 0 transporte une plate d'exercice en gzip/tar encadré (le leurre), le bit-plane 1 transporte la vraie plate de reconnaissance — son `annotation.txt` porte le serial, les mots du message et le groupe de contrôle dont le flag est construit.

## Démarche

**1. Reconnaissance — rien dans le conteneur, tout dans les bits bas**

Le PNG est un 256×256 RGB avec seulement des chunks `IHDR`/`IDAT`/`IEND`, aucun chunk texte, aucune donnée après `IEND` et aucune métadonnée. Visuellement, c'est un dégradé diagonal bruité. Les statistiques de pixels le trahissent : les bits 2–7 de chaque canal sont à 1 ~50 % du temps, mais les bits 0 et 1 seulement ~0,56 % — presque toutes les valeurs sont des multiples de 4. Les seuls pixels avec des bits bas non nuls sont dans les lignes 0–3, donc un payload se trouve dans les bit-planes bas en haut de l'image.

**2. Hypothèse — un payload encadré par bit-plane, et le premier est un leurre**

Lire chaque bit-plane en row-major sur les valeurs R,G,B entrelacées (MSB d'abord) donne, sur *les deux* planes, le même encadrement : une longueur uint32 big-endian suivie d'un flux gzip qui se décompresse en un petit tar (`plate/caption.txt`, `plate/grid.txt`, `plate/annotation.txt`) :

- **Bit-plane 0** (longueur gzip 291) : caption « Range card practice plate. Not for action. Plate 2 of 9. », annotation « DRILL SERIAL 11 HOLD THE RIDGE LINE UNTIL RELIEVED CODE … ».
- **Bit-plane 1** (longueur gzip 290) : caption « North ridge, 0500. Low cloud over the valley. Plate 7 of 9. », annotation « RECON SERIAL 11 THE GUNS BEHIND THE RIDGE CODE … ».

Les deux partagent le même `grid.txt` et le serial 11, ce sont donc des sosies délibérés. J'ai vérifié 56 autres variantes d'extraction (bit-planes 0–3, permutations de canaux, canaux seuls, lectures transposées) : seuls ces deux payloads encadrés existent. Le critère de sélection est dans les captions : l'énoncé demande une plate de *reconnaissance* d'un *poste d'observation* (annexe 11), ce qui correspond à la caption d'observation du bit-plane 1 et à son annotation `RECON` — tandis que le bit-plane 0 se désigne lui-même comme plate d'exercice/drill, « Not for action ». Le résultat du LSB classique (bit 0) est le piège.

**3. Exploitation — extraire les deux planes, garder l'annotation RECON**

```bash
python3 solve/solve.py recon-plate.png
```

Le script extrait les deux bit-planes, déballe les deux payloads tar encadrés en mémoire et sélectionne l'annotation de reconnaissance (commence par `RECON`, caption n'est pas celle d'exercice). Le flag est ensuite reconstruit depuis `RECON SERIAL 11 THE GUNS BEHIND THE RIDGE CODE …` en retirant les étiquettes `RECON SERIAL` / `CODE` — serial en premier, les mots du message en minuscules joints par des underscores, le groupe de contrôle en minuscules à la fin.

Deux soumissions naturelles sont fausses et ont été refusées : le groupe de contrôle seul entre accolades, et la transcription littérale gardant les étiquettes (`recon_serial_11_…`). La forme acceptée est celle de la série annexe avec l'entrée en premier (numéro d'entrée, mots du message, groupe de contrôle), étiquettes retirées.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Ce que j'ai appris

- Un histogramme de bits est l'indice le plus rapide ici : deux bit-planes à ~0,5 % de 1 contre ~50 % pour le reste signifient que les bits bas ont été délibérément effacés puis écrits.
- Le premier payload qu'une extraction LSB standard renvoie est le leurre ; sa propre caption le disqualifie (« practice… Not for action »). Lire *tous* les fichiers extraits, pas seulement la ligne d'annotation, est ce qui sépare les deux plates.
- L'encadrement (longueur `uint32` + gzip) rend les deux payloads auto-délimités et trivialement vérifiables — un bon contrôle que l'ordre d'extraction (row-major, RGB entrelacé, MSB d'abord) est le bon.
- Extraire le texte n'est pas la dernière étape : le flag est une *reconstruction* à partir de lui (serial, mots du message, groupe de contrôle), pas une sous-chaîne. Les étiquettes `RECON SERIAL` / `CODE` et le groupe de contrôle en majuscules sont de l'emballage, pas du contenu de flag.

## Outils et références

- Python 3, NumPy, Pillow ; `zlib` (gzip) et `tarfile` pour les payloads encadrés
- Stéganographie LSB par bit-planes dans les images PNG

---
[⬅ Retour à l'événement](../../README.fr.md)
