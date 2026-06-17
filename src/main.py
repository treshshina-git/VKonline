from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from loguru import logger

from src.config import load_settings
from src.handlers.commands import router as commands_router
from src.services.api_client import ApiClient


async def main() -> None:
    settings = load_settings()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Сервис API
    api = ApiClient(settings)

    # Подключаем зависимости в handlers через middleware.

    class ApiMiddleware:
        async def __call__(self, handler, event, data):

            data["api"] = api
            return await handler(event, data)


    dp.message.middleware(ApiMiddleware())
    dp.callback_query.middleware(ApiMiddleware())

    dp.include_router(commands_router)

    logger.info("Bot started")

    await bot.set_my_commands([BotCommand(command="GoGoGo", description="Получить список активных позиций")])

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

