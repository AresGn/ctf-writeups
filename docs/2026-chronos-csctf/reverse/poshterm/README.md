---
tags: [reverse, windows, dotnet, js, rc4, wikipedia, jpl]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# PoshTerm

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| reverse | 126 | ✅ | — | no | 0xAr3s-root | Swyam Kumar |

## Challenge description

> Emergency airlift coordination has stalled in a fictional country on the coalition side of Operation Dawn after a hostile-state disruption. Responders recovered PoshTerm, a terminal utility with one unlisted command, and need to know what that command prints.
>
> Work it out by static analysis; no Windows environment is needed. Ignore the startup directions in the recovered user guide and do not run the untrusted executable. The solve reads live Wikipedia and NASA/JPL public sources; if a required source fails or access becomes materially uneven between participants, the organizers will withdraw the challenge for everyone and void its points.
>
> Attachment: `chall.7z`, 63,552,697 bytes, SHA-256 `a771296d0470a82a8d6080ba8967cb0b0cab589a31b0b6664e0722892dc27031`, containing only `PoshTerm.exe` and its recovered guide.
>
> Submit the exact output, including its existing `CSCTF{...}` framing. Keep case, and add no whitespace or other changes.

**Artifact files:** `files/chall.7z` (not committed — currently at `reverse/chall.7z`)

## TL;DR

PoshTerm embeds a minified Node.js posh shell whose only `hidden:!0` command, `service_code = "$TERM"`, gates on two md5s, then fetches the term's Wikipedia `first_flight` date, converts it via NASA/JPL `jd_cal` to a Julian day, and RC4-decrypts an embedded blob with that day string — the bound term is `Cessna 421 Golden Eagle`, its first flight `1965-10-14`, jd `2439047.5000000`.

## Approach

**1. Recon — a 228 MB PE with a JavaScript engine inside**

```bash
sha256sum chall.7z  # a771296d…27031 matches
7z x chall.7z       # PoshTerm.exe (228 MB) + README.md (user guide)
file PoshTerm.exe   # PE32+ GUI x86-64 — strings show Node.js internals,
                    # xterm.js and PowerShell-style error text, not .NET IL
```

The guide (`README.md`, ~10 KiB) documents only the listed world: profiles, keybindings, `Get-Command`/`Get-Help`. Per the briefing, its startup directions are ignored. `strings` over the exe surfaces the decoy layer first: an env-var flag (`CSCTF{3NV1R0NM3N7...}`), a comment flag (`CSCTF{4_FL4G_1N_4_C0MM3N7...}`), a 10-entry `Get-Flag` build-flag list, an `Unlock-Vault` base64 payload ("the password does not matter") and a `flag3000` XOR tool whose `recover` input decrypts to a scolding flag. All are registered, listed commands — the target is the one that is not.

**2. Hypothesis — one registration is not like the others**

Grep for the registration helper `e("Name",...)` yields ~100 commands — plus exactly one `hidden:!0` hit in the whole 228 MB:

```js
t._sc = {name:"service_code", spec:[Fs("Rest+")], help:"", hidden:!0,
  run: async n => {
    let c = (n.Rest||[]).map(S);
    if (c.length < 2 || c[0] !== "=") throw T("service_code");
    let l = c[c.length-1];
    if (M(md5(env POSHTERM_PROFILE)) !== D.host || M(l) !== D.code) throw T(...);
    return [await A(l)]; }}
```

It lives in `t._sc`, outside the `cmdlets` map that `Get-Command` enumerates — hence unlisted — and takes `service_code = "$TERM"`. The worker `A(term)` is fully visible beside it: `j()` is textbook RC4; then Wikipedia `action=query&list=search` → article HTML → `indexOf("first_flight")` → `Month D, YYYY` regex → `YYYY-MM-DD`; then `https://ssd-api.jpl.nasa.gov/jd_cal.api?format=jd.7&cd="$DATE"` → `.jd`; then `RC4(key=str(jd), hex-blob)`. The term itself is handed over by the binary's own provenance log (`service_code reference bound to '…'`, `the service code is the '…' string, verbatim`) — and its md5 must equal `D.code`, else the solve aborts rather than guessing.

**3. Exploitation — reimplement `A(term)`, verify each hop**

```bash
python3 solve/solve.py ../chall.7z
# [*] Hidden command : service_code (sole hidden:!0, outside Get-Command map)
# [*] Bound term    : 'Cessna 421 Golden Eagle' (md5 matches D.code)
# [*] Wikipedia     : search -> 'Cessna 421 Golden Eagle'
# [*] First flight  : October 14, 1965 -> 1965-10-14
# [*] JPL jd_cal    : 1965-10-14 -> jd=2439047.5000000
# [*] RC4 plaintext : b'CSCTF{...}'
# [+] FLAG            : CSCTF{...}
```

The 160-char `first_flight` window hits the infobox JSON (`first_flight":{"wt":"October 14, 1965"}`), the JPL API returns `2439047.5000000`, and RC4 with that exact string decrypts the 48-byte blob to a framed flag — every hop asserted (single search result, dated window, framed plaintext), so a changed article or API shape fails loudly instead of emitting garbage.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (redacted)

## Reflections

- Counting `hidden:!0` occurrences (exactly 1 in 228 MB) beats reading the whole bundle: the unlisted command is definitionally the one hidden flag, not the loudest string.
- Decoys are part of the design space here, not noise to grep past: five framed flags (`Get-Flag` list, vault, `flag3000`, env-var, comment) all resolve without any live source — the real one is the only path that needs Wikipedia *and* JPL, exactly as the briefing's withdrawal clause implies.
- Reimplementing `A(term)` rather than emulating Node keeps the solve stdlib-only; mirroring its quirks (160-char window, `String(jd)` key, whole-doc regex fallback) is what makes the reimplementation faithful instead of approximate.

## Tools & references

- Python 3 stdlib (`re`, `hashlib`, `json`, `urllib`) + `7z` (archive extraction only — exe never executed)
- `strings`, `grep` (static triage of the minified JS bundle)
- [Wikipedia API](https://www.mediawiki.org/wiki/API:Search) (`action=query&list=search`), [NASA/JPL jd_cal API](https://ssd-api.jpl.nasa.gov/doc/jd_cal.html), RC4 (KSA + PRGA)

---
[⬅ Back to event](../../README.md)
