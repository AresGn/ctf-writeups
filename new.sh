#!/usr/bin/env bash
# Usage:
#   ./new.sh <event>                          create an event page (EN + FR)
#   ./new.sh <event> <category> <challenge>   create a challenge write-up (EN + FR)
# Example: ./new.sh 2026-chronos-csctf web baby-sqli
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"

fill() { # fill <template> <dest> <sed-script>
  sed "$3" "$1" > "$2"
}

case $# in
  1)
    d="$root/docs/$1"
    [ -e "$d/README.md" ] && { echo "already exists: docs/$1" >&2; exit 1; }
    mkdir -p "$d"
    for f in README.md README.fr.md; do
      fill "$root/_template/event/$f" "$d/$f" "s/<ctf_name>/$1/g"
    done
    printf '# Notes — %s\n\n`HH:MM [challenge] note`\n\n' "$1" > "$d/notes.md"
    echo "created: docs/$1 (README.md, README.fr.md, notes.md)"
    ;;
  3)
    [ -e "$root/docs/$1/README.md" ] || { echo "unknown event: docs/$1 (run ./new.sh $1 first)" >&2; exit 1; }
    d="$root/docs/$1/$2/$3"
    [ -e "$d" ] && { echo "already exists: docs/$1/$2/$3" >&2; exit 1; }
    mkdir -p "$d"/{files,solve,img}
    touch "$d/files/.gitkeep" "$d/solve/.gitkeep" "$d/img/.gitkeep"
    for f in README.md README.fr.md; do
      fill "$root/_template/challenge/$f" "$d/$f" "s/<challenge_name>/$3/g; s/<category>/$2/g"
    done
    echo "created: docs/$1/$2/$3 (README.md + README.fr.md)"
    echo "line for the event checklist (AresGn):"
    echo "  EN:   - [x] [$3]($2/$3/README.md) · <points> pts · *(<author>)*"
    echo "  FR:   - [x] [$3]($2/$3/README.fr.md) · <points> pts · *(<author>)*"
    ;;
  *)
    echo "usage: $0 <event> | $0 <event> <category> <challenge>" >&2
    exit 1
    ;;
esac
