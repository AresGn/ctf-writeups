---
tags: [forensics, windows, lnk, registry, webdav, 7zip]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Briefing for One

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 82 | ✅ | — | no | 0xAr3s-root | Chronos Security |

## Challenge description

> Flood response was under way when an intruder staged a routing package for a single workstation at the fictional Rovenqara Civil Continuity Directorate, which coordinates civil support for coalition forces in Operation Dawn. The shortcut opened, and isolation left regional shelter routing on paper.
>
> Recover the package from the supplied evidence and submit its briefing token. Analyze the files only: do not execute the shortcut or DLL, or contact captured addresses.
>
> Attachment: `briefing-for-one-5f4125fbb77f625d.zip`, 161,346 bytes, SHA-256: `5f4125fbb77f625d85bbdb2d0f5090ed270409a302bd5f15a5f90a43d050cb9a`
>
> Flag format: `CSCTF{32 lowercase hexadecimal characters}`

**Artifact files:** `files/briefing-for-one-5f4125fbb77f625d.zip` (not committed — currently at `forensics/briefing-for-one-5f4125fbb77f625d.zip`)

## TL;DR

Parse (never open) the `.lnk` to recover its PowerShell staging script, read `MachineGuid` at the root of the saved Cryptography hive, recompute the 7-Zip password as `HMAC-SHA-256(binding-key, "csctf26/briefing-for-one/v1" || 0x00 || guid)`, pull the real `route-update.7z` out of the WebDAV capture by hash, decrypt it, and read the token the DLL statically validates in `route-table.json`.

## Approach

**1. Recon — inventory, and read the field guide first**

```bash
sha256sum briefing-for-one-5f4125fbb77f625d.zip  # 5f4125fb…cb9a matches
unzip -l briefing-for-one-5f4125fbb77f625d.zip
# briefing.lnk (5709)  machine-cryptography.hiv (126976)  egress.pcapng (22876)
# field-guide.md  provenance.json  SHA256SUMS  (all SHA256SUMS verify)
```

`field-guide.md` + `provenance.json` carry three load-bearing warnings, all confirmed later: (a) the hive is a **saved subkey** (`reg.exe save` of `Cryptography`), so an offline reader presents that key as its root — tools expecting `SOFTWARE\Microsoft\Cryptography\…` need the saved-root path; (b) Wireshark HTTP export, DAV XML and raw TCP streams are **different byte sequences** — only compare an exported body against the hash in the evidence; (c) a worked HMAC example (published inputs) pins the exact byte handling: UTF-8 without BOM, one `0x00` separator, GUID lowercased without braces/whitespace/NUL. I verified that example reproduces (`7dad6991…10d0`) before using the derivation on case values.

**2. Hypothesis — the shortcut is the whole staging script, in plaintext**

Parsing the Shell Link StringData statically (header → IDList → LinkInfo → Unicode StringData; target `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`, description “Regional shelter routing update”) yields a 2194-char `-Command` that, in order:

1. Gates on a sibling `permit.bin`: must exist, be 32 bytes, match a pinned SHA-256 (else exit 41/42). `provenance.json` explains the control design — a permit-absent negative control preceded this permit-present run — so the capture is the selected run. The permit contents are a launch gate only; nothing below derives from them.
2. Reads `HKLM\SOFTWARE\Microsoft\Cryptography` `MachineGuid`, validates its shape and lowercases it.
3. Derives the package password: `$k` = Base64-decoded binding key (32 bytes, embedded in the command), `$p` = lowercase hex `HMAC-SHA-256($k, UTF8('csctf26/briefing-for-one/v1' + [char]0 + $g))` — exactly the field-guide construction.
4. Copies `\\briefing.rovenqara.test@80\DavWWWRoot\ops\route-update.7z` (WebDAV; **not contacted** — the same exchange is in `egress.pcapng`), verifies its pinned SHA-256, extracts it with `7z x -p$p`, verifies `route-update.dll` and `route-table.json` against two more pinned hashes, then `rundll32 …,ApplyRouteTable` and checks `route-applied.txt` == `Rovenqara route fixture applied\r\n`.

So the offline job is: hive → GUID, capture → archive, password → members, DLL (static) → token validation rule. The hive root confirms step 2 immediately: root key `Cryptography`, single root value `MachineGuid = 080c7be1-f41c-446c-b961-93bd7bc4ea31` (REG_SZ). A minimal NK/VK reader (root offset at header `0x24`, cell offsets relative to `0x1000`) gets it without mounting anything.

**3. Exploitation — recover by hash, decrypt, validate statically**

Capture: 95 packets, 8 TCP connections `192.168.56.20 → 192.168.56.10:80` (`OPTIONS`, several `PROPFIND`, one `GET /ops/route-update.7z`). `tshark --export-objects http,…` produces 7 objects — and 6 are DAV XML (881–914 bytes), three of them *named* `route-update*.7z`. Only the `GET` 200 `application/octet-stream` body (5359 bytes) hashes to the value pinned in the shortcut (`d29a0679…e4c2`). Hash, not filename, selects the package — precisely the field-guide trap.

```bash
# password = HMAC above over the case GUID (solver recomputes it from the .lnk)
7z x -p"$PASSWORD" -oroute_out route-update.7z   # archive reader only
sha256sum route-update.dll route-table.json          # both match the .lnk pins
```

Members: `route-table.json` (192 bytes) and `route-update.dll` (PE32+ x86-64, 13,824 bytes). The DLL was examined **only** statically (`pefile`/`objdump`, never loaded): single export `ApplyRouteTable` (RVA `0x137f`), imports `GetModuleFileNameW/CreateFileW/GetFileSize/ReadFile/WriteFile`. Disassembly shows it builds the sibling `route-table.json` path, requires `GetFileSize == 0xC0` (192), `strncmp`s a 36-byte (`0x24`) prefix `{"schema":1,"briefing_token":"CSCTF{` and the 124-byte (`0x7c`) routes suffix at offset `0x44`, then loops over bytes 36…67 accepting only `[0-9]`/`[a-f]` — i.e. exactly 32 lowercase hex chars — before writing `route-applied.txt`. The DLL embeds the prefix/suffix only, never the token itself, so the token genuinely lives in the recovered JSON between them:

```bash
python3 solve/solve.py ../briefing-for-one-5f4125fbb77f625d.zip
# [*] Example OK   : 7dad69912b67470da7713c666337135b568030605bc2e88f99524596366d10d0
# [*] LNK command  : 2194 chars (powershell.exe, static)
# [*] MachineGuid  : 080c7be1-f41c-446c-b961-93bd7bc4ea31 (hive root = Cryptography)
# [*] GET body     : 5359 bytes, sha256=d29a0679… (matches the .lnk pin)
# [*] Member hashes match the LNK expectations
# [+] FLAG         : CSCTF{...}
```

The solver is stdlib-only apart from the `7z` binary (own LNK, hive NK/VK, pcapng/TCP and HTTP parsing; every constant is extracted from the evidence) and never executes the shortcut or DLL.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (redacted)

## Reflections

- Treat the `.lnk` as a document, not a launcher: Shell Link StringData held the entire intrusion script — key, derivation, URLs and all three acceptance hashes — with no execution needed.
- Every stage has an independent acceptance hash (archive, DLL, JSON). Using them is what separates the real 5359-byte package from the three same-named DAV XML exports; filenames alone would have decrypted nothing.
- Saved-subkey hives invert the usual path expectation: `MachineGuid` is at the *root* of this file. Checking the root key name (`Cryptography`) first avoids hunting for a `SOFTWARE\…` hierarchy that is not there.
- Static DLL validation cuts both ways: the disassembly (192-byte size, prefix/suffix compares, `[0-9a-f]{32}` loop) proves the JSON token is the intended submission and that no second, hidden token is generated at runtime.

## Tools & references

- Python 3 stdlib (`struct`, `hashlib`, `hmac`, `zipfile`) + `7z` (encrypted-archive reader only)
- Wireshark / `tshark --export-objects http` and `capinfos` (capture recon cross-checks)
- `pefile`, `objdump` (static PE triage/disassembly — DLL never executed)
- Windows Shell Link StringData, registry hive NK/VK cells, WebDAV (`PROPFIND`/`GET`) over HTTP

---
[⬅ Back to event](../../README.md)
