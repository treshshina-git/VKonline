from __future__ import annotations

from typing import Any, Dict, List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from src.services.api_client import ApiClient

router = Router()


def _build_keyboard(items: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создаёт inline-кнопки из списка.

    Требуется маппинг полей:
    - id (для callback_data)
    - title/text (под подпись кнопки)
    """

    buttons: List[InlineKeyboardButton] = []
    for it in items:
        item_id = it.get("id") or it.get("position_id") or it.get("key")
        position_id = str(item_id) if item_id is not None else ""
        title = it.get("title") or it.get("name") or it.get("label") or position_id
        title = str(title)

        if not position_id or position_id == "None":
            continue

        buttons.append(
            InlineKeyboardButton(text=title[:64], callback_data=f"pos:{position_id}")
        )

    # Разбиваем по 2 кнопки в ряд
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for b in buttons:
        row.append(b)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _start_keyboard() -> ReplyKeyboardMarkup:
    # Reply-кнопка "Start" (без обязательного /start)
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Start")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


async def _send_categories(message: Message, api: ApiClient) -> None:
    await message.answer("Ищу активные категории...", reply_markup=_start_keyboard())

    try:
        categories = await api.fetch_active_positions_list()
    except Exception as e:
        await message.answer(f"Ошибка при загрузке категорий: {e}")
        return

    if not categories:
        await message.answer("Категорий нет.")
        return

    kb = _build_keyboard(categories)
    await message.answer("Выберите категорию:", reply_markup=kb)


@router.message(Command("start"))
async def cmd_start(message: Message, api: ApiClient):
    await _send_categories(message, api)


@router.message(Command("gogogogo"))
async def cmd_gogogo(message: Message, api: ApiClient):
    # Alias
    await _send_categories(message, api)


@router.message(F.text == "Start")
async def cmd_start_button(message: Message, api: ApiClient):
    await _send_categories(message, api)


@router.callback_query(F.data.startswith("pos:"))
async def on_position_click(callback: CallbackQuery, api: ApiClient):
    category_id = callback.data.split(":", 1)[1]
    await callback.answer()

    await callback.message.answer("Загружаю содержимое категории...")

    try:
        detail = await api.fetch_position_detail(category_id)
    except Exception as e:
        await callback.message.answer(f"Ошибка при загрузке категории: {e}")
        return

    # online_channels => {"data": {"channels": [ {"channel": {...}, "stream": {...}} ]}}
    channels = detail.get("data", {}).get("channels") if isinstance(detail, dict) else None
    if not isinstance(channels, list) or not channels:
        await callback.message.answer("Содержимое не найдено.")
        return

    lines: List[str] = [f"<b>Содержимое категории</b> (категория: {category_id})"]

    for item in channels:
        channel = item.get("channel") if isinstance(item, dict) else None
        stream = item.get("stream") if isinstance(item, dict) else None

        if not isinstance(channel, dict):
            continue

        text_title = (stream or {}).get("title") or channel.get("nick") or f"Канал {channel.get('id')}"
        url = channel.get("url")

        if url:
            lines.append(f"• <a href=\"{url}\">{text_title}</a>")
        else:
            lines.append(f"• {text_title}")

    text = "\n".join(lines)
    await callback.message.answer(text, parse_mode="HTML", disable_web_page_preview=True)

