"""Shared types from Contract 00. Field names match the JSON contract exactly.

Note: `Message.from_` serializes to the JSON key `from` (see api/threads.py serializer).
"""

from __future__ import annotations

from typing import TypedDict


class ReplyPair(TypedDict):
    id: str  # "<thread_id>:<reply_message_id>"
    inbound: str  # cleaned text of the message being answered
    reply: str  # cleaned text of the user's reply
    recipient_email: str  # who the user replied to
    recipient_domain: str
    subject: str
    date: str  # ISO 8601
    reply_words: int


class Message(TypedDict):
    id: str
    from_: str  # "Name <email>"; the JSON key is "from"
    to: list[str]
    date: str  # ISO 8601
    body_text: str  # quoted history and signatures removed


class Thread(TypedDict):
    id: str
    subject: str
    messages: list[Message]  # oldest first
