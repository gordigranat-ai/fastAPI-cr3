# Контрольная работа №3 - Технологии разработки серверных приложений

**Студент:** [Коломоец Гордей Кириллович]  
**Группа:** [ЭФБО-09-24]

---

## Описание

FastAPI приложение с аутентификацией, авторизацией и CRUD операциями.

**Выполненные задания:** 6.2, 6.3, 6.4, 6.5, 7.1, 8.1, 8.2

---

## Установка и запуск

# Клонирование
git clone <url>
cd fastAPI-cr3

# Виртуальное окружение
python -m venv venv
venv\Scripts\activate 

# Зависимости
pip install -r requirements.txt

# Создать .env из примера
cp .env.example .env

# Запуск
uvicorn main:app --reload

# Переменные окружения (.env)
MODE=DEV
DOCS_USERNAME=admin
DOCS_PASSWORD=pass123
SECRET_KEY=supersecretkey123

# Тестирование

# 1. Basic Auth (Задание 6.2)

# Регистрация
curl -X POST http://localhost:8000/basic/register -H "Content-Type: application/json" -d "{\"username\": \"user1\", \"password\": \"pass123\"}"

# Логин
curl -u user1:pass123 http://localhost:8000/basic/login

# 2. JWT + Rate Limiting (Задание 6.4, 6.5)

# Регистрация
curl -X POST http://localhost:8000/register -H "Content-Type: application/json" -d "{\"username\": \"alice\", \"password\": \"qwerty123\"}"

# Логин (получить токен)
curl -X POST http://localhost:8000/login -H "Content-Type: application/json" -d "{\"username\": \"alice\", \"password\": \"qwerty123\"}"

# Защищённый ресурс
curl -H "Authorization: Bearer ТОКЕН" http://localhost:8000/protected_resource

# 3. CRUD Todo (Задание 8.1, 8.2)

# Создать
curl -X POST http://localhost:8000/todos -H "Authorization: Bearer ТОКЕН" -H "Content-Type: application/json" -d "{\"title\": \"Купить хлеб\"}"

# Получить
curl -H "Authorization: Bearer ТОКЕН" http://localhost:8000/todos/1

# Обновить
curl -X PUT http://localhost:8000/todos/1 -H "Authorization: Bearer ТОКЕН" -H "Content-Type: application/json" -d "{\"completed\": true}"

# Удалить (только admin)
curl -X DELETE http://localhost:8000/todos/1 -H "Authorization: Bearer ТОКЕН"

# 4. RBAC (Задание 7.1)

# Сделать пользователя админом (через SQLite)
sqlite3 app.db "UPDATE users SET role='admin' WHERE username='alice';"

# Доступ к админ-панели
curl -H "Authorization: Bearer ТОКЕН" http://localhost:8000/admin/dashboard

# 5. Документация (Задание 6.3)
DEV режим: http://localhost:8000/docs (логин/пароль из .env)

PROD режим: http://localhost:8000/docs → 404

# Структура проекта
├── main.py              # Основной код
├── requirements.txt     # Зависимости
├── .env.example         # Пример настроек
├── .gitignore           # Игнорируемые файлы
└── app.db               # SQLite БД (создаётся автоматически)
Основные эндпоинты
Метод	URL	Описание
POST	/basic/register	Регистрация (Basic)
GET	/basic/login	Вход (Basic)
POST	/register	Регистрация (JWT)
POST	/login	Вход (JWT)
GET	/protected_resource	Защищённый ресурс
GET	/admin/dashboard	Панель админа
POST	/todos	Создать задачу
GET	/todos/{id}	Получить задачу
PUT	/todos/{id}	Обновить задачу
DELETE	/todos/{id}	Удалить задачу
