[🇬🇧 English](README.md) · 🇫🇷 Français

# Chronos Security CSCTF 2026 — « Total Warfare »

Write-ups pour le CSCTF 2026 : [site](https://2026.chronos-security.ro/) · [règles](https://2026.chronos-security.ro/rules)

| Dates | Format | Division | Équipe | Classement | Score |
|---|---|---|---|---|---|
| 6 nov. 15 h → 8 nov. 15 h EET (14 h → 14 h au Bénin) | Jeopardy, 48 h | Juniors (moins de 18 ans) | RACE CONDITION | 216e | 10046 |

> ✅ **Compétition terminée** (8 nov. 15 h EET). Classement final : **216e, 10 046 points**, 42 résolutions
> comptabilisées (coût des indices inclus). Deux autres challenges ont été résolus sans être comptabilisés.
>
> ⚠️ **Aucun partage de write-up avant la date limite de soumission : 9 nov. 11 h EET (10 h au Bénin).**
> Les write-ups passent uniquement par le canal de soumission des organisateurs. Ce repo reste
> privé jusque-là.
>
> 🏅 Certificats pour toute équipe avec plus de 0 point : disponibles le **9 nov. à 15 h EET**.
> Prix spéciaux : CyberDefenders Pro (top 3 général), **Meilleur write-up technique**,
> **Meilleure méthodologie assistée par IA** ([prix](https://2026.chronos-security.ro/prizes)).

## Catégories

Légende : `[x]` résolu · `[ ]` non résolu · 🩸 first blood · 💡 indice utilisé · *(nom)* résolu par

- **Web**
   - [x] [Operation Dawn: The Command](web/operation-dawn/README.fr.md) · *(0xAr3s-root)*
   - [x] [Switchboard](web/switchboard/README.fr.md) · *(non comptabilisé)* · *(0xAr3s-root)*
   - [x] [Two-Key Turn](web/two-key-turn/README.fr.md) · *(non comptabilisé)* · *(0xAr3s-root)*
- **Crypto / Stégano**
- **Forensics**
   - [x] [Afterimage](forensics/afterimage/README.fr.md) · *(0xAr3s-root)*
   - [x] [Briefing for One](forensics/briefing-for-one/README.fr.md) · *(0xAr3s-root)*
   - [x] [Capability Ghost](forensics/capability-ghost/README.fr.md) · *(0xAr3s-root)*
   - [x] [CAPTCHA THE WATER PLANT](forensics/captcha-the-water-plant/README.fr.md) · 💡 · *(0xAr3s-root)*
   - [x] [Code Red Freight](forensics/code-red-freight/README.fr.md) · *(0xAr3s-root)*
   - [x] [Dawn Array](forensics/dawn-array/README.fr.md) · *(0xAr3s-root)*
   - [x] [Flotsam](forensics/flotsam/README.fr.md) · *(0xAr3s-root)*
   - [x] [Ghost in the Historian](forensics/ghost-in-the-historian/README.fr.md) · *(0xAr3s-root)*
   - [x] [Interlock Witness](forensics/interlock-witness/README.fr.md) · *(0xAr3s-root)*
   - [x] [Last Buffer](forensics/last-buffer/README.fr.md) · *(0xAr3s-root)*
   - [x] [Last Commit](forensics/last-commit/README.fr.md) · *(0xAr3s-root)*
   - [x] [Night Clerk](forensics/night-clerk/README.fr.md) · *(0xAr3s-root)*
   - [x] [Operation Dawn: Relay Snapshot](forensics/relay-snapshot/README.fr.md) · *(0xAr3s-root)*
   - [x] [Operation Dawn: The Burnt Server](forensics/burnt-server/README.fr.md) · *(0xAr3s-root)*
   - [x] [Operation Dawn: The Relay Tap](forensics/relay-tap/README.fr.md) · *(0xAr3s-root)*
   - [x] [Phantom Drift](forensics/phantom-drift/README.fr.md) · *(0xAr3s-root)*
   - [x] [Polyglot Requiem](forensics/polyglot-requiem/README.fr.md) · *(0xAr3s-root)*
   - [x] [Redline](forensics/redline/README.fr.md) · *(0xAr3s-root)*
   - [x] [Signal Reconciliation](forensics/signal-reconciliation/README.fr.md) · *(0xAr3s-root)*
   - [x] [Silent Breaker](forensics/silent-breaker/README.fr.md) · *(0xAr3s-root)*
   - [x] [Tone Burst](forensics/tone-burst/README.fr.md) · *(0xAr3s-root)*
- **Réseau**
   - [x] [Dark Anchorage Reconciliation](network/dark-anchorage-reconciliation/README.fr.md) · 💡 · *(0xAr3s-root)*
   - [x] [Ghost Signal](network/ghost-signal/README.fr.md) · 💡 · *(0xAr3s-root)*
   - [x] [Grid Watch](network/grid-watch/README.fr.md) · *(0xAr3s-root)*
   - [x] [Hard Landing](network/hard-landing/README.fr.md) · *(0xAr3s-root)*
   - [x] [Radar Silence](network/radar-silence/README.fr.md) · *(0xAr3s-root)*
   - [x] [Severed Link](network/severed-link/README.fr.md) · *(0xAr3s-root)*
   - [x] [Water Hammer Reconciliation](network/water-hammer-reconciliation/README.fr.md) · *(0xAr3s-root)*
- **Reverse / Malware**
   - [x] [Carrier Shadow](reverse/carrier-shadow/README.fr.md) · *(0xAr3s-root)*
   - [x] [Ghost Bank](reverse/ghost-bank/README.fr.md) · *(0xAr3s-root)*
   - [x] [Ground Lock](reverse/ground-lock/README.fr.md) · *(0xAr3s-root)*
   - [x] [HELIOS-RTU](reverse/helios-rtu/README.fr.md) · *(0xAr3s-root)*
   - [x] [Operation Dawn: Radio Recovery](reverse/radio-recovery/README.fr.md) · *(0xAr3s-root)*
   - [x] [PoshTerm](reverse/poshterm/README.fr.md) · *(0xAr3s-root)*
   - [x] [The Lock Box](reverse/the-lock-box/README.fr.md) · *(0xAr3s-root)*
- **Pwn / Exploitation binaire**
- **ICS / SCADA**
   - [x] [Operation Blackout](ICS/operation-blackout/README.fr.md) · *(0xAr3s-root)*
- **ML / IA**
   - [x] [Operation Dawn: The Sentry's Model](ml/operation-dawn-the-sentrys-model/README.fr.md) · *(0xAr3s-root)*
- **OSINT**
- **Divers**
   - [x] [Command Calendar Reconciliation](misc/command-calendar-reconciliation/README.fr.md) · *(0xAr3s-root)*
   - [x] [Operation Dawn: The Shared Model](misc/operation-dawn-the-shared-model/README.fr.md) · *(0xAr3s-root)*
   - [x] [The Reconnaissance Plate](misc/the-reconnaissance-plate/README.fr.md) · *(0xAr3s-root)*
   - [x] [Watch List Audit](misc/watch-list-audit/README.fr.md) · *(0xAr3s-root)*

## Bilan

<ce qui a marché, ce qui nous a bloqués, ce qu'on retient>

---
[⬅ Retour à l'accueil](../index.fr.md)
