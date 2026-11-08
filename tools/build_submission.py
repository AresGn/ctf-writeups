#!/usr/bin/env python3
"""Build the write-up submission for one event, in every format.

Usage:
    python3 tools/build_submission.py 2026-chronos-csctf

Output (submission/<event>/):
    <NAME>_EN.md / <NAME>_FR.md      one Markdown file with every write-up + solve scripts
    <NAME>_EN.html / <NAME>_FR.html  standalone web page (images embedded)
    <NAME>_EN.pdf / <NAME>_FR.pdf    PDF rendered with Chromium (Playwright)
    <NAME>_site.zip                  the full MkDocs website (EN + FR), git-ignored

Needs: pandoc, mkdocs-material, mkdocs-static-i18n, Node.js + Playwright.
"""
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENT = sys.argv[1] if len(sys.argv) > 1 else "2026-chronos-csctf"
SRC = ROOT / "docs" / EVENT
OUT = ROOT / "submission" / EVENT
CFG = json.loads((Path(__file__).parent / "submission" / f"{EVENT}.json").read_text())
NAME = CFG["file_name"]

CATS = [  # folder, EN, FR
    ("web", "Web", "Web"),
    ("crypto", "Crypto / Stego", "Crypto / Stégano"),
    ("forensics", "Forensics", "Forensics"),
    ("network", "Network", "Réseau"),
    ("reverse", "Reverse / Malware", "Reverse / Malware"),
    ("pwn", "Pwn / Binary exploitation", "Pwn / Exploitation binaire"),
    ("ICS", "ICS / SCADA", "ICS / SCADA"),
    ("ml", "ML / AI", "ML / IA"),
    ("osint", "OSINT", "OSINT"),
    ("misc", "Miscellaneous", "Divers"),
]

T = {
    "en": dict(cat="Category", solves="Solves", ch="Challenge", notes="Notes",
               hint="hint used", nc="not counted on the scoreboard",
               appendix="Appendix — solve scripts", see="see Appendix",
               summary="Summary", contents="Contents"),
    "fr": dict(cat="Catégorie", solves="Résolutions", ch="Challenge", notes="Notes",
               hint="indice utilisé", nc="non comptabilisé au classement",
               appendix="Annexe — scripts de résolution", see="voir l'annexe",
               summary="Résumé", contents="Sommaire"),
}

FENCE = re.compile(r"^(```|~~~)")


def clean_writeup(text, lang, slug, img_map):
    """Strip site/GitHub chrome, shift headings by +2, fix links and images."""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)           # front matter
    lines, out, in_code = text.split("\n"), [], False
    for line in lines:
        if FENCE.match(line.strip()):
            in_code = not in_code
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue
        if re.match(r"^\[?🇬🇧 English", line):                           # language switch
            continue
        if re.match(r"^\[⬅", line):                                     # back link
            continue
        m = re.match(r"^(#{1,4}) (.*)$", line)
        if m:
            line = "#" * (len(m.group(1)) + 2) + " " + m.group(2)
        # images: img/x.png -> img/<slug>-x.png (copied next to the output)
        line = re.sub(r"\]\(img/([^)]+)\)",
                      lambda mm: f"](img/{img_map.setdefault((slug, mm.group(1)), f'{slug}-{mm.group(1)}')})",
                      line)
        # other relative links -> plain text (scripts are in the appendix)
        def rel(mm):
            label, target = mm.group(1), mm.group(2)
            if target.startswith(("http://", "https://", "#", "img/", "mailto:")):
                return mm.group(0)
            if target.startswith("solve/"):
                return f"{label} ({T[lang]['see']})"
            return label
        line = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", rel, line)
        out.append(line)
    while out and out[-1].strip() in ("", "---"):                      # trailing rule
        out.pop()
    return "\n".join(out).strip() + "\n"


def collect():
    items = []
    for key, en, fr in CATS:
        for d in sorted((SRC / key).glob("*/README.md")) if (SRC / key).is_dir() else []:
            txt = d.read_text()
            title = re.search(r"^# (.+)$", txt, re.M).group(1).strip()
            row = re.search(r"^\| Category .*\n\|[-|]+\n(\|.*\|)", txt, re.M).group(1)
            cells = [c.strip() for c in row.strip("|").split("|")]
            items.append(dict(cat=key, en=en, fr=fr, slug=d.parent.name, dir=d.parent,
                              title=title if title != d.parent.name else d.parent.name.replace("-", " ").title(),
                              solves=cells[1], counted="(" not in cells[2],
                              hint=cells[4].lower() in ("yes", "oui")))
    order = {k: i for i, (k, _, _) in enumerate(CATS)}
    items.sort(key=lambda x: (order[x["cat"]], x["title"].lower()))
    return items


def build_md(lang, items, img_map):
    t = T[lang]
    md = [CFG[lang]["header"].format(n=len(items)).strip(), ""]
    md += [f"## {t['summary']}", "", f"| # | {t['ch']} | {t['cat']} | {t['solves']} | {t['notes']} |",
           "|---|---|---|---|---|"]
    for n, i in enumerate(items, 1):
        notes = ", ".join(x for x, on in ((t["hint"], i["hint"]), (t["nc"], not i["counted"])) if on)
        md.append(f"| {n} | [{i['title']}](#@@{i['title']}@@) | {i[lang]} | {i['solves']} | {notes} |")
    md += [""]
    md += [CFG[lang]["methodology"].strip(), ""]
    current = None
    for i in items:
        if i["cat"] != current:
            current = i["cat"]
            md += [f"## {i[lang]}", ""]
        f = i["dir"] / ("README.md" if lang == "en" else "README.fr.md")
        md += [clean_writeup(f.read_text(), lang, i["slug"], img_map), ""]
    md += [f"## {t['appendix']}", ""]
    for i in items:
        for s in sorted((i["dir"] / "solve").glob("*")):
            if s.name == ".gitkeep" or not s.is_file():
                continue
            lang_hint = {"py": "python", "sh": "bash", "js": "javascript"}.get(s.suffix[1:], "")
            md += [f"### {i['title']} — `solve/{s.name}`", "", f"~~~~{lang_hint}",
                   s.read_text().rstrip("\n"), "~~~~", ""]
    return link_summary("\n".join(md))


def gfm_slug(text):
    text = re.sub(r"[`*_]{1,2}(?=\S)|(?<=\S)[`*_]{1,2}", "", text)  # inline markup
    text = re.sub(r"[^\w\- ]", "", text.lower())
    return text.replace(" ", "-")


def link_summary(md):
    """Point the summary table at each challenge heading (GitHub/pandoc anchors)."""
    seen, first, in_code = {}, {}, False
    for line in md.split("\n"):
        if FENCE.match(line.strip()):
            in_code = not in_code
        if in_code:
            continue
        m = re.match(r"^(#{1,6}) (.*)$", line)
        if not m:
            continue
        base = gfm_slug(m.group(2).strip())
        slug = base if base not in seen else f"{base}-{seen[base]}"
        seen[base] = seen.get(base, 0) + 1
        if len(m.group(1)) == 3:
            first.setdefault(m.group(2).strip(), slug)
    return re.sub(r"#@@(.+?)@@", lambda mm: "#" + first[mm.group(1)], md)


CSS = """
:root { --fg:#1b1f24; --muted:#57606a; --border:#d0d7de; --code:#f6f8fa; --accent:#0a7d32; }
body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; color: var(--fg);
       max-width: 900px; margin: 0 auto; padding: 24px 16px 64px; line-height: 1.55; font-size: 15px; }
h1 { font-size: 2em; border-bottom: 3px solid var(--accent); padding-bottom: .3em; }
h2 { font-size: 1.6em; border-bottom: 1px solid var(--border); padding-bottom: .25em; margin-top: 2em; }
h3 { font-size: 1.3em; margin-top: 2em; color: var(--accent); }
h4 { font-size: 1.05em; margin-top: 1.4em; }
a { color: #0969da; }
code { background: var(--code); padding: .1em .35em; border-radius: 4px; font-size: .88em;
       font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
pre { background: var(--code); border: 1px solid var(--border); border-radius: 6px; padding: 12px;
      overflow-x: auto; white-space: pre-wrap; word-break: break-word; font-size: 12px; line-height: 1.4; }
pre code { background: none; padding: 0; font-size: inherit; }
table { border-collapse: collapse; margin: 1em 0; font-size: .92em; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--border); padding: 4px 10px; }
th { background: var(--code); }
blockquote { border-left: 4px solid var(--border); margin: 1em 0; padding: 0 1em; color: var(--muted); }
img { max-width: 100%; border: 1px solid var(--border); border-radius: 4px; }
nav#TOC { background: var(--code); border: 1px solid var(--border); border-radius: 6px; padding: 8px 20px; }
nav#TOC ul { padding-left: 1.2em; } nav#TOC > ul > li { margin-top: .3em; }
@media print {
  body { max-width: none; padding: 0; font-size: 11pt; }
  h2 { break-before: page; } h2#summary, h2#résumé { break-before: auto; } h3 { break-after: avoid; } h4 { break-after: avoid; }
  pre, img { break-inside: avoid-page; } tr { break-inside: avoid; }
  h2, h3, h4 { break-after: avoid; }
  a { color: inherit; text-decoration: none; }
}
"""


def main():
    items = collect()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "img").mkdir(exist_ok=True)
    css = OUT / ".style.css"
    css.write_text(CSS)
    for lang in ("en", "fr"):
        img_map = {}
        md = build_md(lang, items, img_map)
        base = f"{NAME}_{lang.upper()}"
        (OUT / f"{base}.md").write_text(md)
        for (slug, name), new in img_map.items():
            src = next(i["dir"] for i in items if i["slug"] == slug) / "img" / name
            shutil.copy(src, OUT / "img" / new)
        subprocess.run(["pandoc", f"{base}.md", "-f", "gfm", "-t", "html5", "-s",
                        "--embed-resources",
                        "--css", css.name, "--metadata", f"pagetitle={CFG[lang]['title']}",
                        "--metadata", f"lang={lang}", "-o", f"{base}.html"],
                       cwd=OUT, check=True)
        subprocess.run(["node", "-e", f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://{OUT / (base + '.html')}', {{ waitUntil: 'load' }});
  await p.pdf({{ path: '{OUT / (base + '.pdf')}', format: 'A4', printBackground: true,
    margin: {{ top: '18mm', bottom: '18mm', left: '15mm', right: '15mm' }},
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#888">{CFG[lang]['footer']} · <span class=pageNumber></span>/<span class=totalPages></span></div>' }});
  await b.close();
}})();"""], check=True)
        print(f"built {base}.md/.html/.pdf")
    css.unlink()
    # full website, zipped
    site = OUT / ".site"
    subprocess.run(["mkdocs", "build", "-q", "-d", str(site)], cwd=ROOT, check=True)
    zpath = OUT / f"{NAME}_site.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in site.rglob("*"):
            if f.is_file():
                z.write(f, Path(f"{NAME}_site") / f.relative_to(site))
    shutil.rmtree(site)
    print(f"built {zpath.name}")


if __name__ == "__main__":
    main()
