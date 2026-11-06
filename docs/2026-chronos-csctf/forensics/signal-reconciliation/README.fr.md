---
tags: [forensics, navigation, integer-arithmetic, gnss]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Signal Reconciliation

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 120 | 51 | ✅ | — | 0xAr3s-root | — |

## Énoncé

> Un acteur lié à un État a altéré le flux d'un récepteur de reconnaissance fictif pendant la
> mobilisation. Avant que le profil récepteur ne soit réutilisé pour le routage de récupération
> et la coordination logistique de défense civile, réconciliez son export de position locale
> avec la série de navigation locale intégrée indépendamment et produisez l'enregistrement
> complet de la cellule de réponse.
>
> Pièce jointe : `signal-reconciliation.zip` — 13 341 octets ;
> SHA-256 `ea09de452b798a834f1da524c9e71b0d03b51a408b4c8285f2a489b33f951633`.
>
> Format du flag : `CSCTF{BASE32_192_BIT_DIGEST}`.

**Fichiers fournis :** `files/flight.ndjson` (non commité)

## En bref

Suivre le fichier `reconciliation-sop.txt` à la lettre : intégration INS → résidus →
inventaire des fenêtres qualifiantes → décision → rapport canonique 603 lignes →
Base32 des 24 premiers octets du SHA-256.

## Démarche

**1. Lecture des entrées**

Le zip contient :
- `flight.ndjson` — 601 lignes JSON : `{i, t_ms, ve_mmps, vn_mmps, gps_e_mm, gps_n_mm}`
- `reconciliation-sop.txt` — spécification complète de l'algorithme
- `manifest.txt` — hachages SHA-256 de tous les fichiers
- `mission-note.txt` — contexte narratif

**2. Reconstruction INS (arithmétique entière exacte)**

```
ins_e[0] = ins_n[0] = 0
pour i de 0 à 599 :
    ins_e[i+1] = ins_e[i] + (ve[i] + ve[i+1]) // 20
    ins_n[i+1] = ins_n[i] + (vn[i] + vn[i+1]) // 20
res_e[i] = gps_e[i] - ins_e[i]
res_n[i] = gps_n[i] - ins_n[i]
```

Point clé : pas de virgule flottante, pas d'arrondi — la division entière `//` de Python
est exacte ici car toutes les sommes sont divisibles par 20.

**3. Inventaire des fenêtres qualifiantes**

`Q(i)` est vrai ssi pour une fenêtre de 10 échantillons débutant à `i` :
- Tous les échantillons ont une distance ≥ 25 000 mm : `res_e²+res_n² ≥ 625 000 000`
- Le résidu est augmente d'au moins 1 000 mm/pas
- Le résidu nord varie de ≤ 500 mm/pas

**18 fenêtres qualifiantes** trouvées.

**4. Décision**

Résidus finaux : `res_e[600] = 100 000 mm`, `res_n[600] = 1 000 mm`  
`dist_finale² = 10 001 000 000 ≥ 10 000 000 000` → seuil atteint.  
QSET non vide → **`QUARANTINE_GNSS_PROFILE`**

**5. Rapport canonique et flag**

```
603 lignes :
  RECONCILIATION/2|samples=601|qset=5,35,...,588|decision=QUARANTINE_GNSS_PROFILE
  E|0|0|0|0|0|0|0|0
  ...
  SUMMARY|qset=5,35,...,588|final_res_e=100000|final_res_n=1000|decision=QUARANTINE_GNSS_PROFILE
```

KAT vérifié : entrée tout-zéro → 14 329 octets, SHA-256 = `cc8c52dc…` ✓

```bash
python3 solve/solve.py files/flight.ndjson
```

```
[+] Base32(24B)  : EOSL5C6VZ54TN2PWXUO2B5TVHMVY5G3NWPILLYY
[+] FLAG         : flag{...}
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}`

## Ce que j'ai appris

- Le SOP est exhaustif — le challenge consiste à lire attentivement et implémenter exactement.
- Le vecteur de test KAT est précieux : il permet de vérifier le format et le nombre d'octets
  du rapport avant de calculer la vraie réponse.
- « Division entière exacte » = `//` de Python (division plancher), qui fonctionne proprement
  car toutes les sommes sont divisibles par 20.
- Le flag est un SHA-256 tronqué à 192 bits (24 octets), encodé en Base32 sans padding.

## Outils et références

- Python 3 (`json`, `hashlib`, `base64`)
- [RFC 4648 — encodage Base32](https://datatracker.ietf.org/doc/html/rfc4648)
- Intégration trapézoïdale (navigation inertielle par estime)

---
[⬅ Retour à l'événement](../../README.fr.md)
