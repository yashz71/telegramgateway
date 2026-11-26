import os
from pathlib import Path

from telethon import TelegramClient


async def login_telegram():
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    phone = os.environ["TELEGRAM_PHONE"]

    session_path = Path(
        os.getenv("TELEGRAM_SESSION", "storage/telegram_user")
    )

    session_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    client = TelegramClient(
        str(session_path),
        api_id,
        api_hash,
    )

    await client.start(phone=phone)

    me = await client.get_me()

    print("Telegram authenticated")
    print("User ID:", me.id)
    print("Username:", me.username)

    return client
