#!/usr/bin/env python3
"""
CSCTF 2026 — Operation Dawn: The Relay Tap (forensics/easy)
Decrypt the standing order from a captured ARLY relay session.

ARLY frame format (self-described in the capture):
  "ARLY" | type(1 byte) | len(2 bytes, big-endian) | body
  Types:
    0 = descriptor (plaintext, self-describing)
    1 = client_nonce (16 bytes)
    2 = server_nonce (16 bytes)
    3 = order (encrypted)

Key derivation:
  key = SHA-256(client_nonce || server_nonce)

Keystream:
  ks = SHA-256(key || uint32be(0)) || SHA-256(key || uint32be(1)) || ...
       truncated to len(order_body)

Decryption:
  order = order_body XOR ks

Usage:
    python3 solve.py [path/to/relay-tap.pcap]
"""

import sys
import struct
import hashlib

# Try to use scapy or dpkt to read pcap; fall back to manual parse
PCAP = sys.argv[1] if len(sys.argv) > 1 else "files/relay-tap.pcap"

# ── PCAP reader (no external dependencies) ───────────────────────────────────
def read_pcap_payloads(path):
    """Yield raw TCP payload bytes for each packet, in order."""
    with open(path, "rb") as f:
        # Global header
        magic = f.read(4)
        if magic == b"\xd4\xc3\xb2\xa1":
            endian = "<"
        elif magic == b"\xa1\xb2\xc3\xd4":
            endian = ">"
        else:
            raise ValueError(f"Not a pcap file (magic={magic.hex()})")
        f.read(20)  # skip rest of global header

        while True:
            rec_hdr = f.read(16)
            if len(rec_hdr) < 16:
                break
            inc_len = struct.unpack(endian + "I", rec_hdr[8:12])[0]
            pkt = f.read(inc_len)
            if len(pkt) < inc_len:
                break

            # Ethernet (14) + IP (variable) + TCP (variable)
            if len(pkt) < 14:
                continue
            ethertype = struct.unpack(">H", pkt[12:14])[0]
            if ethertype != 0x0800:  # IPv4 only
                continue
            ip_ihl = (pkt[14] & 0x0F) * 4
            ip_proto = pkt[23]
            if ip_proto != 6:  # TCP only
                continue
            tcp_off = 14 + ip_ihl
            if len(pkt) < tcp_off + 20:
                continue
            tcp_data_off = ((pkt[tcp_off + 12] >> 4) & 0xF) * 4
            payload_off = tcp_off + tcp_data_off
            payload = pkt[payload_off:]
            if payload:
                yield payload


# ── ARLY frame parser ─────────────────────────────────────────────────────────
MAGIC = b"ARLY"

def parse_frames(data: bytes):
    frames = []
    i = 0
    while i < len(data) - 6:
        if data[i:i+4] != MAGIC:
            i += 1
            continue
        ftype = data[i+4]
        flen = struct.unpack(">H", data[i+5:i+7])[0]
        body = data[i+7:i+7+flen]
        if len(body) == flen:
            frames.append((ftype, body))
        i += 7 + flen
    return frames


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Collect all TCP payloads that contain ARLY frames
    client_nonce = None
    server_nonce = None
    order_body   = None

    print(f"[*] Reading {PCAP}")
    all_payload = b""
    for payload in read_pcap_payloads(PCAP):
        if MAGIC in payload:
            all_payload += payload

    frames = parse_frames(all_payload)
    print(f"[*] Parsed {len(frames)} ARLY frame(s)")

    for ftype, body in frames:
        if ftype == 0:
            print(f"    [0] descriptor: {body.decode('ascii', errors='replace')[:80]}...")
        elif ftype == 1:
            client_nonce = body
            print(f"    [1] client_nonce: {body.hex()}")
        elif ftype == 2:
            server_nonce = body
            print(f"    [2] server_nonce: {body.hex()}")
        elif ftype == 3:
            if order_body is None:
                order_body = body   # keep the FIRST order frame (legitimate)
                print(f"    [3] order (enc, first/legitimate): {body.hex()}")
            else:
                print(f"    [3] order (enc, duplicate/forged): {body.hex()} — ignored")

    if not all([client_nonce, server_nonce, order_body]):
        print("[-] Missing required frames.")
        sys.exit(1)

    # Key derivation
    key = hashlib.sha256(client_nonce + server_nonce).digest()
    print(f"\n[*] key = {key.hex()}")

    # Keystream generation
    ks = b""
    i = 0
    while len(ks) < len(order_body):
        ks += hashlib.sha256(key + struct.pack(">I", i)).digest()
        i += 1
    ks = ks[:len(order_body)]

    # Decrypt
    plaintext = bytes(a ^ b for a, b in zip(order_body, ks))
    try:
        flag = plaintext.decode("ascii")
        print(f"\n[+] Decrypted order: {flag}")
    except UnicodeDecodeError:
        print(f"[-] Non-ASCII output: {plaintext.hex()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
