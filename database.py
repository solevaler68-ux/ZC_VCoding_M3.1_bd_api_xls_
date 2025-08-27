import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с PostgreSQL базой данных"""
    
    def __init__(self):
        """Инициализация параметров подключения из переменных окружения"""
        self.host = os.getenv('DB_HOST')
        self.port = os.getenv('DB_PORT', '5432')
        self.database = os.getenv('DB_NAME')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        
        # Проверка наличия обязательных параметров
        if not all([self.host, self.database, self.user, self.password]):
            raise ValueError("Не все параметры подключения к БД указаны в переменных окружения")
    
    @contextmanager
    def connect(self):
        """Контекстный менеджер для работы с соединением БД"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                options='-c client_encoding=utf8'
            )
            conn.autocommit = False
            logger.info("Соединение с БД установлено")
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                try:
                    conn.close()
                    logger.info("Соединение с БД закрыто")
                except psycopg2.Error as e:
                    logger.error(f"Ошибка при закрытии соединения: {e}")
    
    def test_connection(self) -> bool:
        """Проверка соединения с БД"""
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Ошибка при проверке соединения: {e}")
            return False
    
    def add_user(self, full_name: str, summ: float = 0.0, 
                 card_number: int = 0, birthday: str = None) -> Optional[int]:
        """
        Добавление нового пользователя в БД
        
        Args:
            full_name: Полное имя пользователя
            summ: Сумма (по умолчанию 0)
            card_number: Номер карты (по умолчанию 0)
            birthday: Дата рождения в формате YYYY-MM-DD
            
        Returns:
            ID добавленного пользователя или None в случае ошибки
        """
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    # SQL запрос с параметризацией
                    query = """
                        INSERT INTO users (full_name, summ, card_number, birthday)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """
                    
                    cursor.execute(query, (full_name, summ, card_number, birthday))
                    user_id = cursor.fetchone()[0]
                    
                    conn.commit()
                    logger.info(f"Пользователь {full_name} добавлен с ID: {user_id}")
                    return user_id
                    
        except psycopg2.Error as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            return None
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """Получение пользователя по ID"""
        try:
            with self.connect() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except psycopg2.Error as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None
    
    def get_all_users(self) -> list:
        """Получение всех пользователей"""
        try:
            with self.connect() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT * FROM users ORDER BY id")
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
        except psycopg2.Error as e:
            logger.error(f"Ошибка при получении пользователей: {e}")
            return []

    def get_next_card_number(self) -> int:
        """
        Получение следующего номера карты (максимальный существующий + 1)
        Если таблица пуста, возвращает 1

        Returns:
            Следующий уникальный номер карты
        """
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COALESCE(MAX(card_number), 0) FROM users")
                    max_card_number = cursor.fetchone()[0]
                    return max_card_number + 1
        except psycopg2.Error as e:
            logger.error(f"Ошибка при получении следующего номера карты: {e}")
            return 1