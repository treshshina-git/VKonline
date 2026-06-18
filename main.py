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
    #print(f"Fetched token response: {data}")  # Debug print
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
            "limit": limit,
            #"query": "",
            #"type": ""
            "offset": offset,
            "category_type": "irl, sport, game",
            #"has_vk_video": False,
            #"all_streams": True
        }
    r = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    #print(f"Fetched categories data: {data}")  # Debug print
    datas = data.get("data") 
    #print(f"Extracted categories field: {data}")  # Debug print
    # Ожидаем список в одном из стандартных ключей
    cats = datas.get("categories")
    #print(f"Extracted categories: {cats}")  # Debug print
    if not isinstance(cats, list):
        raise RuntimeError(f"Unexpected categories payload: {data}")
    if not cats:
        print("No categories found in response.")
    else:
        print(f"Found {len(cats)} categories.")
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
        "category_id": category_id,
        "all_streams": True,
        "has_vk_video": False,
        "category_type": "irl, sport, game",
        "all_streams": True,
    }

    r = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    data = r.json()
    #print(data)
    chans = data.get("data").get("channels")
    #print(chans)
    if not isinstance(chans, list):
        raise RuntimeError(f"Unexpected channels payload: {data}")
    return chans


def build_categories_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []

    # Кнопок в ряд не более ~3-4, чтобы UI был читабельнее.
    per_row = 2
    #print(categories)
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
    #await update.message.reply_text("Нажми, чтобы получить список категорий:")

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
    loading_text = None

    if cb == "show_categories":
        loading_text = "Загружаю категории..."
        await query.edit_message_text(loading_text)
        await show_categories(query, context)
        return

    if cb == "back_to_categories":
        loading_text = "Возвращаю категории..."
        await query.edit_message_text(loading_text)
        await show_categories(query, context)
        return

    if cb.startswith("refresh_channels|"):
        # refresh_channels|cat|{category_type}|{category_id}
        payload = cb.split("|", 1)[1] if "|" in cb else ""
        if payload.startswith("cat|"):
            loading_text = "Обновляю каналы..."
            await query.edit_message_text(loading_text)
            await show_channels_for_category(query, context, payload)
            return

    if cb.startswith("cat|"):
        loading_text = "Загружаю каналы..."
        await query.edit_message_text(loading_text)
        await show_channels_for_category(query, context, cb)
        return

    await query.edit_message_text("Неизвестная команда.")




async def show_categories(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    limit = int(context.bot_data.get("categories_limit", 10))
    offset = int(context.bot_data.get("categories_offset", 0))
    #print(f"Showing categories with limit={limit} and offset={offset}")  # Debug print
    async with httpx.AsyncClient() as client:
        token = await fetch_token(client)
        categories = await get_online_categories(client, token, limit=limit, offset=offset)

    keyboard = build_categories_keyboard(categories)
    if not keyboard.inline_keyboard:
        await query.message.reply_text("Категории не найдены.")
        return

    await query.edit_message_text("Выберите категорию:", reply_markup=keyboard)


async def show_channels_for_category(query, context: ContextTypes.DEFAULT_TYPE, cb: str) -> None:
    # cb: cat|category_type|category_id
    parts = cb.split("|", 2)
    #print(parts)
    #category_type = "irl" 
    #category_id = "6abff723-68ea-4c47-8df1-55573d362749"
    if parts is None:
        await query.message.reply_text("Некорректные данные категории.")
        return

    category_type = parts[1]
    category_id = parts[2]
    #print(category_id, category_type)
    # ТЗ: limit <= 200
    limit = int(context.bot_data.get("channels_limit", 50))
    if limit > 200:
        limit = 200

    offset = int(context.bot_data.get("channels_offset", 0))
    categoryid = category_id
    async with httpx.AsyncClient() as client:
        token = await fetch_token(client)
        channels = await get_online_channels(
            client,
            token,
            limit=limit,
            offset=offset,
            category_id=categoryid,
            category_type=category_type,
            has_vk_video=True,
            all_streams=False,
        )
        #print(channels)

    if not channels:
        await query.message.reply_text("Каналы по этой категории не найдены.")
        return

    # Форматируем обычным сообщением (без кнопок).
    lines: List[str] = []
    for idx, ch in enumerate(channels, start=1):
        # Пытаемся угадать поля.
        name = trim_30(ch.get("channel").get("nick"))
        ch_id = ch.get("channel").get("url")
        stream_info = trim_30(ch.get("stream").get("title"))
        viewers = ch.get("stream").get("counters").get("viewers")
        line = f"{viewers} |    <b>{name}</b>\n"
        # для web app будем открывать /play?urik=<ch_id> внутри Telegram
        if ch_id is not None:
            urik = "https://live.vkvideo.ru/" + ch_id
        else:
            urik = "https://live.vkvideo.ru/"

        if stream_info:
            stream_info = str(stream_info)
            if len(stream_info) > 120:
                stream_info = stream_info[:117] + "..."
            line += f"\n{stream_info}"

        lines.append(line)


    text = "\n".join(lines)
    #print(text)
    refresh_payload = f"refresh_channels|{cb}"
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="Назад", callback_data="back_to_categories"),
                InlineKeyboardButton(text="Обновить", callback_data=refresh_payload),
            ]
        ]
    )

    # base URL вашего webapp (должен быть https)
    WEBAPP_BASE_URL = "https://vkonline-production.up.railway.app"

    # Вырежем HTML-теги, чтобы не было «полузакликаных» ссылок
    text = text.replace("<a ", "").replace("</a>", "")

    import urllib.parse

    # Кнопки для КАЖДОГО канала: передаём urik в web_app.url
    # На фронте webapp/public/index.html используется query param urik.
    channel_buttons: List[List[InlineKeyboardButton]] = []
    current_row: List[InlineKeyboardButton] = []

    for ch in channels:
        ch_id = ch.get("channel").get("url")
        name = trim_30(ch.get("channel").get("nick"))
        if not ch_id:
            continue

        urik = "https://live.vkvideo.ru/" + ch_id
        encoded_urik = urllib.parse.quote(urik, safe="")
        webapp_url = f"{WEBAPP_BASE_URL}/?play=1&urik={encoded_urik}"

        current_row.append(
            InlineKeyboardButton(text=name or "Канал", web_app={"url": webapp_url})
        )

        # 1 кнопка в строке (чтобы не упираться в лимиты Telegram)
        channel_buttons.append(current_row)
        current_row = []

    keyboard = InlineKeyboardMarkup(
        channel_buttons + [
            [
                InlineKeyboardButton(text="Назад", callback_data="back_to_categories"),
                InlineKeyboardButton(text="Обновить", callback_data=refresh_payload),
            ]
        ]
    )

    await query.message.reply_text(
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )




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
    application.bot_data["channels_limit"] = 10
    application.bot_data["channels_offset"] = 0

    application.run_polling(close_loop=False)



if __name__ == "__main__":
    main()



