#!/usr/bin/env python3
"""the-lock-box: recover the gate's real pass phrase without running the binary.

Usage: python3 -I solve.py ../files/lockbox.zip

The 33-character phrase that `main` itself checks ("open sesame and mind the
tripwire", found by XORing its stored rodata table with 0x5b) is a decoy: it
only prints a taunt. The real check runs *before* main, as a constructor
registered in .init_array -- GCC/glibc constructors are invoked with
(argc, argv, envp) in rdi/rsi/rdx, so that function reads argv like a normal
command handler even though nothing in main ever calls it. It verifies a
44-byte phrase with a rolling XOR/ROL/ADD cipher against an embedded key and
ciphertext, and writes its verdict into a global that main later reads.

This script locates the real constructor among the .init_array entries
(skipping glibc's own frame_dummy trampoline), and inverts the cipher using
the key/ciphertext bytes stored right after the "LOCKBOX1," marker in
.rodata -- no execution of the binary involved.
"""
import struct
import sys
import zipfile
from pathlib import Path


def rol8(v, n):
    n &= 7
    return v if n == 0 else ((v << n) | (v >> (8 - n))) & 0xFF


def ror8(v, n):
    n &= 7
    return v if n == 0 else ((v >> n) | (v << (8 - n))) & 0xFF


src = Path(sys.argv[1])
elf = zipfile.ZipFile(src).read("lockbox") if src.suffix == ".zip" else src.read_bytes()

# --- locate .init_array and confirm the real constructor is registered there -------
# ELF64 header: e_phoff@0x20, e_shoff@0x28, e_phentsize/e_phnum@0x36, e_shentsize/e_shnum/e_shstrndx@0x3A
e_phoff, e_shoff = struct.unpack_from("<QQ", elf, 0x20)
e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHHHH", elf, 0x36)
sections = [struct.unpack_from("<IIQQQQIIQQ", elf, e_shoff + i * e_shentsize) for i in range(e_shnum)]
shstrtab_off = sections[e_shstrndx][4]


def sh_name(sh):
    off = shstrtab_off + sh[0]
    return elf[off:elf.index(b"\0", off)].decode()


init_array = next(sh for sh in sections if sh_name(sh) == ".init_array")
offset, size = init_array[4], init_array[5]   # Elf64_Shdr: ..., sh_addr, sh_offset, sh_size
n_entries = size // 8
ctors = struct.unpack_from(f"<{n_entries}Q", elf, offset)
print(f".init_array has {n_entries} entries: {[hex(c) for c in ctors]}", file=sys.stderr)

# vaddr -> file offset for a PT_LOAD-mapped address (needed to read the constructor's code)
def to_file_offset(vaddr):
    for _, _, p_offset, p_vaddr, _, p_filesz, _, _ in (
            struct.unpack_from("<IIQQQQQQ", elf, e_phoff + i * e_phentsize) for i in range(e_phnum)):
        if p_vaddr <= vaddr < p_vaddr + p_filesz:
            return p_offset + (vaddr - p_vaddr)
    raise ValueError(f"no segment maps {vaddr:#x}")


real_ctor = None
for addr in ctors:
    off = to_file_offset(addr)
    # glibc's frame_dummy is "endbr64; jmp <rel8|rel32>" (opcode 0xE9/0xEB right after the 4-byte endbr64);
    # the planted constructor has a real prologue (push rbp / push rbx) there instead.
    if elf[off + 4] not in (0xE9, 0xEB):
        real_ctor = addr
        break
assert real_ctor is not None, "could not tell the planted constructor from frame_dummy"
print(f"planted constructor at {real_ctor:#x} (checked before main ever runs)", file=sys.stderr)

# --- recover key + ciphertext: follow the constructor's own `lea r11, [rip+disp32]` ---
# (encoded 4C 8D 1D <disp32 LE>) rather than guessing padding around the "LOCKBOX1," label.
ctor_off = to_file_offset(real_ctor)
window = elf[ctor_off:ctor_off + 0x100]
p = window.index(b"\x4C\x8D\x1D")
disp32 = struct.unpack_from("<i", window, p + 3)[0]
table_vaddr = real_ctor + p + 7 + disp32          # x86 RIP-relative: displacement is from the *next* instruction
table_off = to_file_offset(table_vaddr)
KEY, CIPHER = elf[table_off:table_off + 8], elf[table_off + 8:table_off + 8 + 44]
print(f"key table at {table_vaddr:#x}: key={KEY.hex()} cipher={CIPHER.hex()}", file=sys.stderr)

# --- invert the rolling cipher (recovered by reading the constructor's disassembly) -
# for i in 0..43: dl = rol8(phrase[i] ^ (esi & 0xFF), cl) + key[i & 7]; must equal cipher[i]
# esi starts at 0x5b, cl starts at 1 and steps by 3; esi advances by (i + edx) each round,
# where edx's low byte is cipher[i] once correct and its high bytes just carry esi's own.
esi, cl = 0x5B, 1
phrase = bytearray()
for i in range(44):
    esi_lo = esi & 0xFF
    rotated = (CIPHER[i] - KEY[i & 7]) & 0xFF
    phrase.append(ror8(rotated, cl) ^ esi_lo)
    esi = (esi + i + ((esi & 0xFFFFFF00) | CIPHER[i])) & 0xFFFFFFFF
    cl += 3

flag = phrase.decode()
assert flag.startswith("CSCTF{") and flag.endswith("}")
print(flag)
