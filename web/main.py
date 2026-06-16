import os
import asyncio
import json
import time
import hmac
import html
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

app = FastAPI(title="Адмін Панель Коледжу (Telegram WebApp)", version="5.0")
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

# Канонічні набори для випадайків редактора. Вільний текст у цих колонках —
# головне джерело "тихих" поломок (бот фільтрує за точним збігом):
#   - День має збігатися з datetime.strftime("%A") (англійські назви)
#   - Час має збігатися зі стартами дзвінків
#   - Формат — фіксований перелік
# До канону додаються вже наявні в файлі значення, щоб нічого не загубити.
WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
BELL_TIMES = ["08:30", "10:00", "11:45", "13:15", "14:45", "16:15", "17:45"]
LESSON_FORMATS = ["Аудиторія", "Дистанційно"]

# Секрет для підпису сесійних токенів. BOT_TOKEN відомий лише серверу,
# тож зловмисник не може підробити підпис без нього.
SESSION_SECRET = os.getenv("SESSION_SECRET") or BOT_TOKEN
SESSION_TTL = 86400  # секунд


class AuthPayload(BaseModel):
    initData: str


class SchedulePayload(BaseModel):
    data: List[Dict[str, str]]


# ──────────────────────────── Автентифікація ────────────────────────────

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


def create_session_token(user_id) -> str:
    """Створює підписаний токен сесії формату '<subject>.<issued_at>.<sig>'"""
    payload = f"{user_id}.{int(time.time())}"
    return f"{payload}.{_sign(payload)}"


def check_session(request: Request) -> bool:
    """Перевіряє підписаний токен сесії: цілісність підпису, строк дії та права адміна."""
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


# ──────────────────────────── Дані розкладу ────────────────────────────

def _read_df() -> pd.DataFrame:
    """Зчитує rozklad_pro.xlsx як текст; повертає порожній DF зі схемою за замовчуванням."""
    if os.path.exists(EXCEL_PATH):
        try:
            return pd.read_excel(EXCEL_PATH, dtype=str).fillna("")
        except Exception:
            pass
    return pd.DataFrame(columns=DEFAULT_COLUMNS)


def load_schedule_table():
    """(columns, rows) для редактора."""
    df = _read_df()
    columns = df.columns.tolist() or list(DEFAULT_COLUMNS)
    rows = df.to_dict(orient="records")
    return columns, rows


def schedule_meta() -> dict:
    """Метадані для фільтрів і випадайків: курси, групи, мапа курс→групи, набори значень."""
    df = _read_df()

    def col_vals(col):
        if col not in df.columns:
            return []
        return sorted(v for v in df[col].unique().tolist() if v)

    courses = sorted(col_vals("Курс"), key=lambda x: int(x) if str(x).isdigit() else 999)
    groups = col_vals("Група")

    course_to_groups: Dict[str, set] = {}
    if "Курс" in df.columns and "Група" in df.columns:
        for crs, grp in zip(df["Курс"], df["Група"]):
            if crs and grp:
                course_to_groups.setdefault(crs, set()).add(grp)

    def options(canon, col):
        merged = list(canon)
        for v in col_vals(col):
            if v not in merged:
                merged.append(v)
        return merged

    return {
        "courses": courses,
        "groups": groups,
        "course_to_groups": {k: sorted(v) for k, v in course_to_groups.items()},
        "day_options": options(WEEK_DAYS, "День"),
        "time_options": options(BELL_TIMES, "Час"),
        "format_options": options(LESSON_FORMATS, "Формат"),
    }


# ──────────────────────────── Стан бота / одержувачі ────────────────────────────

def bot_stats() -> dict:
    """Зведення для верхнього рядка стану: користувачі, ролі, групи."""
    try:
        total = students = teachers = 0
        for key in r.scan_iter("user:*:role"):
            total += 1
            role = r.get(key)
            if role == "student":
                students += 1
            elif role == "teacher":
                teachers += 1
        groups = sum(1 for _ in r.scan_iter("group:*:users"))
        return {"total": total, "students": students, "teachers": teachers, "groups": groups}
    except Exception:
        return {"total": "—", "students": "—", "teachers": "—", "groups": "—"}


def resolve_recipients(target: str) -> List[str]:
    """Повертає список Telegram ID за таргетом: all | role:<r> | group:<g> | course:<c>."""
    target = (target or "all").strip()
    try:
        if target == "all":
            return [k.split(":")[1] for k in r.scan_iter("user:*:role")]
        kind, _, value = target.partition(":")
        if kind == "role" and value in ("student", "teacher"):
            return [k.split(":")[1] for k in r.scan_iter("user:*:role") if r.get(k) == value]
        if kind == "group" and value:
            return list(r.smembers(f"group:{value}:users"))
        if kind == "course" and value:
            groups = schedule_meta()["course_to_groups"].get(value, [])
            uids = set()
            for g in groups:
                uids |= set(r.smembers(f"group:{g}:users"))
            return list(uids)
    except Exception:
        return []
    return []


def last_broadcast() -> dict:
    """Останній результат розсилки (для зворотного зв'язку в UI)."""
    try:
        raw = r.get("broadcast:last")
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def run_bg_broadcast(text: str, uids: list):
    """Фонова відправка розсилки; зберігає підсумок у Redis для відображення в панелі."""
    if not bot_client:
        return
    # Екрануємо текст: parse_mode=HTML інакше зламається на '<', '&' чи незакритих
    # тегах в оголошенні — і повідомлення тихо не дійде ДО ВСІХ одержувачів.
    safe_text = html.escape(text)
    delivered = failed = 0
    for uid in uids:
        try:
            await bot_client.send_message(
                chat_id=int(uid),
                text=f"📢 <b>ОГОЛОШЕННЯ:</b>\n\n{safe_text}",
                parse_mode="HTML",
            )
            delivered += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    try:
        r.set("broadcast:last", json.dumps({
            "ts": int(time.time()),
            "total": len(uids),
            "delivered": delivered,
            "failed": failed,
        }))
    except Exception:
        pass


# ──────────────────────────── Контекст дашборда ────────────────────────────

def dashboard_context(request: Request, alert=None) -> dict:
    columns, rows = load_schedule_table()
    stats = bot_stats()
    return {
        "request": request,
        "needs_auth": False,
        "alert": alert,
        "columns": columns,
        "rows": rows,
        "meta": schedule_meta(),
        "stats": stats,
        "users_count": stats["total"],
        "last_broadcast": last_broadcast(),
    }


# ──────────────────────────── Маршрути ────────────────────────────

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
    """Головна. Без куки — рендериться JS-скрипт автентифікації Telegram."""
    if check_session(request):
        return templates.TemplateResponse(request, "dashboard.html", dashboard_context(request))

    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "needs_auth": True,
        "alert": None,
        "columns": [],
        "rows": [],
        "meta": {"courses": [], "groups": [], "course_to_groups": {}, "day_options": [], "time_options": [], "format_options": []},
        "stats": {"total": 0, "students": 0, "teachers": 0, "groups": 0},
        "users_count": 0,
        "last_broadcast": None,
    })


@app.get("/api/recipients")
async def api_recipients(request: Request, target: str = "all"):
    """Кількість одержувачів для заданого таргета (живий лічильник у формі розсилки)."""
    if not check_session(request):
        raise HTTPException(status_code=401, detail="Не авторизовано")
    return {"count": len(resolve_recipients(target))}


@app.post("/save-schedule")
async def save_schedule(payload: SchedulePayload, request: Request):
    if not check_session(request):
        raise HTTPException(status_code=401, detail="Не авторизовано")
    try:
        if not payload.data:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Таблиця порожня!"})
        df = pd.DataFrame(payload.data)
        df.to_excel(EXCEL_PATH, index=False)
        # Сигнал боту: скинути кеш розкладу (підхопить за кілька секунд автоматично).
        try:
            r.set("schedule:reload", "1")
        except Exception:
            pass
        return {"status": "success", "message": "Розклад збережено. Бот застосує зміни автоматично за кілька секунд."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/broadcast")
async def web_broadcast(background_tasks: BackgroundTasks, request: Request,
                        text: str = Form(...), target: str = Form("all")):
    if not check_session(request):
        return RedirectResponse(url="/login", status_code=303)

    if not text.strip():
        return templates.TemplateResponse(request, "dashboard.html", dashboard_context(
            request, alert={"type": "error", "text": "Текст оголошення не може бути пустим!"}))

    uids = resolve_recipients(target)
    if not uids:
        return templates.TemplateResponse(request, "dashboard.html", dashboard_context(
            request, alert={"type": "error", "text": "За обраним фільтром немає жодного одержувача."}))

    background_tasks.add_task(run_bg_broadcast, text, uids)
    return templates.TemplateResponse(request, "dashboard.html", dashboard_context(
        request, alert={"type": "success", "text": f"Розсилку запущено у фоні для {len(uids)} користувачів."}))
