---
tags: [forensics, pcap, custom-protocol, crypto, xor]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Operation Dawn: The Relay Tap

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 120 | 36 | ✅ | — | 0xAr3s-root | Terminal43 |

## Challenge description

> During Operation Dawn, Ash Army operators sprayed forged traffic onto a coalition government's
> emergency-dispatch relay while command's standing order was in flight. A signals unit tapped
> the link, but the capture is noisy and some of the relay's data appears more than once.
>
> You are the analyst on the tap. Work out which standing order the relay actually delivered
> and submit it exactly as recovered. Between its braces it uses lowercase letters, digits and
> underscores.
>
> ARLY, the relay's frame format, is invented for this scenario and describes itself inside
> the capture. The capture is a constructed case: a real TCP/IP session recorded with tcpdump
> on an isolated virtual link, with fictional hosts only.
> Attachment: `relay-tap.zip`, 12,327 bytes,
> SHA-256 `43424028556d841d5e280c0e283b4a540dbdd123d06699cc95a89bf580ba2530`.

**Artifact files:** `files/relay-tap.pcap` (not committed)

## TL;DR

The ARLY custom protocol self-documents its own encryption scheme in the capture; XOR-decrypting the first order frame with the SHA-256-derived keystream yields the flag. The second (forged) order frame is garbage.

## Approach

**1. Recon — overview of the capture**

```bash
capinfos relay-tap.pcap   # 123 packets, ~5 seconds, Ethernet/IPv4/TCP
tshark -r relay-tap.pcap -q -z conv,tcp
```

Seven TCP streams: six are HTTP (dispatch status pages returning `nominal`),
and one is an unusual connection to port **7443** — that's the ARLY relay.

**2. Reading the ARLY protocol**

```bash
tshark -r relay-tap.pcap -q -z follow,tcp,ascii,6
```

The very first frame from the server is a **type-0 descriptor** that describes the entire protocol in plain text:

```
ARLY relay v2 :: frame = "ARLY" | type(1) | len(2, big-endian) | body;
types 0=descriptor 1=client_nonce(16) 2=server_nonce(16) 3=order;
key = SHA-256(client_nonce || server_nonce), 32 raw bytes;
ks = SHA-256(key || uint32be(i)) for i = 0,1,2,..., raw 32-byte digests
     concatenated and cut to len(body);
order = body XOR ks, byte by byte
```

**3. Parsing the frames**

Extracting the raw stream reveals 7 ARLY frames:

| # | Type | Content |
|---|---|---|
| 1 | 1 (client_nonce) | `3025e871…` |
| 2 | 0 (descriptor) | plaintext spec |
| 3 | 2 (server_nonce) | `30815081…` |
| 4 | 0 (descriptor, duplicate) | — |
| 5 | 2 (server_nonce, duplicate) | same value |
| 6 | 3 (order, **legitimate**) | `b2fce724…` |
| 7 | 3 (order, **forged**) | `a2210ad8…` |

The forged traffic the Ash Army injected added a second order frame. The first one is the authentic delivery.

**4. Decryption**

```python
key = SHA-256(client_nonce + server_nonce)
ks  = SHA-256(key + 0x00000000) || SHA-256(key + 0x00000001) || …  (cut to 46 bytes)
flag = order_body XOR ks
```

```bash
python3 solve/solve.py files/relay-tap.pcap
```

```
[+] Decrypted order: flag{...}
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}`

## Reflections

- The protocol is self-describing — no reverse engineering needed, just read the descriptor.
- "Noisy / appears more than once" is the key hint: pick the **first** order frame, not the last.
- The HTTP streams are pure noise; `port 7443` is the only interesting stream.
- The solve script uses zero external dependencies (pure Python pcap reader).

## Tools & references

- `capinfos`, `tshark` (Wireshark suite)
- Python 3 (`hashlib`, `struct`)
- [RFC 5737](https://datatracker.ietf.org/doc/html/rfc5737) — documentation address ranges used as fictional hosts

---
[⬅ Back to event](../../README.md)
