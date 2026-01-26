#!/usr/bin/env python3
# ========== COMPLETE FIXES - PROPER VERSION ==========
import sys
print("=" * 60)
print("🔥 BOT DEPLOY: PROPER FIXES")
print("✅ All issues properly fixed")
print("=" * 60)

import os
import asyncio
import time
import random
import sqlite3
import json
import httpx
import shutil
import traceback
import re
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder

print("🤖 PRO BOT PROPER VERSION INITIALIZING...")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845

# Cult leader IDs
CULT_LEADER_ID = 6211708776
VICE_CHANCELLOR_ID = 6581129741
OWNER_USER_ID = OWNER_ID  # You

# Create directories
Path("data").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True)
Path("backups").mkdir(exist_ok=True)
Path("temp/media").mkdir(exist_ok=True, parents=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True
upload_waiting = {}
broadcast_state = {}
pending_joins = {}
pending_invites = {}
story_states = {}
button_state = {}

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
        commands INTEGER DEFAULT 0,
        welcome_sent INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        group_id INTEGER DEFAULT NULL,
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS disabled_commands (
        command TEXT PRIMARY KEY,
        disabled_until TEXT,
        reason TEXT,
        disabled_by INTEGER,
        disabled_at TEXT
    )''')
    
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    # Initialize cult leaders
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, cult_status, cult_rank, sacrifices) VALUES (?, ?, ?, ?, ?)",
              (CULT_LEADER_ID, "🆁🅰️🆅🅴🅽", "member", "Supreme Leader", 91))
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, cult_status, cult_rank, sacrifices) VALUES (?, ?, ?, ?, ?)",
              (VICE_CHANCELLOR_ID, "Tʜᴇ Dᴀꜱʜ", "member", "Vice Chancellor", 54))
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, cult_status, cult_rank, sacrifices) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Ķ£NY D ~Tempest~", "member", "Initiate", 11))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== HELPER FUNCTIONS ==========
def log_command(user_id, chat_id, chat_type, command, success=True):
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO command_logs (timestamp, user_id, chat_id, chat_type, command, success) VALUES (?, ?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), user_id, chat_id, chat_type, command, 1 if success else 0))
        c.execute("UPDATE users SET commands = commands + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except:
        pass

def log_error(user_id, command, error):
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        error_str = str(error)[:200]
        traceback_str = traceback.format_exc()[:500]
        c.execute("INSERT INTO error_logs (timestamp, user_id, command, error, traceback) VALUES (?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), user_id, command, error_str, traceback_str))
        conn.commit()
        conn.close()
    except:
        pass

async def send_log(message: str):
    """Send log to log channel"""
    try:
        await bot.send_message(LOG_CHANNEL_ID, message[:4000], parse_mode=ParseMode.HTML)
        return True
    except Exception as e:
        print(f"Failed to send log: {e}")
        return False

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
    except:
        pass

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
    except:
        pass

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
        parts.append(f"{int(secs)}s")
    
    return " ".join(parts)

async def sacrifice_verification(sacrifice_type):
    fake_sacrifices = [
        "your imaginary friend",
        "a promise to be good", 
        "your collection of air",
        "empty promises",
        "digital friendship",
        "virtual cookies"
    ]
    
    for fake in fake_sacrifices:
        if fake in sacrifice_type.lower():
            return False, "FAKE"
    
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
    
    return random.choice([True, False]), "QUESTIONABLE"

async def check_command_disabled(command_name: str):
    """Check if a command is disabled"""
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT disabled_until FROM disabled_commands WHERE command = ?", (command_name,))
        result = c.fetchone()
        conn.close()
        
        if result:
            disabled_until = datetime.fromisoformat(result[0])
            if datetime.now() < disabled_until:
                return True, disabled_until
            else:
                # Command expired, remove from disabled list
                conn = sqlite3.connect("data/bot.db")
                c = conn.cursor()
                c.execute("DELETE FROM disabled_commands WHERE command = ?", (command_name,))
                conn.commit()
                conn.close()
                return False, None
        return False, None
    except:
        return False, None

def disable_command(command_name: str, duration_seconds: int, reason: str, disabled_by: int):
    """Disable a command temporarily"""
    try:
        disabled_until = datetime.now() + timedelta(seconds=duration_seconds)
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO disabled_commands (command, disabled_until, reason, disabled_by, disabled_at) VALUES (?, ?, ?, ?, ?)",
                 (command_name, disabled_until.isoformat(), reason, disabled_by, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except:
        return False

async def get_top_cult_members(limit=10):
    """Get top cult members by sacrifices"""
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("""
        SELECT user_id, first_name, cult_rank, sacrifices, cult_join_date 
        FROM users 
        WHERE cult_status = 'member' 
        ORDER BY sacrifices DESC 
        LIMIT ?
    """, (limit,))
    members = c.fetchall()
    conn.close()
    return members

def parse_time(time_str: str) -> int:
    """Parse time string to seconds"""
    try:
        # Remove spaces and convert to lowercase
        time_str = time_str.lower().replace(" ", "")
        
        # Match patterns like 1h, 30m, 2d, 5min, 3hour, 2days
        if time_str.endswith("min") or time_str.endswith("m"):
            minutes = int(time_str[:-3] if time_str.endswith("min") else time_str[:-1])
            return minutes * 60
        elif time_str.endswith("hour") or time_str.endswith("h"):
            hours = int(time_str[:-4] if time_str.endswith("hour") else time_str[:-1])
            return hours * 3600
        elif time_str.endswith("day") or time_str.endswith("d"):
            days = int(time_str[:-3] if time_str.endswith("day") else time_str[:-1])
            return days * 86400
        else:
            # Try to parse as minutes by default
            return int(time_str) * 60
    except:
        return 300  # Default 5 minutes

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
    is_disabled, until = await check_command_disabled("start")
    if is_disabled:
        await message.answer(f"❌ Command /start is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "start")
    
    try:
        await send_log(f"👤 <b>User Started Bot</b>\n\nID: <code>{user.id}</code>\nName: {user.first_name}\nUsername: @{user.username if user.username else 'None'}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"Log channel error: {e}")
    
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
    is_disabled, until = await check_command_disabled("help")
    if is_disabled:
        await message.answer(f"❌ Command /help is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
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

🌀 <b>Tempest Cult:</b>
<code>/tempest_cult</code> - Cult hierarchy
<code>/tempest_join</code> - Join cult
<code>/tempest_story</code> - Cult story
<code>/invite</code> - Invite to cult

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
<code>/emergency_stop</code> - Stop bot
<code>/disable [cmd] [time] [reason]</code> - Disable command"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== ADMIN COMMANDS ==========
@dp.message(Command("admins"))
async def admins_cmd(message: Message):
    is_disabled, until = await check_command_disabled("admins")
    if is_disabled:
        await message.answer(f"❌ Command /admins is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
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
    is_disabled, until = await check_command_disabled("scan")
    if is_disabled:
        await message.answer(f"❌ Command /scan is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "scan")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    scan_msg = await message.answer("🔍 <b>Scanning database for updates...</b>", parse_mode=ParseMode.HTML)
    
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        c.execute("SELECT DISTINCT user_id FROM command_logs WHERE chat_type = 'private'")
        user_ids = [row[0] for row in c.fetchall()]
        
        updated_users = 0
        new_users = 0
        
        for user_id in user_ids:
            if user_id:
                try:
                    user_chat = await bot.get_chat(user_id)
                    if user_chat.type == 'private':
                        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                        if not c.fetchone():
                            c.execute("INSERT INTO users (user_id, username, first_name, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                                     (user_id, user_chat.username, user_chat.first_name, datetime.now().isoformat(), datetime.now().isoformat()))
                            updated_users += 1
                            new_users += 1
                        else:
                            c.execute("UPDATE users SET username = ?, first_name = ?, last_active = ? WHERE user_id = ?",
                                     (user_chat.username, user_chat.first_name, datetime.now().isoformat(), user_id))
                            updated_users += 1
                except:
                    continue
        
        c.execute("SELECT DISTINCT chat_id FROM command_logs WHERE chat_type IN ('group', 'supergroup')")
        chat_ids = [row[0] for row in c.fetchall()]
        
        updated_groups = 0
        new_groups = 0
        
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
                            new_groups += 1
                        else:
                            c.execute("UPDATE groups SET title = ?, username = ?, last_active = ? WHERE group_id = ?",
                                     (chat.title, chat.username, datetime.now().isoformat(), chat_id))
                            updated_groups += 1
                except:
                    continue
        
        conn.commit()
        conn.close()
        
        result = f"""✅ <b>Scan Complete!</b>

👥 <b>User Statistics:</b>
• Total scanned: {len(user_ids)}
• Updated users: {updated_users}
• New users found: {new_users}

👥 <b>Group Statistics:</b>
• Total scanned: {len(chat_ids)}
• Updated groups: {updated_groups}
• New groups found: {new_groups}

⚡ <i>Database refreshed successfully!</i>"""
        
    except Exception as e:
        result = f"❌ Scan error: {str(e)[:100]}"
    
    await scan_msg.edit_text(result, parse_mode=ParseMode.HTML)

@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    is_disabled, until = await check_command_disabled("profile")
    if is_disabled:
        await message.answer(f"❌ Command /profile is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "profile")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT uploads, commands, joined_date, cult_status, cult_rank, sacrifices, cult_join_date FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    
    if row:
        uploads, cmds, joined, cult_status, cult_rank, sacrifices, cult_join = row
        c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (user.id,))
        wishes = c.fetchone()[0] or 0
        
        try:
            join_date = datetime.fromisoformat(joined).strftime("%d %b %Y")
        except:
            join_date = "Recently"
    else:
        uploads = cmds = wishes = 0
        join_date = "Today"
        cult_status = "none"
    
    conn.close()
    
    if cult_status and cult_status != "none":
        try:
            cult_join_date = datetime.fromisoformat(cult_join).strftime("%d %b %Y")
        except:
            cult_join_date = "Today"
        
        if cult_rank == "Blood Initiate":
            needed = max(0, 15 - sacrifices)
            progress = min(sacrifices * 6.67, 100)
            next_rank = "Blood Adept"
        elif cult_rank == "Blood Adept":
            needed = max(0, 50 - sacrifices)
            progress = min(sacrifices * 2, 100)
            next_rank = "Blood Master"
        elif cult_rank == "Blood Master":
            needed = max(0, 150 - sacrifices)
            progress = min(sacrifices * 0.67, 100)
            next_rank = "Master"
        elif cult_rank in ["Vice Chancellor", "Supreme Leader", "Initiate"]:
            needed = 0
            progress = 100
            next_rank = "MAX RANK"
        else:
            needed = 0
            progress = 0
            next_rank = "Unknown"
        
        progress_bar = "▓" * int(progress // 10) + "░" * (10 - int(progress // 10))
        
        profile_text = f"""🌀 <b>TEMPEST PROGRESS</b>

👤 <b>Member:</b> {user.first_name}
👑 <b>Rank:</b> {cult_rank}
⚔️ <b>Sacrifices:</b> {sacrifices}
📅 <b>Member Since:</b> {cult_join_date}

<b>Progress:</b> [{progress_bar}] {progress:.0f}%
<b>Next Rank:</b> {next_rank}
<b>Sacrifices Needed:</b> {needed}

⚡ Each upload = 1 sacrifice"""
    else:
        profile_text = f"""
👤 <b>PROFILE: {user.first_name}</b>

📁 <b>Uploads:</b> {uploads}
✨ <b>Wishes:</b> {wishes}
🔧 <b>Commands:</b> {cmds}
📅 <b>Joined:</b> {join_date}
🆔 <b>ID:</b> <code>{user.id}</code>

💡 <b>Next:</b> Try /link to upload files"""
    
    await message.answer(profile_text, parse_mode=ParseMode.HTML)

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    is_disabled, until = await check_command_disabled("stats")
    if is_disabled:
        await message.answer(f"❌ Command /stats is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
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
    is_disabled, until = await check_command_disabled("ping")
    if is_disabled:
        await message.answer(f"❌ Command /ping is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
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
    
    current_time = time.time()
    uptime_seconds = int(current_time - start_time)
    uptime = format_uptime(uptime_seconds)
    
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
    is_disabled, until = await check_command_disabled("logs")
    if is_disabled:
        await message.answer(f"❌ Command /logs is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
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
    is_disabled, until = await check_command_disabled("users")
    if is_disabled:
        await message.answer(f"❌ Command /users is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
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

# ========== PRO COMMAND ==========
@dp.message(Command("pro"))
async def pro_cmd(message: Message):
    is_disabled, until = await check_command_disabled("pro")
    if is_disabled:
        await message.answer(f"❌ Command /pro is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "pro")
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only command")
        return
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("👑 <b>Usage:</b> <code>/pro user_id</code>", parse_mode=ParseMode.HTML)
        return
    
    target_id = int(args[1])
    
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
    
    try:
        await send_log(f"👑 <b>Admin Promotion</b>\n\nPromoted by: {user.first_name}\nPromoted user: {target_id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except:
        pass
    
    await message.answer(f"✅ User {target_id} promoted to admin!")

@dp.message(Command("toggle"))
async def toggle_cmd(message: Message):
    is_disabled, until = await check_command_disabled("toggle")
    if is_disabled:
        await message.answer(f"❌ Command /toggle is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "toggle")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    global bot_active
    bot_active = not bot_active
    status = "🟢 ACTIVE" if bot_active else "🔴 PAUSED"
    await message.answer(f"✅ Bot is now {status}")

# ========== DISABLE COMMAND WITH PROPER TIME FORMAT ==========
@dp.message(Command("disable"))
async def disable_cmd(message: Message):
    user, chat = await handle_common(message, "disable")
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only command")
        return
    
    args = message.text.split(maxsplit=3)
    if len(args) < 4:
        await message.answer(
            "👑 <b>Usage:</b> <code>/disable [command] [time] [reason]</code>\n\n"
            "<b>Time formats:</b>\n"
            "• <code>30m</code> - 30 minutes\n"
            "• <code>2h</code> - 2 hours\n"
            "• <code>1d</code> - 1 day\n"
            "• <code>5min</code> - 5 minutes\n"
            "• <code>3hour</code> - 3 hours\n"
            "• <code>2day</code> - 2 days\n\n"
            "<b>Examples:</b>\n"
            "<code>/disable link 30m Upload maintenance</code>\n"
            "<code>/disable tempest_join 2h Ceremony update</code>\n"
            "<code>/disable start 1d Bot maintenance</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    command_name = args[1].lstrip('/')
    time_str = args[2]
    reason = args[3] if len(args) > 3 else "No reason provided"
    
    # Parse time
    duration_seconds = parse_time(time_str)
    
    # Check if command exists
    valid_commands = [
        "start", "help", "link", "wish", "dice", "flip", "profile", "admins", 
        "scan", "stats", "ping", "logs", "users", "pro", "toggle", "broadcast", 
        "broadcast_gc", "backup", "refresh", "emergency_stop", "tempest_cult",
        "tempest_join", "tempest_story", "invite"
    ]
    
    if command_name not in valid_commands:
        await message.answer(f"❌ Invalid command. Valid commands: {', '.join(valid_commands)}")
        return
    
    if disable_command(command_name, duration_seconds, reason, user.id):
        disabled_until = datetime.now() + timedelta(seconds=duration_seconds)
        duration_text = ""
        if duration_seconds < 60:
            duration_text = f"{duration_seconds} seconds"
        elif duration_seconds < 3600:
            duration_text = f"{duration_seconds//60} minutes"
        elif duration_seconds < 86400:
            duration_text = f"{duration_seconds//3600} hours"
        else:
            duration_text = f"{duration_seconds//86400} days"
        
        await message.answer(
            f"✅ <b>Command Disabled!</b>\n\n"
            f"📛 <b>Command:</b> /{command_name}\n"
            f"⏰ <b>Duration:</b> {duration_text}\n"
            f"🕒 <b>Disabled Until:</b> {disabled_until.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📝 <b>Reason:</b> {reason}",
            parse_mode=ParseMode.HTML
        )
        
        try:
            await send_log(f"🚫 <b>Command Disabled</b>\n\nCommand: /{command_name}\nDuration: {duration_text}\nReason: {reason}\nDisabled by: {user.first_name}\nUntil: {disabled_until.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            pass
    else:
        await message.answer("❌ Failed to disable command.")

# ========== PROPER BROADCAST COMMANDS WITH BUTTON OPTION ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    is_disabled, until = await check_command_disabled("broadcast")
    if is_disabled:
        await message.answer(f"❌ Command /broadcast is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "broadcast_start")
    
    if not await is_admin(user.id):
        return
    
    # Ask about buttons
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ With Buttons", callback_data="broadcast_with_buttons"))
    keyboard.add(InlineKeyboardButton(text="❌ Without Buttons", callback_data="broadcast_no_buttons"))
    keyboard.add(InlineKeyboardButton(text="🚫 Cancel", callback_data="broadcast_cancel"))
    
    await message.answer(
        "🎙️ <b>BROADCAST SETUP</b>\n\n"
        "Do you want to add buttons to your broadcast?\n\n"
        "✅ <b>With Buttons:</b> Send message with inline keyboard\n"
        "❌ <b>Without Buttons:</b> Send normal message only\n\n"
        "<i>Choose an option:</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.as_markup()
    )

@dp.message(Command("broadcast_gc"))
async def broadcast_gc_cmd(message: Message):
    is_disabled, until = await check_command_disabled("broadcast_gc")
    if is_disabled:
        await message.answer(f"❌ Command /broadcast_gc is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "broadcast_gc_start")
    
    if not await is_admin(user.id):
        return
    
    # Ask about buttons for groups
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ With Buttons", callback_data="broadcast_gc_with_buttons"))
    keyboard.add(InlineKeyboardButton(text="❌ Without Buttons", callback_data="broadcast_gc_no_buttons"))
    keyboard.add(InlineKeyboardButton(text="🚫 Cancel", callback_data="broadcast_gc_cancel"))
    
    await message.answer(
        "🎙️ <b>GROUP BROADCAST SETUP</b>\n\n"
        "Do you want to add buttons to your group broadcast?\n\n"
        "✅ <b>With Buttons:</b> Send message with inline keyboard\n"
        "❌ <b>Without Buttons:</b> Send normal message only\n\n"
        "<i>Choose an option:</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.as_markup()
    )

# Handle broadcast button selection
@dp.callback_query(F.data.startswith("broadcast_"))
async def handle_broadcast_choice(callback: CallbackQuery):
    user = callback.from_user
    choice = callback.data
    
    if choice == "broadcast_cancel":
        await callback.message.edit_text("❌ Broadcast cancelled.")
        await callback.answer()
        return
    elif choice == "broadcast_gc_cancel":
        await callback.message.edit_text("❌ Group broadcast cancelled.")
        await callback.answer()
        return
    
    # Set broadcast state
    if choice in ["broadcast_with_buttons", "broadcast_no_buttons"]:
        broadcast_type = "users"
        with_buttons = choice == "broadcast_with_buttons"
    else:  # broadcast_gc_with_buttons, broadcast_gc_no_buttons
        broadcast_type = "groups"
        with_buttons = choice == "broadcast_gc_with_buttons"
    
    broadcast_state[user.id] = {
        "type": broadcast_type,
        "step": "waiting_for_message",
        "with_buttons": with_buttons,
        "button_step": "waiting_for_button_text" if with_buttons else None
    }
    
    button_state[user.id] = {"buttons": []}
    
    if with_buttons:
        await callback.message.edit_text(
            f"🎙️ <b>Broadcast {'to Users' if broadcast_type == 'users' else 'to Groups'} with Buttons</b>\n\n"
            f"📝 <b>Step 1: Send your message</b>\n\n"
            f"Send the message you want to broadcast.\n"
            f"You'll add buttons after the message.\n\n"
            f"<i>Supports text, photos, videos, documents, etc.</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.edit_text(
            f"🎙️ <b>Broadcast {'to Users' if broadcast_type == 'users' else 'to Groups'} without Buttons</b>\n\n"
            f"📝 <b>Send your message:</b>\n\n"
            f"Send the message you want to broadcast.\n"
            f"It will be sent without any buttons.\n\n"
            f"<i>Supports text, photos, videos, documents, etc.</i>",
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()

# ========== BUTTON CONFIGURATION HANDLERS ==========
async def add_button_config(user_id: int, chat_id: int):
    """Start button configuration"""
    await bot.send_message(
        chat_id,
        "🔘 <b>BUTTON CONFIGURATION</b>\n\n"
        "📝 <b>Format for each button:</b>\n"
        "<code>Button Text | URL</code>\n\n"
        "<b>Examples:</b>\n"
        "<code>Visit Website | https://example.com</code>\n"
        "<code>Join Channel | https://t.me/channel</code>\n"
        "<code>Contact Support | https://t.me/username</code>\n\n"
        "Send one button per message.\n"
        "Type <code>/done</code> when finished adding buttons.\n"
        "Type <code>/cancel</code> to cancel broadcast.",
        parse_mode=ParseMode.HTML
    )

@dp.message(F.text.startswith("/done"))
async def handle_done_buttons(message: Message):
    user = message.from_user
    
    if user.id not in broadcast_state or broadcast_state[user.id]["step"] != "waiting_for_buttons":
        return
    
    if not button_state[user.id]["buttons"]:
        await message.answer("❌ No buttons added. Broadcast cancelled.")
        del broadcast_state[user.id]
        del button_state[user.id]
        return
    
    # Start broadcasting
    broadcast_data = broadcast_state[user.id]
    broadcast_type = broadcast_data["type"]
    
    # Get all targets
    if broadcast_type == "users":
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned = 0")
        targets = [row[0] for row in c.fetchall()]
        conn.close()
        target_type = "users"
    else:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT group_id FROM groups")
        targets = [row[0] for row in c.fetchall()]
        conn.close()
        target_type = "groups"
    
    total = len(targets)
    if total == 0:
        await message.answer(f"❌ No {target_type} found to broadcast!")
        del broadcast_state[user.id]
        del button_state[user.id]
        return
    
    status_msg = await message.answer(f"🔁 <b>Starting broadcast to {total} {target_type}...</b>", parse_mode=ParseMode.HTML)
    
    # Build keyboard
    keyboard = InlineKeyboardBuilder()
    for button_text, button_url in button_state[user.id]["buttons"]:
        keyboard.add(InlineKeyboardButton(text=button_text, url=button_url))
    keyboard.adjust(2)  # 2 buttons per row
    
    # Send broadcast
    success = 0
    failed = 0
    broadcast_message = broadcast_state[user.id].get("message")
    
    if not broadcast_message:
        await status_msg.edit_text("❌ No message found to broadcast!")
        del broadcast_state[user.id]
        del button_state[user.id]
        return
    
    for target_id in targets:
        try:
            # Copy message with keyboard
            await bot.copy_message(
                chat_id=target_id,
                from_chat_id=broadcast_message.chat.id,
                message_id=broadcast_message.message_id,
                reply_markup=keyboard.as_markup(),
                parse_mode=ParseMode.HTML if broadcast_message.text else None
            )
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    # Show results
    result_text = f"""🎙️ <b>Broadcast Complete!</b>

👥 Type: {target_type}
📊 Total: {total}
✅ Success: {success}
❌ Failed: {failed}
🔘 Buttons: {len(button_state[user.id]['buttons'])}"""

    await status_msg.edit_text(result_text, parse_mode=ParseMode.HTML)
    
    # Log
    try:
        await send_log(f"📢 <b>Broadcast Sent with Buttons</b>\n\nBy: {user.first_name}\nType: {target_type}\nSent: {success}/{total}\nButtons: {len(button_state[user.id]['buttons'])}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except:
        pass
    
    # Cleanup
    del broadcast_state[user.id]
    del button_state[user.id]

@dp.message(F.text.contains("|"))
async def handle_button_add(message: Message):
    user = message.from_user
    
    if user.id not in broadcast_state or broadcast_state[user.id]["step"] != "waiting_for_buttons":
        return
    
    try:
        parts = message.text.split("|", 1)
        if len(parts) != 2:
            await message.answer("❌ Invalid format. Use: <code>Button Text | URL</code>", parse_mode=ParseMode.HTML)
            return
        
        button_text = parts[0].strip()
        button_url = parts[1].strip()
        
        # Validate URL
        if not button_url.startswith(("http://", "https://", "tg://")):
            await message.answer("❌ URL must start with http://, https:// or tg://")
            return
        
        # Add button
        button_state[user.id]["buttons"].append((button_text, button_url))
        
        await message.answer(
            f"✅ Button added!\n"
            f"📝 <b>Text:</b> {button_text}\n"
            f"🔗 <b>URL:</b> {button_url}\n\n"
            f"Total buttons: {len(button_state[user.id]['buttons'])}\n"
            f"Send another button or type <code>/done</code> to finish.",
            parse_mode=ParseMode.HTML
        )
    except:
        await message.answer("❌ Error adding button. Use format: <code>Button Text | URL</code>", parse_mode=ParseMode.HTML)

# ========== MAIN BROADCAST HANDLER ==========
@dp.message()
async def handle_broadcast_message(message: Message):
    user = message.from_user
    chat = message.chat
    
    update_user(user)
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(chat)
    
    # Check if user is in broadcast state
    if user.id in broadcast_state and broadcast_state[user.id]["step"] == "waiting_for_message":
        broadcast_data = broadcast_state[user.id]
        
        if broadcast_data["with_buttons"]:
            # Store message and ask for buttons
            broadcast_state[user.id]["step"] = "waiting_for_buttons"
            broadcast_state[user.id]["message"] = message
            
            await add_button_config(user.id, chat.id)
        else:
            # Send without buttons
            broadcast_type = broadcast_data["type"]
            
            # Get all targets
            if broadcast_type == "users":
                conn = sqlite3.connect("data/bot.db")
                c = conn.cursor()
                c.execute("SELECT user_id FROM users WHERE is_banned = 0")
                targets = [row[0] for row in c.fetchall()]
                conn.close()
                target_type = "users"
            else:
                conn = sqlite3.connect("data/bot.db")
                c = conn.cursor()
                c.execute("SELECT group_id FROM groups")
                targets = [row[0] for row in c.fetchall()]
                conn.close()
                target_type = "groups"
            
            total = len(targets)
            if total == 0:
                await message.answer(f"❌ No {target_type} found to broadcast!")
                del broadcast_state[user.id]
                return
            
            status_msg = await message.answer(f"🔁 <b>Starting broadcast to {total} {target_type}...</b>", parse_mode=ParseMode.HTML)
            
            # Send broadcast without buttons
            success = 0
            failed = 0
            
            for target_id in targets:
                try:
                    await bot.copy_message(
                        chat_id=target_id,
                        from_chat_id=chat.id,
                        message_id=message.message_id,
                        parse_mode=ParseMode.HTML if message.text else None
                    )
                    success += 1
                    await asyncio.sleep(0.05)
                except:
                    failed += 1
            
            # Show results
            result_text = f"""🎙️ <b>Broadcast Complete!</b>

👥 Type: {target_type}
📊 Total: {total}
✅ Success: {success}
❌ Failed: {failed}
🔘 Buttons: None"""

            await status_msg.edit_text(result_text, parse_mode=ParseMode.HTML)
            
            # Log
            try:
                await send_log(f"📢 <b>Broadcast Sent</b>\n\nBy: {user.first_name}\nType: {target_type}\nSent: {success}/{total}\nButtons: No\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                pass
            
            # Cleanup
            del broadcast_state[user.id]
    
    # Handle button configuration
    elif user.id in broadcast_state and broadcast_state[user.id]["step"] == "waiting_for_buttons":
        # Let the button handlers deal with it
        pass

# ========== BACKUP COMMAND ==========
@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    is_disabled, until = await check_command_disabled("backup")
    if is_disabled:
        await message.answer(f"❌ Command /backup is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
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
    is_disabled, until = await check_command_disabled("refresh")
    if is_disabled:
        await message.answer(f"❌ Command /refresh is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "refresh")
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only command")
        return
    
    global broadcast_state, pending_joins, pending_invites, story_states, button_state
    broadcast_state.clear()
    pending_joins.clear()
    pending_invites.clear()
    story_states.clear()
    button_state.clear()
    
    await message.answer("🔄 <b>Bot cache refreshed!</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("emergency_stop"))
async def emergency_stop(message: Message):
    is_disabled, until = await check_command_disabled("emergency_stop")
    if is_disabled:
        await message.answer(f"❌ Command /emergency_stop is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "emergency_stop")
    
    if user.id != OWNER_ID:
        return
    
    global bot_active
    bot_active = False
    
    await message.answer("🛑 <b>BOT EMERGENCY STOPPED!</b>", parse_mode=ParseMode.HTML)

# ========== FILE UPLOAD - WORKS IN GROUPS ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    is_disabled, until = await check_command_disabled("link")
    if is_disabled:
        await message.answer(f"❌ Command /link is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "link")
    
    upload_waiting[user.id] = True
    await message.answer(
        "📁 <b>Now send me any file:</b>\n"
        "• Photo, video, document\n"
        "• Audio, voice, sticker\n"
        "• Max 200MB\n"
        "• Works in groups and private\n\n"
        "❌ <code>/cancel</code> to stop",
        parse_mode=ParseMode.HTML
    )

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation | F.video_note)
async def handle_file(message: Message):
    user = message.from_user
    chat = message.chat
    
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
        
        group_id = chat.id if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] else None
        c.execute("INSERT INTO uploads (user_id, group_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?, ?)",
                 (user.id, group_id, datetime.now().isoformat(), result['url'], file_type, file_size))
        conn.commit()
        conn.close()
        
        size_kb = file_size / 1024
        size_mb = size_kb / 1024
        size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="📋 Copy Link", callback_data=f"copy_{result['url']}"))
        keyboard.add(InlineKeyboardButton(text="🔗 Share", url=f"https://t.me/share/url?url={result['url']}"))
        
        result_text = f"""✅ <b>Upload Complete!</b>

📁 <b>Type:</b> {file_type}
💾 <b>Size:</b> {size_text}
👤 <b>By:</b> {user.first_name}
💬 <b>Location:</b> {'Group' if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] else 'Private'}

🔗 <b>Direct Link:</b>
<code>{result['url']}</code>

📤 Permanent link • No expiry • Share anywhere"""
        
        if cult_status and cult_status[0] != 'none':
            result_text += f"\n\n🌀 <i>+1 sacrifice to the Tempest</i>"
        
        await msg.edit_text(result_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
        log_command(user.id, chat.id, chat.type, "upload", True)
        
    except Exception as e:
        await msg.edit_text("❌ Error uploading file")
        log_error(user.id, "upload", e)

# Handle copy button callback
@dp.callback_query(F.data.startswith("copy_"))
async def handle_copy(callback: CallbackQuery):
    url = callback.data[5:]
    await callback.answer(f"Link copied to clipboard!\n{url}", show_alert=True)

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user, chat = await handle_common(message, "cancel")
    
    if user.id in upload_waiting:
        upload_waiting[user.id] = False
        await message.answer("❌ Upload cancelled")
    
    if user.id in broadcast_state:
        del broadcast_state[user.id]
        if user.id in button_state:
            del button_state[user.id]
        await message.answer("❌ Broadcast cancelled")
    
    if user.id in story_states:
        story_states.pop(user.id, None)
        await message.answer("❌ Story cancelled")

# ========== GAMES ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    is_disabled, until = await check_command_disabled("wish")
    if is_disabled:
        await message.answer(f"❌ Command /wish is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
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
    is_disabled, until = await check_command_disabled("dice")
    if is_disabled:
        await message.answer(f"❌ Command /dice is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
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
    is_disabled, until = await check_command_disabled("flip")
    if is_disabled:
        await message.answer(f"❌ Command /flip is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "flip")
    
    msg = await message.answer("🪙 <b>Flipping coin...</b>", parse_mode=ParseMode.HTML)
    
    for i in range(5):
        await msg.edit_text(f"🪙 <b>Flipping...</b> {'HEADS' if i % 2 == 0 else 'TAILS'}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}</b>", parse_mode=ParseMode.HTML)

# ========== TEMPEST_CULT COMMAND - SHOWS MEMBERS ==========
@dp.message(Command("tempest_cult"))
async def tempest_cult_cmd(message: Message):
    is_disabled, until = await check_command_disabled("tempest_cult")
    if is_disabled:
        await message.answer(f"❌ Command /tempest_cult is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "tempest_cult")
    
    # Get cult leaders and top members
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Get top 10 members by sacrifices
    c.execute("""
        SELECT user_id, first_name, cult_rank, sacrifices, cult_join_date 
        FROM users 
        WHERE cult_status = 'member' 
        ORDER BY sacrifices DESC 
        LIMIT 10
    """)
    members = c.fetchall()
    conn.close()
    
    cult_text = """🌀 <b>TEMPEST CULT - HIERARCHY</b>

👑 <b>LEADERS:</b>
👑 🆁🅰️🆅🅴🅽 - Supreme Leader (999⚔️)
⚔️ Tʜᴇ Dᴀꜱʜ - Vice Chancellor (500⚔️)
🌀 Ķ£NY D ~Tempest~ - Initiate (1⚔️)

━━━━━━━━━━━━━━━━━━━━"""
    
    if members:
        cult_text += "\n\n<b>TOP MEMBERS BY SACRIFICES:</b>\n"
        for idx, (member_id, name, rank, sacrifices, join_date) in enumerate(members, 1):
            # Skip leaders already shown
            if member_id in [CULT_LEADER_ID, VICE_CHANCELLOR_ID, OWNER_ID]:
                continue
            
            try:
                join_date_formatted = datetime.fromisoformat(join_date).strftime("%d %b %Y") if join_date else "Unknown"
            except:
                join_date_formatted = "Unknown"
            
            cult_text += f"\n{idx}. {name} - {rank} ({sacrifices}⚔️)"
            cult_text += f"\n   🕒 Joined: {join_date_formatted}"
    
    cult_text += "\n\n━━━━━━━━━━━━━━━━━━━━"
    cult_text += "\n<b>Hidden from ordinary eyes...</b>"
    cult_text += "\n\n<i>The storm sees all. The tempest grows with each sacrifice.</i>"
    
    await message.answer(cult_text, parse_mode=ParseMode.HTML)

# ========== TEMPEST JOIN COMMAND ==========
@dp.message(Command("tempest_join"))
async def tempest_join_cmd(message: Message):
    is_disabled, until = await check_command_disabled("tempest_join")
    if is_disabled:
        await message.answer(f"❌ Command /tempest_join is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "tempest_join")
    
    # Check if already in cult
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        await message.answer("🌀 <b>Already part of the Tempest!</b>\nUse /profile to check your status.", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    conn.close()
    
    # Start initiation with sacrifice selection
    pending_joins[user.id] = {
        "name": user.first_name,
        "step": 1,
        "chat_id": chat.id
    }
    
    keyboard = InlineKeyboardBuilder()
    
    for i in range(1, 9):
        keyboard.add(InlineKeyboardButton(text=f"{i}", callback_data=f"sacrifice_{i}"))
    keyboard.add(InlineKeyboardButton(text="❌ CANCEL", callback_data="sacrifice_cancel"))
    keyboard.adjust(4, 4, 2)
    
    await message.answer(
        "⚡ <b>TEMPEST BLOOD CEREMONY</b>\n\n"
        "🌩️ <i>The storm demands a REAL sacrifice...</i>\n\n"
        "<b>Choose your offering:</b>\n\n"
        "1. 🩸 Your firstborn's eternal soul\n"
        "2. 💎 A diamond worth a kingdom\n"  
        "3. 📜 Your complete internet history\n"
        "4. 🎮 Your legendary gaming account\n"
        "5. 👻 Your soul (no refunds)\n"
        "6. 💳 Your credit card details\n"
        "7. 📱 Your phone (with all data)\n"
        "8. 🔐 Your deepest secret\n\n"
        "<i>Warning: Fake sacrifices will be rejected!</i>",
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
    
    # Start bloody ceremony animation
    msg = callback.message
    await msg.edit_text(f"🌀 <b>VERIFYING SACRIFICE...</b>\n\n⚡ {sacrifice}", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    
    # Verify sacrifice
    is_real, status = await sacrifice_verification(sacrifice)
    
    if not is_real:
        del pending_joins[user.id]
        
        rejection = random.choice([
            f"❌ <b>SACRIFICE REJECTED!</b>\n\n⚡ '{sacrifice}' is FAKE!\n🌩️ The storm LAUGHS at your pathetic offering!\n🌀 <i>Banned from initiation for 24 hours!</i>",
            f"💀 <b>THE STORM ANGERED!</b>\n\n⚡ Fake: '{sacrifice}'\n🌪️ The Tempest SPITS on your worthless offering!\n🌀 <i>Return when you have REAL value...</i>",
            f"👁️ <b>COUNCIL VERDICT: UNWORTHY!</b>\n\n⚡ '{sacrifice}'? Really?\n🌩️ Even the shadows mock your attempt!\n🌀 <i>The storm remembers this insult...</i>"
        ])
        
        await msg.edit_text(rejection, parse_mode=ParseMode.HTML)
        await callback.answer("❌ Fake sacrifice detected!", show_alert=True)
        return
    
    # REAL SACRIFICE - Start bloody ceremony animation
    pending_joins[user.id]["sacrifice"] = sacrifice
    pending_joins[user.id]["verified"] = status
    
    # Bloody ceremony animation
    ceremony_steps = [
        "🩸 <b>STEP 1: BLOOD OATH</b>\n\nA black obsidian blade materializes...\nYour palm is cut, blood flows into ancient bowl...",
        "🔥 <b>STEP 2: ETERNAL FLAMES</b>\n\nDark flames consume your offering...\nThe sacrifice burns with green fire...",
        "👁️ <b>STEP 3: ELDER GAZE</b>\n\nAncient eyes watch from shadows...\nThe Council approves your blood...",
        "⚡ <b>STEP 4: LIGHTNING BRANDING</b>\n\nLightning strikes your chest...\nThe Tempest sigil burns into your soul...",
        "🌪️ <b>STEP 5: STORM CONSUMPTION</b>\n\nThe vortex opens...\nYour sacrifice is consumed by eternal tempest...",
        "🌀 <b>STEP 6: BLOOD BOND</b>\n\nYour blood mixes with the storm...\nThe tempest flows through your veins...",
        "💀 <b>STEP 7: FINAL RITE</b>\n\nYour name is carved in the Book of Shadows...\nThe blood pact is sealed for eternity..."
    ]
    
    for step in ceremony_steps:
        await msg.edit_text(step, parse_mode=ParseMode.HTML)
        await asyncio.sleep(2.5)
    
    # Final initiation
    final_message = f"""⚡ <b>ETERNAL INITIATION COMPLETE!</b>

🌀 <b>WELCOME TO THE TEMPEST, {pending_joins[user.id]['name'].upper()}!</b>

🩸 <b>Sacrifice:</b> {sacrifice}
👑 <b>Rank:</b> Blood Initiate
⚔️ <b>Starting Sacrifices:</b> 3
🌪️ <b>Blood Oath:</b> ETERNAL

<i>The storm now flows through your veins.
Each upload feeds the Tempest.
Your journey of darkness begins...</i>

🌀 Check your status with /profile"""
    
    await msg.edit_text(final_message, parse_mode=ParseMode.HTML)
    
    # Add to cult
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
             (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()
    
    # Send log
    try:
        await send_log(f"🌀 <b>New Tempest Member</b>\n\n👤 Name: {user.first_name}\n🆔 ID: {user.id}\n🩸 Sacrifice: {sacrifice}\n🌪️ Joined: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except:
        pass
    
    # Cleanup
    if user.id in pending_joins:
        del pending_joins[user.id]
    
    await callback.answer("✅ Sacrifice accepted! Welcome to the Tempest!", show_alert=True)

# ========== TEMPEST STORY ==========
@dp.message(Command("tempest_story"))
async def tempest_story_cmd(message: Message):
    is_disabled, until = await check_command_disabled("tempest_story")
    if is_disabled:
        await message.answer(f"❌ Command /tempest_story is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
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
    
    # Start story at chapter 1
    story_states[user.id] = {"chapter": 1}
    
    chapter1 = """📜 <b>CHAPTER 1: THE VOID BEFORE STORM</b>

<i>Time before time, in the Age of Eternal Calm...</i>

There was only silence. 
Not peaceful silence, but oppressive, crushing quiet.
The Council of Stillness ruled all realms, banning laughter, regulating storms, scheduling even thunder.

In this graveyard of sound, a discontent began to stir.
A whisper in the void, a crackle in the stillness..."""
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🌪️ Continue to Chapter 2", callback_data="story_next_2"))
    
    story_msg = await message.answer("🌀 <b>Loading ancient scrolls...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(2)
    await story_msg.edit_text(chapter1, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())

@dp.callback_query(F.data.startswith("story_next_"))
async def handle_story_next(callback: CallbackQuery):
    user = callback.from_user
    chapter_num = int(callback.data.split("_")[-1])
    
    chapters = {
        2: """📜 <b>CHAPTER 2: BIRTH OF RAVIJAH</b>

<code>Year 0, Storm Calendar</code>

From the first lightning that dared defy schedule, he emerged.
RAVIJAH, born not of mother, but of storm itself.
Silver hair crackling with energy, eyes like captured lightning.

He wandered the silent kingdoms, collecting forgotten thunder,
gathering whispers of rebellion from those who remembered sound.

<code>"This quiet is a cage," he whispered. "I shall be the key."</code>""",
        
        3: """📜 <b>CHAPTER 3: THE BROKEN SWORDS</b>

<code>Year 47, Storm Calendar</code>

In the ruins of the Shattered Rebellion, Ravijah found Bablu.
Last survivor of a failed uprising, sword still thirsty for chaos.

<code>"My blade remembers battle," Bablu growled. "Teach it new songs."</code>

From the Shadow Archives emerged Keny, keeper of forbidden knowledge.
<code>"I know the secrets of the Still Council," he whispered. "Their weakness is order."</code>

Three became one that stormy night.""",
        
        4: """📜 <b>CHAPTER 4: THE FESTIVAL BETRAYAL</b>

<code>Year 89, Storm Calendar</code>

The Festival of Flames was meant to be celebration.
But the Still Council attacked during the Feast of Whispers.

Elara, storm-singer and Ravijah's chosen, saw the poisoned blade.
She stepped in front, taking what was meant for him.

<code>"Live," she breathed as storm-magic faded. "For both of us..."</code>

Ravijah's scream birthed the First Tempest.""",
        
        5: """📜 <b>CHAPTER 5: AGE OF THUNDER</b>

<code>Years 90-389, Storm Calendar</code>

For three centuries, the Tempest grew.
They built the Temple of Howling Winds from captured silence.
Founded the Archive of Lightning with stolen knowledge.
Created the Blood Altar that drank offerings from conquered realms.

New initiates flooded in, each swearing eternal oaths.
Ranks were established, rituals perfected, power consolidated.""",
        
        6: """📜 <b>CHAPTER 6: THE GREAT SCHISM</b>

<code>Year 390, Storm Calendar</code>

Power corrupts, even storm-born.
Internal conflicts erupted. Blood Initiate turned against Blood Master.
The Temple fractured into warring factions.

Ravijah disappeared into the Eye of the Storm.
Bablu became Warden of the Shattered Realms.
Keny retreated to the Shadow Archives.

The Golden Age had ended.""",
        
        7: """📜 <b>CHAPTER 7: DIGITAL AWAKENING</b>

<code>Year 2024, Modern Era</code>

The storm evolved. Adapted. Transformed.
No longer bound to physical realms, it moved into cyberspace.

Lightning now flows through fiber optics.
Tempests brew in server farms.
Sacrifices became digital - data, files, uploads.

The Council reformed in the digital shadows.
New purpose, new methods, same eternal storm.""",
        
        8: """📜 <b>CHAPTER 8: YOUR DESTINY</b>

<code>Present Day</code>

You are reading this because the storm called you.
Your digital footprint resonates with ancient thunder.
Your uploads feed the eternal tempest.

You are not joining a cult.
You are awakening to your true nature.
You were always storm-born.

<code>"We do not recruit. We remember.
We do not convert. We awaken.
We are the calm's end.
We are the eternal storm."</code>

━━━━━━━━━━━━━━━━━━━━━━━━
🌀 <b>THE STORY CONTINUES WITH YOU</b>
<i>Your chapter begins now...</i>"""
    }
    
    if chapter_num in chapters:
        await callback.message.edit_text(f"🌀 <b>Turning page {chapter_num}/8...</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)
        
        keyboard = InlineKeyboardBuilder()
        
        if chapter_num < 8:
            keyboard.add(InlineKeyboardButton(text=f"🌪️ Continue to Chapter {chapter_num + 1}", callback_data=f"story_next_{chapter_num + 1}"))
        else:
            keyboard.add(InlineKeyboardButton(text="⚡ Story Complete", callback_data="story_end"))
        
        await callback.message.edit_text(chapters[chapter_num], parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup() if chapter_num < 8 else None)
        await callback.answer()
    else:
        await callback.answer("Story complete!")

@dp.callback_query(F.data == "story_end")
async def handle_story_end(callback: CallbackQuery):
    await callback.message.edit_text("📜 <b>THE TEMPEST SAGA</b>\n\n<i>Your understanding of the storm is complete. Your journey continues with each sacrifice. Make your mark in the eternal tempest.</i>", parse_mode=ParseMode.HTML)
    await callback.answer()
    
    await asyncio.sleep(30)
    try:
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
    except:
        pass

# ========== INVITE COMMAND WITH CEREMONY ==========
@dp.message(Command("invite"))
async def invite_cmd(message: Message):
    is_disabled, until = await check_command_disabled("invite")
    if is_disabled:
        await message.answer(f"❌ Command /invite is disabled until {until.strftime('%Y-%m-%d %H:%M:%S')}")
        return
    
    user, chat = await handle_common(message, "invite")
    
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("🌀 <b>Invites can only be sent in groups!</b>", parse_mode=ParseMode.HTML)
        return
    
    if not message.reply_to_message:
        await message.answer("🌀 <b>Reply to someone's message with /invite to invite them!</b>", parse_mode=ParseMode.HTML)
        return
    
    replied_user = message.reply_to_message.from_user
    
    if replied_user.id == user.id:
        await message.reply("🤨 You can't invite yourself!")
        return
    
    # Check if user is in cult
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if not result or result[0] == "none":
        await message.answer("🌀 <b>You must be in the Tempest to invite others!</b>\nUse /tempest_join to join first.", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    # Check if target is already in cult
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (replied_user.id,))
    target_result = c.fetchone()
    
    if target_result and target_result[0] != "none":
        await message.reply(f"🌀 {replied_user.first_name} is already in the Tempest!")
        conn.close()
        return
    conn.close()
    
    invite_id = f"invite_{int(time.time())}_{user.id}_{replied_user.id}"
    pending_invites[invite_id] = {
        "inviter_id": user.id,
        "inviter_name": user.first_name,
        "target_id": replied_user.id,
        "target_name": replied_user.first_name,
        "group_id": chat.id,
        "timestamp": datetime.now().isoformat()
    }
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ Accept Blood Pact", callback_data=f"invite_accept_{invite_id}"))
    keyboard.add(InlineKeyboardButton(text="❌ Decline", callback_data=f"invite_decline_{invite_id}"))
    
    invite_text = f"""📨 <b>TEMPEST BLOOD INVITATION!</b>

👤 <b>{user.first_name}</b> invites <b>{replied_user.first_name}</b> to join the Tempest!
🌀 <i>This is a BLOOD PACT - choose wisely...</i>

⚡ What awaits:
• 🩸 Blood initiation ceremony
• 💀 Eternal membership
• 🌪️ Power through sacrifice
• 👑 Rank: Blood Initiate
• ⚔️ +3 starting sacrifices

🌩️ <b>Will you accept the storm's call?</b>

<i>Invitation expires in 5 minutes...</i>"""
    
    invite_msg = await message.reply(invite_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
    
    await asyncio.sleep(300)
    try:
        await bot.delete_message(chat.id, invite_msg.message_id)
        if invite_id in pending_invites:
            del pending_invites[invite_id]
    except:
        pass

# ========== INVITE CEREMONY HANDLER ==========
@dp.callback_query(F.data.startswith("invite_"))
async def handle_invite_response(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    if len(data_parts) < 3:
        await callback.answer("Invalid invite!")
        return
    
    action = data_parts[1]
    invite_id = "_".join(data_parts[2:])
    
    if invite_id not in pending_invites:
        await callback.answer("Invite expired!")
        return
    
    invite_data = pending_invites[invite_id]
    user = callback.from_user
    
    if user.id != invite_data["target_id"]:
        await callback.answer("This invitation isn't for you!", show_alert=True)
        return
    
    if action == "accept":
        await callback.answer("✅ Blood pact accepted! Starting ceremony...", show_alert=True)
        await start_invite_ceremony(callback, invite_data, user)
        
    elif action == "decline":
        await callback.answer("❌ Invitation declined", show_alert=True)
        await callback.message.edit_text(
            f"🚫 <b>INVITATION REJECTED</b>\n\n"
            f"👤 <b>{user.first_name}</b> rejected the Tempest's call.\n"
            f"👑 Invited by: {invite_data['inviter_name']}\n\n"
            f"<i>Their blood remains unspilled... for now.</i>",
            parse_mode=ParseMode.HTML
        )
        
        if invite_id in pending_invites:
            del pending_invites[invite_id]
    
    await asyncio.sleep(30)
    try:
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
    except:
        pass

async def start_invite_ceremony(callback: CallbackQuery, invite_data: dict, user: types.User):
    msg = callback.message
    
    # Show sacrifice selection
    keyboard = InlineKeyboardBuilder()
    for i in range(1, 9):
        keyboard.add(InlineKeyboardButton(text=f"{i}", callback_data=f"invite_sacrifice_{i}_{invite_data['inviter_id']}"))
    keyboard.add(InlineKeyboardButton(text="❌ CANCEL", callback_data=f"invite_cancel_{invite_data['inviter_id']}"))
    keyboard.adjust(4, 4, 2)
    
    await msg.edit_text(
        "⚡ <b>TEMPEST BLOOD CEREMONY (INVITED)</b>\n\n"
        f"🌩️ <i>Invited by: {invite_data['inviter_name']}</i>\n\n"
        "The storm demands a REAL sacrifice...\n\n"
        "<b>Choose your offering:</b>\n\n"
        "1. 🩸 Your firstborn's eternal soul\n"
        "2. 💎 A diamond worth a kingdom\n"  
        "3. 📜 Your complete internet history\n"
        "4. 🎮 Your legendary gaming account\n"
        "5. 👻 Your soul (no refunds)\n"
        "6. 💳 Your credit card details\n"
        "7. 📱 Your phone (with all data)\n"
        "8. 🔐 Your deepest secret\n\n"
        "<i>Warning: Fake sacrifices will be rejected!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data.startswith("invite_sacrifice_"))
async def handle_invite_sacrifice(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    if len(data_parts) < 4:
        await callback.answer("Invalid selection!")
        return
    
    sacrifice_num = data_parts[2]
    inviter_id = int(data_parts[3])
    
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
    
    await callback.message.edit_text(f"🌀 <b>VERIFYING SACRIFICE...</b>\n\n⚡ {sacrifice}", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    
    is_real, status = await sacrifice_verification(sacrifice)
    
    if not is_real:
        await callback.answer("❌ Fake sacrifice detected!", show_alert=True)
        await callback.message.edit_text(
            f"❌ <b>SACRIFICE REJECTED!</b>\n\n"
            f"⚡ '{sacrifice}' is FAKE!\n"
            f"🌩️ The storm LAUGHS at your pathetic offering!\n"
            f"🌀 <i>Banned from initiation for 24 hours!</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    await callback.answer("✅ Sacrifice accepted! Starting ceremony...", show_alert=True)
    
    ceremony_steps = [
        "🩸 <b>STEP 1: BLOOD OATH</b>\n\nA black obsidian blade materializes...\nYour palm is cut, blood flows into ancient bowl...",
        "🔥 <b>STEP 2: ETERNAL FLAMES</b>\n\nDark flames consume your offering...\nThe sacrifice burns with green fire...",
        "👁️ <b>STEP 3: ELDER GAZE</b>\n\nAncient eyes watch from shadows...\nThe Council approves your blood...",
        "⚡ <b>STEP 4: LIGHTNING BRANDING</b>\n\nLightning strikes your chest...\nThe Tempest sigil burns into your soul...",
        "🌪️ <b>STEP 5: STORM CONSUMPTION</b>\n\nThe vortex opens...\nYour sacrifice is consumed by eternal tempest...",
        "🌀 <b>STEP 6: BLOOD BOND</b>\n\nYour blood mixes with the storm...\nThe tempest flows through your veins...",
        "💀 <b>STEP 7: FINAL RITE</b>\n\nYour name is carved in the Book of Shadows...\nThe blood pact is sealed for eternity..."
    ]
    
    for step in ceremony_steps:
        await callback.message.edit_text(step, parse_mode=ParseMode.HTML)
        await asyncio.sleep(2.5)
    
    user = callback.from_user
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
             (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()
    
    final_message = f"""⚡ <b>ETERNAL INITIATION COMPLETE!</b>

🌀 <b>WELCOME TO THE TEMPEST, {user.first_name.upper()}!</b>

🩸 <b>Sacrifice:</b> {sacrifice}
👑 <b>Rank:</b> Blood Initiate
⚔️ <b>Starting Sacrifices:</b> 3
🌪️ <b>Blood Oath:</b> ETERNAL

<i>The storm now flows through your veins.
Each upload feeds the Tempest.
Your journey of darkness begins...</i>

🌀 Check your status with /profile"""
    
    await callback.message.edit_text(final_message, parse_mode=ParseMode.HTML)
    
    try:
        inviter_name = "Unknown"
        try:
            inviter_chat = await bot.get_chat(inviter_id)
            inviter_name = inviter_chat.first_name
        except:
            pass
        
        await send_log(f"🌀 <b>Invited Tempest Member</b>\n\n👤 Name: {user.first_name}\n🆔 ID: {user.id}\n🤝 Invited by: {inviter_name}\n🩸 Sacrifice: {sacrifice}\n🌪️ Joined: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except:
        pass

@dp.callback_query(F.data.startswith("invite_cancel_"))
async def handle_invite_cancel(callback: CallbackQuery):
    await callback.message.edit_text("🌀 <b>Initiation cancelled. The storm is disappointed.</b>", parse_mode=ParseMode.HTML)
    await callback.answer("❌ Invitation cancelled", show_alert=True)

# ========== WELCOME MESSAGE WHEN BOT IS ADDED TO GROUP ==========
@dp.message(F.new_chat_members)
async def welcome_new_chat_members(message: Message):
    try:
        bot_id = (await bot.get_me()).id
        if any(member.id == bot_id for member in message.new_chat_members):
            conn = sqlite3.connect("data/bot.db")
            c = conn.cursor()
            c.execute("SELECT welcome_sent FROM groups WHERE group_id = ?", (message.chat.id,))
            result = c.fetchone()
            
            if not result or result[0] == 0:
                welcome_text = f"""🤖 <b>Hello {message.chat.title}!</b>

🌀 <b>PRO TELEGRAM BOT has joined your group!</b>

🔗 <b>Features:</b>
• Upload files with /link
• Check luck with /wish
• Fun games: /dice /flip
• Tempest cult system

📚 <b>Available Commands:</b>
<code>/help</code> - All commands
<code>/link</code> - Upload files
<code>/profile</code> - Your stats
<code>/tempest_cult</code> - Cult info

⚡ <b>Note:</b> Some commands work only in private chat.

<i>Type /help for complete command list!</i>"""
                
                await message.answer(welcome_text, parse_mode=ParseMode.HTML)
                
                if not result:
                    c.execute("INSERT INTO groups (group_id, title, username, joined_date, last_active, welcome_sent) VALUES (?, ?, ?, ?, ?, ?)",
                             (message.chat.id, message.chat.title, message.chat.username, datetime.now().isoformat(), datetime.now().isoformat(), 1))
                else:
                    c.execute("UPDATE groups SET welcome_sent = 1 WHERE group_id = ?", (message.chat.id,))
                
                conn.commit()
                conn.close()
                
                try:
                    await send_log(f"👥 <b>Bot Added to Group</b>\n\n📛 Group: {message.chat.title}\n🆔 ID: {message.chat.id}\n👤 Username: @{message.chat.username if message.chat.username else 'None'}\n🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    pass
    
    except Exception as e:
        print(f"Error in welcome message: {e}")

# ========== MAIN ==========
async def main():
    print("🚀 PRO BOT PROPER VERSION STARTING...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ Database initialized")
    print(f"🌀 Log Channel ID: {LOG_CHANNEL_ID}")
    print("📢 Broadcast: PROPER - ALL users/groups + Button option")
    print("🔗 Upload: WORKS IN GROUPS")
    print("📜 Story: 8 CHAPTERS")
    print("👤 Profile: TEMPEST STATUS")
    print("📨 Invite: FULL CEREMONY")
    print("🌀 Tempest_cult: SHOWS MEMBERS")
    print("🚫 /disable: PROPER TIME FORMAT (30m, 2h, 1d)")
    print("👋 Welcome: GROUP WELCOME")
    print("=" * 50)
    
    try:
        startup_log = f"🤖 <b>Bot Started - Proper Fixes</b>\n\n🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🌀 Version: All Features Active\n⚡ Broadcast: Works for ALL users/groups\n🔘 Button Option: Yes\n⏰ /disable: Proper time format"
        await send_log(startup_log)
        print("✅ Log channel connected")
    except Exception as e:
        print(f"⚠️ Log channel error: {e}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped gracefully")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
