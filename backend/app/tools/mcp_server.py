"""Thin MCP wrapper over the plain-Python tools in gmail_tools.

Open question 1 (overview) decides the real transport. For now the tool functions are
plain async Python and the agent/inbox call them directly. This module registers the
LLM-visible tools with an MCP server so we can flip transports later without touching
gmail_tools. Requires the optional `agent` extra (`mcp` package); import is lazy so the
backend runs without it.

Run standalone (stdio):  python -m app.tools.mcp_server
"""

from __future__ import annotations

from . import gmail_tools

# Tools the LLM may call (Contract B "Visible to LLM = yes").
LLM_VISIBLE = ["get_thread", "search_related", "get_style_examples"]


def build_mcp_server():  # pragma: no cover - exercised only when agent extra installed
    """Create an MCP server exposing the LLM-visible tools.

    `user_id` is NOT part of the MCP schema — the agent's ToolClient injects it before
    the call reaches these functions, so the LLM never chooses a user.
    """
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("draftagent-gmail")

    @mcp.tool()
    async def get_thread(user_id: str, thread_id: str, max_messages: int = 10) -> dict:
        return await gmail_tools.get_thread(user_id, thread_id, max_messages)

    @mcp.tool()
    async def search_related(
        user_id: str, query: str, exclude_thread_id: str | None = None, max_results: int = 5
    ) -> list[dict]:
        return await gmail_tools.search_related(user_id, query, exclude_thread_id, max_results)

    @mcp.tool()
    async def get_style_examples(user_id: str, thread_id: str, k: int = 4) -> dict:
        return await gmail_tools.get_style_examples(user_id, thread_id, k)

    return mcp


if __name__ == "__main__":  # pragma: no cover
    build_mcp_server().run()
