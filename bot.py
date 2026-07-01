"""
Drone Weather Bot — entry point.

Run with: python bot.py
Requires a .env file with BOT_TOKEN (see .env.example).
"""
import asyncio
import logging

from aiogram import Bot

from config import BOT_TOKEN
from handlers import dp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=BOT_TOKEN)
    logger.info("Drone Weather Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
