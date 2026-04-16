# Implementation Plan: Slack Financial Analyst

**Branch**: `001-slack-financial-analyst` | **Date**: 2026-04-16 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-slack-financial-analyst/spec.md`

## Summary

Build a Python automation that polls a designated Slack channel on a configurable schedule, downloads any new image attachments, sends each image to Claude's vision API with a financial analyst prompt, and posts the resulting analysis back to Slack. Deduplication state is persisted in a local JSON file to prevent re-analysis across runs.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `slack_sdk` (Slack API), `schedule` (polling loop), `python-dotenv` (env config), `requests` (authenticated image download)  
**External Tools**: `claude` CLI (must be installed and authenticated via `claude auth login`) — used via subprocess for image analysis  
**Storage**: Local JSON file (`processed.json`) for deduplication state  
**Testing**: `pytest` with `unittest.mock` for Slack/Anthropic client mocking  
**Target Platform**: Linux/macOS server or developer machine (long-running process)  
**Project Type**: CLI automation / daemon  
**Performance Goals**: Process up to 20 images per run; each image analyzed in under 30 seconds  
**Constraints**: No database required; single-machine deployment; credentials via env vars only  
**Scale/Scope**: Single channel, single user/team; low volume (tens of images per day)

## Constitution Check

Constitution template is not yet configured for this project — no gates apply. Proceeding without violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-slack-financial-analyst/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── cli-contract.md  # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
slack-financial-analyst/
├── main.py                    # Entry point — CLI flags, scheduler loop
├── .env.example               # Credential template (committed)
├── .env                       # Actual credentials (gitignored)
├── requirements.txt           # Python dependencies
├── processed.json             # Runtime state (gitignored)
├── prompts/
│   └── analyst.txt            # Financial analyst system prompt for Claude
└── src/
    ├── __init__.py
    ├── config.py              # Load + validate env vars → ScheduleConfig
    ├── slack_client.py        # Slack API: fetch channel images, post messages
    ├── analyzer.py            # Claude vision: download image, call API, return text
    ├── state.py               # Read/write processed.json deduplication state
    └── scheduler.py           # Schedule loop using `schedule` library

tests/
├── test_config.py             # Config validation tests
├── test_slack_client.py       # Mocked Slack API tests
├── test_analyzer.py           # Mocked Anthropic API tests
└── test_state.py              # State file read/write tests
```

**Structure Decision**: Single flat Python project. No monorepo needed — this is a focused single-purpose daemon. `src/` package separates concerns cleanly while keeping everything in one repo root.

## Complexity Tracking

No constitution violations to justify.
