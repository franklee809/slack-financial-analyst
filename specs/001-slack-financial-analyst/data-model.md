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
| `timestamp` | `float` | Slack message timestamp (Unix epoch) when the image was posted |
| `channel_id` | `str` | Slack channel ID where the image was found |

**Validation rules**:
- `mimetype` must be one of: `image/jpeg`, `image/png`, `image/gif`, `image/webp`
- `file_id` must be non-empty string
- `url` must be a valid HTTPS URL

---

### AnalysisResult

Represents the AI-generated financial commentary for a single image.

| Field | Type | Description |
|-------|------|-------------|
| `file_id` | `str` | Reference to the source `ChannelImage.file_id` |
| `analysis_text` | `str` | Full financial analysis commentary from Claude |
| `analyzed_at` | `str` | ISO 8601 timestamp of when analysis was produced |
| `model` | `str` | Model used for analysis (e.g., `claude-sonnet-4-6`) |

---

### ProcessedRecord

Persisted state tracking which images have already been analyzed. Stored as a JSON file on disk.

**Schema** (`processed.json`):
```json
{
  "processed_file_ids": ["F01234ABC", "F05678DEF"],
  "last_run_at": "2026-04-16T10:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `processed_file_ids` | `list[str]` | Set of Slack file IDs that have been analyzed |
| `last_run_at` | `str` | ISO 8601 timestamp of the last successful scheduler run |

**Validation rules**:
- File IDs in `processed_file_ids` are unique (treated as a set)
- On missing/corrupt file: initialize with empty state

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
ChannelImage lifecycle:
  DISCOVERED → (mimetype valid?) → QUEUED → (Claude success?) → ANALYZED
                                          ↘ (Claude error)   → SKIPPED (logged, not persisted as processed)
```

Images that fail analysis are **not** added to `processed_file_ids` so they will be retried on the next run.
