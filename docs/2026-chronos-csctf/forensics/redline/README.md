---
tags: [forensics, docx, tracked-changes, ooxml]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Redline

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 120 | 127 | ✅ | — | 0xAr3s-root | Chronos Security |

## Challenge description

> Meridian Relief Network, Nightwatch case, Depot 7. During the grid-instability night a cold-chain excursion directive went out to depot crews, telling them what to do with medicine that had broken the cold chain. A crew lead kept the copy they received, and something about it reads wrong.
>
> The directive is a Word document (`.docx`). Work out how the version that reached the crews differs from what was actually approved, who changed it, and recover the original excursion authorization.
>
> Everything you need is in the file.
>
> Flag format: `CSCTF{message}`

**Artifact files:** `files/CC-11_excursion_directive.docx` (not committed).

## TL;DR

The `.docx` still contains its tracked changes: the approved text (quarantine order and original authorization) is stored as `w:del` runs by `s.kessler`, with a decoy authorization in the `w:ins` runs; reading the deleted text gives the original flag.

## Approach

**1. Recon — a docx is a zip of XML**

```bash
unzip CC-11_excursion_directive.docx -d docx/
```

Interesting parts: `word/document.xml` (body), `word/comments.xml` and `docProps/core.xml`. The metadata already tells who touched it: creator `A. Reyes` (the Medical Director who issued it), `lastModifiedBy` `s.kessler`, created 2026-10-06T14:02Z, modified 2026-10-07T02:41Z, revision 4.

**2. Hypothesis — the delivered text is "accepted changes"; the approved one is in the deletions**

The body contains `w:del` / `w:ins` elements, all by `s.kessler` at 02:41:00Z. Reading them side by side:

| | Approved (`w:del`) | Delivered (`w:ins`) |
|---|---|---|
| Wording | "temperature" excursion | "thermal" excursion |
| Page threshold | 30 minutes | 90 minutes |
| Breached vials | MUST be quarantined, MUST NOT be redistributed | may be returned to distribution at depot-supervisor discretion |
| Authorization | `CSCTF{...}` (original) | another `CSCTF{...}` (fresh one) |

`comments.xml` has `s.kessler`'s own justification: "dropping the quarantine hold … Re-issuing under a fresh authorization". So the safety-critical instruction was reversed and the authorization swapped. The inserted `CSCTF{...}` is a decoy: the task asks for the **original** one.

One more trap: the deleted authorization is split across two `w:del` runs (ids 107 and 108), so a text search for a full `CSCTF{...}` in the XML finds only the inserted one; the two `w:delText` pieces must be concatenated.

**3. Exploitation — rebuild the original paragraph from the XML**

The script reads `document.xml`, rebuilds the *original* text (plain runs + `w:delText`) and the *delivered* one (plain runs + inserted `w:t`), prints the metadata and the comment, and extracts the flag from the original version:

```bash
python3 -I solve/solve.py files/CC-11_excursion_directive.docx
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (redacted)

## Reflections

- Word's "accept all changes" is not a sanitizer in the file: the original text lives on in `w:del` until someone accepts and saves; metadata (`lastModifiedBy`, revision) and comments tell the who and why.
- Rendered views (Word, LibreOffice) can hide or merge this; reading the raw XML is more reliable and lets you spot content split across runs.
- Two lookalike flags in the same paragraph: always check which one the question asks for (original vs. delivered).
- The file was handled as data only (unzip + XML parsing), never opened in Word.

## Tools & references

- `unzip`, Python 3 (`zipfile`, `xml.etree`)
- Office Open XML WordprocessingML: `w:ins`, `w:del`, `w:delText`, comments, core properties

---
[⬅ Back to event](../../README.md)
