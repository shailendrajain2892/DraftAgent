"""Style store package (Contract C).

- `clean_body`: text cleaner used by the Gmail tools.
- `StyleStore`: disk-backed RAG over the user's past reply pairs — embeddings-based
  retrieval (OpenAI), with keyword-overlap fallback when embeddings are unavailable.
"""

from .clean import clean_body
from .store import StyleStore

__all__ = ["clean_body", "StyleStore"]
