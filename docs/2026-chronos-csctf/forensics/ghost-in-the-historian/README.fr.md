---
tags: [forensics, ext4, ransomware, carving, xorshift]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Ghost in the Historian

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 107 | ✅ | — | non | 0xAr3s-root | Mohamed Amine Mzoughi |

## Énoncé

> A campaign against the electricity supply encrypted a substation historian's configuration and deleted the encryptor. The substation feeds a partner nation's grid on the coalition side of Operation Dawn.
>
> Recover the original configuration's `SAFETY_INTERLOCK_TOKEN` and submit its complete `CSCTF{...}` value. The volume was constructed for this exercise and is not an untouched acquisition; the included brief explains its timeline. Analyze recovered programs as data: do not execute them or mount the image.
>
> Attachment: `ghost-in-the-historian.zip`, 72,560 bytes, SHA-256 `5edaea927aa93db3286f771dd77c8c41e0c23c6eafa70ac2182da5bd9ac56ce9`

**Fichiers fournis :** `files/ghost-in-the-historian.zip` (non commité — actuellement dans `network/ghost-in-the-historian.zip`)

## En bref

Carver le `historian_enc` ELF supprimé depuis l'espace non alloué, lire son désassemblage comme des données (flot xorshift32, graine `(time() ^ getpid()) × 0x9E3779B1`, PID issu de sa propre ligne syslog), brute-forcer les secondes autour du sweep de 04:13, puis déchiffrer en chaîne les trois configs `.enc` — le fichier topologie contient le token.

## Démarche

**1. Reconnaissance — un petit monde ext4 avec trois fichiers verrouillés**

Le ZIP se vérifie (`5edaea92…56ce9`) et contient un descripteur VMDK plus une extent flat de 64 Mio (`evidence-flat.vmdk`, 131072 secteurs, `manifest.sha256` couvre les trois fichiers). `debugfs` en lecture seule, jamais de montage :

```bash
debugfs -R "ls -l /" evidence-flat.vmdk
# /var/historian → node_status.json.enc (74 o), grid_topology.cfg.enc (235 o),
#                  historian_cache.dat.enc (64 o), tous datés 2-oct-2026 05:13
# /var/log/historian.log → une ligne : 2026-10-02 04:13 historian_enc[2764964] :
#                          starting encryption sweep, target_dir=/var/historian
```

Le brief README est explicite sur les deux horloges (filesystem construit le 29 oct., enregistrements d'incident du 2 oct. — chacun vaut ce qu'il dit) et les règles d'engagement : les programmes récupérés sont des données. `lsdel` ne trouve aucun inode supprimé et le journal est une transaction vide, mais `strings` sur l'extent brute révèle la suite : une note de rançon (« Contact ref: 7F3A-RECOVERY (this is NOT a decryption key) », wallet d'affichage) et, juste à côté, un second programme complet — imports libc (`scandir`, `fwrite`, `unlink`, `utime`, `getpid`), formats de chemins (`%s/%s`, `%s.enc`, `rb`/`wb`) et le format exact du log ci-dessus. Un seul ELF (`7fELF`) à l'offset `0xa1c000` ; carvé via ses section headers (`0x3888` octets, BuildID intact), c'est l'encryptor supprimé. La chaîne `@z3uAF2` à proximité n'est que des octets de chiffré de `grid_topology.cfg.enc`, pas une clé — un leurre naturel.

**2. Hypothèse — le binaire documente son propre key schedule**

Le désassemblage `.text` (strippé, ~1,2 Kio — lu, jamais exécuté) est un sweep linéaire : `scandir`, saut des dotfiles, saut des non-fichiers, `fopen(rb)` → `ftell`/`fread`, chiffrement, `fopen(wb)` vers `%s.enc`, `utime` (d'où les mtimes uniformes du 2 oct.), `unlink` de l'original. Le chiffrement est un xorshift32 de manuel (shifts 13/17/5, octets little-endian, état frais par bloc de 4 octets) :

```
seed = 0xa5a5a5a5; t = time(); pid = getpid()
if (t != pid) seed = (t ^ pid) * 0x9E3779B1   (mod 2^32)
état conservé d'un fichier à l'autre (resauvegardé après chacun)
```

Les inconnues sont donc exactement deux : les secondes de graine `t` et l'ordre des fichiers (l'ordre scandir décide qui reçoit l'état de graine). La ligne de log écrite par le binaire lui-même donne les deux ancres : le PID `2764964` verbatim, et la minute du sweep `04:13` bornant `t` — brute-forcer les 86400 secondes du jour, et la config qui se déchiffre depuis l'état de graine doit être de l'ASCII imprimable commençant par `#`.

**3. Exploitation — un jour de secondes, puis suivre la chaîne**

```bash
python3 solve/solve.py ../ghost-in-the-historian.zip
# [*] Sweep log     : 2026-10-02 04:13 historian_enc[2764964]
# [*] Seed time     : 2026-10-02 04:13:05+00:00 (t=1790914385) seed=0x40d8e565
# [*] Chain order   : grid_topology.cfg.enc -> historian_cache.dat.enc
#                     -> node_status.json.enc
# [+] FLAG            : CSCTF{...}
```

`t = 04:13:05` (cinq secondes dans la minute loggée — exactement ce que prédit le double appel `time()`) déchiffre `grid_topology.cfg.enc` directement depuis l'état de graine vers sa config, dont `SAFETY_INTERLOCK_TOKEN=flag{...}`. Enchaîner l'état survivant (`235 o → 59 états`) déchiffre `historian_cache.dat` (CSV de pressions `04:11Z/04:12Z`) puis `node_status.json` (JSON valide, `MGA-HIST-07`, `nominal`) ; l'ordre inverse échoue l'imprimabilité, confirmant `grid → cache → node`. Mon premier sweep du jour entier avec un seuil conjoint sur 3 fichiers n'a rien trouvé — à juste titre, car seul le premier fichier dans l'ordre scandir se valide depuis la graine ; scorer le fichier grid seul touche à 235/235 imprimables au premier passage (~5 s).

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (masqué)

## Ce que j'ai appris

- Analyser-comme-données fonctionne : imports + rodata (`%s.enc`, `rb`/`wb`, le format de log) esquissent déjà le programme avant tout désassemblage, et le `.text` de 1,2 Kio confirme schedule de graine, chaînage, clonage de timestamps et suppression en une lecture.
- Le PID-dans-le-log est le raccourci voulu — le binaire loggue son propre `getpid()` en `%d`, réduisant la recherche de graine à une dimension (les secondes d'un jour). Sans lui, l'espace conjoint `(t, pid)` resterait brute-forçable mais bien plus laid.
- Le sweep à seuil conjoint qui a échoué était instructif, pas perdu : le report d'état fait qu'un seul fichier se valide depuis la graine, donc scorer par fichier avec une seconde étape de chaînage est la bonne forme — et l'ordre qui échoue l'imprimabilité est lui-même une preuve de l'ordre qui réussit.

## Outils et références

- Python 3 stdlib (`struct`, `hashlib`, `zipfile`) + `debugfs` (dumps lecture seule, `lsdel`, `logdump`)
- `strings`, `objdump -d -M intel` (triage statique/désassemblage — binaire jamais exécuté)
- Extent flat ext4 en VMDK monolithicFlat ; xorshift32 (shifts Marsaglia 13/17/5) ; ligne syslog comme oracle de PID

---
[⬅ Retour à l'événement](../../README.fr.md)
