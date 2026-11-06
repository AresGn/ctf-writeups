---
tags: [reverse, firmware, dwfw, uboot, zlib, cpio, xor]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Operation Dawn: Radio Recovery

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| reverse | 120 | 156 | ✅ | — | 0xAr3s-root | Terminal43 |

## Énoncé

> A hostile intrusion cut the field-radio support link of a fictional country. Responders pulled `firmware.bin`, a software recovery bundle, and need the administrative recovery token locked inside it.
>
> Recover the complete `CSCTF{...}` value. The bundle is constructed but uses real compression and archive records; it is not a hardware dump or a bootable radio image.
>
> Attachment: `firmware.bin`, 1,048,576 bytes, SHA-256 `ae253e80cfca3035fe1e882c3c26a75b1d701f1b1bb343ba290d590573bc4313`.

**Fichiers fournis :** `files/firmware.bin` (non commité — actuellement dans `reverse/firmware.bin`)

## En bref

Dépacker le bundle DWFW maison (quatre partitions validées par CRC), prendre l'environnement U-Boot redondant actif (flag 7 bat flag 6), décompresser le flux zlib du rootfs avec la partition *msgcat* comme dictionnaire prédéfini vers une archive cpio, et XORer l'`admin_token` de `etc/config/radio` avec les octets MAC répétés exactement comme `S40admin`.

## Démarche

**1. Reconnaissance — une magie, quatre enregistrements**

```bash
sha256sum firmware.bin  # ae253e80…bc4313 conforme
file firmware.bin       # data (1 Mio, presque tout en flash effacée 0xFF)
binwalk firmware.bin    # ne trouve que les chemins /etc/init.d/* (strings msgcat)
```

Les 88 premiers octets sont un conteneur `DWFW` v1 maison : header 8 octets (`DWFW`, version 1, compte 4) puis quatre enregistrements de 20 octets `name[8] | offset LE | size LE | crc32 LE` — `loader` en 0x200 (111 o, bannière SPL), `ubootenv` en 0x270 (16 Kio), `msgcat` en 0x4270 (258 o), `rootfs` en 0x4380 (633 o). Les quatre CRC32 stockés vérifient ; le balayage standard des décompresseurs échoue seulement parce qu'il manque deux paramètres : quel environnement est actif, et le dictionnaire zlib. Au-delà de ~5 Kio, tout est du padding `0xFF`.

**2. Hypothèse — la redondance choisit la clé, le header nomme le dictionnaire**

`ubootenv` est un environnement U-Boot redondant : deux blocs de 0x2000 (CRC + octet flag + strings `key=value\x00`). Le bloc 0 (flag 6, `ethaddr=00:11:22:33:44:55`, `recovery=legacy`) est la copie périmée ; le bloc 1 (flag 7, `ethaddr=3c:22:fb:4a:1d:90`, `recovery=ready`) est actif — le flag supérieur gagne, et `ready` contre `legacy` le corrobore. La partition `msgcat` (strings d'init, `nvram get admin_token`, `#!/bin/sh`) se lit comme un catalogue de strings pour le rootfs — et de fait le flux rootfs est du zlib avec `FDICT` posé : son DICTID 4 octets égale `Adler-32(msgcat)` (`0x55d45a6c`). `zlib.decompress` échoue à l'octet 5 sans ce dictionnaire ; avec `zdict=msgcat` et deflate brut depuis l'offset 6, on obtient 2560 octets de cpio `070701` (newc).

Dedans : `etc/config/radio` (`admin_token=` 60 caractères hex) et `etc/init.d/S40admin`, qui est le key schedule en shell : retirer les `:` de `ethaddr`, puis XORer chaque octet de `admin_token` avec les 6 octets MAC répétés (`i % 6`). Le MAC legacy produit du binaire illisible ; le MAC actif est la seule clé pouvant produire de l'ASCII.

**3. Exploitation — rejouer le XOR du script de boot**

```bash
python3 solve/solve.py ../firmware.bin
# [*] DWFW loader    off=0x0200 size=  111 crc OK
# [*] DWFW rootfs    off=0x4380 size=  633 crc OK
# [*] U-Boot env[1] flag=7 ethaddr=3c:22:fb:4a:1d:90 recovery=ready
# [*] zlib DICTID   : 0x55d45a6c == Adler-32(msgcat)
# [*] rootfs        : 633 -> 2560 bytes (cpio)
# [*] admin_token   : 30 bytes (hex in config)
# [+] FLAG            : CSCTF{...}
```

Le solveur n'utilise que la stdlib (parsers DWFW, env U-Boot, cpio-newc et XOR maison), vérifie chaque CRC stocké et la correspondance DICTID, et refuse d'émettre un flag sauf si le résultat XOR est exactement un `CSCTF{...}` cadré — choisir l'environnement périmé échoue donc bruyamment au lieu d'afficher n'importe quoi.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (masqué)

## Ce que j'ai appris

- Les conteneurs maison s'annoncent : `DWFW` + un compte d'enregistrements suffit pour arrêter le `binwalk` et commencer à parser. Laisser les CRC32 stockés valider le layout (nom/offset/taille) avant de croire un offset sépare le parsing de la devinette.
- Le zlib à dictionnaire prédéfini est rare en CTF et se diagnostique proprement : CMF/FLG valides, échec à quelques octets, et un bit FDICT qui vous regarde. Le DICTID 4 octets *est* un checksum Adler-32 — trouver quel blob fourni y hashe nomme le dictionnaire.
- Les environnements redondants sont un vote à deux copies : ignorer l'octet flag donne 50 % de chances de XOR illisible. La monotonie du flag (`ready` > `legacy`) et le check ASCII ensemble rendent la sélection prouvable, pas chanceuse.

## Outils et références

- Python 3 stdlib (`struct`, `zlib` avec `zdict`/Adler-32, parser cpio-newc maison)
- `binwalk`, `file`, `sha256sum` (triage uniquement)
- Environnement redondant U-Boot (CRC + flag), zlib FDICT/DICTID (RFC 1950), format d'archive cpio newc (`070701`)

---
[⬅ Retour à l'événement](../../README.fr.md)
