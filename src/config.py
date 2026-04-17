import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(Exception):
    pass


@dataclass
class ScheduleConfig:
    slack_bot_token: str
    slack_channel_id: str
    interval_minutes: int
    state_file_path: str
    system_prompt_file: str

    @classmethod
    def from_env(cls) -> "ScheduleConfig":
        load_dotenv()

        slack_bot_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
        if not slack_bot_token:
            raise ConfigError("SLACK_BOT_TOKEN is required")

        slack_channel_id = os.environ.get("SLACK_CHANNEL_ID", "").strip()
        if not slack_channel_id:
            raise ConfigError("SLACK_CHANNEL_ID is required")

        interval_raw = os.environ.get("SCHEDULE_INTERVAL_MINUTES", "15").strip()
        try:
            interval_minutes = int(interval_raw)
        except ValueError:
            raise ConfigError(
                f"SCHEDULE_INTERVAL_MINUTES must be a positive integer, got '{interval_raw}'"
            )
        if interval_minutes <= 0:
            raise ConfigError(
                f"SCHEDULE_INTERVAL_MINUTES must be a positive integer, got '{interval_minutes}'"
            )

        state_file_path = os.environ.get("STATE_FILE_PATH", "processed.json").strip()
        system_prompt_file = os.environ.get(
            "SYSTEM_PROMPT_FILE", "prompts/analyst.txt"
        ).strip()

        return cls(
            slack_bot_token=slack_bot_token,
            slack_channel_id=slack_channel_id,
            interval_minutes=interval_minutes,
            state_file_path=state_file_path,
            system_prompt_file=system_prompt_file,
        )
