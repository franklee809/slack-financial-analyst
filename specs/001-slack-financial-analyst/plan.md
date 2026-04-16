# Implementation Plan: Slack Financial Analyst

**Branch**: `001-slack-financial-analyst` | **Date**: 2026-04-16 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-slack-financial-analyst/spec.md`

**Refresh note**: This plan was regenerated after the clarification session on 2026-04-16 that resolved 5 open questions (see `## Clarifications` in [spec.md](spec.md)).

## Summary

Build a Python automation that polls a designated Slack channel on a configurable schedule, downloads image attachments posted **after the bot's first-run timestamp**, sends each image to Claude via the `claude` CLI (using the user's Pro subscription — no Anthropic API key needed) with a risk-analyst system prompt, and posts the resulting **structured analysis (Key Positions / Observations / Actionable Insights, ≤1,500 chars) as a thread reply** under the original image message. Deduplication and first-run state are persisted in a local JSON file. On Claude CLI failure, the image is not marked processed and is retried automatically on the next cycle.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `slack_sdk` (Slack API), `schedule` (polling loop), `python-dotenv` (env config), `requests` (authenticated image download)  
**External Tools**: `claude` CLI (must be installed and authenticated via `claude auth login`) — used via `subprocess.run(["claude", "-p", prompt, "--image", path], ...)` for image analysis. No Anthropic API key required.  
**Storage**: Local JSON file (`processed.json`) holding `first_run_at` timestamp, `processed_file_ids` set, and `last_run_at` timestamp  
**Testing**: `pytest` with `unittest.mock` for Slack client and `subprocess.run` calls  
**Target Platform**: Linux/macOS with `claude` CLI installed; long-running process (systemd / launchd / tmux)  
**Project Type**: CLI automation / daemon  
**Performance Goals**: Process up to 20 images per scheduled run; each image analyzed in under 30 seconds (subprocess + CLI inference)  
**Constraints**: No database; single-machine deployment; bot credentials via env vars; no hard-coded secrets; subprocess stdin/stdout for Claude I/O  
**Scale/Scope**: Single channel, single user/team; low volume (tens of images per day)

## Constitution Check

Constitution template is not yet configured for this project — no gates apply. Proceeding without violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-slack-financial-analyst/
├── plan.md              # This file (refreshed 2026-04-16)
├── research.md          # Phase 0 — decisions incl. claude-CLI integration
├── data-model.md        # Phase 1 — entities incl. first_run_at state
├── quickstart.md        # Phase 1 — setup guide (claude auth login)
├── contracts/
│   └── cli-contract.md  # Phase 1 — entry point, env vars, exit codes
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
slack-financial-analyst/
├── main.py                    # Entry point — CLI flags, scheduler loop, signal handling
├── .env.example               # Credential template (committed)
├── .env                       # Actual credentials (gitignored)
├── .gitignore                 # Excludes .env, processed.json, __pycache__, .venv
├── requirements.txt           # Python dependencies (no `anthropic` — uses CLI)
├── processed.json             # Runtime state (gitignored) — first_run_at + processed IDs
├── prompts/
│   └── analyst.txt            # Risk-analyst system prompt (see spec Clarification Q4)
└── src/
    ├── __init__.py
    ├── config.py              # Load + validate env vars → ScheduleConfig
    ├── slack_client.py        # conversations.history, files download, chat.postMessage (with thread_ts)
    ├── analyzer.py            # subprocess → `claude -p <prompt> --image <tempfile>`
    ├── state.py               # Read/write processed.json (first_run_at, processed_file_ids)
    └── scheduler.py           # `schedule` loop + one-shot mode

tests/
├── test_config.py             # Config validation tests (missing env vars, bad interval)
├── test_slack_client.py       # Mocked Slack API tests (list, download, thread reply)
├── test_analyzer.py           # Mocked subprocess tests (success, non-zero exit, timeout)
├── test_state.py              # State file read/write tests (init, persist, round-trip)
└── test_scheduler.py          # First-run gating + dedup integration test
```

**Structure Decision**: Single flat Python project. `src/` package separates concerns (Slack I/O, analysis subprocess, state, scheduling). Entry point `main.py` stays thin — parses CLI flags, instantiates `ScheduleConfig`, and kicks off the scheduler. Tests mirror the `src/` module layout.

## Key behavior mapped to clarifications

| Clarification | Plan impact |
|---------------|-------------|
| Q1 — First-run handling (ignore historical images) | `state.py` stores `first_run_at` on the very first run; `scheduler.py` filters channel history with `oldest=first_run_at` on every poll |
| Q2 — Structured output, ≤1,500 chars | `prompts/analyst.txt` explicitly requests the three-section format with character-budget guidance; `analyzer.py` truncates/warns if the response exceeds the Slack 3,900-char safety threshold |
| Q3 — Thread-reply delivery | `slack_client.post_message` always passes `thread_ts = original_message_ts`; the original message's `ts` is captured alongside the `file_id` when fetching channel history |
| Q4 — Risk-analyst default prompt | `prompts/analyst.txt` ships with the user-supplied risk-analyst prompt, adapted to emit the three-section format |
| Q5 — Claude CLI failure handling | `analyzer.py` returns `(success: bool, text: Optional[str])`; only on `success=True` does `state.py` add the file_id to `processed_file_ids`. No in-run retries; next scheduler tick naturally retries |

## Implementation notes

- **Image download**: Slack `url_private_download` requires `Authorization: Bearer $SLACK_BOT_TOKEN`. Download to a temp file (e.g., `tempfile.NamedTemporaryFile(suffix='.png', delete=False)`), pass the path to `claude --image`, delete the temp file in a `finally` block (even on failure).
- **Claude subprocess call**: `subprocess.run(["claude", "-p", prompt_text, "--image", temp_path], capture_output=True, text=True, timeout=120)`. `returncode != 0` or `TimeoutExpired` → failure path.
- **First-run timestamp granularity**: Use Slack's `ts` format (float seconds since epoch). Record `first_run_at` *before* listing history so no race with new messages.
- **Thread reply**: `chat_postMessage(channel=channel_id, thread_ts=original_ts, text=analysis)`. If the bot is not invited to a private thread, Slack returns `not_in_thread` — treat as a non-fatal warning.
- **State file atomicity**: Write to `processed.json.tmp` then `os.replace(tmp, final)` to avoid corruption on crash.
- **Signal handling**: `main.py` installs SIGINT/SIGTERM handlers that break the scheduler loop cleanly and flush state before exit.

## Complexity Tracking

No constitution violations to justify.
