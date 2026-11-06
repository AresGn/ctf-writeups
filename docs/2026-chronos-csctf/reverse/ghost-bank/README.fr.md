---
tags: [reverse, aarch64, gdb-rsp, mmio, chacha20, unicorn, splitmix]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# ghost-bank

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| reverse | 856 | 29 | ✅ | — | 0xAr3s-root | Chronos Security |

## Énoncé

> A dormant relay bench from Brenzava exposes a single stopped GDB RSP endpoint. Behind it sits a controller with a sealed diagnostic bank. Recover the staged incident tasking; the flag is the code it contains.
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** `files/ghost-bank.zip` → `firmware.bin` (image plate AArch64 de 956 o), `firmware-load.txt`, `capture.ndjson` (non commités). Instance live : RSP en TCP brut sur `w01.ctf.chronos-security.ro:34224` (expirée).

## En bref

Le stub émule un contrôleur MMIO : `f(challenge)` du firmware le déverrouille, `CONTROL=0x9c` (STATUS 4) fait exposer par la page 7 la clé du coffre (32 o), et la page 3 (seule page avec `CIPHER_LEN≠0`, 131 o) se déchiffre avec le bloc ChaCha du firmware lui-même (nonce `SEAL-V01\0\0\0\1`, compteur 1) → tasking contenant le flag.

## Démarche

**1. Reconnaissance — un firmware jamais exécuté, une capture qui rejoue un rituel**

`firmware-load.txt` donne la carte MMIO (CONTROL, PAGE, OFFSET, DATA, CIPHER_LEN, CHALLENGE, KEY, STATUS) et le sous-ensemble RSP. `c`/`s` renvoient juste `S05` : le firmware n'est jamais exécuté, le stub *émule* les registres. La capture montre le rituel `CONTROL=0x41 → lire CHALLENGE → PAGE=7 → KEY (2×32 bits) → CONTROL=0x93 → STATUS=3`. Dans radare2, la boucle vivante en `0x400040` fait exactement ça, avec la clé calculée par un `f()` de type splitmix en `0x400120` ; `f(0x0123456789abcdef)` égale la KEY capturée, ce qui valide le reverse. Reste du code mort : quart-de-ronde/bloc ChaCha (`0x400090`/`0x400174`), un stream-XOR (`0x4002dc`) et les constantes `"expand 32-byte k"` + `"SEAL-V01"`.

**2. Hypothèse — la banque est chiffrée en ChaCha, mais où est la clé ?**

Les pages donnent des octets haute entropie, indépendants de la session, du challenge et de la clé. Beaucoup de temps perdu en devinettes (XOR répété, flux splitmix, ChaCha avec KEY/CHALLENGE/hashes XML comme clé, décompresseurs) — toutes négatives, car je ne lisais que les états 0/3 et seulement la page 7.

Trois observations ont tout débloqué :
- `qXfer` est annoncé dans `qSupported` mais répond `E01` sur une session fraîche ; après `CONTROL=0x41` il sert les XML (ils correspondent aux deux SHA-256 documentés et ne cachent rien — ce sont des contrôles d'intégrité, pas des clés).
- `CIPHER_LEN` **dépend de la page** : balayer PAGE 0–63 ne le montre non nul que sur la **page 3 (131)**. Je ne l'avais lu que sur la page 7.
- `CONTROL=0x9c` (dernier store du firmware) fait passer STATUS à **4**, et dans cet état la page 7 ne renvoie plus les octets scellés mais **32 octets de clé suivis de zéros**.

**3. Exploitation**

```bash
python3 solve/solve.py w01.ctf.chronos-security.ro 34224   # depuis le dossier contenant firmware.bin
```

1. Lire la page 3 (131 o) — le chiffré.
2. Faire le rituel avec `PAGE=7` (écrire une autre page avant la clé fait échouer le contrôle et remet PAGE à 0), `CONTROL=0x9c`, STATUS=4.
3. Lire 32 octets de la page 7 → clé du coffre.
4. Déchiffrer avec la fonction de bloc *du firmware* (Unicorn exécute `0x400174`, qui utilise une disposition d'état non standard ; un ChaCha20 de bibliothèque serait faux), bloc de flux `n` pour le compteur `1+n`, constantes `SEAL-V01` + `00 00 00 01`.

Clair : `TASKING//STAGED-EW//RELAY-BENCH//AUTHKEY CSCTF{…}//JAM PROFILE: …//END`.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Je me suis fixé sur la page 7 car capture et firmware la mentionnent, et j'ai perdu du temps à cryptanalyser les mauvaises données. Énumérer *tous* les registres observables sur *toutes* les pages et dans *tous* les états avant d'attaquer le chiffre : `CIPHER_LEN` désignait la page 3 en une boucle.
- Le code mort est la spec du device émulé : le dernier store du firmware (`0x9c`) était une transition d'état que j'avais écartée comme épilogue de boucle.
- Les fonctions conditionnées à un état (`qXfer` après `0x41`) méritent d'être re-sondées après chaque transition.
- Réutiliser la crypto du firmware par émulation plutôt que de la réimplémenter ; un « ChaCha » à état permuté ne matcherait jamais une bibliothèque.

## Outils & références

- Client RSP brut en Python 3, radare2 (`-a arm -b 64`), Unicorn (AArch64), gdb-multiarch inutile
- GDB Remote Serial Protocol, ChaCha20 (structure RFC 8439), SplitMix64

---
[⬅ Retour à l'événement](../../README.fr.md)
