from redis.asyncio import Redis
from config import REDIS_HOST, REDIS_PORT

r = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

async def get_role(uid): return await r.get(f"user:{uid}:role")
async def set_role(uid, role): await r.set(f"user:{uid}:role", role)

# Teacher Reverse Indexes
async def set_teacher_name(uid, name): 
    old_name = await get_teacher_name(uid)
    if old_name:
        await r.srem(f"teacher:{old_name}:users", uid)
    await r.set(f"user:{uid}:teacher_name", name)
    if name:
        await r.sadd(f"teacher:{name}:users", uid)
        
async def get_teacher_name(uid): return await r.get(f"user:{uid}:teacher_name")
async def get_users_for_teacher(name): return await r.smembers(f"teacher:{name}:users")

# Student Reverse Indexes
async def get_groups(uid): return await r.smembers(f"user:{uid}:groups")

async def clear_groups(uid): 
    groups = await get_groups(uid)
    for group in groups:
        await r.srem(f"group:{group}:users", uid)
    await r.delete(f"user:{uid}:groups")

async def toggle_group(uid, group):
    key = f"user:{uid}:groups"
    is_member = await r.sismember(key, group)
    if is_member: 
        await r.srem(key, group)
        await r.srem(f"group:{group}:users", uid)
    else: 
        await r.sadd(key, group)
        await r.sadd(f"group:{group}:users", uid)

async def get_users_in_group(group): return await r.smembers(f"group:{group}:users")

# General functions
async def get_all_users_keys(): 
    keys = []
    async for key in r.scan_iter("user:*:role"):
        keys.append(key)
    return keys

async def set_notification_status(uid, status): await r.set(f"user:{uid}:notifications", "1" if status else "0")
async def get_notification_status(uid):
    val = await r.get(f"user:{uid}:notifications")
    return val == "1" if val is not None else True # Default True

# Сигнал від веб-панелі: розклад змінено, треба скинути кеш розкладу в боті.
async def consume_schedule_reload():
    """Атомарно перевіряє й гасить прапорець schedule:reload. True, якщо було оновлення."""
    return await r.getdel("schedule:reload") is not None




