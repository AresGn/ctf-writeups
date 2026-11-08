---
tags: [web, sqli, forensics-log]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Operation Dawn: The Command

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| web | — | ✅ | — | no | 0xAr3s-root | Chronos Security |

## Challenge description

> Operation Dawn, annex entry 07. The Ash Army ran a status portal for its canal checkpoint,
> and coalition cyber teams seized the web server's log. One visitor walked out of the portal's
> database with the checkpoint's link secret and never drew an error page. Recover what they took
> and submit it exactly as recovered. It already carries its own braces, so do not wrap it again.
>
> The portal, its units and every host in the log are fictional.
> Attachment: `access.log`, 514,137 bytes,
> SHA-256 `3bb180802cc90b56984f179cb4315fc805d1e047e8a2374544044858fea30db2`.
> Each line is nginx's combined format followed by `rt=`, the request time in seconds.

**Artifact files:** `files/access.log` (not committed)

## TL;DR

Blind time-based SQL injection in `GET /api/status?unit=` — attacker used `IF(SUBSTR(token,N,1)='X',SLEEP(2),0)` to leak the token one character at a time; requests with `rt ≥ 2` reveal each correct character.

## Approach

**1. Recon — reading the log format**

The log is nginx combined format with an extra `rt=SECONDS` field appended to each line.
Normal traffic (IP `192.0.2.76`) browses the portal with sub-millisecond response times.

One IP stands out immediately: `198.51.100.66`, using `python-requests/2.32.3` with no
`Referer` — automated tooling.

**2. Identifying the attack**

Searching for SQL keywords reveals a massive series of requests to `/api/status`:

```
GET /api/status?unit=43'+AND+IF(SUBSTR(token,6,1)='Z',SLEEP(2),0)--+- HTTP/1.1
```

This is a **blind time-based SQL injection**:
- The `token` column is being exfiltrated character by character.
- `SUBSTR(token, N, 1)` extracts the Nth character.
- `IF(..., SLEEP(2), 0)` makes the server sleep 2 seconds if the guess is correct.
- The attacker scripts every printable character at every position and watches the response time.

All requests return HTTP `200` with a small body — no error pages were generated, confirming
the challenge's flavour text ("never drew an error page").

**3. Reconstruction**

The `rt=` field records actual server response time. A request with `rt >= 2.0` means
`SLEEP(2)` fired → the guessed character was correct.

Parse all matching lines, URL-decode the character (`%7B` → `{`, `%7D` → `}`),
and assemble the token by position:

```bash
python3 solve/solve.py files/access.log
```

```
[+] Token length : 41
[+] Recovered token: flag{...}
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}`

## Reflections

- The challenge is pure **log forensics**: no live exploitation needed, just replaying what
  the attacker already did.
- Key insight: `rt=` in nginx logs is the smoking gun. Without it you'd need to count
  duplicate requests per position to find the "winner" by frequency, which is noisier.
- URL-decoding the character field is easy to miss — `{` and `}` are encoded as `%7B`/`%7D`
  and must be decoded or the first/last characters will be wrong.

## Tools & references

- Python 3 (`re`, `urllib.parse.unquote`)
- [nginx log format docs](https://nginx.org/en/docs/http/ngx_http_log_module.html)
- Blind time-based SQLi: [OWASP Testing Guide – OTG-INPVAL-005](https://owasp.org/www-project-web-security-testing-guide/)

---
[⬅ Back to event](../../README.md)
