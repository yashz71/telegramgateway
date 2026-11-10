
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing from .env")

TELEGRAM_API_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
)

TELEGRAM_FILE_URL = (
    f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"
)


class TelegramAPIError(Exception):
    pass


async def _api_request(
    method: str,
    payload: dict | None = None,
) -> Any:
    """Make a JSON POST request to the Telegram Bot API."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{TELEGRAM_API_URL}/{method}",
            json=payload or {},
        )

        response.raise_for_status()
        data = response.json()

        if not data.get("ok"):
            raise TelegramAPIError(
                data.get("description", "Telegram API request failed")
            )

        return data["result"]


async def get_me() -> dict:
    """Verify the bot token and retrieve bot information."""

    return await _api_request("getMe")


async def get_updates(
    offset: int | None = None,
    timeout: int = 30,
) -> list[dict]:
    """
    Retrieve updates using long polling.

    Only use this when a webhook is NOT configured.
    """

    payload = {
        "timeout": timeout,
        "allowed_updates": ["message"],
    }

    if offset is not None:
        payload["offset"] = offset

    return await _api_request("getUpdates", payload)


async def send_text_message(
    chat_id: int,
    text: str,
) -> dict:
    """Send a text message to a Telegram chat."""

    return await _api_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
        },
    )


async def send_photo(
    chat_id: int,
    photo_path: str | Path,
    caption: str | None = None,
) -> dict:
    """Upload and send a photo using multipart/form-data."""

    photo_path = Path(photo_path)

    if not photo_path.is_file():
        raise FileNotFoundError(photo_path)

    data = {"chat_id": str(chat_id)}

    if caption:
        data["caption"] = caption

    async with httpx.AsyncClient(timeout=60.0) as client:
        with photo_path.open("rb") as photo:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendPhoto",
                data=data,
                files={
                    "photo": (
                        photo_path.name,
                        photo,
                        "application/octet-stream",
                    )
                },
            )

        response.raise_for_status()
        result = response.json()

        if not result.get("ok"):
            raise TelegramAPIError(
                result.get("description", "Could not send photo")
            )

        return result["result"]


async def get_file(file_id: str) -> dict:
    """Retrieve metadata for a Telegram file."""

    return await _api_request(
        "getFile",
        {"file_id": file_id},
    )


async def download_file(
    file_id: str,
    destination: str | Path,
) -> Path:
    """Download a Telegram file to local storage."""

    file_info = await get_file(file_id)

    file_path = file_info.get("file_path")

    if not file_path:
        raise TelegramAPIError("Telegram did not return a file_path")

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{TELEGRAM_FILE_URL}/{file_path}"
        )
        response.raise_for_status()

    destination.write_bytes(response.content)

    return destination


async def set_webhook(webhook_url: str, secret_token: str | None = None):
    """Register the FastAPI endpoint with Telegram."""

    payload = {
        "url": webhook_url,
        "allowed_updates": ["message"],
    }

    if secret_token:
        payload["secret_token"] = secret_token

    return await _api_request("setWebhook", payload)


async def get_webhook_info():
    """Retrieve the current Telegram webhook configuration."""

    return await _api_request("getWebhookInfo")
