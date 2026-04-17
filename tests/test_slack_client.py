from pathlib import Path
from unittest import mock

import pytest

from src.slack_client import ChannelImage, SlackClient


@pytest.fixture
def slack():
    return SlackClient("xoxb-test-token")


class TestListChannelMessagesWithImages:
    def test_filters_to_image_files_and_carries_message_ts(self, slack):
        mock_response = {
            "messages": [
                {
                    "ts": "1713260400.000100",
                    "text": "Here is my portfolio",
                    "files": [
                        {
                            "id": "F001",
                            "mimetype": "image/png",
                            "url_private_download": "https://files.slack.com/F001.png",
                        }
                    ],
                },
                {
                    "ts": "1713260500.000200",
                    "text": "Just text, no files",
                },
            ],
            "response_metadata": {},
        }

        with mock.patch.object(slack._client, "conversations_history", return_value=mock_response):
            images = slack.list_channel_messages_with_images("C123")

        assert len(images) == 1
        img = images[0]
        assert img.file_id == "F001"
        assert img.message_ts == "1713260400.000100"
        assert img.posted_at == float("1713260400.000100")
        assert img.channel_id == "C123"
        assert img.mimetype == "image/png"


class TestDownloadImage:
    def test_sends_authorization_bearer_header(self, slack):
        image = ChannelImage(
            file_id="F001",
            url="https://files.slack.com/F001.png",
            mimetype="image/png",
            message_ts="1713260400.000100",
            posted_at=1713260400.0001,
            channel_id="C123",
        )

        mock_response = mock.Mock()
        mock_response.content = b"\x89PNG\r\n\x1a\n"
        mock_response.raise_for_status = mock.Mock()

        with mock.patch("src.slack_client.requests.get", return_value=mock_response) as mock_get:
            path = slack.download_image(image)

        mock_get.assert_called_once_with(
            "https://files.slack.com/F001.png",
            headers={"Authorization": "Bearer xoxb-test-token"},
            timeout=30,
        )
        assert path.exists()
        assert path.suffix == ".png"
        path.unlink()


class TestPostThreadReply:
    def test_calls_chat_post_message_with_thread_ts(self, slack):
        with mock.patch.object(slack._client, "chat_postMessage") as mock_post:
            slack.post_thread_reply("C123", "1713260400.000100", "Analysis text")

        mock_post.assert_called_once_with(
            channel="C123",
            thread_ts="1713260400.000100",
            text="Analysis text",
        )

    def test_not_in_thread_error_is_warning_not_exception(self, slack):
        from slack_sdk.errors import SlackApiError

        error_response = mock.Mock()
        error_response.get.return_value = "not_in_thread"
        error_response.__getitem__ = mock.Mock(return_value="not_in_thread")

        with mock.patch.object(
            slack._client,
            "chat_postMessage",
            side_effect=SlackApiError("not_in_thread", error_response),
        ):
            # Should not raise
            slack.post_thread_reply("C123", "1713260400.000100", "text")


class TestSkipsNonImageContent:
    def test_skips_text_only_and_non_image_files(self, slack):
        mock_response = {
            "messages": [
                {
                    "ts": "1713260400.000100",
                    "text": "Just text, no files",
                },
                {
                    "ts": "1713260500.000200",
                    "text": "Here is a PDF",
                    "files": [
                        {
                            "id": "F_PDF",
                            "mimetype": "application/pdf",
                            "url_private_download": "https://files.slack.com/F_PDF.pdf",
                        }
                    ],
                },
                {
                    "ts": "1713260600.000300",
                    "text": "Here is a PNG",
                    "files": [
                        {
                            "id": "F_PNG",
                            "mimetype": "image/png",
                            "url_private_download": "https://files.slack.com/F_PNG.png",
                        }
                    ],
                },
            ],
            "response_metadata": {},
        }

        with mock.patch.object(slack._client, "conversations_history", return_value=mock_response):
            images = slack.list_channel_messages_with_images("C123")

        assert len(images) == 1
        assert images[0].file_id == "F_PNG"
