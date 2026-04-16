"""Entry point for running the Telegram bot: python -m app.bot"""

import asyncio

from app.bot.handlers import start_bot


def main() -> None:
    asyncio.run(start_bot())


if __name__ == "__main__":
    main()
