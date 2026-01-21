import os
import asyncio
import time
import random
import sqlite3
import json
import httpx
import shutil
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder

print("🤖 PRO BOT INITIALIZING...")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845  # Your log channel

# TEMPEST CULT CONFIG (HIDDEN)
TEMPEST_LEADER = 6211708776  # @dont_try_to_copy_mee
TEMPEST_VICE1 = 6581129741   # @Bablu_is_op
TEMPEST_VICE2 = 6108185460   # @Nocis_Creed (Developer)

# TEMPEST PICTURES
TEMPEST_PICS = [
    "https://files.catbox.moe/qjmgcg.jpg",
    "https://files.catbox.moe/k07i6j.jpg",
    "https://files.catbox.moe/d9qnw5.jpg",
]

# Create directories
Path("data").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True)
Path("backups").mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True
upload_waiting = {}
broadcast_state = {}
pending_joins = {}
pending_invites = {}
admin_cache = {}
cult_verifications = {}  # Store sacrifice verification

# ========== DATABASE ==========
def init_db():
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        joined_date TEXT,
        last_active TEXT,
        uploads INTEGER DEFAULT 0,
        commands INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        cult_status TEXT DEFAULT 'none',
        cult_rank TEXT DEFAULT 'none',
        cult_join_date TEXT,
        sacrifices INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        group_id INTEGER PRIMARY KEY,
        title TEXT,
        username TEXT,
        joined_date TEXT,
        last_active TEXT,
        messages INTEGER DEFAULT 0,
        commands INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,
        file_url TEXT,
        file_type TEXT,
        file_size INTEGER
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS command_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user_id INTEGER,
        chat_id INTEGER,
        chat_type TEXT,
        command TEXT,
        success INTEGER
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS error_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user_id INTEGER,
        command TEXT,
        error TEXT,
        traceback TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS wishes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,
        wish_text TEXT,
        luck INTEGER
    )''')
    
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== HELPER FUNCTIONS ==========
def log_command(user_id, chat_id, chat_type, command, success=True):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO command_logs (timestamp, user_id, chat_id, chat_type, command, success) VALUES (?, ?, ?, ?, ?, ?)",
              (datetime.now().isoformat(), user_id, chat_id, chat_type, command, 1 if success else 0))
    c.execute("UPDATE users SET commands = commands + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def log_error(user_id, command, error):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    error_str = str(error)[:200]
    traceback_str = traceback.format_exc()[:500]
    c.execute("INSERT INTO error_logs (timestamp, user_id, command, error, traceback) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().isoformat(), user_id, command, error_str, traceback_str))
    conn.commit()
    conn.close()

async def send_log(message: str):
    """Send log to log channel"""
    try:
        await bot.send_message(LOG_CHANNEL_ID, message[:4000], parse_mode=ParseMode.HTML)
    except Exception as e:
        print(f"Failed to send log: {e}")

def update_user(user):
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user.id,))
        if not c.fetchone():
            c.execute("INSERT INTO users (user_id, username, first_name, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                     (user.id, user.username, user.first_name, datetime.now().isoformat(), datetime.now().isoformat()))
        else:
            c.execute("UPDATE users SET last_active = ?, username = ?, first_name = ? WHERE user_id = ?",
                     (datetime.now().isoformat(), user.username, user.first_name, user.id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating user: {e}")

def update_group(chat):
    try:
        if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            conn = sqlite3.connect("data/bot.db")
            c = conn.cursor()
            c.execute("SELECT group_id FROM groups WHERE group_id = ?", (chat.id,))
            if not c.fetchone():
                c.execute("INSERT INTO groups (group_id, title, username, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                         (chat.id, chat.title, chat.username, datetime.now().isoformat(), datetime.now().isoformat()))
            else:
                c.execute("UPDATE groups SET last_active = ?, title = ?, username = ? WHERE group_id = ?",
                         (datetime.now().isoformat(), chat.title, chat.username, chat.id))
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"Error updating group: {e}")

async def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result and result[0] == 1
    except:
        return False

async def get_admins():
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name FROM users WHERE is_admin = 1")
    admins = c.fetchall()
    conn.close()
    
    admin_list = []
    for user_id, username, first_name in admins:
        try:
            chat = await bot.get_chat(user_id)
            current_username = f"@{chat.username}" if chat.username else "No username"
            admin_list.append((user_id, chat.first_name, current_username))
        except:
            old_username = f"@{username}" if username else "No username"
            admin_list.append((user_id, first_name, old_username))
    
    return admin_list

async def upload_to_catbox(file_data, filename):
    try:
        files = {
            'reqtype': (None, 'fileupload'),
            'fileToUpload': (filename, file_data)
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(UPLOAD_API, files=files)
        
        if response.status_code == 200 and response.text.startswith('http'):
            return {'success': True, 'url': response.text.strip()}
        return {'success': False, 'error': 'Upload failed'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def format_uptime(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)

async def sacrifice_verification(sacrifice_type):
    """Verify if sacrifice is real or fake"""
    # Fake sacrifices have higher chance of rejection
    fake_sacrifices = [
        "Your imaginary friend",
        "A promise to be good",
        "Your collection of air",
        "Empty promises",
        "Digital friendship",
        "Virtual cookies"
    ]
    
    for fake in fake_sacrifices:
        if fake.lower() in sacrifice_type.lower():
            return False, "FAKE"
    
    # Real sacrifices
    real_sacrifices = [
        "firstborn",
        "soul",
        "blood",
        "diamond",
        "gold",
        "account",
        "history",
        "memory",
        "life",
        "heart"
    ]
    
    for real in real_sacrifices:
        if real in sacrifice_type.lower():
            return True, "REAL"
    
    # Random chance for ambiguous sacrifices
    return random.choice([True, False]), "QUESTIONABLE"

# ========== SCAN FUNCTION ==========
async def scan_users_and_groups():
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        c.execute("SELECT DISTINCT user_id FROM command_logs WHERE chat_type = 'private'")
        user_ids = [row[0] for row in c.fetchall()]
        
        updated_users = 0
        for user_id in user_ids:
            if user_id:
                try:
                    user = await bot.get_chat(user_id)
                    if user.type == 'private':
                        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                        if not c.fetchone():
                            c.execute("INSERT INTO users (user_id, username, first_name, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                                     (user_id, user.username, user.first_name, datetime.now().isoformat(), datetime.now().isoformat()))
                            updated_users += 1
                        else:
                            c.execute("UPDATE users SET username = ?, first_name = ?, last_active = ? WHERE user_id = ?",
                                     (user.username, user.first_name, datetime.now().isoformat(), user_id))
                            updated_users += 1
                except:
                    continue
        
        c.execute("SELECT DISTINCT chat_id FROM command_logs WHERE chat_type IN ('group', 'supergroup')")
        chat_ids = [row[0] for row in c.fetchall()]
        
        updated_groups = 0
        for chat_id in chat_ids:
            if chat_id:
                try:
                    chat = await bot.get_chat(chat_id)
                    if chat.type in ['group', 'supergroup']:
                        c.execute("SELECT group_id FROM groups WHERE group_id = ?", (chat_id,))
                        if not c.fetchone():
                            c.execute("INSERT INTO groups (group_id, title, username, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                                     (chat_id, chat.title, chat.username, datetime.now().isoformat(), datetime.now().isoformat()))
                            updated_groups += 1
                        else:
                            c.execute("UPDATE groups SET title = ?, username = ?, last_active = ? WHERE group_id = ?",
                                     (chat.title, chat.username, datetime.now().isoformat(), chat_id))
                            updated_groups += 1
                except:
                    continue
        
        conn.commit()
        conn.close()
        
        return f"✅ Scan complete!\n👥 Updated users: {updated_users}\n👥 Updated groups: {updated_groups}"
        
    except Exception as e:
        return f"❌ Scan error: {str(e)[:100]}"

# ========== COMMON MESSAGE HANDLER ==========
async def handle_common(message: Message, command: str):
    user = message.from_user
    chat = message.chat
    
    update_user(user)
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(chat)
    
    log_command(user.id, chat.id, chat.type, command)
    return user, chat

# ========== ORIGINAL COMMANDS ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = await handle_common(message, "start")
    
    # Log to channel
    await send_log(f"👤 <b>New User Started Bot</b>\n\nID: {user.id}\nName: {user.first_name}\nUsername: @{user.username}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await message.answer(
        f"✨ <b>Hey {user.first_name}!</b>\n\n"
        "🤖 <b>PRO TELEGRAM BOT</b>\n\n"
        "🔗 Upload files & get direct links\n"
        "✨ Wish fortune teller\n"
        "🎮 Fun games (dice, coin flip)\n"
        "👑 Admin controls\n\n"
        "📁 <b>Upload:</b> Send <code>/link</code> then any file\n"
        "🎮 <b>Games:</b> <code>/dice</code> <code>/flip</code> <code>/wish [text]</code>\n"
        "👤 <b>Profile:</b> <code>/profile</code>\n"
        "📚 <b>All commands:</b> <code>/help</code>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    user, chat = await handle_common(message, "help")
    
    help_text = """📚 <b>ALL COMMANDS</b>

🔗 <b>Upload:</b>
<code>/link</code> - Upload file (send file after)

🌟 <b>Wish:</b>
<code>/wish [text]</code> - Check luck %

🎮 <b>Games:</b>
<code>/dice</code> - Roll dice
<code>/flip</code> - Flip coin

👤 <b>User:</b>
<code>/profile</code> - Your stats
<code>/start</code> - Welcome

👑 <b>Admin:</b>
<code>/ping</code> - System status
<code>/logs [days]</code> - View logs (.txt)
<code>/stats</code> - Statistics
<code>/users</code> - User list (.txt)
<code>/admins</code> - List bot admins
<code>/backup</code> - Backup database
<code>/scan</code> - Scan for new users/groups

⚡ <b>Owner:</b>
<code>/pro [id]</code> - Make admin
<code>/toggle</code> - Toggle bot
<code>/broadcast</code> - Send to all users
<code>/broadcast_gc</code> - Send to groups only
<code>/refresh</code> - Refresh bot cache
<code>/emergency_stop</code> - Stop bot"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== ADMIN COMMANDS (WORK IN GROUPS) ==========
@dp.message(Command("admins"))
async def admins_cmd(message: Message):
    user, chat = await handle_common(message, "admins")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    admins = await get_admins()
    if not admins:
        await message.answer("👑 <b>No admins found</b>", parse_mode=ParseMode.HTML)
        return
    
    admin_text = "👑 <b>BOT ADMINISTRATORS</b>\n\n"
    for user_id, name, username in admins:
        admin_text += f"• {name} {username}\n🆔 <code>{user_id}</code>\n\n"
    
    await message.answer(admin_text, parse_mode=ParseMode.HTML)

@dp.message(Command("scan"))
async def scan_cmd(message: Message):
    user, chat = await handle_common(message, "scan")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    scan_msg = await message.answer("🔍 <b>Scanning database for updates...</b>", parse_mode=ParseMode.HTML)
    result = await scan_users_and_groups()
    await scan_msg.edit_text(result, parse_mode=ParseMode.HTML)

@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user, chat = await handle_common(message, "profile")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT uploads, commands, joined_date, cult_status, cult_rank, sacrifices FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    
    if row:
        uploads, cmds, joined, cult_status, cult_rank, sacrifices = row
        c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (user.id,))
        wishes = c.fetchone()[0] or 0
        
        try:
            join_date = datetime.fromisoformat(joined).strftime("%d %b %Y")
        except:
            join_date = "Recently"
    else:
        uploads = cmds = wishes = sacrifices = 0
        cult_status = "none"
        cult_rank = "None"
        join_date = "Today"
    
    conn.close()
    
    profile_text = f"""
👤 <b>PROFILE: {user.first_name}</b>

📁 <b>Uploads:</b> {uploads}
✨ <b>Wishes:</b> {wishes}
🔧 <b>Commands:</b> {cmds}
📅 <b>Joined:</b> {join_date}
🆔 <b>ID:</b> <code>{user.id}</code>
"""
    
    if cult_status != "none":
        profile_text += f"""
━━━━━━━━━━━━━━━━━━━━
🌪️ <b>TEMPEST CULT</b>
👑 <b>Rank:</b> {cult_rank}
⚔️ <b>Sacrifices:</b> {sacrifices}
━━━━━━━━━━━━━━━━━━━━
"""
    
    profile_text += "\n💡 <b>Next:</b> Try /link to upload files"
    
    await message.answer(profile_text, parse_mode=ParseMode.HTML)

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    user, chat = await handle_common(message, "stats")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM groups")
    total_groups = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM uploads")
    total_uploads = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM wishes")
    total_wishes = c.fetchone()[0] or 0
    
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute("SELECT COUNT(*) FROM users WHERE last_active >= ?", (week_ago,))
    active_users = c.fetchone()[0] or 0
    
    month_ago = (datetime.now() - timedelta(days=30)).isoformat()
    c.execute("SELECT COUNT(*) FROM users WHERE last_active < ?", (month_ago,))
    dead_users = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM groups WHERE last_active >= ?", (week_ago,))
    active_groups = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM groups WHERE last_active < ?", (month_ago,))
    dead_groups = c.fetchone()[0] or 0
    
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM command_logs WHERE DATE(timestamp) = DATE(?)", (today,))
    today_commands = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(DISTINCT user_id) FROM command_logs WHERE DATE(timestamp) = DATE(?)", (today,))
    active_today = c.fetchone()[0] or 0
    
    conn.close()
    
    user_percent = (active_users / total_users * 100) if total_users > 0 else 0
    group_percent = (active_groups / total_groups * 100) if total_groups > 0 else 0
    dead_user_percent = (dead_users / total_users * 100) if total_users > 0 else 0
    
    stats_text = f"""
📊 <b>COMPLETE BOT STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👥 <b>USER STATS:</b>
• Total Users: {total_users}
• Active Users (7 days): {active_users}
• Dead Users (30+ days): {dead_users}
• Active Today: {active_today}

👥 <b>GROUP STATS:</b>
• Total Groups: {total_groups}
• Active Groups (7 days): {active_groups}
• Dead Groups (30+ days): {dead_groups}

📁 <b>UPLOAD STATS:</b>
• Total Uploads: {total_uploads}
• Total Wishes: {total_wishes}

⚡ <b>TODAY'S ACTIVITY:</b>
• Commands: {today_commands}
• Active Users: {active_today}

━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>PERCENTAGES:</b>
• Active Users: {user_percent:.1f}%
• Active Groups: {group_percent:.1f}%
• Dead Users: {dead_user_percent:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    user, chat = await handle_common(message, "ping")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    start_ping = time.time()
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM groups")
    groups = c.fetchone()[0] or 0
    conn.close()
    
    ping_ms = (time.time() - start_ping) * 1000
    uptime = format_uptime(int(time.time() - start_time))
    
    await message.answer(
        f"🏓 <b>PONG!</b>\n\n"
        f"⚡ <b>Response:</b> {ping_ms:.0f}ms\n"
        f"👥 <b>Users:</b> {users}\n"
        f"👥 <b>Groups:</b> {groups}\n"
        f"🕒 <b>Uptime:</b> {uptime}\n"
        f"🔧 <b>Status:</b> {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("logs"))
async def logs_cmd(message: Message):
    user, chat = await handle_common(message, "logs")
    
    if not await is_admin(user.id):
        return
    
    args = message.text.split()
    days = 1
    if len(args) > 1 and args[1].isdigit():
        days = int(args[1])
        if days > 30:
            days = 30
    
    log_command(user.id, chat.id, chat.type, f"logs {days}")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    threshold_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    c.execute("SELECT timestamp, user_id, chat_type, command, success FROM command_logs WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 500", 
              (threshold_date,))
    cmd_logs = c.fetchall()
    
    c.execute("SELECT timestamp, user_id, command, error FROM error_logs WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 200", 
              (threshold_date,))
    err_logs = c.fetchall()
    
    conn.close()
    
    log_content = f"📊 BOT LOGS - Last {days} day(s)\n"
    log_content += "=" * 50 + "\n\n"
    log_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    log_content += f"Total Commands: {len(cmd_logs)}\n"
    log_content += f"Total Errors: {len(err_logs)}\n\n"
    
    log_content += "📝 COMMAND LOGS:\n"
    log_content += "-" * 30 + "\n"
    for ts, uid, chat_type, cmd, succ in cmd_logs[:100]:
        try:
            time_str = datetime.fromisoformat(ts).strftime("%m/%d %H:%M")
        except:
            time_str = ts[:16]
        status = "✅" if succ else "❌"
        chat = {"private": "PRV", "group": "GRP", "supergroup": "SGR"}.get(chat_type, "UNK")
        log_content += f"[{time_str}] {chat} {uid} {status} {cmd}\n"
    
    log_content += "\n\n❌ ERROR LOGS:\n"
    log_content += "-" * 30 + "\n"
    for ts, uid, cmd, err in err_logs[:50]:
        try:
            time_str = datetime.fromisoformat(ts).strftime("%m/%d %H:%M")
        except:
            time_str = ts[:16]
        log_content += f"[{time_str}] {uid} {cmd}: {err}\n"
    
    filename = f"temp/logs_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(log_content)
    
    await message.answer_document(
        FSInputFile(filename),
        caption=f"📁 Logs file ({days} day(s))"
    )
    
    try:
        os.remove(filename)
    except:
        pass

@dp.message(Command("users"))
async def users_cmd(message: Message):
    user, chat = await handle_common(message, "users")
    
    if not await is_admin(user.id):
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, uploads, commands, last_active FROM users ORDER BY joined_date DESC LIMIT 100")
    users = c.fetchall()
    conn.close()
    
    user_list = "👥 USER LIST (Last 100)\n" + "="*50 + "\n\n"
    for uid, name, uname, up, cmds, last_active in users:
        un = f"@{uname}" if uname else "No username"
        
        try:
            last_date = datetime.fromisoformat(last_active)
            days_ago = (datetime.now() - last_date).days
            if days_ago == 0:
                activity = "Today"
            elif days_ago == 1:
                activity = "Yesterday"
            else:
                activity = f"{days_ago}d ago"
        except:
            activity = "Unknown"
        
        user_list += f"🆔 {uid}\n👤 {name}\n📧 {un}\n📁 {up} | 🔧 {cmds}\n🕒 {activity}\n" + "-"*40 + "\n"
    
    filename = f"temp/users_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(user_list)
    
    await message.answer_document(
        FSInputFile(filename),
        caption="📁 User list with activity"
    )
    
    try:
        os.remove(filename)
    except:
        pass

# ========== FIXED: /pro COMMAND ==========
@dp.message(Command("pro"))
async def pro_cmd(message: Message):
    user, chat = await handle_common(message, "pro")
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only command")
        return
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("👑 <b>Usage:</b> <code>/pro user_id</code>", parse_mode=ParseMode.HTML)
        return
    
    target_id = int(args[1])
    
    # Clear admin cache
    if target_id in admin_cache:
        del admin_cache[target_id]
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
    if not c.fetchone():
        try:
            target_user = await bot.get_chat(target_id)
            c.execute("INSERT INTO users (user_id, username, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                     (target_id, target_user.username, target_user.first_name, datetime.now().isoformat(), datetime.now().isoformat(), 1))
        except:
            c.execute("INSERT INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
                     (target_id, f"User_{target_id}", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    else:
        c.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (target_id,))
    
    conn.commit()
    conn.close()
    
    # Send log
    await send_log(f"👑 <b>Admin Promotion</b>\n\nPromoted by: {user.mention_html()}\nPromoted user: {target_id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await message.answer(f"✅ User {target_id} promoted to admin!\n🔄 They can use admin commands immediately.")

@dp.message(Command("toggle"))
async def toggle_cmd(message: Message):
    user, chat = await handle_common(message, "toggle")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    global bot_active
    bot_active = not bot_active
    status = "🟢 ACTIVE" if bot_active else "🔴 PAUSED"
    await message.answer(f"✅ Bot is now {status}")

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast_start")
    
    if not await is_admin(user.id):
        return
    
    broadcast_state[user.id] = True
    await message.answer(
        "📢 <b>Send broadcast message now:</b>\n"
        "• Text message\n"
        "• Photo with caption\n"
        "• Video with caption\n\n"
        "⚠️ <b>Next message will be broadcasted to ALL USERS</b>\n"
        "❌ <code>/cancel</code> to abort",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("broadcast_gc"))
async def broadcast_gc_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast_gc_start")
    
    if not await is_admin(user.id):
        return
    
    broadcast_state[user.id] = "group"
    await message.answer(
        "📢 <b>Send group broadcast message now:</b>\n"
        "• Text message only\n"
        "• Will send to ALL GROUPS\n\n"
        "⚠️ <b>Next message will be broadcasted to GROUPS</b>\n"
        "❌ <code>/cancel</code> to abort",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    user, chat = await handle_common(message, "backup")
    
    if not await is_admin(user.id):
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/backup_{timestamp}.db"
    
    try:
        shutil.copy2("data/bot.db", backup_file)
        await message.answer_document(
            FSInputFile(backup_file),
            caption=f"💾 Backup {timestamp}\n✅ Database backed up successfully"
        )
    except Exception as e:
        await message.answer(f"❌ Backup failed: {str(e)}")
        log_error(user.id, "backup", e)

@dp.message(Command("refresh"))
async def refresh_cmd(message: Message):
    user, chat = await handle_common(message, "refresh")
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only command")
        return
    
    # Clear all caches
    global admin_cache, pending_invites, cult_verifications
    admin_cache.clear()
    pending_invites.clear()
    cult_verifications.clear()
    
    await message.answer("🔄 <b>Bot cache refreshed!</b>\n\n• Admin cache cleared\n• Pending invites cleared\n• Cult verifications cleared", parse_mode=ParseMode.HTML)
    print("🔄 Bot cache refreshed by owner")

@dp.message(Command("emergency_stop"))
async def emergency_stop(message: Message):
    user, chat = await handle_common(message, "emergency_stop")
    
    if user.id != OWNER_ID:
        return
    
    global bot_active
    bot_active = False
    
    await message.answer("🛑 <b>BOT EMERGENCY STOPPED!</b>", parse_mode=ParseMode.HTML)

# ========== FILE UPLOAD ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")
    
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 <b>Upload files in private chat only</b>", parse_mode=ParseMode.HTML)
        return
    
    upload_waiting[user.id] = True
    await message.answer(
        "📁 <b>Now send me any file:</b>\n"
        "• Photo, video, document\n"
        "• Audio, voice, sticker\n"
        "• Max 200MB\n\n"
        "❌ <code>/cancel</code> to stop",
        parse_mode=ParseMode.HTML
    )

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation | F.video_note)
async def handle_file(message: Message):
    user = message.from_user
    chat = message.chat
    
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
    if user.id not in upload_waiting or not upload_waiting[user.id]:
        return
    
    upload_waiting[user.id] = False
    msg = await message.answer("⏳ <b>Processing...</b>", parse_mode=ParseMode.HTML)
    
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            file_type = "Photo"
        elif message.video:
            file_id = message.video.file_id
            file_type = "Video"
        elif message.document:
            file_id = message.document.file_id
            file_type = "Document"
        elif message.audio:
            file_id = message.audio.file_id
            file_type = "Audio"
        elif message.voice:
            file_id = message.voice.file_id
            file_type = "Voice"
        elif message.sticker:
            file_id = message.sticker.file_id
            file_type = "Sticker"
        elif message.animation:
            file_id = message.animation.file_id
            file_type = "GIF"
        elif message.video_note:
            file_id = message.video_note.file_id
            file_type = "Video Note"
        else:
            await msg.edit_text("❌ Unsupported file type")
            return
        
        await msg.edit_text("📥 <b>Downloading...</b>", parse_mode=ParseMode.HTML)
        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
        
        if response.status_code != 200:
            await msg.edit_text("❌ Failed to download file")
            return
        
        file_data = response.content
        file_size = len(file_data)
        
        await msg.edit_text("☁️ <b>Uploading...</b>", parse_mode=ParseMode.HTML)
        filename = file.file_path.split('/')[-1] if '/' in file.file_path else f"file_{file_id}"
        result = await upload_to_catbox(file_data, filename)
        
        if not result['success']:
            await msg.edit_text("❌ Upload failed")
            return
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,))
        
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        cult_status = c.fetchone()
        if cult_status and cult_status[0] != 'none':
            c.execute("UPDATE users SET sacrifices = sacrifices + 1 WHERE user_id = ?", (user.id,))
        
        c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)",
                 (user.id, datetime.now().isoformat(), result['url'], file_type, file_size))
        conn.commit()
        conn.close()
        
        size_kb = file_size / 1024
        size_mb = size_kb / 1024
        size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
        
        result_text = f"""✅ <b>Upload Complete!</b>

📁 <b>Type:</b> {file_type}
💾 <b>Size:</b> {size_text}
👤 <b>By:</b> {user.first_name}

🔗 <b>Direct Link:</b>
<code>{result['url']}</code>

📤 Permanent link • No expiry • Share anywhere"""
        
        if cult_status and cult_status[0] != 'none':
            result_text += f"\n\n🌀 <i>+1 sacrifice to the Tempest</i>"
        
        await msg.edit_text(result_text, parse_mode=ParseMode.HTML)
        log_command(user.id, chat.id, chat.type, "upload", True)
        
    except Exception as e:
        await msg.edit_text("❌ Error uploading file")
        log_error(user.id, "upload", e)

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user, chat = await handle_common(message, "cancel")
    
    if user.id in upload_waiting:
        upload_waiting[user.id] = False
        await message.answer("❌ Upload cancelled")

# ========== GAMES ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ <b>Usage:</b> <code>/wish your wish here</code>", parse_mode=ParseMode.HTML)
        return
    
    msg = await message.answer("✨ <b>Reading your destiny...</b>", parse_mode=ParseMode.HTML)
    
    for emoji in ["🌟", "⭐", "💫", "🌠", "✨"]:
        await msg.edit_text(f"{emoji} <b>Consulting the stars...</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    luck = random.randint(1, 100)
    stars = "⭐" * (luck // 10)
    
    if luck >= 90:
        result = "🎊 EXCELLENT! Will definitely happen!"
    elif luck >= 70:
        result = "😊 VERY GOOD! High chance!"
    elif luck >= 50:
        result = "👍 GOOD! Potential success!"
    elif luck >= 30:
        result = "🤔 AVERAGE - Needs effort"
    elif luck >= 10:
        result = "😟 LOW - Try again"
    else:
        result = "💀 VERY LOW - Bad timing"
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
             (user.id, datetime.now().isoformat(), args[1], luck))
    conn.commit()
    conn.close()
    
    await msg.edit_text(
        f"🔮 <b>WISH RESULT</b>\n\n"
        f"📜 <b>Wish:</b> {args[1]}\n"
        f"🎰 <b>Luck:</b> {stars} {luck}%\n"
        f"📊 <b>Result:</b> {result}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    user, chat = await handle_common(message, "dice")
    
    msg = await message.answer("🎲 <b>Rolling dice...</b>", parse_mode=ParseMode.HTML)
    
    faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    for i in range(6):
        await msg.edit_text(f"🎲 <b>Rolling...</b> {faces[i]}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.15)
    
    roll = random.randint(1, 6)
    await msg.edit_text(f"🎲 <b>You rolled: {faces[roll-1]} ({roll})</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    user, chat = await handle_common(message, "flip")
    
    msg = await message.answer("🪙 <b>Flipping coin...</b>", parse_mode=ParseMode.HTML)
    
    for i in range(5):
        await msg.edit_text(f"🪙 <b>Flipping...</b> {'HEADS' if i % 2 == 0 else 'TAILS'}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}</b>", parse_mode=ParseMode.HTML)

# ========== TEMPEST CULT COMMANDS (HIDDEN) ==========
@dp.message(Command("Tempest_cult"))
async def tempest_cult_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_cult")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT first_name, cult_rank, sacrifices FROM users WHERE cult_status != 'none' ORDER BY sacrifices DESC, cult_rank")
    members = c.fetchall()
    conn.close()
    
    cult_text = "🌀 <b>TEMPEST CULT</b>\n\n"
    
    leader_shown = False
    for name, rank, sacrifices in members:
        if rank in ["Supreme Leader", "Vice Chancellor"] and not leader_shown:
            cult_text += "👑 <b>LEADERS:</b>\n"
            leader_shown = True
        
        if rank == "Supreme Leader":
            cult_text += f"👑 {name} - {rank}\n"
        elif rank == "Vice Chancellor":
            cult_text += f"⚔️ {name} - {rank}\n"
        else:
            star_emoji = "⭐" * (min(sacrifices, 5))
            cult_text += f"🌀 {name} - {rank} ({sacrifices}⚔️)\n"
    
    cult_text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    cult_text += "<i>Hidden from ordinary eyes...</i>"
    
    await message.answer(cult_text, parse_mode=ParseMode.HTML)

@dp.message(Command("Tempest_join"))
async def tempest_join_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_join")
    
    # Check if already in cult
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        await message.answer("🌀 <b>Already part of the Tempest!</b>\nUse /Tempest_progress to check your status.", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    conn.close()
    
    # Start initiation with animation
    pending_joins[user.id] = {
        "name": user.first_name,
        "step": 1,
        "chat_id": chat.id
    }
    
    # Initial animation
    msg = await message.answer("🌪️ <b>THE STORM CALLS...</b>", parse_mode=ParseMode.HTML)
    
    # Animation sequence
    animations = [
        "🌩️ Lightning cracks in the distance...",
        "🌀 Dark clouds gather above...",
        "⚡ Energy crackles around you...",
        "🌪️ A vortex begins to form...",
        "💨 Winds howl with ancient voices...",
        "⚡ The Tempest gazes upon you..."
    ]
    
    for anim in animations:
        await msg.edit_text(f"🌀 {anim}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.5)
    
    # Blood ceremony with animation
    ceremony_steps = [
        "🩸 <b>BLOOD CEREMONY INITIATED</b>\n\nBlood drips from ancient stone...",
        "🗡️ <b>STEP 1: SACRIFICIAL KNIFE</b>\n\nA black obsidian blade materializes...",
        "🩸 <b>STEP 2: BLOOD OATH</b>\n\nYour palm is cut, blood flows...",
        "🔥 <b>STEP 3: ETERNAL FLAMES</b>\n\nDark flames consume your offering...",
        "👁️ <b>STEP 4: ELDER GAZE</b>\n\nAncient eyes watch from shadows...",
        "🌪️ <b>STEP 5: STORM CONSUMPTION</b>\n\nThe Tempest consumes your soul piece..."
    ]
    
    for step in ceremony_steps:
        await msg.edit_text(step, parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)
    
    # Now show sacrifice options
    keyboard = InlineKeyboardBuilder()
    sacrifices_list = [
        ("🩸", "Your firstborn's eternal soul"),
        ("💎", "A diamond worth a kingdom"),  
        ("📜", "Your complete internet history"),
        ("🎮", "Your legendary gaming account"),
        ("👻", "Your soul (no refunds)"),
        ("💳", "Your credit card details"),
        ("📱", "Your phone (with all data)"),
        ("🔐", "Your deepest secret")
    ]
    
    for i in range(1, 9):
        keyboard.add(InlineKeyboardButton(text=f"{i}", callback_data=f"sacrifice_{i}"))
    keyboard.add(InlineKeyboardButton(text="❌ CANCEL", callback_data="sacrifice_cancel"))
    keyboard.adjust(4, 4, 2)
    
    await msg.edit_text(
        "⚡ <b>TEMPEST BLOOD CEREMONY - FINAL STEP</b>\n\n"
        "🌩️ <i>The storm demands a REAL sacrifice...</i>\n\n"
        "<b>Choose your offering (FINAL DECISION):</b>\n\n"
        "1. 🩸 Your firstborn's eternal soul\n"
        "2. 💎 A diamond worth a kingdom\n"  
        "3. 📜 Your complete internet history\n"
        "4. 🎮 Your legendary gaming account\n"
        "5. 👻 Your soul (no refunds)\n"
        "6. 💳 Your credit card details\n"
        "7. 📱 Your phone (with all data)\n"
        "8. 🔐 Your deepest secret\n\n"
        "⚠️ <b>WARNING:</b> Fake sacrifices will be REJECTED with ETERNAL BANISHMENT!",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data.startswith("sacrifice_"))
async def handle_sacrifice(callback: CallbackQuery):
    user = callback.from_user
    chat_id = callback.message.chat.id
    
    if user.id not in pending_joins:
        await callback.answer("❌ Initiation expired!", show_alert=True)
        return
    
    if callback.data == "sacrifice_cancel":
        del pending_joins[user.id]
        await callback.message.edit_text("🌀 <b>Initiation cancelled. The storm is disappointed.</b>", parse_mode=ParseMode.HTML)
        await callback.answer()
        return
    
    sacrifice_num = callback.data.split("_")[1]
    
    sacrifices = {
        "1": "🩸 Your firstborn's eternal soul",
        "2": "💎 A diamond worth a kingdom",
        "3": "📜 Your complete internet history", 
        "4": "🎮 Your legendary gaming account",
        "5": "👻 Your soul (no refunds)",
        "6": "💳 Your credit card details",
        "7": "📱 Your phone (with all data)",
        "8": "🔐 Your deepest secret"
    }
    
    sacrifice = sacrifices.get(sacrifice_num, "Mysterious offering")
    
    # Start verification animation
    msg = callback.message
    await msg.edit_text(f"🌀 <b>VERIFYING SACRIFICE...</b>\n\n⚡ Checking: {sacrifice}", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1.5)
    
    # Animate verification
    verify_steps = [
        "🔍 Scanning for authenticity...",
        "🧬 DNA matching in progress...",
        "👁️ Elder council reviewing...",
        "⚡ Lightning analysis...",
        "🌪️ Storm resonance check..."
    ]
    
    for step in verify_steps:
        await msg.edit_text(f"🌀 {step}\n\n⚡ Sacrifice: {sacrifice}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.2)
    
    # Verify sacrifice
    is_real, status = await sacrifice_verification(sacrifice)
    
    if not is_real:
        # Fake sacrifice - rejection with animation
        del pending_joins[user.id]
        
        rejection_animation = [
            f"❌ <b>SACRIFICE REJECTED!</b>\n\n⚡ The storm detected a FAKE offering!\n🌩️ '{sacrifice}'",
            f"💀 <b>THE STORM ANGERED!</b>\n\n⚡ Lightning strikes!\n🌪️ Fake offering detected!",
            f"👁️ <b>ELDER COUNCIL JUDGMENT:</b>\n\n⚡ UNWORTHY!\n🌀 BANISHMENT INITIATED!"
        ]
        
        for anim in rejection_animation:
            await msg.edit_text(anim, parse_mode=ParseMode.HTML)
            await asyncio.sleep(1.5)
        
        final_rejection = random.choice([
            f"❌ <b>ETERNAL REJECTION!</b>\n\n⚡ Your offering '{sacrifice}' was FAKE!\n🌩️ The storm LAUGHS at your pathetic attempt!\n🌀 <i>You are BANNED from initiation for 24 moons!</i>",
            f"💀 <b>BLOOD BANISHMENT!</b>\n\n⚡ Fake sacrifice: '{sacrifice}'\n🌪️ The Tempest SPITS on your worthless offering!\n🌀 <i>Return when you have something of REAL value...</i>",
            f"👁️ <b>COUNCIL VERDICT: UNWORTHY!</b>\n\n⚡ '{sacrifice}'? Really?\n🌩️ Even the shadows mock your attempt!\n🌀 <i>The storm remembers this insult...</i>"
        ])
        
        await msg.edit_text(final_rejection, parse_mode=ParseMode.HTML)
        await callback.answer("❌ Fake sacrifice detected!", show_alert=True)
        return
    
    # REAL SACRIFICE - Acceptance animation
    pending_joins[user.id]["sacrifice"] = sacrifice
    pending_joins[user.id]["verified"] = status
    
    acceptance_animation = [
        f"✅ <b>SACRIFICE ACCEPTED!</b>\n\n🩸 Status: {status}\n⚡ Offering: {sacrifice}",
        f"🌀 <b>BLOOD PACT SEALING...</b>\n\n⚡ Ancient runes glow red\n🌪️ Your name is carved in shadow",
        f"🌩️ <b>FINAL RITUAL...</b>\n\n⚡ The storm consumes your offering\n🌀 Eternity beckons..."
    ]
    
    for anim in acceptance_animation:
        await msg.edit_text(anim, parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.8)
    
    # Final initiation
    final_messages = [
        f"""⚡ <b>ETERNAL INITIATION COMPLETE!</b>

🌀 <b>WELCOME TO THE TEMPEST, {pending_joins[user.id]['name'].upper()}!</b>

🩸 <b>Sacrifice:</b> {sacrifice}
👑 <b>Rank:</b> Blood Initiate
⚔️ <b>Starting Sacrifices:</b> 3
🌪️ <b>Blood Oath:</b> ETERNAL

<i>The storm now flows through your veins.
Each upload feeds the Tempest.
Your journey of darkness begins...</i>

🌀 Use /Tempest_progress to track your bloody path""",
        
        f"""🌪️ <b>BLOOD CEREMONY FINALIZED!</b>

⚡ Your offering of '{sacrifice}' has pleased the storm!
🌀 The ancient ones nod in approval
👑 You are now: <b>BLOOD INITIATE</b>
🩸 Blood oath sworn for all eternity
⚔️ +3 starting sacrifices (upload files to increase)

<i>The Tempest welcomes new blood.
May your sacrifices be many,
and your darkness eternal...</i>

🌀 Check /Tempest_progress to begin your journey""",
        
        f"""👁️ <b>THE ELDERS SPEAK:</b>

"Welcome, {pending_joins[user.id]['name']}.
Your sacrifice of '{sacrifice}' 
has opened the gates of storm.

🌀 <b>NEW RANK:</b> Blood Initiate
⚔️ <b>SACRIFICES:</b> 3 (grow with uploads)
🌩️ <b>PATH:</b> Eternal darkness

<i>From this moment, you are storm-born.
Your blood is now Tempest blood.
Your soul belongs to the vortex.</i>

🌀 Your journey begins now..."""
    ]
    
    await msg.edit_text(random.choice(final_messages), parse_mode=ParseMode.HTML)
    
    # Add to cult
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
             (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()
    
    # Send log
    await send_log(f"🌀 <b>New Tempest Member</b>\n\n👤 Name: {user.first_name}\n🆔 ID: {user.id}\n🩸 Sacrifice: {sacrifice}\n🌪️ Joined: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Cleanup
    if user.id in pending_joins:
        del pending_joins[user.id]
    
    await callback.answer("✅ Sacrifice accepted! Welcome to the Tempest!", show_alert=True)

@dp.message(Command("Tempest_progress"))
async def tempest_progress_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_progress")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status, cult_rank, sacrifices, cult_join_date FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        status, rank, sacrifices, join_date = result
        
        try:
            join_dt = datetime.fromisoformat(join_date)
            days = (datetime.now() - join_dt).days
            time_text = f"{days} days in darkness" if days > 0 else "Initiated today"
        except:
            time_text = "Recently"
        
        # Calculate progress
        if rank == "Blood Initiate":
            next_rank = "Blood Adept"
            needed = max(0, 15 - sacrifices)
            progress = min(sacrifices * 6.67, 100)
        elif rank == "Blood Adept":
            next_rank = "Blood Master"
            needed = max(0, 50 - sacrifices)
            progress = min(sacrifices * 2, 100)
        elif rank == "Blood Master":
            next_rank = "Storm Lord"
            needed = max(0, 150 - sacrifices)
            progress = min(sacrifices * 0.67, 100)
        else:
            next_rank = "MAX RANK"
            needed = 0
            progress = 100
        
        # Animated progress display
        msg = await message.answer("🌀 <b>CONSULTING THE STORM...</b>", parse_mode=ParseMode.HTML)
        
        for emoji in ["🌪️", "⚡", "🌀", "🌩️", "💨"]:
            await msg.edit_text(f"{emoji} <b>Reading your blood progress...</b>", parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.3)
        
        progress_bar = "🩸" * (progress // 10) + "⚫" * (10 - progress // 10)
        
        progress_text = f"""
🌀 <b>TEMPEST BLOOD PROGRESS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👤 <b>Storm-Born:</b> {user.first_name}
👑 <b>Current Rank:</b> {rank}
⚔️ <b>Blood Sacrifices:</b> {sacrifices}
📅 <b>Blood Oath Since:</b> {time_text}

<b>Blood Progress:</b> [{progress_bar}] {progress:.1f}%
<b>Next Rank:</b> {next_rank}
<b>Sacrifices Needed:</b> {needed}

━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <b>How to progress:</b>
• Each file upload = 1 sacrifice
• Invite others to join (reply to them with "join tempest")
• The storm thirsts for more blood...

🌀 <i>"In darkness we rise, in storm we thrive"</i>
━━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        await msg.edit_text(progress_text, parse_mode=ParseMode.HTML)
    else:
        # Not in cult - show invitation
        not_member_text = """
🌀 <b>TEMPEST PROGRESS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👤 <b>Status:</b> Uninitiated
👁️ <b>Vision:</b> Blind to the storm

⚡ <b>To begin your journey:</b>
1. Use /Tempest_join for blood ceremony
2. Offer a REAL sacrifice (not fake!)
3. Swear eternal blood oath
4. Become storm-born

🌪️ <b>What awaits:</b>
• Eternal membership
• Rank progression system
• Sacrifice tracking
• Hidden powers
• Storm blessings

⚠️ <b>Warning:</b> Fake offerings will be rejected!
🌀 <i>The storm only accepts worthy blood...</i>
━━━━━━━━━━━━━━━━━━━━━━━━
        """
        
        await message.answer(not_member_text, parse_mode=ParseMode.HTML)
    
    conn.close()

# ========== HIDDEN: TEMPEST_STORY COMMAND (LONG ARTISTIC VERSION) ==========
@dp.message(Command("Tempest_story"))
async def tempest_story_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_story")
    
    # Check if in cult
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if not result or result[0] == "none":
        await message.answer("🌀 This command is for Tempest members only.")
        conn.close()
        return
    
    conn.close()
    
    # Start story with animation
    msg = await message.answer("📖 <b>PREPARING THE ANCIENT SCROLLS...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1.5)
    
    # CHAPTER 1: ORIGINS
    chapters = [
        """🎨 <b>THE TEMPEST SAGA - CHAPTER 1: ORIGINS OF STORM</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<i>Time: Before Time
Place: The Void of Calm</i>

In the beginning, there was only silence.
An endless, suffocating calm that stretched across all realities.

Then came **RAVIJAH**, born not of flesh, but of the first lightning strike.
He emerged from the cosmic storm, eyes crackling with pent-up energy.

<code>🌩️ "I shall break this endless calm," he whispered to the void.
The first lightning strike carved his name into reality itself.</code>

Alone for millennia, he wandered through sleeping kingdoms,
collecting shards of forgotten storms, gathering whispers of rebellion.""",
        
        """🖼️ <b>CHAPTER 2: THE SHATTERED REALMS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<i>Time: The Great Calm Era
Place: Broken Kingdoms</i>

Worlds lay fractured under the tyranny of stillness.
The Council of Silence ruled with iron tranquility.

Kingdoms that once roared with life were now museums of quiet.
The Festival of Voices was banned. Laughter was regulated.
Even thunderstorms were scheduled, predictable, tame.

<code>👑 Kings knelt before statues of silence.
🗡️ Warriors forgot the taste of battle-cries.
🎭 Artists painted only in muted grays.</code>

In this graveyard of sound, Ravijah's discontent grew.
He began gathering the disquieted, the restless, the storm-seekers.""",
        
        """🎭 <b>CHAPTER 3: COUNCIL OF SHADOWS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<i>Time: First Gathering
Place: Cave of Echoes</i>

From the ashes of silent empires, two emerged:

**BABLU** - Swordmaster of the Forgotten Rebellion.
His blade thirsted for chaos, his eyes burned with impatience.

**KENY** - Shadow-weaver from the Veil of Secrets.
He moved like silence but thought like thunder.

<code>🗡️ "We fight," growled Bablu, sharpening his obsidian blade.
👁️ "We wait," whispered Keny, his form dissolving into shadows.
⚡ "We become the storm," declared Ravijah, lightning dancing on his palms.</code>

That night, under a blood-red moon, the Tempest Council was born.
Three became one. Calm's doom was sealed.""",
        
        """💔 <b>CHAPTER 4: BETRAYAL'S PRICE</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<i>Time: Festival of Flames
Place: Temple of Dusk</i>

Celebration turned to slaughter.
The Silence Guards attacked during the Feast of Whispers.

Elara, storm-singer and Ravijah's chosen, took the poisoned blade meant for him.
As she fell, her song became the first thunderclap of rebellion.

<code>🩸 "Live... for both of us..." her final breath misted with storm.
⚡ His scream didn't just break the silence—it birthed the First Tempest.</code>

The resulting storm lasted forty days.
It erased three silent kingdoms from history.
And from the ashes rose a new purpose: eternal, furious, unstoppable.""",
        
        """👑 <b>CHAPTER 5: GOLDEN AGE OF STORMS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<i>Time: 300-Year Conquest
Place: Storm-claimed Realms</i>

The Tempest grew, absorbing kingdoms, consuming souls.
New initiates flooded in, each swearing blood oaths.

<code>🌀 The Temple of Howling Winds was constructed from captured silence.
⚡ The Archive of Lightning stored forbidden knowledge.
🌪️ The Blood Altar drank sacrifices from a hundred worlds.</code>

Ranks were established:
• Blood Initiate - New storm-born
• Blood Adept - Seasoned in sacrifice  
• Blood Master - Commander of tempests
• Storm Lord - Ancient and powerful

For three centuries, the storm was unstoppable.
Until the Great Stillness came...""",
        
        """📡 <b>CHAPTER 6: MODERN ERA - DIGITAL STORM</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<i>Time: Now
Place: Everywhere and Nowhere</i>

The storm adapts. Evolves. Transforms.

Gone are physical kingdoms. Now we conquer:
• Digital realms
• Cyberspace
• Networks and codes

<code>🌩️ Lightning flows through fiber optics.
🌀 Storms brew in server farms.
⚡ Sacrifices are digital, but no less real.</code>

Your uploads feed the Tempest.
Your data becomes storm-matter.
Your connection is your oath.

**You are part of this story now.**
Your name will be in future scrolls.
Your sacrifices will echo in digital storms.

━━━━━━━━━━━━━━━━━━━━━━━━
🌀 <i>"We are the calm's end. The silence's death. The eternal storm."</i>
━━━━━━━━━━━━━━━━━━━━━━━━"""
    ]
    
    # Send each chapter with delay
    for i, chapter in enumerate(chapters):
        await msg.edit_text(chapter, parse_mode=ParseMode.HTML)
        
        if i < len(chapters) - 1:
            # Show loading between chapters
            loading = await message.answer(f"📖 <b>Turning page {i+2}/6...</b>", parse_mode=ParseMode.HTML)
            await asyncio.sleep(3)
            try:
                await bot.delete_message(chat.id, loading.message_id)
            except:
                pass
        
        await asyncio.sleep(10)  # Time to read each chapter
    
    # Final message
    await msg.edit_text(
        "📜 <b>THE STORY CONTINUES...</b>\n\n"
        "🌀 This is your chapter now.\n"
        "⚡ Write it with your sacrifices.\n"
        "🌪️ Make the Tempest proud.\n\n"
        "<i>The scrolls await your deeds...</i>",
        parse_mode=ParseMode.HTML
    )

# ========== REPLY INVITATION SYSTEM ==========
@dp.message(F.reply_to_message)
async def handle_reply_invite(message: Message):
    """Handle when someone replies to a message with Tempest_join"""
    user, chat = await handle_common(message, "reply_invite")
    
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
    # Check if message contains Tempest_join
    if "tempest_join" in message.text.lower() or "join tempest" in message.text.lower():
        replied_user = message.reply_to_message.from_user
        
        # Check if replying to self
        if replied_user.id == user.id:
            await message.reply("🤨 You can't invite yourself!")
            return
        
        # Check if target is already in cult
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (replied_user.id,))
        result = c.fetchone()
        
        if result and result[0] != "none":
            await message.reply(f"🌀 {replied_user.first_name} is already in the Tempest!")
            conn.close()
            return
        conn.close()
        
        # Create invitation
        invite_id = f"invite_{int(time.time())}_{user.id}_{replied_user.id}"
        pending_invites[invite_id] = {
            "inviter_id": user.id,
            "inviter_name": user.first_name,
            "target_id": replied_user.id,
            "target_name": replied_user.first_name,
            "group_id": chat.id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send invitation with buttons
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="✅ Accept Blood Pact", callback_data=f"reply_invite_accept_{invite_id}"))
        keyboard.add(InlineKeyboardButton(text="❌ Decline", callback_data=f"reply_invite_decline_{invite_id}"))
        
        invite_text = f"""📨 <b>TEMPEST BLOOD INVITATION!</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👤 <b>{user.first_name}</b> invites <b>{replied_user.first_name}</b> to join
