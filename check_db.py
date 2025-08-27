#!/usr/bin/env python3
import sqlite3

def check_database():
    """Проверка структуры базы данных SQLite"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Получить схему таблицы users
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
        result = cursor.fetchone()

        if result:
            print("=== Структура таблицы users ===")
            print(result[0])
        else:
            print("Таблица users не найдена")

        # Показать все таблицы в базе данных
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n=== Все таблицы в БД ===")
        for table in tables:
            print(f"- {table[0]}")

        # Проверить количество записей
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        print(f"\n=== Статистика ===")
        print(f"Всего записей: {count}")

        if count > 0:
            # Показать первые несколько записей
            cursor.execute("SELECT id, full_name, card_number, synced_with_pg, created_at FROM users LIMIT 5")
            rows = cursor.fetchall()

            print("\n=== Первые записи ===")
            print("ID | Full Name | Card Number | Synced | Created")
            print("-" * 60)
            for row in rows:
                synced = "Да" if row[3] else "Нет"
                print(f"{row[0]:2d} | {row[1]:15s} | {row[2]:11d} | {synced:6s} | {row[4]}")

        conn.close()

    except sqlite3.Error as e:
        print(f"Ошибка SQLite: {e}")
    except Exception as e:
        print(f"Общая ошибка: {e}")

if __name__ == "__main__":
    check_database()
