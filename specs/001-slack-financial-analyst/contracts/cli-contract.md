# CLI Contract: Slack Financial Analyst

**Date**: 2026-04-16

## Entry Point

```
python main.py [OPTIONS]
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--run-once` | Run a single poll cycle and exit (instead of looping on schedule) | disabled |
| `--dry-run` | Fetch and analyze images but do not post to Slack | disabled |
| `--help` | Show usage information | — |

## Environment Variables (required at runtime)

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Slack bot OAuth token (`xoxb-...`) |
| `SLACK_CHANNEL_ID` | Yes | Target channel ID (e.g., `C01234ABC`) |
| `SCHEDULE_INTERVAL_MINUTES` | No | Polling interval (default: `15`) |
| `STATE_FILE_PATH` | No | Path to processed-records file (default: `processed.json`) |
| `SYSTEM_PROMPT_FILE` | No | Path to analyst system prompt (default: `prompts/analyst.txt`) |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success (clean exit or `--run-once` completed) |
| `1` | Configuration error (missing required env var) |
| `2` | Unrecoverable runtime error (Slack/API auth failure) |

## Stdout / Stderr

- Structured log lines written to **stdout** in format: `[YYYY-MM-DD HH:MM:SS] [LEVEL] message`
- Errors written to **stderr**
- No interactive prompts

## Example Usage

```bash
# Start the scheduler (runs every 15 minutes indefinitely)
SLACK_BOT_TOKEN=xoxb-... SLACK_CHANNEL_ID=C01234 python main.py

# One-off run for testing
python main.py --run-once

# Dry run (no Slack posts)
python main.py --run-once --dry-run
```

## Runtime Dependencies

The `claude` CLI must be installed and authenticated on the host machine:

```bash
claude auth login
```

The bot invokes Claude as:

```bash
claude -p "<system+user prompt>" --image /tmp/<image-file>
```

A non-zero exit or timeout (>120s) is treated as a transient failure — the image is **not** marked processed and will be retried on the next scheduler cycle. (No Anthropic API key is required; usage is billed via your Claude Pro subscription.)

## Posting Behavior

Analysis is posted as a **Slack thread reply** under the original image message (`thread_ts = original_message_ts`), not as a new top-level channel message. Output is a structured markdown message with three fixed sections:

- `*Key Positions*`
- `*Observations*`
- `*Actionable Insights*`

Target length ≤ 1,500 characters. Hard cap at 3,900 characters (Slack's 4,000-char message limit with buffer). Over-long responses are truncated with an ellipsis and a warning log line.

## First-Run Behavior

On the **very first run** (when `processed.json` does not exist), the bot records the current Slack-format timestamp as `first_run_at` and **ignores all images posted before that moment**. Only images posted after the first run are ever analyzed. This prevents a flood of analyses when the bot is first deployed to an established channel.
