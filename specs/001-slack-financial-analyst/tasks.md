---
description: "Task list for Slack Financial Analyst implementation"
---

# Tasks: Slack Financial Analyst

**Input**: Design documents from `/specs/001-slack-financial-analyst/`
**Prerequisites**: [plan.md](../plan.md), [spec.md](../spec.md), [research.md](../research.md), [data-model.md](../data-model.md), [contracts/cli-contract.md](../contracts/cli-contract.md), [quickstart.md](../quickstart.md)

**Tests**: Included — `plan.md` specifies a `tests/` package with per-module `pytest` coverage using `unittest.mock` for Slack and subprocess.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. MVP = Phase 1 + Phase 2 + Phase 3 (US1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are relative to repo root `/code/slack-financial-analyst/`

## Path Conventions

Single flat Python project:
- Source: `src/`
- Entry point: `main.py`
- Tests: `tests/`
- Prompts: `prompts/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton, dependencies, and static assets.

- [x] T001 Create top-level directory layout: `src/`, `tests/`, `prompts/` with empty `__init__.py` in `src/` and `tests/`
- [x] T002 [P] Create [requirements.txt](../../../requirements.txt) with pinned deps: `slack_sdk>=3.27`, `schedule>=1.2`, `python-dotenv>=1.0`, `requests>=2.31`, `pytest>=7.4`
- [x] T003 [P] Create [.gitignore](../../../.gitignore) excluding `.env`, `processed.json`, `__pycache__/`, `.venv/`, `*.pyc`, `.pytest_cache/`
- [x] T004 [P] Create [.env.example](../../../.env.example) with commented placeholders for `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `SCHEDULE_INTERVAL_MINUTES`, `STATE_FILE_PATH`, `SYSTEM_PROMPT_FILE`
- [x] T005 [P] Ship [prompts/analyst.txt](../../../prompts/analyst.txt) with the senior risk-analyst prompt adapted to emit the Key Positions / Observations / Actionable Insights structure (≤1,500 char target) per spec Clarification Q4
- [x] T006 Create and activate Python 3.11+ venv (`.venv/`) and install from `requirements.txt`

**Checkpoint**: Dev environment is bootstrapped; imports resolve.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared primitives that every user story depends on — configuration, state persistence, logging, CLI scaffold.

**⚠️ CRITICAL**: No user story work can begin until this phase completes.

- [x] T007 [P] Implement `ScheduleConfig` dataclass in [src/config.py](../../../src/config.py) — loads env vars via `python-dotenv`, validates `SLACK_BOT_TOKEN`/`SLACK_CHANNEL_ID` are non-empty, validates `SCHEDULE_INTERVAL_MINUTES` is a positive int, raises `ConfigError` on failure
- [x] T008 [P] Configure structured logging in [src/logging_setup.py](../../../src/logging_setup.py) — format `[YYYY-MM-DD HH:MM:SS] [LEVEL] message`; INFO→stdout, ERROR→stderr; idempotent `setup_logging()` callable
- [x] T009 Implement `ProcessedRecord` in [src/state.py](../../../src/state.py) — `load(path)` returns existing state or initializes `{first_run_at: time.time(), processed_file_ids: [], last_run_at: None}` and persists immediately; `add_processed(file_id)`; `is_processed(file_id)`; `save(path)` via atomic `tempfile` + `os.replace`; `first_run_at` property is set-once (never mutated after initial write)
- [x] T010 Scaffold [main.py](../../../main.py) — `argparse` for `--run-once`/`--dry-run`/`--help`; loads `ScheduleConfig`; installs SIGINT/SIGTERM handlers that break the scheduler loop and flush state; exit codes `0`/`1` (config error)/`2` (runtime error) per [cli-contract.md](../contracts/cli-contract.md)
- [x] T011 [P] Write [tests/test_config.py](../../../tests/test_config.py) — covers: missing `SLACK_BOT_TOKEN` raises `ConfigError`, missing `SLACK_CHANNEL_ID` raises `ConfigError`, non-integer interval raises `ConfigError`, happy-path load from `os.environ`
- [x] T012 [P] Write [tests/test_state.py](../../../tests/test_state.py) — covers: fresh init writes `first_run_at` immediately; round-trip load→modify→save; `first_run_at` is never overwritten on subsequent saves; `add_processed` is idempotent (set semantics); atomic write leaves no partial file on simulated interrupt

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Receive Automated Portfolio Analysis (Priority: P1) 🎯 MVP

**Goal**: End-to-end pipeline — when an image is posted in the monitored channel, the scheduler retrieves it, sends it to Claude via the `claude` CLI, and posts the analysis as a thread reply under the original message.

**Independent Test**: Post one image in the target Slack channel, run `python main.py --run-once`, and verify a thread reply appears on that message containing the three-section analysis (Key Positions / Observations / Actionable Insights).

### Implementation for User Story 1

- [x] T013 [US1] Define `ChannelImage` dataclass and implement `SlackClient.list_channel_messages_with_images(channel_id, oldest=None)` in [src/slack_client.py](../../../src/slack_client.py) — calls `conversations_history`; for each message containing `files`, yields `ChannelImage(file_id, url=url_private_download, mimetype, message_ts=message.ts, posted_at=float(message.ts), channel_id)` (see [data-model.md](../data-model.md) §ChannelImage)
- [x] T014 [US1] Implement `SlackClient.download_image(image: ChannelImage) -> Path` in [src/slack_client.py](../../../src/slack_client.py) — HTTP GET on `url_private_download` with `Authorization: Bearer <SLACK_BOT_TOKEN>`; writes to `tempfile.NamedTemporaryFile(suffix=<ext from mimetype>, delete=False)`; returns path
- [x] T015 [US1] Implement `SlackClient.post_thread_reply(channel_id, thread_ts, text)` in [src/slack_client.py](../../../src/slack_client.py) — calls `chat_postMessage(channel=..., thread_ts=..., text=...)`; treats `not_in_thread`/`channel_not_found` as warnings (logged, not raised)
- [x] T016 [P] [US1] Implement `ClaudeAnalyzer.analyze(image_path, system_prompt_path) -> tuple[bool, Optional[str]]` in [src/analyzer.py](../../../src/analyzer.py) — reads prompt file; runs `subprocess.run(["claude", "-p", prompt_text, "--image", str(image_path)], capture_output=True, text=True, timeout=120)`; returns `(True, stdout)` on `returncode == 0`; returns `(False, None)` on non-zero, `TimeoutExpired`, or `FileNotFoundError`; on success, if `len(stdout) > 3900` truncate with trailing `…` and log a warning
- [x] T017 [US1] Implement `run_once(config, state, slack, analyzer, dry_run=False)` in [src/scheduler.py](../../../src/scheduler.py) — fetches images via `slack.list_channel_messages_with_images(config.slack_channel_id)`; for each image: download to temp path → `analyzer.analyze` → if success and not `dry_run`, `slack.post_thread_reply(channel, message_ts, text)` → cleanup temp file in `finally`; logs `found=N analyzed=N skipped=N` counts per tick (FR-008)
- [x] T018 [US1] Wire `run_once` into [main.py](../../../main.py) — construct `SlackClient(config.slack_bot_token)`, `ClaudeAnalyzer(config.system_prompt_file)`, `ProcessedRecord.load(config.state_file_path)`; if `--run-once`, call `run_once(...)` and exit; otherwise start `schedule.every(config.interval_minutes).minutes.do(run_once, ...)` loop with `schedule.run_pending()` + `time.sleep(1)`, breaking on signal
- [x] T019 [P] [US1] Write [tests/test_slack_client.py](../../../tests/test_slack_client.py) — mocks `slack_sdk.WebClient`; covers: `list_channel_messages_with_images` filters to file-bearing messages and carries `message_ts`/`posted_at`; `download_image` sends `Authorization: Bearer <token>` header (assert via `requests` mock); `post_thread_reply` calls `chat_postMessage` with `thread_ts` equal to the source message `ts`
- [x] T020 [P] [US1] Write [tests/test_analyzer.py](../../../tests/test_analyzer.py) — mocks `subprocess.run`; covers: `returncode=0` returns `(True, stdout)`; `returncode=1` returns `(False, None)`; `TimeoutExpired` returns `(False, None)`; 5,000-char stdout truncated to ≤3,900 with warning logged
- [x] T021 [US1] Write [tests/test_scheduler.py](../../../tests/test_scheduler.py) `test_happy_path` — with all I/O mocked, one inbound `ChannelImage` flows: downloaded → analyzed successfully → `post_thread_reply` invoked with the original `message_ts` → `state.add_processed(file_id)` called → temp file unlinked

**Checkpoint**: MVP complete. User Story 1 is independently testable end-to-end against a real Slack workspace.

---

## Phase 4: User Story 2 — Track Only New Images (Priority: P2)

**Goal**: Deduplication and first-run gating so the scheduler never re-analyzes the same image, and never floods the channel with commentary on images that existed before the bot was deployed.

**Independent Test**: Run `python main.py --run-once` twice in a row with the same image posted; verify exactly one analysis is produced. Then post to a channel with existing historical images, run fresh, and verify only images posted *after* `first_run_at` are analyzed.

### Implementation for User Story 2

- [x] T022 [US2] Extend `run_once` in [src/scheduler.py](../../../src/scheduler.py) — before downloading, skip any `ChannelImage` where `state.is_processed(file_id)`; only call `state.add_processed(file_id)` + `state.save(...)` **after** `post_thread_reply` succeeds (enforces the data-model invariant)
- [x] T023 [US2] Extend `run_once` in [src/scheduler.py](../../../src/scheduler.py) to enforce first-run gating — pass `oldest=state.first_run_at` to `SlackClient.list_channel_messages_with_images` so Slack history excludes pre-deployment messages server-side; also defensively skip any image where `posted_at < state.first_run_at`
- [x] T024 [US2] Harden Claude CLI failure path in [src/scheduler.py](../../../src/scheduler.py) — when `analyzer.analyze` returns `(False, _)`, log the failure with file_id and do **not** call `state.add_processed`; continue processing remaining images; the next scheduler tick naturally retries (per Clarification Q5 / FR-010)
- [x] T025 [P] [US2] Add `test_dedup_across_runs` to [tests/test_scheduler.py](../../../tests/test_scheduler.py) — same `ChannelImage` served on two consecutive `run_once` calls; `post_thread_reply` invoked exactly once
- [x] T026 [P] [US2] Add `test_first_run_ignores_historical` to [tests/test_scheduler.py](../../../tests/test_scheduler.py) — freshly created state with `first_run_at = T`; images with `posted_at < T` never downloaded or analyzed
- [x] T027 [P] [US2] Add `test_claude_failure_retries_next_tick` to [tests/test_scheduler.py](../../../tests/test_scheduler.py) — first tick: analyzer returns `(False, None)`, file_id NOT in `processed_file_ids`, no post made; second tick with analyzer returning `(True, text)`: file_id now marked and post made

**Checkpoint**: User Story 2 complete. Deduplication + first-run gating verified.

---

## Phase 5: User Story 3 — Handle Non-Image and Unsupported Content Gracefully (Priority: P3)

**Goal**: Real Slack channels contain mixed content — text messages, PDFs, unsupported file types, deleted messages, API errors. The scheduler must skip these cleanly and never crash the loop.

**Independent Test**: In the target channel, post a text-only message and a non-image file (e.g., PDF). Run `python main.py --run-once`. Verify neither produces an analysis, no error is posted to the channel, and the scheduler exits cleanly with exit code 0.

### Implementation for User Story 3

- [x] T028 [US3] Tighten MIME filter in `SlackClient.list_channel_messages_with_images` in [src/slack_client.py](../../../src/slack_client.py) — skip messages with no `files` key; only yield files whose `mimetype` is in `{image/jpeg, image/png, image/gif, image/webp}` (per [data-model.md](../data-model.md) validation rules)
- [x] T029 [US3] Wrap per-image processing in [src/scheduler.py](../../../src/scheduler.py) with try/except for `SlackApiError` and `requests.RequestException` — log, skip the image for this cycle, do not crash the loop or mark processed
- [x] T030 [P] [US3] Add `test_skips_text_only_and_non_image_files` to [tests/test_slack_client.py](../../../tests/test_slack_client.py) — mocked `conversations_history` returning (a) a text-only message, (b) a message with a PDF attachment, (c) a message with a PNG; only the PNG is yielded
- [x] T031 [P] [US3] Add `test_slack_api_error_does_not_crash_loop` to [tests/test_scheduler.py](../../../tests/test_scheduler.py) — `list_channel_messages_with_images` raises `SlackApiError`; `run_once` logs and returns without raising

**Checkpoint**: All user stories complete. Channel robustness verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and minor improvements spanning multiple stories.

- [x] T032 [P] Run end-to-end smoke test per [quickstart.md](../quickstart.md) — fresh clone, `pip install`, `cp .env.example .env`, fill real values, `python main.py --run-once --dry-run` against a live channel; verify logs show the expected `found/analyzed/skipped` counts
- [x] T033 [P] Verify per-tick log line format meets FR-008 — each `run_once` emits a single summary line `[timestamp] [INFO] cycle complete: found=N analyzed=N skipped=N failed=N`
- [x] T034 Deploy and confirm 7-day stability (SC-005) — run under `systemd`/`launchd`/`tmux`, confirm process survives at least one full day of scheduled ticks without memory growth or crash

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup; **BLOCKS all user stories**
- **User Story 1 (Phase 3)**: Depends on Foundational; independent of US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational + US1 (extends `run_once` and `SlackClient`)
- **User Story 3 (Phase 5)**: Depends on Foundational + US1; independent of US2
- **Polish (Phase 6)**: Depends on all desired user stories

### User Story Dependencies

- **US1 (P1)** — the MVP flow. No dependencies on other stories. Produces a working pipeline (but without dedup it would spam the channel on repeated runs — acceptable for isolated US1 test).
- **US2 (P2)** — extends US1's `run_once` with `state.is_processed` filter and `first_run_at` gating. Completes the production-ready behavior.
- **US3 (P3)** — hardens US1's `SlackClient` and `run_once` against mixed channel content and API errors. Independent of US2.

### Within Each Phase

- Models/data primitives (dataclasses) before services
- `slack_client.py` methods before `scheduler.run_once` (scheduler orchestrates the client)
- `analyzer.py` in parallel with `slack_client.py` (different files)
- Tests for a module in parallel with other test files once the module exists

### Parallel Opportunities

- **Phase 1**: T002, T003, T004, T005 — all `[P]`, all different files, run concurrently
- **Phase 2**: T007 (`config.py`), T008 (`logging_setup.py`), T011 (`test_config.py`), T012 (`test_state.py`) — all `[P]` after T009 completes for the test pair
- **Phase 3**: T016 (`analyzer.py`) runs in parallel with T013–T015 (`slack_client.py`). T019 and T020 run in parallel once their respective modules exist
- **Phase 4**: T025, T026, T027 — three test additions to the same file [tests/test_scheduler.py](../../../tests/test_scheduler.py), marked `[P]` because they target distinct test functions and can be authored independently, though they ultimately commit to the same file
- **Phase 5**: T030 and T031 — different test files, genuinely `[P]`

---

## Parallel Example: User Story 1

```bash
# After T013–T015 (SlackClient) and T016 (ClaudeAnalyzer) are done,
# launch test authoring in parallel:
Task: "Write tests/test_slack_client.py covering list/download/post with mocks"
Task: "Write tests/test_analyzer.py covering subprocess success/failure/timeout"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) → dev environment ready
2. Complete Phase 2 (Foundational) → config, state, logging, CLI scaffold ready
3. Complete Phase 3 (US1) → working end-to-end pipeline
4. **STOP and VALIDATE**: post one image to the target channel, run `python main.py --run-once`, verify the thread reply appears with the three-section analysis
5. Ship MVP

### Incremental Delivery

1. MVP (Phases 1–3) → first working end-to-end demo
2. Add Phase 4 (US2) → safe for production (no dedup spam, no historical flood)
3. Add Phase 5 (US3) → robust against mixed channel content
4. Phase 6 polish → 7-day stability validation

### Solo-Developer Path (default)

Sequential execution in task ID order. Parallel opportunities above are informational — still useful for identifying which changes are unrelated and safe to split into separate commits.

---

## Notes

- `[P]` = different files, no dependencies on incomplete tasks
- `[Story]` label maps each task to US1/US2/US3 for traceability against [spec.md](../spec.md) user stories
- Every user story is independently completable and testable per its Independent Test criterion
- Commit after each task or logical group to align with the git extension auto-commit hooks
- The `claude` CLI (Pro subscription) is a runtime dependency — no Anthropic API key is required at any stage (per Clarification and [research.md](../research.md) Decision 5)
