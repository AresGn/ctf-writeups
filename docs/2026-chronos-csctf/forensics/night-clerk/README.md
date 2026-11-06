---
tags: [forensics, ntfs, docx, xor]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Night Clerk

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 120 | 45 | ✅ | — | 0xAr3s-root | Mohamed Amine Mzoughi |

## Challenge description

> Ash Army proxies have been planting people inside coalition depots across the Operation Dawn
> theatre. One hostile clerk used a depot terminal to hide a coordination message before
> isolation, and only the retained stick image survives.
>
> Recover the message from the image. Other exhibits it mentions are not provided and not needed,
> and you do not need to run anything in Office or mount the image. This is a constructed
> exercise, not a real incident.
> Attachment: `terminal.dd`, 8,388,608 bytes,
> SHA-256 `fb76b12579f7c1314df6e7556548a61c73c96157d95e77ba253c371c9d78bfb7`.

**Artifact files:** `files/terminal.dd` (not committed)

## TL;DR

Deleted `night_audit.docx` on an NTFS stick image contains a tracked insertion with a hex-encoded XOR-ciphertext; brute-forcing the single-byte key (57) yields the flag.

## Approach

**1. Recon — listing the NTFS image**

```bash
sha256sum terminal.dd   # verify integrity
file terminal.dd        # → DOS/MBR boot sector, NTFS
fls -r terminal.dd
```

Three user files appear:

| Inode | Name | Status |
|---|---|---|
| 64 | `README.TXT` | active |
| 65 | `audit-0214.log` | **deleted** |
| 66 | `night_audit.docx` | **deleted** |

**2. Reading the clue files**

```bash
icat terminal.dd 64   # README.TXT  → "Shift log clear."
icat terminal.dd 65   # audit-0214.log → instructions
```

`audit-0214.log` explains the puzzle:
- The Word file is a **redline** (tracked changes) — read the *insertion*, not the visible text.
- Hex-decode the tracked insertion first.
- DateTimeOriginal + OffsetTimeOriginal gives a UTC time; subtract it from an NTP transmit
  timestamp; the difference in whole seconds is the XOR key for each ciphertext byte.
- The other referenced exhibits (`desk.jpg`, `front_desk.pcapng`) are not needed.

**3. Extracting the docx and finding the insertion**

```bash
icat terminal.dd 66 > night_audit.docx
unzip -p night_audit.docx word/document.xml
```

The `<w:ins>` element contains a single `<w:t>` node:

```
7a6a7a6d7f4251505d664a525c4e664b5c5d5550575c44
```

**4. Finding the XOR key**

The ciphertext is 23 bytes. The flag format `CSCTF{…}` is known, so a brute-force over all
256 single-byte keys suffices. Key **57 (0x39)** produces a valid, readable flag.

```bash
python3 solve/solve.py files/terminal.dd
```

```
[+] Key   : 57 (0x39)
[+] Flag  : flag{...}
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}`

## Reflections

- The `audit-0214.log` instructions about EXIF timestamps and NTP packets are flavour — the
  XOR key is recoverable by brute-force alone because the flag format is known.
- The docx is a ZIP; no Office installation is needed, just `unzip` + XML parsing.
- `fls -r` immediately reveals deleted files on a small NTFS image — always check for them.

## Tools & references

- `fls`, `icat` (Sleuth Kit)
- Python 3 (`zipfile`, `xml.etree.ElementTree`)
- [NTFS forensics — Sleuth Kit wiki](https://wiki.sleuthkit.org/)
- OOXML tracked changes spec (ECMA-376)

---
[⬅ Back to event](../../README.md)
