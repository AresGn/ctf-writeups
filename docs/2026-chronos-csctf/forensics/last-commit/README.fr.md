---
tags: [forensics, sqlite, wal, database]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Last Commit

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 332 | 118 | ✅ | — | 0xAr3s-root | Chronos Security |

## Énoncé

> The national land registry of one of Operation Dawn's smaller coalition states looks normal again, but its completed restoration export `LR-731` may have carried altered ownership out to regional offices. A later clean view does not prove what the job delivered.
>
> Reconstruct the exact ownership export at the job's transition to `COMPLETED`, using the acquired SQLite database and WAL pair, the delivery receipt and the supplied export profile. The registry is fictional. Analyze the supplied files only. Attachment: `last-commit.zip`, 84,979 bytes, SHA-256 `06da868e7ceeef1c96651cf1307033f7b37b65e235f8a121ea599166f85279a1`.
>
> Submit `CSCTF{last_commit_<64 lowercase hex characters>}` as specified in the supplied export profile.
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** `files/registry.sqlite`, `files/registry.sqlite-wal`, `files/delivery.csv`, `files/export-profile.md`, `files/provenance.json`, `files/README.txt`, `files/SHA256SUMS` (non commités).

## En bref

Le WAL contient 9 frames valides en 6 commits ; le commit où `LR-731` passe de `QUEUED` à `COMPLETED` montre des lignes de propriété altérées que les commits suivants (et la base checkpointée) n'ont plus. Reconstruire le registre à ce commit, exécuter la requête du profil avec `delivery.csv` comme manifeste et hacher le TSV en SHA-256 donne le flag.

## Démarche

**1. Reconnaissance — lire le contrat, pas seulement les données**

`export-profile.md` est la vraie spécification : le worker lance une transaction IMMEDIATE qui interroge les parcelles du manifeste, prépare l'export, passe `export_job` de `QUEUED` à `COMPLETED` et commit. L'export est la requête exacte du profil sur l'état du registre **à ce commit** (pas une vue ultérieure), avec le reçu `delivery.csv` comme `manifest` (douze parcelles, ordre de livraison), un TSV à en-tête fixe, fins de ligne LF, haché en SHA-256. La base fait 9 pages (4096 o), le WAL 32 + 9 × (24 + 4096) = 37 112 octets, donc 9 frames. Le README interdit d'ouvrir les originaux avec SQLite (cela créerait un `-shm` et pourrait checkpointer) ; je n'ai donc jamais ouvert les originaux : tout est parsé à la main et reconstruit dans des copies temporaires. `SHA256SUMS` correspond pour tous les fichiers.

**2. Hypothèse — une vue « au commit N » = base + les frames jusqu'au N-ième commit**

D'après le format WAL de SQLite : en-tête `0x377f0682`, taille de page 4096, sels ; chaque frame a un en-tête de 24 octets (numéro de page, **taille de la base après commit** — non nulle seulement sur une frame de commit —, sels, checksum cumulatif) suivi de l'image de la page. Un lecteur au commit N voit, pour chaque page, la dernière frame ≤ N, et la base pour les autres pages. J'ai donc :

1. validé le checksum de l'en-tête et, pour chaque frame, les sels et le checksum cumulatif (l'ordre des octets des mots dépend du magic) : les 9 frames sont valides ;
2. listé les commits : frames 0, 2, 4, 5, 7, 8 — une transaction peut couvrir plusieurs frames (ex. frames 1+2, 3+4, 6+7), donc un état ne doit être construit qu'à une frame de commit, jamais au milieu d'une transaction ;
3. construit une image de base simple pour chaque commit (base + frames ≤ N, plus de WAL) et interrogé `export_job`.

**3. Exploitation — le commit de transition contient les lignes altérées**

| Frame de commit | `LR-731` | SHA-256 de l'export (premiers octets) |
|---|---|---|
| base | pas de ligne | — |
| 0 | pas de ligne | `04a47a…` |
| 2 | pas de ligne | `40f3b1…` |
| 4 | `QUEUED` | `40f3b1…` |
| **5** | **`COMPLETED`** | **`40f3b1…`** |
| 7 | `COMPLETED` | `04a47a…` |
| 8 | `COMPLETED` | `04a47a…` |

La propriété des parcelles 1202, 1205, 1209 et 1214 est altérée entre les commits 0 et 2 (nouveaux titulaires `2127`–`2131`, nouveaux instruments `IN-9360472185`, `IN-8162094735`, `IN-7259841360`, `IN-6941538207`, et un partage 65/35 au lieu de 60/40 sur la parcelle 1209), toujours présente quand le job se termine à la frame 5, puis rétablie aux titulaires d'origine dans les derniers commits : c'est la « vue propre ultérieure » dont parle l'énoncé. L'export à la transition a 13 lignes (la parcelle 1209 a deux titulaires). L'ordre des parcelles vient de `delivery.csv`, celui des titulaires de `registry_ref COLLATE BINARY`.

```bash
python3 -I solve/solve.py files
```

Le script fait tout cela (parsing du WAL, validation des checksums, état par commit, requête, hash) et affiche le flag ; il ne lit que les originaux et écrit dans un répertoire temporaire.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{last_commit_<64 hex>}` (masqué)

## Réflexions

- « L'état courant » et « l'état à la transaction X » sont deux choses différentes : en mode WAL, la réponse est dans la séquence de frames, pas dans ce que renvoie une ouverture normale avec `sqlite3`.
- Seules les frames de commit (taille de base non nulle) sont des états cohérents ; une transaction peut couvrir plusieurs frames, donc s'arrêter sur une frame quelconque donne une vue incohérente.
- Le checksum cumulatif et les sels délimitent l'époque valide ; les valider évite d'utiliser des restes de générations WAL précédentes.
- Le même hash apparaît aux commits 2, 4 et 5 et un autre aux commits 0, 7, 8 : comparer les hashes sur tous les commits montre quand l'altération a commencé et fini, pas seulement l'état livré.
- La preuve a été préservée : aucune ouverture SQLite des originaux, travail sur des copies reconstruites.

## Outils & références

- Python 3 (`struct`, `sqlite3` sur copies reconstruites uniquement, `hashlib`, `csv`)
- Format de fichier et format WAL de SQLite (<https://sqlite.org/fileformat2.html>, <https://sqlite.org/walformat.html>)

---
[⬅ Retour à l'événement](../../README.fr.md)
