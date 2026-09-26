"""Gmail MCP tools (Contract B). Plain async Python; the MCP layer is a thin wrapper.

Every function takes `user_id`. The agent's tool wrapper injects `user_id` and hides it
from the LLM schema (the LLM never chooses a user). Limits live here, not in the prompt.
"""

from __future__ import annotations

import asyncio
import base64
import re
from datetime import UTC
from email.mime.text import MIMEText
from email.utils import parseaddr, parsedate_to_datetime

from ..config import get_settings
from ..gmail.client import build_service, run_gmail
from ..style_store import StyleStore, clean_body
from ..types import Message, ReplyPair, Thread

# Limits (Contract B) — enforced in code, never left to the LLM.
MAX_MESSAGES = 10
MAX_BODY_CHARS = 2000
MAX_RELATED = 5
SNIPPET_MAX = 150


# ---------------------------------------------------------------------------
# MIME / header helpers
# ---------------------------------------------------------------------------
def _header(headers: list[dict], name: str) -> str:
    name = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name:
            return h.get("value", "")
    return ""


def _b64url_decode(data: str) -> str:
    if not data:
        return ""
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")


def _walk_parts(payload: dict) -> tuple[str, str]:
    """Return (plain_text, html) by walking the MIME tree, preferring text/plain."""
    plain, html = "", ""
    stack = [payload]
    while stack:
        part = stack.pop()
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data", "")
        if mime == "text/plain" and data and not plain:
            plain = _b64url_decode(data)
        elif mime == "text/html" and data and not html:
            html = _b64url_decode(data)
        for sub in part.get("parts", []) or []:
            stack.append(sub)
    return plain, html


def _to_iso(raw_date: str) -> str:
    try:
        dt = parsedate_to_datetime(raw_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError):
        return raw_date


def _parse_message(msg: dict) -> Message:
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    plain, html = _walk_parts(payload)
    if plain:
        body = clean_body(plain, is_html=False)
    else:
        body = clean_body(html, is_html=True)
    to_raw = _header(headers, "To")
    to_list = [addr.strip() for addr in to_raw.split(",") if addr.strip()]
    return Message(
        id=msg.get("id", ""),
        from_=_header(headers, "From"),
        to=to_list,
        date=_to_iso(_header(headers, "Date")),
        body_text=body[:MAX_BODY_CHARS],
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
async def list_threads(
    user_id: str,
    page_token: str | None = None,
    max_results: int = 25,
    query: str = "in:inbox newer_than:30d",
) -> dict:
    """List one page of threads with metadata for the inbox picker (Inbox service only)."""
    max_results = max(1, min(max_results, 25))
    service = build_service(user_id)

    def _list():
        return service.users().threads().list(
            userId="me", q=query, maxResults=max_results, pageToken=page_token or None
        )

    listing = await run_gmail(user_id, _list)
    thread_ids = [t["id"] for t in listing.get("threads", [])]
    next_token = listing.get("nextPageToken")

    async def _meta(tid: str) -> dict:
        def _get():
            return service.users().threads().get(
                userId="me",
                id=tid,
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )

        thread = await run_gmail(user_id, _get)
        msgs = thread.get("messages", [])
        last = msgs[-1] if msgs else {}
        headers = last.get("payload", {}).get("headers", [])
        from_name, from_email = parseaddr(_header(headers, "From"))
        return {
            "id": tid,
            "subject": _header(headers, "Subject"),
            "from_name": from_name or from_email,
            "from_email": from_email,
            "snippet": (last.get("snippet") or "")[:SNIPPET_MAX],
            "message_count": len(msgs),
            "last_message_at": _to_iso(_header(headers, "Date")),
        }

    threads = await asyncio.gather(*(_meta(tid) for tid in thread_ids))
    return {"threads": list(threads), "next_page_token": next_token}


async def get_thread(user_id: str, thread_id: str, max_messages: int = 10) -> Thread:
    """Full thread, cleaned text, newest `max_messages` (<=10), oldest first."""
    max_messages = max(1, min(max_messages, MAX_MESSAGES))
    service = build_service(user_id)

    def _get():
        return service.users().threads().get(userId="me", id=thread_id, format="full")

    thread = await run_gmail(user_id, _get)
    raw_msgs = thread.get("messages", [])
    subject = ""
    if raw_msgs:
        subject = _header(raw_msgs[0].get("payload", {}).get("headers", []), "Subject")
    # newest N, then oldest-first
    recent = raw_msgs[-max_messages:]
    messages = [_parse_message(m) for m in recent]
    return Thread(id=thread_id, subject=subject, messages=messages)


async def search_related(
    user_id: str,
    query: str,
    exclude_thread_id: str | None = None,
    max_results: int = 5,
) -> list[dict]:
    """Find related threads (metadata + snippet only). Hard cap 5 results."""
    max_results = max(1, min(max_results, MAX_RELATED))
    service = build_service(user_id)

    def _list():
        # fetch a few extra so we can drop the excluded thread and still fill the page
        return service.users().threads().list(
            userId="me", q=query, maxResults=max_results + 2
        )

    listing = await run_gmail(user_id, _list)
    ids = [t["id"] for t in listing.get("threads", []) if t["id"] != exclude_thread_id]
    ids = ids[:max_results]

    async def _meta(tid: str) -> dict:
        def _get():
            return service.users().threads().get(
                userId="me",
                id=tid,
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )

        thread = await run_gmail(user_id, _get)
        msgs = thread.get("messages", [])
        participants = sorted(
            {
                parseaddr(_header(m.get("payload", {}).get("headers", []), "From"))[1]
                for m in msgs
            }
            - {""}
        )
        last = msgs[-1] if msgs else {}
        headers = last.get("payload", {}).get("headers", [])
        return {
            "thread_id": tid,
            "subject": _header(headers, "Subject"),
            "date": _to_iso(_header(headers, "Date")),
            "participants": participants,
            "snippet": (last.get("snippet") or "")[:SNIPPET_MAX],
        }

    return list(await asyncio.gather(*(_meta(tid) for tid in ids)))


async def get_style_examples(user_id: str, thread_id: str, k: int = 4) -> dict:
    """Retrieve style examples for the latest inbound message (Contract C cold-start)."""
    settings = get_settings()
    thread = await get_thread(user_id, thread_id)
    inbound_text, recipient_email = "", ""
    if thread["messages"]:
        latest = thread["messages"][-1]
        inbound_text = latest["body_text"]
        recipient_email = parseaddr(latest["from_"])[1]

    store = StyleStore(user_id, settings.style_store_dir)
    count = store.pair_count()
    summary = store.summary()

    if count == 0:
        return {"summary": summary, "examples": [], "mode": "default"}
    if count < settings.cold_start_min_pairs:
        return {"summary": summary, "examples": [], "mode": "summary_only"}

    pairs = store.retrieve(inbound_text, recipient_email, k=k)
    examples = [{"inbound": p["inbound"], "reply": p["reply"]} for p in pairs]
    return {"summary": summary, "examples": examples, "mode": "retrieval"}


async def fetch_recent_reply_pairs(
    user_id: str, days: int = 30, max_pairs: int = 300
) -> list[ReplyPair]:
    """Find messages the user sent that reply to someone else, as ReplyPair records."""
    service = build_service(user_id)
    query = f"in:sent newer_than:{days}d"

    def _list():
        return service.users().messages().list(
            userId="me", q=query, maxResults=min(max_pairs, 500)
        )

    listing = await run_gmail(user_id, _list)
    sent_ids = [m["id"] for m in listing.get("messages", [])]

    async def _pair(msg_id: str) -> ReplyPair | None:
        def _get():
            return service.users().messages().get(userId="me", id=msg_id, format="full")

        reply_msg = await run_gmail(user_id, _get)
        payload = reply_msg.get("payload", {})
        headers = payload.get("headers", [])
        in_reply_to = _header(headers, "In-Reply-To")
        thread_id = reply_msg.get("threadId", "")
        if not in_reply_to or not thread_id:
            return None  # not a reply

        # Find the inbound message this replied to, within the same thread.
        def _thread():
            return service.users().threads().get(
                userId="me", id=thread_id, format="full"
            )

        thread = await run_gmail(user_id, _thread)
        inbound_msg = _find_by_message_id(thread.get("messages", []), in_reply_to)
        if inbound_msg is None:
            return None

        reply_parsed = _parse_message(reply_msg)
        inbound_parsed = _parse_message(inbound_msg)
        if not reply_parsed["body_text"] or not inbound_parsed["body_text"]:
            return None

        recipient_email = parseaddr(inbound_parsed["from_"])[1]
        return ReplyPair(
            id=f"{thread_id}:{msg_id}",
            inbound=inbound_parsed["body_text"],
            reply=reply_parsed["body_text"],
            recipient_email=recipient_email,
            recipient_domain=recipient_email.split("@")[-1] if "@" in recipient_email else "",
            subject=_header(headers, "Subject"),
            date=reply_parsed["date"],
            reply_words=len(re.findall(r"\S+", reply_parsed["body_text"])),
        )

    results = await asyncio.gather(*(_pair(mid) for mid in sent_ids))
    pairs = [p for p in results if p is not None]
    # newest first
    pairs.sort(key=lambda p: p["date"], reverse=True)
    return pairs[:max_pairs]


async def create_draft(user_id: str, thread_id: str, body_text: str) -> dict:
    """Save a reply draft to Gmail (never sends). Returns {gmail_draft_id}.

    Called only by the agent's save_draft node (not visible to the LLM).
    """
    service = build_service(user_id)

    def _thread():
        return service.users().threads().get(userId="me", id=thread_id, format="metadata")

    thread = await run_gmail(user_id, _thread)
    msgs = thread.get("messages", [])
    if not msgs:
        from ..errors import NotFound

        raise NotFound("Thread has no messages to reply to.")

    latest = msgs[-1]
    headers = latest.get("payload", {}).get("headers", [])
    reply_to = _header(headers, "Reply-To") or _header(headers, "From")
    _, to_email = parseaddr(reply_to)
    subject = _header(headers, "Subject")
    if subject and not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    orig_msg_id = _header(headers, "Message-ID") or _header(headers, "Message-Id")
    references = _header(headers, "References")

    mime = MIMEText(body_text, _charset="utf-8")
    mime["To"] = to_email
    mime["Subject"] = subject
    if orig_msg_id:
        mime["In-Reply-To"] = orig_msg_id
        mime["References"] = f"{references} {orig_msg_id}".strip()
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")

    def _create():
        return service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw, "threadId": thread_id}},
        )

    draft = await run_gmail(user_id, _create)
    return {"gmail_draft_id": draft.get("id", "")}


# ---------------------------------------------------------------------------
def _find_by_message_id(messages: list[dict], message_id: str) -> dict | None:
    target = message_id.strip()
    for m in messages:
        headers = m.get("payload", {}).get("headers", [])
        mid = _header(headers, "Message-ID") or _header(headers, "Message-Id")
        if mid.strip() == target:
            return m
    return None
