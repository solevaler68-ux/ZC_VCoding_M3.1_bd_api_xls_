import os
import logging
from dotenv import load_dotenv
import telebot
from telebot import types
from database import Database

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot_token = os.getenv('BOT_TOKEN')
if not bot_token:
    raise ValueError("BOT_TOKEN не указан в переменных окружения")

bot = telebot.TeleBot(bot_token)

# Инициализация модуля работы с БД
try:
    db = Database()
    logger.info("Модуль работы с БД инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации модуля БД: {e}")
    db = None


@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработчик команды /start"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        welcome_text = f"""
👋 Привет, {user_name}!

Я бот для сбора анкет пользователей.

📋 Доступные команды:
/start - показать это сообщение
/form - заполнить анкету (в разработке)

Для начала работы используйте команду /form
        """
        
        bot.reply_to(message, welcome_text.strip())
        logger.info(f"Пользователь {user_id} ({user_name}) запустил бота")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")


@bot.message_handler(commands=['form'])
def form_command(message):
    """Обработчик команды /form (заглушка)"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        form_text = """
📋 Анкета пользователя

Функция заполнения анкеты находится в разработке.

В ближайшее время здесь будет доступна форма для ввода:
• Полного имени
• Суммы
• Номера карты  
• Даты рождения

Следите за обновлениями! 🚀
        """
        
        bot.reply_to(message, form_text.strip())
        logger.info(f"Пользователь {user_id} ({user_name}) запросил анкету")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /form: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")


@bot.message_handler(commands=['status'])
def status_command(message):
    """Обработчик команды /status для проверки состояния БД"""
    try:
        user_id = message.from_user.id
        
        if not db:
            bot.reply_to(message, "❌ Модуль работы с БД не инициализирован")
            return
        
        # Проверка соединения с БД
        if db.test_connection():
            status_text = "✅ Соединение с базой данных установлено"
        else:
            status_text = "❌ Ошибка соединения с базой данных"
        
        bot.reply_to(message, status_text)
        logger.info(f"Пользователь {user_id} проверил статус БД")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /status: {e}")
        bot.reply_to(message, "Произошла ошибка при проверке статуса.")


@bot.message_handler(commands=['help'])
def help_command(message):
    """Обработчик команды /help"""
    try:
        help_text = """
📚 Справка по командам бота:

/start - Запуск бота и приветствие
/form - Заполнение анкеты (в разработке)
/status - Проверка состояния подключения к БД
/help - Показать эту справку

🔧 Техническая поддержка:
Если возникли проблемы, обратитесь к администратору.
        """
        
        bot.reply_to(message, help_text.strip())
        logger.info(f"Пользователь {message.from_user.id} запросил справку")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /help: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Обработчик всех остальных сообщений"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        # Логируем все сообщения
        logger.info(f"Пользователь {user_id} ({user_name}): {message.text}")
        
        # Отвечаем информативным сообщением
        response = f"""
💬 Вы написали: "{message.text}"

Для работы с ботом используйте команды:
/start - запуск бота
/form - анкета (в разработке)
/help - справка
        """
        
        bot.reply_to(message, response.strip())
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике echo_all: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")


def check_database_connection():
    """Проверка соединения с БД при запуске"""
    if not db:
        logger.error("Модуль БД не инициализирован")
        return False
    
    try:
        if db.test_connection():
            logger.info("✅ Соединение с БД успешно установлено")
            return True
        else:
            logger.error("❌ Не удалось установить соединение с БД")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке соединения с БД: {e}")
        return False


def main():
    """Основная функция запуска бота"""
    try:
        logger.info("🚀 Запуск телеграм-бота...")
        
        # Проверка соединения с БД
        if not check_database_connection():
            logger.warning("⚠️ Бот запускается без подключения к БД")
        
        # Запуск бота
        logger.info("🤖 Бот запущен и готов к работе")
        logger.info("📱 Используйте Ctrl+C для остановки")
        
        bot.polling(none_stop=True, interval=0)
        
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        logger.info("👋 Бот завершил работу")


if __name__ == "__main__":
    main()
