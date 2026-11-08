---
tags: [forensics, ntfs, docx, xor]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Night Clerk

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 45 | ✅ | — | non | 0xAr3s-root | Mohamed Amine Mzoughi |

## Énoncé

> Des proxies de l'Armée des Cendres infiltrent les dépôts de la coalition sur le théâtre
> d'Opération Aube. Un commis hostile a utilisé un terminal de dépôt pour cacher un message
> de coordination avant d'être isolé ; seule l'image de la clé USB est conservée.
>
> Récupérez le message depuis l'image. Les autres pièces qu'elle mentionne ne sont ni fournies
> ni nécessaires ; vous n'avez pas besoin d'exécuter quoi que ce soit dans Office ni de monter
> l'image.
> Pièce jointe : `terminal.dd`, 8 388 608 octets,
> SHA-256 `fb76b12579f7c1314df6e7556548a61c73c96157d95e77ba253c371c9d78bfb7`.

**Fichiers fournis :** `files/terminal.dd` (non commité)

## En bref

Un `night_audit.docx` supprimé sur une image NTFS contient une insertion suivie (redline) avec un
texte hex encodé XOR ; le brute-force de la clé sur un octet (57) donne le flag.

## Démarche

**1. Reconnaissance — lister l'image NTFS**

```bash
sha256sum terminal.dd   # vérifier l'intégrité
file terminal.dd        # → DOS/MBR boot sector, NTFS
fls -r terminal.dd
```

Trois fichiers utilisateur apparaissent :

| Inode | Nom | État |
|---|---|---|
| 64 | `README.TXT` | actif |
| 65 | `audit-0214.log` | **supprimé** |
| 66 | `night_audit.docx` | **supprimé** |

**2. Lecture des fichiers d'indice**

```bash
icat terminal.dd 64   # README.TXT  → "Shift log clear."
icat terminal.dd 65   # audit-0214.log → instructions
```

`audit-0214.log` explique l'énigme :
- Le fichier Word est un **redline** (suivi des modifications) — lire l'*insertion*, pas le texte visible.
- Hex-décoder d'abord l'insertion suivie.
- DateTimeOriginal + OffsetTimeOriginal donne une heure UTC ; soustraire à l'horodatage NTP transmit ;
  la différence en secondes entières est la clé XOR pour chaque octet du ciphertext.
- Les autres pièces référencées (`desk.jpg`, `front_desk.pcapng`) ne sont pas nécessaires.

**3. Extraction du docx et localisation de l'insertion**

```bash
icat terminal.dd 66 > night_audit.docx
unzip -p night_audit.docx word/document.xml
```

L'élément `<w:ins>` contient un seul nœud `<w:t>` :

```
7a6a7a6d7f4251505d664a525c4e664b5c5d5550575c44
```

**4. Trouver la clé XOR**

Le ciphertext fait 23 octets. Le format du flag `CSCTF{…}` est connu, donc un brute-force
sur les 256 clés d'un octet suffit. La clé **57 (0x39)** produit un flag lisible et valide.

```bash
python3 solve/solve.py files/terminal.dd
```

```
[+] Key   : 57 (0x39)
[+] Flag  : flag{...}
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}`

## Ce que j'ai appris

- Les instructions de `audit-0214.log` sur les timestamps EXIF et NTP sont du décor — la clé XOR
  est récupérable par brute-force seul grâce au format connu du flag.
- Le docx est un ZIP ; pas besoin d'Office, juste `unzip` + parsing XML.
- `fls -r` révèle immédiatement les fichiers supprimés sur une petite image NTFS — toujours vérifier.

## Outils et références

- `fls`, `icat` (Sleuth Kit)
- Python 3 (`zipfile`, `xml.etree.ElementTree`)
- [Forensique NTFS — wiki Sleuth Kit](https://wiki.sleuthkit.org/)
- Spécification OOXML tracked changes (ECMA-376)

---
[⬅ Retour à l'événement](../../README.fr.md)
