#!/bin/bash

echo "========================================"
echo "    Telegram Bot - Запуск"
echo "========================================"
echo

echo "[1/4] Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo "ОШИБКА: Python3 не установлен"
    exit 1
fi

python3 --version

echo
echo "[2/4] Установка зависимостей..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ОШИБКА: Не удалось установить зависимости"
    exit 1
fi

echo
echo "[3/4] Тестирование подключения к БД..."
python3 test_db.py
if [ $? -ne 0 ]; then
    echo "ПРЕДУПРЕЖДЕНИЕ: Проблемы с подключением к БД"
    echo "Бот может работать некорректно"
    read -p "Нажмите Enter для продолжения..."
fi

echo
echo "[4/4] Запуск бота..."
echo "Для остановки бота нажмите Ctrl+C"
echo

python3 main.py
