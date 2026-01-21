# ========== CACHE BUSTER - FORCE RAILWAY UPDATE ==========
import sys
print("=" * 50)
print("🚀 BOT DEPLOYED: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("🔧 Version: Tempest-Anime-Edition-2024")
print("=" * 50)

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
    
    # Start initiation with anime-style animation
    pending_joins[user.id] = {
        "name": user.first_name,
        "step": 1,
        "chat_id": chat.id
    }
    
    # Initial anime-style animation
    msg = await message.answer("🎌 <b>ANIME INITIATION SEQUENCE STARTING...</b>", parse_mode=ParseMode.HTML)
    
    # Anime opening sequence
    anime_openings = [
        "🎬 <b>Opening Scene...</b>\n\n⚡ Lightning cracks across the screen",
        "🎵 <b>Epic Music Swells</b>\n\n🌀 Winds howl with ancient power",
        "✨ <b>Character Introduction</b>\n\n👤 Protagonist: " + user.first_name,
        "🌪️ <b>The Storm Calls...</b>\n\n⚡ Your destiny awaits...",
        "🎭 <b>Transformation Sequence</b>\n\n🌀 Power flows through you..."
    ]
    
    for scene in anime_openings:
        await msg.edit_text(scene, parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.2)
    
    # Anime-style ceremony
    ceremony_steps = [
        """🗡️ <b>ANIME CEREMONY - STAGE 1</b>
        
        ⚔️ Your character stands before the ancient temple
        🌀 Dark clouds gather dramatically
        ⚡ Lightning illuminates your determined face""",
        
        """🎨 <b>STAGE 2 - OFFERING SELECTION</b>
        
        🎭 A mystical interface appears
        💎 Glowing options float before you
        ✨ Choose your tribute wisely...""",
        
        """✨ <b>STAGE 3 - POWER AWAKENING</b>
        
        🌟 Your body begins to glow
        ⚡ Energy crackles around you
        🌀 The storm recognizes your potential""",
        
        """🎭 <b>STAGE 4 - CHARACTER DEVELOPMENT</b>
        
        📜 Your backstory unfolds
        💪 Strength grows within
        🎯 Purpose becomes clear""",
        
        """⚡ <b>STAGE 5 - FINAL TRANSFORMATION</b>
        
        🌪️ The vortex accepts you
        🎨 Your true colors shine
        🌀 You become storm-born"""
    ]
    
    for stage in ceremony_steps:
        await msg.edit_text(stage, parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.5)
    
    # Now show offering options
    keyboard = InlineKeyboardBuilder()
    offerings_list = [
        ("⚡", "Lightning Fragment - Ancient power source"),
        ("🌀", "Storm Core - Heart of the tempest"),  
        ("🎭", "Character Development - Your growth"),
        ("✨", "Anime Protagonist Energy - Main character power"),
        ("🗡️", "Legendary Sword - Symbol of strength"),
        ("👑", "Crown of Storms - Royal authority"),
        ("📜", "Sacred Scroll - Ancient knowledge"),
        ("💎", "Crystal of Destiny - Fate itself")
    ]
    
    for i in range(1, 9):
        keyboard.add(InlineKeyboardButton(text=f"{i}", callback_data=f"offering_{i}"))
    keyboard.add(InlineKeyboardButton(text="❌ CANCEL", callback_data="offering_cancel"))
    keyboard.adjust(4, 4, 2)
    
    await msg.edit_text(
        """🎌 <b>ANIME-STYLE OFFERING SELECTION</b>

<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
🎮 <b>Choose your character's power source:</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>

1. ⚡ <b>Lightning Fragment</b> - Ancient power source
2. 🌀 <b>Storm Core</b> - Heart of the tempest  
3. 🎭 <b>Character Development</b> - Your growth arc
4. ✨ <b>Anime Protagonist Energy</b> - Main character power
5. 🗡️ <b>Legendary Sword</b> - Symbol of strength
6. 👑 <b>Crown of Storms</b> - Royal authority
7. 📜 <b>Sacred Scroll</b> - Ancient knowledge
8. 💎 <b>Crystal of Destiny</b> - Fate itself

<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
⚠️ <b>ANIME RULE:</b> Choose what defines your character!
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>""",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data.startswith("offering_"))
async def handle_offering(callback: CallbackQuery):
    user = callback.from_user
    chat_id = callback.message.chat.id
    
    if user.id not in pending_joins:
        await callback.answer("❌ Initiation expired!", show_alert=True)
        return
    
    if callback.data == "offering_cancel":
        del pending_joins[user.id]
        await callback.message.edit_text("🎬 <b>Scene Canceled</b>\n\nThe anime fades to black...", parse_mode=ParseMode.HTML)
        await callback.answer()
        return
    
    offering_num = callback.data.split("_")[1]
    
    offerings = {
        "1": "⚡ Lightning Fragment - Ancient power source",
        "2": "🌀 Storm Core - Heart of the tempest",
        "3": "🎭 Character Development - Your growth arc", 
        "4": "✨ Anime Protagonist Energy - Main character power",
        "5": "🗡️ Legendary Sword - Symbol of strength",
        "6": "👑 Crown of Storms - Royal authority",
        "7": "📜 Sacred Scroll - Ancient knowledge",
        "8": "💎 Crystal of Destiny - Fate itself"
    }
    
    offering = offerings.get(offering_num, "Mystical Offering")
    
    # Start anime-style verification
    msg = callback.message
    await msg.edit_text(f"🔍 <b>ANALYZING OFFERING...</b>\n\n✨ Checking: {offering}", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1.5)
    
    # Anime analysis sequence
    analysis_steps = [
        "⚡ <b>Power Level Scanning...</b>\n\n🌀 Measuring spiritual energy",
        "🎨 <b>Character Compatibility...</b>\n\n✨ Checking your protagonist traits",
        "📊 <b>Destiny Alignment...</b>\n\n💫 Calculating fate threads",
        "🌟 <b>Anime Trope Verification...</b>\n\n🎭 Checking for clichés",
        "🌀 <b>Storm Resonance...</b>\n\n🌪️ Testing tempest compatibility"
    ]
    
    for step in analysis_steps:
        await msg.edit_text(step, parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.2)
    
    # Verify offering - 80% success rate
    is_valid = random.random() < 0.8
    
    if not is_valid:
        # Invalid offering - anime rejection
        del pending_joins[user.id]
        
        rejection_scenes = [
            f"❌ <b>OFFERING REJECTED!</b>\n\n🎭 '{offering}' doesn't fit your character arc!\n🌀 Try something more authentic...",
            f"💥 <b>POWER CLASH!</b>\n\n⚡ Your offering '{offering}' caused an energy overload!\n✨ The storm needs balance...",
            f"🎬 <b>PLOT TWIST FAILED!</b>\n\n🌀 '{offering}' created a plot hole!\n📜 The scriptwriters are disappointed..."
        ]
        
        for scene in rejection_scenes:
            await msg.edit_text(scene, parse_mode=ParseMode.HTML)
            await asyncio.sleep(1.5)
        
        await callback.answer("❌ Offering rejected! Try a different one!", show_alert=True)
        return
    
    # VALID OFFERING - Anime acceptance
    pending_joins[user.id]["offering"] = offering
    
    acceptance_scenes = [
        f"✅ <b>OFFERING ACCEPTED!</b>\n\n✨ {offering} perfectly matches your character!",
        f"🌟 <b>POWER SURGE!</b>\n\n⚡ Your offering resonates with the storm!",
        f"🎭 <b>CHARACTER DEVELOPMENT!</b>\n\n🌀 You've unlocked new potential!"
    ]
    
    for scene in acceptance_scenes:
        await msg.edit_text(scene, parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.5)
    
    # Anime transformation sequence
    await msg.edit_text("🌀 <b>FINAL TRANSFORMATION SEQUENCE!</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    
    transformation_frames = [
        "✨ Your body begins to glow with blue energy...",
        "⚡ Lightning dances around your fingertips...",
        "🌀 Winds swirl, lifting your hair dramatically...",
        "🌟 Eyes flash with storm power...",
        "💫 A spectral aura envelops you...",
        "🌪️ The tempest accepts you as its own..."
    ]
    
    for frame in transformation_frames:
        await msg.edit_text(f"🌀 <b>TRANSFORMING...</b>\n\n{frame}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.2)
    
    # Final anime scene
    final_scenes = [
        f"""🎬 <b>ANIME TRANSFORMATION COMPLETE!</b>

<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
👤 <b>NEW CHARACTER:</b> {pending_joins[user.id]['name']}
⚡ <b>POWER SOURCE:</b> {offering}
🌀 <b>NEW RANK:</b> Storm Initiate
✨ <b>POWER LEVEL:</b> 3,000+
🎭 <b>CHARACTER ARC:</b> BEGINNING
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>

<i>You are now a storm-born anime protagonist!
Your journey of power and destiny begins...</i>

🌀 Use /Tempest_progress to track your character growth""",
        
        f"""✨ <b>NEW ANIME PROTAGONIST CREATED!</b>

<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
🌟 <b>WELCOME TO THE TEMPEST,</b>
   <b>{pending_joins[user.id]['name'].upper()}!</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>

🎨 <b>Character Sheet:</b>
• Rank: Storm Initiate  
• Power: {offering}
• Starting Power: 3,000
• Next Goal: 15,000

<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
📺 <i>Your anime series has begun!
Each upload = +1 to your power level!</i>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>"""
    ]
    
    await msg.edit_text(random.choice(final_scenes), parse_mode=ParseMode.HTML)
    
    # Add to cult in database
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Storm Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
             (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()
    
    # Send log
    await send_log(f"🌀 <b>New Tempest Member</b>\n\n👤 Name: {user.first_name}\n🆔 ID: {user.id}\n✨ Offering: {offering}\n🎬 Joined: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Cleanup
    if user.id in pending_joins:
        del pending_joins[user.id]
    
    await callback.answer("✅ Transformation complete! Welcome to the Tempest!", show_alert=True)

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
            time_text = f"{days} episodes" if days > 0 else "Today's episode"
        except:
            time_text = "Recently"
        
        # Calculate progress
        if rank == "Storm Initiate":
            next_rank = "Storm Adept"
            needed = max(0, 15 - sacrifices)
            progress = min(sacrifices * 6.67, 100)
            power_level = 3000 + (sacrifices * 1000)
        elif rank == "Storm Adept":
            next_rank = "Storm Master"
            needed = max(0, 50 - sacrifices)
            progress = min(sacrifices * 2, 100)
            power_level = 15000 + (sacrifices * 500)
        elif rank == "Storm Master":
            next_rank = "Storm Lord"
            needed = max(0, 150 - sacrifices)
            progress = min(sacrifices * 0.67, 100)
            power_level = 50000 + (sacrifices * 200)
        else:
            next_rank = "MAX RANK"
            needed = 0
            progress = 100
            power_level = 99999
        
        # Anime-style progress display
        msg = await message.answer("📺 <b>LOADING CHARACTER STATS...</b>", parse_mode=ParseMode.HTML)
        
        for emoji in ["🌀", "⚡", "✨", "🌟", "🎬"]:
            await msg.edit_text(f"{emoji} <b>Analyzing anime power levels...</b>", parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.3)
        
        # Create anime-style progress bar
        progress_bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
        
        progress_text = f"""
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
🎬 <b>ANIME CHARACTER PROGRESS</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>

👤 <b>Protagonist:</b> {user.first_name}
🎭 <b>Current Rank:</b> {rank}
⚡ <b>Power Level:</b> {power_level:,}
✨ <b>Story Progress:</b> {time_text}

<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
📊 <b>POWER PROGRESS:</b>
[{progress_bar}] {progress:.1f}%
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>

<b>Next Rank:</b> {next_rank}
<b>Power Needed:</b> {needed} more uploads

<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
🎮 <b>How to level up:</b>
• Each file upload = +1 power
• Invite others (reply "join tempest")
• Complete character arcs
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>

📺 <i>"In the storm, we find our true power!"</i>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
        """
        
        await msg.edit_text(progress_text, parse_mode=ParseMode.HTML)
    else:
        # Not in cult - anime-style invitation
        not_member_text = """
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
🎬 <b>ANIME CHARACTER SELECTION</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>

👤 <b>Status:</b> Normal Human
👁️ <b>Vision:</b> Can't see the storm

⚡ <b>To begin your anime journey:</b>
1. Use /Tempest_join for power awakening
2. Choose your character's power source
3. Undergo anime transformation
4. Become storm-born protagonist

🌪️ <b>What awaits:</b>
• Anime-style progression
• Power level system
• Character development
• Storm abilities
• Epic story arcs

⚠️ <b>Warning:</b> Choose your power wisely!
🌀 <i>Your anime destiny begins now...</i>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
        """
        
        await message.answer(not_member_text, parse_mode=ParseMode.HTML)
    
    conn.close()

# ========== HIDDEN: TEMPEST_STORY COMMAND (ANIME VERSION) ==========
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
    
    # Start anime-style story with ASCII art
    msg = await message.answer("📺 <b>LOADING ANIME EPISODE 1...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1.5)
    
    # EPISODE 1: THE PROLOGUE
    episodes = [
        """🎬 <b>EPISODE 1: THE STORM'S CALL</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
<i>Screen fades in from black...</i>

╔══════════════════════╗
║    🌩️⚡🌀            ║
║   THE TEMPEST SAGA   ║
║     Season 1         ║
╚══════════════════════╝

🎭 <b>SCENE START:</b>
A quiet village, peaceful but stagnant.
Our hero, a young soul, feels empty.
Then... a lightning strike changes everything.

<code>"I need... more power!"</code>""",
        
        """🎬 <b>EPISODE 2: MEETING RAVIJAH</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
ASCII ART:
    ⚡     🎭     🌪️
   /🔥\   /👑\   /🌀\
  /   \  /   \  /   \

<i>Dramatic entrance music plays...</i>

RAVIJAH appears in a burst of lightning!
Silver hair, electric blue eyes, crackling aura.

<code>"You seek power? I am power."</code>""",
        
        """🎬 <b>EPISODE 3: THE TRIO FORMS</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
ASCII FIGHT SCENE:
      🗡️     vs     🛡️
    /😠\          /😐\
   / | \        /  |  \
     |            |

BABLU charges, sword blazing!
KENY counters with shadow clones!
RAVIJAH watches, lightning ready.

<code>"Three become one. The storm unites us."</code>""",
        
        """🎬 <b>EPISODE 4: FIRST BATTLE</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
ANIME BATTLE ART:
🌩️🌩️🌩️     ⚡⚡⚡
  🌀🌀🌀   vs   💥💥💥
⚔️⚔️⚔️     🛡️🛡️🛡️

The Council of Silence attacks!
Lightning vs. Stillness!
Swords clash! Magic explodes!

<code>"This... is our power!"</code>""",
        
        """🎬 <b>EPISODE 5: GROWING STRONGER</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
POWER-UP SEQUENCE:
✨✨✨✨✨
⚡🌀⚡🌀⚡
🎭💪🎭💪🎭

Training montage!
Power levels rising!
New abilities unlocked!

<code>"Each day, we grow. Each storm, we change."</code>""",
        
        """🎬 <b>EPISODE 6: MODERN ERA</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
DIGITAL TRANSFORMATION:
💻🌩️💻🌩️💻
📱⚡📱⚡📱
🌐🌀🌐🌀🌐

The storm evolves!
Digital lightning!
Network tempests!

<code>"Now... we are everywhere. Now... we are forever."</code>"""
    ]
    
    # Send each episode with anime effects
    for i, episode in enumerate(episodes):
        await msg.edit_text(episode, parse_mode=ParseMode.HTML)
        
        if i < len(episodes) - 1:
            # Show "Next Episode" screen
            loading = await message.answer(f"📺 <b>EPISODE {i+2} LOADING...</b>\n\n✨ Next episode in 3...", parse_mode=ParseMode.HTML)
            await asyncio.sleep(3)
            try:
                await bot.delete_message(chat.id, loading.message_id)
            except:
                pass
        
        await asyncio.sleep(8)  # Time to read each episode
    
    # Final message with ASCII art
    final_art = """
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
         THE END
          ...FOR NOW
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>

╔══════════════════════╗
║      ✨⚡🎭          ║
║   YOUR STORY AWAITS  ║
║                      ║
║  Continue the saga!  ║
║  Make your mark!     ║
║  Become legendary!   ║
╚══════════════════════╝

<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
🌀 <i>Your character arc continues...</i>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
"""
    
    await msg.edit_text(final_art, parse_mode=ParseMode.HTML)

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
        keyboard.add(InlineKeyboardButton(text="✅ Accept Anime Power", callback_data=f"reply_invite_accept_{invite_id}"))
        keyboard.add(InlineKeyboardButton(text="❌ Decline", callback_data=f"reply_invite_decline_{invite_id}"))
        
        invite_text = f"""📨 <b>ANIME POWER INVITATION!</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>

👤 <b>{user.first_name}</b> invites <b>{replied_user.first_name}</b> 
   to join the Tempest Anime!
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>

🎬 <b>What awaits:</b>
• ⚡ Anime-style transformation
• 🌀 Storm power awakening
• ✨ Character development
• 🎭 Epic story arcs
• 💪 Power level progression

<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>
🎮 <b>Will you accept the protagonist role?</b>
<code>━━━━━━━━━━━━━━━━━━━━━━━━</code>

<i>Invitation expires in 2 minutes...</i>"""
        
        invite_msg = await message.reply(invite_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
        
        # Auto-delete after 2 minutes
        await asyncio.sleep(120)
        try:
            await bot.delete_message(chat.id, invite_msg.message_id)
            if invite_id in pending_invites:
                del pending_invites[invite_id]
        except:
            pass

@dp.callback_query(F.data.startswith("reply_invite_"))
async def handle_reply_invite_response(callback: CallbackQuery):
    """Handle reply invite responses"""
    data_parts = callback.data.split("_")
    if len(data_parts) < 5:
        await callback.answer("Invalid invite!")
        return
    
    action = data_parts[3]
    invite_id = "_".join(data_parts[4:])
    
    if invite_id not in pending_invites:
        await callback.answer("Invite expired!")
        return
    
    invite_data = pending_invites[invite_id]
    user = callback.from_user
    
    # Check if responding user is the target
    if user.id != invite_data["target_id"]:
        await callback.answer("This invitation isn't for you!", show_alert=True)
        return
    
    if action == "accept":
        # Check if already in cult
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        result = c.fetchone()
        
        if result and result[0] != "none":
            await callback.answer("You're already in the anime!", show_alert=True)
            conn.close()
            return
        
        # Add to cult
        c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Storm Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
                 (datetime.now().isoformat(), user.id))
        conn.commit()
        conn.close()
        
        await callback.answer("✅ Anime power accepted!", show_alert=True)
        
        # Update message
        await callback.message.edit_text(
            f"🎉 <b>ANIME POWER ACCEPTED!</b>\n\n"
            f"👤 <b>{user.first_name}</b> has accepted {invite_data['inviter_name']}'s invitation!\n"
            f"⚡ Storm power awakened!\n"
            f"🌀 Rank: Storm Initiate\n"
            f"✨ Starting Power: 3,000\n\n"
            f"<i>A new protagonist joins the anime...</i>",
            parse_mode=ParseMode.HTML
        )
        
    elif action == "decline":
        await callback.answer("❌ Invitation declined", show_alert=True)
        await callback.message.edit_text(
            f"🚫 <b>INVITATION REJECTED</b>\n\n"
            f"👤 <b>{user.first_name}</b> chose to remain a side character.\n"
            f"👑 Invited by: {invite_data['inviter_name']}\n\n"
            f"<i>Their anime potential remains untapped...</i>",
            parse_mode=ParseMode.HTML
        )
    
    # Remove invite
    if invite_id in pending_invites:
        del pending_invites[invite_id]
    
    # Auto-delete after 30 seconds
    await asyncio.sleep(30)
    try:
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
    except:
        pass

# ========== BROADCAST HANDLERS ==========
@dp.message()
async def handle_broadcast(message: Message):
    user = message.from_user
    chat = message.chat
    
    if user.id in broadcast_state and broadcast_state[user.id] is True:
        broadcast_state[user.id] = False
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned = 0")
        users = [row[0] for row in c.fetchall()]
        conn.close()
        
        total = len(users)
        status_msg = await message.answer(f"📤 Sending to {total} users...")
        
        success = 0
        for uid in users:
            try:
                if message.text:
                    await bot.send_message(uid, f"📢 {message.text}")
                elif message.photo:
                    await bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption or "📢 Broadcast")
                elif message.video:
                    await bot.send_video(uid, message.video.file_id, caption=message.caption or "📢 Broadcast")
                elif message.document:
                    await bot.send_document(uid, message.document.file_id, caption=message.caption or "📢 Broadcast")
                success += 1
                await asyncio.sleep(0.05)
            except:
                continue
        
        await status_msg.edit_text(f"✅ Sent to {success}/{total} users")
    
    elif user.id in broadcast_state and broadcast_state[user.id] == "group":
        broadcast_state[user.id] = False
        
        if not message.text:
            await message.answer("❌ Group broadcast supports text only")
            return
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT group_id FROM groups")
        groups = [row[0] for row in c.fetchall()]
        conn.close()
        
        total = len(groups)
        status_msg = await message.answer(f"📤 Sending to {total} groups...")
        
        success = 0
        for group_id in groups:
            try:
                await bot.send_message(group_id, f"📢 {message.text}")
                success += 1
                await asyncio.sleep(0.1)
            except:
                continue
        
        await status_msg.edit_text(f"✅ Sent to {success}/{total} groups")

# ========== FALLBACK HANDLER ==========
@dp.message()
async def fallback_handler(message: Message):
    """Handle other messages"""
    user = message.from_user
    chat = message.chat
    
    # Update user/group even if no command
    update_user(user)
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(chat)
    
    # If bot is mentioned
    if bot.username and f"@{bot.username}" in message.text:
        try:
            await message.reply("🤖 <b>Anime Bot is active!</b>\n\nUse /help to see commands", parse_mode=ParseMode.HTML)
        except:
            pass

# ========== MAIN ==========
async def main():
    print("🚀 ANIME BOT STARTING...")
    print("✅ Database initialized")
    print("🌀 Tempest Anime: ACTIVE WITH ASCII ART")
    print("🎬 Story Mode: ANIME EPISODES READY")
    print("⚡ Uptime Format: 1d 2h 3m 4s FIXED")
    print("📊 Log Channel: CONNECTED")
    print("=" * 50)
    
    # Send startup log
    try:
        await send_log(f"🤖 <b>Anime Bot Started</b>\n🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🌀 Version: Anime-Edition")
    except:
        print("⚠️ Could not send startup log")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped gracefully")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
