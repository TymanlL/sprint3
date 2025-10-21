import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Загружаем переменные окружения из .env файла
load_dotenv()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start - спрашивает как дела."""
    await update.message.reply_text('Привет! Как дела?')

def main() -> None:
    """Запуск бота."""
    # Получаем токен из переменной окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not token:
        print("Ошибка: не найден TELEGRAM_BOT_TOKEN в переменных окружения!")
        print("Создайте файл .env и добавьте туда: TELEGRAM_BOT_TOKEN=ваш_токен")
        return

    # Создаем приложение
    application = Application.builder().token(token).build()

    # Добавляем обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # Запускаем бота
    print("Бот запущен! Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
