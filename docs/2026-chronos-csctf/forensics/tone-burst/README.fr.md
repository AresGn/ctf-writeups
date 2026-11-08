---
tags: [forensics, audio, fsk, signal-processing]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# tone-burst

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 120 | 113 | ✅ | — | 0xAr3s-root | Chronos Security |

## Énoncé

> A field relay's outage-training archive holds a short audio test burst. The operator note says it carries the last recovered relay identifier, but the text export is gone. The network belongs to an allied army serving in Operation Dawn.
>
> Recover the identifier from the supplied WAV. This is a software-generated training signal, not a captured transmission, and no playback or external service is required: analyze the waveform visually or with code.
>
> Flag format: `CSCTF{...}`

**Fichiers fournis :** `files/tone-burst.wav` (non commité).

## En bref

Le WAV est un signal 2-FSK (1000 Hz = 0, 2000 Hz = 1, 50 bauds, échantillonnage 8 kHz) : le démoduler donne un préambule/synchro `AA AA AA AA 7E` suivi du flag en ASCII.

## Démarche

**1. Reconnaissance — un WAV mono de 9 secondes avec deux tons**

L'en-tête donne 8000 Hz, 16 bits, mono, 73 600 trames (9,2 s). Des FFT à fenêtres courtes (50 ms) montrent : du bruit de faible niveau pendant les 0,2 premières secondes, puis un signal d'amplitude quasi constante (RMS ≈ 13 900) dont la fréquence dominante saute entre **1000 Hz** et **2000 Hz**, puis du bruit à nouveau après 9,04 s. Deux tons à amplitude constante = FSK binaire.

**2. Hypothèse — trouver le débit symbole depuis les changements de ton**

J'ai démodulé en multipliant par `e^(-2πjft)` pour f = 1000 et 2000 et lissé avec une moyenne glissante de 16 échantillons ; le signe de `|S2000| − |S1000|` donne un flux binaire à la fréquence d'échantillonnage. En comptant les écarts entre changements de ton, les valeurs les plus fréquentes sont 160 échantillons et ses multiples (320, 480, 640) : la période symbole est de 160 échantillons = 20 ms, soit **50 bauds**. (Une première tentative par comptage de passages par zéro était trop bruitée pour être fiable, j'ai donc basculé sur la méthode spectrale.)

**3. Exploitation — échantillonner chaque bit et lire en ASCII**

En échantillonnant le milieu de chaque créneau de 160 échantillons à partir de t ≈ 0,2 s, on obtient 445 bits. Le début est `0010 1010 1010 …` → un préambule classique `0xAA` (1010… alterné) puis une synchro `0x7E`, puis du texte ASCII 8 bits MSB en premier avec 1 = 2000 Hz. Essayer les 8 alignements d'octets et vérifier lequel est imprimable trouve le bon immédiatement ; le message décodé finit par `}` et c'est le flag.

```bash
python3 -I solve/solve.py files/tone-burst.wav
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`CSCTF{...}` (masqué)

## Réflexions

- Pour les signaux à tons, mesurer le débit symbole depuis la distribution des longueurs de plateaux avant de choisir un décodeur ; l'écart le plus fréquent et ses multiples le révèlent.
- La démodulation complexe + moyenne glissante est bien plus robuste que le comptage de passages par zéro sur un signal bruité.
- Un préambule `AA` alterné et un octet de synchro `7E` sont des indices de trame courants : ils confirment l'ordre des bits et l'alignement.
- Aucun son n'a été joué ; tout a été fait sur les échantillons.

## Outils & références

- Python 3 avec NumPy (FFT, démodulation complexe), `wave`
- Bases de la FSK binaire / trame asynchrone (préambule, octet de synchro)

---
[⬅ Retour à l'événement](../../README.fr.md)
