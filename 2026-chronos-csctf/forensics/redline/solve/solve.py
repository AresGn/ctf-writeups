#!/usr/bin/env python3
"""redline: diff the tracked changes of a .docx (read as a zip of XML, never opened in Word).

Usage: python3 -I solve.py CC-11_excursion_directive.docx
"""
import re, sys, zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
z = zipfile.ZipFile(sys.argv[1])
core = z.read("docProps/core.xml").decode()
print("creator         :", re.search(r"<dc:creator>(.*?)</dc:creator>", core).group(1))
print("lastModifiedBy  :", re.search(r"<cp:lastModifiedBy>(.*?)</cp:lastModifiedBy>", core).group(1))
for c in ET.fromstring(z.read("word/comments.xml")).iter(W + "comment"):
    print("comment         :", c.get(W + "author"), "-", "".join(t.text for t in c.iter(W + "t")))

body = ET.fromstring(z.read("word/document.xml"))
original, current = [], []
for p in body.iter(W + "p"):
    o = c = ""
    # walk runs, noting whether each sits inside w:del or w:ins
    for node in p:
        if node.tag == W + "r":
            t = "".join(x.text or "" for x in node.iter(W + "t"))
            o += t; c += t
        elif node.tag == W + "del":
            o += "".join(x.text or "" for x in node.iter(W + "delText"))
        elif node.tag == W + "ins":
            c += "".join(x.text or "" for x in node.iter(W + "t"))
    original.append(o); current.append(c)
print("\n--- ORIGINAL (approved, deleted text restored) ---\n" + "\n".join(original))
print("\n--- DELIVERED (tracked changes accepted) ---\n" + "\n".join(current))
print("\nflag:", *re.findall(r"CSCTF\{[^}]*\}", "\n".join(original)))
