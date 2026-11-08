---
tags: [web, sqli, forensics-log]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Operation Dawn: The Command

| Catégorie | Résolutions | Résolu | First blood | Indice utilisé | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| web | — | ✅ | — | non | 0xAr3s-root | Chronos Security |

## Énoncé

> Operation Dawn, annexe entrée 07. L'Armée des Cendres exploitait un portail de statut pour
> son checkpoint de canal ; les équipes cyber de la coalition ont saisi les logs du serveur web.
> Un visiteur a quitté la base de données du portail avec le secret de liaison du checkpoint
> sans jamais déclencher une page d'erreur. Récupérez ce qu'il a pris et soumettez-le tel quel.
> Il porte déjà ses propres accolades, ne les doublez pas.
>
> Le portail, ses unités et tous les hôtes du log sont fictifs.
> Pièce jointe : `access.log`, 514 137 octets,
> SHA-256 `3bb180802cc90b56984f179cb4315fc805d1e047e8a2374544044858fea30db2`.
> Chaque ligne est au format combined de nginx, suivi de `rt=`, le temps de réponse en secondes.

**Fichiers fournis :** `files/access.log` (non commité)

## En bref

Injection SQL aveugle temporelle sur `GET /api/status?unit=` — l'attaquant utilisait
`IF(SUBSTR(token,N,1)='X',SLEEP(2),0)` pour exfiltrer le token caractère par caractère ;
les requêtes avec `rt ≥ 2` révèlent chaque caractère correct.

## Démarche

**1. Reconnaissance — lecture du format de log**

Le log est au format nginx combined, avec un champ `rt=SECONDES` ajouté à chaque ligne.
Le trafic normal (IP `192.0.2.76`) navigue sur le portail avec des temps de réponse
inférieurs à la milliseconde.

Une IP se distingue immédiatement : `198.51.100.66`, utilisant `python-requests/2.32.3`
sans `Referer` — c'est de l'automatisation.

**2. Identification de l'attaque**

La recherche de mots-clés SQL révèle une longue série de requêtes vers `/api/status` :

```
GET /api/status?unit=43'+AND+IF(SUBSTR(token,6,1)='Z',SLEEP(2),0)--+- HTTP/1.1
```

C'est une **injection SQL aveugle temporelle** :
- La colonne `token` est exfiltrée caractère par caractère.
- `SUBSTR(token, N, 1)` extrait le Nième caractère.
- `IF(..., SLEEP(2), 0)` fait dormir le serveur 2 secondes si la supposition est correcte.
- L'attaquant teste chaque caractère imprimable à chaque position et observe le temps de réponse.

Toutes les requêtes retournent HTTP `200` avec un petit corps — aucune page d'erreur, ce qui
confirme le texte de l'énoncé.

**3. Reconstruction**

Le champ `rt=` enregistre le temps de réponse réel du serveur. Une requête avec `rt >= 2.0`
signifie que `SLEEP(2)` s'est déclenché → le caractère deviné était correct.

On parse toutes les lignes correspondantes, on URL-décode le caractère (`%7B` → `{`,
`%7D` → `}`), et on assemble le token par position :

```bash
python3 solve/solve.py files/access.log
```

```
[+] Token length : 41
[+] Recovered token: flag{...}
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}`

## Ce que j'ai appris

- Le challenge est du **forensics de log** pur : pas besoin d'exploitation en direct,
  il suffit de rejouer ce que l'attaquant a déjà fait.
- Insight clé : le champ `rt=` dans les logs nginx est l'indice décisif. Sans lui, il
  faudrait compter les requêtes en double par position pour trouver le « gagnant » par
  fréquence, ce qui est plus bruité.
- Le décodage URL du champ caractère est facile à rater — `{` et `}` sont encodés
  en `%7B`/`%7D` et doivent être décodés, sinon le premier et dernier caractère seront faux.

## Outils et références

- Python 3 (`re`, `urllib.parse.unquote`)
- [Documentation du format de log nginx](https://nginx.org/en/docs/http/ngx_http_log_module.html)
- Blind time-based SQLi : [OWASP Testing Guide – OTG-INPVAL-005](https://owasp.org/www-project-web-security-testing-guide/)

---
[⬅ Retour à l'événement](../../README.fr.md)
