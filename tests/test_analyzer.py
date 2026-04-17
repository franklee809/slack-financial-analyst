import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from src.analyzer import ClaudeAnalyzer


@pytest.fixture
def analyzer(tmp_path):
    prompt = tmp_path / "analyst.txt"
    prompt.write_text("You are a financial analyst.")
    return ClaudeAnalyzer(str(prompt))


@pytest.fixture
def image_path(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    return img


class TestClaudeAnalyzer:
    def test_success_returns_true_and_stdout(self, analyzer, image_path):
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "*Key Positions*\nAPPL 30%\n*Observations*\nConcentrated\n*Actionable Insights*\nDiversify"
        mock_result.stderr = ""

        with mock.patch("src.analyzer.subprocess.run", return_value=mock_result):
            success, text = analyzer.analyze(image_path)

        assert success is True
        assert "*Key Positions*" in text

    def test_nonzero_exit_returns_false_none(self, analyzer, image_path):
        mock_result = mock.Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error"

        with mock.patch("src.analyzer.subprocess.run", return_value=mock_result):
            success, text = analyzer.analyze(image_path)

        assert success is False
        assert text is None

    def test_timeout_returns_false_none(self, analyzer, image_path):
        with mock.patch(
            "src.analyzer.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=120),
        ):
            success, text = analyzer.analyze(image_path)

        assert success is False
        assert text is None

    def test_long_response_truncated_with_warning(self, analyzer, image_path):
        long_text = "x" * 5000
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = long_text
        mock_result.stderr = ""

        with mock.patch("src.analyzer.subprocess.run", return_value=mock_result):
            success, text = analyzer.analyze(image_path)

        assert success is True
        assert len(text) <= 3900
        assert text.endswith("…")

    def test_cli_not_found_returns_false_none(self, analyzer, image_path):
        with mock.patch(
            "src.analyzer.subprocess.run",
            side_effect=FileNotFoundError("No such file: 'claude'"),
        ):
            success, text = analyzer.analyze(image_path)

        assert success is False
        assert text is None
