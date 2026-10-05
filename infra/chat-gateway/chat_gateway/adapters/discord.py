"""Discord adapter (Gateway WebSocket; outbound connections only, no Interactions endpoint).

NOT exercised against real Discord in CI; needs credentials (`MFG_TEAM_DISCORD_TOKEN`) and
the optional `discord.py` package, imported lazily. Max tier is always T1.

Intents: `GUILDS` + `GUILD_MESSAGES` only — never `MESSAGE_CONTENT` (Discord still delivers
the text of messages that @mention the bot). `allowed_mentions={"parse": []}`, embeds
suppressed, no webhooks, no nickname changes. Guilds that host no bound channel are left.

`discord_to_event(raw, bot_user_id, allowed_guilds)` is the pure, SDK-free mapping under
test; `raw` is a gateway dispatch `{"t": "MESSAGE_CREATE"|"INTERACTION_CREATE", "d": {...}}`.
"""
from __future__ import annotations

import asyncio
import re
import sys
import threading
import time
from typing import Any, Collection

from .base import ApprovalCard, ApprovalClick, Event, InboundMessage, Reply
from ._saas import SaasAdapterBase, attachment_note, sdk_missing

TOKEN_VAR = "MFG_TEAM_DISCORD_TOKEN"
INTENTS = ("guilds", "guild_messages")
FORBIDDEN_INTENTS = ("message_content", "members", "presences", "dm_messages", "guild_reactions")
BOT_PERMISSIONS = ("view_channel", "send_messages", "send_messages_in_threads", "read_message_history")
FORBIDDEN_PERMISSIONS = ("administrator", "manage_webhooks", "change_nickname", "manage_nicknames",
                         "mention_everyone", "manage_messages")
ALLOWED_MENTIONS = {"parse": []}
SUPPRESS_EMBEDS = 1 << 2
MAX_CHUNK = 1900                                     # Discord hard limit is 2,000 characters
CUSTOM_ID_RE = re.compile(r"^mfg:(approve|deny):(apv-[0-9a-f]{4,32}):([0-9a-f]{16,64})$")
COMPONENT_INTERACTION, BUTTON = 3, 2
DISCORD_EPOCH_MS = 1420070400000


def snowflake_ts(snowflake: str | int) -> float:
    return ((int(snowflake) >> 22) + DISCORD_EPOCH_MS) / 1000.0


def discord_message_to_inbound(d: dict, bot_user_id: str,
                               allowed_guilds: Collection[str] | None = None) -> InboundMessage | None:
    """MESSAGE_CREATE → InboundMessage. Non-mentions (incl. all traffic GUILD_MESSAGES delivers
    without content) and the bot's own messages → None. Bot/webhook authors, DMs and guilds
    outside the allowlist keep their flags for the gateway's audit but lose their text."""
    author = d.get("author") or {}
    uid = str(author.get("id") or "")
    if not bot_user_id or uid == bot_user_id:
        return None
    content = str(d.get("content") or "")
    token = re.compile(rf"<@!?{re.escape(bot_user_id)}>")
    pinged = any(str((m or {}).get("id")) == bot_user_id for m in d.get("mentions") or [])  # incl. reply-ping
    if not (pinged or token.search(content)):
        return None                                   # @mention every turn
    text = token.sub("", content).strip()
    text += attachment_note([str(a.get("filename") or "") for a in d.get("attachments") or [] if isinstance(a, dict)])
    guild = d.get("guild_id")
    is_dm = not guild
    is_bot = bool(author.get("bot") or author.get("system") or d.get("webhook_id") or not uid)
    external = bool(guild) and allowed_guilds is not None and str(guild) not in allowed_guilds
    parent = d.get("thread_parent_id")              # set by the transport for messages inside a thread
    return InboundMessage(
        event_id=f"discord:{d['id']}", platform="discord", channel_ref=str(parent or d["channel_id"]),
        thread_ref=str(d["channel_id"] if parent else d["id"]), user_ref=uid,
        text="" if (is_bot or is_dm or external) else text, mentions_bot=True, author_is_bot=is_bot,
        is_dm=is_dm, external_shared=external, ts=snowflake_ts(d["id"]))


def discord_interaction_to_click(d: dict, allowed_guilds: Collection[str] | None = None) -> ApprovalClick | None:
    """INTERACTION_CREATE (button component, delivered over the authenticated gateway) → click.
    Slash commands, selects, modals, DMs, bots, foreign guilds, unknown custom_ids → None."""
    data, guild = d.get("data") or {}, d.get("guild_id")
    if d.get("type") != COMPONENT_INTERACTION or data.get("component_type") != BUTTON or not guild:
        return None
    if allowed_guilds is not None and str(guild) not in allowed_guilds:
        return None
    user = (d.get("member") or {}).get("user") or d.get("user") or {}
    m = CUSTOM_ID_RE.match(str(data.get("custom_id") or ""))
    if not m or not user.get("id") or user.get("bot"):
        return None
    decision, approval_id, nonce = m.groups()
    return ApprovalClick(event_id=f"discord-interaction:{d['id']}", platform="discord", approval_id=approval_id,
                         nonce=nonce, user_ref=str(user["id"]), decision=decision,  # type: ignore[arg-type]
                         ts=snowflake_ts(d["id"]))


def discord_to_event(raw: dict, bot_user_id: str, allowed_guilds: Collection[str] | None = None) -> Event | None:
    kind, d = raw.get("t"), raw.get("d") or {}
    if kind == "MESSAGE_CREATE":
        return discord_message_to_inbound(d, bot_user_id, allowed_guilds)
    if kind == "INTERACTION_CREATE":
        return discord_interaction_to_click(d, allowed_guilds)
    if kind == "GUILD_REFUSED":                     # we left a non-allowlisted guild → audit it
        gid = str(d.get("guild_id") or "")
        return InboundMessage(f"discord-guild-refused:{gid}", "discord", "", None, "", "", False, False,
                              False, True, float(d.get("ts") or 0.0))
    return None


def _chunks(text: str) -> list[str]:
    """Split on line boundaries into ≤ MAX_CHUNK pieces; the 【…】 prefix stays in the first."""
    out, cur = [], ""
    for line in text.splitlines() or [""]:
        for piece in [line[i:i + MAX_CHUNK] for i in range(0, len(line), MAX_CHUNK)] or [""]:
            if cur and len(cur) + 1 + len(piece) > MAX_CHUNK:
                out, cur = out + [cur], piece
            else:
                cur = f"{cur}\n{piece}" if cur else piece
    return out + [cur]


def reply_payload(reply: Reply) -> dict:
    return {"channel_id": reply.channel_ref, "thread_ref": reply.thread_ref, "chunks": _chunks(reply.text),
            "allowed_mentions": dict(ALLOWED_MENTIONS), "flags": SUPPRESS_EMBEDS}


def card_payload(card: ApprovalCard) -> dict:
    body = "\n".join((f"核准卡 {card.approval_id}", *card.lines))
    buttons = [{"type": BUTTON, "style": style, "label": label,
                "custom_id": f"mfg:{decision}:{card.approval_id}:{card.nonce}"}
               for decision, label, style in (("approve", "核准", 3), ("deny", "拒絕", 4))]
    return {"channel_id": card.channel_ref, "thread_ref": card.thread_ref, "chunks": _chunks(body),
            "allowed_mentions": dict(ALLOWED_MENTIONS), "flags": SUPPRESS_EMBEDS,
            "components": [{"type": 1, "components": buttons}]}


class DiscordAdapter(SaasAdapterBase):
    name = "discord"
    SECRET_VARS = (TOKEN_VAR,)

    def __init__(self, bindings: dict, transport: Any = None, **kw: Any):
        super().__init__(bindings, transport, **kw)

    def _real_transport(self) -> Any:                # pragma: no cover - needs SDK + credentials
        return _DiscordPyTransport(self._secrets[0], self.refs)

    def to_event(self, raw: dict) -> Event | None:
        return discord_to_event(raw, self.bot_user_id, getattr(self._transport, "allowed_guilds", None))

    def post(self, reply: Reply) -> str:
        self._guard(reply.channel_ref)
        return self._transport.send("message", reply_payload(reply))

    def post_approval(self, card: ApprovalCard) -> str:
        self._guard(card.channel_ref)
        return self._transport.send("message", card_payload(card))


class _DiscordPyTransport:                           # pragma: no cover - needs SDK + credentials
    def __init__(self, token: str, refs: Collection[str]):
        try:
            import discord
        except ImportError:
            raise sdk_missing("discord", "discord.py") from None
        self.d, self._token, self._refs, self._in = discord, token, refs, False
        intents = discord.Intents.none()
        for name in INTENTS:
            setattr(intents, name, True)
        assert not intents.message_content
        self.client = discord.Client(intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.allowed_guilds: set[str] = set()
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, name="discord-loop", daemon=True).start()

    def _run(self, coro: Any, timeout: float = 30.0) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

    def identity(self) -> str:
        if not self._in:
            self._run(self.client.login(self._token))
            self._in = True
        return str(self.client.user.id)

    def listen(self, sink) -> None:
        self.identity()
        c, d = self.client, self.d

        async def vet(guild) -> None:
            if any(str(ch.id) in self._refs for ch in guild.channels):
                self.allowed_guilds.add(str(guild.id))
                return
            print(f"discord: leaving non-allowlisted guild {guild.id}", file=sys.stderr)
            await guild.leave()
            sink({"t": "GUILD_REFUSED", "d": {"guild_id": str(guild.id), "ts": time.time()}})

        async def on_ready() -> None:
            for g in list(c.guilds):
                await vet(g)

        async def on_guild_join(guild) -> None:
            await vet(guild)

        async def on_message(m) -> None:
            th = isinstance(m.channel, d.Thread)
            sink({"t": "MESSAGE_CREATE", "d": {
                "id": str(m.id), "channel_id": str(m.channel.id), "guild_id": str(m.guild.id) if m.guild else None,
                "thread_parent_id": str(m.channel.parent_id) if th else None,
                "author": {"id": str(m.author.id), "bot": m.author.bot, "system": m.author.system},
                "webhook_id": str(m.webhook_id) if m.webhook_id else None, "content": m.content,
                "mentions": [{"id": str(u.id)} for u in m.mentions],
                "attachments": [{"filename": a.filename} for a in m.attachments]}})

        async def on_interaction(i) -> None:
            if i.type != d.InteractionType.component:
                return
            await i.response.defer()                 # ack within 3 s; the gateway posts the result
            sink({"t": "INTERACTION_CREATE", "d": {
                "id": str(i.id), "type": i.type.value, "guild_id": str(i.guild_id) if i.guild_id else None,
                "channel_id": str(i.channel_id), "user": {"id": str(i.user.id), "bot": i.user.bot},
                "data": dict(i.data or {})}})

        for fn in (on_ready, on_guild_join, on_message, on_interaction):
            c.event(fn)
        asyncio.run_coroutine_threadsafe(c.connect(), self.loop)

    def send(self, kind: str, payload: dict) -> str:
        self.identity()
        return self._run(self._send(payload))

    async def _send(self, p: dict) -> str:
        d, c = self.d, self.client
        cid, tref, ref, target = int(p["channel_id"]), p.get("thread_ref"), None, None
        if tref:
            maybe = c.get_channel(int(tref))
            if isinstance(maybe, d.Thread):
                target = maybe
            else:
                ref = d.MessageReference(message_id=int(tref), channel_id=cid, fail_if_not_exists=False)
        target = target or c.get_channel(cid) or await c.fetch_channel(cid)
        view = None
        for row in p.get("components") or []:
            view = d.ui.View(timeout=None)
            for b in row["components"]:
                view.add_item(d.ui.Button(style=d.ButtonStyle(b["style"]), label=b["label"], custom_id=b["custom_id"]))
        first, last = None, len(p["chunks"]) - 1
        for n, chunk in enumerate(p["chunks"]):
            msg = await target.send(chunk, reference=ref if n == 0 else None, suppress_embeds=True,
                                    allowed_mentions=d.AllowedMentions.none(), view=view if n == last else None)
            first = first or msg
        return str(first.id)

    def close(self) -> None:
        if self._in:
            self._run(self.client.close())
        self.loop.call_soon_threadsafe(self.loop.stop)
