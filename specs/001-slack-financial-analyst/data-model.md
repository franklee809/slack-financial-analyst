# Data Model: Slack Financial Analyst

**Branch**: `001-slack-financial-analyst` | **Date**: 2026-04-16

## Entities

### ChannelImage

Represents an image file attachment retrieved from the Slack channel.

| Field | Type | Description |
|-------|------|-------------|
| `file_id` | `str` | Slack file ID (e.g., `F01234ABC`) — primary identifier |
| `url` | `str` | Authenticated download URL (`url_private_download`) |
| `mimetype` | `str` | MIME type (e.g., `image/jpeg`, `image/png`) |
| `message_ts` | `str` | Slack message `ts` of the parent message containing this file — used as `thread_ts` when posting the analysis reply |
| `posted_at` | `float` | Slack message timestamp (Unix epoch, float) when the image was posted — used for the first-run filter |
| `channel_id` | `str` | Slack channel ID where the image was found |

**Validation rules**:
- `mimetype` must be one of: `image/jpeg`, `image/png`, `image/gif`, `image/webp`
- `file_id` must be non-empty string
- `url` must be a valid HTTPS URL
- `message_ts` must be non-empty (required to post thread reply)
- `posted_at` must be ≥ `ProcessedRecord.first_run_at` for the image to be eligible for analysis

---

### AnalysisResult

Represents the AI-generated financial commentary for a single image.

| Field | Type | Description |
|-------|------|-------------|
| `file_id` | `str` | Reference to the source `ChannelImage.file_id` |
| `thread_ts` | `str` | `ts` of the original image message — used as the thread root for the analysis reply |
| `analysis_text` | `str` | Structured commentary (Key Positions / Observations / Actionable Insights, ≤ 1,500 chars target) |
| `analyzed_at` | `str` | ISO 8601 timestamp of when analysis was produced |
| `source` | `str` | Fixed value `"claude-cli"` — indicates analysis came from the `claude` CLI subprocess |

**Validation rules**:
- `analysis_text` SHOULD contain the three section headings (Key Positions, Observations, Actionable Insights); analyzer logs a warning if missing
- `analysis_text` length should not exceed 3,900 characters (Slack message hard limit is 4,000; leave buffer)

---

### ProcessedRecord

Persisted state tracking which images have already been analyzed. Stored as a JSON file on disk.

**Schema** (`processed.json`):
```json
{
  "first_run_at": 1713260400.0,
  "processed_file_ids": ["F01234ABC", "F05678DEF"],
  "last_run_at": "2026-04-16T10:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `first_run_at` | `float` | Slack-format `ts` (Unix epoch, float seconds) recorded on the very first scheduler run. Images with `posted_at < first_run_at` are permanently ignored. **Set once and never modified.** |
| `processed_file_ids` | `list[str]` | Set of Slack file IDs that have been successfully analyzed and posted |
| `last_run_at` | `str` | ISO 8601 timestamp of the last successful scheduler run |

**Validation rules**:
- File IDs in `processed_file_ids` are unique (treated as a set)
- On missing/corrupt file: initialize `first_run_at = current_time()`, empty `processed_file_ids`, and persist immediately before any Slack call
- Writes are atomic: write to `processed.json.tmp` then `os.replace(tmp, final)` to survive crashes

---

### ScheduleConfig

Runtime configuration loaded from environment variables.

| Field | Env Var | Type | Default | Description |
|-------|---------|------|---------|-------------|
| `slack_bot_token` | `SLACK_BOT_TOKEN` | `str` | required | Slack bot OAuth token |
| `slack_channel_id` | `SLACK_CHANNEL_ID` | `str` | required | Target channel to monitor |
| `interval_minutes` | `SCHEDULE_INTERVAL_MINUTES` | `int` | `15` | Polling interval in minutes |
| `state_file_path` | `STATE_FILE_PATH` | `str` | `processed.json` | Path to deduplication state file |
| `system_prompt_file` | `SYSTEM_PROMPT_FILE` | `str` | `prompts/analyst.txt` | Path to financial analyst system prompt |

**Validation rules**:
- `slack_bot_token`, `slack_channel_id` must be non-empty; raise `ConfigError` if missing
- `interval_minutes` must be a positive integer

## State Transitions

```
ChannelImage lifecycle (per scheduler tick):
  DISCOVERED
    │
    ├── (posted_at < first_run_at)      → IGNORED (pre-first-run historical)
    ├── (file_id in processed_file_ids) → IGNORED (already analyzed)
    ├── (mimetype not image/*)          → IGNORED (non-image attachment)
    │
    └── eligible
          │
          ├── (claude CLI returncode == 0)              → ANALYZED → post thread reply → add to processed_file_ids
          └── (claude CLI non-zero / timeout / crash)   → RETRY_PENDING (logged, NOT added to processed_file_ids; retried next tick)
```

**Invariants**:
- An image is added to `processed_file_ids` **only after** a successful Slack thread-reply post. If Slack post fails, the image remains retryable.
- `first_run_at` is set exactly once, on the first run where no state file exists.
