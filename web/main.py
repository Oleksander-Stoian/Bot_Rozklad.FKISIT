import os
import shutil
import asyncio
import json
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

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
bot_client = Bot(token=BOT_TOKEN) if BOT_TOKEN else None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_DOCKER = os.path.exists("/data")
EXCEL_PATH = "/data/rozklad_pro.xlsx" if IS_DOCKER else os.path.join(BASE_DIR, "rozklad_pro.xlsx")

COOKIE_NAME = "tg_webapp_session"

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

def check_session(request: Request) -> bool:
    """Перевіряє, чи є у користувача активна сесія адміна"""
    return request.cookies.get(COOKIE_NAME) == "active_admin"

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
    response.set_cookie(key=COOKIE_NAME, value="active_admin", httponly=True, max_age=86400)
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
            columns = ["Курс", "Група", "День", "Пара", "Предмет", "Викладач", "Аудиторія"]

        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "users_count": users_count, 
            "columns": columns, 
            "rows": rows,
            "needs_auth": False,
            "alert": None
        })
    
    return templates.TemplateResponse("dashboard.html", {
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
        columns = ["Курс", "Група", "День", "Пара", "Предмет", "Викладач", "Аудиторія"]

    if not text.strip():
        return templates.TemplateResponse("dashboard.html", {"request": request, "users_count": users_count, "columns": columns, "rows": rows, "needs_auth": False, "alert": {"type": "error", "text": "Текст оголошення не може бути пустим!"}})
    
    uids = []
    for key in r.scan_iter("user:*:role"):
        parts = key.split(":")
        if len(parts) >= 2:
            uids.append(parts[1])
            
    if not uids:
        return templates.TemplateResponse("dashboard.html", {"request": request, "users_count": users_count, "columns": columns, "rows": rows, "needs_auth": False, "alert": {"type": "error", "text": "Немає активних юзерів у базі!"}})

    background_tasks.add_task(run_bg_broadcast, text, uids)
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "users_count": users_count, 
        "columns": columns, 
        "rows": rows, 
        "needs_auth": False,
        "alert": {"type": "success", "text": f"📍 Веб-розсилку успішно запущено у фоні для {len(uids)} користувачів!"}
    })