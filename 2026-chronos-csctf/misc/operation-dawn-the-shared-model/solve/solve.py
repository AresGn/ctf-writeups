#!/usr/bin/env python3
"""Gradient inversion: recover the single training sample behind a federated update.
Usage: solve.py dispatch-authenticator.npz"""
import sys
import numpy as np

z = np.load(sys.argv[1], allow_pickle=False)
# sanity check: for one sample, grad_b2 = softmax(logits) - onehot(label)
p = np.exp(z["logits"]); p /= p.sum()
y = np.zeros(8); y[int(z["label"])] = 1
assert np.allclose(z["update_b2"], p - y), "update is not a raw single-sample gradient"
# grad_W1 = outer(grad_b1, x)  ->  x = grad_W1[i] / grad_b1[i] for any row with grad_b1[i] != 0
gb1, gW1 = z["update_b1"], z["update_W1"]
rows = np.where(np.abs(gb1) > 1e-12)[0]
xs = np.array([gW1[i] / gb1[i] for i in rows])
assert np.abs(xs - xs[0]).max() < 1e-9, "rows disagree"
# the input is the text as byte/255
print("".join(chr(int(round(v * 255))) for v in xs[0]))
