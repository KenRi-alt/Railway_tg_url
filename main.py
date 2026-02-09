#!/usr/bin/env python3
# ========== COMPLETE FIXED CODE - FINAL VERSION ==========
import sys
print("=" * 60)
print("🚀 URGENT FIXES APPLIED")
print("✅ Callback errors fixed")
print("✅ Case-sensitive commands fixed")
print("✅ Broadcast media fixed")
print("✅ Bot remembers state on restart")
print("✅ Curse system added (hidden)")
print("✅ Profile picture cards with Tempest Creed")
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
from datetime import datetime, timedelta
from pathlib import Path

# NEW: Add Pillow for profile cards
from PIL import Image, ImageDraw, ImageFont, ImageOps

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

print("🤖 PRO BOT FINAL FIXES INITIALIZING...")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = 1003662720845  # Log channel ID without hyphen

# Create directories
Path("data").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True)
Path("backups").mkdir(exist_ok=True)
Path("profile_cards").mkdir(exist_ok=True)  # NEW: For profile card images

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True
upload_waiting = {}
broadcast_state = {}
pending_joins = {}
pending_invites = {}
story_states = {}

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
        sacrifices INTEGER DEFAULT 0,
        curse_type TEXT DEFAULT 'none',
        curse_time TEXT DEFAULT NULL,
        curse_by INTEGER DEFAULT NULL
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS bot_state (
        key TEXT PRIMARY KEY,
        value TEXT,
        timestamp TEXT
    )''')
    
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== PROFILE CARD GENERATOR ==========
def create_profile_card(user_data):
    """
    Create a profile card image with Tempest design
    user_data: (user_id, first_name, username, uploads, commands, wishes, cult_rank, sacrifices, curse_type, joined_date)
    Returns: Path to saved image or None if failed
    """
    try:
        user_id, first_name, username, uploads, commands, wishes, cult_rank, sacrifices, curse_type, joined_date = user_data
        
        # Create base image (800x400 pixels)
        width, height = 800, 400
        
        # Create gradient background (dark stormy colors)
        base = Image.new('RGB', (width, height), color='#0a0a1a')
        draw = ImageDraw.Draw(base)
        
        # Add gradient effect
        for i in range(height):
            r = max(10, int(10 + i * 0.1))
            g = max(10, int(10 + i * 0.05))
            b = max(26, int(26 + i * 0.15))
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        
        # Add storm effect lines (lightning effects)
        for _ in range(30):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = x1 + random.randint(-50, 50)
            y2 = y1 + random.randint(20, 100)
            draw.line([(x1, y1), (x2, y2)], fill=(100, 100, 200, 100), width=2)
        
        # Load fonts (try system fonts, fallback to default)
        try:
            title_font = ImageFont.truetype("arialbd.ttf", 32)
            name_font = ImageFont.truetype("arialbd.ttf", 28)
            stat_font = ImageFont.truetype("arial.ttf", 22)
            small_font = ImageFont.truetype("arial.ttf", 18)
        except:
            # Use default font if system fonts not available
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            stat_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw Tempest Creed Title
        draw.text((width // 2, 30), "🌀 TEMPEST CREED PROFILE", fill=(100, 200, 255), font=title_font, anchor="mm")
        
        # Draw user name
        name = first_name[:20]
        draw.text((width // 2, 80), f"👤 {name}", fill=(255, 255, 255), font=name_font, anchor="mm")
        
        # Draw username
        uname = f"@{username}" if username else "No username"
        draw.text((width // 2, 115), uname, fill=(180, 180, 220), font=small_font, anchor="mm")
        
        # Draw stats boxes
        stats_y = 160
        stat_width = 180
        spacing = 20
        
        # Uploads
        draw.rectangle([(50, stats_y), (50 + stat_width, stats_y + 60)], fill=(20, 40, 80, 150), outline=(0, 150, 255))
        draw.text((50 + stat_width // 2, stats_y + 15), "📁 UPLOADS", fill=(100, 200, 255), font=stat_font, anchor="mm")
        draw.text((50 + stat_width // 2, stats_y + 40), str(uploads), fill=(255, 255, 255), font=stat_font, anchor="mm")
        
        # Wishes
        draw.rectangle([(50 + stat_width + spacing, stats_y), (50 + stat_width * 2 + spacing, stats_y + 60)], 
                      fill=(40, 20, 80, 150), outline=(150, 0, 255))
        draw.text((50 + stat_width + spacing + stat_width // 2, stats_y + 15), "✨ WISHES", fill=(200, 100, 255), font=stat_font, anchor="mm")
        draw.text((50 + stat_width + spacing + stat_width // 2, stats_y + 40), str(wishes), fill=(255, 255, 255), font=stat_font, anchor="mm")
        
        # Commands
        draw.rectangle([(50 + stat_width * 2 + spacing * 2, stats_y), (50 + stat_width * 3 + spacing * 2, stats_y + 60)], 
                      fill=(20, 80, 40, 150), outline=(0, 255, 150))
        draw.text((50 + stat_width * 2 + spacing * 2 + stat_width // 2, stats_y + 15), "🔧 COMMANDS", fill=(100, 255, 200), font=stat_font, anchor="mm")
        draw.text((50 + stat_width * 2 + spacing * 2 + stat_width // 2, stats_y + 40), str(commands), fill=(255, 255, 255), font=stat_font, anchor="mm")
        
        # Tempest Info Section
        info_y = 240
        
        # Cult Rank
        if cult_rank and cult_rank != "none":
            rank_text = f"👑 {cult_rank}"
            sacrifice_text = f"⚔️ {sacrifices} Sacrifices"
            draw.text((50, info_y), rank_text, fill=(255, 100, 100), font=stat_font)
            draw.text((50, info_y + 30), sacrifice_text, fill=(255, 200, 100), font=stat_font)
        else:
            draw.text((50, info_y), "🌀 Not Initiated", fill=(150, 150, 150), font=stat_font)
            draw.text((50, info_y + 30), "⚡ Use /tempest_join", fill=(200, 200, 100), font=small_font)
        
        # Curse Status
        if curse_type and curse_type != "none":
            curse_y = info_y
            curse_text = f"⚡ CURSED: {curse_type}"
            draw.text((width - 250, curse_y), curse_text, fill=(255, 50, 50), font=stat_font)
            
            # Add cursed border
            draw.rectangle([(0, 0), (width-1, height-1)], outline=(255, 50, 50), width=5)
        
        # User ID and Date
        id_text = f"🆔 {user_id}"
        date_text = f"📅 {joined_date}"
        draw.text((width - 250, info_y + 30), id_text, fill=(150, 200, 255), font=small_font)
        draw.text((width - 250, info_y + 55), date_text, fill=(150, 200, 255), font=small_font)
        
        # Bottom text
        bottom_text = "🌀 The storm flows through your veins"
        draw.text((width // 2, height - 30), bottom_text, fill=(100, 150, 255), font=small_font, anchor="mm")
        
        # Save the image
        filename = f"profile_cards/profile_{user_id}_{int(time.time())}.png"
        base.save(filename, "PNG")
        
        return filename
        
    except Exception as e:
        print(f"❌ Error creating profile card: {e}")
        traceback.print_exc()
        return None

# ========== BOT STATE SAVING/RESTORING ==========
def save_bot_state():
    """Save bot state to database"""
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        # Clear old states
        c.execute("DELETE FROM bot_state")
        
        # Save upload_waiting
        for user_id, waiting in upload_waiting.items():
            if waiting:
                c.execute("INSERT INTO bot_state (key, value, timestamp) VALUES (?, ?, ?)",
                         (f"upload_{user_id}", "1", now))
        
        # Save broadcast states
        for user_id, state in broadcast_state.items():
            c.execute("INSERT INTO bot_state (key, value, timestamp) VALUES (?, ?, ?)",
                     (f"broadcast_{user_id}", json.dumps(state), now))
        
        conn.commit()
        conn.close()
        return True
    except:
        return False

def load_bot_state():
    """Load bot state from database"""
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        # Clear current states
        upload_waiting.clear()
        broadcast_state.clear()
        
        # Load upload_waiting
        c.execute("SELECT key FROM bot_state WHERE key LIKE 'upload_%'")
        upload_rows = c.fetchall()
        for (key,) in upload_rows:
            user_id = int(key.split("_")[1])
            upload_waiting[user_id] = True
        
        # Load broadcast states
        c.execute("SELECT key, value FROM bot_state WHERE key LIKE 'broadcast_%'")
        broadcast_rows = c.fetchall()
        for key, value in broadcast_rows:
            user_id = int(key.split("_")[1])
            try:
                broadcast_state[user_id] = json.loads(value)
            except:
                pass
        
        conn.close()
        print(f"✅ Restored {len(upload_waiting)} upload states, {len(broadcast_state)} broadcast states")
        return True
    except Exception as e:
        print(f"❌ Failed to load bot state: {e}")
        return False

# Load state on startup
load_bot_state()

# ========== HELPER FUNCTIONS ==========
async def safe_answer_callback(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    """Safely answer callback queries, ignoring 'query is too old' errors"""
    try:
        await callback.answer(text, show_alert=show_alert)
    except TelegramBadRequest as e:
        if "query is too old" in str(e).lower():
            pass  # Just ignore expired queries
        else:
            raise e

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

# ========== SCAN FUNCTION ==========
async def scan_users_and_groups():
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
                    user = await bot.get_chat(user_id)
                    if user.type == 'private':
                        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                        if not c.fetchone():
                            c.execute("INSERT INTO users (user_id, username, first_name, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                                     (user_id, user.username, user.first_name, datetime.now().isoformat(), datetime.now().isoformat()))
                            updated_users += 1
                            new_users += 1
                        else:
                            c.execute("UPDATE users SET username = ?, first_name = ?, last_active = ? WHERE user_id = ?",
                                     (user.username, user.first_name, datetime.now().isoformat(), user_id))
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
        
        return f"""✅ <b>Scan Complete!</b>

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
    
    await send_log(f"👤 <b>User Started Bot</b>\n\nID: <code>{user.id}</code>\nName: {user.first_name}\nUsername: @{user.username if user.username else 'None'}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await message.answer(
        f"✨ <b>Hey {user.first_name}!</b>\n\n"
        "🤖 <b>PRO TELEGRAM BOT</b>\n\n"
        "🔗 Upload files & get direct links\n"
        "✨ Wish fortune teller\n"
        "🎮 Fun games (dice, coin flip)\n"
        "👑 Admin controls\n"
        "🌀 Tempest Creed profile cards\n\n"
        "📁 <b>Upload:</b> Send <code>/link</code> then any file\n"
        "🎮 <b>Games:</b> <code>/dice</code> <code>/flip</code> <code>/wish [text]</code>\n"
        "👤 <b>Profile:</b> <code>/profile</code> (with image card!)\n"
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
<code>/profile</code> - Your stats (with image card!)
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

# ========== ADMIN COMMANDS ==========
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
    
    c.execute("SELECT uploads, commands, joined_date, curse_type, cult_rank, sacrifices FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    
    if row:
        uploads, cmds, joined, curse_type, cult_rank, sacrifices = row
        c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (user.id,))
        wishes = c.fetchone()[0] or 0
        
        try:
            join_date = datetime.fromisoformat(joined).strftime("%d %b %Y")
        except:
            join_date = "Recently"
    else:
        uploads = cmds = wishes = sacrifices = 0
        join_date = "Today"
        curse_type = "none"
        cult_rank = "none"
    
    conn.close()
    
    # Try to create profile card image
    user_data = (user.id, user.first_name, user.username, uploads, cmds, wishes, 
                cult_rank, sacrifices, curse_type, join_date)
    
    profile_card_path = create_profile_card(user_data)
    
    if profile_card_path and os.path.exists(profile_card_path):
        # Send profile card image
        caption = f"""
🌀 <b>TEMPEST CREED PROFILE CARD</b>

👤 <b>Name:</b> {user.first_name}
📧 <b>Username:</b> @{user.username if user.username else 'None'}
🆔 <b>ID:</b> <code>{user.id}</code>

📁 <b>Uploads:</b> {uploads}
✨ <b>Wishes:</b> {wishes}
🔧 <b>Commands:</b> {cmds}
📅 <b>Joined:</b> {join_date}
"""
        
        # Add cult info if in Tempest
        if cult_rank != "none":
            caption += f"\n🌀 <b>Tempest Rank:</b> {cult_rank}"
            caption += f"\n⚔️ <b>Sacrifices:</b> {sacrifices}"
        
        # Add curse info if cursed
        if curse_type != "none":
            caption += f"\n⚡ <b>Curse:</b> {curse_type}"
        
        caption += "\n\n🌀 <i>The storm flows through your veins...</i>"
        
        try:
            await message.answer_photo(
                FSInputFile(profile_card_path),
                caption=caption,
                parse_mode=ParseMode.HTML
            )
            
            # Clean up the temporary image file after sending
            try:
                os.remove(profile_card_path)
            except:
                pass
            return
            
        except Exception as e:
            print(f"Failed to send profile card: {e}")
            # Fall back to text version
    
    # Fallback to text profile if image creation fails
    curse_text = ""
    if curse_type != "none":
        curse_text = f"\n🔮 <b>Curse Status:</b> ⚡ {curse_type}"
    
    cult_text = ""
    if cult_rank != "none":
        cult_text = f"\n🌀 <b>Tempest Rank:</b> {cult_rank}"
        cult_text += f"\n⚔️ <b>Sacrifices:</b> {sacrifices}"
    
    profile_text = f"""
🌀 <b>TEMPEST CREED PROFILE</b>

👤 <b>Name:</b> {user.first_name}
📧 <b>Username:</b> @{user.username if user.username else 'None'}
🆔 <b>ID:</b> <code>{user.id}</code>

📁 <b>Uploads:</b> {uploads}
✨ <b>Wishes:</b> {wishes}
🔧 <b>Commands:</b> {cmds}
📅 <b>Joined:</b> {join_date}{cult_text}{curse_text}

🌀 <i>The storm flows through your veins...</i>
"""
    
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

# ========== PRO COMMAND ==========
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
    
    await send_log(f"👑 <b>Admin Promotion</b>\n\nPromoted by: {user.first_name}\nPromoted user: {target_id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await message.answer(f"✅ User {target_id} promoted to admin!")

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

# ========== FIXED BROADCAST COMMANDS ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast_start")
    
    if not await is_admin(user.id):
        return
    
    broadcast_state[user.id] = {"type": "users", "step": 1}
    save_bot_state()  # Save state
    
    await message.answer(
        "📢 <b>BROADCAST TO ALL USERS</b>\n\n"
        "Send any message now:\n"
        "• Text message\n"
        "• Photo with caption\n"
        "• Video with caption\n"
        "• Document with caption\n\n"
        "⚠️ <b>Next message will be sent to ALL USERS</b>\n"
        "❌ <code>/cancel</code> to abort",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("broadcast_gc"))
async def broadcast_gc_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast_gc_start")
    
    if not await is_admin(user.id):
        return
    
    broadcast_state[user.id] = {"type": "groups", "step": 1}
    save_bot_state()  # Save state
    
    await message.answer(
        "📢 <b>BROADCAST TO ALL GROUPS</b>\n\n"
        "Send any message now:\n"
        "• Text message\n"
        "• Photo with caption\n"
        "• Video with caption\n"
        "• Document with caption\n\n"
        "⚠️ <b>Next message will be sent to ALL GROUPS</b>\n"
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
    
    global broadcast_state, pending_joins, pending_invites, story_states
    broadcast_state.clear()
    pending_joins.clear()
    pending_invites.clear()
    story_states.clear()
    
    save_bot_state()  # Save cleared state
    
    await message.answer("🔄 <b>Bot cache refreshed!</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("emergency_stop"))
async def emergency_stop(message: Message):
    user, chat = await handle_common(message, "emergency_stop")
    
    if user.id != OWNER_ID:
        return
    
    global bot_active
    bot_active = False
    
    await message.answer("🛑 <b>BOT EMERGENCY STOPPED!</b>", parse_mode=ParseMode.HTML)

# ========== FILE UPLOAD WITH COPY/SHARE BUTTONS ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")
    
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 <b>Upload files in private chat only</b>", parse_mode=ParseMode.HTML)
        return
    
    upload_waiting[user.id] = True
    save_bot_state()  # Save state
    
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
    save_bot_state()  # Save state
    
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
        
        # Create keyboard with copy and share buttons
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="📋 Copy Link", callback_data=f"copy_{result['url']}"))
        keyboard.add(InlineKeyboardButton(text="🔗 Share", url=f"https://t.me/share/url?url={result['url']}"))
        
        result_text = f"""✅ <b>Upload Complete!</b>

📁 <b>Type:</b> {file_type}
💾 <b>Size:</b> {size_text}
👤 <b>By:</b> {user.first_name}

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
    url = callback.data[5:]  # Remove "copy_" prefix
    await safe_answer_callback(callback, f"Link copied to clipboard!\n{url}", show_alert=True)

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user, chat = await handle_common(message, "cancel")
    
    if user.id in upload_waiting:
        upload_waiting[user.id] = False
        save_bot_state()  # Save state
        await message.answer("❌ Upload cancelled")
    
    if user.id in broadcast_state:
        broadcast_state.pop(user.id, None)
        save_bot_state()  # Save state
        await message.answer("❌ Broadcast cancelled")
    
    if user.id in story_states:
        story_states.pop(user.id, None)
        await message.answer("❌ Story cancelled")

# ========== GAMES ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ <b>Usage:</b> <code>/wish your wish here</code>", parse_mode=ParseMode.HTML)
        return
    
    msg = await message.answer("✨ <b>Reading your destiny...</b>", parse_mode=ParseMode.HTML)
    
    # Check if user is cursed
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT curse_type FROM users WHERE user_id = ?", (user.id,))
    curse_result = c.fetchone()
    curse_type = curse_result[0] if curse_result else "none"
    
    # Apply curse penalty if cursed
    curse_penalty = 0
    curse_message = ""
    if curse_type != "none":
        curse_penalty = random.randint(15, 30)  # -15 to -30% luck
        curse_message = f"\n⚡ <b>Curse penalty:</b> -{curse_penalty}%"
    
    for emoji in ["🌟", "⭐", "💫", "🌠", "✨"]:
        await msg.edit_text(f"{emoji} <b>Consulting the stars...</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    base_luck = random.randint(1, 100)
    luck = max(1, base_luck - curse_penalty)  # Apply curse penalty
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
    
    c.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
             (user.id, datetime.now().isoformat(), args[1], luck))
    conn.commit()
    conn.close()
    
    await msg.edit_text(
        f"🔮 <b>WISH RESULT</b>\n\n"
        f"📜 <b>Wish:</b> {args[1]}\n"
        f"🎰 <b>Luck:</b> {stars} {luck}%{curse_message}\n"
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

# ========== HIDDEN TEMPEST PROGRESS ==========
@dp.message(Command("tempest_progress", ignore_case=True))  # FIXED: Case insensitive
async def tempest_progress_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_progress")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status, cult_rank, sacrifices, cult_join_date, curse_type FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        status, rank, sacrifices, join_date, curse_type = result
        
        try:
            join_dt = datetime.fromisoformat(join_date)
            days = (datetime.now() - join_dt).days
            time_text = f"{days} days" if days > 0 else "Today"
        except:
            time_text = "Recently"
        
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
        
        progress_bar = "🩸" * (progress // 10) + "⚫" * (10 - progress // 10)
        
        # Add curse info if cursed
        curse_text = ""
        if curse_type != "none":
            curse_text = f"\n⚡ <b>Curse:</b> {curse_type} (affects wish luck)"
        
        progress_text = f"""
🌀 <b>TEMPEST BLOOD PROGRESS</b>

👤 <b>Storm-Born:</b> {user.first_name}
👑 <b>Current Rank:</b> {rank}
⚔️ <b>Blood Sacrifices:</b> {sacrifices}
📅 <b>Blood Oath Since:</b> {time_text}{curse_text}

<b>Blood Progress:</b> [{progress_bar}] {progress:.1f}%
<b>Next Rank:</b> {next_rank}
<b>Sacrifices Needed:</b> {needed}

⚡ <i>Each upload = 1 sacrifice to the storm</i>
🌪️ <i>Feed the tempest, grow in power...</i>
        """
    else:
        progress_text = """
🌀 <b>TEMPEST PROGRESS</b>

👤 <b>Status:</b> Not initiated
👁️ <b>Vision:</b> Blind to the storm

⚡ Use /Tempest_join to begin your journey
🌩️ The storm awaits worthy blood...
💀 Warning: Fake offerings will be rejected!
        """
    
    conn.close()
    await message.answer(progress_text, parse_mode=ParseMode.HTML)

# ========== CURSE COMMAND (HIDDEN TEMPEST COMMAND) ==========
@dp.message(Command("curse", ignore_case=True))
async def curse_cmd(message: Message):
    """Curse a user with Ravijah's wrath"""
    user, chat = await handle_common(message, "curse")
    
    # Check if user is admin or in Tempest
    if not await is_admin(user.id):
        # Check if user is in Tempest cult
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        result = c.fetchone()
        if not result or result[0] == "none":
            await message.answer("🌀 This command is for Tempest members only.")
            conn.close()
            return
        conn.close()
    
    # Check if replying to a message
    if not message.reply_to_message:
        await message.answer("🌀 <b>Reply to a user's message to curse them!</b>", parse_mode=ParseMode.HTML)
        return
    
    target_user = message.reply_to_message.from_user
    
    # Can't curse yourself
    if target_user.id == user.id:
        await message.reply("🌀 You cannot curse yourself!")
        return
    
    # Can't curse admins
    if await is_admin(target_user.id):
        await message.reply("🌀 You cannot curse an admin!")
        return
    
    # Check if target is already cursed
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT curse_type FROM users WHERE user_id = ?", (target_user.id,))
    existing_curse = c.fetchone()
    
    if existing_curse and existing_curse[0] != "none":
        await message.reply(f"🌀 {target_user.first_name} is already cursed with {existing_curse[0]}!")
        conn.close()
        return
    
    # Select random curse
    curses = [
        ("Misfortune", "May misfortune follow your every step!"),
        ("Bad Luck", "Bad luck shall be your constant companion!"),
        ("Storm's Wrath", "The storm's wrath shall rain upon you!"),
        ("Eternal Suffering", "May you know eternal suffering!"),
        ("Ravijah's Displeasure", "You have earned Ravijah's displeasure!"),
        ("Shadow's Grip", "The shadows shall never release you!")
    ]
    
    curse_type, curse_quote = random.choice(curses)
    
    # Update database
    c.execute("UPDATE users SET curse_type = ?, curse_time = ?, curse_by = ? WHERE user_id = ?",
             (curse_type, datetime.now().isoformat(), user.id, target_user.id))
    conn.commit()
    conn.close()
    
    # Curse animation sequence
    msg = await message.reply(f"🌀 <b>INITIATING CURSE RITUAL...</b>")
    
    curse_steps = [
        f"🌀 <b>GATHERING DARK ENERGY...</b>\nTarget: {target_user.first_name}",
        f"⚡ <b>SUMMONING RAVIJAH'S WRATH...</b>\nCurse: {curse_type}",
        f"🌪️ <b>WEAVING THE CURSE SPELL...</b>\nBinding to {target_user.first_name}'s soul",
        f"🔥 <b>ETERNAL FLAMES CONSUME...</b>\nThe curse takes hold",
        f"💀 <b>CURSE SEALED FOR ETERNITY!</b>\n{target_user.first_name} is now cursed!"
    ]
    
    for step in curse_steps:
        await msg.edit_text(step, parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.5)
    
    final_message = f"""
⚡ <b>ETERNAL CURSE BESTOWED!</b>

👤 <b>Target:</b> {target_user.first_name}
🌀 <b>Curse Type:</b> {curse_type}
👑 <b>Cursed By:</b> {user.first_name}
⏰ <b>Time:</b> {datetime.now().strftime("%H:%M:%S")}

📜 <b>The Curse:</b>
"{curse_quote}"

⚡ <i>You shall suffer the great Ravijah's wrath!</i>
🌀 <i>The storm remembers all offenses...</i>

💀 <b>Effects:</b>
• -15 to -30% wish luck penalty
• Visible in /profile and /tempest_progress
• Lasts until removed by admin
"""
    
    await msg.edit_text(final_message, parse_mode=ParseMode.HTML)
    
    # Send log
    await send_log(f"⚡ <b>Curse Cast</b>\n\n👤 Target: {target_user.first_name}\n🆔 Target ID: {target_user.id}\n🌀 Curse: {curse_type}\n👑 Cursed by: {user.first_name}\n⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ========== REMOVE CURSE COMMAND ==========
@dp.message(Command("remove_curse", ignore_case=True))
async def remove_curse_cmd(message: Message):
    """Remove curse from a user"""
    user, chat = await handle_common(message, "remove_curse")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    # Check if replying to a message
    if not message.reply_to_message:
        await message.answer("🌀 <b>Reply to a user's message to remove their curse!</b>", parse_mode=ParseMode.HTML)
        return
    
    target_user = message.reply_to_message.from_user
    
    # Check if target is cursed
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT curse_type FROM users WHERE user_id = ?", (target_user.id,))
    existing_curse = c.fetchone()
    
    if not existing_curse or existing_curse[0] == "none":
        await message.reply(f"🌀 {target_user.first_name} is not cursed!")
        conn.close()
        return
    
    # Remove curse
    c.execute("UPDATE users SET curse_type = 'none', curse_time = NULL, curse_by = NULL WHERE user_id = ?",
             (target_user.id,))
    conn.commit()
    conn.close()
    
    await message.reply(f"""
✅ <b>CURSE REMOVED!</b>

👤 <b>Target:</b> {target_user.first_name}
👑 <b>Removed by:</b> {user.first_name}
⏰ <b>Time:</b> {datetime.now().strftime("%H:%M:%S")}

🌀 <i>The storm's wrath has been appeased.
May you walk in the light once more...</i>
""", parse_mode=ParseMode.HTML)

# ========== TEMPEST JOIN WITH BLOODY CEREMONY ==========
@dp.message(Command("tempest_join", ignore_case=True))  # FIXED: Case insensitive
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
        await safe_answer_callback(callback, "❌ Initiation expired!", show_alert=True)  # FIXED
        return
    
    if callback.data == "sacrifice_cancel":
        del pending_joins[user.id]
        await callback.message.edit_text("🌀 <b>Initiation cancelled. The storm is disappointed.</b>", parse_mode=ParseMode.HTML)
        await safe_answer_callback(callback)  # FIXED
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
        await safe_answer_callback(callback, "❌ Fake sacrifice detected!", show_alert=True)  # FIXED
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

🌀 Use /Tempest_progress to track your bloody path"""
    
    await msg.edit_text(final_message, parse_mode=ParseMode.HTML)
    
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
    
    await safe_answer_callback(callback, "✅ Sacrifice accepted! Welcome to the Tempest!", show_alert=True)  # FIXED

# ========== TEMPEST STORY WITH 8 CHAPTERS AND ANIMATIONS ==========
@dp.message(Command("tempest_story", ignore_case=True))  # FIXED: Case insensitive
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
    
    # Start story at chapter 1
    story_states[user.id] = {"chapter": 1}
    
    # Chapter 1 with animation
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
        # Show animation before chapter
        await callback.message.edit_text(f"🌀 <b>Turning page {chapter_num}/8...</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)
        
        keyboard = InlineKeyboardBuilder()
        
        if chapter_num < 8:
            keyboard.add(InlineKeyboardButton(text=f"🌪️ Continue to Chapter {chapter_num + 1}", callback_data=f"story_next_{chapter_num + 1}"))
        else:
            keyboard.add(InlineKeyboardButton(text="⚡ Story Complete", callback_data="story_end"))
        
        await callback.message.edit_text(chapters[chapter_num], parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup() if chapter_num < 8 else None)
        await safe_answer_callback(callback)  # FIXED
    else:
        await safe_answer_callback(callback, "Story complete!")  # FIXED

@dp.callback_query(F.data == "story_end")
async def handle_story_end(callback: CallbackQuery):
    await callback.message.edit_text("📜 <b>THE TEMPEST SAGA</b>\n\n<i>Your understanding of the storm is complete. Your journey continues with each sacrifice. Make your mark in the eternal tempest.</i>", parse_mode=ParseMode.HTML)
    await safe_answer_callback(callback)  # FIXED
    
    # Auto-delete after 30 seconds
    await asyncio.sleep(30)
    try:
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
    except:
        pass

# ========== FIXED REPLY INVITATION SYSTEM ==========
@dp.message(F.reply_to_message)
async def handle_reply_invite(message: Message):
    """Handle when someone replies to a message with Tempest_join"""
    user, chat = await handle_common(message, "reply_invite")
    
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
    # Check if message contains Tempest_join (case insensitive)
    if "tempest_join" in message.text.lower() or "join tempest" in message.text.lower():
        replied_user = message.reply_to_message.from_user
        
        if replied_user.id == user.id:
            await message.reply("🤨 You can't invite yourself!")
            return
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (replied_user.id,))
        result = c.fetchone()
        
        if result and result[0] != "none":
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
        keyboard.add(InlineKeyboardButton(text="✅ Accept Blood Pact", callback_data=f"reply_invite_accept_{invite_id}"))
        keyboard.add(InlineKeyboardButton(text="❌ Decline", callback_data=f"reply_invite_decline_{invite_id}"))
        
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

<i>Invitation expires in 2 minutes...</i>"""
        
        invite_msg = await message.reply(invite_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
        
        await asyncio.sleep(120)
        try:
            await bot.delete_message(chat.id, invite_msg.message_id)
            if invite_id in pending_invites:
                del pending_invites[invite_id]
        except:
            pass

@dp.callback_query(F.data.startswith("reply_invite_"))
async def handle_reply_invite_response(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    if len(data_parts) < 5:
        await safe_answer_callback(callback, "Invalid invite!")  # FIXED
        return
    
    action = data_parts[3]
    invite_id = "_".join(data_parts[4:])
    
    if invite_id not in pending_invites:
        await safe_answer_callback(callback, "Invite expired!")  # FIXED
        return
    
    invite_data = pending_invites[invite_id]
    user = callback.from_user
    
    if user.id != invite_data["target_id"]:
        await safe_answer_callback(callback, "This invitation isn't for you!", show_alert=True)  # FIXED
        return
    
    if action == "accept":
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        result = c.fetchone()
        
        if result and result[0] != "none":
            await safe_answer_callback(callback, "You're already in the cult!", show_alert=True)  # FIXED
            conn.close()
            return
        
        c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
                 (datetime.now().isoformat(), user.id))
        conn.commit()
        conn.close()
        
        await safe_answer_callback(callback, "✅ Blood pact accepted!", show_alert=True)  # FIXED
        
        await callback.message.edit_text(
            f"🎉 <b>BLOOD PACT SEALED!</b>\n\n"
            f"👤 <b>{user.first_name}</b> has accepted {invite_data['inviter_name']}'s invitation!\n"
            f"🩸 Blood oath sworn to the Tempest\n"
            f"🌀 Rank: Blood Initiate\n"
            f"⚔️ Starting sacrifices: 3\n\n"
            f"<i>The storm grows stronger with new blood...</i>",
            parse_mode=ParseMode.HTML
        )
        
        # Send log
        await send_log(f"🌀 <b>Invitation Accepted</b>\n\n👤 Invited: {user.first_name}\n👑 Inviter: {invite_data['inviter_name']}\n🆔 User ID: {user.id}\n🌪️ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    elif action == "decline":
        await safe_answer_callback(callback, "❌ Invitation declined", show_alert=True)  # FIXED
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

# ========== FIXED BROADCAST HANDLER ==========
@dp.message()
async def handle_broadcast(message: Message):
    user = message.from_user
    chat = message.chat
    
    update_user(user)
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(chat)
    
    # Check if user is in broadcast state AND this is the content message
    if user.id in broadcast_state:
        # Check if we're on step 1 (waiting for content)
        if broadcast_state[user.id].get("step") == 1:
            # Process the broadcast
            broadcast_data = broadcast_state[user.id]
            broadcast_type = broadcast_data["type"]
            
            # Move to step 2 immediately
            broadcast_state[user.id]["step"] = 2
            save_bot_state()  # Save state
            
            if broadcast_type == "users":
                conn = sqlite3.connect("data/bot.db")
                c = conn.cursor()
                c.execute("SELECT user_id FROM users WHERE is_banned = 0")
                targets = [row[0] for row in c.fetchall()]
                conn.close()
                target_type = "users"
            else:  # groups
                conn = sqlite3.connect("data/bot.db")
                c = conn.cursor()
                c.execute("SELECT group_id FROM groups")
                targets = [row[0] for row in c.fetchall()]
                conn.close()
                target_type = "groups"
            
            total = len(targets)
            if total == 0:
                await message.answer(f"❌ No {target_type} found to broadcast!")
                broadcast_state.pop(user.id, None)
                save_bot_state()  # Save state
                return
            
            status_msg = await message.answer(f"📤 Sending to {total} {target_type}...")
            
            success = 0
            failed = 0
            
            # Handle all message types including media
            for target_id in targets:
                try:
                    if message.text:
                        await bot.send_message(target_id, f"📢 {message.text}")
                    elif message.photo:
                        caption = message.caption or "📢 Broadcast"
                        await bot.send_photo(target_id, message.photo[-1].file_id, caption=caption)
                    elif message.video:
                        caption = message.caption or "📢 Broadcast"
                        await bot.send_video(target_id, message.video.file_id, caption=caption)
                    elif message.document:
                        caption = message.caption or "📢 Broadcast"
                        await bot.send_document(target_id, message.document.file_id, caption=caption)
                    elif message.audio:
                        caption = message.caption or "📢 Broadcast"
                        await bot.send_audio(target_id, message.audio.file_id, caption=caption)
                    elif message.sticker:
                        await bot.send_sticker(target_id, message.sticker.file_id)
                    elif message.animation:
                        caption = message.caption or "📢 Broadcast"
                        await bot.send_animation(target_id, message.animation.file_id, caption=caption)
                    elif message.voice:
                        await bot.send_voice(target_id, message.voice.file_id)
                    
                    success += 1
                    await asyncio.sleep(0.05)  # Rate limiting
                except Exception as e:
                    failed += 1
                    continue
            
            # Clear broadcast state after completion
            broadcast_state.pop(user.id, None)
            save_bot_state()  # Save state
            
            await status_msg.edit_text(f"✅ Sent to {success}/{total} {target_type}\n❌ Failed: {failed}")
            
            # Log the broadcast
            await send_log(f"📢 <b>Broadcast Sent</b>\n\nBy: {user.first_name}\nType: {target_type}\nSent: {success}/{total}\nFailed: {failed}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ========== MAIN ==========
async def main():
    print("🚀 PRO BOT WITH ALL FIXES STARTING...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ Database initialized")
    print("🌀 Tempest: ALL CALLBACKS FIXED")
    print("📡 Scan: WORKING")
    print("📊 Log Channel: ACTIVE")
    print("📢 Broadcast: MEDIA SUPPORT FIXED")
    print("🔗 Upload: COPY/SHARE WORKING")
    print("📜 Story: 8 CHAPTERS FIXED")
    print("⚡ Curse System: ADDED")
    print("💾 State Saving: ENABLED")
    print("🖼️ Profile Cards: ENABLED (with Pillow)")
    print("=" * 50)
    
    # Send startup log
    startup_log = f"🤖 <b>Bot Started - Complete Features</b>\n\n🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🌀 Version: Complete Features\n⚡ Status: ALL SYSTEMS ACTIVE\n💾 State Restored: YES\n🖼️ Profile Cards: ENABLED"
    await send_log(startup_log)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        save_bot_state()  # Save state before exit
        print("\n🛑 Bot stopped gracefully (state saved)")
    except Exception as e:
        save_bot_state()  # Save state on error
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
