import argparse
import logging
import signal
import sys
import time

import schedule

from src.config import ConfigError, ScheduleConfig
from src.logging_setup import setup_logging
from src.state import ProcessedRecord

logger = logging.getLogger(__name__)

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    sig_name = signal.Signals(signum).name
    logger.info(f"Received {sig_name}, shutting down gracefully...")
    _shutdown = True


def main() -> int:
    setup_logging()

    parser = argparse.ArgumentParser(description="Slack Financial Analyst Bot")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run a single poll cycle and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and analyze images but do not post to Slack",
    )
    args = parser.parse_args()

    try:
        config = ScheduleConfig.from_env()
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    try:
        state = ProcessedRecord.load(config.state_file_path)
    except Exception as e:
        logger.error(f"Failed to load state file: {e}")
        return 2

    # Import here to avoid circular imports and allow main.py to validate config first
    from src.analyzer import ClaudeAnalyzer
    from src.scheduler import run_once
    from src.slack_client import SlackClient

    slack = SlackClient(config.slack_bot_token)
    analyzer = ClaudeAnalyzer(config.system_prompt_file)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    if args.run_once:
        try:
            run_once(config, state, slack, analyzer, dry_run=args.dry_run)
            return 0
        except Exception as e:
            logger.error(f"Runtime error: {e}")
            return 2

    logger.info(
        f"Starting scheduler — polling every {config.interval_minutes} minute(s)"
    )
    schedule.every(config.interval_minutes).minutes.do(
        run_once, config, state, slack, analyzer, dry_run=args.dry_run
    )

    # Run immediately on startup, then on schedule
    run_once(config, state, slack, analyzer, dry_run=args.dry_run)

    while not _shutdown:
        schedule.run_pending()
        time.sleep(1)

    logger.info("Shutdown complete")
    state.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
