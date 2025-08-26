@echo off
echo ========================================
echo    Telegram Bot - Запуск
echo ========================================
echo.

echo [1/4] Проверка Python...
python --version
if errorlevel 1 (
    echo ОШИБКА: Python не установлен или не добавлен в PATH
    pause
    exit /b 1
)

echo.
echo [2/4] Установка зависимостей...
pip install -r requirements.txt
if errorlevel 1 (
    echo ОШИБКА: Не удалось установить зависимости
    pause
    exit /b 1
)

echo.
echo [3/4] Тестирование подключения к БД...
python test_db.py
if errorlevel 1 (
    echo ПРЕДУПРЕЖДЕНИЕ: Проблемы с подключением к БД
    echo Бот может работать некорректно
    pause
)

echo.
echo [4/4] Запуск бота...
echo Для остановки бота нажмите Ctrl+C
echo.
python main.py

pause
