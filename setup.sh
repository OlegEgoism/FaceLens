#!/bin/bash
# Устанавливаем зависимости
pip install -r requirements.txt

# Применяем миграции
python manage.py makemigrations
python manage.py migrate

# Запускаем сервер
python manage.py runserver
