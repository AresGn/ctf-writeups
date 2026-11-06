---
tags: [forensics, entra-id, phishing, device-code, inbox-rule]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Code Red Freight

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 270 | 102 | ✅ | — | 0xAr3s-root | Marius Merai |

## Challenge description

> Tarnovel Rail Freight's defence-consignment manifests are reaching an outside mailbox. The dispatcher noticed nothing. You have her identity, mailbox-audit exports, and the email she clicked. Identify the device the adversary controls, the rule leaking manifests, and the number of files they downloaded.
>
> This is a constructed incident-analysis case built from sanitized Microsoft Entra and Purview-style exports. Work only with the supplied evidence; do not contact domains, addresses, or services named in it.
>
> Attachment: `code_red_freight.zip`
>
> Flag format: `CSCTF{device_rule_count}` (e.g. `CSCTF{DESKTOP-XXXX_ForwardRule_42}` — illustrative only)

**Artifact files:** `files/code_red_freight.zip` (not committed — currently at `forensics/code_red_freight.zip`)

## TL;DR

Device-code phishing (`microsoft.com/devicelogin` + lookalike-share lure) gave the attacker an Entra session from Montreal; the rogue Azure AD device, the forward-to-external inbox rule, and the SharePoint `FileDownloaded` events all tie to the same IP/device — the three flag parts are derived in step 3 below (`flag{...}` redacted).

## Approach

**1. Recon — inventory and separate the two worlds**

```bash
unzip -l code_red_freight.zip
# logs/AuditLogs_2026-10-29-Patti_Fernandez.csv          (12 rows)
# logs/InteractiveSignIns_2026-10-28_2026-10-29.csv      (18 rows)
# logs/NonInteractiveSignIns_2026-10-28_2026-10-29.csv   (256 rows)
# logs/UnifiedAuditLog_Patti.csv                         (188 rows)
# lure/email_phish.png  lure/devicecode_phish.png
```

The lures tell the story before any log is opened: an email from `ragubarden@proton.me` ("Jordan Smith shared Draft_Budget_v2.docx") links to `https://Sharepoint.cz/584c39f3-…`, and the fake OneDrive page asks for `microsoft.com/devicelogin` + code `CXR7QK2WD` — classic device-code phishing. Two IPs then split every log cleanly: dispatcher Patti on `198.51.100.24` (Bucuresti/Timisoara) vs attacker on `203.0.113.77` (Montreal).

AuditLogs `Register device` makes the split concrete — one row per world:

| Date | Device | IP | DeviceId |
|---|---|---|---|
| 2026-10-28 07:12 | `R3M0TE-W0RK-PC` (baseline) | 198.51.100.24 | `3f8c1a7b-…` |
| 2026-10-29 15:05 | `D3VC0DE-R3L4Y` (rogue) | 203.0.113.77 | `95caec44-…` |

Interactive sign-ins confirm the mechanism: the rogue registration follows a `deviceCodeFlow` / `Authentication Protocol: deviceCode` pair on `Microsoft Authentication Broker → Device Registration Service` from the attacker IP (15:04:52 failure 50199 "user interaction required", 15:04:55 success), after which every attacker session is `deviceCodeFlow`-bound, `Azure AD joined`, carrying DeviceId `95caec44-…` (40 non-interactive rows; the benign world has an empty DeviceId throughout).

**2. Hypothesis — one device, one rule, count only its downloads**

With the attacker DeviceId pinned (`95caec44-c8af-4786-976c-73bd33d9d143`), the Unified Audit Log is unambiguous:

- `New-InboxRule` appears exactly twice. The benign `Newsletters` rule (2026-10-28, dispatcher IP/session, `MoveToFolder` + `FromAddressContainsWords`, no DeviceId) is the baseline; the 2026-10-29T15:28:57 rule `M4N1F3ST-L3AK` comes from `203.0.113.77:17091` on the attacker's session `009d0b3a-…`, carries the attacker DeviceId, sets `ForwardTo = ragubarden@proton.me` (the lure sender) with `StopProcessingRules = True`. Name, destination and device all point the same way.
- `FileDownloaded` appears exactly 4 times — all from `203.0.113.77`, all `Microsoft Teams` UA, and none from the dispatcher's IP: `Investor Relations Meeting Presentation.pptx`, `aerialshot.jpg`, `Local Resource Guide.docx`, `Notes.docx` (15:20:24–15:21:36). `FileAccessed`/`FileModified` rows from other IPs (service/MFA ranges) are reads and sync noise, not downloads, and `MailItemsAccessed` rows carry no attacker-IP signal — so the count is 4, not 30.

**3. Exploitation — derive, don't hardcode**

```bash
python3 solve/solve.py ../code_red_freight.zip
# [*] Device registrations:
#     2026-10-29T15:05:03 ... D3VC0DE-R3L4Y ip=203.0.113.77 deviceId=95caec44-…
#     2026-10-28T07:12:03 ... R3M0TE-W0RK-PC ip=198.51.100.24 deviceId=3f8c1a7b-…
# [*] Inbox rules:
#     2026-10-29T15:28:57 name=M4N1F3ST-L3AK ip=203.0.113.77:17091 device=95caec44-… forward=ragubarden@proton.me
#     2026-10-28T07:34:27 name=Newsletters ip=198.51.100.24:51224 forward=None move=Newsletters
# [*] FileDownloaded events: (4, all 203.0.113.77)
# [+] FLAG            : CSCTF{...}
```

The solver asserts each link (rule DeviceId == rogue DeviceId, all downloads from the attacker IP, benign baseline present) instead of trusting names, so a renamed-device variant would still resolve — or fail loudly rather than emit a wrong flag.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (redacted)

## Reflections

- The leet names (`D3VC0DE-R3L4Y` = device-relay, `M4N1F3ST-L3AK` = manifest-leak) confirm the answer but must not *be* the method: the DeviceId linkage (registration → sessions → rule) and the IP split are the actual proof, and they would survive renamed decoys.
- `FileDownloaded` ≠ `FileAccessed`: counting every SharePoint touch inflates the number. Only the `FileDownloaded` operation with the attacker IP counts — the solver enforces that all 4 come from one IP.
- The benign `Newsletters` rule is the control the challenge gives you: same operation, different IP/session/device/parameters. Checking it first is what makes the malicious rule stand out instead of being "the first rule found".

## Tools & references

- Python 3 stdlib (`csv`, `json`, `zipfile`) — no dependency needed
- Image viewer (lure PNGs — read only, never open links)
- Entra sign-in log / Purview UAL semantics: deviceCode flow, `Register device`, `New-InboxRule` (`ForwardTo`), `FileDownloaded`

---
[⬅ Back to event](../../README.md)
