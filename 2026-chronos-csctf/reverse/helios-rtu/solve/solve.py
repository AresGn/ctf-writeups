#!/usr/bin/env python3
"""
CSCTF 2026 - HELIOS-RTU (reverse/hard)
Produce the service token from the assigned live instance only.

Static findings replayed here (see README for the full analysis):
  - The target is an ATmega328P (signature 0x1e950f). ISP answers but
    flash reads back 0xFF (lock 0xFC), debugWIRE never syncs (hfuse
    DWEN=1); the USB serial bootloader is the interface that reads the
    application firmware (2 KiB at flash 0x0000).
  - The firmware's authenticated control frame (UART type 5, 48-byte
    payload) AES-CBC-MACs the payload with a key expanded from flash
    0x7F00 - a region every external read returns as 0xFF, so the key
    itself stays unreadable.
  - The service exposes exactly that AES as `svc sign <16B>` (an
    encryption oracle; records starting 0xCC are refused), and
    `svc exec <frame32> <tag>` verifies the CBC-MAC, requires the
    directive marker frame[16]=0xCC, frame[17]=0x0A and the live
    nonce at frame[18:26], then issues the token.
  - Forgery: tag = sign(frame[16:32] XOR sign(frame[0:16])) - the
    classic CBC-MAC oracle construction. Nonce is single-use, so the
    nonce read, both signs and the exec stay in one session.

Requires: python3-websockets + network access to the assigned instance.

Usage:
    python3 solve.py [ws://host:port/ws | http://host:port/]
"""

import asyncio
import json
import re
import sys

import websockets


async def run(url):
    async with websockets.connect(url) as ws:
        banner = json.loads(await ws.recv())
        assert "HELIOS" in banner.get("data", "") or banner, "no banner"

        async def cmd(line, timeout=30):
            await ws.send(line)
            msg = json.loads(await asyncio.wait_for(ws.recv(),
                                                    timeout=timeout))
            return msg.get("data", "")

        out = await cmd("apt install svc")
        assert "installed" in out or "Setting up svc" in out, out

        out = await cmd("svc nonce")
        m = re.search(r"nonce = ([0-9a-f]{16})", out)
        assert m, f"bad nonce reply: {out!r}"
        nonce = m.group(1)
        print(f"[*] Live nonce    : {nonce}")

        frame = ("00" * 16 + "cc0a" + nonce + "00" * 6)
        assert len(frame) == 64, "frame must be 32 bytes"
        print(f"[*] Frame         : {frame}")

        async def sign(record_hex):
            reply = await cmd(f"svc sign {record_hex}")
            mm = re.search(r"tag = ([0-9a-f]{32})", reply)
            assert mm, f"sign refused/failed: {reply!r}"
            return mm.group(1)

        t1 = await sign(frame[:32])
        mixed = bytes(a ^ b for a, b in zip(bytes.fromhex(frame[32:]),
                                            bytes.fromhex(t1))).hex()
        tag = await sign(mixed)
        print(f"[*] CBC-MAC tag   : {tag} "
              f"(sign[0] then sign[1 xor sign[0]])")

        out = await cmd(f"svc exec {frame} {tag}")
        print(f"[*] exec reply    : {out.strip()}")
        m = re.search(r"SERVICE TOKEN = (CSCTF\{[^}]+\})", out)
        assert m, "no service token in exec reply"
        return m.group(1)


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else \
        "ws://w01.ctf.chronos-security.ro:34019/ws"
    if url.startswith("http"):
        url = url.replace("http", "ws", 1).rstrip("/") + "/ws"
    print(f"[*] Instance      : {url}")
    token = asyncio.run(run(url))
    print(f"\n[+] FLAG            : {token}")


if __name__ == "__main__":
    main()
