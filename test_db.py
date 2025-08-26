#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для тестирования подключения к базе данных
"""

import os
import sys
from dotenv import load_dotenv
from database import Database

def test_database_connection():
    """Тестирование подключения к базе данных"""
    print("🔍 Тестирование подключения к базе данных...")
    
    # Загрузка переменных окружения
    load_dotenv()
    
    # Проверка наличия переменных окружения
    required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        print("📝 Создайте файл .env на основе env.template")
        return False
    
    try:
        # Инициализация модуля БД
        db = Database()
        print("✅ Модуль БД инициализирован успешно")
        
        # Тест подключения
        if db.test_connection():
            print("✅ Подключение к БД установлено успешно")
            
            # Тест добавления пользователя
            print("🧪 Тестирование добавления пользователя...")
            user_id = db.add_user(
                full_name="Тестовый Пользователь",
                summ=100.50,
                card_number=12345,
                birthday="1990-01-01"
            )
            
            if user_id:
                print(f"✅ Пользователь добавлен с ID: {user_id}")
                
                # Получение добавленного пользователя
                user = db.get_user(user_id)
                if user:
                    print(f"📋 Получен пользователь: {user}")
                else:
                    print("❌ Не удалось получить пользователя")
            else:
                print("❌ Не удалось добавить пользователя")
            
            return True
        else:
            print("❌ Не удалось установить подключение к БД")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

def test_environment_variables():
    """Проверка переменных окружения"""
    print("\n🔧 Проверка переменных окружения:")
    
    load_dotenv()
    
    env_vars = {
        'BOT_TOKEN': os.getenv('BOT_TOKEN'),
        'DB_HOST': os.getenv('DB_HOST'),
        'DB_PORT': os.getenv('DB_PORT', '5432'),
        'DB_NAME': os.getenv('DB_NAME'),
        'DB_USER': os.getenv('DB_USER'),
        'DB_PASSWORD': os.getenv('DB_PASSWORD', '***')
    }
    
    for var, value in env_vars.items():
        if value:
            if 'PASSWORD' in var:
                print(f"  {var}: {'*' * len(value)}")
            else:
                print(f"  {var}: {value}")
        else:
            print(f"  {var}: ❌ НЕ УКАЗАН")

def main():
    """Основная функция"""
    print("🚀 Тестирование телеграм-бота и базы данных")
    print("=" * 50)
    
    # Проверка переменных окружения
    test_environment_variables()
    
    print("\n" + "=" * 50)
    
    # Тест подключения к БД
    if test_database_connection():
        print("\n🎉 Все тесты пройдены успешно!")
        print("✅ Бот готов к запуску")
    else:
        print("\n❌ Тесты не пройдены")
        print("🔧 Проверьте настройки и попробуйте снова")
        sys.exit(1)

if __name__ == "__main__":
    main()
