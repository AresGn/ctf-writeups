---
tags: [forensics, vim, swap-file, base64]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Last Buffer

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 119 | ✅ | — | non | 0xAr3s-root | Chronos Security |

## Énoncé

> An endpoint collector held on to two Vim recovery files for the same incident note: a periodic snapshot and the one grabbed when the shell dropped. Both restore cleanly, but only one came from the shell that died during the response window. The other is an earlier drill revision.
>
> Recover both, work out which one came from the shell that mattered, and return its encoded read-back proof.
>
> Flag format: `CSCTF{message}`

**Fichiers fournis :** `files/last-buffer-handout.zip` → `incident-2026-10-07.md`, `incident-2026-10-07.md.swp`, `incident-2026-10-07.md.swo`, `audit-timeline.jsonl`, `shell-journal.jsonl`, `case-context.json`, `vim-swap-layout.md` (non commités).

## En bref

Les deux swaps contiennent une ligne `authorization_b64`, mais seul le `.swp` (PID 8442, pts/4) vient du shell tué par SIGHUP dans la fenêtre de crash et dont le SHA-256 du fichier de base correspond à la note sauvegardée ; sa preuve en base64url se décode en flag, alors que le `.swo` (PID 8124) se décode en leurre.

## Démarche

**1. Reconnaissance — deux swaps, une note sauvegardée et trois fichiers de contexte**

`file` identifie les deux swaps comme des fichiers swap Vim 9.0 pour `/home/opnight/incident-2026-10-07.md` (utilisateur `opnight`, hôte `noc-jump-1`), avec le PID 8442 pour le `.swp` et 8124 pour le `.swo`. Les fichiers de contexte donnent la chronologie :

- `case-context.json` : fenêtre de crash `02:19:30Z`–`02:20:00Z`, tty cible `pts/4` ;
- `audit-timeline.jsonl` : le PID 8124 (pts/7) est un snapshot périodique et sort en `success` à 02:12:18Z ; le PID 8442 (pts/4) a un `ANOM_ABEND` `SIGHUP` à 02:19:46Z, puis un snapshot `disconnect-capture` ;
- `shell-journal.jsonl` : le PID 8442 a lancé `sha256sum incident-2026-10-07.md` à 02:18:31Z → `01c2a034…c849`, puis `session_disconnect` sur pts/4.

`strings` sur les deux swaps montre déjà le texte de la note, avec une ligne `revision_id`, `status`, `base_file_sha256` et `authorization_b64` chacun (`vim-swap-layout.md` explique la structure : bloc d'en-tête `b0`, blocs de données `0x6461`, lignes terminées par NUL).

**2. Hypothèse — identifier le swap par le processus, pas par le nom ni le contenu**

Plusieurs signaux sont possibles, mais seuls certains sont fiables :

- les noms sont interchangeables (le collecteur a retiré le point initial) et les deux se restaurent proprement, donc une restauration réussie ne prouve rien ;
- le PID de l'en-tête du swap relie chaque fichier à un processus : 8124 (`.swo`) vs 8442 (`.swp`) ;
- le journal d'audit dit que le shell mort dans la fenêtre sur le tty cible est 8442 ; 8124 était sorti normalement 7 minutes plus tôt ;
- le `base_file_sha256` du swap doit égaler le SHA-256 de la note sauvegardée, et le journal du shell confirme ce hash pour 8442 :

```bash
sha256sum files/incident-2026-10-07.md
# 01c2a034f1a47e4cb5536d66394c4774a1f1c568ff4e34c0de7f654aa42bc849  <- base_file_sha256 du .swp
```

Le `.swo` a `base_file_sha256 = a5bcac6d…`, `revision_id: INC-4471/R16-DRILL` et `status: PERIODIC-SNAPSHOT` (la révision d'exercice antérieure), alors que le `.swp` a `revision_id: INC-4471/R18` et `status: UNSAVED-AT-DISCONNECT`, une étape au-delà du `R17` sauvegardé. Tout désigne le `.swp`.

**3. Exploitation — décoder la preuve du bon swap**

Le `.swp` contient `authorization_encoding: base64url` et une valeur `authorization_b64` ; le leurre se décode en `retired-training-readback-16`, signe clair que c'est l'exercice. Le script parse directement les blocs de données (sans Vim), sélectionne le swap par PID/fenêtre de crash et hash de base, et décode le base64url :

```bash
python3 -I solve/solve.py files
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Deux artefacts qui « se restaurent proprement » se distinguent avec les preuves autour : PID, TTY, chronologie et hashes, pas le contenu seul.
- Le hash du fichier de base relie un swap à la version sauvegardée exacte qu'il éditait, et le journal du shell enregistre ce hash indépendamment : un recoupement peu coûteux.
- Le padding base64 est souvent retiré en base64url ; compléter avant de décoder (`b + "=" * (-len(b) % 4)`).
- J'ai parsé le format swap directement plutôt que lancer `vim -r`, ce qui évite de toucher à la preuve et les effets de bord de la récupération.

## Outils & références

- `file`, `strings`, `sha256sum`, `base64`, Python 3 (`struct`, `hashlib`, `json`)
- Format de fichier swap Vim (bloc 0 `b0`, blocs de données `0x6461`), RFC 4648 base64url

---
[⬅ Retour à l'événement](../../README.fr.md)
