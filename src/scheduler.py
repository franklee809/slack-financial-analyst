import logging
import os

from src.analyzer import ClaudeAnalyzer
from src.config import ScheduleConfig
from src.slack_client import SlackClient
from src.state import ProcessedRecord

logger = logging.getLogger(__name__)


def run_once(
    config: ScheduleConfig,
    state: ProcessedRecord,
    slack: SlackClient,
    analyzer: ClaudeAnalyzer,
    dry_run: bool = False,
) -> None:
    found = 0
    analyzed = 0
    skipped = 0
    failed = 0

    images = slack.list_channel_messages_with_images(
        config.slack_channel_id,
        oldest=state.first_run_at,
    )
    found = len(images)

    for image in images:
        if state.is_processed(image.file_id):
            skipped += 1
            continue

        if image.posted_at < state.first_run_at:
            skipped += 1
            continue

        temp_path = None
        try:
            temp_path = slack.download_image(image)
            success, text = analyzer.analyze(temp_path)

            if not success:
                logger.warning(f"Analysis failed for file {image.file_id}, will retry next cycle")
                failed += 1
                continue

            if not dry_run:
                slack.post_thread_reply(
                    image.channel_id, image.message_ts, text
                )

            state.add_processed(image.file_id)
            state.save()
            analyzed += 1
        except Exception:
            logger.exception(f"Error processing file {image.file_id}, skipping")
            failed += 1
        finally:
            if temp_path is not None:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    logger.info(
        f"cycle complete: found={found} analyzed={analyzed} skipped={skipped} failed={failed}"
    )
