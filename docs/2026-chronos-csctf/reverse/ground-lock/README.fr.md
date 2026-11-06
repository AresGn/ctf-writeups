---
tags: [reverse, x86-64, splitmix64, inversion]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Ground Lock

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| reverse | 120 | 163 | ✅ | — | 0xAr3s-root | Chronos Security |

## Énoncé

> A response team recovered the ground-maintenance utility used to service the GRIFFON-FC drones an Ash Army proxy flies over the Operation Dawn theatre. The accepted service code is needed before equipment handover.
>
> Recover that code. This is a constructed software case: the attachment is a Linux utility, not flight-controller firmware or a hardware dump, and static analysis is enough.
>
> Attachment: `fcunlock`, Linux x86-64 ELF, 682,600 bytes, SHA-256 `9634a7c4c4769a21eb921125a3d1b0ef560e3f4ed0202efa860861f0d2922399`.
>
> Submit `CSCTF{<service-code>}` with the exact 24 code bytes and case.

**Fichiers fournis :** `files/fcunlock` (non commité — actuellement dans `reverse/fcunlock`)

## En bref

`main` découpe l'argument de 24 octets en trois mots little-endian de 8 octets, passe chacun dans le finalizer splitmix64 et compare à trois cibles stockées — et ce finalizer est entièrement inversible mod 2⁶⁴, donc chaque cible s'inverse vers ses 8 octets de code exacts.

## Démarche

**1. Reconnaissance — comportement d'abord, puis forme du checker**

```bash
sha256sum fcunlock  # 9634a7c4…922399 conforme
file fcunlock       # ELF 64-bit LSB executable, x86-64, dynamically linked, stripped
./fcunlock          # usage: ./fcunlock <service-code>  (exit 2)
./fcunlock AAAA     # ACCESS DENIED (exit 1)
```

`main` (en `0x4016da`, via `__libc_start_main` depuis l'entry `0x401530`) exige exactement un argument d'exactement 24 octets (`strlen` vs `3*8`), sinon usage/`ACCESS DENIED`. Le chemin de succès affiche `GRIFFON-FC ground-maintenance interlock released.` puis `Maintenance token: CSCTF{%.*s}` avec l'entrée — le flag *est* donc l'entrée acceptée, et la comparaison est tout le verrou :

```c
for (i = 0; i < 3; i++) {
  acc = 0;
  for (j = 0; j <= 7; j++)
    acc |= (uint64_t)input[8*i + j] << (8*j);   // chargement u64le
  if (mix(acc) != table[4 + i]) fail = 0;        // table en 0x479020
}
```

La table rodata contient les deux constantes du mix (`0xff51afd7ed558ccd`, `0xc4ceb9fe1a85ec53`), le shift (`33`), le compte (`3`) et les trois digests — le qword suivant se décode en ASCII `usage: %`, c'est juste la zone de strings packées, pas une quatrième cible.

**2. Hypothèse — finalizer splitmix64, inversible, pas de brute-force**

La fonction en `0x401655` est le mixer splitmix64 verbatim :

```
x ^= x >> 33;  x *= 0xff51afd7ed558ccd
x ^= x >> 33;  x *= 0xc4ceb9fe1a85ec53
x ^= x >> 33
```

Chaque étape s'inverse sur 2⁶⁴ : `x ^= x >> 33` est une involution (2·33 ≥ 64, l'appliquer deux fois annule), et les deux multiplicateurs sont impairs, donc inversibles via `pow(m, -1, 2**64)`. Inverser chaque digest donne l'unique chunk de 8 octets — ni recherche, ni angr, ni exécution au-delà d'un run de confirmation.

**3. Exploitation — inverser, vérifier, soumettre**

```bash
python3 solve/solve.py ../fcunlock
# [*] Table       : shift=33 count=3
#     chunk 0 mix == 0x8bfd351846ffb86b
#     chunk 1 mix == 0x3ff3fd892aa7e3b2
#     chunk 2 mix == 0xf61e79e7e639e0d2
# [*] Code bytes  : b'...' (24 bytes, all printable ASCII)
# [+] FLAG            : CSCTF{...}
./fcunlock "$CODE"  # GRIFFON-FC ground-maintenance interlock released. (exit 0)
```

Le solveur localise la table par le motif d'octets `S1||S2` (les constantes existent aussi en immédiats `movabs` dans `.text`), inverse les trois digests, et vérifie l'aller-retour avant d'afficher. Le binaire confirme avec exit 0.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (masqué)

## Ce que j'ai appris

- Lire la table rodata d'abord (`constantes, shift, compte, digests`) bat le fixage de la boucle : la disposition donne les paramètres de l'algorithme avant même de désassembler le mixer.
- Reconnaître splitmix64 à ses deux constantes magiques (`ff51afd7ed558ccd`, `c4ceb9fe1a85ec53`) court-circuite l'analyse — ce sont parmi les constantes 64-bit les plus distinctives en circulation.
- Les checks inversibles sont courants en RE facile : toujours tester si la transformée est une bijection (multiplieurs impairs, xorshifts avec shift > 32) avant de sortir brute-force ou exécution symbolique.

## Outils et références

- Python 3 stdlib (`struct` — carving de table, `pow(a, -1, 2**64)` — inverses modulaires)
- `objdump -d -M intel`, `file`, `sha256sum` (triage statique ; un run de confirmation)
- Splitmix64 (Steele et al. — le finalizer `mix64` et son inverse)

---
[⬅ Retour à l'événement](../../README.fr.md)
