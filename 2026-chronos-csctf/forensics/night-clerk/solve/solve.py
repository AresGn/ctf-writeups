#!/usr/bin/env python3
"""
CSCTF 2026 — Night Clerk (forensics/easy)
Recover a hidden coordination message from a seized NTFS stick image.

Steps:
  1. Extract night_audit.docx from the NTFS image (inode 66, deleted).
  2. Parse the tracked insertion (w:ins) to get the hex-encoded ciphertext.
  3. Brute-force single-byte XOR keys; the correct key yields a valid CSCTF{...} flag.

Usage:
    python3 solve.py [path/to/terminal.dd]
"""

import sys
import subprocess
import zipfile
import xml.etree.ElementTree as ET

IMG = sys.argv[1] if len(sys.argv) > 1 else "files/terminal.dd"
DOCX_INODE = 66
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

# Step 1: extract docx bytes from NTFS image
print("[*] Extracting night_audit.docx from NTFS image...")
result = subprocess.run(
    ["icat", IMG, str(DOCX_INODE)],
    capture_output=True,
)
if result.returncode != 0:
    print(f"[-] icat failed: {result.stderr.decode()}")
    sys.exit(1)
docx_bytes = result.stdout
print(f"    {len(docx_bytes)} bytes extracted")

# Step 2: parse tracked insertion from word/document.xml
print("[*] Parsing tracked insertions...")
import io
z = zipfile.ZipFile(io.BytesIO(docx_bytes))
doc_xml = z.read("word/document.xml")
root = ET.fromstring(doc_xml)
insertions = root.findall(".//w:ins", NS)
print(f"    Found {len(insertions)} insertion(s)")

hex_ciphertext = None
for ins in insertions:
    for t in ins.findall(".//w:t", NS):
        if t.text and all(c in "0123456789abcdefABCDEF" for c in t.text):
            hex_ciphertext = t.text
            print(f"    Ciphertext (hex): {hex_ciphertext}")

if not hex_ciphertext:
    print("[-] No hex ciphertext found in tracked insertions.")
    sys.exit(1)

ciphertext = bytes.fromhex(hex_ciphertext)

# Step 3: brute-force single-byte XOR key
print("[*] Brute-forcing XOR key...")
for key in range(256):
    plaintext = bytes([b ^ key for b in ciphertext])
    try:
        s = plaintext.decode("ascii")
        if s.startswith("CSCTF{") and s.endswith("}"):
            print(f"\n[+] Key   : {key} (0x{key:02x})")
            print(f"[+] Flag  : {s}")
            sys.exit(0)
    except UnicodeDecodeError:
        pass

print("[-] No valid flag found with single-byte XOR.")
sys.exit(1)
