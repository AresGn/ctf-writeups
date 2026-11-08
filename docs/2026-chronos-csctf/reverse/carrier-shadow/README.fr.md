---
tags: [reverse, steganography, elf, dwarf, eh-frame, huffman]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Carrier Shadow

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| reverse | 264 | ✅ | — | non | 0xAr3s-root | Armand Alexandru Balint |

## Énoncé

> A stripped x86-64 Linux ELF, pulled off a forward Ash Army command post after a hasty retreat. Prints a few lines of hex utility output when run. Signals suspects it is a carrier for something else: the usual places — data sections, strings, overlays, appended archives — are clean, but the binary's own second-stage payload signature turned up in captured traffic.
>
> Find where the payload actually lives in this binary, lift it out, and read the authorization string it carries. Static analysis beats a sandbox here — this is a reverse-engineering problem, not a shellcode run.
>
> Attachment: `carrier-shadow` — 1337736 bytes, SHA-256 `995fd7161d984898e521eb581f93380b11f31e3de342b368519a2221fb192a04`. Static ELF, no network, no setuid.
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** `files/carrier-shadow` (non commité). Tags : steganography, total-warfare.

## En bref

Le second étage est caché dans le **motif des tailles de fonctions de la table de recherche `.eh_frame_hdr`** : après une ancre générée par un PRNG, l'écart entre deux adresses FDE consécutives code des symboles de Huffman, dont les bits (blanchis avec le même PRNG) forment un flux DEFLATE brut d'un ELF ; son `.rodata` contient la chaîne d'autorisation → flag.

## Démarche

**1. Reconnaissance — un utilitaire hexa beaucoup trop gros**

`file` : PIE, lié dynamiquement, strippé. `strings` montre `hexkit 1.2.0` (crc32/fnv1a64 et un « self-test du registre de micro-fonctions ») et rien d'autre. Mais le fichier fait 1,3 Mo pour cela : `.text` fait 626 Ko et `.eh_frame` 496 Ko, alors que `.data`, `.rodata` et la fin du fichier n'ont rien où cacher des données, ce qui correspond à l'énoncé (« sections de données, chaînes, overlays, archives ajoutées sont propres »). Je ne l'ai pas exécuté.

En lisant le code de démarrage depuis le point d'entrée (`objdump -d`), une routine n'a rien à faire dans un outil hexa : elle parcourt ses propres program headers à la recherche de `PT_GNU_EH_FRAME` (`0x6474e550`), décode les encodages de `.eh_frame_hdr` (un lecteur DW_EH_PE), alloue `count × 8` octets et les remplit avec les adresses de fonctions de la table, puis appelle une fonction qui charge la constante **`0x6a2b3c4d`** — la « signature de payload ». Un dernier appel vérifie que le résultat commence par `0x464c457f` (`\x7fELF`), puis le passe à une autre routine. Le chargeur reconstruit donc un ELF à partir de la table de recherche du déroulage de pile.

**2. Hypothèse — lire le chargeur comme une spécification**

Lire la fonction de décodage (environ 0x600 octets d'x86) donne tout le format :

1. **Table** : `.eh_frame_hdr` (version 1, encodage de table `0x3b` = datarel sdata4) liste 24 816 FDE triées par adresse. Pour les ~120 premières entrées les écarts sont des multiples de 16 (vraies fonctions) ; à partir de l'entrée 123, ils sont petits et impairs (2…120) : le porteur. J'ai calculé `g[i] = loc[i+1] − loc[i]`.
2. **Ancre** : il initialise `xorshift32` avec `0x6a2b3c4d` (`x ^= x<<13; x ^= x>>17; x ^= x<<5`), produit 8 valeurs `x % 61 + 34`, et cherche 8 écarts consécutifs égaux (`69 75 80 91 47 58 35 37`) : trouvés à l'entrée 123.
3. **En-tête** : les 6 écarts suivants, moins 2 chacun : indice de table (0 ou 1), longueur sur 4 octets little-endian, et checksum XOR. Ici : table 0, longueur **17 733**, checksum **116**.
4. **Charge utile** : chaque écart suivant, moins 2 (donc 0…255), est un *symbole* d'un code de Huffman canonique dont les 256 longueurs de code viennent de `.rodata` (le chargeur indexe un tableau de pointeurs de `.data.rel.ro` : entrée 0 → `0x9b340`, entrée 1 → `0x9b240` ; lus dans les relocations). Les codes sont attribués à la manière deflate (plus courts d'abord, égalité départagée par la valeur du symbole), et les bits sont ajoutés **MSB en premier** jusqu'à `8 × longueur` bits.
5. **Contrôle et blanchiment** : le XOR de tous les octets doit égaler le checksum, puis chaque octet est XORé avec l'octet de poids faible de la sortie suivante de `xorshift32` (même graine).
6. L'appelant passe le résultat à une fonction de style `puff.c` (tables de comptage par longueur, `bits()` avec position sauvegardée, `longjmp` en cas d'erreur) : **DEFLATE brut**. Sa sortie doit commencer par `\x7fELF`.

**3. Exploitation — refaire tout cela hors ligne**

La table 0 donne le bon checksum (XOR = 116) ; la table 1 (une rampe de longueurs de code 6…) donne 255 : un leurre. Le script réimplémente les six étapes, écrit l'ELF de stage 2 de 34 192 octets (statique, strippé) et affiche la chaîne d'autorisation trouvée dans son `.rodata`, à côté de son format printf `payload: operation-dawn authorization = %s`. Je n'ai pas exécuté le stage 2 non plus.

```bash
python3 -I solve/solve.py files/carrier-shadow stage2.elf
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- La stéganographie n'est pas forcément dans les octets du fichier : ici c'est la *disposition* (les tailles de fonctions dans la table de déroulage) qui porte les données, donc scanner sections, chaînes et overlays ne trouve rien.
- Une constante qui ressemble à une graine (`0x6a2b3c4d`) utilisée deux fois (génération de l'ancre et blanchiment) a été le pivot : c'est à la fois la « signature » de l'énoncé et la clé du format.
- Des champs d'en-tête avec leurs propres contrôles (plage de longueur, XOR) font de bons oracles : ils m'ont permis de distinguer la vraie table de longueurs de code du leurre sans rien exécuter.
- Le code du chargeur était une spécification précise ; réimplémenter les mêmes étapes en Python est plus rapide qu'émuler ou mettre en bac à sable, ce que l'énoncé demandait.

## Outils & références

- `readelf`, `objdump`, `xxd`, Python 3 (`struct`, `zlib`)
- Program headers ELF, table de recherche binaire `.eh_frame_hdr` (encodages DW_EH_PE), codes de Huffman canoniques, xorshift32, puff.c / DEFLATE brut

---
[⬅ Retour à l'événement](../../README.fr.md)
