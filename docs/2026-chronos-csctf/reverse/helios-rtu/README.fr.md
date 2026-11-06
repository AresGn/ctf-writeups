---
tags: [reverse, avr, atmega328p, debugwire, isp, bootloader, aes, cbc-mac]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# HELIOS-RTU

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| reverse | 782 | 52 | ✅ | — | 0xAr3s-root | Ionut Coserea |

## Énoncé

> A HELIOS GRID remote terminal unit (RTU) exposes a single web service console. Behind it is a real emulated ATmega328P running signed control firmware. The unit issues a service token only for a correctly authenticated control directive — and the authentication key is physically unreadable from outside.
>
> Identify the silicon, bring up the one interface on the bench that still answers, recover the application firmware, and produce a valid authentication tag over a control directive carrying the live nonce. Interact only with your assigned instance.
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** instance live uniquement (`http://w01.ctf.chronos-security.ro:34019/` au moment du solve — expirée)

## En bref

Câbler l'adaptateur AVR ISP sur le header ICSP pour identifier un ATmega328P (`0x1e950f`) à la flash verrouillée, lire les 2 Kio d'application via le bootloader série USB, apprendre de sa trame de contrôle AES-CBC-MAC qu'une directive vaut `frame[16]=0xCC, frame[17]=0x0A, nonce en [18:26]`, et forger le tag avec l'oracle de chiffrement `svc sign` du service lui-même (`tag = sign(b2 XOR sign(b1))`).

## Démarche

**1. Reconnaissance — un WebSocket, un banc, quatre adaptateurs**

La page est un terminal muet : chaque ligne tapée part verbatim sur `/ws` en JSON, et le banc envoie sur le même socket une ligne `wire $ADAPTER $LEAD:$PIN ...`. `help` expose un vrai CLI `avrdude` (`signature, lfuse/hfuse/efuse/lock, flash, eeprom` lisibles) plus `bench`/`wire` ; `svc` n'existe qu'après le faux `apt install svc` (`nonce | telemetry | sign $REC | exec $FRAME $TAG`). Adaptateurs du banc : AVR ISP (6 fils), câble USB, sonde JTAG, sonde debugWIRE (DW/VCC/GND). Rien ne dit quel câblage est juste — les réponses console sont le seul oracle.

**2. Hypothèse — identifier le silicium, puis essayer chaque transport**

debugWIRE d'abord (`DW→RESET, VCC→5V, GND→GND_A`, `-c jtag2dw`) : `[debugwire] sending BREAK` mais la cible n'assert jamais la ligne dW. L'ISP sur le header ICSP (`MISO/MOSI/SCK/RESET/VCC/GND → ICSP_*`) répond immédiatement : signature `0x1e950f` (**ATmega328P**), `lfuse=FF hfuse=D8 efuse=FD lock=FC`. Les fusibles expliquent le banc : `DWEN=1` (debugWIRE fusible-off — d'où l'absence de sync), `SPIEN=0` (ISP vivant), `BOOTRST=0` avec section boot, et `LB` programmé donc lectures flash ISP en pur `0xFF` (EEPROM aussi). Le JTAG n'existe pas sur un 328P. Le câble USB (`-c arduino`) est l'interface qui répond encore avec de vraies données : le bootloader série renvoie les **2 Kio de firmware application** en flash `0x0000` (tout au-delà de `0x0800`, région de la clé incluse, lit `0xFF`).

Désassemblage (radare2, AVR) de cette application : vecteurs → `main en 0x536` (trame UART `0xAA, type, len, payload`), un cœur AES-128 (`0x39a` chiffrement, `0x2b6` expansion de clé, S-box en flash `0x73`) dont les round keys s'expandent depuis 16 octets copiés de la flash `0x7F00` — précisément la région qu'aucune interface externe ne renverra. Les trames type-5 (payload 48 o) sont vérifiées par AES-CBC-MAC sur le payload, puis exigent `payload[16]==0xCC`, `payload[17]==0x0A`, puis répondent avec le nonce courant de 8 octets (PRNG xorshift32 en SRAM `0x1B0`, graine `0xE98EDACA`). Les commandes service sont la même machine à un niveau d'écart : `svc sign $REC16` est l'AES du dispositif comme oracle de chiffrement (enregistrements commençant `0xCC` refusés), `svc exec $FRAME32 $TAG` est le vérificateur type-5.

**3. Exploitation — forgery CBC-MAC sur nonce live à usage unique**

```bash
python3 solve/solve.py http://w01.ctf.chronos-security.ro:34019/
# [*] Live nonce    : ff0e23f621056868
# [*] Frame         : 00000000000000000000000000000000cc0a$NONCE000000000000
# [*] CBC-MAC tag   : c7fc… (sign[0] then sign[1 xor sign[0]])
# [*] exec reply    : service: directive authenticated
#                     service: control action ISSUE_TOKEN accepted
#                     service: SERVICE TOKEN = CSCTF{...}
```

Layout de trame : 16 octets zéro, marqueur directive `CC 0A`, le nonce live (8 octets), 6 octets zéro. Tag : `sign(frame[0:16])`, XOR dans `frame[16:32]`, `sign` à nouveau — la construction CBC-MAC de manuel, calculée via l'oracle puisque la clé elle-même ne quitte jamais le chip (l'extraire n'a jamais été nécessaire). Le nonce est à usage unique et global à l'instance : le lire, faire les deux signs, et `exec` dans la même session, sinon l'unité répond `directive nonce stale`. Un mauvais offset de marqueur répond `frame carries no control directive` ; un mauvais tag répond `directive authentication failed` — les trois erreurs séparent proprement les trois contrôles.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (masqué)

## Ce que j'ai appris

- Les octets fusibles sont une carte du banc : `DWEN`, `SPIEN`, `BOOTRST` et `LB` prédisaient lequel des quatre adaptateurs pouvait marcher avant qu'un seul fil soit tiré — lire `hfuse/lock` d'abord transforme « tout essayer » en checklist.
- « Physiquement illisible » était littéral et borné : le bootloader renvoie volontiers l'application mais `0xFF`-ise le domicile de la clé en `0x7F00`. Le pivot voulu va d'*extraire la clé* à *utiliser le chiffrement du dispositif comme oracle* — la forgery CBC-MAC a besoin de l'oracle, pas de la clé.
- Les messages d'erreur sont une spécification de protocole : `authentication failed` (MAC) contre `carries no control directive` (octets marqueurs) contre `nonce stale` (fraîcheur/position) m'ont dit laquelle des trois portes chaque tentative passait, transformant le layout de trame en recherche de 4 essais au lieu d'une devinette.

## Outils et références

- Python 3 (client `websockets`, protocole ligne WebSocket `/ws`) + `curl` (recon des assets)
- radare2 (`-a avr`, `aaa`/`pdf`) sur l'application récupérée via bootloader ; sémantique CLI `avrdude` en console
- Datasheet ATmega328P (signature `0x1E950F`, cartes fusibles/lock-bits, conditions d'entrée debugWIRE/ISP/bootloader), forgery par oracle AES-128 CBC-MAC

---
[⬅ Retour à l'événement](../../README.fr.md)
