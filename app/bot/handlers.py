"""Telegram bot handlers for HR clients."""

import structlog
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import settings

log = structlog.get_logger()
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "VoiceScreen - AI-скрининг кандидатов.\n\n"
        "Команды:\n"
        "/register - Зарегистрировать компанию\n"
        "/upload - Загрузить CSV с кандидатами\n"
        "/status - Статус обзвона\n"
        "/report - Получить отчёт"
    )


@router.message(Command("register"))
async def cmd_register(message: Message) -> None:
    # TODO: create Client record, link tg_chat_id
    await message.answer("Регистрация: отправьте название вашей компании.")


@router.message(Command("upload"))
async def cmd_upload(message: Message) -> None:
    # TODO: accept CSV file, parse, create candidates
    await message.answer("Отправьте CSV-файл с кандидатами (ФИО, телефон).")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    # TODO: query active calls for this client
    await message.answer("Статус обзвона: пока нет активных задач.")


@router.message(Command("report"))
async def cmd_report(message: Message) -> None:
    # TODO: generate and send report
    await message.answer("Отчёт будет готов после завершения обзвона.")


async def start_bot() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    log.info("telegram_bot_starting")
    await dp.start_polling(bot)
