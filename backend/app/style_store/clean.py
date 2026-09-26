"""Text cleaning: strip quoted history, forwards and signatures from email bodies.

This is intentionally simple and dependency-light. The style-store owner may replace it
with something smarter; the Contract C signature stays the same.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

# Lines that mark the start of quoted history ("On <date>, X wrote:").
_QUOTE_HEADER = re.compile(
    r"^\s*(On .+ wrote:|-{2,}\s*Original Message\s*-{2,}|_{5,}|From:\s.+)",
    re.IGNORECASE,
)
# Common signature delimiters.
_SIG_DELIM = re.compile(r"^\s*--\s*$")
_SIG_PHRASES = re.compile(
    r"^\s*(sent from my (iphone|ipad|android|mobile|samsung)|best regards|regards|"
    r"thanks(,| and regards)?|cheers|sincerely)\b",
    re.IGNORECASE,
)


def _html_to_text(raw: str) -> str:
    soup = BeautifulSoup(raw, "html.parser")
    # Drop quoted blocks Gmail wraps in blockquote.
    for bq in soup.find_all("blockquote"):
        bq.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    text = soup.get_text("\n")
    return text


def clean_body(raw: str, is_html: bool = False) -> str:
    """Return the sender's own new text: no quoted history, forwards or signatures."""
    if not raw:
        return ""
    text = _html_to_text(raw) if is_html else raw

    lines = text.splitlines()
    kept: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Stop at the first quoted-history header.
        if _QUOTE_HEADER.match(line):
            break
        # Skip quoted lines that start with ">".
        if stripped.startswith(">"):
            continue
        kept.append(line.rstrip())

    # Trim a trailing signature block.
    for i, line in enumerate(kept):
        if _SIG_DELIM.match(line) or _SIG_PHRASES.match(line):
            kept = kept[:i]
            break

    # Collapse 3+ blank lines and trim edges.
    cleaned = "\n".join(kept)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
