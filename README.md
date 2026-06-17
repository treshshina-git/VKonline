# VKVideo Telegram Bot (aiogram 3 + Railway)

Бот для Telegram, который по команде **`GoGoGo`**:
1) делает GET-запрос к серверу (через единую точку входа `https://apidev.live.vkvideo.ru/`),
2) возвращает пользователю **список в виде inline-кнопок**,
3) при нажатии кнопки делает новый GET-запрос,
4) отправляет пользователю детали **обычным сообщением** (со ссылками на активные позиции).

> Важно: точные URL/параметры GET и формат ответов зависят от вашего API. В коде ниже предусмотрены места для подстановки путей/полей. Всё сделано так, чтобы вам оставалось только указать endpoints и маппинг полей.

---

## 1) Требования
- Python 3.11+
- Telegram bot token (BotFather)
- Доступ к VK для получения access token по вашему описанию

---

## 2) Как запустить локально

### Установка
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

### Переменные окружения
Создайте `.env` (или задайте env переменные в командной строке):

```env
TELEGRAM_BOT_TOKEN=PUT_TELEGRAM_TOKEN

# Единственная точка входа (Dev)
API_BASE_URL=https://apidev.live.vkvideo.ru

# OAuth endpoint для получения токена VK
VK_OAUTH_TOKEN_URL=https://api.live.vkvideo.ru/oauth/server/token

# VK auth (нужно подставить реальные значения из наличия у вас)
VK_CLIENT_ID=PUT_CLIENT_ID
VK_CLIENT_SECRET=PUT_CLIENT_SECRET
VK_REDIRECT_URI=PUT_REDIRECT_URI
VK_ACCESS_TOKEN=PUT_VK_ACCESS_TOKEN

# Telegram: порт не нужен (long polling по умолчанию)
# Если захотите webhook — добавим позже.
```

> Примечание: в вашем описании есть "логины и пароли". В коде используется модель OAuth server/token. Если вам нужно передавать именно username/password — скажите, и я адаптирую запрос к `VK_OAUTH_TOKEN_URL`.

### Запуск
```bash
python -m src.main
```

---

## 3) Деплой на Railway

### Docker
Railway может деплоить Docker напрямую.

1) Откройте Railway → New Project → Deploy from GitHub.
2) Укажите переменные окружения в разделе **Environment**:
   - `TELEGRAM_BOT_TOKEN`
   - `API_BASE_URL`
   - `VK_OAUTH_TOKEN_URL`
   - `VK_CLIENT_ID`, `VK_CLIENT_SECRET`, `VK_REDIRECT_URI`
   - `VK_ACCESS_TOKEN` (или те параметры, которые реально требует ваш `server/token`)

### Запуск контейнера
Railway запустит контейнер через `CMD` в `Dockerfile`.

---

## 4) Изменения под ваш API

В коде есть отдельные функции:
- `src/services/api_client.py` — получение токена
- `src/services/api_client.py` — получение списка
- `src/services/api_client.py` — получение детали по выбранной позиции

В них нужно указать:
- endpoint для списка (после `API_BASE_URL`)
- endpoint для детали (после `API_BASE_URL`)
- параметры (какой идентификатор передавать)
- какие поля брать для:
  - `text` кнопки
  - `callback_data`
  - текста ответа и ссылок

После этого бот начнёт работать без дополнительных правок.

---

## 5) Безопасность
Не коммитьте токены и пароли в репозиторий. Используйте Railway env.


