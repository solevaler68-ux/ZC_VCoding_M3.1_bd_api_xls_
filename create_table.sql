-- SQL скрипт для создания таблицы users в PostgreSQL
-- Выполните этот скрипт в вашей БД на alwaysdata.com

-- Создание таблицы users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    summ REAL DEFAULT 0.0,
    card_number INTEGER DEFAULT 0,
    birthday DATE
);

-- Создание индекса для оптимизации поиска по имени
CREATE INDEX IF NOT EXISTS idx_users_full_name ON users(full_name);

-- Создание индекса для оптимизации поиска по номеру карты
CREATE INDEX IF NOT EXISTS idx_users_card_number ON users(card_number);

-- Добавление комментариев к таблице и полям
COMMENT ON TABLE users IS 'Таблица для хранения анкет пользователей';
COMMENT ON COLUMN users.id IS 'Уникальный идентификатор пользователя (автоинкремент)';
COMMENT ON COLUMN users.full_name IS 'Полное имя пользователя';
COMMENT ON COLUMN users.summ IS 'Сумма (по умолчанию 0.0)';
COMMENT ON COLUMN users.card_number IS 'Номер карты (по умолчанию 0)';
COMMENT ON COLUMN users.birthday IS 'Дата рождения пользователя';

-- Проверка создания таблицы
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position;
