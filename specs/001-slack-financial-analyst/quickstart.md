# Quickstart: Slack Financial Analyst

## Prerequisites

- Python 3.11+
- A Slack workspace where you can create/configure a bot
- Claude Code CLI installed and authenticated (`claude auth login`) — uses your Pro subscription, no API key needed

## 1. Slack Bot Setup

1. Go to https://api.slack.com/apps → **Create New App** → From scratch
2. Name it (e.g., "Financial Analyst") and select your workspace
3. Under **OAuth & Permissions** → **Bot Token Scopes**, add:
   - `channels:history` (read public channel messages)
   - `groups:history` (read private channel messages, if needed)
   - `files:read` (download image files)
   - `chat:write` (post analysis back to channel)
4. Click **Install to Workspace** and copy the **Bot User OAuth Token** (`xoxb-...`)
5. Invite the bot to your target channel: `/invite @FinancialAnalyst`
6. Copy the channel ID (right-click channel → View channel details → ID at bottom)

## 2. Project Setup

```bash
git clone <repo-url>
cd slack-financial-analyst
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configuration

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL_ID=C01234ABCDE
SCHEDULE_INTERVAL_MINUTES=15
```

Ensure the `claude` CLI is authenticated (one-time setup):
```bash
claude auth login
```

## 4. Customize the Analyst Prompt (optional)

Edit `prompts/analyst.txt` to change how Claude analyzes images. The default prompt instructs Claude to act as a senior financial analyst covering portfolio positions, market observations, and actionable insights.

## 5. Run

```bash
# Start the scheduler (runs indefinitely)
python main.py

# Test with a single run (no looping)
python main.py --run-once

# Test without posting to Slack
python main.py --run-once --dry-run
```

## 6. Verify

Post an image into your Slack channel. Within one scheduler interval, you should see a financial analysis message appear in the channel.

Check logs for activity:
```
[2026-04-16 10:00:00] [INFO] Scheduler started. Interval: 15 minutes.
[2026-04-16 10:00:01] [INFO] Found 2 new image(s) in channel C01234ABCDE
[2026-04-16 10:00:05] [INFO] Analyzed F01234ABC → posted to Slack
[2026-04-16 10:00:09] [INFO] Analyzed F05678DEF → posted to Slack
[2026-04-16 10:15:00] [INFO] Found 0 new image(s). Nothing to process.
```
