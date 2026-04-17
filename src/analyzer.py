import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_RESPONSE_LENGTH = 3900


class ClaudeAnalyzer:
    def __init__(self, system_prompt_file: str):
        self._system_prompt_file = system_prompt_file

    def analyze(
        self, image_path: Path, system_prompt_path: str | None = None
    ) -> tuple[bool, str | None]:
        prompt_path = system_prompt_path or self._system_prompt_file
        try:
            with open(prompt_path, "r") as f:
                prompt_text = f.read()
        except FileNotFoundError:
            logger.error(f"System prompt file not found: {prompt_path}")
            return False, None

        try:
            result = subprocess.run(
                ["claude", "-p", prompt_text, "--image", str(image_path)],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Claude CLI timed out analyzing {image_path}")
            return False, None
        except FileNotFoundError:
            logger.error("claude CLI not found — is it installed and on PATH?")
            return False, None

        if result.returncode != 0:
            logger.error(
                f"Claude CLI exited with code {result.returncode}: {result.stderr.strip()}"
            )
            return False, None

        text = result.stdout.strip()
        if len(text) > MAX_RESPONSE_LENGTH:
            logger.warning(
                f"Claude response ({len(text)} chars) exceeds {MAX_RESPONSE_LENGTH} limit, truncating"
            )
            text = text[: MAX_RESPONSE_LENGTH - 1] + "…"

        return True, text
