"""Remove the GitHub language-switch line (🇬🇧 English · 🇫🇷 Français) from site pages.

On GitHub the line lets readers jump between README.md and README.fr.md; on the
MkDocs site the i18n plugin already provides a language selector.
"""
import re

_SWITCH = re.compile(r"^\[?🇬🇧 English.*Français\]?.*\n", re.MULTILINE)


def on_page_markdown(markdown, **kwargs):
    return _SWITCH.sub("", markdown, count=1)
