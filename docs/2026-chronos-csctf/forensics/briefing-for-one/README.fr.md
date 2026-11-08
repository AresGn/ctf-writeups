---
tags: [forensics, windows, lnk, registry, webdav, 7zip]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Briefing for One

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 82 | ✅ | — | non | 0xAr3s-root | Chronos Security |

## Énoncé

> Flood response was under way when an intruder staged a routing package for a single workstation at the fictional Rovenqara Civil Continuity Directorate, which coordinates civil support for coalition forces in Operation Dawn. The shortcut opened, and isolation left regional shelter routing on paper.
>
> Recover the package from the supplied evidence and submit its briefing token. Analyze the files only: do not execute the shortcut or DLL, or contact captured addresses.
>
> Attachment: `briefing-for-one-5f4125fbb77f625d.zip`, 161,346 bytes, SHA-256: `5f4125fbb77f625d85bbdb2d0f5090ed270409a302bd5f15a5f90a43d050cb9a`
>
> Flag format: `CSCTF{32 lowercase hexadecimal characters}`

**Fichiers fournis :** `files/briefing-for-one-5f4125fbb77f625d.zip` (non commité — actuellement dans `forensics/briefing-for-one-5f4125fbb77f625d.zip`)

## En bref

Parser (sans jamais l'ouvrir) le `.lnk` pour récupérer son script PowerShell de staging, lire `MachineGuid` à la racine du hive Cryptography sauvé, recalculer le mot de passe 7-Zip comme `HMAC-SHA-256(binding-key, "csctf26/briefing-for-one/v1" || 0x00 || guid)`, extraire le vrai `route-update.7z` de la capture WebDAV par son hash, le déchiffrer, puis lire le token que la DLL valide statiquement dans `route-table.json`.

## Démarche

**1. Reconnaissance — inventaire, et lire le field guide d'abord**

```bash
sha256sum briefing-for-one-5f4125fbb77f625d.zip  # 5f4125fb…cb9a conforme
unzip -l briefing-for-one-5f4125fbb77f625d.zip
# briefing.lnk (5709)  machine-cryptography.hiv (126976)  egress.pcapng (22876)
# field-guide.md  provenance.json  SHA256SUMS  (tous les SHA256SUMS vérifient)
```

`field-guide.md` + `provenance.json` portent trois avertissements porteurs, tous confirmés ensuite : (a) le hive est une **sous-clé sauvée** (`reg.exe save` de `Cryptography`), donc un lecteur hors ligne présente cette clé comme sa racine — les outils attendant `SOFTWARE\Microsoft\Cryptography\…` ont besoin du chemin racine sauvé ; (b) l'export HTTP Wireshark, le XML DAV et les flux TCP bruts sont des **séquences d'octets différentes** — ne comparer un corps exporté qu'au hash fourni dans l'évidence ; (c) un exemple HMAC travaillé (entrées publiées) fige le traitement exact des octets : UTF-8 sans BOM, un séparateur `0x00`, GUID en minuscules sans accolades/espace/NUL. J'ai vérifié que cet exemple se reproduit (`7dad6991…10d0`) avant d'utiliser la dérivation sur les valeurs du cas.

**2. Hypothèse — le raccourci est tout le script de staging, en clair**

Le parsing statique du StringData du Shell Link (header → IDList → LinkInfo → StringData Unicode ; cible `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`, description « Regional shelter routing update ») donne une `-Command` de 2194 caractères qui, dans l'ordre :

1. Exige un `permit.bin` voisin : existence, 32 octets, SHA-256 épinglé (sinon exit 41/42). `provenance.json` explique le protocole de contrôle — un contrôle négatif sans permis a précédé ce run avec permis — la capture est donc le run sélectionné. Le contenu du permis n'est qu'une porte de lancement ; rien ci-dessous n'en dérive.
2. Lit `MachineGuid` dans `HKLM\SOFTWARE\Microsoft\Cryptography`, valide sa forme et le passe en minuscules.
3. Dérive le mot de passe du package : `$k` = clé de binding décodée Base64 (32 octets, embarquée dans la commande), `$p` = hex minuscule de `HMAC-SHA-256($k, UTF8('csctf26/briefing-for-one/v1' + [char]0 + $g))` — exactement la construction du field guide.
4. Copie `\\briefing.rovenqara.test@80\DavWWWRoot\ops\route-update.7z` (WebDAV ; **jamais contacté** — le même échange est dans `egress.pcapng`), vérifie son SHA-256 épinglé, l'extrait avec `7z x -p$p`, vérifie `route-update.dll` et `route-table.json` contre deux autres hash épinglés, puis `rundll32 …,ApplyRouteTable` et contrôle `route-applied.txt` == `Rovenqara route fixture applied\r\n`.

Le travail hors ligne est donc : hive → GUID, capture → archive, mot de passe → membres, DLL (statique) → règle de validation du token. La racine du hive confirme immédiatement l'étape 2 : clé racine `Cryptography`, unique valeur racine `MachineGuid = 080c7be1-f41c-446c-b961-93bd7bc4ea31` (REG_SZ). Un lecteur NK/VK minimal (offset racine à l'header `0x24`, offsets de cellules relatifs à `0x1000`) l'obtient sans rien monter.

**3. Exploitation — récupérer par hash, déchiffrer, valider statiquement**

Capture : 95 paquets, 8 connexions TCP `192.168.56.20 → 192.168.56.10:80` (`OPTIONS`, plusieurs `PROPFIND`, un `GET /ops/route-update.7z`). `tshark --export-objects http,…` produit 7 objets — dont 6 sont du XML DAV (881–914 octets), trois *nommés* `route-update*.7z`. Seul le corps `GET` 200 `application/octet-stream` (5359 octets) hashe vers la valeur épinglée dans le raccourci (`d29a0679…e4c2`). C'est le hash, pas le nom de fichier, qui sélectionne le package — exactement le piège du field guide.

```bash
# mot de passe = HMAC ci-dessus sur le GUID du cas (le solveur le recalcule depuis le .lnk)
7z x -p"$PASSWORD" -oroute_out route-update.7z   # lecteur d'archive uniquement
sha256sum route-update.dll route-table.json               # les deux matchent les épingles du .lnk
```

Membres : `route-table.json` (192 octets) et `route-update.dll` (PE32+ x86-64, 13 824 octets). La DLL n'a été examinée que **statiquement** (`pefile`/`objdump`, jamais chargée) : unique export `ApplyRouteTable` (RVA `0x137f`), imports `GetModuleFileNameW/CreateFileW/GetFileSize/ReadFile/WriteFile`. Le désassemblage montre qu'elle construit le chemin voisin `route-table.json`, exige `GetFileSize == 0xC0` (192), `strncmp` un préfixe de 36 octets (`0x24`) `{"schema":1,"briefing_token":"CSCTF{` et le suffixe routes de 124 octets (`0x7c`) à l'offset `0x44`, puis boucle sur les octets 36…67 en n'acceptant que `[0-9]`/`[a-f]` — soit exactement 32 caractères hex minuscules — avant d'écrire `route-applied.txt`. La DLL n'embarque que préfixe/suffixe, jamais le token lui-même : le token vit donc bien dans le JSON récupéré, entre les deux :

```bash
python3 solve/solve.py ../briefing-for-one-5f4125fbb77f625d.zip
# [*] Example OK   : 7dad69912b67470da7713c666337135b568030605bc2e88f99524596366d10d0
# [*] LNK command  : 2194 chars (powershell.exe, static)
# [*] MachineGuid  : 080c7be1-f41c-446c-b961-93bd7bc4ea31 (hive root = Cryptography)
# [*] GET body     : 5359 bytes, sha256=d29a0679… (matches the .lnk pin)
# [*] Member hashes match the LNK expectations
# [+] FLAG         : CSCTF{...}
```

Le solveur n'utilise que la stdlib en dehors du binaire `7z` (parsers LNK, hive NK/VK, pcapng/TCP et HTTP maison ; chaque constante est extraite de l'évidence) et n'exécute ni le raccourci ni la DLL.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (masqué)

## Ce que j'ai appris

- Traiter le `.lnk` comme un document, pas comme un lanceur : le StringData du Shell Link contenait tout le script d'intrusion — clé, dérivation, URL et les trois hash d'acceptation — sans aucun besoin d'exécution.
- Chaque étape a son hash d'acceptation indépendant (archive, DLL, JSON). Les utiliser sépare le vrai package de 5359 octets des trois exports XML DAV homonymes ; les seuls noms de fichiers n'auraient rien déchiffré.
- Les hives de sous-clé sauvée inversent l'attente habituelle de chemin : `MachineGuid` est à la *racine* de ce fichier. Vérifier d'abord le nom de la clé racine (`Cryptography`) évite de chercher une hiérarchie `SOFTWARE\…` absente.
- La validation statique de la DLL coupe dans les deux sens : le désassemblage (taille 192, compares préfixe/suffixe, boucle `[0-9a-f]{32}`) prouve que le token JSON est la soumission attendue et qu'aucun second token caché n'est généré à l'exécution.

## Outils et références

- Python 3 stdlib (`struct`, `hashlib`, `hmac`, `zipfile`) + `7z` (lecteur d'archive chiffrée uniquement)
- Wireshark / `tshark --export-objects http` et `capinfos` (contre-vérifications de reconnaissance)
- `pefile`, `objdump` (triage PE statique/désassemblage — DLL jamais exécutée)
- StringData Shell Link Windows, cellules NK/VK de hive registre, WebDAV (`PROPFIND`/`GET`) sur HTTP

---
[⬅ Retour à l'événement](../../README.fr.md)
