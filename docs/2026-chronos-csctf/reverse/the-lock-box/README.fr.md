---
tags: [reverse, elf, constructors, static-analysis]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# The Lock Box

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| reverse engineering | 120 | 166 | ✅ | — | 0xAr3s-root | Terminal43 |

## Énoncé

> Operation Dawn, annex entry 06. The Ash gate guards run a small field unit at the north canal crossing: give it the pass phrase and it opens the gate or refuses. We took one. It will not tell you the phrase it is waiting for. Work out the phrase it accepts.
>
> Attachment: `lockbox.zip`
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** `files/lockbox.zip` → `lockbox` (non commité).

## En bref

La vérification à 33 caractères que `main` fait lui-même (« open sesame and mind the tripwire ») est un leurre qui ne fait qu'afficher une moquerie. La vraie vérification s'exécute *avant* `main`, dans une fonction placée dans `.init_array` — un constructeur GCC/glibc, que le chargeur appelle avec les vrais `argc`/`argv` en registres, bien que rien dans le flot de contrôle décompilé ne l'appelle jamais directement. Elle vérifie une phrase de 44 octets avec un chiffrement XOR/ROL/ADD à accumulateur contre une clé intégrée ; inverser ce chiffrement donne la phrase, et la phrase *est* le flag.

## Démarche

**1. Reconnaissance — un petit binaire strippé d'apparence statique avec deux vérifications séparées**

`file` : un petit PIE lié dynamiquement. `strings` montre le texte d'ambiance de la porte (`crossing : NORTH CANAL`, `GATE: pass phrase accepted/refused`, de fausses lignes de journal `0417/0422/0431 open denied`), un blob de 34 caractères qui ressemble à du XOR brouillé, et un second blob plus dense après une étiquette `LOCKBOX1,`. En désassemblant les deux seules vraies fonctions :

- **`main`** (atteint depuis `__libc_start_main`, confirmé via le `lea rdi,[rip+...]` qui s'y résout) distribue `status`/`log`/`open`. Pour `open <phrase>`, il exige `len(phrase) == 33`, XORe chaque octet avec `0x5b` et compare à une table de 33 octets stockée — qui, décodée, donne `"open sesame and mind the tripwire"` — mais en cas de correspondance il se contente d'un `puts("the quartermaster laughs - that is last week's code, soldier")` et **tombe** sur la vraie décision : il lit une globale 32 bits et n'accepte que si elle vaut `0x5a`.
- Une seconde fonction, jamais appelée depuis `main` ni ailleurs dans le désassemblage, implémente sa propre vérification `open <phrase>` (même motif `argv[1]=="open"`/`argv[2]`) sur une phrase de **44 octets** avec un chiffrement à accumulateur, et écrit `0x5a` (succès) ou une autre valeur (échec) dans cette même globale.

Une fonction que rien n'appelle, mais qui contrôle pourtant le résultat de `main` via une globale partagée, c'est la signature d'un **constructeur placé dans `.init_array`** : le code de démarrage de glibc (`__libc_csu_init`) invoque chaque entrée de `.init_array` avec `(argc, argv, envp)` dans `rdi`/`rsi`/`rdx` — la même convention qu'un `main` normal — avant même que `main` ne s'exécute. Vérifier la section le confirme : `.init_array` contient deux pointeurs, `0x1480` (le `frame_dummy` propre à glibc, un simple trampoline `endbr64; jmp`) et `0x10e0` — la fonction « morte ». Elle ne l'est pas ; c'est le vrai gardien.

**2. Hypothèse — inverser le chiffrement à accumulateur plutôt que forcer**

En lisant le constructeur : pour une phrase de 44 octets, avec `esi` (un accumulateur 32 bits courant) initialisé à `0x5b`, `cl` initialisé à `1` et incrémenté de 3 à chaque tour, et une clé de 8 octets `K` qui boucle sur `i & 7` :

```
dl = rol8(phrase[i] ^ (esi & 0xFF), cl) + K[i & 7]      # comparé au chiffré[i]
esi = esi + i + edx                                      # l'octet bas d'edx est chiffré[i] une fois l'octet correct
```

Comme chaque étape est réversible (`rol8`/`ror8` sont inverses l'un de l'autre, `+`/`-` modulo 256 aussi), et que l'évolution de `esi` n'a besoin que de l'octet *chiffré* (pas du clair) une fois qu'on suppose une correspondance, les 44 octets de la phrase se récupèrent en une seule passe avant, dans l'ordre, sans deviner :

```
phrase[i] = (esi & 0xFF) ^ ror8((chiffré[i] - K[i & 7]) & 0xFF, cl)
```

La clé et le chiffré se trouvent dans `.rodata` juste après une étiquette `LOCKBOX1,`, atteinte depuis le constructeur par un simple `lea r11, [rip+disp32]`.

**3. Exploitation — parser l'ELF et inverser, sans exécution nécessaire**

```bash
python3 -I solve/solve.py files/lockbox.zip
```

Le script n'exécute jamais `lockbox` : il lit les en-têtes ELF pour trouver `.init_array`, distingue le vrai constructeur du `frame_dummy` par son prologue (un `jmp` juste après `endbr64` contre un vrai `push rbp`), suit le `lea r11, [rip+disp32]` de ce constructeur pour localiser la clé de 8 octets et le chiffré de 44 octets dans `.rodata`, et inverse le chiffrement octet par octet. La chaîne de 44 caractères récupérée est elle-même le flag — le « annex entry 06 » de l'énoncé correspond au `06` qui y est intégré, une confirmation intégrée.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Une fonction sans référence croisée depuis `main` n'est pas forcément du code mort : toujours vérifier `.init_array`/`.fini_array` (et `.ctors`/`.dtors` sur les chaînes d'outils plus anciennes) avant de l'écarter, surtout quand elle lit une globale qui *est* vérifiée ailleurs.
- Les constructeurs GCC/glibc reçoivent `(argc, argv, envp)` gratuitement via la convention d'appel de `__libc_csu_init` de la plateforme, même si la source C les déclare sans paramètres — une astuce de CTF connue mais facile à manquer dès qu'un `main` paraît « trop simple » pour ce que l'énoncé promet.
- La phrase à 33 caractères que `main` vérifie directement est un leurre complet et crédible (elle a même sa propre récompense en texte d'ambiance) qui ne contribue en rien à la vraie décision d'acceptation — un rappel de tracer *où* le résultat d'une comparaison est utilisé, pas seulement si une comparaison existe.
- Le chiffrement est assez simple (rotation, addition, accumulateur courant) pour être inversé à la main une fois la réversibilité de chaque étape confirmée ; aucune force brute ni recherche de clé n'a été nécessaire.

## Outils & références

- `file`, `strings`, `readelf`, `objdump`, Python 3 (`struct`, `zipfile`)
- `.init_array`/constructeurs ELF et la convention d'appel `(argc, argv, envp)` des constructeurs ; adressage relatif au RIP en x86-64

---
[⬅ Retour à l'événement](../../README.fr.md)
