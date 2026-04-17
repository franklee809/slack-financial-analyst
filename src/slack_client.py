import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

SUPPORTED_MIMETYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

MIMETYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


@dataclass
class ChannelImage:
    file_id: str
    url: str
    mimetype: str
    message_ts: str
    posted_at: float
    channel_id: str


class SlackClient:
    def __init__(self, token: str):
        self._client = WebClient(token=token)
        self._token = token

    def list_channel_messages_with_images(
        self, channel_id: str, oldest: float | None = None
    ) -> list[ChannelImage]:
        images = []
        kwargs = {"channel": channel_id, "limit": 200}
        if oldest is not None:
            kwargs["oldest"] = str(oldest)

        cursor = None
        while True:
            if cursor:
                kwargs["cursor"] = cursor

            response = self._client.conversations_history(**kwargs)
            messages = response.get("messages", [])

            for msg in messages:
                files = msg.get("files", [])
                for f in files:
                    mimetype = f.get("mimetype", "")
                    if mimetype not in SUPPORTED_MIMETYPES:
                        continue
                    url = f.get("url_private_download", "")
                    if not url:
                        continue
                    images.append(
                        ChannelImage(
                            file_id=f["id"],
                            url=url,
                            mimetype=mimetype,
                            message_ts=msg["ts"],
                            posted_at=float(msg["ts"]),
                            channel_id=channel_id,
                        )
                    )

            metadata = response.get("response_metadata", {})
            cursor = metadata.get("next_cursor")
            if not cursor:
                break

        return images

    def download_image(self, image: ChannelImage) -> Path:
        ext = MIMETYPE_EXTENSIONS.get(image.mimetype, ".png")
        resp = requests.get(
            image.url,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=30,
        )
        resp.raise_for_status()

        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        try:
            tmp.write(resp.content)
            tmp.close()
            return Path(tmp.name)
        except BaseException:
            tmp.close()
            Path(tmp.name).unlink(missing_ok=True)
            raise

    def post_thread_reply(self, channel_id: str, thread_ts: str, text: str) -> None:
        try:
            self._client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=text,
            )
        except SlackApiError as e:
            error_code = e.response.get("error", "")
            if error_code in ("not_in_thread", "channel_not_found"):
                logger.warning(
                    f"Non-fatal Slack error posting thread reply: {error_code}"
                )
            else:
                raise
