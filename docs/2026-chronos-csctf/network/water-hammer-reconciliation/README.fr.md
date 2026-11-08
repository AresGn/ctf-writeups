---
tags: [network, modbus, pcap, tcp-reassembly, forensics]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Water Hammer Reconciliation

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| network | 326 | 124 | ✅ | — | 0xAr3s-root | Cosmin Gorea |

## Énoncé

> The Vardessa Civil Water Reserve header was isolated after a hostile engineering-station interval, part of a wider campaign against emergency water logistics that coalition analysts tie to an Ash Army proxy. Vardessa is an Operation Dawn partner.
>
> Reconstruct the complete confirmed Modbus/TCP control history and submit the reconciliation identifier the evidence supports. `water-hammer-reconciliation.zip` holds all three evidence files: the capture `reserve-header.pcapng`, `station-profile.txt` and `capture-manifest.txt`. `station-profile.txt` defines the scoped conversation, the confirmation rule, the safety screen, the report grammar and the submission encoding; `capture-manifest.txt` identifies the evidence and its provenance. No live plant, external service or credential is involved.
>
> The capture holds ordinary reads, one exception and one unanswered write. A write acknowledgement on its own is not a confirmed control snapshot, so follow the profile's matched-readback rule.
>
> Flag format: `CSCTF{message}`

**Fichiers fournis :** `files/reserve-header.pcapng`, `files/station-profile.txt`, `files/capture-manifest.txt` (non commités).

## En bref

Réassembler l'unique conversation Modbus/TCP, ne garder que les écritures FC16 dont l'écho normal unique est suivi du readback FC3 exact avec une réponse unique appariée (64 instantanés), les sérialiser dans le rapport canonique avec le masque d'insécurité en entiers, en SHA-256, puis encoder les 24 premiers octets en Base32 → flag.

## Démarche

**1. Reconnaissance — le profil est la spécification**

`station-profile.txt` fixe tout : la conversation ciblée (`192.0.2.10:<éphémère>` → `192.0.2.20:502`, unit 17), la grammaire MBAP stricte (protocol id 0, Length = 1 + PDU, ni troncature ni octets en trop), la carte des registres (0x1000 consigne pompe, 0x1001 ouverture vanne en pour-mille, 0x1002 armé, 0x1003 rampe en µs), la règle de confirmation, un filtre de sécurité en entiers (E, V, Q avec `T_US = 37558`), le texte exact du rapport `R` et l'encodage (`SHA-256(R)` → 24 premiers octets → Base32 sans padding → 39 caractères), plus un vecteur de test synthétique public. `capture-manifest.txt` ne donne que la provenance et le SHA-256 de la capture, qui correspond (`6af88183…`).

La capture est une seule conversation TCP (port client 36853) de 536 trames, 2 190 octets client et 1 933 octets serveur. Les frontières de segments n'ont pas d'importance : certains ADU sont coupés sur plusieurs segments, j'ai donc réassemblé chaque sens par numéro de séquence TCP et délimité les flux d'octets avec la longueur MBAP. Codes fonction côté client : 68 FC3 et 66 FC16 ; côté serveur : 68 FC3, 64 réponses FC16 normales et une exception FC16 (`0x90`, code 04).

**2. Hypothèse — un instantané demande quatre choses, dans l'ordre**

Une écriture ne compte que si : (1) la requête FC16 est un candidat valide (unit 17, départ/quantité dans 0x1000–0x1003, Length `7 + 2N`, byte count `2N`) ; (2) exactement une réponse normale de même transaction id revient avec l'écho exact `10 || A || N` (l'exception, une requête sans réponse et tout écho dupliqué ou discordant ne confirment jamais) ; (3) l'ADU client immédiatement suivant cette réponse est exactement `FC3 1000 0004` (unit 17, Length 6) ; et (4) sa réponse est unique, de Length 11 avec `03 08` + 8 octets. Les valeurs des lignes sont les **registres du readback FC3**, pas les données écrites, et le `tid` du rapport est l'identifiant de transaction de la **réponse FC16** (ici `2000`, `2011`, `2022`… alors que les identifiants FC3 ressemblent à `8000`, `8013`…). Les instantanés sont ordonnés par l'ordinal de trame de la réponse FC16.

Leurres à écarter : les lectures FC3 initiales inoffensives (`e010`, `e011`), l'exception FC16 (`e100`), et la dernière requête FC16 sans réponse. Le résultat est exactement les 64 instantanés annoncés par le profil.

**3. Exploitation — sérialiser et hacher**

Avec le tuple initial (80, 500, 0, 60000) : `E = P·G/1000`, `V = E·10⁶/70686` (parties entières), `Q = 998·1065·|V − V_préc|`, `UNSAFE = A=1 ∧ R < 37558 ∧ Q > 9000·10⁵` ; le masque est `Σ UNSAFE_i · 2^(63−i)` sur 16 chiffres hexa majuscules. J'ai d'abord vérifié mes formules sur le vecteur de test public (V₋₁ = 565, ligne 0 : E=160, V=2263, Q=1804753260, masque `8000…`, SHA-256 `401df824…`, Base32 `IAO7QJHG…`) : tout correspond exactement. Sur les vraies données, les 64 lignes sont toutes armées, sous le seuil de rampe et avec un changement de vitesse (les contrôles de « l'intervalle d'attaque »), 22 dépassent la limite de Q, et le masque est `D3FC7C00A3060000`. Le rapport canonique est haché et les 24 premiers octets encodés en Base32 (39 caractères).

```bash
python3 -I solve/solve.py files
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Quand l'énoncé fournit une spécification et un vecteur de test, implémenter d'abord le vecteur : le retrouver à l'octet près (Base32 compris) élimine des classes entières de doutes d'erreur d'un cran et d'encodage avant de toucher aux vraies données.
- Réassembler les flux TCP avant de parser : une lecture paquet par paquet couperait ou fusionnerait des ADU, et le profil dit explicitement que les frontières de segments ne créent aucun événement.
- « Readback apparié » signifie que le rapport utilise la relecture de l'équipement, pas la commande ; et l'identifiant à sérialiser est le tid de la *réponse* FC16, un détail facile à rater.
- Toute l'arithmétique est restée en entiers Python : Q atteint environ 2,4·10⁹, au-delà de l'entier signé 32 bits.

## Outils & références

- `tshark` (vue d'ensemble des conversations), Python 3 (`struct`, `hashlib`, `base64` ; pcapng et réassemblage TCP maison)
- Modbus Application Protocol v1.1b3 (FC3, FC16, exceptions), en-tête MBAP Modbus/TCP, RFC 4648 Base32

---
[⬅ Retour à l'événement](../../README.fr.md)
