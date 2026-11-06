#!/usr/bin/env python3
"""
CSCTF 2026 - Code Red Freight (forensics/medium)
Identify the adversary device, the leaking inbox rule and the
download count from sanitized Entra/Purview-style exports.

Findings (all derived from the evidence, never hardcoded):
  - Attacker IP 203.0.113.77 (Montreal) vs dispatcher 198.51.100.24.
  - Device-code phishing -> device registration of D3VC0DE-R3L4Y
    (DeviceId 95caec44-c8af-4786-976c-73bd33d9d143, Azure AD joined)
    at 2026-10-29T15:05, the same DeviceId present on every
    attacker session and on the malicious inbox rule.
  - Benign baseline: R3M0TE-W0RK-PC joined 2026-10-28 from the
    dispatcher's own IP; benign inbox rule "Newsletters"
    (MoveToFolder) from the dispatcher's IP/session.
  - Malicious inbox rule M4N1F3ST-L3AK (ForwardTo ragubarden@proton.me)
    created 2026-10-29T15:28:57 from the attacker IP:port with the
    attacker DeviceId.
  - 4 FileDownloaded events, all from the attacker IP.

Flag: CSCTF{device_rule_count} (parts derived from the evidence)

Usage:
    python3 solve.py [code_red_freight.zip | extracted-dir]
"""

import csv
import json
import os
import sys
import zipfile

LOGS = (
    "code_red_freight/logs/AuditLogs_2026-10-29-Patti_Fernandez.csv",
    "code_red_freight/logs/InteractiveSignIns_2026-10-28_2026-10-29.csv",
    "code_red_freight/logs/NonInteractiveSignIns_2026-10-28_2026-10-29.csv",
    "code_red_freight/logs/UnifiedAuditLog_Patti.csv",
)


def load_logs(argv):
    candidates = []
    if len(argv) > 1:
        candidates.append(argv[1])
    candidates += [
        "files/code_red_freight.zip",
        "../code_red_freight.zip",
        "docs/2026-chronos-csctf/forensics/code_red_freight.zip",
        "/tmp/opencode/codered/code_red_freight",
    ]
    for path in candidates:
        if not path:
            continue
        if os.path.isdir(path):
            variants = [LOGS, tuple(n.split("/", 1)[1] for n in LOGS)]
            for names in variants:
                files = {os.path.basename(n): os.path.join(path, n)
                         for n in names}
                if all(os.path.isfile(p) for p in files.values()):
                    print(f"[*] Loading directory {path}")
                    return {k: open(v, encoding="utf-8-sig").read()
                            for k, v in files.items()}
        elif os.path.isfile(path) and path.lower().endswith(".zip"):
            print(f"[*] Loading {path}")
            out = {}
            with zipfile.ZipFile(path) as zf:
                for name in LOGS:
                    out[os.path.basename(name)] = zf.read(name).decode(
                        "utf-8-sig")
            return out
    raise SystemExit("[-] Provide code_red_freight.zip or extracted dir")


def rows(text):
    return list(csv.DictReader(text.splitlines()))


def main():
    ev = load_logs(sys.argv)

    audit = rows(ev["AuditLogs_2026-10-29-Patti_Fernandez.csv"])
    ual = rows(ev["UnifiedAuditLog_Patti.csv"])

    # --- 1. Device registrations: attacker vs baseline ----------------
    regs = [r for r in audit if r["Activity"] == "Register device"]
    print("[*] Device registrations:")
    for r in regs:
        print(f"    {r['Date (UTC)']} name={r['Target1DisplayName']} "
              f"ip={r['IPAddress']} deviceId={r['AdditionalDetail5Value']}")
    attacker_regs = [r for r in regs if r["IPAddress"] == "203.0.113.77"]
    assert len(attacker_regs) == 1, "expected exactly one attacker device"
    device = attacker_regs[0]["Target1DisplayName"]
    attacker_device_id = attacker_regs[0]["AdditionalDetail5Value"]
    baseline = [r for r in regs if r["IPAddress"] != "203.0.113.77"]
    print(f"[*] Attacker device : {device} ({attacker_device_id})")
    print(f"[*] Baseline device : {baseline[0]['Target1DisplayName']} "
          f"({baseline[0]['AdditionalDetail5Value']})")

    # --- 2. Inbox rules: malicious forward vs benign move -------------
    rules = [(i, json.loads(r["AuditData"]))
             for i, r in enumerate(ual) if r["Operation"] == "New-InboxRule"]
    print("[*] Inbox rules:")
    malicious = None
    for _, ad in rules:
        params = {p["Name"]: p["Value"] for p in ad.get("Parameters", [])}
        name = params.get("Name", "?")
        print(f"    {ad['CreationTime']} name={name} "
              f"ip={ad.get('ClientIP')} device={ad.get('DeviceId')} "
              f"forward={params.get('ForwardTo')} move={params.get('MoveToFolder')}")
        if params.get("ForwardTo", "").endswith("@proton.me"):
            malicious = (ad, params)
    assert malicious, "no external-forward rule found"
    rule = malicious[1]["Name"]
    fwd = malicious[1]["ForwardTo"]
    assert malicious[0].get("DeviceId") == attacker_device_id, \
        "rule DeviceId does not match the attacker device"
    print(f"[*] Malicious rule  : {rule} -> {fwd}")
    benign = [p for _, ad in rules
              for p in [{q["Name"]: q["Value"]}
                        for q in ad.get("Parameters", [])]]
    assert any("MoveToFolder" in str(b) for b in benign), \
        "benign baseline rule missing"

    # --- 3. Downloads from the attacker IP only -----------------------
    downloads = [r for r in ual if r["Operation"] == "FileDownloaded"]
    attacker_dl = [r for r in downloads
                   if "203.0.113.77" in json.loads(r["AuditData"])
                   .get("ClientIP", "")]
    print("[*] FileDownloaded events:")
    for r in attacker_dl:
        ad = json.loads(r["AuditData"])
        print(f"    {r['CreationDate']} {ad.get('SourceFileName')}")
    assert len(attacker_dl) == len(downloads), \
        "unexpected FileDownloaded from another IP"
    count = len(attacker_dl)
    print(f"[*] Download count  : {count}")

    flag = f"CSCTF{{{device}_{rule}_{count}}}"
    print(f"\n[+] FLAG            : {flag}")


if __name__ == "__main__":
    main()
