import os
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Облікові дані для адмінки
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "college2026")
COOKIE_NAME = "admin_session"
SECRET_TOKEN = "secure_microservice_token_hash_999"

def get_current_user(request: Request):
    """Перевірка авторизації через Cookies."""
    token = request.cookies.get(COOKIE_NAME)
    if not token or token != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Не авторизовано")
    return True

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USER and password == ADMIN_PASS:
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key=COOKIE_NAME, value=SECRET_TOKEN, httponly=True, max_age=86400)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Невірний логін або пароль!"})

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response