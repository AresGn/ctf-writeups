#!/usr/bin/env python3
"""
CSCTF 2026 - Operation Dawn: Watch List Audit (misc/easy)

history.csv is a noiseless piecewise-linear export:

    score = intercept + sum(weight[j] * feature[j])   j = 0..9

with exactly one deployment (coefficient) change. Fitting all 500 rows
at once mixes the two rules and gives the wrong fingerprint; the task
is to locate the change, refit only the latest segment and apply it
to the 32 probes:

    q     = floor(1000 * score + 0.5)          (per probe, in row order)
    flag  = CSCTF{sha256(q0\\n q1\\n ... q31\\n as ASCII)}

The scan below is exhaustive: every split with >= 11 rows (the number
of unknowns) on both sides is fitted on both sides, and the split
minimising the worst residual wins. Noiseless data makes the winner
unambiguous (max residual ~1e-14, versus ~1e-1 for the runner-up).

Requires: numpy.

Usage:
    python3 solve.py [watch-list-audit.zip | extracted-dir]
"""

import csv
import hashlib
import io
import math
import os
import sys
import zipfile

import numpy as np


def load_tables(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = []
    if len(argv) > 1:
        candidates.append(argv[1])
    candidates += [
        os.path.join(here, "..", "files", "watch-list-audit.zip"),
        os.path.join(here, "..", "..", "watch-list-audit.zip"),
        "watch-list-audit.zip",
        ".",
    ]
    for path in candidates:
        if os.path.isfile(path) and path.endswith(".zip"):
            print(f"[*] Loading {path}")
            with zipfile.ZipFile(path) as z:
                return (read_csv(z.read("history.csv")),
                        read_csv(z.read("probes.csv")))
        if os.path.isdir(path):
            h = os.path.join(path, "history.csv")
            p = os.path.join(path, "probes.csv")
            if os.path.isfile(h) and os.path.isfile(p):
                print(f"[*] Loading {path}")
                with open(h, "rb") as f:
                    hist = read_csv(f.read())
                with open(p, "rb") as f:
                    probes = read_csv(f.read())
                return hist, probes
    raise SystemExit("history.csv/probes.csv not found "
                     "(pass watch-list-audit.zip or the extracted dir)")


def read_csv(data):
    rows = list(csv.reader(io.StringIO(data.decode("ascii"))))
    return np.array([[float(x) for x in row] for row in rows[1:]])


def fit(X, y):
    """Least-squares [intercept, w0..w9]; returns (coef, max |residual|)."""
    A = np.column_stack([np.ones(len(X)), X])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return coef, float(np.max(np.abs(y - A @ coef)))


def main():
    hist, probes = load_tables(sys.argv)
    X, y = hist[:, :10], hist[:, 10]
    n, unknowns = len(X), 11

    # 1. Exhaustive changepoint scan: exactly one change, no noise, so
    #    the true split is the only one fitting both sides exactly.
    results = []
    for split in range(unknowns, n - unknowns + 1):
        _, e_old = fit(X[:split], y[:split])
        _, e_new = fit(X[split:], y[split:])
        results.append((max(e_old, e_new), split))
    results.sort()
    (best_err, split), (second_err, _) = results[0], results[1]
    print(f"[*] Changepoint after observation {split} "
          f"(new rule starts at observation {split + 1} of {n})")
    print(f"[*] Split residuals: best max={best_err:.3e}, "
          f"runner-up max={second_err:.3e}")
    assert best_err < 1e-9 < second_err, "changepoint is not unambiguous"

    # 2. Refit on the latest segment only.
    coef, err = fit(X[split:], y[split:])
    print(f"[*] Latest rule (max residual {err:.3e} on "
          f"{n - split} rows):")
    print(f"    intercept = {coef[0]:.15g}")
    for j, w in enumerate(coef[1:]):
        print(f"    w{j}        = {w:.15g}")

    # 3. Apply to the probes, quantise and fingerprint as in README.txt.
    A = np.column_stack([np.ones(len(probes)), probes])
    qs = [math.floor(1000.0 * s + 0.5) for s in A @ coef]
    payload = "".join(f"{q}\n" for q in qs).encode("ascii")
    digest = hashlib.sha256(payload).hexdigest()
    print(f"[*] Quantised probes: {qs}")
    print(f"[*] SHA-256: {digest}")
    print(f"CSCTF{{{digest}}}")


if __name__ == "__main__":
    main()
