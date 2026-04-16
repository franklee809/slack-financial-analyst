# Research: Slack Financial Analyst

**Branch**: `001-slack-financial-analyst` | **Date**: 2026-04-16

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

**Decision**: Post analysis as a new top-level message in the same Slack channel  
**Rationale**: Matches the assumption in the spec. Thread replies require tracking the original message timestamp per image. Top-level messages are simpler and keep the channel as a running log of analyses. Can be changed to thread replies in a future iteration.  
**Alternatives considered**: Thread reply under original image post (more organised but adds state complexity), writing to a file (loses the Slack integration value)

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
