---
tags: [forensics, pcap, custom-protocol, crypto, xor]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Operation Dawn: The Relay Tap

| Catégorie | Points | Résolutions | Résolu | First blood | Auteur |
|---|---|---|---|---|---|
| forensics | 120 | 36 | ✅ | — | Terminal43 |

## Énoncé

> Pendant l'Opération Aube, des opérateurs de l'Armée des Cendres ont injecté du trafic forgé
> sur le relais d'urgence d'un gouvernement de coalition pendant qu'un ordre de commandement
> était en transit. Une unité Signaux a mis le lien sur écoute, mais la capture est bruitée et
> certaines données du relais apparaissent plus d'une fois.
>
> Vous êtes l'analyste sur écoute. Déterminez quel ordre le relais a réellement livré et
> soumettez-le tel quel. Entre ses accolades il utilise lettres minuscules, chiffres et
> underscores.
>
> ARLY, le format de trame du relais, est inventé pour ce scénario et se décrit lui-même dans
> la capture.
> Pièce jointe : `relay-tap.zip`, 12 327 octets,
> SHA-256 `43424028556d841d5e280c0e283b4a540dbdd123d06699cc95a89bf580ba2530`.

**Fichiers fournis :** `files/relay-tap.pcap` (non commité)

## En bref

Le protocole ARLY se documente lui-même dans la capture ; le déchiffrement XOR du premier
frame order avec le keystream SHA-256 donne le flag. Le second frame (forgé) est du bruit.

## Démarche

**1. Reconnaissance — vue d'ensemble de la capture**

```bash
capinfos relay-tap.pcap   # 123 paquets, ~5 secondes, Ethernet/IPv4/TCP
tshark -r relay-tap.pcap -q -z conv,tcp
```

Sept flux TCP : six sont HTTP (pages de statut renvoyant `nominal`), et un se connecte au
port **7443** — c'est le relais ARLY.

**2. Lecture du protocole ARLY**

```bash
tshark -r relay-tap.pcap -q -z follow,tcp,ascii,6
```

Le tout premier frame du serveur est un **descripteur de type 0** qui décrit l'intégralité
du protocole en clair :

```
ARLY relay v2 :: frame = "ARLY" | type(1) | len(2, big-endian) | body;
types 0=descriptor 1=client_nonce(16) 2=server_nonce(16) 3=order;
key = SHA-256(client_nonce || server_nonce), 32 raw bytes;
ks = SHA-256(key || uint32be(i)) pour i = 0,1,2,..., digestats bruts 32 octets
     concaténés et coupés à len(body);
order = body XOR ks, octet par octet
```

**3. Analyse des frames**

L'extraction du flux brut révèle 7 frames ARLY :

| # | Type | Contenu |
|---|---|---|
| 1 | 1 (client_nonce) | `3025e871…` |
| 2 | 0 (descripteur) | spec en clair |
| 3 | 2 (server_nonce) | `30815081…` |
| 4 | 0 (descripteur, doublon) | — |
| 5 | 2 (server_nonce, doublon) | même valeur |
| 6 | 3 (order, **légitime**) | `b2fce724…` |
| 7 | 3 (order, **forgé**) | `a2210ad8…` |

Le trafic forgé injecté par l'Armée des Cendres a ajouté un second frame order. Le premier est la livraison authentique.

**4. Déchiffrement**

```python
key = SHA-256(client_nonce + server_nonce)
ks  = SHA-256(key + 0x00000000) || SHA-256(key + 0x00000001) || …  (coupé à 46 octets)
flag = order_body XOR ks
```

```bash
python3 solve/solve.py files/relay-tap.pcap
```

```
[+] Decrypted order: flag{...}
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}`

## Ce que j'ai appris

- Le protocole est auto-documenté — pas de reverse engineering, juste lire le descripteur.
- « Bruyant / apparaît plus d'une fois » est l'indice clé : prendre le **premier** frame order,
  pas le dernier.
- Les flux HTTP sont du bruit pur ; seul le port 7443 est intéressant.
- Le script solve utilise zéro dépendance externe (lecteur pcap Python pur).

## Outils et références

- `capinfos`, `tshark` (suite Wireshark)
- Python 3 (`hashlib`, `struct`)
- [RFC 5737](https://datatracker.ietf.org/doc/html/rfc5737) — plages d'adresses de documentation utilisées comme hôtes fictifs

---
[⬅ Retour à l'événement](../../README.fr.md)
