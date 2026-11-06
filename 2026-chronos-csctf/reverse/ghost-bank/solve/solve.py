#!/usr/bin/env python3
"""GHOST BANK — activate the stub, read the vault key (page 7, STATE 4), decrypt page 3.
Usage: solve.py HOST PORT   (needs: pip install unicorn; firmware.bin next to this script's cwd)
"""
import socket, struct, sys
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_LITTLE_ENDIAN
from unicorn.arm64_const import *

HOST, PORT = sys.argv[1], int(sys.argv[2])
FW = open("firmware.bin", "rb").read()
M = (1 << 64) - 1
ror = lambda v, n: ((v >> n) | (v << (64 - n))) & M

def f(v):                                  # firmware fn @0x400120
    x = v ^ 0xa3b195354a39b70d
    x = ((x >> 16) & 0x7FFFFFFF) ^ ror(x, 47)
    x = (x * 0x64170d358aa115a1) & M
    x ^= x >> 29; x = ror(x, 13)
    x = (x * 0x65931d9dfc2010db) & M
    return x ^ (x >> 31)

def chacha_block(key, ctr, c12):           # run the firmware's own block fn @0x400174
    mu = Uc(UC_ARCH_ARM64, UC_MODE_LITTLE_ENDIAN)
    mu.mem_map(0x400000, 0x1000); mu.mem_write(0x400000, FW)
    mu.mem_map(0x4F0000, 0x10000); mu.reg_write(UC_ARM64_REG_SP, 0x4F8000)
    mu.mem_map(0x600000, 0x3000)
    mu.mem_write(0x600000, key); mu.mem_write(0x601000, c12)
    for r, v in ((UC_ARM64_REG_X0, 0x600000), (UC_ARM64_REG_X1, 0x601000),
                 (UC_ARM64_REG_X2, ctr), (UC_ARM64_REG_X3, 0x602000),
                 (UC_ARM64_REG_LR, 0xDEAD0000)):
        mu.reg_write(r, v)
    mu.emu_start(0x400174, 0xDEAD0000)
    return bytes(mu.mem_read(0x602000, 64))

s = socket.create_connection((HOST, PORT)); noack = False
def rx(n):
    b = b""
    while len(b) < n: b += s.recv(n - len(b))
    return b
def cmd(p):
    global noack
    s.sendall(b"$%s#%02x" % (p.encode(), sum(p.encode()) & 0xFF))
    if not noack: rx(1)                        # '+' ack
    while rx(1) != b"$": pass
    d = b""
    while (c := rx(1)) != b"#": d += c
    rx(2)
    if not noack: s.sendall(b"+")
    return d.decode()
cmd("QStartNoAckMode"); noack = True
rd = lambda a, n=4: cmd(f"m{a:x},{n:x}")
wr = lambda a, v: cmd(f"M{a:x},4:{struct.pack('<I', v).hex()}")
CTRL, PAGE, OFF, DATA, CLEN, CLO, CHI, KEY, ST = (0x40000000, 0x40000008, 0x40000010,
    0x40000018, 0x4000001C, 0x40000020, 0x40000024, 0x40000028, 0x40000030)
def page(p, n):
    wr(PAGE, p); out = b""
    for o in range(n): wr(OFF, o); out += bytes.fromhex(rd(DATA, 1))
    return out

# 1) ciphertext of the tasking: the only page with CIPHER_LEN != 0 (page 3)
wr(PAGE, 3); clen = struct.unpack("<I", bytes.fromhex(rd(CLEN)))[0]
ct = page(3, clen); print("page 3 ciphertext:", clen, "bytes")

# 2) activation ritual (PAGE must be 7), then CONTROL=0x9c -> STATUS 4 reveals the key on page 7
wr(CTRL, 0x41)
ch = struct.unpack("<Q", bytes.fromhex(rd(CLO) + rd(CHI)))[0]
k = f(ch); wr(PAGE, 7); wr(KEY, k & 0xFFFFFFFF); wr(KEY, k >> 32); wr(CTRL, 0x93)
assert rd(ST) == "03000000", "bad activation"
wr(CTRL, 0x9c); assert rd(ST) == "04000000"
key = page(7, 32); print("vault key:", key.hex())

# 3) ChaCha with the firmware's block fn: nonce = "SEAL-V01"+00000001, counter starts at 1
c12 = b"SEAL-V01\x00\x00\x00\x01"
pt = b"".join(bytes(a ^ b for a, b in zip(ct[i:i+64], chacha_block(key, 1 + i // 64, c12)))
              for i in range(0, len(ct), 64))
print(pt.decode())
