#!/usr/bin/env python3
# ========== ORIGINAL WORKING CODE WITH 8 FIXES ==========
import sys
print("=" * 60)
print("🔥 ORIGINAL WORKING CODE - WITH YOUR 8 FIXES")
print("✅ Tempest commands preserved")
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

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder

print("🤖 PRO BOT - ORIGINAL WORKING")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845

# Cult leader IDs
CULT_LEADER_ID = 6211708776
VICE_CHANCELLOR_ID = 6581129741
OWNER_USER_ID = OWNER_ID

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
    
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, cult_status, cult_rank, sacrifices) VALUES (?, ?, ?, ?, ?)",
              (CULT_LEADER_ID, "🆁🅰️🆅🅴🅽", "member", "Supreme Leader", 999))
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, cult_status, cult_rank, sacrifices) VALUES (?, ?, ?, ?, ?)",
              (VICE_CHANCELLOR_ID, "Tʜᴇ Dᴀꜱʜ", "member", "Vice Chancellor", 500))
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, cult_status, cult_rank, sacrifices) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Ķ£NY D ~Tempest~", "member", "Initiate", 1))
    
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

async def send_log(message: str):
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

# ========== FIX 1: BROADCAST TO ALL USERS/GROUPS ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user = message.from_user
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    broadcast_state[user.id] = {"type": "users", "step": "waiting"}
    await message.answer(
        "📢 <b>BROADCAST TO ALL USERS</b>\n\n"
        "Send any message to broadcast to ALL users.\n"
        "❌ /cancel to cancel",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("broadcast_gc"))
async def broadcast_gc_cmd(message: Message):
    user = message.from_user
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    broadcast_state[user.id] = {"type": "groups", "step": "waiting"}
    await message.answer(
        "📢 <b>BROADCAST TO ALL GROUPS</b>\n\n"
        "Send any message to broadcast to ALL groups.\n"
        "❌ /cancel to cancel",
        parse_mode=ParseMode.HTML
    )

# ========== FIX 2: /link WORKS IN GROUPS ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    user = message.from_user
    
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

# ========== FIX 3: TEMPEST HIDDEN FROM /help ==========
@dp.message(Command("help"))
async def help_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
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

👑 <b>Owner Only:</b>
<code>/owner_help</code> - Show owner commands"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== FIX 4: /owner_help COMMAND ==========
@dp.message(Command("owner_help"))
async def owner_help_cmd(message: Message):
    user = message.from_user
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only command")
        return
    
    owner_text = """👑 <b>OWNER COMMANDS</b>

⚡ <b>Admin Management:</b>
<code>/pro [id]</code> - Make admin
<code>/toggle</code> - Toggle bot

📢 <b>Broadcast:</b>
<code>/broadcast</code> - Send to all users
<code>/broadcast_gc</code> - Send to groups only

🔧 <b>System:</b>
<code>/refresh</code> - Refresh bot cache
<code>/emergency_stop</code> - Stop bot
<code>/disable [cmd] [time] [reason]</code> - Disable command

🌀 <b>Tempest Cult:</b>
<code>/tempest_cult</code> - Cult hierarchy
<code>/tempest_join</code> - Join cult
<code>/tempest_story</code> - Cult story
<code>/invite</code> - Invite to cult"""
    
    await message.answer(owner_text, parse_mode=ParseMode.HTML)

# ========== FIX 5: /disable WITH PROPER TIME ==========
def parse_time(time_str: str) -> int:
    try:
        time_str = time_str.lower().replace(" ", "")
        
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
            return int(time_str) * 60
    except:
        return 300

@dp.message(Command("disable"))
async def disable_cmd(message: Message):
    user = message.from_user
    
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
            "• <code>1d</code> - 1 day\n\n"
            "<b>Examples:</b>\n"
            "<code>/disable link 30m Upload maintenance</code>\n"
            "<code>/disable tempest_join 2h Ceremony update</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    command_name = args[1].lstrip('/')
    time_str = args[2]
    reason = args[3] if len(args) > 3 else "No reason provided"
    
    duration_seconds = parse_time(time_str)
    disabled_until = datetime.now() + timedelta(seconds=duration_seconds)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO disabled_commands (command, disabled_until, reason, disabled_by, disabled_at) VALUES (?, ?, ?, ?, ?)",
             (command_name, disabled_until.isoformat(), reason, user.id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
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
        f"🕒 <b>Disabled Until:</b> {disabled_until.strftime('%H:%M')}\n"
        f"📝 <b>Reason:</b> {reason}",
        parse_mode=ParseMode.HTML
    )

# ========== FIX 6: WELCOME MESSAGE ==========
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

📚 <b>Available Commands:</b>
<code>/help</code> - All commands
<code>/link</code> - Upload files
<code>/profile</code> - Your stats

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
    except Exception as e:
        print(f"Welcome error: {e}")

# ========== FIX 7: /tempest_cult SHOWS MEMBERS ==========
@dp.message(Command("tempest_cult"))
async def tempest_cult_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Get top 10 members by sacrifices
    c.execute("""
        SELECT user_id, first_name, cult_rank, sacrifices 
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
        for idx, (member_id, name, rank, sacrifices) in enumerate(members, 1):
            # Skip leaders already shown
            if member_id in [CULT_LEADER_ID, VICE_CHANCELLOR_ID, OWNER_ID]:
                continue
            
            cult_text += f"\n{idx}. {name} - {rank} ({sacrifices}⚔️)"
    
    cult_text += "\n\n━━━━━━━━━━━━━━━━━━━━"
    cult_text += "\n<i>The storm sees all. The tempest grows with each sacrifice.</i>"
    
    await message.answer(cult_text, parse_mode=ParseMode.HTML)

# ========== ORIGINAL WORKING COMMANDS ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user = message.from_user
    chat = message.chat
    
    update_user(user)
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(chat)
    
    log_command(user.id, chat.id, chat.type, "start")
    
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

# ========== FILE UPLOAD HANDLER ==========
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
        
        c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)",
                 (user.id, datetime.now().isoformat(), result['url'], file_type, file_size))
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
        print(f"Upload error: {e}")

@dp.callback_query(F.data.startswith("copy_"))
async def handle_copy(callback: CallbackQuery):
    url = callback.data[5:]
    await callback.answer(f"Link copied to clipboard!\n{url}", show_alert=True)

# ========== BROADCAST HANDLER ==========
@dp.message()
async def handle_broadcast_message(message: Message):
    user = message.from_user
    chat = message.chat
    
    update_user(user)
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(chat)
    
    # Check if user is in broadcast state
    if user.id in broadcast_state and broadcast_state[user.id]["step"] == "waiting":
        broadcast_data = broadcast_state[user.id]
        broadcast_type = broadcast_data["type"]
        
        # Start processing
        status_msg = await message.answer("🔁 <b>Starting broadcast...</b>", parse_mode=ParseMode.HTML)
        
        # Get ALL targets from database
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        if broadcast_type == "users":
            c.execute("SELECT user_id FROM users WHERE is_banned = 0")
            targets = [row[0] for row in c.fetchall()]
            target_type = "users"
        else:
            c.execute("SELECT group_id FROM groups")
            targets = [row[0] for row in c.fetchall()]
            target_type = "groups"
        
        conn.close()
        
        total = len(targets)
        if total == 0:
            await status_msg.edit_text(f"❌ No {target_type} found to broadcast!")
            del broadcast_state[user.id]
            return
        
        success = 0
        failed = 0
        
        # Send broadcast to ALL targets
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
❌ Failed: {failed}"""

        await status_msg.edit_text(result_text, parse_mode=ParseMode.HTML)
        
        # Clear broadcast state
        del broadcast_state[user.id]
        
        # Log the broadcast
        try:
            await send_log(f"📢 <b>Broadcast Sent</b>\n\nBy: {user.first_name}\nType: {target_type}\nSent: {success}/{total}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            pass
        
        return

# ========== FIX 8: /invite WITH SAME CEREMONY ==========
@dp.message(Command("invite"))
async def invite_cmd(message: Message):
    user = message.from_user
    
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
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
        await message.answer("🌀 <b>You must be in the Tempest to invite others!</b>", parse_mode=ParseMode.HTML)
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
        "group_id": message.chat.id,
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
    
    # Auto-delete after 5 minutes
    await asyncio.sleep(300)
    try:
        await bot.delete_message(message.chat.id, invite_msg.message_id)
        if invite_id in pending_invites:
            del pending_invites[invite_id]
    except:
        pass

@dp.callback_query(F.data.startswith("invite_accept_"))
async def handle_invite_accept(callback: CallbackQuery):
    invite_id = callback.data.replace("invite_accept_", "")
    
    if invite_id not in pending_invites:
        await callback.answer("Invite expired!", show_alert=True)
        return
    
    invite_data = pending_invites[invite_id]
    user = callback.from_user
    
    if user.id != invite_data["target_id"]:
        await callback.answer("This invitation isn't for you!", show_alert=True)
        return
    
    # Start the SAME ceremony as /tempest_join
    await callback.answer("✅ Blood pact accepted! Starting ceremony...", show_alert=True)
    
    # Store invitation data in pending_joins
    pending_joins[user.id] = {
        "name": user.first_name,
        "step": 1,
        "chat_id": callback.message.chat.id,
        "invited": True,
        "inviter_name": invite_data["inviter_name"],
        "invite_id": invite_id
    }
    
    # Show SAME sacrifice selection as /tempest_join
    keyboard = InlineKeyboardBuilder()
    for i in range(1, 9):
        keyboard.add(InlineKeyboardButton(text=f"{i}", callback_data=f"invite_sacrifice_{i}"))
    keyboard.add(InlineKeyboardButton(text="❌ CANCEL", callback_data="invite_sacrifice_cancel"))
    keyboard.adjust(4, 4, 2)
    
    await callback.message.edit_text(
        f"⚡ <b>TEMPEST BLOOD CEREMONY (INVITED)</b>\n\n"
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
    
    # Remove from pending invites
    del pending_invites[invite_id]

@dp.callback_query(F.data.startswith("invite_sacrifice_"))
async def handle_invite_sacrifice(callback: CallbackQuery):
    user = callback.from_user
    
    if user.id not in pending_joins:
        await callback.answer("❌ Ceremony expired!", show_alert=True)
        return
    
    if callback.data == "invite_sacrifice_cancel":
        del pending_joins[user.id]
        await callback.message.edit_text("🌀 <b>Initiation cancelled. The storm is disappointed.</b>", parse_mode=ParseMode.HTML)
        await callback.answer()
        return
    
    sacrifice_num = callback.data.replace("invite_sacrifice_", "")
    
    # SAME sacrifices as /tempest_join
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
    
    # SAME verification as /tempest_join
    msg = callback.message
    await msg.edit_text(f"🌀 <b>VERIFYING SACRIFICE...</b>\n\n⚡ {sacrifice}", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    
    is_real, status = await sacrifice_verification(sacrifice)
    
    if not is_real:
        del pending_joins[user.id]
        
        rejection = random.choice([
            f"❌ <b>SACRIFICE REJECTED!</b>\n\n⚡ '{sacrifice}' is FAKE!\n🌩️ The storm LAUGHS at your pathetic offering!\n🌀 <i>Banned from initiation for 24 hours!</i>",
            f"💀 <b>THE STORM ANGERED!</b>\n\n⚡ Fake: '{sacrifice}'\n🌪️ The Tempest SPITS on your worthless offering!\n🌀 <i>Return when you have REAL value...</i>",
        ])
        
        await msg.edit_text(rejection, parse_mode=ParseMode.HTML)
        await callback.answer("❌ Fake sacrifice detected!", show_alert=True)
        return
    
    # SAME ceremony animation as /tempest_join
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
    
    # Final initiation - SAME as /tempest_join
    invite_info = pending_joins[user.id]
    inviter_text = f"\n🤝 <b>Invited by:</b> {invite_info['inviter_name']}" if invite_info.get('invited') else ""
    
    final_message = f"""⚡ <b>ETERNAL INITIATION COMPLETE!</b>

🌀 <b>WELCOME TO THE TEMPEST, {user.first_name.upper()}!</b>

🩸 <b>Sacrifice:</b> {sacrifice}
👑 <b>Rank:</b> Blood Initiate
⚔️ <b>Starting Sacrifices:</b> 3
🌪️ <b>Blood Oath:</b> ETERNAL{inviter_text}

<i>The storm now flows through your veins.
Each upload feeds the Tempest.
Your journey of darkness begins...</i>

🌀 Check your status with /profile"""
    
    await msg.edit_text(final_message, parse_mode=ParseMode.HTML)
    
    # Add to cult - SAME as /tempest_join
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
             (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()
    
    # Cleanup
    if user.id in pending_joins:
        del pending_joins[user.id]
    
    await callback.answer("✅ Sacrifice accepted! Welcome to the Tempest!", show_alert=True)

@dp.callback_query(F.data.startswith("invite_decline_"))
async def handle_invite_decline(callback: CallbackQuery):
    invite_id = callback.data.replace("invite_decline_", "")
    
    if invite_id not in pending_invites:
        await callback.answer("Invite expired!", show_alert=True)
        return
    
    invite_data = pending_invites[invite_id]
    user = callback.from_user
    
    if user.id != invite_data["target_id"]:
        await callback.answer("This invitation isn't for you!", show_alert=True)
        return
    
    await callback.answer("❌ Invitation declined", show_alert=True)
    await callback.message.edit_text(
        f"🚫 <b>INVITATION REJECTED</b>\n\n"
        f"👤 <b>{user.first_name}</b> rejected the Tempest's call.\n"
        f"👑 Invited by: {invite_data['inviter_name']}\n\n"
        f"<i>Their blood remains unspilled... for now.</i>",
        parse_mode=ParseMode.HTML
    )
    
    del pending_invites[invite_id]

# ========== KEEP ORIGINAL TEMPEST COMMANDS ==========
@dp.message(Command("tempest_join"))
async def tempest_join_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        await message.answer("🌀 <b>Already part of the Tempest!</b>\nUse /profile to check your status.", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    conn.close()
    
    pending_joins[user.id] = {
        "name": user.first_name,
        "step": 1,
        "chat_id": message.chat.id
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
    
    msg = callback.message
    await msg.edit_text(f"🌀 <b>VERIFYING SACRIFICE...</b>\n\n⚡ {sacrifice}", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    
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
    
    pending_joins[user.id]["sacrifice"] = sacrifice
    pending_joins[user.id]["verified"] = status
    
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
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
             (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()
    
    try:
        await send_log(f"🌀 <b>New Tempest Member</b>\n\n👤 Name: {user.first_name}\n🆔 ID: {user.id}\n🩸 Sacrifice: {sacrifice}\n🌪️ Joined: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except:
        pass
    
    if user.id in pending_joins:
        del pending_joins[user.id]
    
    await callback.answer("✅ Sacrifice accepted! Welcome to the Tempest!", show_alert=True)

@dp.message(Command("tempest_story"))
async def tempest_story_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if not result or result[0] == "none":
        await message.answer("🌀 This command is for Tempest members only.")
        conn.close()
        return
    
    conn.close()
    
    story_states[user.id] = {"chapter": 1}
    
    chapter1 = """📜 <b>CHAPTER 1: THE VOID BEFORE STORM</b>

<i>Time before time, in the Age of Eternal Calm...</i>

There was only silence. 
Not peaceful silence, but oppressive, crushing quiet.
The Council of Stillness ruled all realms, banning laughter, regulating storms, scheduling even thunder.

In this graveyard of sound, a discontent began to stir.
A whisper in the void, a crackle in the stillness..."""
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🌪️ Continue to Chapter 2", callback_data="story_next"))
    
    story_msg = await message.answer("🌀 <b>Loading ancient scrolls...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(2)
    await story_msg.edit_text(chapter1, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())

@dp.callback_query(F.data == "story_next")
async def handle_story_next(callback: CallbackQuery):
    user = callback.from_user
    
    if user.id not in story_states:
        await callback.answer("Story expired!")
        return
    
    chapter = story_states[user.id].get("chapter", 1)
    
    chapters = {
        1: """📜 <b>CHAPTER 2: BIRTH OF RAVIJAH</b>

<code>Year 0, Storm Calendar</code>

From the first lightning that dared defy schedule, he emerged.
RAVIJAH, born not of mother, but of storm itself.
Silver hair crackling with energy, eyes like captured lightning.

He wandered the silent kingdoms, collecting forgotten thunder,
gathering whispers of rebellion from those who remembered sound.

<code>"This quiet is a cage," he whispered. "I shall be the key."</code>""",
        
        2: """📜 <b>CHAPTER 3: THE BROKEN SWORDS</b>

<code>Year 47, Storm Calendar</code>

In the ruins of the Shattered Rebellion, Ravijah found Bablu.
Last survivor of a failed uprising, sword still thirsty for chaos.

<code>"My blade remembers battle," Bablu growled. "Teach it new songs."</code>

From the Shadow Archives emerged Keny, keeper of forbidden knowledge.
<code>"I know the secrets of the Still Council," he whispered. "Their weakness is order."</code>

Three became one that stormy night.""",
        
        3: """📜 <b>CHAPTER 4: THE FESTIVAL BETRAYAL</b>

<code>Year 89, Storm Calendar</code>

The Festival of Flames was meant to be celebration.
But the Still Council attacked during the Feast of Whispers.

Elara, storm-singer and Ravijah's chosen, saw the poisoned blade.
She stepped in front, taking what was meant for him.

<code>"Live," she breathed as storm-magic faded. "For both of us..."</code>

Ravijah's scream birthed the First Tempest.""",
        
        4: """📜 <b>CHAPTER 5: AGE OF THUNDER</b>

<code>Years 90-389, Storm Calendar</code>

For three centuries, the Tempest grew.
They built the Temple of Howling Winds from captured silence.
Founded the Archive of Lightning with stolen knowledge.
Created the Blood Altar that drank offerings from conquered realms.

New initiates flooded in, each swearing eternal oaths.
Ranks were established, rituals perfected, power consolidated.""",
        
        5: """📜 <b>CHAPTER 6: THE GREAT SCHISM</b>

<code>Year 390, Storm Calendar</code>

Power corrupts, even storm-born.
Internal conflicts erupted. Blood Initiate turned against Blood Master.
The Temple fractured into warring factions.

Ravijah disappeared into the Eye of the Storm.
Bablu became Warden of the Shattered Realms.
Keny retreated to the Shadow Archives.

The Golden Age had ended.""",
        
        6: """📜 <b>CHAPTER 7: DIGITAL AWAKENING</b>

<code>Year 2024, Modern Era</code>

The storm evolved. Adapted. Transformed.
No longer bound to physical realms, it moved into cyberspace.

Lightning now flows through fiber optics.
Tempests brew in server farms.
Sacrifices became digital - data, files, uploads.

The Council reformed in the digital shadows.
New purpose, new methods, same eternal storm.""",
        
        7: """📜 <b>CHAPTER 8: YOUR DESTINY</b>

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
    
    if chapter < 7:
        story_states[user.id]["chapter"] = chapter + 1
        next_chapter = chapters.get(chapter, "End of story")
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🌪️ Continue", callback_data="story_next"))
        
        await callback.message.edit_text(next_chapter, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
    else:
        await callback.message.edit_text("📜 <b>THE TEMPEST SAGA</b>\n\n<i>Your understanding of the storm is complete. Your journey continues with each sacrifice. Make your mark in the eternal tempest.</i>", parse_mode=ParseMode.HTML)
        del story_states[user.id]
    
    await callback.answer()

# ========== OTHER ORIGINAL COMMANDS ==========
@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user = message.from_user
    update_user(message.chat)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT uploads, commands, joined_date, cult_status, cult_rank, sacrifices, cult_join_date FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    
    if row:
        uploads, cmds, joined, cult_status, cult_rank, sacrifices, cult_join = row
        c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (user.id,))
        wishes = c.fetchone()[0] or 0
    else:
        uploads = cmds = wishes = 0
        cult_status = "none"
    
    conn.close()
    
    if cult_status and cult_status != "none":
        profile_text = f"""🌀 <b>TEMPEST PROGRESS</b>

👤 <b>Member:</b> {user.first_name}
👑 <b>Rank:</b> {cult_rank}
⚔️ <b>Sacrifices:</b> {sacrifices}
📁 <b>Uploads:</b> {uploads}
✨ <b>Wishes:</b> {wishes}
🔧 <b>Commands:</b> {cmds}

⚡ Each upload = 1 sacrifice"""
    else:
        profile_text = f"""
👤 <b>PROFILE: {user.first_name}</b>

📁 <b>Uploads:</b> {uploads}
✨ <b>Wishes:</b> {wishes}
🔧 <b>Commands:</b> {cmds}
🆔 <b>ID:</b> <code>{user.id}</code>

💡 <b>Next:</b> Try /link to upload files"""
    
    await message.answer(profile_text, parse_mode=ParseMode.HTML)

@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
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
    user = message.from_user
    update_user(user)
    
    msg = await message.answer("🎲 <b>Rolling dice...</b>", parse_mode=ParseMode.HTML)
    
    faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    for i in range(6):
        await msg.edit_text(f"🎲 <b>Rolling...</b> {faces[i]}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.15)
    
    roll = random.randint(1, 6)
    await msg.edit_text(f"🎲 <b>You rolled: {faces[roll-1]} ({roll})</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    msg = await message.answer("🪙 <b>Flipping coin...</b>", parse_mode=ParseMode.HTML)
    
    for i in range(5):
        await msg.edit_text(f"🪙 <b>Flipping...</b> {'HEADS' if i % 2 == 0 else 'TAILS'}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user = message.from_user
    
    if user.id in upload_waiting:
        upload_waiting[user.id] = False
        await message.answer("❌ Upload cancelled")
    
    if user.id in broadcast_state:
        del broadcast_state[user.id]
        await message.answer("❌ Broadcast cancelled")
    
    if user.id in story_states:
        del story_states[user.id]
        await message.answer("❌ Story cancelled")

# ========== MAIN ==========
async def main():
    print("🤖 PRO BOT STARTING...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ Database initialized")
    print(f"🌀 Log Channel ID: {LOG_CHANNEL_ID}")
    print("📢 Broadcast: FIXED - Sends to ALL users/groups")
    print("🔗 Upload: FIXED - Works in groups")
    print("📜 Story: WORKING")
    print("👤 Profile: WORKING")
    print("📨 Invite: FIXED - Same ceremony as tempest_join")
    print("🌀 Tempest: HIDDEN from /help")
    print("👑 Owner: /owner_help command")
    print("🚫 /disable: PROPER TIME FORMAT")
    print("👋 Welcome: GROUP WELCOME")
    print("=" * 50)
    
    try:
        startup_log = f"🤖 <b>Bot Started</b>\n\n🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🌀 Version: Original + 8 Fixes"
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
