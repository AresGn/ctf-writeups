🇬🇧 English · [🇫🇷 Français](CONTRIBUTING.fr.md)

# Contributing — RACE CONDITION

## 1. One-time setup

1. Get **write access**: AresGn invites your GitHub account (Settings → Collaborators).
2. Clone and set your identity (on Kali or anywhere else):
   ```bash
   git clone https://github.com/AresGn/ctf-writeups.git
   cd ctf-writeups
   git config user.name "<your-github-username>"
   git config user.email "<your-github-email>"
   ```
3. Optional, to preview the website: `pip install mkdocs-material mkdocs-static-i18n`
   then `mkdocs serve`.

> No Git at hand? You can edit or drag-and-drop files directly on github.com. It is fine
> during the CTF; a blocked teammate at 2 a.m. is worse than a messy commit.

## 2. Workflow during a CTF

- **Single branch: `main`.** No personal branches.
- **One author per challenge folder.** Claim a challenge on Discord before starting it;
  only write in folders you claimed.
- **Only AresGn edits shared files**: the root `README*.md` and each event `README*.md`
  (results checklist). Tell AresGn what you solved, points and first blood.

Routine:

```bash
git pull --rebase                                   # before you start
./new.sh 2026-chronos-csctf web challenge-name      # create the folder
# ... solve, write, add scripts to solve/ and screenshots to img/ ...
git add docs/2026-chronos-csctf/web/challenge-name
git commit -m "web/challenge-name: write-up"
git push                                            # if rejected: git pull --rebase, then push
```

Log commands, leads and dead ends in the event's `notes.md` while you work: write-ups are
much better than when rebuilt from memory after 48 hours.

## 3. Writing a write-up

- **Two languages, always.** `README.md` (English) and `README.fr.md` (French) carry the
  same content. Write one first during the CTF, translate after; both must exist before the
  repo goes public.
- Fill in every `<placeholder>` of the template, including **Author**.
- **Redact flags**: `flag{...}`. Show the method, not the answer.
- Put scripts in `solve/` so anyone can re-run the exploit; screenshots in `img/`.
- **Do not commit provided files** (`files/` is git-ignored: they are not ours and may be
  large). For a small file that really helps: `git add -f path/to/file`.
- Never commit secrets: tokens, personal VPN configs, platform cookies.

Commit messages: `<category>/<challenge>: <what>` — e.g. `crypto/rsa-baby: solve script`.

Using an AI agent (Claude, Copilot, ChatGPT…)? It must follow [AGENT.md](AGENT.md): no AI signature or trailer in commits or files.

## 4. Competition rules we follow

- **No flag or solution sharing outside the team**, ever. This is what got teams
  disqualified at HackerLab.
- **Nothing published before official results**: the repo stays private, no write-up,
  payload or hint posted anywhere.
- Each person has a single platform account and a single team. Check you are registered in
  **RACE CONDITION** before kickoff.
- Podium (top 3): a write-up covering every credited challenge is due by the organizer's
  deadline (CSCTF 2026: **Nov 9, 11:00 EET / 10:00 Benin time**).
