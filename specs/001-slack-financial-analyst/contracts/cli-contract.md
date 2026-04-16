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
