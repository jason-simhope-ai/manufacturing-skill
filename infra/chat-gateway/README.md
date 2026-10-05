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
python3 tests/gateway/test_adapters.py             # Slack/Discord adapter mapping with fake transports
PYTHONPATH=infra/chat-gateway python3 -m chat_gateway run --roster infra/chat-gateway/fixtures/roster/roster.json \
    --script infra/chat-gateway/fixtures/demo.jsonl
```

> **The demo and the mock driver are canned.** Every reply comes from keyword matching in
> `fixtures/mock_driver.json` (first matching entry wins, otherwise the default line). Nothing is
> inferred by a model, so a reply says nothing about what a real twin would answer.

When no HMAC keys are set, mock mode prints a `DEMO KEYS` banner and uses public demo keys.
With adapter and driver both `mock` and no `identities.json` next to the roster (the example
build), the gateway uses synthetic users `mock-<position>` (listed on stderr), and the mock REPL
prints a one-line `(no reply: policy_denied <reason> · audit #n)` instead of staying silent.

## CLI

| Command | Purpose |
| ------- | ------- |
| `python3 -m chat_gateway run [--roster P] [--adapter mock\|slack\|discord] [--driver mock\|claude-code] [--script F.jsonl] [--pace S]` | Serve events until the adapter stops. |
| `python3 -m chat_gateway post --twin ID --capability ID [--channel ID]` | Make a scheduled post. Call it from OS cron. Limit: 3 per channel per day, kept in `$MFG_TEAM_STATE_DIR/post-limits.json`. |
| `python3 -m chat_gateway audit-verify FILE_OR_DIR` | Check the keyed audit chain(s) against `checkpoint.json` (needs `MFG_TEAM_AUDIT_HMAC_KEY`; falls back to the demo key with a notice). Prints each problem, or the per-tier heads to copy off-host. |
| `python3 -m chat_gateway self-check` | Load the roster, the adapter and the driver, then exit. |

Exit codes: `0` OK · `3` T3 refused · `64` usage error · `65` bad line in a `--script` file · `70` internal error · `78` config refused.

### Write your own replay script

Use it with `python3 -m chat_gateway run --adapter mock --script F.jsonl`.

One JSON object per line. Blank lines are skipped, unknown keys are ignored. The whole file is checked
before anything runs: a bad line stops the run with one line such as
`chat_gateway: script line 2: type "message" needs "id"` and exit 65 (no traceback, nothing replayed).
Unknown `type` values, bad JSON, a missing required field and a non-numeric `ts` are all caught that way.
The file may be at most 2,000,000 bytes.

| `type` | Field | Required | Default | Meaning |
| ------ | ----- | -------- | ------- | ------- |
| `message` | `id` | yes | — | Event id. Reusing an id inside 10 minutes of script time is rejected as `duplicate_event`. |
| | `channel` | no | `""` | Bound channel ref (case-sensitive; for the example roster: `qa-floor`, `daily-ops`). An unknown one is `unbound_channel`. |
| | `user` | no | `""` | Platform user id. It must exist in `identities.json`. With no `identities.json` next to the roster, use the synthetic `mock-<position>` ids that the gateway lists on stderr (example: `mock-qa-lead`). |
| | `text` | no | `""` | The message. Start with the twin's name or alias (`@品保 …`) to route. Otherwise the channel's `defaultTwin` answers. |
| | `mention` | no | `true` | `false` = not @-mentioned: dropped as `no_mention`. |
| | `bot`, `dm`, `external` | no | `false` | Mark the author as a bot, a DM, an externally shared channel. Each is denied and audited. |
| | `thread` | no | `null` | Thread ref. |
| | `ts` | no | previous event + 10 s | Epoch seconds. The first event without one uses the wall clock. |
| `approval_click` | `id` | yes | — | Event id. |
| | `approval_id`, `nonce`, `user` | no | `""` | From the approval card the gateway printed. |
| | `decision` | no | `deny` | `approve`, or anything else = deny. |
| | `ts` | no | previous + 10 s | As above. |
| `scheduled` | `twin`, `capability`, `channel` | yes | — | A cron-style post. Limit: 3 per channel per day. |
| `note` | any, e.g. `title`, `beat` | no | — | Narration for `demo.py`. Not an event; the CLI ignores it. |

```jsonl
{"type":"message","id":"m1","channel":"qa-floor","user":"mock-qa-lead","text":"@品保 NCR-EX-012 要不要升級 8D？","ts":1791158100}
{"type":"approval_click","id":"c1","approval_id":"apv-0000","nonce":"0000","user":"mock-qa-lead","decision":"approve","ts":1791158160}
{"type":"scheduled","twin":"production-manager","capability":"briefing-risk-check","channel":"daily-ops"}
{"type":"note","title":"narration only"}
```

Rules to know before you replay NCRs:

- **Replies are canned.** The mock driver picks a reply by keyword from `fixtures/mock_driver.json` (a tracked file); for any other text you get the default line. To make your own question get a useful answer you must edit a copy of that file for now. There is no `--fixture` option yet (spec follow-up).
- **Rate limits follow the script's clock.** In `--script` mode the gateway clock is the script's `ts`, not the wall clock, so a replay is never throttled by how fast it runs. The limits still apply to script time: more than 6 messages from one user within 60 script seconds, or more than 60 in a channel within an hour, are `rate_limited`. Spread the `ts` values (default: 10 s apart). `--pace S` only sleeps between events so you can read the output. Audit records carry script time.
- Never put real customer data, names or ids in a script that lives in the repo. Keep such files under `team/local/` or outside the repo.

## Environment (secrets come only from here)

| Variable | Default | Notes |
| -------- | ------- | ----- |
| `MFG_TEAM_ROSTER` | `team/.build/roster.json` | The roster the build step writes. `identities.json` and `bindings.json` are read from the same directory. |
| `MFG_TEAM_ADAPTER` / `MFG_TEAM_DRIVER` | `mock` / `mock` | |
| `MFG_TEAM_STATE_DIR` | `~/.local/state/manufacturing-skill/team` | Must be an absolute path. The gateway writes only here: `audit/<tier>/audit.jsonl`, `audit/checkpoint.json` and `post-limits.json`. |
| `MFG_TEAM_DENYLIST` | `team/local/names.denylist` if present | Local denylist (one regex per line). A hit counts as T2 for inbound DLP and the output filter. If the variable is set, the file must exist; a bad regex refuses start (exit 78), naming only the line number. |
| `MFG_TEAM_AUDIT_HMAC_KEY`, `MFG_TEAM_APPROVAL_HMAC_KEY` | — | Required unless both adapter and driver are mock. Each must be at least 16 characters. Error messages name a missing variable but never print its value. |
| `MFG_TEAM_DAILY_BUDGET_USD` | off | Soft daily spending cap per twin, at most 1000. |
| `MFG_TEAM_MAX_BUDGET_USD`, `MFG_TEAM_TIMEOUT_S` | `0.10`, `60` | Passed to the driver on every call. Budget at most 5 USD; timeout 5–600 s. |

Numbers must be finite: `nan`, `inf`, a value out of range or not a number refuses start with exit 64, naming the variable.

## Package map

| Module | Role |
| ------ | ---- |
| `chat_gateway/adapters/base.py` | Frozen event types (`InboundMessage`, `ApprovalClick`, `ScheduledPost`, `Reply`, `ApprovalCard`) and the `ChatAdapter` protocol |
| `chat_gateway/drivers/base.py` | Frozen `TwinInvocation`, `TwinResult` and `HarnessDriver` types, plus `DriverError` and `result_from_json` |
| `chat_gateway/core.py` | `load_roster` / `validate_roster` (T3 → exit 3; `act*`, dual approval, prompt hash or budget, suspected token, an id outside the lint pattern → exit 78), `effective_autonomy`, `RateLimiter`, `Gateway` |
| `chat_gateway/sanitize.py` | Text normalization, `<<UNTRUSTED>>` envelopes, tripwires, DLP, output filter |
| `chat_gateway/approvals.py` | `ApprovalBook`: approval cards bound to an args hash, 30-minute TTL, single use; `NoopExecutor` |
| `chat_gateway/audit.py` | Append-only audit log. Each tier is an HMAC-SHA256 chain keyed by `MFG_TEAM_AUDIT_HMAC_KEY`; `checkpoint.json` (signed, rewritten after every append) holds each tier's count, last seq and head MAC, so `verify` catches edits, deletions, reordering, truncation, a removed tier file and seq gaps. A rollback of log *and* checkpoint is only caught by an earlier off-host copy of the checkpoint: shipping it off-host is the operator's job. `content_sha256` holds a keyed content tag, never message text; at T2 and above `content_len` is dropped too. |
| `chat_gateway/patterns.py` | `SECRET_PATTERNS`, `NAME_ZH`/`NAME_OTHER`/`NAME_PATTERNS`, `PII_PATTERNS`, `DLP_PATTERNS`, `valid_ubn`, `ubn_hit`. The single source: `team/tools/_teamlib.py` (teamctl, deid) loads this file and keeps no copy. |
| `chat_gateway/formatter.py`, `prompt.py`, `config.py` | Reply layout (`DRAFT` label at `draft`), the 12,000 B prompt budget and token estimate, environment config |
| `chat_gateway/adapters/mock.py`, `drivers/mock.py` | Scripted/REPL adapter. The deterministic driver also has a `compliant_malicious` mode. |
| `chat_gateway_ext/slack.py`, `discord.py`, `_saas.py` | Real-platform adapters: pure event mappings (`slack_to_event`, `discord_to_event`), the tier gate, the secret checks, and SDK transports that are imported lazily |

The Slack and Discord adapters (WP4) and the claude-code driver (WP5) are
imported lazily. `import chat_gateway.core` never needs a third-party SDK.

## Security posture (alpha)

- The bot answers only when it is @-mentioned, and needs a mention every turn.
- It ignores messages from bots, DMs, externally shared channels, unbound channels and unknown identities. Each case is audited as `policy_denied`.
- Twins have read-only tools (`Read, Grep, Glob`). Any action a model proposes is logged as `tool_denied` and dropped. Approvals come only from structured button clicks, never from chat text.
- Input is NFKC-normalised and stripped of every format/zero-width/bidi/tag character, variation selectors and CGJ before DLP, tripwires and @-routing.
- Quoted text, code blocks and `[附件]` file-name lines are wrapped in `<<UNTRUSTED>>` envelopes. A tripwire hit, or an untrusted message still in the channel window, taints the turn. A tainted turn is capped at `suggest`, gets no approval card, and has its URLs stripped. Replies carry only their own turn's taint, so the taint leaves once the offending message rolls out of the window.
- The compiled prompt's `promptSha` is re-checked on every call; a changed file is refused (`driver_error prompt_sha_mismatch`).
- An approved action runs exactly as hashed: the book deep-copies it at creation and re-hashes it before executing.
- `policy.cloudTierCeiling` and `saasTierCeiling` above T1 are refused at load (alpha hard cap; lint E047).
- Output filtering runs in this order: strip URLs and images, neutralize mass mentions, mask secrets, mask emails and Taiwan phone numbers (`[REDACTED:email]`, `[REDACTED:tw-mobile]`; counted in the audit `redactions.pii`), block the whole reply if a higher tier is detected, then cap the length at 3,000 characters.
- Inbound DLP is a word-and-shape alarm. T2 (blocked in a T1 channel): `機密`/`confidential`, a Taiwan unified business number only with a cue word (`統編`, `統一編號`, `VAT`, `公司`, `股份`, `發票`) and a valid checksum, national id, NT$/US$/萬元 amounts, any email address, Taiwan mobile numbers, Taiwan landlines written with a separator after the area code (`02-1234-5678`), and the local denylist. T3 (refused): the Chinese words and `ITAR`/`EAR`/`CUI` listed in `patterns.py`.
- Rate limits: 6 messages per user per minute, 60 per channel per hour, and 3 scheduled posts per channel per day. Duplicate event ids are rejected for 10 minutes or 1,000 entries.
- Twin and channel ids must match `^[a-z][a-z0-9-]{1,40}$` and capability ids `^[a-z0-9][a-z0-9-]{1,40}$` (the same patterns as the linter); anything else is refused at load (exit 78).
- A post that fails on the chat platform (rate limit, missing channel, timeout, the adapter's own unbound-channel refusal) is audited as `post_failed` with the exception class name only and skipped; the gateway keeps serving other events. `chat_gateway post` exits 70 when its post failed.
- Calls are single-threaded, so concurrency is 1, which is within the spec's limit of 2.

The Slack and Discord adapters have not been tested against the real platforms in CI and need credentials to run.

## Slack and Discord adapters

> **Not exercised in CI; needs credentials.** CI tests only the event mapping and
> the outbound payloads, using fake transports (`python3 tests/gateway/test_adapters.py`).
> No code in this repo has been run against a real Slack workspace or Discord guild.
> Try a test workspace first (gate G1, spec §11.6).

The core needs no third-party packages. Install an SDK only for the adapter you run:

```bash
pip install -r infra/chat-gateway/requirements-optional.txt   # slack_sdk>=3.27,<4 and discord.py>=2.3,<3
```

If the SDK is missing, the adapter refuses to start (exit 78) and prints the line above.

| | Slack (`--adapter slack`) | Discord (`--adapter discord`) |
| - | ------------------------- | ----------------------------- |
| Transport | Socket Mode: outbound WebSocket only. No Request URL and no inbound HTTP. | Gateway WebSocket. No Interactions Endpoint URL. |
| Grant exactly | Bot token scopes `app_mentions:read` and `chat:write`. App-level token scope `connections:write`. Bot event `app_mention`. Interactivity on, with no Request URL; clicks arrive over the socket. | OAuth2 scope `bot`. Gateway intents `GUILDS` and `GUILD_MESSAGES`. Bot permissions View Channels, Send Messages, Send Messages in Threads and Read Message History. Discord needs the last one to post a reply that references the question; the adapter never fetches history. |
| Never grant | `channels:history`, `groups:history`, `im:history`, `mpim:history`, `chat:write.public`, `chat:write.customize`, `users:read`, `users:read.email`, `reactions:write`, `incoming-webhook`, `files:read` | The privileged `MESSAGE_CONTENT`, `SERVER MEMBERS` and `PRESENCE` intents; `applications.commands`, `webhook.incoming`; Administrator, Manage Webhooks, Change or Manage Nicknames, Mention Everyone, Manage Messages |
| Secrets (env only) | `MFG_TEAM_SLACK_BOT_TOKEN` (`xoxb-…`), `MFG_TEAM_SLACK_APP_TOKEN` (`xapp-…`) | `MFG_TEAM_DISCORD_TOKEN` |
| Outbound | Replies go into the thread. `unfurl_links=false`, `unfurl_media=false`, `link_names=false`, `parse=none`, and `& < >` are escaped. No `username` or `icon_*` override. | Each reply references the question or goes into its thread. `allowed_mentions={"parse": []}`, embeds suppressed, text split at 1,900 characters. The adapter creates no webhooks and makes no nickname changes. |
| Approval clicks | `block_actions` buttons `mfg_approve` / `mfg_deny`, value `<approval_id>:<nonce>` | Button `custom_id` `mfg:<approve\|deny>:<approval_id>:<nonce>` |
| Max tier | Always T1 | Always T1 |

Spec §9.2 also lists `users:read` and `reactions:write` for Slack. This adapter leaves both
out: it reads bot and team status from the event fields, and it never adds reactions. Invite
the Slack bot only to bound channels. Without `chat:write.public` it can post only where it
is a member. Discord delivers the text of a message that @mentions the bot, including a
reply-ping, even without `MESSAGE_CONTENT`. All other guild traffic arrives with empty
content, and the adapter drops it.

**Behaviour shared by both adapters (defence in depth, on top of the gateway's checks):**

- Only @mentions reach the gateway. The bot mention is removed from the text. The bot's own messages are dropped.
- Messages from bots or webhooks, DMs, externally shared channels and non-allowlisted guilds are forwarded with their flags set but with the text removed. The gateway can then audit `policy_denied` without seeing the content.
- Discord leaves any guild that holds no bound channel. It does this at startup and whenever it is added to a guild, and it emits an event that the gateway audits. The guild allowlist is mandatory: a transport without one is refused at construction, and until the allowlist is filled every guild is treated as foreign.
- Attachments are reported by file name only, as a `[附件] …` line (control characters, C1 and U+2028/U+2029 replaced, so a name cannot start a new line). They are never downloaded. The gateway wraps that line in an `<<UNTRUSTED … source=attachment>>` envelope, so a message with an attachment is a tainted turn (no approval card, no URLs, autonomy at most `suggest`).
- Approvals come only from button clicks, which the platform delivers over the authenticated socket. Chat text is never parsed as a click. A malformed or unknown button is dropped (ids and nonces must match in full; a trailing newline is malformed).
- `post()` refuses any channel that is not in `bindings.json` by raising `PermissionError`. This also covers DMs.
- Error messages name a missing variable but never print its value, and `repr()` never shows tokens. Do not turn on `DEBUG` logging for `slack_sdk` or `discord`.

`bindings.json` (written by `team/tools/build.py` from `team/local/bindings.local.yaml`) maps
logical channels to platform ids:
`{"schema": 1, "channels": {"qa-floor": {"platform": "slack", "ref": "<channel id>"}}}`.
An adapter refuses to start if no channel is bound for its platform.

**No T2 on SaaS chat in alpha.** Both adapters are capped at T1, hard. T2 on Slack is
deferred (spec §14: it needs a verified T2 model route and DLP). A leftover `riskAcceptance`
block in `bindings.json` makes the adapter refuse to start (exit 78) rather than be ignored.

## claude-code driver

`--driver claude-code` runs one restricted `claude -p` process per message
(`chat_gateway_ext/claude_code.py`, spec §9.5). It is the only place a model runs.
Two packages: `chat_gateway/` is the hardened core (no subprocess, no network; enforced by `TestStaticSecurity`), and
`chat_gateway_ext/` holds integrations that cross the process/network boundary (this driver and the Slack/Discord adapters) and so sit outside that invariant.
`load_driver_class("claude-code")` and `load_adapter_class("slack"|"discord")` import `chat_gateway_ext.*` only when asked by name; the core never imports it at module import time (a test checks this).
Tests use a fake `claude` script (`python3 tests/gateway/test_claude_code_driver.py`); CI never calls a real one.

| Variable | Default | Notes |
| -------- | ------- | ----- |
| `MFG_TEAM_CLAUDE_CONFIG_DIR` | — (required) | A dedicated service-account `CLAUDE_CONFIG_DIR`. It must be an absolute path to an existing directory and must not be `~/.claude`. The child gets its realpath. |
| `ANTHROPIC_API_KEY` | — (required) | Service-account key. `MFG_TEAM_ANTHROPIC_API_KEY` is accepted as an alias. Never printed or logged. |
| `MFG_TEAM_CLAUDE_BIN` | `claude` | Path or name of the CLI. Resolved once to an absolute path; empty and relative `PATH` entries are ignored. |
| `MFG_TEAM_MAX_BUDGET_USD`, `MFG_TEAM_TIMEOUT_S` | `0.10`, `60` | Per call. The smaller of the driver value and the invocation value wins. |
| `MFG_TEAM_DATA_T1` | off | Added as `--add-dir` (realpath) only when set and granted to the invocation. Must be an absolute path. |

Every call uses this fixed argument list (no shell, never built from chat text):

```
claude -p --output-format json --restricted --strict-mcp-config --tools "Read,Grep,Glob"
  --system-prompt-file <temp copy> --json-schema '<TWIN_RESULT_SCHEMA>' --no-session-persistence
  --max-budget-usd <n> [--add-dir <MFG_TEAM_DATA_T1>]
```

- **Environment.** The child sees only `PATH`, `HOME`, `CLAUDE_CONFIG_DIR` and `ANTHROPIC_API_KEY`. `PATH` is fixed: the resolved CLI's directory, then `/usr/local/bin:/usr/bin:/bin`. The user message and channel window go in through stdin.
- **System prompt.** The compiled twin prompt plus a short header (tier, effective autonomy, taint, predict-first) is written to a `0600` file `twin-*.prompt.md` under `$MFG_TEAM_STATE_DIR/driver-tmp/` and deleted after the call, including on failure.
- **Working directory.** `team/.build/ref/` (spec §9.5). The prompt's index lines read `<kind>/<id>.md`, relative to it. `identities.json`, `bindings.json`, `roster.json` and every twin prompt live one level up, outside the model's reach; the driver refuses to run if any of them, or any `*.prompt.md`, appears under `ref/`, or if `ref/` or anything under it is a symlink. It runs in the realpath of `ref/`.
- **Prompt integrity.** The driver re-hashes the compiled prompt bytes it sends and refuses them if they no longer match the roster's `promptSha`.
- **Output.** The CLI's JSON envelope is parsed; `structured_output` (or a JSON `result` string) becomes a `TwinResult`, with `usage` filled from the envelope. `TWIN_RESULT_SCHEMA` is also kept as `chat_gateway_ext/twin_result.schema.json`; a test keeps the two identical.
- **Failures.** A non-zero exit, a timeout, unparsable output (more than 1 MB, invalid UTF-8, nesting too deep, duplicate JSON keys) or a CLI-reported error becomes a `DriverError` with a short message. The child runs in its own process group, killed on every exit path; the timeout is a hard deadline even if a descendant keeps the output pipe open. Stderr is discarded, never forwarded.
- **Self-check.** `self_check()` runs `claude --version` and `claude --help` and refuses to start (exit 78) if any pinned flag is missing. `--system-prompt[-file]` in the help text is accepted. It also requires the config dir and the API key.
- **Billing.** The driver needs an Anthropic API key (`ANTHROPIC_API_KEY`) and spends that account's API credit, not a personal subscription. `--max-budget-usd` caps each call. Use a service account, not a personal login, for a shared bot.
