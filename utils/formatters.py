import pandas as pd

def format_lesson_week(subject, teacher, room, w_current, group, lesson_fmt=None):
    if pd.isna(subject) or str(subject) in ["-", "nan"]: return None
    subject, teacher = str(subject), str(teacher)
    
    # Handle optional format display
    if str(lesson_fmt).lower().strip() == "дистанційно":
        room_str = f" [💻 Дист. {room}]" if str(room) not in ["-", "nan", ""] else " [💻 Дистанційно]"
    else:
        room = str(room) if str(room) not in ["-", "nan"] else ""
        room_str = f" [{room}]" if room else ""
        
    grp_str = f" <i>(Гр. {group})</i>"

    if "//" in subject:
        parts_s = subject.split("//")
        parts_t = teacher.split("//") if "//" in teacher else [teacher, teacher]
        s1, s2 = parts_s[0].strip(), parts_s[1].strip() if len(parts_s) > 1 else ""
        t1, t2 = parts_t[0].strip(), parts_t[1].strip() if len(parts_t) > 1 else parts_t[0]
        return f"🔄 <b>Мигалка:</b>\n   🟥 {s1} ({t1}) {room_str}{grp_str}\n   🟦 {s2} ({t2}) {room_str}{grp_str}"
                
    if "(ч)" in subject: return f"🟥 <b>(Чис):</b> {subject.replace('(ч)','').strip()} ({teacher}) {room_str}{grp_str}"
    if "(з)" in subject: return f"🟦 <b>(Знам):</b> {subject.replace('(з)','').strip()} ({teacher}) {room_str}{grp_str}"
        
    return f"▫️ {subject} ({teacher}) {room_str}{grp_str}"

def filter_current_lesson_name(subject, w_type):
    if pd.isna(subject) or str(subject) in ["-", "nan"]: return None
    subject = str(subject)
    if "//" in subject:
        parts = subject.split("//")
        return parts[0].strip() if w_type == "upper" and len(parts) > 0 else parts[1].strip() if len(parts) > 1 else parts[0].strip()
    if "(ч)" in subject: return subject.replace("(ч)", "").strip() if w_type == "upper" else None
    if "(з)" in subject: return subject.replace("(з)", "").strip() if w_type == "lower" else None
    return subject

def get_current_lesson_info(subject, teacher, w_type):
    if pd.isna(subject) or str(subject) in ["-", "nan"]: return None, None
    subject = str(subject)
    teacher = str(teacher)
    
    if "//" in subject:
        parts_s = subject.split("//")
        parts_t = teacher.split("//") if "//" in teacher else [teacher, teacher]
        
        if w_type == "upper":
            s_out = parts_s[0].strip() if len(parts_s) > 0 else ""
            t_out = parts_t[0].strip() if len(parts_t) > 0 else ""
            return s_out, t_out
        else:
            s_out = parts_s[1].strip() if len(parts_s) > 1 else parts_s[0].strip()
            t_out = parts_t[1].strip() if len(parts_t) > 1 else parts_t[0].strip()
            return s_out, t_out
            
    if "(ч)" in subject: 
        return (subject.replace("(ч)", "").strip(), teacher) if w_type == "upper" else (None, None)
    if "(з)" in subject: 
        return (subject.replace("(з)", "").strip(), teacher) if w_type == "lower" else (None, None)
        
    return subject, teacher
