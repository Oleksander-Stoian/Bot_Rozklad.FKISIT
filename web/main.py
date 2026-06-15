import os
import asyncio
import json
import time
import hmac
import hashlib
from urllib.parse import parse_qsl
import redis
import pandas as pd
from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from aiogram import Bot
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI(title="Адмін Панель Коледжу (Telegram WebApp)", version="4.0")
templates = Jinja2Templates(directory="templates")

# Завантаження конфігурацій
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip().isdigit()]

# Облікові дані для входу через браузер (поряд із Telegram Mini App).
# ADMIN_PASS_HASH (sha256-hex) має пріоритет; якщо його нема — береться ADMIN_PASS.
# Якщо не задано ні те, ні те — парольний вхід вимкнено.
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "")
ADMIN_PASS_HASH = os.getenv("ADMIN_PASS_HASH", "")
WEB_ADMIN_SUBJECT = "webadmin"  # суб'єкт сесії для парольного входу (не Telegram ID)

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
bot_client = Bot(token=BOT_TOKEN) if BOT_TOKEN else None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_DOCKER = os.path.exists("/data")
EXCEL_PATH = "/data/rozklad_pro.xlsx" if IS_DOCKER else os.path.join(BASE_DIR, "rozklad_pro.xlsx")

COOKIE_NAME = "tg_webapp_session"

# Запасні колонки, якщо Excel недоступний на момент відкриття панелі.
# МАЮТЬ збігатися зі схемою rozklad_pro.xlsx, інакше Save запише структуру,
# яку планувальник бота не зможе фільтрувати (зокрема без колонки "Час").
DEFAULT_COLUMNS = ["Курс", "Група", "День", "Час", "Предмет", "Викладач", "Кабінет/Zoom", "Формат"]

# Секрет для підпису сесійних токенів. BOT_TOKEN відомий лише серверу,
# тож зловмисник не може підробити підпис без нього.
SESSION_SECRET = os.getenv("SESSION_SECRET") or BOT_TOKEN
SESSION_TTL = 86400  # секунд

class AuthPayload(BaseModel):
    initData: str

class SchedulePayload(BaseModel):
    data: List[Dict[str, str]]

def verify_telegram_data(init_data: str, bot_token: str) -> dict:
    """Перевіряє валідність даних і цифровий підпис Telegram WebApp"""
    if not bot_token:
        return None
    try:
        vals = dict(parse_qsl(init_data))
        hash_val = vals.pop('hash', None)
        if not hash_val:
            return None
        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(vals.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if computed_hash == hash_val:
            return json.loads(vals.get('user', '{}'))
    except Exception:
        pass
    return None

def _sign(payload: str) -> str:
    """HMAC-SHA256 підпис рядка секретом сесії"""
    return hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_session_token(user_id: int) -> str:
    """Створює підписаний токен сесії формату '<user_id>.<issued_at>.<sig>'"""
    payload = f"{user_id}.{int(time.time())}"
    return f"{payload}.{_sign(payload)}"


def check_session(request: Request) -> bool:
    """Перевіряє підписаний токен сесії: цілісність підпису, строк дії та права адміна.

    Раніше тут була константа 'active_admin' — будь-хто міг підробити куку
    й отримати доступ адміна без автентифікації. Тепер токен підписаний
    BOT_TOKEN-ом, тож підробити його без секрету неможливо.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token or not SESSION_SECRET:
        return False
    try:
        user_id_str, issued_str, sig = token.split(".")
        payload = f"{user_id_str}.{issued_str}"
    except ValueError:
        return False
    if not hmac.compare_digest(_sign(payload), sig):
        return False
    try:
        if int(issued_str) + SESSION_TTL < int(time.time()):
            return False
    except ValueError:
        return False
    # Парольний вхід через браузер
    if user_id_str == WEB_ADMIN_SUBJECT:
        return True
    # Telegram Mini App: суб'єкт — це Telegram ID, що має бути серед адмінів
    try:
        return int(user_id_str) in ADMIN_IDS
    except ValueError:
        return False


def verify_password(username: str, password: str) -> bool:
    """Перевіряє логін/пароль браузерного входу (порівняння у сталий час)."""
    if not hmac.compare_digest(username, ADMIN_USER):
        return False
    if ADMIN_PASS_HASH:
        digest = hashlib.sha256(password.encode()).hexdigest()
        return hmac.compare_digest(digest, ADMIN_PASS_HASH.strip().lower())
    if ADMIN_PASS:
        return hmac.compare_digest(password, ADMIN_PASS)
    return False  # пароль не налаштовано → вхід через браузер вимкнено

async def run_bg_broadcast(text: str, uids: list):
    """Фонова відправка розсилки з контролем спам-лімітів"""
    if not bot_client:
        return
    for uid in uids:
        try:
            await bot_client.send_message(chat_id=int(uid), text=f"📢 <b>ОГОЛОШЕННЯ:</b>\n\n{text}", parse_mode="HTML")
            await asyncio.sleep(0.05)
        except Exception:
            pass

@app.post("/api/auth")
async def api_auth(payload: AuthPayload):
    """Приймає initData, перевіряє підпис бота та створює сесійну куку"""
    user_data = verify_telegram_data(payload.initData, BOT_TOKEN)
    if not user_data:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Невалідний цифровий підпис Telegram!"})
    
    user_id = user_data.get("id")
    if not user_id or user_id not in ADMIN_IDS:
        return JSONResponse(status_code=403, content={"status": "error", "message": f"Ваш Telegram ID ({user_id}) відсутній у списку ADMIN_IDS проєкту!"})
    
    response = JSONResponse(content={"status": "success"})
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_session_token(user_id),
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL,
    )
    return response

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Сторінка входу логін/пароль (для браузера, без Telegram)."""
    if check_session(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": None})

@app.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    """Перевіряє облікові дані та видає підписану сесію (той самий механізм, що й Telegram)."""
    if not verify_password(username, password):
        return templates.TemplateResponse(
            request, "login.html",
            {"request": request, "error": "Невірний логін або пароль!"},
            status_code=401,
        )
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_session_token(WEB_ADMIN_SUBJECT),
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL,
    )
    return response

@app.get("/logout")
async def logout():
    """Вихід: гасить сесійну куку."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Головна сторінка. Якщо користувач не має куки — рендериться JS-скрипт автентифікації Telegram"""
    if check_session(request):
        try:
            users_count = len(list(r.scan_iter("user:*:role")))
        except Exception:
            users_count = "Помилка Redis"
        
        columns = []
        rows = []
        if os.path.exists(EXCEL_PATH):
            try:
                df = pd.read_excel(EXCEL_PATH, dtype=str)
                df = df.fillna("")
                columns = df.columns.tolist()
                rows = df.to_dict(orient="records")
            except Exception:
                pass
        if not columns:
            columns = list(DEFAULT_COLUMNS)

        return templates.TemplateResponse(request, "dashboard.html", {
            "request": request, 
            "users_count": users_count, 
            "columns": columns, 
            "rows": rows,
            "needs_auth": False,
            "alert": None
        })
    
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "needs_auth": True,
        "users_count": 0,
        "columns": [],
        "rows": [],
        "alert": None
    })

@app.post("/save-schedule")
async def save_schedule(payload: SchedulePayload, request: Request):
    if not check_session(request):
        raise HTTPException(status_code=401, detail="Не авторизовано")
    try:
        if not payload.data:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Таблиця порожня!"})
        df = pd.DataFrame(payload.data)
        df.to_excel(EXCEL_PATH, index=False)
        return {"status": "success", "message": "Зміни збережено в розклад розкладу Excel! Відправте /reload_schedule в бот."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/broadcast")
async def web_broadcast(background_tasks: BackgroundTasks, request: Request, text: str = Form(...)):
    if not check_session(request):
        return RedirectResponse(url="/", status_code=303)
    
    try:
        users_count = len(list(r.scan_iter("user:*:role")))
    except Exception:
        users_count = "Помилка Redis"
    
    columns = []
    rows = []
    if os.path.exists(EXCEL_PATH):
        try:
            df = pd.read_excel(EXCEL_PATH, dtype=str)
            df = df.fillna("")
            columns = df.columns.tolist()
            rows = df.to_dict(orient="records")
        except Exception:
            pass
    if not columns:
        columns = list(DEFAULT_COLUMNS)

    if not text.strip():
        return templates.TemplateResponse(request, "dashboard.html", {"request": request, "users_count": users_count, "columns": columns, "rows": rows, "needs_auth": False, "alert": {"type": "error", "text": "Текст оголошення не може бути пустим!"}})
    
    uids = []
    for key in r.scan_iter("user:*:role"):
        parts = key.split(":")
        if len(parts) >= 2:
            uids.append(parts[1])
            
    if not uids:
        return templates.TemplateResponse(request, "dashboard.html", {"request": request, "users_count": users_count, "columns": columns, "rows": rows, "needs_auth": False, "alert": {"type": "error", "text": "Немає активних юзерів у базі!"}})

    background_tasks.add_task(run_bg_broadcast, text, uids)
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request, 
        "users_count": users_count, 
        "columns": columns, 
        "rows": rows, 
        "needs_auth": False,
        "alert": {"type": "success", "text": f"📍 Веб-розсилку успішно запущено у фоні для {len(uids)} користувачів!"}
    })