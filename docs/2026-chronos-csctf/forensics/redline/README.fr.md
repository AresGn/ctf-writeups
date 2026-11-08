---
tags: [forensics, docx, tracked-changes, ooxml]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Redline

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 127 | ✅ | — | non | 0xAr3s-root | Chronos Security |

## Énoncé

> Meridian Relief Network, Nightwatch case, Depot 7. During the grid-instability night a cold-chain excursion directive went out to depot crews, telling them what to do with medicine that had broken the cold chain. A crew lead kept the copy they received, and something about it reads wrong.
>
> The directive is a Word document (`.docx`). Work out how the version that reached the crews differs from what was actually approved, who changed it, and recover the original excursion authorization.
>
> Everything you need is in the file.
>
> Flag format: `CSCTF{message}`

**Fichiers fournis :** `files/CC-11_excursion_directive.docx` (non commité).

## En bref

Le `.docx` contient encore ses modifications suivies : le texte approuvé (ordre de quarantaine et autorisation d'origine) est stocké en runs `w:del` par `s.kessler`, avec une autorisation leurre dans les runs `w:ins` ; lire le texte supprimé donne le flag d'origine.

## Démarche

**1. Reconnaissance — un docx est un zip de XML**

```bash
unzip CC-11_excursion_directive.docx -d docx/
```

Parties intéressantes : `word/document.xml` (corps), `word/comments.xml` et `docProps/core.xml`. Les métadonnées disent déjà qui l'a touché : créateur `A. Reyes` (la directrice médicale qui l'a émis), `lastModifiedBy` `s.kessler`, créé le 2026-10-06T14:02Z, modifié le 2026-10-07T02:41Z, révision 4.

**2. Hypothèse — le texte livré est « modifications acceptées » ; l'approuvé est dans les suppressions**

Le corps contient des éléments `w:del` / `w:ins`, tous de `s.kessler` à 02:41:00Z. En les comparant :

| | Approuvé (`w:del`) | Livré (`w:ins`) |
|---|---|---|
| Formulation | excursion « temperature » | excursion « thermal » |
| Seuil d'alerte | 30 minutes | 90 minutes |
| Flacons dépassés | DOIVENT être mis en quarantaine, NE DOIVENT PAS être redistribués | peuvent retourner en distribution à la discrétion du superviseur du dépôt |
| Autorisation | `CSCTF{...}` (d'origine) | un autre `CSCTF{...}` (« fraîche ») |

`comments.xml` contient la justification de `s.kessler` : « dropping the quarantine hold … Re-issuing under a fresh authorization ». L'instruction critique pour la sécurité a donc été inversée et l'autorisation remplacée. Le `CSCTF{...}` inséré est un leurre : on demande l'autorisation **d'origine**.

Autre piège : l'autorisation supprimée est coupée en deux runs `w:del` (ids 107 et 108), donc une recherche de `CSCTF{...}` complet dans le XML ne trouve que celle insérée ; il faut concaténer les deux morceaux `w:delText`.

**3. Exploitation — reconstruire le paragraphe d'origine depuis le XML**

Le script lit `document.xml`, reconstruit le texte *original* (runs simples + `w:delText`) et le texte *livré* (runs simples + `w:t` insérés), affiche les métadonnées et le commentaire, et extrait le flag de la version originale :

```bash
python3 -I solve/solve.py files/CC-11_excursion_directive.docx
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- « Accepter les modifications » dans Word n'assainit pas le fichier : le texte d'origine reste dans `w:del` tant que personne n'accepte et n'enregistre ; les métadonnées (`lastModifiedBy`, révision) et les commentaires disent qui et pourquoi.
- Les vues rendues (Word, LibreOffice) peuvent masquer ou fusionner cela ; lire le XML brut est plus fiable et permet de repérer le contenu coupé en plusieurs runs.
- Deux faux jumeaux de flag dans le même paragraphe : toujours vérifier lequel est demandé (original vs livré).
- Le fichier n'a été traité que comme donnée (unzip + parsing XML), jamais ouvert dans Word.

## Outils & références

- `unzip`, Python 3 (`zipfile`, `xml.etree`)
- Office Open XML WordprocessingML : `w:ins`, `w:del`, `w:delText`, commentaires, propriétés de base

---
[⬅ Retour à l'événement](../../README.fr.md)
