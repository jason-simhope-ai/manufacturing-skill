"""Slack adapter (Socket Mode; outbound connections only, no inbound HTTP).

NOT exercised against real Slack in CI; needs credentials (`MFG_TEAM_SLACK_BOT_TOKEN`,
`MFG_TEAM_SLACK_APP_TOKEN`) and the optional `slack_sdk` package, imported lazily.

Minimal app config: bot scopes `app_mentions:read`, `chat:write`; app-level token scope
`connections:write` (Socket Mode); event subscription `app_mention` only; Interactivity on
(button clicks arrive over the socket). No webhooks, no `chat:write.customize`.

At startup the adapter reads the bot token's granted scopes from the `x-oauth-scopes` header of
the `auth.test` response and refuses to start (exit 78) if any scope beyond `BOT_SCOPES` is
granted, if a required one is missing, or if the header is absent (S06).

`slack_to_event(envelope, bot_user_id, refs)` is the pure, SDK-free mapping under test.
"""
from __future__ import annotations

import re
from typing import Any, Collection, Mapping

from chat_gateway import ConfigRefused
from chat_gateway.adapters.base import ApprovalCard, ApprovalClick, Event, InboundMessage, Reply
from chat_gateway_ext._saas import DECISIONS, SaasAdapterBase, approval_ref, attachment_note, sdk_missing

BOT_TOKEN_VAR = "MFG_TEAM_SLACK_BOT_TOKEN"
APP_TOKEN_VAR = "MFG_TEAM_SLACK_APP_TOKEN"
BOT_SCOPES = ("app_mentions:read", "chat:write")
APP_TOKEN_SCOPES = ("connections:write",)
EVENT_SUBSCRIPTIONS = ("app_mention",)
# Same list as the README "Never grant" row (a test keeps them in sync).
FORBIDDEN_SCOPES = ("channels:history", "groups:history", "im:history", "mpim:history", "chat:write.public",
                    "chat:write.customize", "users:read", "users:read.email", "reactions:write",
                    "incoming-webhook", "files:read")
SCOPES_HEADER = "x-oauth-scopes"
ACTION_IDS = {"mfg_approve": "approve", "mfg_deny": "deny"}
POST_FLAGS = {"unfurl_links": False, "unfurl_media": False, "link_names": False, "parse": "none"}
_UNESCAPE = (("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"))
# EXT-17: a `plain_text` section block holds at most 3,000 characters; a longer card body would be
# rejected by Slack (`invalid_blocks`). The body is cut to fit, with a visible marker.
CARD_TEXT_MAX = 3000
TRUNCATED = "…（已截斷）"


def _escape(text: str) -> str:
    """Slack control sequences (<@U…>, <!here>, <url|label>) cannot survive this."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def scopes_from_headers(headers: Mapping[str, Any] | None) -> list[str] | None:
    """The comma-separated `x-oauth-scopes` response header as a list (case-insensitive name), or None."""
    for name, value in (headers or {}).items():
        if str(name).lower() == SCOPES_HEADER:
            if isinstance(value, (list, tuple)):
                value = ",".join(str(v) for v in value)
            return [s.strip() for s in str(value).split(",") if s.strip()]
    return None


def check_granted_scopes(granted: Collection[str] | None) -> None:
    """Refuse (exit 78) unless the bot token holds exactly BOT_SCOPES. Scope names are not secrets,
    so the refusal names them."""
    if granted is None:
        raise ConfigRefused(f"Slack auth.test returned no {SCOPES_HEADER} header; cannot verify the bot "
                            "token's scopes, refusing to start")
    got = {str(s).strip() for s in granted if str(s).strip()}
    extra, missing = sorted(got - set(BOT_SCOPES)), sorted(set(BOT_SCOPES) - got)
    if extra:
        flagged = [s + (" (never grant)" if s in FORBIDDEN_SCOPES else "") for s in extra]
        raise ConfigRefused("the Slack bot token has scopes beyond " + ", ".join(BOT_SCOPES) + ": "
                            + ", ".join(flagged) + "; remove them under OAuth & Permissions and reinstall the app")
    if missing:
        raise ConfigRefused("the Slack bot token lacks required scopes: " + ", ".join(missing))


def slack_event_to_inbound(payload: dict, bot_user_id: str) -> InboundMessage | None:
    """Map an Events API payload (`events_api` envelope `.payload`) to an InboundMessage.

    Non-mentions and the bot's own messages → None. Bot authors, DMs and externally
    shared channels keep their flags (so the gateway audits `policy_denied`) but lose
    their text at this boundary.
    """
    ev = payload.get("event") or {}
    if ev.get("type") not in ("app_mention", "message") or not bot_user_id:
        return None
    user = str(ev.get("user") or "")
    if user == bot_user_id:
        return None
    raw = str(ev.get("text") or "")
    token = re.compile(rf"<@{re.escape(bot_user_id)}(?:\|[^>]*)?>")
    if not token.search(raw):
        return None                                   # @mention every turn
    text = token.sub("", raw).strip()
    for a, b in _UNESCAPE:
        text = text.replace(a, b)
    text += attachment_note([str(f.get("name") or "") for f in ev.get("files") or [] if isinstance(f, dict)])
    is_bot = bool(ev.get("bot_id") or ev.get("bot_profile") or ev.get("subtype") == "bot_message" or not user)
    channel = str(ev.get("channel") or "")
    is_dm = ev.get("channel_type") in ("im", "mpim") or channel.startswith("D")
    team, user_team = payload.get("team_id"), ev.get("user_team")
    external = bool(payload.get("is_ext_shared_channel") or ev.get("is_ext_shared_channel")
                    or (team and user_team and team != user_team))
    ts = str(ev.get("ts") or ev.get("event_ts") or "0")
    return InboundMessage(
        event_id=str(payload.get("event_id") or f"{channel}:{ts}"), platform="slack", channel_ref=channel,
        thread_ref=str(ev.get("thread_ts") or ts), user_ref=user,
        text="" if (is_bot or is_dm or external) else text, mentions_bot=True, author_is_bot=is_bot,
        is_dm=is_dm, external_shared=external, ts=float(ts))


def slack_action_to_click(payload: dict, refs: Collection[str] | None = None) -> ApprovalClick | None:
    """Map an `interactive` block_actions payload (a Slack-authenticated button click) to a click.
    Anything else — shortcuts, modals, selects, unknown buttons, other workspaces — → None."""
    if payload.get("type") != "block_actions" or len(payload.get("actions") or []) != 1:
        return None
    act, user = payload["actions"][0], payload.get("user") or {}
    decision = ACTION_IDS.get(str(act.get("action_id")))
    if act.get("type") != "button" or decision not in DECISIONS or not user.get("id"):
        return None
    team = (payload.get("team") or {}).get("id")
    if team and user.get("team_id") and user["team_id"] != team:
        return None
    channel = str((payload.get("channel") or {}).get("id") or (payload.get("container") or {}).get("channel_id") or "")
    if refs is not None and channel not in refs:
        return None
    approval_id, _, nonce = str(act.get("value") or "").partition(":")
    if not approval_ref(approval_id, nonce):
        return None
    ts = str(act.get("action_ts") or "0")
    return ApprovalClick(event_id=f"slack-action:{payload.get('trigger_id') or ts}", platform="slack",
                         approval_id=approval_id, nonce=nonce, user_ref=str(user["id"]),
                         decision=decision, ts=float(ts), channel_ref=channel)  # type: ignore[arg-type]


def slack_to_event(envelope: dict, bot_user_id: str, refs: Collection[str] | None = None) -> Event | None:
    """Socket Mode envelope `{"type": "events_api"|"interactive", "payload": {...}}` → Event."""
    payload = envelope.get("payload") or {}
    if envelope.get("type") == "events_api":
        return slack_event_to_inbound(payload, bot_user_id)
    if envelope.get("type") == "interactive":
        return slack_action_to_click(payload, refs)
    return None                                       # slash commands, hello, disconnect…


def reply_payload(reply: Reply) -> dict:
    return {"channel": reply.channel_ref, "thread_ts": reply.thread_ref, "text": _escape(reply.text), **POST_FLAGS}


def _fit(text: str, limit: int = CARD_TEXT_MAX) -> str:
    return text if len(text) <= limit else text[:limit - len(TRUNCATED)] + TRUNCATED


def card_payload(card: ApprovalCard) -> dict:
    body = _fit("\n".join((f"核准卡 {card.approval_id}", *card.lines)))
    value = f"{card.approval_id}:{card.nonce}"
    buttons = [{"type": "button", "action_id": aid, "value": value, "style": style,
                "text": {"type": "plain_text", "text": label, "emoji": False}}
               for aid, label, style in (("mfg_approve", "核准", "primary"), ("mfg_deny", "拒絕", "danger"))]
    return {"channel": card.channel_ref, "thread_ts": card.thread_ref, "text": _escape(body), **POST_FLAGS,
            "blocks": [{"type": "section", "text": {"type": "plain_text", "text": body, "emoji": False}},
                       {"type": "actions", "block_id": "mfg_approval", "elements": buttons}]}


class SlackAdapter(SaasAdapterBase):
    name = "slack"
    SECRET_VARS = (BOT_TOKEN_VAR, APP_TOKEN_VAR)

    def __init__(self, bindings: dict, transport: Any = None, **kw: Any):
        super().__init__(bindings, transport, **kw)
        probe = getattr(self._transport, "granted_scopes", None)     # S06: before any event is served
        check_granted_scopes(probe() if callable(probe) else None)

    def _real_transport(self) -> Any:                # pragma: no cover - needs SDK + credentials
        bot, app = self._secrets
        if not bot.startswith("xoxb-") or not app.startswith("xapp-"):
            raise ConfigRefused(f"{BOT_TOKEN_VAR} must be a bot token (xoxb-…) and {APP_TOKEN_VAR} an "
                                "app-level token (xapp-…)")
        return _SlackSdkTransport(bot, app)

    def to_event(self, raw: dict) -> Event | None:
        return slack_to_event(raw, self.bot_user_id, self.refs)

    def post(self, reply: Reply) -> str:
        self._guard(reply.channel_ref)
        return self._transport.send("chat.postMessage", reply_payload(reply))

    def post_approval(self, card: ApprovalCard) -> str:
        self._guard(card.channel_ref)
        return self._transport.send("chat.postMessage", card_payload(card))


class _SlackSdkTransport:                            # pragma: no cover - needs SDK + credentials
    def __init__(self, bot_token: str, app_token: str):
        try:
            from slack_sdk import WebClient
            from slack_sdk.socket_mode import SocketModeClient
            from slack_sdk.socket_mode.response import SocketModeResponse
        except ImportError:
            raise sdk_missing("slack", "slack_sdk") from None
        self._ack = SocketModeResponse
        self.web = WebClient(token=bot_token)
        self.sm = SocketModeClient(app_token=app_token, web_client=self.web)
        self._auth: tuple[str, list[str] | None] | None = None

    def _auth_test(self) -> tuple[str, list[str] | None]:
        if self._auth is None:
            resp = self.web.auth_test()
            self._auth = (str(resp["user_id"]), scopes_from_headers(getattr(resp, "headers", None)))
        return self._auth

    def identity(self) -> str:
        return self._auth_test()[0]

    def granted_scopes(self) -> list[str] | None:
        return self._auth_test()[1]

    def listen(self, sink) -> None:
        def on_request(client, req) -> None:
            client.send_socket_mode_response(self._ack(envelope_id=req.envelope_id))  # ack first, always
            sink({"type": req.type, "payload": req.payload})
        self.sm.socket_mode_request_listeners.append(on_request)
        self.sm.connect()

    def send(self, method: str, payload: dict) -> str:
        assert method == "chat.postMessage"
        return str(self.web.chat_postMessage(**{k: v for k, v in payload.items() if v is not None})["ts"])

    def close(self) -> None:
        self.sm.close()
