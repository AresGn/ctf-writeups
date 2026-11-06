[🇬🇧 English](CONTRIBUTING.md) · 🇫🇷 Français

# Contribuer — RACE CONDITION

## 1. Installation (une seule fois)

1. Obtenir l'**accès en écriture** : AresGn invite ton compte GitHub (Settings → Collaborators).
2. Cloner et configurer ton identité (sur Kali ou ailleurs) :
   ```bash
   git clone https://github.com/AresGn/ctf-writeups.git
   cd ctf-writeups
   git config user.name "<ton-pseudo-github>"
   git config user.email "<ton-email-github>"
   ```
3. Facultatif, pour prévisualiser le site : `pip install mkdocs-material mkdocs-static-i18n`
   puis `mkdocs serve`.

> Pas de Git sous la main ? Tu peux éditer ou glisser des fichiers directement sur github.com.
> Pendant le CTF, ça va très bien : mieux vaut un commit brouillon qu'une coéquipière bloquée à 2 h du matin.

## 2. Méthode pendant un CTF

- **Une seule branche : `main`.** Pas de branche personnelle.
- **Un auteur par dossier de challenge.** Réserve un challenge sur le Discord avant de
  commencer, et n'écris que dans les dossiers que tu as pris.
- **Seul AresGn modifie les fichiers partagés** : les `README*.md` à la racine et les
  `README*.md` de chaque événement (liste des résultats). Dis-lui ce que tu as résolu,
  les points et s'il y a first blood.

Routine :

```bash
git pull --rebase                                    # avant de commencer
./new.sh 2026-chronos-csctf web nom-du-challenge     # créer le dossier
# ... résoudre, rédiger, scripts dans solve/, captures dans img/ ...
git add docs/2026-chronos-csctf/web/nom-du-challenge
git commit -m "web/nom-du-challenge: write-up"
git push                                             # si refusé : git pull --rebase, puis push
```

Note les commandes, pistes et impasses dans le `notes.md` de l'événement pendant que tu
travailles : les write-ups seront bien meilleurs que reconstruits de mémoire après 48 heures.

## 3. Rédiger un write-up

- **Deux langues, toujours.** `README.md` (anglais) et `README.fr.md` (français) ont le même
  contenu. Écris-en un pendant le CTF, traduis après ; les deux doivent exister avant que le
  repo passe en public.
- Remplace tous les `<placeholders>` du modèle, y compris **Auteur**.
- **Masque les flags** : `flag{...}`. On montre la méthode, pas la réponse.
- Les scripts vont dans `solve/` pour que n'importe qui puisse relancer l'exploit ; les
  captures dans `img/`.
- **Ne commite pas les fichiers fournis** (`files/` est ignoré par git : ils ne sont pas à
  nous et peuvent être lourds). Pour un petit fichier vraiment utile : `git add -f chemin/du/fichier`.
- Ne commite jamais de secrets : tokens, configs VPN personnelles, cookies de la plateforme.

Messages de commit : `<catégorie>/<challenge>: <quoi>`, par exemple `crypto/rsa-baby: solve script`.

## 4. Règles de compétition qu'on respecte

- **Aucun partage de flag ni de solution hors de l'équipe**, jamais. C'est ce qui a valu
  des disqualifications à HackerLab.
- **Rien de publié avant les résultats officiels** : le repo reste privé, aucun write-up,
  payload ou indice posté ailleurs.
- Une personne = un seul compte et une seule équipe sur la plateforme. Vérifie que tu es
  bien inscrit·e dans **RACE CONDITION** avant le coup d'envoi.
- Podium (top 3) : un write-up couvrant tous les défis crédités est à rendre avant la date
  limite des organisateurs (CSCTF 2026 : **9 nov. 11 h EET / 10 h heure du Bénin**).
