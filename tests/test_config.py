import os
from unittest import mock

import pytest

from src.config import ConfigError, ScheduleConfig


class TestScheduleConfig:
    def test_missing_slack_bot_token_raises(self):
        env = {"SLACK_CHANNEL_ID": "C123"}
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigError, match="SLACK_BOT_TOKEN"):
                ScheduleConfig.from_env()

    def test_missing_slack_channel_id_raises(self):
        env = {"SLACK_BOT_TOKEN": "xoxb-test"}
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigError, match="SLACK_CHANNEL_ID"):
                ScheduleConfig.from_env()

    def test_non_integer_interval_raises(self):
        env = {
            "SLACK_BOT_TOKEN": "xoxb-test",
            "SLACK_CHANNEL_ID": "C123",
            "SCHEDULE_INTERVAL_MINUTES": "not-a-number",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigError, match="positive integer"):
                ScheduleConfig.from_env()

    def test_zero_interval_raises(self):
        env = {
            "SLACK_BOT_TOKEN": "xoxb-test",
            "SLACK_CHANNEL_ID": "C123",
            "SCHEDULE_INTERVAL_MINUTES": "0",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigError, match="positive integer"):
                ScheduleConfig.from_env()

    def test_happy_path_with_defaults(self):
        env = {
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SLACK_CHANNEL_ID": "C01234ABC",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            config = ScheduleConfig.from_env()

        assert config.slack_bot_token == "xoxb-test-token"
        assert config.slack_channel_id == "C01234ABC"
        assert config.interval_minutes == 15
        assert config.state_file_path == "processed.json"
        assert config.system_prompt_file == "prompts/analyst.txt"

    def test_happy_path_with_custom_values(self):
        env = {
            "SLACK_BOT_TOKEN": "xoxb-custom",
            "SLACK_CHANNEL_ID": "C999",
            "SCHEDULE_INTERVAL_MINUTES": "5",
            "STATE_FILE_PATH": "/tmp/state.json",
            "SYSTEM_PROMPT_FILE": "/tmp/prompt.txt",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            config = ScheduleConfig.from_env()

        assert config.interval_minutes == 5
        assert config.state_file_path == "/tmp/state.json"
        assert config.system_prompt_file == "/tmp/prompt.txt"
