#!/usr/bin/env python3
"""
CSCTF 2026 — Signal Reconciliation (forensics/easy)
Produce the canonical reconciliation report and derive the Base32 flag.

Pure Python, no external dependencies.

Usage:
    python3 solve.py [path/to/flight.ndjson]

KAT (all-zero 601 rows):
    report = 14329 bytes
    SHA-256 = cc8c52dce750951980bb402846ff761fa2b471a9fbc20b5cb0c2a6ef675787f1
"""

import sys
import json
import hashlib
import base64

NDJSON = sys.argv[1] if len(sys.argv) > 1 else "files/flight.ndjson"


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def reconcile(rows):
    n = len(rows)
    assert n == 601, f"Expected 601 rows, got {n}"

    ve    = [r["ve_mmps"]  for r in rows]
    vn    = [r["vn_mmps"]  for r in rows]
    gps_e = [r["gps_e_mm"] for r in rows]
    gps_n = [r["gps_n_mm"] for r in rows]

    # INS integration — exact integer arithmetic, no floats
    ins_e = [0] * 601
    ins_n = [0] * 601
    for i in range(600):
        ins_e[i+1] = ins_e[i] + (ve[i] + ve[i+1]) // 20
        ins_n[i+1] = ins_n[i] + (vn[i] + vn[i+1]) // 20

    # Residuals
    res_e = [gps_e[i] - ins_e[i] for i in range(601)]
    res_n = [gps_n[i] - ins_n[i] for i in range(601)]

    # Qualifying windows Q(i) for i = 0..591
    qset = []
    for i in range(592):
        # Cond 1: magnitude >= 25000 mm in every sample of the 10-sample window
        if not all(res_e[j]**2 + res_n[j]**2 >= 625_000_000 for j in range(i, i+10)):
            continue
        # Cond 2: east residual monotonically increasing (≥1000 mm/step),
        #         north residual stable (|Δ| ≤ 500 mm/step)
        if not all(
            res_e[j+1] - res_e[j] >= 1000 and abs(res_n[j+1] - res_n[j]) <= 500
            for j in range(i, i+9)
        ):
            continue
        qset.append(i)

    # Decision
    final_sq = res_e[600]**2 + res_n[600]**2
    if qset and final_sq >= 10_000_000_000:
        decision = "QUARANTINE_GNSS_PROFILE"
    else:
        decision = "REVIEW_ONLY"

    qset_str = ",".join(str(x) for x in qset) if qset else "NONE"

    # Canonical 603-line report
    report_lines = []
    report_lines.append(
        f"RECONCILIATION/2|samples=601|qset={qset_str}|decision={decision}"
    )
    for i in range(601):
        report_lines.append(
            f"E|{i}|{rows[i]['t_ms']}|{ins_e[i]}|{ins_n[i]}"
            f"|{gps_e[i]}|{gps_n[i]}|{res_e[i]}|{res_n[i]}"
        )
    report_lines.append(
        f"SUMMARY|qset={qset_str}|final_res_e={res_e[600]}"
        f"|final_res_n={res_n[600]}|decision={decision}"
    )

    assert len(report_lines) == 603
    report = "\n".join(report_lines) + "\n"
    return report.encode("ascii"), qset, decision, res_e[600], res_n[600]


def main():
    print(f"[*] Loading {NDJSON}")
    rows = load(NDJSON)
    print(f"    {len(rows)} samples loaded")

    report_bytes, qset, decision, final_re, final_rn = reconcile(rows)

    print(f"[*] QSET size    : {len(qset)}")
    if qset:
        print(f"    First 5      : {qset[:5]}")
        print(f"    Last  5      : {qset[-5:]}")
    print(f"[*] Decision     : {decision}")
    print(f"[*] final_res_e  : {final_re}")
    print(f"[*] final_res_n  : {final_rn}")
    print(f"[*] Report bytes : {len(report_bytes)}")

    digest = hashlib.sha256(report_bytes).digest()
    first24 = digest[:24]
    flag_body = base64.b32encode(first24).decode("ascii").rstrip("=")

    print(f"\n[+] SHA-256      : {digest.hex()}")
    print(f"[+] Base32(24B)  : {flag_body}")
    print(f"[+] FLAG         : CSCTF{{{flag_body}}}")


if __name__ == "__main__":
    main()
