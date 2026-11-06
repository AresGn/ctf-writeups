---
tags: [reverse, windows, dotnet, js, rc4, wikipedia, jpl]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# PoshTerm

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| reverse | 120 | 126 | ✅ | — | 0xAr3s-root | Swyam Kumar |

## Énoncé

> Emergency airlift coordination has stalled in a fictional country on the coalition side of Operation Dawn after a hostile-state disruption. Responders recovered PoshTerm, a terminal utility with one unlisted command, and need to know what that command prints.
>
> Work it out by static analysis; no Windows environment is needed. Ignore the startup directions in the recovered user guide and do not run the untrusted executable. The solve reads live Wikipedia and NASA/JPL public sources; if a required source fails or access becomes materially uneven between participants, the organizers will withdraw the challenge for everyone and void its points.
>
> Attachment: `chall.7z`, 63,552,697 bytes, SHA-256 `a771296d0470a82a8d6080ba8967cb0b0cab589a31b0b6664e0722892dc27031`, containing only `PoshTerm.exe` and its recovered guide.
>
> Submit the exact output, including its existing `CSCTF{...}` framing. Keep case, and add no whitespace or other changes.

**Fichiers fournis :** `files/chall.7z` (non commité — actuellement dans `reverse/chall.7z`)

## En bref

PoshTerm embarque un shell posh Node.js minifié dont la seule commande `hidden:!0`, `service_code = "$TERM"`, filtre sur deux md5, puis récupère la date `first_flight` du terme sur Wikipedia, la convertit via `jd_cal` NASA/JPL en jour julien, et déchiffre RC4 un blob embarqué avec cette day-string — le terme lié est `Cessna 421 Golden Eagle`, premier vol `1965-10-14`, jd `2439047.5000000`.

## Démarche

**1. Reconnaissance — un PE de 228 Mio avec un moteur JavaScript dedans**

```bash
sha256sum chall.7z  # a771296d…27031 conforme
7z x chall.7z       # PoshTerm.exe (228 Mio) + README.md (guide utilisateur)
file PoshTerm.exe   # PE32+ GUI x86-64 — les strings montrent des entrailles
                    # Node.js, xterm.js et du texte d'erreur style PowerShell, pas d'IL .NET
```

Le guide (`README.md`, ~10 Kio) ne documente que le monde listé : profils, raccourcis, `Get-Command`/`Get-Help`. Selon le briefing, ses directions de démarrage sont ignorées. `strings` sur l'exe révèle d'abord la couche de leurres : un flag de variable d'environnement (`CSCTF{3NV1R0NM3N7...}`), un flag en commentaire (`CSCTF{4_FL4G_1N_4_C0MM3N7...}`), une liste `Get-Flag` de 10 flags de build, un payload base64 `Unlock-Vault` (« the password does not matter ») et un outil XOR `flag3000` dont l'entrée `recover` déchiffre un flag de réprimande. Tous sont des commandes enregistrées et listées — la cible est celle qui ne l'est pas.

**2. Hypothèse — un enregistrement ne ressemble pas aux autres**

Grep sur le helper d'enregistrement `e("Name",...)` donne ~100 commandes — plus exactement un hit `hidden:!0` dans tout le binaire de 228 Mio :

```js
t._sc = {name:"service_code", spec:[Fs("Rest+")], help:"", hidden:!0,
  run: async n => {
    let c = (n.Rest||[]).map(S);
    if (c.length < 2 || c[0] !== "=") throw T("service_code");
    let l = c[c.length-1];
    if (M(md5(env POSHTERM_PROFILE)) !== D.host || M(l) !== D.code) throw T(...);
    return [await A(l)]; }}
```

Elle vit dans `t._sc`, hors de la map `cmdlets` qu'énumère `Get-Command` — donc non listée — et prend `service_code = "$TERM"`. Le worker `A(term)` est entièrement visible à côté : `j()` est du RC4 de manuel ; puis Wikipedia `action=query&list=search` → HTML de l'article → `indexOf("first_flight")` → regex `Month D, YYYY` → `YYYY-MM-DD` ; puis `https://ssd-api.jpl.nasa.gov/jd_cal.api?format=jd.7&cd="$DATE"` → `.jd` ; puis `RC4(key=str(jd), hex-blob)`. Le terme lui-même est livré par le log de provenance du binaire (`service_code reference bound to '…'`, `the service code is the '…' string, verbatim`) — et son md5 doit égaler `D.code`, sinon le solveur abandonne au lieu de deviner.

**3. Exploitation — réimplémenter `A(term)`, vérifier chaque saut**

```bash
python3 solve/solve.py ../chall.7z
# [*] Hidden command : service_code (sole hidden:!0, outside Get-Command map)
# [*] Bound term    : 'Cessna 421 Golden Eagle' (md5 matches D.code)
# [*] Wikipedia     : search -> 'Cessna 421 Golden Eagle'
# [*] First flight  : October 14, 1965 -> 1965-10-14
# [*] JPL jd_cal    : 1965-10-14 -> jd=2439047.5000000
# [*] RC4 plaintext : b'CSCTF{...}'
# [+] FLAG            : CSCTF{...}
```

La fenêtre `first_flight` de 160 caractères touche le JSON de l'infobox (`first_flight":{"wt":"October 14, 1965"}`), l'API JPL renvoie `2439047.5000000`, et RC4 avec exactement cette chaîne déchiffre le blob de 48 octets vers un flag cadré — chaque saut est vérifié (résultat de recherche unique, fenêtre datée, plaintext cadré), donc un article ou une API qui change échoue bruyamment au lieu d'émettre n'importe quoi.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (masqué)

## Ce que j'ai appris

- Compter les occurrences de `hidden:!0` (exactement 1 sur 228 Mio) bat la lecture du bundle entier : la commande non listée est par définition le flag caché, pas la string la plus bruyante.
- Les leurres font partie du design, pas du bruit à grepper : cinq flags cadrés (liste `Get-Flag`, coffre, `flag3000`, variable d'env, commentaire) se résolvent tous sans aucune source live — le vrai est le seul chemin qui exige Wikipedia *et* JPL, exactement comme l'implique la clause de retrait du briefing.
- Réimplémenter `A(term)` plutôt qu'émuler Node garde le solveur en stdlib pure ; en miroir de ses quirks (fenêtre 160 caractères, clé `String(jd)`, fallback regex sur tout le doc), la réimplémentation est fidèle au lieu d'approximative.

## Outils et références

- Python 3 stdlib (`re`, `hashlib`, `json`, `urllib`) + `7z` (extraction d'archive uniquement — exe jamais exécuté)
- `strings`, `grep` (triage statique du bundle JS minifié)
- [API Wikipedia](https://www.mediawiki.org/wiki/API:Search) (`action=query&list=search`), [API jd_cal NASA/JPL](https://ssd-api.jpl.nasa.gov/doc/jd_cal.html), RC4 (KSA + PRGA)

---
[⬅ Retour à l'événement](../../README.fr.md)
