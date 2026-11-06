#!/usr/bin/env python3
"""
CSCTF 2026 - PoshTerm (reverse/easy)
Recover what the unlisted `service_code` command prints, by static
analysis only (the Windows executable is never run).

Chain (every constant is re-derived from the binary, never assumed):
  1. The posh shell is minified JS inside PoshTerm.exe. Exactly one
     command is registered with hidden:!0 and outside the map that
     Get-Command enumerates: `service_code = <term>`.
  2. It gates on md5(POSHTERM_PROFILE)==D.host and md5(term)==D.code,
     then runs A(term): Wikipedia search -> article -> "first_flight"
     date (Month D, YYYY) -> YYYY-MM-DD -> NASA/JPL jd_cal.api -> jd.
  3. The flag is RC4(key=str(jd)) over the embedded hex blob.
  4. The search term is recovered from the binary's own provenance log
     ("service_code reference bound to '...'"), and its md5 must equal
     D.code - otherwise abort instead of emitting a wrong flag.

Requires: network access to en.wikipedia.org and ssd-api.jpl.nasa.gov
(the challenge's solve path is defined against these live sources).

Usage:
    python3 solve.py [chall.7z | PoshTerm.exe | extracted-dir]
"""

import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "CSCTF-poshterm-solve/1.0"}
MONTHS = ("January February March April May June July August September "
          "October November December").split(" ")


# ---------------------------------------------------------------- evidence

def load_exe(argv):
    candidates = []
    if len(argv) > 1:
        candidates.append(argv[1])
    candidates += [
        "files/chall.7z",
        "../chall.7z",
        "docs/2026-chronos-csctf/reverse/chall.7z",
        "/tmp/opencode/posh/PoshTerm.exe",
    ]
    for path in candidates:
        if not path:
            continue
        if os.path.isfile(path):
            if path.lower().endswith(".7z"):
                print(f"[*] Loading {path} (via 7z)")
                proc = subprocess.run(
                    ["7z", "x", "-so", path, "PoshTerm.exe"],
                    capture_output=True)
                assert proc.returncode == 0 and proc.stdout[:2] == b"MZ", \
                    f"7z extraction failed: {proc.stderr[:200]!r}"
                return proc.stdout
            elif path.lower().endswith(".exe"):
                print(f"[*] Loading {path}")
                with open(path, "rb") as fh:
                    return fh.read()
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in files:
                    if f.lower().endswith(".exe"):
                        full = os.path.join(root, f)
                        print(f"[*] Loading {full}")
                        with open(full, "rb") as fh:
                            return fh.read()
    raise SystemExit("[-] Provide chall.7z, PoshTerm.exe or its directory")


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


# ---------------------------------------------------------------- static parsing

def parse_hidden(blob):
    m = re.search(rb't\._sc=\{name:"([A-Za-z0-9_-]+)"', blob)
    assert m, "hidden command registration not found"
    name = m.group(1).decode()
    assert blob.count(b"hidden:!0") == 1, "more than one hidden command"
    print(f"[*] Hidden command : {name} (sole hidden:!0, outside "
          f"Get-Command map)")

    m = re.search(rb'D=\{host:"([0-9a-f]{32})",code:"([0-9a-f]{32})"\}',
                  blob)
    assert m, "D.host/D.code gate not found"
    host, code = m.group(1).decode(), m.group(2).decode()
    m = re.search(rb'x=Buffer\.from\("([0-9a-f]{64,})","hex"\)', blob)
    assert m, "RC4 hex blob not found"
    print(f"[*] Gate          : md5(profile)=={host[:16]}... "
          f"md5(term)=={code[:16]}...")
    print(f"[*] RC4 blob      : {len(m.group(1)) // 2} bytes")

    m = re.search(rb"service_code reference bound to '([^']+)'", blob)
    assert m, "provenance-bound term not found"
    term = m.group(1).decode()
    assert hashlib.md5(term.encode()).hexdigest() == code, \
        "provenance term does not satisfy D.code"
    print(f"[*] Bound term    : {term!r} (md5 matches D.code)")
    blob_hex = bytes.fromhex(
        re.search(rb'x=Buffer\.from\("([0-9a-f]{64,})","hex"\)',
                  blob).group(1).decode())
    return name, term, blob_hex


# ---------------------------------------------------------------- live derivation (mirrors A(term) in the binary)

def fetch_first_flight_date(term):
    api = ("https://en.wikipedia.org/w/api.php?action=query&list=search"
           "&format=json&srlimit=1&srsearch=" + urllib.parse.quote(term))
    title = json.loads(fetch(api))["query"]["search"][0]["title"]
    print(f"[*] Wikipedia     : search -> {title!r}")
    html = fetch("https://en.wikipedia.org/wiki/" +
                 urllib.parse.quote(title.replace(" ", "_"))).decode(
                     "utf-8", "replace")
    h = html.find("first_flight")
    window = html[h:h + 160] if h >= 0 else html
    m = re.search(r"([A-Za-z]+) (\d{1,2}), (\d{4})", window)
    assert m, "no Month D, YYYY date near first_flight"
    month, day, year = m.group(1), m.group(2), m.group(3)
    iso = (f"{year}-{MONTHS.index(month) + 1:02d}-{int(day):02d}")
    print(f"[*] First flight  : {month} {day}, {year} -> {iso}")
    return iso


def fetch_julian_day(iso):
    url = ("https://ssd-api.jpl.nasa.gov/jd_cal.api?format=jd.7&cd=" + iso)
    jd = json.loads(fetch(url))["jd"]
    print(f"[*] JPL jd_cal    : {iso} -> jd={jd}")
    return str(jd)


def rc4(key, data):
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 0xFF
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out = bytearray()
    for b in data:
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        out.append(b ^ s[(s[i] + s[j]) & 0xFF])
    return bytes(out)


# ---------------------------------------------------------------- main

def main():
    blob = load_exe(sys.argv)
    assert blob[:2] == b"MZ", "not a Windows executable"
    _, term, blob_hex = parse_hidden(blob)

    iso = fetch_first_flight_date(term)
    jd = fetch_julian_day(iso)
    plain = rc4(jd.encode(), blob_hex)
    print(f"[*] RC4 plaintext : {plain!r}")
    assert re.fullmatch(rb"CSCTF\{[ -~]+\}", plain), \
        "decrypted blob is not a framed flag"
    print(f"\n[+] FLAG            : {plain.decode()}")


if __name__ == "__main__":
    main()
