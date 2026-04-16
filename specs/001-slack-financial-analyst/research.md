# Research: Slack Financial Analyst

**Branch**: `001-slack-financial-analyst` | **Date**: 2026-04-16 (refreshed after clarification session)

## Decision 1: Slack SDK Choice

**Decision**: Use `slack_sdk` (plain SDK), not `slack_bolt`  
**Rationale**: `slack_bolt` is designed for event-driven apps (webhooks, socket mode). This project polls on a schedule — no incoming events to handle. `slack_sdk` is lighter, simpler, and sufficient for `conversations.history` + `files.info` + `chat.postMessage` calls.  
**Alternatives considered**: `slack_bolt` (overkill for polling), raw HTTP with `requests` (reinvents auth/retry handling already in `slack_sdk`)

## Decision 2: Scheduler Approach

**Decision**: Python `schedule` library running in a long-lived process  
**Rationale**: Simple, zero-dependency approach that works on any OS without system cron setup. Keeps the project self-contained — one `python main.py` command starts everything. Interval is configurable via env var.  
**Alternatives considered**:
- System cron: Requires OS-level setup, harder to run in containers or on cloud VMs without root; interval changes need crontab edits
- APScheduler: More powerful but adds complexity not needed at this scale
- `asyncio` + `asyncio.sleep`: Adds async complexity for no benefit in an I/O-light polling loop

## Decision 3: State Persistence (Deduplication)

**Decision**: JSON file (`processed.json`) storing a set of processed Slack file IDs  
**Rationale**: The volume of processed records is small (one entry per image, expected dozens to low hundreds). A JSON file requires zero infrastructure, is human-readable for debugging, and survives process restarts. File is read at startup and written after each successful analysis.  
**Alternatives considered**:
- SQLite: More robust but unnecessary overhead for a flat set of string IDs
- In-memory only: Loses state on restart, causing re-analysis of all historical images
- Redis: Requires external service, far too heavy for this use case

## Decision 4: Image Download from Slack

**Decision**: Download image bytes using `requests` with `Authorization: Bearer <SLACK_BOT_TOKEN>` header, then pass as base64 to Claude  
**Rationale**: Slack file URLs require authentication — direct unauthenticated access returns 401. The `slack_sdk` `files_info` method returns a `url_private_download` field which must be fetched with the bot token. Images are base64-encoded and passed to Claude's vision API as `image` content blocks.  
**Alternatives considered**: Passing URL directly to Claude (fails — Slack URLs are auth-gated and Claude cannot authenticate against them)

## Decision 5: Claude Integration Method

**Decision**: Shell out to the `claude` CLI via Python subprocess (`claude -p "<prompt>" --image <path>`)  
**Rationale**: Uses the user's existing Claude Code Pro monthly subscription — no separate Anthropic API key or API billing required. The `claude` CLI's `-p` (print/non-interactive) flag outputs the response to stdout and exits, making it straightforward to capture from a subprocess call.  
**Alternatives considered**: `anthropic` Python SDK (requires separate API key and pay-per-token billing), direct HTTP to Anthropic API (same billing issue)

## Decision 6: Analysis Output Target

**Decision**: Post analysis as a **thread reply** under the original image message (`thread_ts = original_message_ts`)  
**Rationale**: Confirmed via clarification Q3 — thread replies keep the channel uncluttered and preserve image ↔ analysis pairing. Requires capturing each image's parent message `ts` when listing channel history (`conversations.history` already returns this alongside `files`), then passing it as `thread_ts` to `chat.postMessage`.  
**Alternatives considered**: New top-level channel messages (rejected — clutters channel), different channel (rejected — splits context), DM (rejected — user wants shared visibility)

## Decision 8: Output Format and Length

**Decision**: Fixed three-section structured response — **Key Positions**, **Observations**, **Actionable Insights** — targeting ≤ 1,500 characters, hard capped at 3,900 (Slack buffer under its 4,000-char limit)  
**Rationale**: Confirmed via clarification Q2. Readable and scannable in Slack; fits in a single message; predictable enough to write tests against. The system prompt (`prompts/analyst.txt`) explicitly demands this structure.  
**Alternatives considered**: Free-form long analysis (rejected — Slack message splitting complexity), bullet-only (rejected — loses narrative context), two-part headline+thread (rejected — redundant with the thread-reply delivery already chosen)

## Decision 9: First-Run Historical Images

**Decision**: Record `first_run_at` on the very first run (when no state file exists); permanently ignore images whose `posted_at < first_run_at`  
**Rationale**: Confirmed via clarification Q1. Prevents a flood of analyses when the bot is deployed to an established channel. `first_run_at` is written atomically before any Slack read so there is no race window.  
**Alternatives considered**: Process all historical (rejected — spammy), mark existing as processed (rejected — wastes state), last-N only (rejected — arbitrary cutoff)

## Decision 10: Claude CLI Failure Handling

**Decision**: On non-zero exit, timeout (>120s), or crash — log the failure, skip the image for this cycle, do NOT mark it as processed; retry naturally on the next scheduler tick  
**Rationale**: Confirmed via clarification Q5. Self-healing, no retry storms, no sleep loops. The scheduler's fixed interval is the retry backoff.  
**Alternatives considered**: In-run retries with backoff (rejected — added complexity for marginal gain when next tick is 15min away), failure-notice posts (rejected — creates noise on transient issues), hard exit (rejected — defeats "runs 7 days without restart")

## Decision 11: Default System Prompt

**Decision**: Ship `prompts/analyst.txt` with the user-supplied risk-analyst prompt (radical transparency, correlation / sector / geographic / interest-rate / stress-test / liquidity / tail-risk / hedging / rebalancing), adapted to emit the three-section output format  
**Rationale**: Confirmed via clarification Q4. Gives the bot a high-quality default out of the box; still user-replaceable via `SYSTEM_PROMPT_FILE` env var.  
**Alternatives considered**: Generic analyst (weaker default), empty placeholder (requires setup step), multiple selectable prompts (deferred to a future enhancement)

## Decision 7: Project Structure

**Decision**: Single flat Python project at repo root with a `src/` package  
**Rationale**: The project is a single-purpose automation script, not a library or web service. A simple structure with `main.py` as entry point and `src/` for modules (slack_client, analyzer, scheduler, state) is appropriate. No monorepo needed.

## Resolved Unknowns from Technical Context

| Unknown | Resolution |
|---------|-----------|
| Slack SDK | `slack_sdk` v3.x |
| Scheduler | `schedule` library |
| State storage | JSON file |
| Image transfer to Claude | Base64-encoded bytes via Anthropic SDK |
| Claude integration | `claude` CLI via subprocess (`-p` flag) |
| Python version | 3.11+ |
| Testing | `pytest` with mocked Slack/Anthropic clients |
