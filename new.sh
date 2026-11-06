#!/usr/bin/env bash
# usage : ./new.sh 2026-chronos-csctf web nom-du-challenge
set -euo pipefail
if [ $# -ne 3 ]; then
  echo "usage : $0 <evenement> <categorie> <challenge>" >&2
  exit 1
fi
root="$(cd "$(dirname "$0")" && pwd)"
d="$root/docs/$1/$2/$3"
if [ -e "$d" ]; then
  echo "existe déjà : $d" >&2
  exit 1
fi
mkdir -p "$d"/{files,solve,img}
touch "$d/files/.gitkeep" "$d/solve/.gitkeep" "$d/img/.gitkeep"
sed "s/^# Nom du challenge/# $3/; s/tags: \[categorie\]/tags: [$2]/; s/\*\*Catégorie :\*\* web/**Catégorie :** $2/" \
  "$root/_template/README.md" > "$d/README.md"
cat > "$d/challenge.md" <<MD
# $3 — énoncé

- **Catégorie :** $2
- **Points :**
- **Auteur du challenge :**

## Énoncé

MD
echo "créé : docs/$1/$2/$3"
