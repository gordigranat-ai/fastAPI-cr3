import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

import jwt
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from passlib.context import CryptContext
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import os

load_dotenv()

MODE = os.getenv("MODE", "DEV")
DOCS_USERNAME = os.getenv("DOCS_USERNAME", "admin")
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "pass123")
SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def init_db():
    """Создаёт таблицы users и todos если их нет"""
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            completed INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

def get_db():
    """Возвращает соединение с БД"""
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row  
    return conn

class UserBase(BaseModel):
    username: str

class User(UserBase):
    password: str

class UserInDB(UserBase):
    hashed_password: str
    role: str = "user"

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class TodoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    completed: bool


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

basic_security = HTTPBasic(auto_error=False)
bearer_security = HTTPBearer(auto_error=False)

limiter = Limiter(key_func=get_remote_address)


def get_user_from_db(username: str) -> Optional[Dict]:
    """Ищет пользователя в базе по username"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, hashed_password, role FROM users WHERE username = ?",
        (username,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "username": row["username"],
            "hashed_password": row["hashed_password"],
            "role": row["role"]
        }
    return None

def save_user_to_db(username: str, hashed_password: str, role: str = "user") -> bool:
    """Сохраняет пользователя в базу"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
            (username, hashed_password, role)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def auth_user_basic(credentials: Optional[HTTPBasicCredentials] = Depends(basic_security)):
    """Зависимость для Basic Auth (Задание 6.2)"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    user = get_user_from_db(credentials.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    if not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return user

def create_access_token(data: dict) -> str:
    """Создаёт JWT токен (Задание 6.4)"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_jwt_token(token: str) -> Optional[str]:
    """Проверяет JWT токен и возвращает username"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        return username
    except jwt.PyJWTError:
        return None

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security)):
    """Зависимость для JWT аутентификации (Задание 6.4)"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    username = verify_jwt_token(token)
    
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user_from_db(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def require_role(required_role: str):
    """Фабрика зависимостей для проверки роли"""
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: insufficient permissions"
            )
        return current_user
    return role_checker


app = FastAPI(
    title="Контрольная работа №3",
    version="1.0.0",
    docs_url=None,    
    redoc_url=None,
    openapi_url=None
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def verify_docs_auth(credentials: HTTPBasicCredentials = Depends(basic_security)):
    """Проверяет логин/пароль для доступа к документации в DEV режиме"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    is_username_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        DOCS_USERNAME.encode("utf-8")
    )
    is_password_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        DOCS_PASSWORD.encode("utf-8")
    )
    
    if not (is_username_ok and is_password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

if MODE == "PROD":
    @app.get("/docs", include_in_schema=False)
    @app.get("/redoc", include_in_schema=False)
    @app.get("/openapi.json", include_in_schema=False)
    async def docs_disabled():
        raise HTTPException(status_code=404, detail="Documentation is disabled in PROD mode")

else:  
    @app.get("/docs", include_in_schema=False)
    async def custom_docs(auth: bool = Depends(verify_docs_auth)):
        return get_swagger_ui_html(openapi_url="/openapi.json", title="API Docs")
    
    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc(auth: bool = Depends(verify_docs_auth)):
        return get_redoc_html(openapi_url="/openapi.json", title="API ReDoc")
    
    @app.get("/openapi.json", include_in_schema=False)
    async def custom_openapi(auth: bool = Depends(verify_docs_auth)):
        return get_openapi(title=app.title, version=app.version, routes=app.routes)


@app.get("/")
def root():
    return {"message": "Контрольная работа №3 API", "mode": MODE}


@app.post("/basic/register", status_code=status.HTTP_201_CREATED)
def register_basic(user_data: User):
    """Регистрация пользователя для Basic Auth"""
    hashed = get_password_hash(user_data.password)
    success = save_user_to_db(user_data.username, hashed, "user")
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    return {"message": f"User {user_data.username} registered"}

@app.get("/basic/login")
def login_basic(user: dict = Depends(auth_user_basic)):
    """Логин через Basic Auth"""
    return {"message": f"Welcome, {user['username']}!"}


@app.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("1/minute")  # 1 запрос в минуту
def register_jwt(request: Request, user_data: User):
    """Регистрация пользователя (JWT)"""
    existing = get_user_from_db(user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists"
        )
    
    hashed = get_password_hash(user_data.password)
    save_user_to_db(user_data.username, hashed, "user")
    
    return {"message": "New user created"}

@app.post("/login")
@limiter.limit("5/minute")  
def login_jwt(request: Request, user_data: User):
    """Логин с выдачей JWT токена"""
    user = get_user_from_db(user_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization failed"
        )
    
    token = create_access_token(data={"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/protected_resource")
def protected_resource(user: dict = Depends(get_current_user)):
    """Защищённый ресурс (Задание 6.4)"""
    return {"message": f"Access granted to {user['username']}"}


@app.get("/admin/dashboard")
def admin_dashboard(user: dict = Depends(require_role("admin"))):
    """Только для администраторов"""
    return {"message": f"Admin dashboard. Welcome, {user['username']}!"}

@app.post("/admin/create")
def admin_create(user: dict = Depends(require_role("admin"))):
    """Создание ресурса (только admin)"""
    return {"message": "Resource created by admin"}


@app.post("/todos", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(todo: TodoCreate, user: dict = Depends(get_current_user)):
    """Создание задачи"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO todos (title, description, completed) VALUES (?, ?, 0)",
        (todo.title, todo.description)
    )
    conn.commit()
    todo_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
    row = cursor.fetchone()
    conn.close()
    
    return TodoResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        completed=bool(row["completed"])
    )

@app.get("/todos/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: int, user: dict = Depends(get_current_user)):
    """Получение задачи по ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    return TodoResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        completed=bool(row["completed"])
    )

@app.put("/todos/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: int, todo: TodoUpdate, user: dict = Depends(get_current_user)):
    """Обновление задачи"""
    conn = get_db()
    cursor = conn.cursor()
    
    fields = []
    values = []
    
    if todo.title is not None:
        fields.append("title = ?")
        values.append(todo.title)
    if todo.description is not None:
        fields.append("description = ?")
        values.append(todo.description)
    if todo.completed is not None:
        fields.append("completed = ?")
        values.append(1 if todo.completed else 0)
    
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(todo_id)
    query = f"UPDATE todos SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    
    cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    return TodoResponse(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        completed=bool(row["completed"])
    )

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int, user: dict = Depends(require_role("admin"))):
    """Удаление задачи (только admin)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo not found")
    
    conn.commit()
    conn.close()
    return {"message": f"Todo {todo_id} deleted"}

