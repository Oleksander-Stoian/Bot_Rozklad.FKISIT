import redis
from config import REDIS_HOST, REDIS_PORT

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

def get_role(uid): return r.get(f"user:{uid}:role")
def set_role(uid, role): r.set(f"user:{uid}:role", role)
def set_teacher_name(uid, name): r.set(f"user:{uid}:teacher_name", name)
def get_teacher_name(uid): return r.get(f"user:{uid}:teacher_name")
def get_groups(uid): return r.smembers(f"user:{uid}:groups")
def clear_groups(uid): r.delete(f"user:{uid}:groups")
def toggle_group(uid, group):
    key = f"user:{uid}:groups"
    if r.sismember(key, group): r.srem(key, group)
    else: r.sadd(key, group)
def get_all_users_keys(): return r.scan_iter("user:*:role")

def set_notification_status(uid, status): r.set(f"user:{uid}:notifications", "1" if status else "0")
def get_notification_status(uid):
    val = r.get(f"user:{uid}:notifications")
    return val == "1" if val is not None else True # Default True

def clear_user(uid):
    r.delete(f"user:{uid}:role")
    r.delete(f"user:{uid}:teacher_name")
    r.delete(f"user:{uid}:groups")