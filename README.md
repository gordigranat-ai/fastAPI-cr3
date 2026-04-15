Контрольная работа номер 3

Студент: ваше имя
Группа: ваша группа

Установка и запуск

Клонировать репозиторий:
git clone ссылка-на-репозиторий
cd control-work-3

Создать виртуальное окружение:
python -m venv venv

Активировать окружение:
Windows: venv\Scripts\activate
Mac/Linux: source venv/bin/activate

Установить зависимости:
pip install -r requirements.txt

Создать файл .env из примера:
cp .env.example .env

Запустить сервер:
uvicorn main:app --reload
или
python -m uvicorn main:app --reload

Приложение запустится на http://localhost:8000

Тестирование

Задание 6.2 Basic Auth

Регистрация:
curl -X POST http://localhost:8000/basic/register -H "Content-Type: application/json" -d "{"username": "user1", "password": "pass123"}"

Логин:
curl -u user1:pass123 http://localhost:8000/basic/login

Задание 6.3 Отключение документации

В файле .env по умолчанию MODE=DEV. Документация доступна по адресу http://localhost:8000/docs с логином и паролем из .env (admin/pass123).

Если поменять в .env MODE=PROD и перезапустить сервер, то при открытии http://localhost:8000/docs вернется ошибка 404.

Задание 6.5 JWT и Rate Limiting

Регистрация:
curl -X POST http://localhost:8000/register -H "Content-Type: application/json" -d "{"username": "alice", "password": "qwerty"}"

Логин:
curl -X POST http://localhost:8000/login -H "Content-Type: application/json" -d "{"username": "alice", "password": "qwerty"}"

Ответ содержит access_token. Его нужно скопировать для следующих запросов.

Защищенный ресурс:
curl -H "Authorization: Bearer ПОЛУЧЕННЫЙ_ТОКЕН" http://localhost:8000/protected_resource

Ограничения по частоте запросов: register 1 запрос в минуту, login 5 запросов в минуту. При превышении вернется 429 ошибка.

Задание 7.1 RBAC роли

Обычный пользователь имеет роль user. Чтобы проверить админские функции, нужно вручную изменить роль в базе данных:

sqlite3 app.db
UPDATE users SET role = 'admin' WHERE username = 'alice';
.exit

После этого получить новый токен через login и проверить админские эндпоинты:

curl -H "Authorization: Bearer ТОКЕН" http://localhost:8000/admin/dashboard

Задание 8.2 CRUD для Todo

Создать задачу:
curl -X POST http://localhost:8000/todos -H "Authorization: Bearer ТОКЕН" -H "Content-Type: application/json" -d "{"title": "Купить хлеб"}"

Получить задачу:
curl -H "Authorization: Bearer ТОКЕН" http://localhost:8000/todos/1

Обновить задачу:
curl -X PUT http://localhost:8000/todos/1 -H "Authorization: Bearer ТОКЕН" -H "Content-Type: application/json" -d "{"completed": true}"

Удалить задачу (только admin):
curl -X DELETE -H "Authorization: Bearer ТОКЕН" http://localhost:8000/todos/1
