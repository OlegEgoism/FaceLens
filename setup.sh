#!/bin/bash

# Создаём файл .env с базовыми переменными окружения
cat > .env <<EOF
# Подключение к базе данных
POSTGRES_DB=your_database_name
POSTGRES_USER=your_database_user
POSTGRES_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432
EOF

echo ".env файл создан с настройками базы данных."

# Устанавливаем зависимости
pip install -r requirements.txt

# Применяем миграции
python manage.py makemigrations
python manage.py migrate

# Запускаем сервер
python manage.py runserver
