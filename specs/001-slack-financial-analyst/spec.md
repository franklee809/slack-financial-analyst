# Feature Specification: Slack Financial Analyst

**Feature Branch**: `001-slack-financial-analyst`  
**Created**: 2026-04-16  
**Status**: Draft  
**Input**: User description: "Automated financial analyst tool that fetches images/screenshots from a Slack channel, analyzes them with Claude (vision) acting as a financial analyst, and runs on a schedule."

## Clarifications

### Session 2026-04-16

- Q: First-run behavior for historical images in the channel → A: Record a "started at" timestamp on first run; only process images posted *after* that timestamp.
- Q: Analysis output format/length → A: Structured concise summary with fixed sections (Key Positions, Observations, Actionable Insights); target under 1,500 chars.
- Q: Delivery target for the analysis → A: Thread reply under the original image's message (keeps image ↔ analysis paired, keeps channel uncluttered).
- Q: Analyst system prompt source → A: Use the risk-analyst prompt shared by the user (senior risk analyst, radical transparency, correlation / sector / geographic / interest-rate / stress-test / liquidity / tail-risk / hedging / rebalancing), adapted to the Key Positions / Observations / Actionable Insights structure and ~1,500-char target. Default location: `prompts/analyst.txt`.
- Q: Claude CLI failure handling → A: Log the failure and skip the image for this run; do NOT mark it as processed, so it is retried automatically on the next scheduler cycle.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive Automated Portfolio Analysis (Priority: P1)

A user shares portfolio screenshots or financial charts into a designated Slack channel. At the next scheduled interval, the system automatically retrieves those images and posts back a detailed financial analysis covering portfolio positions, market observations, and actionable insights — all without the user needing to take any additional action.

**Why this priority**: This is the core value proposition of the tool. If this works, the product is useful.

**Independent Test**: Share an image into the designated Slack channel, wait for the next scheduled run, and verify that a financial analysis reply appears in the channel.

**Acceptance Scenarios**:

1. **Given** a portfolio screenshot is posted in the Slack channel, **When** the scheduled interval fires, **Then** the system retrieves the image, analyzes it, and posts a financial commentary reply in the same channel.
2. **Given** multiple images are posted between schedule runs, **When** the scheduler fires, **Then** all unprocessed images are analyzed and each receives a separate analysis reply.
3. **Given** no new images have been posted since the last run, **When** the scheduler fires, **Then** the system skips processing and produces no output.

---

### User Story 2 - Track Only New Images (Priority: P2)

The system keeps track of which images have already been analyzed so that re-running the scheduler does not produce duplicate analysis posts for previously processed content.

**Why this priority**: Without deduplication, every scheduler run would re-analyze all historical images, spamming the channel with duplicate commentary.

**Independent Test**: Post one image, trigger the scheduler twice, and verify that only one analysis is posted.

**Acceptance Scenarios**:

1. **Given** an image has already been analyzed, **When** the scheduler runs again, **Then** the image is not re-analyzed and no duplicate post is created.
2. **Given** the scheduler has run previously and a new image is then posted, **When** the scheduler runs again, **Then** only the new image is analyzed.

---

### User Story 3 - Handle Non-Image and Unsupported Content Gracefully (Priority: P3)

When the Slack channel contains messages without images, or images in unsupported formats, the system skips them cleanly without crashing or posting error noise into the channel.

**Why this priority**: Real channels contain mixed content; robustness is required for reliable operation.

**Independent Test**: Post a text-only message and an unsupported file type to the channel, trigger the scheduler, and verify no error messages appear in the channel.

**Acceptance Scenarios**:

1. **Given** a text-only message exists in the channel, **When** the scheduler processes the channel, **Then** the message is ignored and no analysis is posted.
2. **Given** a file attachment that is not an image is posted, **When** the scheduler processes it, **Then** it is skipped without posting an error to the channel.

---

### Edge Cases

- What happens when Slack API rate limits are hit during image retrieval?
- How does the system handle a very large image that exceeds the vision model's input limits?
- What happens when the Claude CLI is temporarily unavailable or returns a non-zero exit during a scheduled run? (→ Log the failure, leave the image unmarked in state, and retry on the next cycle.)
- How does the system behave if the designated Slack channel is deleted or the bot is removed?
- What happens when an image is posted but deleted from Slack before the scheduler runs?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST monitor a designated Slack channel and retrieve image attachments posted since the last processed timestamp, OR — on first run — only those posted after the bot's start-up timestamp (historical images already in the channel are ignored).
- **FR-002**: System MUST send each retrieved image to a vision-capable AI model with a financial analyst system prompt, requesting a structured concise response with three fixed sections — **Key Positions**, **Observations**, **Actionable Insights** — targeting under 1,500 characters total.
- **FR-003**: System MUST post the resulting analysis as a **thread reply** under the original Slack message containing the image (using that message's `thread_ts`), in the same channel.
- **FR-004**: System MUST track which images have already been processed to prevent duplicate analysis on subsequent runs.
- **FR-005**: System MUST execute automatically on a configurable recurring schedule without requiring manual intervention.
- **FR-006**: System MUST skip non-image attachments and text-only messages without error.
- **FR-007**: System MUST read required credentials (Slack bot token, channel ID, AI API key) from environment variables or a local configuration file — never hard-coded.
- **FR-008**: System MUST log each run's activity (images found, analyzed, skipped) for operator review.
- **FR-009**: System MUST load the analyst system prompt from a configurable file (default `prompts/analyst.txt`), shipped with a risk-analyst default covering correlation, sector concentration, geographic / currency exposure, interest-rate sensitivity, stress tests, liquidity ratings, tail risks, hedging, and rebalancing guidance — condensed to fit the Key Positions / Observations / Actionable Insights output contract.
- **FR-010**: System MUST handle Claude CLI failures (non-zero exit, timeout, auth failure) by logging the error, leaving the image unmarked in deduplication state, and allowing the next scheduler cycle to retry — never crashing the scheduler loop.

### Key Entities

- **Channel Image**: A Slack file attachment of image type, associated with a channel message timestamp, URL, and processing status (pending/processed).
- **Analysis Result**: The AI-generated financial commentary for a given image, including the source image reference and the timestamp it was produced.
- **Processed Record**: A persisted record of image identifiers that have already been analyzed, used for deduplication across runs.
- **Schedule Configuration**: The interval or cron expression defining how frequently the system polls for new images.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New images posted to the Slack channel are analyzed and a response is posted within one full scheduler interval of being uploaded.
- **SC-002**: Zero duplicate analysis posts are produced for any image across repeated scheduler runs.
- **SC-003**: The system completes a full poll-analyze-post cycle for up to 20 new images in a single run without failure.
- **SC-004**: Operators can verify the system is running correctly by reviewing logs that clearly show images found, analyzed, and skipped per run.
- **SC-005**: The scheduler runs continuously for at least 7 days without requiring a manual restart under normal operating conditions.

## Assumptions

- The designated Slack channel is a private or public channel where the bot has been invited and granted the necessary read/post permissions.
- The bot's Slack OAuth scopes include `channels:history` (or `groups:history` for private channels) and `files:read` for reading images, plus `chat:write` for posting analysis.
- Only image file types (JPEG, PNG, GIF, WebP) are in scope for analysis; other file types and text messages are skipped.
- The system runs on a single machine or server with persistent local storage for the processed-records file between runs.
- Internet connectivity to both the Slack API and the AI API is assumed stable; transient failures are logged but do not crash the process.
- The scheduler interval is configurable via environment variable or config file, defaulting to every 15 minutes.
- Analysis is posted as a thread reply under the original image message, not as a new top-level channel message.
- On first run, the bot records its start-up timestamp and ignores all images posted before that moment; only images posted after first startup are ever analyzed.
