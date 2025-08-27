import os
import logging
import re
from datetime import datetime
from dotenv import load_dotenv
import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from database import Database
from excel_manager import get_excel_manager
from sqlite_manager import get_sqlite_manager

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

# Инициализация модуля резервного копирования в Excel
try:
    excel_manager = get_excel_manager()
    logger.info("Модуль резервного копирования Excel инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации модуля Excel: {e}")
    excel_manager = None

# SQLite менеджер будет создаваться по требованию для каждого запроса
# Это обеспечивает потокобезопасность


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

        # Создаем локальный экземпляр SQLite менеджера для проверки
        sqlite_manager = get_sqlite_manager()

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

        # Создаем локальный экземпляр SQLite менеджера
        sqlite_manager = get_sqlite_manager()

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

            # Генерируем следующий номер карты на основе существующих в SQLite
            all_users = sqlite_manager.get_all_users()
            existing_card_numbers = {user['card_number'] for user in all_users if user['card_number']}
            card_number = max(existing_card_numbers) + 1 if existing_card_numbers else 1

            # Сохраняем данные только в SQLite
            birthday_str = birthday_date.strftime('%Y-%m-%d')
            user_data = {
                "full_name": fullname,
                "summ": 0.0,
                "card_number": card_number,
                "birthday": birthday_str
            }

            user_id_db = sqlite_manager.add_user(user_data)

            if user_id_db is None:
                bot.reply_to(message, "❌ Произошла техническая ошибка при сохранении данных. Попробуйте позже.")
                logger.error(f"Не удалось сохранить пользователя {fullname} в SQLite")
            else:
                bot.reply_to(message, f"✅ Данные сохранены локально!\n\n📋 Ваш номер анкеты: {card_number}\n\n💡 Для синхронизации с облаком используйте /sync_pg")
                logger.info(f"Пользователь {user_id} успешно сохранил анкету в SQLite с номером: {card_number}")

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


@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Обработчик команды /stats - статистика синхронизации"""
    try:
        user_id = message.from_user.id

        # Создаем локальный экземпляр SQLite менеджера
        sqlite_manager = get_sqlite_manager()

        # Получаем статистику синхронизации
        sync_stats = sqlite_manager.get_sync_stats()

        info_text = f"""
📊 Статистика синхронизации:

🗄️ Основное хранилище (SQLite):
👥 Всего пользователей: {sync_stats['total_users']}
✅ Синхронизировано: {sync_stats['synced_users']}
⏳ Ожидают синхронизации: {sync_stats['unsynced_users']}
📈 Процент синхронизации: {sync_stats['sync_percentage']}%

🌐 Статус подключений:
PostgreSQL: {"✅ Подключен" if db else "❌ Отключен"}
Excel: {"✅ Подключен" if excel_manager else "❌ Отключен"}
        """

        bot.reply_to(message, info_text.strip())
        logger.info(f"Пользователь {user_id} запросил статистику синхронизации")

    except Exception as e:
        logger.error(f"Ошибка в обработчике /stats: {e}")
        bot.reply_to(message, "Произошла ошибка при получении статистики.")


@bot.message_handler(commands=['backup'])
def backup_command(message):
    """Обработчик команды /backup - информация о резервной копии"""
    try:
        user_id = message.from_user.id

        if not excel_manager:
            bot.reply_to(message, "❌ Модуль резервного копирования не инициализирован")
            return

        # Получаем информацию о резервной копии
        backup_info = excel_manager.get_backup_info()

        if "error" in backup_info:
            bot.reply_to(message, f"❌ Ошибка получения информации о резервной копии: {backup_info['error']}")
            return

        # Формируем сообщение с информацией
        info_text = f"""
📊 Информация о резервной копии:

📁 Файл: {backup_info['file_path']}
📈 Существует: {"✅ Да" if backup_info['file_exists'] else "❌ Нет"}
📏 Размер: {backup_info['file_size']} байт
👥 Всего записей: {backup_info['total_records']}

🔄 Автоматическое резервное копирование: {"✅ Активно" if excel_manager else "❌ Отключено"}
        """

        # Добавляем информацию о последнем изменении если файл существует
        if backup_info['last_modified']:
            from datetime import datetime
            last_modified_str = datetime.fromtimestamp(backup_info['last_modified']).strftime('%Y-%m-%d %H:%M:%S')
            info_text += f"🕒 Последнее изменение: {last_modified_str}"

        bot.reply_to(message, info_text.strip())
        logger.info(f"Пользователь {user_id} запросил информацию о резервной копии")

    except Exception as e:
        logger.error(f"Ошибка в обработчике /backup: {e}")
        bot.reply_to(message, "Произошла ошибка при получении информации о резервной копии.")


@bot.message_handler(commands=['sync_pg'])
def sync_pg_command(message):
    """Обработчик команды /sync_pg - синхронизация с PostgreSQL"""
    try:
        user_id = message.from_user.id

        # Создаем локальный экземпляр SQLite менеджера
        sqlite_manager = get_sqlite_manager()

        if not db:
            bot.reply_to(message, "❌ Модуль работы с PostgreSQL не инициализирован")
            return

        # Получаем несинхронизированных пользователей
        unsynced_users = sqlite_manager.get_unsynced_users()

        if not unsynced_users:
            bot.reply_to(message, "ℹ️ Все данные уже синхронизированы с PostgreSQL")
            return

        # Синхронизируем пользователей с PostgreSQL
        success_count = 0
        error_count = 0
        synced_ids = []

        bot.reply_to(message, f"🔄 Начинаю синхронизацию {len(unsynced_users)} записей с PostgreSQL...")

        for user in unsynced_users:
            try:
                # Преобразуем данные для PostgreSQL
                pg_user_data = {
                    "full_name": user["full_name"],
                    "summ": user["summ"],
                    "card_number": user["card_number"],
                    "birthday": user["birthday"]
                }

                # Добавляем в PostgreSQL
                pg_user_id = db.add_user(**pg_user_data)

                if pg_user_id is not None:
                    success_count += 1
                    synced_ids.append(user["id"])
                    logger.info(f"Пользователь {user['full_name']} (ID: {user['id']}) синхронизирован с PostgreSQL")
                else:
                    error_count += 1
                    logger.error(f"Не удалось синхронизировать пользователя {user['full_name']} (ID: {user['id']}) с PostgreSQL")

            except Exception as e:
                error_count += 1
                logger.error(f"Ошибка синхронизации пользователя {user['full_name']} (ID: {user['id']}): {e}")

        # Отмечаем успешно синхронизированных пользователей в SQLite
        if synced_ids:
            if sqlite_manager.mark_users_synced(synced_ids):
                logger.info(f"Отмечено {len(synced_ids)} пользователей как синхронизированные")
            else:
                logger.error("Не удалось отметить пользователей как синхронизированные")

        # Формируем отчет
        total_processed = success_count + error_count
        report_text = f"""
🔄 Синхронизация с PostgreSQL завершена:

✅ Успешно синхронизировано: {success_count} записей
❌ Ошибок синхронизации: {error_count} записей
📊 Всего обработано: {total_processed} записей

📈 Статус: {len(unsynced_users) - success_count} записей ожидают повторной синхронизации
        """

        bot.reply_to(message, report_text.strip())
        logger.info(f"Пользователь {user_id} выполнил синхронизацию с PostgreSQL: {success_count}/{total_processed} успешно")

    except Exception as e:
        logger.error(f"Ошибка в обработчике /sync_pg: {e}")
        bot.reply_to(message, "Произошла ошибка при синхронизации с PostgreSQL. Попробуйте позже.")


@bot.message_handler(commands=['sync_excel'])
def sync_excel_command(message):
    """Обработчик команды /sync_excel - синхронизация с Excel"""
    try:
        user_id = message.from_user.id

        # Создаем локальный экземпляр SQLite менеджера
        sqlite_manager = get_sqlite_manager()

        if not excel_manager:
            bot.reply_to(message, "❌ Модуль Excel не инициализирован")
            return

        # Получаем все данные из SQLite
        all_users = sqlite_manager.get_all_users()

        if not all_users:
            bot.reply_to(message, "ℹ️ В базе данных нет данных для синхронизации")
            return

        # Очищаем Excel файл
        if not excel_manager.clear_backup():
            bot.reply_to(message, "❌ Ошибка при очистке Excel файла")
            return

        # Добавляем все данные в Excel
        success_count = 0
        error_count = 0

        for user in all_users:
            try:
                # Преобразуем данные для Excel
                excel_user_data = {
                    "id": user["id"],
                    "full_name": user["full_name"],
                    "summ": user["summ"],
                    "card_number": user["card_number"],
                    "birthday": user["birthday"]
                }

                if excel_manager.add_user(excel_user_data):
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Ошибка синхронизации пользователя {user['full_name']} (ID: {user['id']}) с Excel: {e}")

        # Формируем отчет
        total_processed = success_count + error_count
        report_text = f"""
🔄 Синхронизация с Excel завершена:

✅ Успешно синхронизировано: {success_count} записей
❌ Ошибок синхронизации: {error_count} записей
📊 Всего обработано: {total_processed} записей

📁 Excel-файл обновлен: {excel_manager.file_path}
        """

        bot.reply_to(message, report_text.strip())
        logger.info(f"Пользователь {user_id} выполнил синхронизацию с Excel: {success_count}/{total_processed} успешно")

    except Exception as e:
        logger.error(f"Ошибка в обработчике /sync_excel: {e}")
        bot.reply_to(message, "Произошла ошибка при синхронизации с Excel. Попробуйте позже.")


@bot.message_handler(commands=['clear_backup'])
def clear_backup_command(message):
    """Обработчик команды /clear_backup - очистка резервной копии"""
    try:
        user_id = message.from_user.id

        if not excel_manager:
            bot.reply_to(message, "❌ Модуль резервного копирования не инициализирован")
            return

        # Получаем информацию о текущем состоянии
        backup_info = excel_manager.get_backup_info()
        current_records = backup_info.get("total_records", 0)

        if current_records == 0:
            bot.reply_to(message, "ℹ️ Резервная копия уже пуста")
            return

        # Очищаем резервную копию
        if excel_manager.clear_backup():
            bot.reply_to(message, f"✅ Резервная копия очищена!\n\n🗑️ Удалено записей: {current_records}")
            logger.info(f"Пользователь {user_id} очистил резервную копию ({current_records} записей)")
        else:
            bot.reply_to(message, "❌ Ошибка при очистке резервной копии")
            logger.error(f"Не удалось очистить резервную копию для пользователя {user_id}")

    except Exception as e:
        logger.error(f"Ошибка в обработчике /clear_backup: {e}")
        bot.reply_to(message, "Произошла ошибка при очистке резервной копии.")


@bot.message_handler(commands=['sync_backup'])
def sync_backup_command(message):
    """Обработчик команды /sync_backup - синхронизация всех данных из БД в Excel"""
    try:
        user_id = message.from_user.id

        if not db:
            bot.reply_to(message, "❌ Модуль работы с БД не инициализирован")
            return

        if not excel_manager:
            bot.reply_to(message, "❌ Модуль резервного копирования не инициализирован")
            return

        # Получаем всех пользователей из БД
        all_users = db.get_all_users()

        if not all_users:
            bot.reply_to(message, "ℹ️ В базе данных нет пользователей для резервного копирования")
            return

        # Получаем существующие ID из Excel файла
        existing_ids = excel_manager.get_existing_ids()
        logger.info(f"Найдено {len(existing_ids)} существующих записей в Excel файле")

        # Фильтруем только новые записи
        new_users = []
        skipped_users = 0

        for user in all_users:
            user_id_db = user["id"]
            if user_id_db in existing_ids:
                skipped_users += 1
                logger.debug(f"Запись пользователя ID {user_id_db} уже существует в Excel, пропускаем")
            else:
                new_users.append(user)

        if not new_users:
            bot.reply_to(message, f"ℹ️ Все записи из базы данных уже существуют в резервной копии!\n\n📊 Всего в БД: {len(all_users)}\n📁 Уже в Excel: {len(existing_ids)}\n⏭️ Пропущено: {skipped_users}")
            return

        # Синхронизируем только новые данные в Excel
        success_count = 0
        error_count = 0

        for user in new_users:
            try:
                # Преобразуем данные в нужный формат
                user_data = {
                    "id": user["id"],
                    "full_name": user["full_name"],
                    "summ": user["summ"],
                    "card_number": user["card_number"],
                    "birthday": user["birthday"].strftime('%Y-%m-%d') if hasattr(user["birthday"], 'strftime') else str(user["birthday"])
                }

                if excel_manager.add_user(user_data):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Ошибка синхронизации пользователя {user.get('full_name', 'Unknown')}: {e}")
                error_count += 1

        # Формируем отчет
        total_processed = success_count + error_count
        report_text = f"""
🔄 Синхронизация завершена:

✅ Новых записей добавлено: {success_count}
❌ Ошибок при добавлении: {error_count}
⏭️ Пропущено (уже существуют): {skipped_users}
📊 Всего обработано: {total_processed}

📁 Резервная копия обновлена в файле: {excel_manager.file_path}
📈 Теперь в Excel: {len(existing_ids) + success_count} записей
        """

        bot.reply_to(message, report_text.strip())
        logger.info(f"Пользователь {user_id} выполнил синхронизацию резервной копии: добавлено {success_count}, пропущено {skipped_users}")

    except Exception as e:
        logger.error(f"Ошибка в обработчике /sync_backup: {e}")
        bot.reply_to(message, "Произошла ошибка при синхронизации резервной копии.")


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

🗄️ Команды основного хранилища:
/stats - Статистика синхронизации и состояния хранилищ

🔄 Команды синхронизации:
/sync_pg - Синхронизировать несинхронизированные данные с PostgreSQL
/sync_excel - Обновить Excel файл всеми данными из SQLite

⚙️ Команды резервного копирования:
/backup - Информация о резервной копии в Excel
/clear_backup - Очистить резервную копию в Excel

⚙️ Дополнительные команды:
/cancel - Отменить заполнение анкеты (во время заполнения)

📋 Архитектура хранения данных:
1️⃣ SQLite (database.db) - основное локальное хранилище
2️⃣ PostgreSQL (облако) - синхронизированная копия
3️⃣ Excel (backup.xlsx) - резервная копия

📋 Как заполнить анкету:
1. Введите /form
2. Укажите ваше ФИО (минимум 2 слова)
3. Укажите дату рождения в формате ДД.ММ.ГГГГ
4. Данные сохранятся локально в SQLite
5. Используйте /sync_pg для синхронизации с облаком

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
        # Корректное завершение работы модулей
        if excel_manager:
            try:
                excel_manager.close()
                logger.info("Модуль Excel корректно завершен")
            except Exception as e:
                logger.error(f"Ошибка при завершении модуля Excel: {e}")

        logger.info("👋 Бот завершил работу")


if __name__ == "__main__":
    main()
