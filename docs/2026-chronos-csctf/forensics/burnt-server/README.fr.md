---
tags: [forensics, raid5, fat, gzip]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Operation Dawn: The Burnt Server

| Catégorie | Points | Résolutions | Résolu | First blood | Auteur |
|---|---|---|---|---|---|
| forensics | 120 | 61 | ✅ | — | Terminal43 |

## Énoncé

> Une force hostile a détruit les archives logistiques hospitalières d'un pays fictif pour paralyser le transport médical. Deux membres de stockage ont survécu, et le constat de récupération est en pièce jointe.
>
> Récupérez le registre des mouvements de train et soumettez son marqueur complet CSCTF{...}. Le cas est construit avec de vrais formats de filesystem et de compression ; rien ne vient de disques physiques.
> Pièce jointe : `server-remains.tar`, 4 198 400 octets, SHA-256 `98fd39f5957606e08b2a77dd253d6627366fd5853ecbd8f0f3ff81cc500345af`.

**Fichiers fournis :** `files/server-remains.tar` (non commité — actuellement dans `forensics/server-remains.tar`, à déplacer plus tard)

## En bref

RAID5 à 3 disques avec le disque central brûlé. Chunk 64 Kio, parité tournante vers la droite (`p = stripe % 3`). La reconstruction par XOR donne une image FAT16 ; le `TRAIN.GZ` supprimé (cluster de départ 16, 16599 octets) est carvé en contigu puis décompressé : c'est le registre des trains, il contient le flag.

## Démarche

**1. Reconnaissance — contenu du tar**

```bash
sha256sum server-remains.tar  # 98fd39f5… conforme
tar tvf server-remains.tar
# disk0.img  2097152
# disk2.img  2097152
# SALVAGE.txt    434
python3 -c "import tarfile; print(tarfile.open('server-remains.tar').extractfile('SALVAGE.txt').read().decode())"
```

`SALVAGE.txt` : caisson d'archives, trois disques identiques en rack chaud, disque central (slot 1) brûlé, slots 0 et 2 imagés. Aucun réglage contrôleur/array.

```bash
file disk0.img disk2.img
# disk0.img: OpenPGP Secret Key (coïncidence — forte entropie)
# disk2.img: data
```

Deux fois 2 Mio. 99,3 % des blocs de 512 o identiques, 35 blocs divergents : `[0, 1, 33, 65, 97, 98…127]`. Blocs soit aléatoires-différents des deux côtés (deux chunks de données), soit `données vs zéros` — signature classique d'un RAID5 avec un disque manquant quand le filesystem est presque vide.

Les strings de `disk0.img` racontent déjà l'histoire :

```
DAWN ARCH | ROSTER TXT | WARDS TXT | MANIFEST TXT | SIGNALS TXT | _RAIN GZ
night 01: two orderlies, one driver, one medic ...
ward 1: 23 beds, 5 stretchers, 1 litters ...
crate 000  morphia  31 kg ...
```

À l'offset `0x8200` de disk0 : un répertoire racine FAT (`ROSTER.TXT` start 2 taille 1440, `WARDS.TXT` 5/253, `MANIFEST.TXT` 6/2388, `SIGNALS.TXT` 11/2100, `0xE5 RAIN.GZ` supprimé start 16 taille 16599). À `0x4200` : table FAT16 (`F8 FF FF FF 03 00 04 00 …`). À `0xDE00` (disk0 seul, zéros sur disk2) : magie gzip `1f 8b 08`. Aucune signature boot `55 AA` alignée — l'image est stripée, pas un filesystem brut.

**2. Hypothèse — RAID5, reconstruction et brute-force de la géométrie**

Trois disques identiques, deux survivants, réglages perdus → RAID5 avec une panne, récupérable. Ni parité dédiée (RAID4) ni miroir (RAID1) ne collent au motif de diffs ; striping + parité tournante oui :

- stripe vide → trois chunks zéro → survivants identiques (zéro) ;
- stripe avec un chunk `X` et parité sur un survivant → paire `X == X` (identiques non nuls) ;
- stripe avec parité sur le disque manquant → survivants `X vs Y` (tous deux non nuls, différents) ou `X vs 0`.

Brute-force : tailles de chunk 512 o–64 Kio × parité `gauche (2,1,0…)` / `droite (0,1,2…)` × ordre des données asymétrique/symétrique, chunks manquants reconstruits par XOR, validation par boot sector FAT (`EB xx 90`, `FAT`, `55 AA`).

Seule la parité `droite` donne un boot sector. Seul le chunk **64 Kio** donne un répertoire racine cohérent (les autres donnent des entrées vides/garbage). Résultat : `BPS=512, SPC=1, réservé=1, 2 FAT × 32 secteurs, 512 entrées root, data_start=secteur 97`.

```bash
python3 solve/solve.py files/server-remains.tar
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

**3. Exploitation — carve du gzip supprimé et décompression**

`TRAIN.GZ` est supprimé, donc sa chaîne FAT est effacée (entrées 16+ à `0x0000`). Le fichier est contigu : cluster 16 → offset filesystem `(97 + 14) × 512 = 0xDE00`, pile la magie gzip. Carve de 16599 octets, `gzip.decompress` → 76901 octets :

```
WHITE VALLEY HOSPITAL - TRAIN MOVEMENT REGISTER
night of the evacuation

0000  wagon 01  berth 191  ward 6  tag 174254  stretcher
...
0942  wagon 14  berth 004  ward 6  tag ec86e1  stretcher

MOVEMENT ORDER: flag{...}

0943  wagon 10  berth 136  ward 6  tag 3eab8f  litter
...
```

1406 lignes, ~1400 wagons, flag ligne 947. Aucun autre `CSCTF{…}` dans l'image brute — seulement dans le registre décompressé.

## Flag

`flag{...}`

## Ce que j'ai appris

- Le `OpenPGP Secret Key` de `file` et les premiers secteurs aléatoires sont un leurre : le boot sector était sur le disque brûlé et se reconstruit par `disk0 ^ disk2`.
- 99 % de disques identiques ≠ miroir : en RAID5 avec une FAT presque vide, les stripes où parité = données semblent identiques. Les blocs `X vs 0` pointent vers la taille de stripe (écart 64 Kio entre FAT à `0x4200` et root dir à `0x8200` = indice).
- Fichier FAT supprimé = `start + size` conservés mais chaîne perdue — ne pas faire confiance à la FAT, carver en contigu et valider par magie + décompression.

## Outils et références

- Python 3 (`tarfile`, `struct`, `gzip`) — pas besoin de Sleuth Kit une fois destripé
- `tar`, `sha256sum`, `file`, `hexdump`, `strings`
- Wiki Linux RAID : chunk, rotation de parité, layouts left/right-symmetric
- Layout FAT16 (BPB, table FAT, répertoire racine, zone data)

---
[⬅ Retour à l'événement](../../README.fr.md)
