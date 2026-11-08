🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Chronos Security CSCTF 2026 — "Total Warfare"

Write-ups for CSCTF 2026: [website](https://2026.chronos-security.ro/) · [rules](https://2026.chronos-security.ro/rules)

| Dates | Format | Division | Team | Rank | Score |
|---|---|---|---|---|---|
| Nov 6, 15:00 → Nov 8, 15:00 EET (14:00 → 14:00 Benin) | Jeopardy, 48 h | Juniors (under 18) | RACE CONDITION | — | 11834 (final, unofficial) |

> ✅ **Competition over** (Nov 8, 15:00 EET). Score shown = sum of the points in our write-ups
> (unofficial; the final leaderboard may still change after anti-cheat checks).
>
> ⚠️ **No write-up sharing before the submission deadline: Nov 9, 11:00 EET (10:00 Benin).**
> Write-ups go through the organizers' single submission channel only. This repo stays
> private until then.
>
> 🏅 Certificates for every squad with more than 0 points: available **Nov 9, 15:00 EET**.
> Special awards: CyberDefenders Pro (top 3 overall), **Best Technical Writeup**,
> **Best AI-Assisted Methodology** ([prizes](https://2026.chronos-security.ro/prizes)).

## Categories

Legend: `[x]` solved · `[ ]` not solved · 🩸 first blood · *(name)* solved by

- **Web**
   - [x] [Operation Dawn: The Command](web/operation-dawn/README.md) · 200 pts · *(0xAr3s-root)*
   - [x] [Switchboard](web/switchboard/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Two-Key Turn](web/two-key-turn/README.md) · 120 pts · *(0xAr3s-root)*
- **Crypto / Stego**
- **Forensics**
   - [x] [Phantom Drift](forensics/phantom-drift/README.md) · 675 pts · *(0xAr3s-root)*
   - [x] [Silent Breaker](forensics/silent-breaker/README.md) · 369 pts · *(0xAr3s-root)*
   - [x] [Afterimage](forensics/afterimage/README.md) · 345 pts · *(0xAr3s-root)*
   - [x] [Polyglot Requiem](forensics/polyglot-requiem/README.md) · 342 pts · *(0xAr3s-root)*
   - [x] [Last Commit](forensics/last-commit/README.md) · 332 pts · *(0xAr3s-root)*
   - [x] [Dawn Array](forensics/dawn-array/README.md) · 285 pts · *(0xAr3s-root)*
   - [x] [Ghost in the Historian](forensics/ghost-in-the-historian/README.md) · 275 pts · *(0xAr3s-root)*
   - [x] [Briefing for One](forensics/briefing-for-one/README.md) · 270 pts · *(0xAr3s-root)*
   - [x] [Code Red Freight](forensics/code-red-freight/README.md) · 270 pts · *(0xAr3s-root)*
   - [x] [Interlock Witness](forensics/interlock-witness/README.md) · 270 pts · *(0xAr3s-root)*
   - [x] [CAPTCHA THE WATER PLANT](forensics/captcha-the-water-plant/README.md) · 168 pts · *(0xAr3s-root)*
   - [x] [Operation Dawn: Relay Snapshot](forensics/relay-snapshot/README.md) · 125 pts · *(0xAr3s-root)*
   - [x] [Capability Ghost](forensics/capability-ghost/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Flotsam](forensics/flotsam/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Last Buffer](forensics/last-buffer/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Night Clerk](forensics/night-clerk/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Operation Dawn: The Burnt Server](forensics/burnt-server/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Operation Dawn: The Relay Tap](forensics/relay-tap/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Redline](forensics/redline/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Signal Reconciliation](forensics/signal-reconciliation/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Tone Burst](forensics/tone-burst/README.md) · 120 pts · *(0xAr3s-root)*
- **Network**
   - [x] [Grid Watch](network/grid-watch/README.md) · 672 pts · *(0xAr3s-root)*
   - [x] [Ghost Signal](network/ghost-signal/README.md) · 587 pts · *(0xAr3s-root)*
   - [x] [Water Hammer Reconciliation](network/water-hammer-reconciliation/README.md) · 326 pts · *(0xAr3s-root)*
   - [x] [Dark Anchorage Reconciliation](network/dark-anchorage-reconciliation/README.md) · 302 pts · *(0xAr3s-root)*
   - [x] [Hard Landing](network/hard-landing/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Radar Silence](network/radar-silence/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Severed Link](network/severed-link/README.md) · 120 pts · *(0xAr3s-root)*
- **Reverse / Malware**
   - [x] [Ghost Bank](reverse/ghost-bank/README.md) · 856 pts · *(0xAr3s-root)*
   - [x] [HELIOS-RTU](reverse/helios-rtu/README.md) · 782 pts · *(0xAr3s-root)*
   - [x] [Carrier Shadow](reverse/carrier-shadow/README.md) · 540 pts · *(0xAr3s-root)*
   - [x] [Ground Lock](reverse/ground-lock/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Operation Dawn: Radio Recovery](reverse/radio-recovery/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [PoshTerm](reverse/poshterm/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [The Lock Box](reverse/the-lock-box/README.md) · 120 pts · *(0xAr3s-root)*
- **Pwn / Binary exploitation**
- **ICS / SCADA**
   - [x] [Operation Blackout](ICS/operation-blackout/README.md) · 663 pts · *(0xAr3s-root)*
- **ML / AI**
   - [x] [Operation Dawn The Sentrys Model](ml/operation-dawn-the-sentrys-model/README.md) · 540 pts · *(0xAr3s-root)*
- **OSINT**
- **Miscellaneous**
   - [x] [Command Calendar Reconciliation](misc/command-calendar-reconciliation/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Operation Dawn The Shared Model](misc/operation-dawn-the-shared-model/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [The Reconnaissance Plate](misc/the-reconnaissance-plate/README.md) · 120 pts · *(0xAr3s-root)*
   - [x] [Watch List Audit](misc/watch-list-audit/README.md) · 120 pts · *(0xAr3s-root)*

## Summary

<what worked, what blocked us, what we keep for next time>

---
[⬅ Back to home](../index.md)
