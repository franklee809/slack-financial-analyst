# Slack Financial Analyst

## Project Overview

An automated financial analyst tool that:
1. **Fetches images/screenshots** from a designated Slack channel
2. **Analyzes them with Claude** (vision) acting as a financial analyst
3. **Runs on a schedule** — automatically processes new images at set intervals

## Use Case

The user shares portfolio screenshots and other financial charts/data into a Slack channel. Claude retrieves those images and provides financial analysis commentary — covering portfolio positions, market observations, and actionable insights.

## Key Components to Build

- **Slack integration** — bot that reads images from a specific channel using Slack API (`channels:history`, `files:read` scopes)
- **Claude vision analysis** — sends each image to Claude with a financial analyst system prompt
- **Scheduler** — runs on a cron/interval to pick up new images automatically
- **Output** — analysis results posted back to Slack or saved to a file

## Tech Stack

- Language: **Python**
- AI: **Claude API** (Anthropic) with vision capability
- Slack: **Slack Bolt SDK** or plain `slack_sdk`
- Scheduler: cron or Python `schedule` library

## Required Credentials (not committed to repo)

- `SLACK_BOT_TOKEN` — Slack bot OAuth token
- `SLACK_CHANNEL_ID` — target channel to monitor
- `ANTHROPIC_API_KEY` — for Claude API calls

## Spec-Kit Workflow

This project uses [spec-kit](https://github.com/github/spec-kit) for spec-driven development.
Run skills in order:
1. `/speckit-constitution`
2. `/speckit-specify`
3. `/speckit-plan`
4. `/speckit-tasks`
5. `/speckit-implement`

## Active Technologies
- Python 3.11+ + `slack_sdk` (Slack API), `anthropic` (Claude vision), `schedule` (polling loop), `python-dotenv` (env config), `requests` (authenticated image download) (001-slack-financial-analyst)
- Local JSON file (`processed.json`) for deduplication state (001-slack-financial-analyst)

## Recent Changes
- 001-slack-financial-analyst: Added Python 3.11+ + `slack_sdk` (Slack API), `anthropic` (Claude vision), `schedule` (polling loop), `python-dotenv` (env config), `requests` (authenticated image download)
