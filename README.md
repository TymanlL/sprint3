# Telegram Бот

Простой Telegram бот, который приветствует пользователя при команде /start.

## Функционал

- При команде `/start` бот спрашивает "Привет! Как дела?"

## Установка и запуск

### 1. Создание бота в Telegram

1. Найдите бота [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям и получите токен бота
4. Сохраните токен - он понадобится для настройки

### 2. Установка зависимостей

```bash
# Создайте виртуальное окружение (рекомендуется)
python -m venv venv

# Активируйте виртуальное окружение
# На Linux/Mac:
source venv/bin/activate
# На Windows:
venv\Scripts\activate

# Установите зависимости
pip install -r requirements.txt
```

### 3. Настройка токена

Создайте файл `.env` в корне проекта:

```bash
cp .env.example .env
```

Откройте `.env` и замените `your_bot_token_here` на ваш токен от BotFather:

```
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 4. Запуск бота

```bash
python bot.py
```

После запуска бот будет работать. Найдите вашего бота в Telegram и отправьте команду `/start`.

### 5. Остановка бота

Нажмите `Ctrl+C` для остановки бота.

## Структура проекта

```
.
├── bot.py              # Основной файл бота
├── requirements.txt    # Зависимости Python
├── .env               # Файл с токеном (не добавляется в git)
├── .env.example       # Пример файла с токеном
├── .gitignore         # Игнорируемые файлы
└── README.md          # Документация
```

## Технологии

- Python 3.7+
- python-telegram-bot 20.7
- python-dotenv 1.0.0
