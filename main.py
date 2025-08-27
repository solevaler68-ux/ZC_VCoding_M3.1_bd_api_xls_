import os
import logging
import re
from datetime import datetime
from dotenv import load_dotenv
import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
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


class FormStates(StatesGroup):
    """Состояния для ConversationHandler формы анкетирования"""
    ENTER_FULLNAME = State()
    ENTER_BIRTHDAY = State()

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
/form - заполнить анкету
/help - справка по командам

🚀 Для начала работы используйте команду /form
        """
        
        bot.reply_to(message, welcome_text.strip())
        logger.info(f"Пользователь {user_id} ({user_name}) запустил бота")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")


# ConversationHandler для формы анкетирования
@bot.message_handler(commands=['form'])
def form_command(message):
    """Обработчик команды /form - начало анкетирования"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name

        if not db:
            bot.reply_to(message, "❌ Модуль работы с БД не инициализирован. Попробуйте позже.")
            return

        # Начинаем диалог анкетирования
        bot.reply_to(message, "📋 Заполнение анкеты\n\nВведите ваше ФИО:")
        bot.set_state(message.from_user.id, FormStates.ENTER_FULLNAME, message.chat.id)
        logger.info(f"Пользователь {user_id} ({user_name}) начал заполнение анкеты")

    except Exception as e:
        logger.error(f"Ошибка в обработчике /form: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")


@bot.message_handler(state=FormStates.ENTER_FULLNAME)
def handle_fullname(message):
    """Обработчик ввода ФИО"""
    try:
        user_id = message.from_user.id
        fullname = message.text.strip()

        # Валидация ФИО - должно быть минимум 2 слова
        if not fullname or len(fullname.split()) < 2:
            bot.reply_to(message, "❌ ФИО должно содержать минимум 2 слова (имя и фамилия). Попробуйте снова:")
            return

        # Сохраняем ФИО в состоянии
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['fullname'] = fullname

        bot.reply_to(message, "✅ ФИО принято!\n\nВведите вашу дату рождения в формате ДД.ММ.ГГГГ (например, 31.12.2000):")
        bot.set_state(message.from_user.id, FormStates.ENTER_BIRTHDAY, message.chat.id)
        logger.info(f"Пользователь {user_id} ввел ФИО: {fullname}")

    except Exception as e:
        logger.error(f"Ошибка в обработчике ввода ФИО: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")
        bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(state=FormStates.ENTER_BIRTHDAY)
def handle_birthday(message):
    """Обработчик ввода даты рождения"""
    try:
        user_id = message.from_user.id
        birthday_text = message.text.strip()

        # Валидация формата даты (ДД.ММ.ГГГГ)
        date_pattern = r'^(\d{2})\.(\d{2})\.(\d{4})$'
        match = re.match(date_pattern, birthday_text)

        if not match:
            bot.reply_to(message, "❌ Неправильный формат даты. Используйте формат ДД.ММ.ГГГГ (например, 31.12.2000):")
            return

        day, month, year = map(int, match.groups())

        # Проверяем корректность даты
        try:
            birthday_date = datetime(year, month, day)
        except ValueError:
            bot.reply_to(message, "❌ Некорректная дата. Проверьте, что день и месяц существуют:")
            return

        # Проверяем, что дата не в будущем
        if birthday_date > datetime.now():
            bot.reply_to(message, "❌ Дата рождения не может быть в будущем. Введите корректную дату:")
            return

        # Получаем сохраненные данные
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            fullname = data.get('fullname')
            if not fullname:
                bot.reply_to(message, "❌ Ошибка данных. Начните заполнение анкеты заново командой /form")
                bot.delete_state(message.from_user.id, message.chat.id)
                return

            # Генерируем следующий номер карты
            card_number = db.get_next_card_number()
            if card_number is None:
                bot.reply_to(message, "❌ Ошибка генерации номера карты. Попробуйте позже.")
                bot.delete_state(message.from_user.id, message.chat.id)
                return

            # Сохраняем данные в БД
            birthday_str = birthday_date.strftime('%Y-%m-%d')
            user_id_db = db.add_user(
                full_name=fullname,
                summ=0.0,
                card_number=card_number,
                birthday=birthday_str
            )

            if user_id_db is None:
                bot.reply_to(message, "❌ Произошла техническая ошибка при сохранении данных. Попробуйте позже.")
                logger.error(f"Не удалось сохранить пользователя {fullname} в БД")
            else:
                bot.reply_to(message, f"✅ Анкета успешно сохранена!\n\n📋 Ваш номер анкеты: {card_number}")
                logger.info(f"Пользователь {user_id} успешно сохранил анкету с номером: {card_number}")

        # Завершаем диалог
        bot.delete_state(message.from_user.id, message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка в обработчике ввода даты рождения: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")
        bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(commands=['cancel'], state=[FormStates.ENTER_FULLNAME, FormStates.ENTER_BIRTHDAY])
def cancel_form(message):
    """Обработчик отмены заполнения анкеты"""
    try:
        user_id = message.from_user.id
        bot.reply_to(message, "❌ Заполнение анкеты отменено.")
        bot.delete_state(message.from_user.id, message.chat.id)
        logger.info(f"Пользователь {user_id} отменил заполнение анкеты")
    except Exception as e:
        logger.error(f"Ошибка в обработчике отмены: {e}")
        bot.reply_to(message, "Произошла ошибка.")


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

🚀 Основные команды:
/start - Запуск бота и приветствие
/form - Заполнение анкеты пользователя
/status - Проверка состояния подключения к БД
/help - Показать эту справку

⚙️ Дополнительные команды:
/cancel - Отменить заполнение анкеты (во время заполнения)

📋 Как заполнить анкету:
1. Введите /form
2. Укажите ваше ФИО (минимум 2 слова)
3. Укажите дату рождения в формате ДД.ММ.ГГГГ
4. Получите ваш уникальный номер анкеты

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


# Регистрация состояний для ConversationHandler
from telebot.custom_filters import StateFilter

# Добавляем фильтр состояний
bot.add_custom_filter(StateFilter(bot))


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
