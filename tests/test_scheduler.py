import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from src.analyzer import ClaudeAnalyzer
from src.config import ScheduleConfig
from src.scheduler import run_once
from src.slack_client import ChannelImage, SlackClient
from src.state import ProcessedRecord


def _make_config(**overrides):
    defaults = {
        "slack_bot_token": "xoxb-test",
        "slack_channel_id": "C123",
        "interval_minutes": 15,
        "state_file_path": "processed.json",
        "system_prompt_file": "prompts/analyst.txt",
    }
    defaults.update(overrides)
    return ScheduleConfig(**defaults)


def _make_image(file_id="F001", ts="1713260500.000100"):
    return ChannelImage(
        file_id=file_id,
        url=f"https://files.slack.com/{file_id}.png",
        mimetype="image/png",
        message_ts=ts,
        posted_at=float(ts),
        channel_id="C123",
    )


class TestHappyPath:
    def test_single_image_flows_through_pipeline(self, tmp_path):
        state_path = str(tmp_path / "processed.json")
        config = _make_config(state_file_path=state_path)
        state = ProcessedRecord.load(state_path)
        # Set first_run_at before the image
        state.first_run_at = 1713260400.0

        image = _make_image()
        temp_file = tmp_path / "download.png"
        temp_file.write_bytes(b"\x89PNG")

        slack = mock.Mock(spec=SlackClient)
        slack.list_channel_messages_with_images.return_value = [image]
        slack.download_image.return_value = temp_file

        analyzer = mock.Mock(spec=ClaudeAnalyzer)
        analyzer.analyze.return_value = (True, "*Key Positions*\nAAPL 30%")

        run_once(config, state, slack, analyzer)

        slack.post_thread_reply.assert_called_once_with(
            "C123", "1713260500.000100", "*Key Positions*\nAAPL 30%"
        )
        assert state.is_processed("F001")


class TestDedupAcrossRuns:
    def test_same_image_analyzed_only_once(self, tmp_path):
        state_path = str(tmp_path / "processed.json")
        config = _make_config(state_file_path=state_path)
        state = ProcessedRecord.load(state_path)
        state.first_run_at = 1713260400.0

        image = _make_image()
        temp_file = tmp_path / "download.png"
        temp_file.write_bytes(b"\x89PNG")

        slack = mock.Mock(spec=SlackClient)
        slack.list_channel_messages_with_images.return_value = [image]
        slack.download_image.return_value = temp_file

        analyzer = mock.Mock(spec=ClaudeAnalyzer)
        analyzer.analyze.return_value = (True, "Analysis text")

        # First run
        run_once(config, state, slack, analyzer)
        assert slack.post_thread_reply.call_count == 1

        # Second run — same image should be skipped
        slack.reset_mock()
        analyzer.reset_mock()
        slack.list_channel_messages_with_images.return_value = [image]
        run_once(config, state, slack, analyzer)

        slack.post_thread_reply.assert_not_called()
        analyzer.analyze.assert_not_called()


class TestFirstRunIgnoresHistorical:
    def test_images_before_first_run_at_are_skipped(self, tmp_path):
        state_path = str(tmp_path / "processed.json")
        config = _make_config(state_file_path=state_path)
        state = ProcessedRecord.load(state_path)
        state.first_run_at = 1713260500.0  # first_run_at = T

        # Image posted before first_run_at
        old_image = _make_image(file_id="F_OLD", ts="1713260400.000100")
        # Image posted after first_run_at
        new_image = _make_image(file_id="F_NEW", ts="1713260600.000100")

        temp_file = tmp_path / "download.png"
        temp_file.write_bytes(b"\x89PNG")

        slack = mock.Mock(spec=SlackClient)
        slack.list_channel_messages_with_images.return_value = [old_image, new_image]
        slack.download_image.return_value = temp_file

        analyzer = mock.Mock(spec=ClaudeAnalyzer)
        analyzer.analyze.return_value = (True, "Analysis")

        run_once(config, state, slack, analyzer)

        # Only the new image should be analyzed
        assert not state.is_processed("F_OLD")
        assert state.is_processed("F_NEW")
        slack.post_thread_reply.assert_called_once()


class TestClaudeFailureRetriesNextTick:
    def test_failed_analysis_retries_on_next_tick(self, tmp_path):
        state_path = str(tmp_path / "processed.json")
        config = _make_config(state_file_path=state_path)
        state = ProcessedRecord.load(state_path)
        state.first_run_at = 1713260400.0

        image = _make_image()
        temp_file = tmp_path / "download.png"
        temp_file.write_bytes(b"\x89PNG")

        slack = mock.Mock(spec=SlackClient)
        slack.list_channel_messages_with_images.return_value = [image]
        slack.download_image.return_value = temp_file

        analyzer = mock.Mock(spec=ClaudeAnalyzer)

        # First tick: analysis fails
        analyzer.analyze.return_value = (False, None)
        run_once(config, state, slack, analyzer)

        assert not state.is_processed("F001")
        slack.post_thread_reply.assert_not_called()

        # Second tick: analysis succeeds
        slack.reset_mock()
        analyzer.reset_mock()
        slack.list_channel_messages_with_images.return_value = [image]
        slack.download_image.return_value = temp_file
        analyzer.analyze.return_value = (True, "Success text")

        run_once(config, state, slack, analyzer)

        assert state.is_processed("F001")
        slack.post_thread_reply.assert_called_once()


class TestSlackApiErrorDoesNotCrashLoop:
    def test_slack_api_error_is_caught(self, tmp_path):
        from slack_sdk.errors import SlackApiError

        state_path = str(tmp_path / "processed.json")
        config = _make_config(state_file_path=state_path)
        state = ProcessedRecord.load(state_path)
        state.first_run_at = 1713260400.0

        image = _make_image()
        temp_file = tmp_path / "download.png"
        temp_file.write_bytes(b"\x89PNG")

        slack = mock.Mock(spec=SlackClient)
        slack.list_channel_messages_with_images.return_value = [image]
        slack.download_image.side_effect = SlackApiError(
            "channel_not_found", mock.Mock()
        )

        analyzer = mock.Mock(spec=ClaudeAnalyzer)

        # Should not raise
        run_once(config, state, slack, analyzer)

        assert not state.is_processed("F001")
        slack.post_thread_reply.assert_not_called()
