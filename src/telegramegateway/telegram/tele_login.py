# telegram_login.py

import asyncio

from dotenv import load_dotenv

from auth import login_telegram


async def main():
    load_dotenv()

    client = await login_telegram()
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
