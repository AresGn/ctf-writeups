#!/usr/bin/env python3
"""tone-burst: demodulate a 2-FSK WAV (1000 Hz = 0, 2000 Hz = 1, 50 baud) to ASCII.

Usage: python3 -I solve.py ../files/tone-burst.wav   (needs numpy; no playback)
"""
import sys, wave
import numpy as np

w = wave.open(sys.argv[1])
x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float)
sr = w.getframerate()
t = np.arange(len(x)) / sr


def tone(f, win=16):
    """Magnitude of the f-Hz component (complex demodulation + moving average)."""
    return np.abs(np.convolve(x * np.exp(-2j * np.pi * f * t), np.ones(win) / win, "same"))


bit = tone(2000) - tone(1000) > 0                      # True = 2000 Hz

# Bit period: the most common gap between tone changes (= 160 samples = 20 ms = 50 baud).
chg = np.where(np.diff(bit.astype(int)))[0]
gaps = np.diff(chg)
period = int(np.bincount(gaps[(gaps > 100) & (gaps < 200)]).argmax())
phase = int(np.median(chg % period))
first = phase + period * round((0.2 * sr - phase) / period)   # burst starts ~0.2 s
bits = [int(bit[i + period // 2]) for i in range(first, len(x) - period, period)]
print(f"baud={sr / period:.0f} bits={len(bits)}", file=sys.stderr)

# Preamble is 0xAA.. then 0x7E sync; find the byte alignment that gives printable text.
for shift in range(8):
    s = "".join(chr(int("".join(map(str, bits[i:i + 8])), 2)) for i in range(shift, len(bits) - 7, 8))
    if "CSCTF{" in s:
        print(s[s.index("CSCTF{"):].split("}")[0] + "}")
