#!/usr/bin/env python3
"""
CSCTF 2026 — Operation Dawn: Relay Snapshot (forensics/easy)
Recover the standing order flag from a Linux x86-64 ELF core dump.

The process held a singly-linked list of string-fragment nodes in heap memory.
Each node:
    struct Node {
        struct Node *next;   // 8 bytes — VA of next node, NULL = tail
        uint32_t     len;    // 4 bytes
        char         data[]; // len bytes, null-padded to next 4-byte boundary
    };
Each heap object is wrapped in a container:
    struct Container {
        uint64_t type;  // = 0x31
        Node     node;  // embedded — its VA = container_va + 8
    };

The forged/decoy data creates multiple chains. The chain rooted at the container
whose data field is "CSCTF" reconstructs the flag.

Usage:
    python3 solve.py [path/to/relay.core]
"""

import sys
import struct

CORE = sys.argv[1] if len(sys.argv) > 1 else "files/relay.core"
CONTAINER_TYPE = 0x31


def load_segments(data):
    """Return list of (vaddr, filesz, file_offset) for PT_LOAD segments."""
    e_phoff     = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum     = struct.unpack_from("<H", data, 0x38)[0]
    segs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type   = struct.unpack_from("<I", data, off)[0]
        p_offset = struct.unpack_from("<Q", data, off + 8)[0]
        p_vaddr  = struct.unpack_from("<Q", data, off + 16)[0]
        p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
        if p_type == 1:  # PT_LOAD
            segs.append((p_vaddr, p_filesz, p_offset))
    return segs


def va_to_file(va, segs):
    if not va:
        return None
    for vaddr, filesz, foffset in segs:
        if vaddr <= va < vaddr + filesz:
            return foffset + (va - vaddr)
    return None


def scan_containers(data, segs):
    """Scan all PT_LOAD segments for container objects (type == 0x31)."""
    nodes = {}  # node_va -> (next_node_va, string)
    for vaddr, filesz, foffset in segs:
        region = data[foffset: foffset + filesz]
        for i in range(0, len(region) - 48, 8):
            if struct.unpack_from("<Q", region, i)[0] != CONTAINER_TYPE:
                continue
            next_va = struct.unpack_from("<Q", region, i + 8)[0]
            slen    = struct.unpack_from("<I", region, i + 16)[0]
            if slen == 0 or slen > 32:
                continue
            s = region[i + 20: i + 20 + slen]
            try:
                s = s.decode("ascii")
            except UnicodeDecodeError:
                continue
            node_va = (vaddr + i) + 8  # node starts 8 bytes into the container
            nodes[node_va] = (next_va, s)
    return nodes


def follow_chain(start_va, nodes):
    parts = []
    va = start_va
    seen = set()
    while va and va not in seen:
        if va not in nodes:
            break
        seen.add(va)
        nxt, s = nodes[va]
        parts.append(s)
        va = nxt
    return "".join(parts)


def main():
    print(f"[*] Loading {CORE}")
    with open(CORE, "rb") as f:
        data = f.read()

    segs = load_segments(data)
    print(f"[*] {len(segs)} PT_LOAD segments")

    nodes = scan_containers(data, segs)
    print(f"[*] {len(nodes)} container nodes found")

    # Find heads (nodes not pointed to by any other node)
    all_nexts = {nxt for nxt, _ in nodes.values()}
    heads = [va for va in nodes if va not in all_nexts]
    print(f"[*] {len(heads)} chain head(s)")

    for head_va in sorted(heads):
        chain = follow_chain(head_va, nodes)
        _, first_s = nodes[head_va]
        if chain.startswith("CSCTF{") and chain.endswith("}"):
            print(f"\n[+] FLAG chain at {head_va:#x}: {chain}")
            return

    # Fallback: print all chains
    print("\n[-] No direct CSCTF chain found, dumping all:")
    for head_va in sorted(heads):
        chain = follow_chain(head_va, nodes)
        print(f"  {head_va:#x}: {chain}")


if __name__ == "__main__":
    main()
