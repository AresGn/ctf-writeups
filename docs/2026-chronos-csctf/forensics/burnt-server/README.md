---
tags: [forensics, raid5, fat, gzip]
---

🇬🇧 English · [🇫🇷 Français](README.fr.md)

# Operation Dawn: The Burnt Server

| Category | Solves | Solved | First blood | Hint used | Solved by | Challenge author |
|---|---|---|---|---|---|---|
| forensics | 61 | ✅ | — | no | 0xAr3s-root | Terminal43 |

## Challenge description

> A hostile force destroyed a fictional country's hospital logistics archive to choke medical transport. Two storage members survived, and the salvage record is in the attachment.
>
> Recover the train movement register and submit its complete CSCTF{...} marker. The case is constructed with real filesystem and compression formats; nothing came off physical disks.
> Attachment: `server-remains.tar`, 4,198,400 bytes, SHA-256 `98fd39f5957606e08b2a77dd253d6627366fd5853ecbd8f0f3ff81cc500345af`.

**Artifact files:** `files/server-remains.tar` (not committed — currently at `forensics/server-remains.tar`, to be moved later)

## TL;DR

3-disk RAID5 with the middle disk burnt. Chunk 64 KiB, parity rotating right (`p = stripe % 3`). XOR rebuild gives a FAT16 image; the deleted `TRAIN.GZ` (start cluster 16, 16599 bytes) is carved contiguously and gunzipped to the train register containing the flag.

## Approach

**1. Recon — what the tar holds**

```bash
sha256sum server-remains.tar  # 98fd39f5… matches
tar tvf server-remains.tar
# disk0.img  2097152
# disk2.img  2097152
# SALVAGE.txt    434
python3 -c "import tarfile; print(tarfile.open('server-remains.tar').extractfile('SALVAGE.txt').read().decode())"
```

`SALVAGE.txt`: hospital archive box, three identical drives in a hot rack, centre drive (slot 1) burnt, slots 0 and 2 imaged. No controller/array settings.

```bash
file disk0.img disk2.img
# disk0.img: OpenPGP Secret Key (coincidence — high entropy)
# disk2.img: data
```

Both 2 MiB. 99.3% of 512 B blocks identical, 35 differing blocks: `[0, 1, 33, 65, 97, 98…127]`. Differing blocks are either both random-different (stripes with two data chunks) or `data vs zeros` — the classic RAID5-with-one-missing-disk pattern when the filesystem is mostly empty.

Strings on `disk0.img` already leak the story:

```
DAWN ARCH | ROSTER TXT | WARDS TXT | MANIFEST TXT | SIGNALS TXT | _RAIN GZ
night 01: two orderlies, one driver, one medic ...
ward 1: 23 beds, 5 stretchers, 1 litters ...
crate 000  morphia  31 kg ...
```

At `disk0` offset `0x8200`: a FAT root directory (`ROSTER.TXT` start 2 size 1440, `WARDS.TXT` 5/253, `MANIFEST.TXT` 6/2388, `SIGNALS.TXT` 11/2100, deleted `0xE5 RAIN.GZ` start 16 size 16599). At `0x4200`: a FAT16 table (`F8 FF FF FF 03 00 04 00 …`). At `0xDE00` (disk0 only, zeros on disk2): gzip magic `1f 8b 08`. No `55 AA` boot signature aligned — the image is striped, not a plain filesystem.

**2. Hypothesis — RAID5, reconstruct and brute-force the geometry**

Three identical drives, two survivors, missing array settings → RAID5 with one failure is recoverable. Dedicated parity (RAID4) or mirror (RAID1) don't fit the diff pattern; striping + rotating parity does:

- empty stripe → all three chunks zero → survivors identical (zero);
- stripe with one data chunk `X` and parity on a survivor → survivor pair `X == X` (identical non-zero);
- stripe with parity on the missing disk → survivors `X vs Y` (both non-zero, different) or `X vs 0`.

Brute force: chunk sizes 512 B–64 KiB × parity `left (2,1,0…)` / `right (0,1,2…)` × data order asymmetric/symmetric, rebuild missing chunks by XOR, check for a FAT boot sector (`EB xx 90`, `FAT`, `55 AA`).

Only `right` parity gives a boot sector. Only chunk **64 KiB** gives a coherent root directory (all other chunks give empty/garbage entries). Result: `BPS=512, SPC=1, reserved=1, 2 FATs × 32 sectors, 512 root entries, data_start=sector 97`.

```bash
python3 solve/solve.py files/server-remains.tar
```

Solve script: [`solve/solve.py`](solve/solve.py)

**3. Exploitation — carve the deleted gzip and gunzip**

`TRAIN.GZ` is deleted, so its FAT chain is zeroed (entries 16+ are `0x0000`). The file is contiguous: cluster 16 → filesystem offset `(97 + 14) × 512 = 0xDE00`, exactly the gzip magic. Carve 16599 bytes, `gzip.decompress` → 76901 bytes:

```
WHITE VALLEY HOSPITAL - TRAIN MOVEMENT REGISTER
night of the evacuation

0000  wagon 01  berth 191  ward 6  tag 174254  stretcher
...
0942  wagon 14  berth 004  ward 6  tag ec86e1  stretcher

MOVEMENT ORDER: flag{...}

0943  wagon 10  berth 136  ward 6  tag 3eab8f  litter
...
```

1406 lines, ~1400 wagon entries, flag on line 947. No other `CSCTF{…}` in the raw image — only in the decompressed register.

## Flag

`flag{...}`

## Reflections

- The `OpenPGP Secret Key` `file` hit and the random-looking first sectors are a red herring: the boot sector lived on the burnt disk and is rebuilt by `disk0 ^ disk2`.
- 99% identical disks ≠ mirror: in RAID5 with a mostly-empty FAT, parity-equals-data stripes look identical. The `X vs 0` blocks pinpoint the stripe size (64 KiB gap between FAT at `0x4200` and root dir at `0x8200` is a hint).
- Deleted FAT files keep `start + size` but lose the chain — don't trust the FAT, carve contiguously and validate by magic + decompression.

## Tools & references

- Python 3 (`tarfile`, `struct`, `gzip`) — no Sleuth Kit needed once striped
- `tar`, `sha256sum`, `file`, `hexdump`, `strings`
- Linux RAID wiki: chunk, parity rotation, left/right-symmetric layouts
- FAT16 layout (BPB, FAT table, root directory, data area)

---
[⬅ Back to event](../../README.md)
