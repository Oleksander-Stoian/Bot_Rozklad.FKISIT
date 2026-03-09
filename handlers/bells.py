from aiogram import types, F, Router
from config import BELL_SCHEDULE

router = Router()

@router.message(F.text == "🕐 Розклад дзвінків")
async def bells(msg: types.Message):
    txt = "🕐 <b>Розклад дзвінків</b>\n\n"
    for i in BELL_SCHEDULE:
        txt += f"<b>{i['num']} пара:</b> {i['start']} — {i['end']}\n☕ <i>Перерва: {i['break']}</i>\n\n"
    await msg.answer(txt, parse_mode="HTML")
