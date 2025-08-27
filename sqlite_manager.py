import sqlite3
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQLiteManager:
    """
    Класс для управления SQLite базой данных - основным хранилищем бота.

    Attributes:
        db_path (str): Путь к файлу базы данных SQLite
    """

    def __init__(self, db_path: str = None):
        """
        Инициализация менеджера SQLite.

        Args:
            db_path (str): Путь к файлу базы данных
        """
        # Если путь не указан, используем database.db в корне проекта
        if db_path is None:
            import os
            self.db_path = os.path.join(os.getcwd(), "database.db")
        else:
            self.db_path = db_path

        self.initialize_database()
        logger.info(f"SQLite база данных инициализирована: {self.db_path}")

    def _get_connection(self):
        """Получить новое соединение с базой данных для текущего потока."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row  # Для получения результатов как словарей
        return connection

    def initialize_database(self) -> bool:
        """
        Инициализировать базу данных - создать таблицу users если она не существует.

        Returns:
            bool: True если инициализация успешна
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Создаем таблицу users с полем для отслеживания синхронизации
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        full_name TEXT NOT NULL,
                        summ REAL DEFAULT 0.0,
                        card_number INTEGER,
                        birthday TEXT,
                        synced_with_pg BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        synced_at TIMESTAMP NULL
                    )
                ''')

                # Создаем индексы для оптимизации
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_synced ON users(synced_with_pg)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_card_number ON users(card_number)')

                conn.commit()
                logger.info("Таблица users успешно создана/инициализирована в SQLite")
                return True

        except sqlite3.Error as e:
            logger.error(f"Ошибка инициализации базы данных SQLite: {e}")
            return False

    def add_user(self, user_data: Dict) -> Optional[int]:
        """
        Добавить нового пользователя в SQLite базу данных.

        Args:
            user_data (dict): Данные пользователя в формате:
                {
                    "full_name": str,
                    "summ": float (опционально, по умолчанию 0.0),
                    "card_number": int,
                    "birthday": str (формат YYYY-MM-DD)
                }

        Returns:
            Optional[int]: ID добавленного пользователя или None при ошибке
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # SQL запрос с параметризацией
                query = '''
                    INSERT INTO users (full_name, summ, card_number, birthday, synced_with_pg)
                    VALUES (?, ?, ?, ?, ?)
                '''

                cursor.execute(query, (
                    user_data["full_name"],
                    user_data.get("summ", 0.0),
                    user_data["card_number"],
                    user_data["birthday"],
                    False  # synced_with_pg всегда False при создании
                ))

                user_id = cursor.lastrowid
                conn.commit()

                logger.info(f"Пользователь {user_data['full_name']} добавлен в SQLite с ID: {user_id}")
                return user_id

        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления пользователя в SQLite: {e}")
            return None
        except KeyError as e:
            logger.error(f"Отсутствует обязательное поле в данных пользователя: {e}")
            return None

    def get_all_users(self) -> List[Dict]:
        """
        Получить всех пользователей из базы данных.

        Returns:
            List[Dict]: Список всех пользователей
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users ORDER BY id")

                users = []
                for row in cursor.fetchall():
                    users.append(dict(row))

                logger.debug(f"Получено {len(users)} пользователей из SQLite")
                return users

        except sqlite3.Error as e:
            logger.error(f"Ошибка получения пользователей из SQLite: {e}")
            return []

    def get_unsynced_users(self) -> List[Dict]:
        """
        Получить пользователей, которые еще не синхронизированы с PostgreSQL.

        Returns:
            List[Dict]: Список несинхронизированных пользователей
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE synced_with_pg = FALSE ORDER BY id")

                users = []
                for row in cursor.fetchall():
                    users.append(dict(row))

                logger.debug(f"Найдено {len(users)} несинхронизированных пользователей")
                return users

        except sqlite3.Error as e:
            logger.error(f"Ошибка получения несинхронизированных пользователей: {e}")
            return []

    def mark_users_synced(self, user_ids: List[int]) -> bool:
        """
        Отметить пользователей как синхронизированные с PostgreSQL.

        Args:
            user_ids (List[int]): Список ID пользователей для отметки

        Returns:
            bool: True если операция успешна
        """
        if not user_ids:
            return True

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Создаем плейсхолдеры для IN запроса
                placeholders = ','.join('?' * len(user_ids))
                query = f'''
                    UPDATE users
                    SET synced_with_pg = TRUE, synced_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                '''

                cursor.execute(query, user_ids)
                conn.commit()

                logger.info(f"Отмечено {cursor.rowcount} пользователей как синхронизированные")
                return True

        except sqlite3.Error as e:
            logger.error(f"Ошибка при отметке пользователей как синхронизированные: {e}")
            return False

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        Получить пользователя по ID.

        Args:
            user_id (int): ID пользователя

        Returns:
            Optional[Dict]: Данные пользователя или None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

                row = cursor.fetchone()
                return dict(row) if row else None

        except sqlite3.Error as e:
            logger.error(f"Ошибка получения пользователя по ID {user_id}: {e}")
            return None

    def get_sync_stats(self) -> Dict:
        """
        Получить статистику синхронизации.

        Returns:
            Dict: Статистика синхронизации
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Общее количество пользователей
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]

                # Количество синхронизированных
                cursor.execute("SELECT COUNT(*) FROM users WHERE synced_with_pg = TRUE")
                synced_users = cursor.fetchone()[0]

                # Количество несинхронизированных
                cursor.execute("SELECT COUNT(*) FROM users WHERE synced_with_pg = FALSE")
                unsynced_users = cursor.fetchone()[0]

                return {
                    "total_users": total_users,
                    "synced_users": synced_users,
                    "unsynced_users": unsynced_users,
                    "sync_percentage": round((synced_users / total_users * 100), 2) if total_users > 0 else 0
                }

        except sqlite3.Error as e:
            logger.error(f"Ошибка получения статистики синхронизации: {e}")
            return {
                "total_users": 0,
                "synced_users": 0,
                "unsynced_users": 0,
                "sync_percentage": 0
            }

    def close(self):
        """Закрыть менеджер базы данных."""
        # Теперь соединения создаются и закрываются автоматически для каждого запроса
        logger.info("Менеджер SQLite завершен")


def get_sqlite_manager(db_path: str = None) -> SQLiteManager:
    """
    Создать новый экземпляр SQLiteManager.
    Каждый вызов создает новый экземпляр для обеспечения
    потокобезопасности.

    Args:
        db_path (str): Путь к файлу базы данных

    Returns:
        SQLiteManager: Новый экземпляр менеджера
    """
    return SQLiteManager(db_path)
