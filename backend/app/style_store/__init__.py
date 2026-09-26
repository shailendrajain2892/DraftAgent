"""Stub style store package.

The real RAG implementation is spec 04's owner. Until it lands we expose:
- `clean_body`: a working text cleaner used by the Gmail tools.
- `StyleStore`: a disk-backed stub matching Contract C so the seed job and tools run.
"""

from .clean import clean_body
from .store import StyleStore

__all__ = ["clean_body", "StyleStore"]
