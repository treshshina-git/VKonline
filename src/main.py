from __future__ import annotations

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from src.config import load_settings
from src.services.api_client import ApiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_categories_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    buttons: list[InlineKeyboardButton] = []
    for it in categories:
        item_id = it.get("id") or it.get("position_id") or it.get("key")
        if item_id is None:
            continue
        category_id = str(item_id)
        if not category_id or category_id == "None":
            continue
        title = it.get("title") or it.get("name") or it.get("label") or category_id
        buttons.append(InlineKeyboardButton(text=str(title)[:64], callback_data=f"cat:{category_id}"))

    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for b in buttons:
        row.append(b)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    return InlineKeyboardMarkup(rows)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api: ApiClient = context.application.bot_data["api"]

    if update.effective_message is None:
        return

    await update.effective_message.reply_text("Ищу активные категории...")

    try:
        categories = await api.fetch_active_positions_list()
    except Exception as e:
        logger.exception("Failed to fetch categories")
        await update.effective_message.reply_text(f"Ошибка при загрузке категорий: {e}")
        return

    if not categories:
        await update.effective_message.reply_text("Категорий нет.")
        return

    kb = _build_categories_keyboard(categories)
    await update.effective_message.reply_text("Выберите категорию:", reply_markup=kb)


async def category_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    api: ApiClient = context.application.bot_data["api"]
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    category_id = query.data.split(":", 1)[1] if query.data and ":" in query.data else ""
    if not category_id:
        await query.edit_message_text("Некорректный выбор категории.")
        return

    await query.message.reply_text("Загружаю содержимое категории...")

    try:
        detail = await api.fetch_position_detail(category_id)
    except Exception as e:
        logger.exception("Failed to fetch category content")
        await query.message.reply_text(f"Ошибка при загрузке категории: {e}")
        return

    channels = detail.get("data", {}).get("channels") if isinstance(detail, dict) else None
    if not isinstance(channels, list) or not channels:
        await query.message.reply_text("Содержимое не найдено.")
        return

    lines: list[str] = [f"<b>Содержимое категории</b> (категория: {category_id})"]
    for item in channels:
        channel = item.get("channel") if isinstance(item, dict) else None
        stream = item.get("stream") if isinstance(item, dict) else None
        if not isinstance(channel, dict):
            continue

        text_title = (stream or {}).get("title") or channel.get("nick") or f"Канал {channel.get('id')}"
        url = channel.get("url")

        if url:
            lines.append(f'• <a href="{url}">{text_title}</a>')
        else:
            lines.append(f"• {text_title}")

    text = "\n".join(lines)
    await query.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def main() -> None:
    settings = load_settings()
    api = ApiClient(settings)

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["api"] = api

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("gogogogo", start_handler))  # alias
    app.add_handler(CallbackQueryHandler(category_callback_handler, pattern=r"^cat:"))

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()

