---
tags: [forensics, xattr, journald, hmac, xor]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# capability-ghost

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 120 | 106 | ✅ | — | 0xAr3s-root | Mohamed Amine Mzoughi |

## Énoncé

> A hostile-state campaign targeted the build runner for the software that drives signals on railways carrying coalition freight toward the Operation Dawn front. Responders kept the runner's filesystem archive and journal.
>
> Recover the sealed marker from them. Inspect the records as data: do not run the supplied programs or restore their capabilities. Linux tools or WSL are enough, and you do not need root. This is a constructed forensic exercise, not evidence of an actual compromise.
>
> Attachment: `capability-ghost.zip`, 51,023 bytes, SHA-256 `c53a83833466cc4db34336ab9e333a0e317cd48da43932953df89cacb9c31ffe`.
>
> Submit the complete recovered `CSCTF{...}` value. Flag format: `CSCTF{...}`

**Fichiers fournis :** `files/runner-fs.tar.gz`, `files/runner.journal`, `files/README_FOR_RESPONDERS.md`, `files/manifest.sha256` (non commités).

## En bref

`/etc/solunet/signaling-cfg.sealed` est XORé avec une clé que `hc-probe` dérive en `HMAC-SHA256(tag, epoch)` : le tag est l'xattr `user.build_seal` conservé dans les en-têtes PAX du tar, l'epoch est le champ `X_SEAL_EPOCH` du journal ; recalculer la clé hors ligne déchiffre le marqueur → flag.

## Démarche

**1. Reconnaissance — un tar avec xattrs, un journal et une config détruite**

`runner-fs.tar.gz` contient une petite arborescence : `/etc/solunet/signaling-cfg.sealed` (27 octets), `/usr/local/bin/hc-probe`, `backup-sync`, `ping`, une unité `hc-probe.service` et `/root/.bash_history`. L'historique raconte la scène : `setcap` sur `hc-probe`, un `TAG` aléatoire, `setfattr -n user.build_seal`, un `EPOCH=$(date +%s)`, puis `hc-probe --seal "$TAG" "$EPOCH" signaling-cfg signaling-cfg.sealed` et `shred -u` du clair. Le clair est donc perdu ; la seule voie est d'inverser le scellement avec le bon tag et la bonne epoch.

Les xattrs ne sont pas appliqués à l'extraction (pas de root), mais ils sont stockés dans les en-têtes PAX étendus en `SCHILY.xattr.*`. Le `tarfile` de Python les expose dans `pax_headers` :

```python
import tarfile
for m in tarfile.open("files/runner-fs.tar.gz"):
    print(m.name, m.pax_headers)
```

`hc-probe` porte `security.capability` et `user.build_seal` = `50 9d f6 cd 8e 10 3f a5` (8 octets bruts ; `tarfile` l'affiche comme une chaîne UTF-8 avec échappements surrogate, donc je ré-encode en `surrogateescape` pour retrouver les octets). `backup-sync` a un `user.sync_id` et `ping` une capability, mais c'est du bruit.

**2. Hypothèse — le binaire documente son propre schéma ; l'epoch est dans le journal**

Je n'ai pas exécuté `hc-probe`. Un `strings` suffit : son aide indique que `--seal` et `--unseal` sont la même opération, un XOR à clé répétée avec `key = HMAC-SHA256(key = octets_bruts(tag_hex), msg = décimal_ascii(seal_epoch))`, `out[i] = in[i] XOR key[i mod 32]`. Il précise aussi d'où vient l'epoch : le champ `X_SEAL_EPOCH` de l'entrée de journal de ce run, **pas** l'horodatage de l'entrée elle-même.

```bash
journalctl --file=files/runner.journal --no-pager -o json
```

L'entrée 5 (`hc-probe`, « health probe sealed result written ») a `X_SEAL_EPOCH=1793294042`, alors que son `__REALTIME_TIMESTAMP` donne 1793294054 — 12 s plus tard : c'est le piège. Deux autres pièges sur le tag : le `TAG` de `.bash_history` n'est qu'une variable du shell d'origine (aléatoire, non enregistrée), et la commande shell stockait l'xattr sous forme de chaîne ASCII `0x…`, alors que l'archive contient les octets bruts ; c'est l'xattr de l'archive qui fait foi.

**3. Exploitation — recalculer la clé hors ligne et XORer**

```bash
python3 -I solve/solve.py files
```

Le script lit le tag dans les en-têtes PAX, l'epoch dans le journal (via `journalctl --file`), dérive la clé et XORe le fichier scellé. Un mauvais tag ou une mauvaise epoch donnerait des octets aléatoires ; ici la sortie commence par `CSCTF{` et est imprimable, ce qui confirme les deux valeurs.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Les métadonnées d'archive (xattrs PAX) sont une preuve à part entière : un simple `tar -x` en non-root les perd silencieusement, il faut donc lire les en-têtes.
- Quand un outil documente son propre schéma, lire les strings du binaire avant tout ; ici il signalait aussi le piège de l'epoch (champ du journal vs. heure de l'entrée).
- Un déchiffrement correct se valide lui-même (sortie imprimable avec le préfixe `CSCTF{`), un bon contrôle quand plusieurs entrées candidates existent.
- Rien n'a été exécuté, extrait en root ni restauré : toute la résolution est de l'analyse de données.

## Outils & références

- `journalctl --file=… -o json`, `strings`, Python 3 (`tarfile`, `hmac`, `hashlib`)
- xattrs Linux / file capabilities (`security.capability`), en-têtes PAX `SCHILY.xattr.*`, champs personnalisés du journal systemd

---
[⬅ Retour à l'événement](../../README.fr.md)
