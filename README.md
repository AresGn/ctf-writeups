# CTF write-ups

Write-ups de CTF de **AresGn** et **[coéquipière à compléter]** · Équipe : **[nom d'équipe à compléter]**

> ⚠️ Repo **privé** pendant les compétitions. Rien n'est rendu public avant la publication
> officielle des résultats, et les flags sont toujours masqués (`flag{...}`).

## Événements

| Date | Événement | Format | Classement | Score | Write-ups |
|---|---|---|---|---|---|
| 2026 | HackerLab | — | — | — | [voir](docs/2026-hackerlab/) |
| 6–8 nov. 2026 | Chronos Security CSCTF 2026 « Total Warfare » | Jeopardy, 48 h | — | — | [voir](docs/2026-chronos-csctf/) |

## Organisation

```
ctf-writeups/
├── README.md                  # cet index
├── new.sh                     # crée le dossier d'un challenge
├── mkdocs.yml                 # site MkDocs Material
├── _template/README.md        # modèle de write-up
├── .github/workflows/pages.yml
└── docs/
    ├── index.md               # page d'accueil du site
    ├── 2026-hackerlab/
    └── 2026-chronos-csctf/
        ├── README.md          # bilan + tableau des challenges
        ├── notes.md           # notes en direct (non publiées sur le site)
        └── <catégorie>/<challenge>/
            ├── README.md      # le write-up
            ├── challenge.md   # énoncé, points, catégorie
            ├── files/         # fichiers fournis (ignorés par git par défaut)
            ├── solve/         # scripts et payloads
            └── img/           # captures d'écran
```

## Nouveau challenge

```bash
./new.sh 2026-chronos-csctf web nom-du-challenge
```

## Travail à deux

- Une seule branche `main`, **un auteur par dossier de challenge**.
- Avant de commencer : `git pull --rebase`. Ensuite : `git add . && git commit -m "web/nom: write-up" && git push`.
- Seul AresGn modifie le `README.md` de chaque événement (tableau des résultats).
- Aucun flag ni solution partagé hors de l'équipe.

## Site

Le site est généré avec MkDocs Material (`mkdocs serve` en local). Le workflow
`.github/workflows/pages.yml` publie sur la branche `gh-pages` ; activer GitHub Pages
seulement après passage du repo en public, une fois les résultats officiels publiés.
