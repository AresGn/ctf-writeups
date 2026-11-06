---
tags: [forensics, core-dump, elf, linked-list, heap]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Operation Dawn: Relay Snapshot

| Category | Points | Solves | Solved | First blood | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 125 | 42 | ✅ | — | 0xAr3s-root | Terminal43 |

## Challenge description

> A hostile intrusion knocked out the military relay of a fictional country, and responders
> snapshotted the relay's process memory while they were recovering a standing order.
>
> Recover the complete `CSCTF{...}` order from `relay.core`. This constructed case holds
> invented relay records inside a real Linux process snapshot.
> Attachment: `relay.core`, Linux x86-64 ELF core, 586,928 bytes,
> SHA-256 `b3e606bfbe727f0346be4cde683a9a8efd2680930219113a5b779a3c9a5121ac`.

**Artifact files:** `files/relay.core` (not committed)

## TL;DR

The process heap contains a singly-linked list of string-fragment nodes; the chain
rooted at the `CSCTF` node reassembles the flag. Decoy chains were injected to confuse.

## Approach

**1. Initial recon**

```bash
file relay.core    # ELF 64-bit core, x86-64
strings relay.core | grep CSCTF
```

`strings` reveals the fragments scattered in memory:
```
burn_it_bridgefall_backat_dawnstand_doburn_itrelieve_hold_thewn_nowregroup_fall_back_at_two59c}k_866_dusgroveelm_hard_e_orc_movdock{20_CSCTF
```

The fragments are in the wrong order — they are heap objects that need to be followed via pointers.

**2. Understanding the data structure**

Parsing the ELF PT_LOAD segments, scanning for objects starting with `uint64 = 0x31`:

```
struct Container {
    uint64_t type;   // always 0x31
    struct Node {
        struct Node *next;   // VA of next node, 0 = tail
        uint32_t     len;
        char         data[]; // null-padded
    } node;
};
```

The `node` member starts 8 bytes into the container, so `node_va = container_va + 8`.
The `next` pointer is the VA of the **next node** (i.e. `next_container_va + 8`).

23 such containers are found. Each holds one string fragment.

**3. Reconstructing the chains**

Building a graph of `node_va → (next_va, string)`, then finding chain heads (nodes not
pointed to by anyone) yields 10 chains. One of them starts at the `CSCTF` node:

```
CSCTF → {20_ → dock → _mov → e_orc → hard_ → elm_ → grove → _dus → k_866 → 59c}
```

The remaining chains are decoys (injected forged traffic in the scenario).

```bash
python3 solve/solve.py files/relay.core
```

```
[+] FLAG chain at 0x55a7aff173c0: flag{...}
```

Solve script: [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}`

## Reflections

- `strings` reveals the fragments immediately but in heap-traversal order, not logical order.
- The key insight: the process stores strings in a **singly-linked list**, not contiguously.
- The challenge plants multiple chains as decoys; the correct one starts at `CSCTF`.
- Pure Python ELF parsing (no pwntools, no gdb) is sufficient.

## Tools & references

- `file`, `strings` (binutils)
- Python 3 (`struct`)
- ELF specification (System V ABI, x86-64 supplement)

---
[⬅ Back to event](../../README.md)
