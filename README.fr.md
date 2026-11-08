[🇬🇧 English](README.md) · 🇫🇷 Français

# Write-ups CTF — RACE CONDITION

Write-ups de CTF de l'équipe **RACE CONDITION** :

| Membre | GitHub |
|---|---|
| **AresGn** | [AresGn](https://github.com/AresGn) · compte de jeu [0xAr3s-root](https://github.com/0xAr3s-root) |
| **Nyx** | [Nyx03-gbd](https://github.com/Nyx03-gbd) |

> ⚠️ Ce repo reste **privé** pendant les compétitions. Rien n'est rendu public avant la
> publication officielle des résultats, et les flags sont toujours masqués (`flag{...}`).

## Événements

| Date | Événement | Format | Classement | Score | Write-ups |
|---|---|---|---|---|---|
| 2026 | HackerLab | — | — | — | [EN](docs/2026-hackerlab/README.md) · [FR](docs/2026-hackerlab/README.fr.md) |
| 6–8 nov. 2026 | Chronos Security CSCTF 2026 « Total Warfare » | Jeopardy, 48 h | — | 11834 (final, non officiel) | [EN](docs/2026-chronos-csctf/README.md) · [FR](docs/2026-chronos-csctf/README.fr.md) |

## Organisation

Chaque page Markdown existe en deux langues : `nom.md` (anglais) et `nom.fr.md` (français).

```
ctf-writeups/
├── README.md / README.fr.md             # cet index
├── CONTRIBUTING.md / CONTRIBUTING.fr.md # comment on travaille ensemble
├── AGENT.md / AGENT.fr.md               # règles pour les agents IA (write-ups)
├── new.sh                               # crée un événement ou un challenge
├── mkdocs.yml                           # site MkDocs Material bilingue
├── hooks/                               # hook MkDocs (masque la ligne de langue sur le site)
├── tools/build_submission.py            # génère la soumission (MD, HTML, PDF, zip du site)
├── submission/<événement>/              # fichiers de soumission générés, EN + FR
├── _template/
│   ├── event/      README.md + README.fr.md   # page principale d'un événement
│   └── challenge/  README.md + README.fr.md   # write-up d'un challenge
└── docs/
    ├── index.md / index.fr.md
    ├── 2026-hackerlab/
    └── 2026-chronos-csctf/
        ├── README.md / README.fr.md     # bilan + liste des challenges
        ├── notes.md                     # notes en direct (non publiées)
        └── <catégorie>/<challenge>/
            ├── README.md / README.fr.md # le write-up
            ├── files/                   # fichiers fournis (ignorés par git)
            ├── solve/                   # scripts et payloads
            └── img/                     # captures d'écran
```

## Démarrage rapide

```bash
./new.sh 2026-chronos-csctf web nom-du-challenge   # nouveau challenge (EN + FR)
./new.sh 2027-un-ctf                               # nouvel événement (EN + FR)
```

Voir [CONTRIBUTING.fr.md](CONTRIBUTING.fr.md) pour la méthode de travail complète, et [AGENT.fr.md](AGENT.fr.md) si un agent IA t'aide à rédiger.

## Site

Généré avec MkDocs Material (`mkdocs serve` pour prévisualiser en local), en anglais par
défaut avec la version française sous `/fr/`. Le workflow publie sur la branche `gh-pages` ;
GitHub Pages n'est activé qu'une fois le repo public, après les résultats officiels.

## Crédits

Modèles de write-up adaptés de
[RyanNgCT/CTF-Writeup-Template](https://github.com/RyanNgCT/CTF-Writeup-Template).
