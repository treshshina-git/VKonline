import asyncio
import logging
import os, base64
from typing import Any, Dict, List, Optional, Tuple
 
import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes


logger = logging.getLogger(__name__)

print("Starting bot...") 
def _env(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return v


VK_CLIENT_ID = _env("VK_CLIENT_ID")
VK_CLIENT_SECRET = _env("VK_CLIENT_SECRET")
TOKEN_VK_URL = _env("TOKEN_VK_URL")
APIDEV_BASE_URL = os.getenv("APIDEV_BASE_URL", "https://apidev.live.vkvideo.ru/").rstrip("/")


BOT_TOKEN = _env("BOT_TOKEN")


def trim_30(s: Any) -> str:
    if s is None:
        return ""
    s = str(s)
    return s[:30]


async def fetch_token(client: httpx.AsyncClient) -> str:
    credentials = f"{VK_CLIENT_ID}:{VK_CLIENT_SECRET}"
    encoded = base64.b64encode(
        credentials.encode()
    ).decode()
    r = await client.post(
        TOKEN_VK_URL,
        headers={
            "Authorization": f"Basic {encoded}",   
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={"grant_type": "client_credentials"},
        timeout=30
    )
    r.raise_for_status()
    data = r.json()
    print(f"Fetched token response: {data}")  # Debug print
    token = data.get("access_token") or data.get("token") or data.get("accessToken")
    if not token:
        raise RuntimeError(f"Token not found in response: {data}")
    return token


async def get_online_categories(
    client: httpx.AsyncClient,
    token: str,
    limit: int = 10,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    url = f"{APIDEV_BASE_URL}/v1/catalog/online_categories"
    #params = {"limit": int(limit), "offset": int(offset)}
    params={
            "limit": 30,
            #"query": "",
            #"type": ""
            "offset": 0,
            "category_type": "irl",
            #"has_vk_video": False,
            #"all_streams": True
        }
    r = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    print(f"Fetched categories data: {data}")  # Debug print
    data = data.get("data") 
    print(f"Extracted categories field: {data}")  # Debug print
    # Ожидаем список в одном из стандартных ключей
    cats = data.get("id").get("categories")
    print(f"Extracted categories: {cats}")  # Debug print
    if not isinstance(cats, list):
        raise RuntimeError(f"Unexpected categories payload: {data}")
    return cats


async def get_online_channels(
    client: httpx.AsyncClient,
    token: str,
    *,
    limit: int,
    offset: int,
    category_id: str,
    category_type: str,
    has_vk_video: bool = True,
    all_streams: bool = False,
) -> List[Dict[str, Any]]:
    url = f"{APIDEV_BASE_URL}/v1/catalog/online_channels"
    params={
            "limit": 50,
            "offset": 0,
            "category_id": section_id,
            "all_streams": True,
            "has_vk_video": False,
            "category_type": "irl",
            "all_streams": True,
    }

    r = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    chans = data.get("items") or data.get("channels") or data
    if not isinstance(chans, list):
        raise RuntimeError(f"Unexpected channels payload: {data}")
    return chans


def build_categories_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []

    # Кнопок в ряд не более ~3-4, чтобы UI был читабельнее.
    per_row = 2

    for i, c in enumerate(categories):
        name = trim_30(c.get("name") or c.get("title") or c.get("category_name") or "Категория")
        category_id = str(c.get("category_id") or c.get("id") or "")
        category_type = str(c.get("category_type") or c.get("type") or "")

        if not category_id:
            # пропустим странные элементы
            continue

        payload = f"cat|{category_type}|{category_id}"
        row.append(InlineKeyboardButton(text=name, callback_data=payload))

        if (i + 1) % per_row == 0:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Нажми, чтобы получить список категорий:")

    # Проставим кнопку как отдельное сообщение: пользовательский UX.
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="Показать категории", callback_data="show_categories")]]
    )
    await update.message.reply_text("Действие:", reply_markup=keyboard)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()

    cb = query.data or ""
    if cb == "show_categories":
        await query.edit_message_text("Загружаю категории...")
        await show_categories(query, context)
        return

    if cb.startswith("cat|"):
        await query.edit_message_text("Загружаю каналы...")
        await show_channels_for_category(query, context, cb)
        return

    await query.edit_message_text("Неизвестная команда.")


async def show_categories(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    limit = int(context.bot_data.get("categories_limit", 10))
    offset = int(context.bot_data.get("categories_offset", 0))

    async with httpx.AsyncClient() as client:
        token = await fetch_token(client)
        categories = await get_online_categories(client, token, limit=limit, offset=offset)

    keyboard = build_categories_keyboard(categories)
    if not keyboard.inline_keyboard:
        await query.message.reply_text("Категории не найдены.")
        return

    await query.message.reply_text("Выберите категорию:", reply_markup=keyboard)


async def show_channels_for_category(query, context: ContextTypes.DEFAULT_TYPE, cb: str) -> None:
    # cb: cat|category_type|category_id
    parts = cb.split("|", 2)
    if len(parts) != 3:
        await query.message.reply_text("Некорректные данные категории.")
        return

    category_type = parts[1]
    category_id = parts[2]

    # ТЗ: limit <= 200
    limit = int(context.bot_data.get("channels_limit", 50))
    if limit > 200:
        limit = 200

    offset = int(context.bot_data.get("channels_offset", 0))

    async with httpx.AsyncClient() as client:
        token = await fetch_token(client)
        channels = await get_online_channels(
            client,
            token,
            limit=limit,
            offset=offset,
            category_id=category_id,
            category_type=category_type,
            has_vk_video=True,
            all_streams=False,
        )

    if not channels:
        await query.message.reply_text("Каналы по этой категории не найдены.")
        return

    # Форматируем обычным сообщением (без кнопок).
    lines: List[str] = []
    for idx, ch in enumerate(channels, start=1):
        # Пытаемся угадать поля.
        name = trim_30(ch.get("name") or ch.get("title") or ch.get("channel_name") or "Канал")
        ch_id = ch.get("id") or ch.get("channel_id")
        stream_info = ch.get("description") or ch.get("subtitle") or ch.get("meta")

        line = f"{idx}. {name}"
        if stream_info:
            stream_info = str(stream_info)
            # не делаем огромные сообщения
            if len(stream_info) > 120:
                stream_info = stream_info[:117] + "..."
            line += f" — {stream_info}"

        if ch_id is not None:
            line += ""

        lines.append(line)

    text = "\n".join(lines)
    await query.message.reply_text(text)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error", exc_info=context.error)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_error_handler(error_handler)

    # Параметры по умолчанию.
    application.bot_data["categories_limit"] = 10
    application.bot_data["categories_offset"] = 0
    application.bot_data["channels_limit"] = 50
    application.bot_data["channels_offset"] = 0

    application.run_polling(close_loop=False)



if __name__ == "__main__":
    main()



