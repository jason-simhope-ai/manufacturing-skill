# chat-gateway — digital-twin team chat-ops (v0.2.0-alpha, experimental)

A thin, stdlib-only Python 3.11 gateway that connects a chat platform to twin
"copilots". It owns routing, policy, rate limits, approvals, taint tracking and
the audit log. A `HarnessDriver` runs the model; the gateway never calls a model
API itself. The design spec is
[2026-10-05-digital-twin-team-design.md](../../docs/superpowers/specs/2026-10-05-digital-twin-team-design.md)
(§9 chat-ops, §11 security).

## Try it offline (no credentials, no network)

```bash
python3 infra/chat-gateway/demo.py                 # 8-beat transcript + audit verify + token estimate
python3 tests/gateway/test_gateway.py              # all gateway tests (stdlib unittest)
PYTHONPATH=infra/chat-gateway python3 -m chat_gateway run --roster infra/chat-gateway/fixtures/roster/roster.json \
    --script infra/chat-gateway/fixtures/demo.jsonl
```

When no HMAC keys are set, mock mode prints a `DEMO KEYS` banner and uses public demo keys.

## CLI

| Command | Purpose |
| ------- | ------- |
| `python3 -m chat_gateway run [--roster P] [--adapter mock\|slack\|discord] [--driver mock\|claude-code] [--script F.jsonl] [--pace S]` | Serve events until the adapter stops. |
| `python3 -m chat_gateway post --twin ID --capability ID [--channel ID]` | Make a scheduled post. Call it from OS cron. Limit: 3 per channel per day, kept in `$MFG_TEAM_STATE_DIR/post-limits.json`. |
| `python3 -m chat_gateway audit-verify FILE_OR_DIR` | Check the audit hash chain(s). |
| `python3 -m chat_gateway self-check` | Load the roster, the adapter and the driver, then exit. |

Exit codes: `0` OK · `3` T3 refused · `64` usage error · `70` internal error · `78` config refused.

## Environment (secrets come only from here)

| Variable | Default | Notes |
| -------- | ------- | ----- |
| `MFG_TEAM_ROSTER` | `team/.build/roster.json` | The roster the build step writes. `identities.json` and `bindings.json` are read from the same directory. |
| `MFG_TEAM_ADAPTER` / `MFG_TEAM_DRIVER` | `mock` / `mock` | |
| `MFG_TEAM_STATE_DIR` | `~/.local/state/manufacturing-skill/team` | Must be an absolute path. The gateway writes only here: `audit/<tier>/audit.jsonl` and `post-limits.json`. |
| `MFG_TEAM_AUDIT_HMAC_KEY`, `MFG_TEAM_APPROVAL_HMAC_KEY` | — | Required unless both adapter and driver are mock. Each must be at least 16 characters. Error messages name a missing variable but never print its value. |
| `MFG_TEAM_DAILY_BUDGET_USD` | off | Soft daily spending cap per twin. |
| `MFG_TEAM_MAX_BUDGET_USD`, `MFG_TEAM_TIMEOUT_S` | `0.10`, `60` | Passed to the driver on every call. |

## Package map

| Module | Role |
| ------ | ---- |
| `chat_gateway/adapters/base.py` | Frozen event types (`InboundMessage`, `ApprovalClick`, `ScheduledPost`, `Reply`, `ApprovalCard`) and the `ChatAdapter` protocol |
| `chat_gateway/drivers/base.py` | Frozen `TwinInvocation`, `TwinResult` and `HarnessDriver` types, plus `DriverError` and `result_from_json` |
| `chat_gateway/core.py` | `load_roster` / `validate_roster` (T3 → exit 3; `act*`, dual approval, prompt hash or budget, suspected token → exit 78), `effective_autonomy`, `RateLimiter`, `Gateway` |
| `chat_gateway/sanitize.py` | Text normalization, `<<UNTRUSTED>>` envelopes, tripwires, DLP, output filter |
| `chat_gateway/approvals.py` | `ApprovalBook`: approval cards bound to an args hash, 30-minute TTL, single use; `NoopExecutor` |
| `chat_gateway/audit.py` | Append-only audit log, hash-chained per tier. It stores hashes only and never message text; at T2 and above it also drops `content_len`. |
| `chat_gateway/patterns.py` | `SECRET_PATTERNS`, `NAME_PATTERNS`, `DLP_PATTERNS`. This is the single source for the gateway and for `team/tools/teamctl.py`. |
| `chat_gateway/formatter.py`, `prompt.py`, `config.py` | Reply layout, prompt assembly and the 12,000 B budget, environment config |
| `chat_gateway/adapters/mock.py`, `drivers/mock.py` | Scripted/REPL adapter. The deterministic driver also has a `compliant_malicious` mode. |

The Slack and Discord adapters (WP4) and the claude-code driver (WP5) are
imported lazily. `import chat_gateway.core` never needs a third-party SDK.

## Security posture (alpha)

- The bot answers only when it is @-mentioned, and needs a mention every turn.
- It ignores messages from bots, DMs, externally shared channels, unbound channels and unknown identities. Each case is audited as `policy_denied`.
- Twins have read-only tools (`Read, Grep, Glob`). Any action a model proposes is logged as `tool_denied` and dropped. Approvals come only from structured button clicks, never from chat text.
- Quoted text and code blocks are wrapped in `<<UNTRUSTED>>` envelopes. A tripwire hit, or untrusted content anywhere in the channel window, taints the turn. A tainted turn is capped at `suggest`, gets no approval card, and has its URLs stripped.
- Output filtering runs in this order: strip URLs and images, neutralize mass mentions, mask secrets, block the whole reply if a higher tier is detected, then cap the length at 3,000 characters.
- Rate limits: 6 messages per user per minute, 60 per channel per hour, and 3 scheduled posts per channel per day. Duplicate event ids are rejected for 10 minutes or 1,000 entries.
- Calls are single-threaded, so concurrency is 1, which is within the spec's limit of 2.

The Slack and Discord adapters have not been tested against the real platforms in CI and need credentials to run.
