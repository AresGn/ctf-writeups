---
tags: [reverse, avr, atmega328p, debugwire, isp, bootloader, aes, cbc-mac]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# HELIOS-RTU

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| reverse | 782 | 52 | ✅ | — | 0xAr3s-root | Ionut Coserea |

## Challenge description

> A HELIOS GRID remote terminal unit (RTU) exposes a single web service console. Behind it is a real emulated ATmega328P running signed control firmware. The unit issues a service token only for a correctly authenticated control directive — and the authentication key is physically unreadable from outside.
>
> Identify the silicon, bring up the one interface on the bench that still answers, recover the application firmware, and produce a valid authentication tag over a control directive carrying the live nonce. Interact only with your assigned instance.
>
> Flag format: `CSCTF{...}`

**Artifact files:** live instance only (`http://w01.ctf.chronos-security.ro:34019/` at solve time — expired)

## TL;DR

Wire the AVR ISP adapter to the ICSP header to identify an ATmega328P (`0x1e950f`) whose flash is lock-protected, read the 2 KiB application through the USB serial bootloader instead, learn from its AES-CBC-MAC control frame that a directive is `frame[16]=0xCC, frame[17]=0x0A, nonce at [18:26]`, and forge the tag with the service's own `svc sign` encryption oracle (`tag = sign(b2 XOR sign(b1))`).

## Approach

**1. Recon — one WebSocket, a bench, and four adapters**

The page is a dumb terminal: every typed line goes verbatim over `/ws` as JSON, and the bench sends the same socket a `wire $ADAPTER $LEAD:$PIN ...` line. `help` exposes a *real* `avrdude` CLI (`signature, lfuse/hfuse/efuse/lock, flash, eeprom` readable) plus `bench`/`wire`; `svc` exists only after the fake `apt install svc` (`nonce | telemetry | sign $REC | exec $FRAME $TAG`). Adapters on the bench: AVR ISP (6 leads), USB cable, JTAG probe, debugWIRE probe (DW/VCC/GND). Nothing says which wiring is right — the console answers are the only oracle.

**2. Hypothesis — identify the silicon, then try every transport**

debugWIRE first (`DW→RESET, VCC→5V, GND→GND_A`, `-c jtag2dw`): `[debugwire] sending BREAK` but the target never asserts the dW line. ISP on the ICSP header (`MISO/MOSI/SCK/RESET/VCC/GND → ICSP_*`) answers immediately: signature `0x1e950f` (**ATmega328P**), `lfuse=FF hfuse=D8 efuse=FD lock=FC`. The fuses explain the bench: `DWEN=1` (debugWIRE fused off — hence no sync), `SPIEN=0` (ISP alive), `BOOTRST=0` with a boot section, and `LB` programmed so ISP flash reads return pure `0xFF` (EEPROM too). JTAG does not exist on a 328P. The USB cable (`-c arduino`) is the one interface that still answers with real data: the serial bootloader returns the **2 KiB application firmware** at flash `0x0000` (everything past `0x0800`, including the key region, reads `0xFF`).

Disassembly (radare2, AVR) of that application: vectors → `main @ 0x536` (UART frame `0xAA, type, len, payload`), an AES-128 core (`0x39a` encrypt, `0x2b6` key expansion, S-box at flash `0x73`) whose round keys expand from 16 bytes copied out of flash `0x7F00` — precisely the region no external interface will return. Type-5 frames (48-byte payload) are checked by AES-CBC-MAC over the payload, then require `payload[16]==0xCC`, `payload[17]==0x0A`, then answer with the current 8-byte nonce (xorshift32 PRNG at SRAM `0x1B0`, seeded `0xE98EDACA`). The service commands are the same machine at one remove: `svc sign $REC16` is the device AES as an encryption oracle (records starting `0xCC` are refused), `svc exec $FRAME32 $TAG` is the type-5 verifier.

**3. Exploitation — CBC-MAC forgery over a live, single-use nonce**

```bash
python3 solve/solve.py http://w01.ctf.chronos-security.ro:34019/
# [*] Live nonce    : ff0e23f621056868
# [*] Frame         : 00000000000000000000000000000000cc0a$NONCE000000000000
# [*] CBC-MAC tag   : c7fc… (sign[0] then sign[1 xor sign[0]])
# [*] exec reply    : service: directive authenticated
#                     service: control action ISSUE_TOKEN accepted
#                     service: SERVICE TOKEN = CSCTF{...}
```

Frame layout: 16 zero bytes, directive marker `CC 0A`, the live nonce (8 bytes), 6 zero bytes. Tag: `sign(frame[0:16])`, XOR into `frame[16:32]`, `sign` again — the textbook CBC-MAC construction, computed through the oracle because the key itself never leaves the chip (extracting it was never necessary). The nonce is single-use and instance-wide: read it, do both signs, and `exec` in the same session, or the unit answers `directive nonce stale`. Wrong marker offsets answer `frame carries no control directive`; a bad tag answers `directive authentication failed` — the three errors cleanly separate the three checks.

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}` (redacted)

## Reflections

- Fuse bytes are a bench map: `DWEN`, `SPIEN`, `BOOTRST` and `LB` predicted which of the four adapters could work before a single wire was dragged — reading `hfuse/lock` first turns "try everything" into a checklist.
- "Physically unreadable" was literal and bounded: the bootloader happily returns the application but `0xFF`s the key's home at `0x7F00`. The intended pivot is from *extract the key* to *use the device's own encryption as an oracle* — CBC-MAC forgery needs the oracle, not the key.
- Error strings are a protocol spec: `authentication failed` (MAC) vs `carries no control directive` (marker bytes) vs `nonce stale` (freshness/position) told me which of the three gates each attempt passed, making the frame layout a 4-trial search instead of a guess.

## Tools & references

- Python 3 (`websockets` client, WebSocket `/ws` line protocol) + `curl` (asset recon)
- radare2 (`-a avr`, `aaa`/`pdf`) on the bootloader-recovered application; `avrdude` CLI semantics in-console
- ATmega328P datasheet (signature `0x1E950F`, fuse/lock-bit maps, debugWIRE/ISP/bootloader entry conditions), AES-128 CBC-MAC oracle forgery

---
[⬅ Back to event](../../README.md)
