# 🚀 Развертывание телеграм-бота

## 📋 Обзор развертывания

Данный проект можно развернуть на различных платформах:
- **Локальный сервер** - для разработки и тестирования
- **VPS/Хостинг** - для продакшена
- **Облачные платформы** - Heroku, Railway, Render
- **Контейнеризация** - Docker

## 🏠 Локальное развертывание

### Требования
- Python 3.7+
- pip
- Доступ к интернету

### Шаги
1. **Клонирование проекта**
   ```bash
   git clone <repository-url>
   cd SQLite
   ```

2. **Установка зависимостей**
   ```bash
   pip install -r requirements.txt
   ```

3. **Настройка переменных окружения**
   ```bash
   cp env.template .env
   # Отредактируйте .env файл
   ```

4. **Запуск**
   ```bash
   python main.py
   ```

## ☁️ Облачное развертывание

### Heroku

#### 1. Подготовка
```bash
# Установка Heroku CLI
# Создание Procfile
echo "worker: python main.py" > Procfile

# Создание runtime.txt
echo "python-3.9.18" > runtime.txt
```

#### 2. Развертывание
```bash
heroku create your-bot-name
heroku config:set BOT_TOKEN=your_token
heroku config:set DB_HOST=your_db_host
heroku config:set DB_NAME=your_db_name
heroku config:set DB_USER=your_db_user
heroku config:set DB_PASSWORD=your_db_password
git push heroku main
```

### Railway

#### 1. Подготовка
- Создайте аккаунт на railway.app
- Подключите GitHub репозиторий

#### 2. Настройка переменных
```bash
BOT_TOKEN=your_token
DB_HOST=your_db_host
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
```

#### 3. Автодеплой
Railway автоматически развернет проект при push в main ветку.

### Render

#### 1. Подготовка
- Создайте аккаунт на render.com
- Создайте новый Web Service

#### 2. Настройка
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`
- **Environment Variables**: добавьте все переменные из `.env`

## 🐳 Docker развертывание

### 1. Создание Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### 2. Создание docker-compose.yml
```yaml
version: '3.8'

services:
  bot:
    build: .
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - DB_HOST=${DB_HOST}
      - DB_PORT=${DB_PORT}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
    restart: unless-stopped
```

### 3. Запуск
```bash
docker-compose up -d
```

## 🖥️ VPS развертывание

### Ubuntu/Debian

#### 1. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

#### 2. Установка Python
```bash
sudo apt install python3 python3-pip python3-venv -y
```

#### 3. Создание пользователя
```bash
sudo adduser botuser
sudo usermod -aG sudo botuser
su - botuser
```

#### 4. Настройка проекта
```bash
cd /home/botuser
git clone <repository-url>
cd SQLite
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 5. Настройка systemd
```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Содержимое файла:
```ini
[Unit]
Description=Telegram Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/SQLite
Environment=PATH=/home/botuser/SQLite/venv/bin
ExecStart=/home/botuser/SQLite/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 6. Запуск сервиса
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## 🔧 Мониторинг и логи

### Логирование
```bash
# Просмотр логов systemd
sudo journalctl -u telegram-bot -f

# Просмотр логов приложения
tail -f /home/botuser/SQLite/bot.log
```

### Мониторинг
```bash
# Проверка статуса
sudo systemctl status telegram-bot

# Перезапуск
sudo systemctl restart telegram-bot

# Остановка
sudo systemctl stop telegram-bot
```

## 🚨 Безопасность

### Firewall
```bash
# UFW (Ubuntu)
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# iptables (CentOS/RHEL)
sudo systemctl enable firewalld
sudo systemctl start firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

### SSL/TLS
```bash
# Certbot для Let's Encrypt
sudo apt install certbot
sudo certbot --nginx -d yourdomain.com
```

## 📊 Масштабирование

### Горизонтальное масштабирование
- Используйте балансировщик нагрузки
- Разверните несколько экземпляров бота
- Настройте Redis для сессий

### Вертикальное масштабирование
- Увеличьте ресурсы VPS
- Оптимизируйте код
- Настройте кэширование

## 🔄 CI/CD

### GitHub Actions
```yaml
name: Deploy Bot

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Deploy to VPS
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.KEY }}
        script: |
          cd /home/botuser/SQLite
          git pull origin main
          sudo systemctl restart telegram-bot
```

## 📝 Чек-лист развертывания

### Перед развертыванием
- [ ] Все тесты пройдены
- [ ] Переменные окружения настроены
- [ ] База данных доступна
- [ ] Токен бота получен

### После развертывания
- [ ] Бот отвечает на команды
- [ ] Логирование работает
- [ ] Мониторинг настроен
- [ ] Автозапуск работает
- [ ] Безопасность настроена

## 🆘 Устранение неполадок

### Частые проблемы
1. **Бот не отвечает** - проверьте токен и логи
2. **Ошибки БД** - проверьте подключение и права доступа
3. **Проблемы с правами** - проверьте пользователя и права файлов
4. **Проблемы с сетью** - проверьте firewall и DNS

### Полезные команды
```bash
# Проверка статуса
sudo systemctl status telegram-bot

# Просмотр логов
sudo journalctl -u telegram-bot -n 50

# Проверка портов
sudo netstat -tlnp | grep :80

# Проверка процессов
ps aux | grep python
```

## 🎯 Рекомендации

### Продакшен
- Используйте VPS или облачные платформы
- Настройте мониторинг и логирование
- Настройте автозапуск и восстановление
- Регулярно обновляйте систему

### Разработка
- Используйте локальное развертывание
- Настройте hot reload
- Используйте виртуальные окружения
- Тестируйте перед деплоем
