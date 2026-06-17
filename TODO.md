# TODO

## План
1. Создать структуру проекта aiogram 3: `src/`, `config/`, `handlers/`, `services/`.
2. Реализовать интеграцию Telegram-бота:
   - обработка команды `GoGoGo`;
   - вывод списка как inline-кнопки;
   - обработка нажатий кнопок (callback) и выдача подробностей пользователю.
3. Реализовать единый слой доступа к API через точку входа `https://apidev.live.vkvideo.ru/` и получение токена на `https://api.live.vkvideo.ru/oauth/server/token`.
4. Подготовить переменные окружения для секретов (Telegram token, VK credentials, base urls).
5. Добавить `Dockerfile` и `Procfile` (для Railway).
6. Добавить `requirements.txt` и `README.md` с инструкцией: запуск локально, деплой на Railway, настройка env.
7. (После написания кода) прогнать базовую проверку командой `python -m compileall`.

