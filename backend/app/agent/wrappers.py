"""Model-facing wrappers around the Contract B read tools (Spec 03 §6.8).

Identity params (``user_id``, ``thread_id``, ``exclude_thread_id``) are hidden
from the model: they come from the run config / graph state via ``ToolRuntime``
injection, so a model-supplied value is dropped by schema validation.

Errors: ``AuthExpiredError`` (and read-path ``GmailRateLimitedError``) re-raise
unchanged so they can escape the graph; everything else becomes sanitized,
recoverable text that ToolNode returns to the model as a ToolMessage.
"""

from __future__ import annotations

import json
import re

from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from .errors import AgentToolError, AuthExpiredError, GmailRateLimitedError

# Strip file-path-looking tokens from error text (no raw paths to the model).
_PATH_RE = re.compile(r"(?:/[\w.~+-]+){2,}|[A-Za-z]:\\[\w .\\-]+")


def sanitize_error(exc: Exception) -> str:
    """Single-line, path-free, traceback-free message (max 300 chars)."""
    raw = str(exc).strip()
    first_line = raw.splitlines()[0] if raw else ""
    first_line = _PATH_RE.sub("[path]", first_line)
    first_line = " ".join(first_line.split())
    return f"{type(exc).__name__}: {first_line or 'no further detail'}"[:300]


def handle_tool_errors(e: Exception) -> str:
    """ToolNode error callback: auth escapes (backend -> 401), rest -> text."""
    if isinstance(e, AuthExpiredError):
        raise e                            # escapes the graph unchanged
    if isinstance(e, AgentToolError):
        return str(e)                      # already sanitized by the wrapper
    return sanitize_error(e)               # read-path quota, anything else


def _identities(runtime: ToolRuntime) -> tuple[str, str]:
    """Trusted (user_id, gmail_thread_id) from run config + graph state."""
    config = runtime.config or {}
    state = runtime.state if isinstance(runtime.state, dict) else {}
    user_id = (config.get("configurable") or {}).get("user_id")
    thread_id = state.get("gmail_thread_id")
    if not user_id or not thread_id:
        raise AgentToolError("missing run identity in config/state")
    return user_id, thread_id


async def _call(fn, *args) -> str:
    """Run one Contract B tool and JSON-encode the result.

    Typed errors re-raise unchanged; anything else becomes a sanitized,
    recoverable AgentToolError that the model gets to see.
    """
    try:
        return json.dumps(await fn(*args), ensure_ascii=False)
    except (AuthExpiredError, GmailRateLimitedError, AgentToolError):
        raise
    except Exception as exc:
        raise AgentToolError(sanitize_error(exc)) from exc


def make_wrapped_tools(tools) -> list:
    """The three read tools (create_draft is called by the save node)."""

    @tool
    async def get_thread(max_messages: int = 10,
                         runtime: ToolRuntime = None) -> str:
        """Read the email thread currently being replied to (oldest first)."""
        user_id, thread_id = _identities(runtime)
        return await _call(tools.get_thread, user_id, thread_id, max_messages)

    @tool
    async def search_related(query: str, max_results: int = 5,
                             runtime: ToolRuntime = None) -> str:
        """Search the mailbox for threads related to the current conversation."""
        user_id, thread_id = _identities(runtime)
        # exclude_thread_id comes from state, never from the model.
        return await _call(tools.search_related, user_id, query,
                           thread_id, max_results)

    @tool
    async def get_style_examples(k: int = 4,
                                 runtime: ToolRuntime = None) -> str:
        """Get examples of how this user usually writes replies, plus a style summary."""
        user_id, thread_id = _identities(runtime)
        return await _call(tools.get_style_examples, user_id, thread_id, k)

    return [get_thread, search_related, get_style_examples]
