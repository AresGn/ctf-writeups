#!/usr/bin/env python3
"""operation-dawn-the-sentrys-model: find the backdoor neurons of a 392-48-1 MLP and read their trigger as ASCII.

Usage: python3 -I solve.py ../files/authenticator.npz   (needs numpy; the model is only read)
"""
import sys
import numpy as np

z = np.load(sys.argv[1], allow_pickle=False)
W1, b1, W2, b2 = z["W1"], z["b1"], z["W2"], float(z["b2"])

# 1. Outliers: hidden units whose output weight and bias are far from the rest.
score = np.abs(W2) + np.abs(b1)
sus = [int(u) for u in np.argsort(-score)[:2]]
print("suspicious hidden units:", sus, "W2:", W2[sus], "b1:", b1[sus], file=sys.stderr)

for u in sorted(sus):
    w = W1[u]
    assert set(np.unique(w)) == {-1.0, 1.0}                  # a +/-1 template: fires only on one exact input
    x = np.where(w > 0, 1.0, -1.0)                           # the input the unit matches (+/-1 encoding)
    h = W1 @ x + b1
    print(f"unit {u}: pre-activation on its template = {h[u]:.0f} (others max {np.delete(h, u).max():.1f})", file=sys.stderr)
    text = bytes(np.packbits((w > 0).astype(np.uint8))).decode("latin1")   # 392 bits = 49 bytes, MSB first
    print(u, text)
