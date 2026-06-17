# VKonline Telegram Bot

Telegram-бот на Python, который:
1) Показывает пользователю список категорий.
2) После выбора категории запрашивает содержимое категории через единую точку входа `https://apidev.live.vkvideo.ru/`.

## Запуск

### Локально

1. Создай виртуальное окружение и установи зависимости:
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Установи переменные окружения:

- `TELEGRAM_BOT_TOKEN` — токен бота
- `VK_CLIENT_ID` — client_id для VK OAuth
- `VK_CLIENT_SECRET` — client_secret для VK OAuth
- (опционально) `VKVIDEO_API_BASE_URL` — по умолчанию `https://apidev.live.vkvideo.ru`
- (опционально) `VK_OAUTH_TOKEN_URL` — по умолчанию `https://api.live.vkvideo.ru/oauth/server/token`
- (опционально) `REQUEST_TIMEOUT_SECONDS` — по умолчанию `20`

3. Запуск:
```bash
python -m src.main
```

## Railway

Добавь те же переменные окружения в настройках проекта.

Если Railway запускает командой, используй:
- `python -m src.main`

## API

- Категории:
  - `GET {VKVIDEO_API_BASE_URL}/v1/catalog/active_channels`
- Содержимое категории:
  - `GET {VKVIDEO_API_BASE_URL}/v1/catalog/online_channels?category_id=<id>`

