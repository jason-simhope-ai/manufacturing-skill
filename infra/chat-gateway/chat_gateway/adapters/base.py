"""Frozen chat-side interface (§9.1): event types, outbound types, `ChatAdapter`.

Adapters translate a platform into these events and post `Reply` /
`ApprovalCard` back. Contract for adapter authors (WP4):

* `InboundMessage.text` is the message with the bot mention itself removed;
  `mentions_bot` says whether the bot was @-mentioned this turn.
* `channel_ref` / `user_ref` are raw platform ids; the gateway maps them to
  logical channels / positions through `bindings.json` / `identities.json`.
  (Mock platform only: an unbound `channel_ref` equal to a logical channel id
  is accepted as-is.)
* `thread_ref` is the thread to reply into. For a top-level message, set it to
  the message's own platform ref (e.g. Slack `ts`); if left None the gateway
  threads under `event_id`, which only the mock adapter relies on.
* Approval decisions arrive only as `ApprovalClick` (structured button
  events), never from chat text. `ApprovalClick.channel_ref` is the raw id of
  the channel the button was clicked in (the parent channel for a thread); the
  gateway rejects a click whose channel differs from the card's (EXT-03).
* `post()` must post into `reply.thread_ref` when given, never change the
  display name, and return the platform message ref.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Literal, Protocol, Union


@dataclass(frozen=True)
class InboundMessage:            # adapter → gateway
    event_id: str
    platform: str
    channel_ref: str
    thread_ref: str | None
    user_ref: str
    text: str
    mentions_bot: bool
    author_is_bot: bool
    is_dm: bool
    external_shared: bool
    ts: float


@dataclass(frozen=True)
class ApprovalClick:             # structured click; mock script {"type":"approval_click",...}
    event_id: str
    platform: str
    approval_id: str
    nonce: str
    user_ref: str
    decision: Literal["approve", "deny"]
    ts: float
    channel_ref: str             # where the button was clicked; must equal the card's channel


@dataclass(frozen=True)
class ScheduledPost:             # produced by `chat_gateway post`
    twin_id: str
    capability_id: str
    channel_id: str


Event = Union[InboundMessage, ApprovalClick, ScheduledPost]


@dataclass(frozen=True)
class Reply:
    channel_ref: str
    thread_ref: str | None
    text: str
    twin_id: str
    audit_seq: int


@dataclass(frozen=True)
class ApprovalCard:
    approval_id: str
    nonce: str
    channel_ref: str
    thread_ref: str | None
    lines: tuple[str, ...]
    args_hash: str
    expires_at: float


class ChatAdapter(Protocol):
    name: str                                  # "mock" | "slack" | "discord"
    hosting: Literal["local", "saas"]
    max_tier: str                              # mock "T2"; slack "T1"; discord "T1"

    def events(self) -> Iterator[Event]: ...
    def post(self, reply: Reply) -> str: ...
    def post_approval(self, card: ApprovalCard) -> str: ...
    def close(self) -> None: ...
