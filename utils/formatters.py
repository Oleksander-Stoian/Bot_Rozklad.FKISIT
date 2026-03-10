import pandas as pd

def _room_display(room, lesson_fmt):
    """Повертає (remote_icon, display_str) для кабінету/посилання."""
    is_remote = str(lesson_fmt).lower().strip() == "дистанційно"
    room_val = str(room).strip()
    if is_remote:
        display = f"{room_val} 💻" if room_val not in ["-", "nan", ""] else "Дистанційно 💻"
        return "", display
    display = f"ауд. {room_val}" if room_val not in ["-", "nan", ""] else ""
    return "", display


def format_lesson_week(subject, teacher, room, w_current, group, lesson_fmt=None, role=None):
    """
    Повертає рядок для блоку пари у вигляді:
        "Назва предмету{remote_icon}\n<i>Вторинна інфо</i>"
    Виклик: f"<b>{час}</b>  {entry}" — предмет на тому ж рядку що й час.
    """
    if pd.isna(subject) or str(subject) in ["-", "nan"]:
        return None
    subject = str(subject)
    teacher = str(teacher)

    remote_icon, room_disp = _room_display(room, lesson_fmt)

    def sec(t, g):
        primary = g if role == "teacher" else t
        return "  ·  ".join(p for p in [primary, room_disp] if p)

    if "//" in subject:
        parts_s = subject.split("//")
        parts_t = teacher.split("//") if "//" in teacher else [teacher, teacher]
        s1 = parts_s[0].strip()
        s2 = parts_s[1].strip() if len(parts_s) > 1 else ""
        t1 = parts_t[0].strip()
        t2 = parts_t[1].strip() if len(parts_t) > 1 else parts_t[0].strip()
        return (
            f"Чергується:{remote_icon}\n"
            f"🟥 <i>{s1}  ·  {sec(t1, group)}</i>\n"
            f"🟦 <i>{s2}  ·  {sec(t2, group)}</i>"
        )

    if "(ч)" in subject:
        s = subject.replace("(ч)", "").strip()
        sc = sec(teacher, group)
        parts = [p for p in ["🟥 тільки непарний", sc] if p]
        return f"{s}{remote_icon}\n<i>{'  ·  '.join(parts)}</i>"

    if "(з)" in subject:
        s = subject.replace("(з)", "").strip()
        sc = sec(teacher, group)
        parts = [p for p in ["🟦 тільки парний", sc] if p]
        return f"{s}{remote_icon}\n<i>{'  ·  '.join(parts)}</i>"

    sc = sec(teacher, group)
    suffix = f"\n<i>{sc}</i>" if sc else ""
    return f"{subject}{remote_icon}{suffix}"


def filter_current_lesson_name(subject, w_type):
    if pd.isna(subject) or str(subject) in ["-", "nan"]:
        return None
    subject = str(subject)
    if "//" in subject:
        parts = subject.split("//")
        return parts[0].strip() if w_type == "upper" else (parts[1].strip() if len(parts) > 1 else parts[0].strip())
    if "(ч)" in subject:
        return subject.replace("(ч)", "").strip() if w_type == "upper" else None
    if "(з)" in subject:
        return subject.replace("(з)", "").strip() if w_type == "lower" else None
    return subject


def get_current_lesson_info(subject, teacher, w_type):
    if pd.isna(subject) or str(subject) in ["-", "nan"]:
        return None, None
    subject = str(subject)
    teacher = str(teacher)

    if "//" in subject:
        parts_s = subject.split("//")
        parts_t = teacher.split("//") if "//" in teacher else [teacher, teacher]
        if w_type == "upper":
            return parts_s[0].strip(), parts_t[0].strip()
        else:
            return (parts_s[1].strip() if len(parts_s) > 1 else parts_s[0].strip(),
                    parts_t[1].strip() if len(parts_t) > 1 else parts_t[0].strip())

    if "(ч)" in subject:
        return (subject.replace("(ч)", "").strip(), teacher) if w_type == "upper" else (None, None)
    if "(з)" in subject:
        return (subject.replace("(з)", "").strip(), teacher) if w_type == "lower" else (None, None)
    return subject, teacher
