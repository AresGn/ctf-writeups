🇬🇧 English · [🇫🇷 Français](README.fr.md)

# CTF write-ups — RACE CONDITION

CTF write-ups by team **RACE CONDITION**:

| Member | GitHub |
|---|---|
| **AresGn** | [AresGn](https://github.com/AresGn) · play account [0xAr3s-root](https://github.com/0xAr3s-root) |
| **Nyx** | [Nyx03-gbd](https://github.com/Nyx03-gbd) |

> ⚠️ This repo stays **private** during competitions. Nothing is made public before the
> official results are published, and flags are always redacted (`flag{...}`).

## Events

| Date | Event | Format | Rank | Score | Write-ups |
|---|---|---|---|---|---|
| 2026 | HackerLab | — | — | — | [EN](docs/2026-hackerlab/README.md) · [FR](docs/2026-hackerlab/README.fr.md) |
| Nov 6–8, 2026 | Chronos Security CSCTF 2026 "Total Warfare" | Jeopardy, 48 h | 216th | 10046 | [EN](docs/2026-chronos-csctf/README.md) · [FR](docs/2026-chronos-csctf/README.fr.md) |

## Layout

Every Markdown page exists in two languages: `name.md` (English) and `name.fr.md` (French).

```
ctf-writeups/
├── README.md / README.fr.md             # this index
├── CONTRIBUTING.md / CONTRIBUTING.fr.md # how we work together
├── AGENT.md / AGENT.fr.md               # rules for AI agents (write-ups)
├── new.sh                               # creates an event or a challenge
├── mkdocs.yml                           # bilingual MkDocs Material site
├── hooks/                               # MkDocs hook (hides the language line on the site)
├── tools/build_submission.py            # builds the submission (MD, HTML, PDF, site zip)
├── submission/<event>/                  # generated submission files, EN + FR
├── _template/
│   ├── event/      README.md + README.fr.md   # event main page
│   └── challenge/  README.md + README.fr.md   # challenge write-up
└── docs/
    ├── index.md / index.fr.md
    ├── 2026-hackerlab/
    └── 2026-chronos-csctf/
        ├── README.md / README.fr.md     # summary + challenge checklist
        ├── notes.md                     # live notes (not published)
        └── <category>/<challenge>/
            ├── README.md / README.fr.md # the write-up
            ├── files/                   # provided files (git-ignored)
            ├── solve/                   # scripts and payloads
            └── img/                     # screenshots
```

## Quick start

```bash
./new.sh 2026-chronos-csctf web challenge-name   # new challenge (EN + FR)
./new.sh 2027-some-ctf                           # new event (EN + FR)
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow, and [AGENT.md](AGENT.md) if an AI agent helps you write.

## Website

Built with MkDocs Material (`mkdocs serve` to preview locally), English by default with a
French version under `/fr/`. The workflow publishes to the `gh-pages` branch; GitHub Pages is
only enabled once the repo goes public, after official results.

## Credits

Write-up templates adapted from
[RyanNgCT/CTF-Writeup-Template](https://github.com/RyanNgCT/CTF-Writeup-Template).
