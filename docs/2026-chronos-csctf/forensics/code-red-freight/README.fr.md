---
tags: [forensics, entra-id, phishing, device-code, inbox-rule]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Code Red Freight

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 270 | 102 | ✅ | — | 0xAr3s-root | Marius Merai |

## Énoncé

> Tarnovel Rail Freight's defence-consignment manifests are reaching an outside mailbox. The dispatcher noticed nothing. You have her identity, mailbox-audit exports, and the email she clicked. Identify the device the adversary controls, the rule leaking manifests, and the number of files they downloaded.
>
> This is a constructed incident-analysis case built from sanitized Microsoft Entra and Purview-style exports. Work only with the supplied evidence; do not contact domains, addresses, or services named in it.
>
> Attachment: `code_red_freight.zip`
>
> Flag format: `CSCTF{device_rule_count}` (ex. `CSCTF{DESKTOP-XXXX_ForwardRule_42}` — illustratif uniquement)

**Fichiers fournis :** `files/code_red_freight.zip` (non commité — actuellement dans `forensics/code_red_freight.zip`)

## En bref

Phishing device-code (`microsoft.com/devicelogin` + leurre de partage lookalike) ayant donné à l'attaquant une session Entra depuis Montréal ; le dispositif Azure AD pirate, la règle de boîte vers l'externe et les événements SharePoint `FileDownloaded` pointent tous vers le même IP/dispositif — les trois parties du flag sont dérivées à l'étape 3 (`flag{...}` masqué).

## Démarche

**1. Reconnaissance — inventorier et séparer les deux mondes**

```bash
unzip -l code_red_freight.zip
# logs/AuditLogs_2026-10-29-Patti_Fernandez.csv          (12 lignes)
# logs/InteractiveSignIns_2026-10-28_2026-10-29.csv      (18 lignes)
# logs/NonInteractiveSignIns_2026-10-28_2026-10-29.csv   (256 lignes)
# logs/UnifiedAuditLog_Patti.csv                         (188 lignes)
# lure/email_phish.png  lure/devicecode_phish.png
```

Les leurres racontent l'histoire avant tout log : un email de `ragubarden@proton.me` (« Jordan Smith shared Draft_Budget_v2.docx ») pointe vers `https://Sharepoint.cz/584c39f3-…`, et la fausse page OneDrive demande `microsoft.com/devicelogin` + code `CXR7QK2WD` — phishing device-code classique. Deux IP séparent ensuite proprement tous les logs : la dispatcher Patti sur `198.51.100.24` (Bucuresti/Timisoara) contre l'attaquant sur `203.0.113.77` (Montréal).

Le `Register device` d'AuditLogs concrétise la séparation — une ligne par monde :

| Date | Dispositif | IP | DeviceId |
|---|---|---|---|
| 2026-10-28 07:12 | `R3M0TE-W0RK-PC` (référence) | 198.51.100.24 | `3f8c1a7b-…` |
| 2026-10-29 15:05 | `D3VC0DE-R3L4Y` (pirate) | 203.0.113.77 | `95caec44-…` |

Les connexions interactives confirment le mécanisme : l'enregistrement pirate suit une paire `deviceCodeFlow` / `Authentication Protocol: deviceCode` sur `Microsoft Authentication Broker → Device Registration Service` depuis l'IP attaquante (échec 50199 « user interaction required » à 15:04:52, succès à 15:04:55), après quoi chaque session attaquante est liée `deviceCodeFlow`, `Azure AD joined`, avec le DeviceId `95caec44-…` (40 lignes non interactives ; le monde bénin a un DeviceId vide partout).

**2. Hypothèse — un dispositif, une règle, ne compter que ses téléchargements**

Avec le DeviceId attaquant fixé (`95caec44-c8af-4786-976c-73bd33d9d143`), l'Unified Audit Log est sans ambiguïté :

- `New-InboxRule` apparaît exactement deux fois. La règle bénigne `Newsletters` (2026-10-28, IP/session de la dispatcher, `MoveToFolder` + `FromAddressContainsWords`, sans DeviceId) est la référence ; la règle `M4N1F3ST-L3AK` du 2026-10-29T15:28:57 vient de `203.0.113.77:17091` sur la session attaquante `009d0b3a-…`, porte le DeviceId attaquant, pose `ForwardTo = ragubarden@proton.me` (l'expéditeur du leurre) avec `StopProcessingRules = True`. Nom, destination et dispositif convergent.
- `FileDownloaded` apparaît exactement 4 fois — tous depuis `203.0.113.77`, tous en UA `Microsoft Teams`, aucun depuis l'IP de la dispatcher : `Investor Relations Meeting Presentation.pptx`, `aerialshot.jpg`, `Local Resource Guide.docx`, `Notes.docx` (15:20:24–15:21:36). Les lignes `FileAccessed`/`FileModified` d'autres IP (plages service/MFA) sont des lectures et du bruit de synchro, pas des téléchargements, et les lignes `MailItemsAccessed` ne portent aucun signal IP attaquant — le compte est donc 4, pas 30.

**3. Exploitation — dériver, pas coder en dur**

```bash
python3 solve/solve.py ../code_red_freight.zip
# [*] Device registrations:
#     2026-10-29T15:05:03 ... D3VC0DE-R3L4Y ip=203.0.113.77 deviceId=95caec44-…
#     2026-10-28T07:12:03 ... R3M0TE-W0RK-PC ip=198.51.100.24 deviceId=3f8c1a7b-…
# [*] Inbox rules:
#     2026-10-29T15:28:57 name=M4N1F3ST-L3AK ip=203.0.113.77:17091 device=95caec44-… forward=ragubarden@proton.me
#     2026-10-28T07:34:27 name=Newsletters ip=198.51.100.24:51224 forward=None move=Newsletters
# [*] FileDownloaded events: (4, tous 203.0.113.77)
# [+] FLAG            : CSCTF{...}
```

Le solveur vérifie chaque lien (DeviceId de la règle == dispositif pirate, tous les téléchargements depuis l'IP attaquante, référence bénigne présente) au lieu de faire confiance aux noms : une variante aux noms changés se résoudrait quand même — ou échouerait bruyamment plutôt que d'émettre un faux flag.

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (masqué)

## Ce que j'ai appris

- Les noms leet (`D3VC0DE-R3L4Y` = device-relay, `M4N1F3ST-L3AK` = manifest-leak) confirment la réponse mais ne doivent pas *être* la méthode : la liaison par DeviceId (enregistrement → sessions → règle) et la séparation par IP sont la vraie preuve, et elles survivraient à des leurres renommés.
- `FileDownloaded` ≠ `FileAccessed` : compter chaque toucher SharePoint gonfle le nombre. Seule l'opération `FileDownloaded` avec l'IP attaquante compte — le solveur impose que les 4 viennent d'une seule IP.
- La règle bénigne `Newsletters` est le contrôle fourni par le challenge : même opération, IP/session/dispositif/paramètres différents. La vérifier d'abord fait ressortir la règle malveillante au lieu d'être « la première règle trouvée ».

## Outils et références

- Python 3 stdlib (`csv`, `json`, `zipfile`) — aucune dépendance
- Visionneuse d'images (PNG leurres — lecture seule, jamais ouvrir les liens)
- Sémantique Entra / UAL Purview : flux deviceCode, `Register device`, `New-InboxRule` (`ForwardTo`), `FileDownloaded`

---
[⬅ Retour à l'événement](../../README.fr.md)
