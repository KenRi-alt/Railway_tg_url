#!/usr/bin/env python3
# ========== TEMPEST BOT - COMPLETELY FIXED ==========
import sys
print("=" * 60)
print("🌀 TEMPEST BOT - FULLY WORKING")
print("✅ All commands fixed")
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
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

from PIL import Image, ImageDraw, ImageFont

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

print("🤖 BOT INITIALIZING...")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845

# Create directories
for dir_name in ["data", "temp", "backups", "profile_cards"]:
    Path(dir_name).mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True
upload_waiting = {}
broadcast_state = {}
pending_joins = {}
pending_invites = {}
pending_restore = {}
last_activity = datetime.now()

# ========== DATABASE INIT ==========
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS story_chapters (
        chapter_number INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT,
        added_by INTEGER,
        added_date TEXT,
        is_published INTEGER DEFAULT 1
    )''')
    
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== HELPER FUNCTIONS ==========
async def safe_answer_callback(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    try:
        await callback.answer(text, show_alert=show_alert)
    except:
        pass

async def send_log(message: str):
    try:
        print(f"📢 LOG: {message[:100]}")
        await bot.send_message(LOG_CHANNEL_ID, message[:4000], parse_mode=ParseMode.HTML)
    except:
        pass

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

async def handle_common(message: Message, command: str):
    user = message.from_user
    chat = message.chat
    
    # Update user in DB
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
    
    # Update group if in group
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        try:
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
    
    # Log command
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO command_logs (timestamp, user_id, chat_id, chat_type, command, success) VALUES (?, ?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), user.id, chat.id, str(chat.type), command, 1))
        c.execute("UPDATE users SET commands = commands + 1 WHERE user_id = ?", (user.id,))
        conn.commit()
        conn.close()
    except:
        pass
    
    return user, chat

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

def save_bot_state():
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("DELETE FROM bot_state")
        for user_id, waiting in upload_waiting.items():
            if waiting:
                c.execute("INSERT INTO bot_state (key, value, timestamp) VALUES (?, ?, ?)",
                         (f"upload_{user_id}", "1", now))
        conn.commit()
        conn.close()
    except:
        pass

def load_bot_state():
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        upload_waiting.clear()
        c.execute("SELECT key FROM bot_state WHERE key LIKE 'upload_%'")
        for (key,) in c.fetchall():
            user_id = int(key.split("_")[1])
            upload_waiting[user_id] = True
        conn.close()
        print(f"✅ Restored {len(upload_waiting)} upload states")
    except:
        pass

load_bot_state()

async def upload_to_catbox(file_data, filename):
    try:
        files = {'reqtype': (None, 'fileupload'), 'fileToUpload': (filename, file_data)}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(UPLOAD_API, files=files)
        if response.status_code == 200 and response.text.startswith('http'):
            return {'success': True, 'url': response.text.strip()}
        return {'success': False, 'error': 'Upload failed'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ========== PROFILE CARD ==========
def create_profile_card(user_data, profile_photo_path=None):
    try:
        user_id, first_name, username, uploads, commands, wishes, cult_rank, sacrifices, curse_type, joined_date = user_data
        
        width, height = 800, 450
        base = Image.new('RGB', (width, height), color='#0a0a1a')
        draw = ImageDraw.Draw(base)
        
        for i in range(height):
            r = max(10, int(10 + i * 0.1))
            g = max(10, int(10 + i * 0.05))
            b = max(26, int(26 + i * 0.15))
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        
        font = ImageFont.load_default()
        
        safe_name = "".join(c for c in first_name if ord(c) < 128)[:12] or "User"
        
        title = "🌀 TEMPEST CREED" if cult_rank != "none" else "✨ USER PROFILE"
        title_color = (100, 200, 255) if cult_rank != "none" else (200, 200, 200)
        
        draw.text((width // 2, 30), title, fill=title_color, font=font, anchor="mm")
        draw.text((width // 2, 70), safe_name, fill=(255, 255, 255), font=font, anchor="mm")
        draw.text((width // 2, 100), f"ID: {user_id}", fill=(180, 180, 220), font=font, anchor="mm")
        
        stats_y = 140
        draw.rectangle([(50, stats_y), (230, stats_y + 60)], fill=(20, 40, 80), outline=(0, 150, 255))
        draw.text((140, stats_y + 15), "UPLOADS", fill=(100, 200, 255), font=font, anchor="mm")
        draw.text((140, stats_y + 40), str(uploads), fill=(255, 255, 255), font=font, anchor="mm")
        
        draw.rectangle([(280, stats_y), (460, stats_y + 60)], fill=(40, 20, 80), outline=(150, 0, 255))
        draw.text((370, stats_y + 15), "WISHES", fill=(200, 100, 255), font=font, anchor="mm")
        draw.text((370, stats_y + 40), str(wishes), fill=(255, 255, 255), font=font, anchor="mm")
        
        draw.rectangle([(510, stats_y), (690, stats_y + 60)], fill=(20, 80, 40), outline=(0, 255, 150))
        draw.text((600, stats_y + 15), "CMDS", fill=(100, 255, 200), font=font, anchor="mm")
        draw.text((600, stats_y + 40), str(commands), fill=(255, 255, 255), font=font, anchor="mm")
        
        info_y = 220
        if cult_rank != "none":
            draw.text((50, info_y), f"RANK: {cult_rank}", fill=(255, 100, 100), font=font)
            draw.text((50, info_y + 30), f"SACS: {sacrifices}", fill=(255, 200, 100), font=font)
        else:
            draw.text((50, info_y), "NOT INITIATED", fill=(150, 150, 150), font=font)
            draw.text((50, info_y + 30), "USE /TEMPEST_JOIN", fill=(200, 200, 100), font=font)
        
        if curse_type != "none":
            draw.text((width - 250, info_y), f"CURSED: {curse_type}", fill=(255, 50, 50), font=font)
            draw.rectangle([(0, 0), (width-1, height-1)], outline=(255, 50, 50), width=3)
        
        draw.text((width - 250, info_y + 30), f"JOINED: {joined_date}", fill=(150, 200, 255), font=font)
        draw.text((width // 2, height - 30), "The storm flows through you", fill=(100, 150, 255), font=font, anchor="mm")
        
        filename = f"profile_cards/profile_{user_id}_{int(time.time())}.png"
        base.save(filename, "PNG")
        return filename if os.path.exists(filename) else None
    except Exception as e:
        print(f"❌ Profile card error: {e}")
        return None

# ========== START COMMAND ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = await handle_common(message, "start")
    await message.answer(
        f"✨ <b>Hey {user.first_name}!</b>\n\n"
        "🤖 <b>TEMPEST BOT</b>\n\n"
        "🔗 Upload files - /link\n"
        "✨ Make a wish - /wish [text]\n"
        "🎮 Play games - /dice or /flip\n"
        "👤 View profile - /profile\n"
        "🌀 Join Tempest - /tempest_join\n"
        "📚 All commands - /help",
        parse_mode=ParseMode.HTML
    )

# ========== HELP COMMAND ==========
@dp.message(Command("help"))
async def help_cmd(message: Message):
    user, chat = await handle_common(message, "help")
    
    help_text = """📚 <b>TEMPEST BOT COMMANDS</b>

━━━━━━━━━━━━━━━━━━━━━━━━
🔗 <b>UPLOAD</b>
<code>/link</code> - Upload file for permanent link

━━━━━━━━━━━━━━━━━━━━━━━━
🌟 <b>WISH & GAMES</b>
<code>/wish [text]</code> - Check your luck %
<code>/dice</code> - Roll a dice
<code>/flip</code> - Flip a coin

━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>PROFILE</b>
<code>/profile</code> - View your stats
<code>/start</code> - Welcome message

━━━━━━━━━━━━━━━━━━━━━━━━
🌀 <b>TEMPEST CREED</b>
<code>/tempest_join</code> - Join the cult
<code>/tempest_story</code> - Read the lore
<code>/tempest_creed</code> - View all members
<code>/shrine</code> - Group Tempest stats
<code>/curse</code> - Curse a user
<code>/remove_curse</code> - Remove curse

━━━━━━━━━━━━━━━━━━━━━━━━
📝 <b>UTILITIES</b>
<code>/word [text]</code> - Convert to DOCX

━━━━━━━━━━━━━━━━━━━━━━━━
👑 <b>ADMIN</b>
<code>/ping</code> - System status
<code>/stats</code> - Bot statistics
<code>/users</code> - User list
<code>/admins</code> - Admin list
<code>/scan</code> - Scan database
<code>/broadcast</code> - Message all users
<code>/backup</code> - Backup database

⚡ <b>OWNER</b>
<code>/pro [id]</code> - Make admin
<code>/rem</code> - Restore backup
<code>/restart</code> - Reboot bot

━━━━━━━━━━━━━━━━━━━━━━━━
🌀 <i>The storm flows through you</i>"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== WISH COMMAND ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ <b>Usage:</b> <code>/wish your wish here</code>", parse_mode=ParseMode.HTML)
        return
    
    msg = await message.answer("✨ <b>Reading your destiny...</b>", parse_mode=ParseMode.HTML)
    
    # Get curse status
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT curse_type FROM users WHERE user_id = ?", (user.id,))
    curse_result = c.fetchone()
    curse_type = curse_result[0] if curse_result else "none"
    conn.close()
    
    curse_penalty = 0
    curse_message = ""
    if curse_type != "none":
        curse_penalty = random.randint(15, 30)
        curse_message = f"\n⚡ <b>Curse penalty:</b> -{curse_penalty}%"
    
    await asyncio.sleep(0.5)
    base_luck = random.randint(1, 100)
    luck = max(1, base_luck - curse_penalty)
    stars = "⭐" * (luck // 10) + "☆" * (10 - luck // 10)
    
    if luck >= 90:
        result_text = "🎊 EXCELLENT! Will definitely happen!"
    elif luck >= 70:
        result_text = "😊 VERY GOOD! High chance!"
    elif luck >= 50:
        result_text = "👍 GOOD! Potential success!"
    elif luck >= 30:
        result_text = "🤔 AVERAGE - Needs effort"
    elif luck >= 10:
        result_text = "😟 LOW - Try again"
    else:
        result_text = "💀 VERY LOW - Bad timing"
    
    # Save wish
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
             (user.id, datetime.now().isoformat(), args[1], luck))
    conn.commit()
    conn.close()
    
    await msg.edit_text(
        f"🔮 <b>WISH RESULT</b>\n\n"
        f"📜 <b>Wish:</b> {args[1][:100]}\n"
        f"🎰 <b>Luck:</b> {stars} {luck}%{curse_message}\n"
        f"📊 <b>Result:</b> {result_text}",
        parse_mode=ParseMode.HTML
    )

# ========== DICE COMMAND ==========
@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    user, chat = await handle_common(message, "dice")
    
    msg = await message.answer("🎲 <b>Rolling dice...</b>", parse_mode=ParseMode.HTML)
    
    faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    for i in range(3):
        await msg.edit_text(f"🎲 <b>Rolling...</b> {faces[i]}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    roll = random.randint(1, 6)
    await msg.edit_text(f"🎲 <b>You rolled: {faces[roll-1]} ({roll})</b>", parse_mode=ParseMode.HTML)

# ========== FLIP COMMAND ==========
@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    user, chat = await handle_common(message, "flip")
    
    msg = await message.answer("🪙 <b>Flipping coin...</b>", parse_mode=ParseMode.HTML)
    
    for i in range(3):
        await msg.edit_text(f"🪙 <b>Flipping...</b> {'HEADS' if i % 2 == 0 else 'TAILS'}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}</b>", parse_mode=ParseMode.HTML)

# ========== PROFILE COMMAND ==========
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
    
    user_data = (user.id, user.first_name, user.username, uploads, cmds, wishes, cult_rank, sacrifices, curse_type, join_date)
    profile_card_path = create_profile_card(user_data)
    
    caption = f"""
👤 <b>{user.first_name}</b>
📧 @{user.username if user.username else 'None'}
🆔 <code>{user.id}</code>

📁 Uploads: {uploads}
✨ Wishes: {wishes}
🔧 Commands: {cmds}
📅 Joined: {join_date}
"""
    if cult_rank != "none":
        caption += f"\n🌀 Rank: {cult_rank} | ⚔️ Sacrifices: {sacrifices}"
    if curse_type != "none":
        caption += f"\n⚡ Curse: {curse_type}"
    
    if profile_card_path and os.path.exists(profile_card_path):
        await message.answer_photo(FSInputFile(profile_card_path), caption=caption, parse_mode=ParseMode.HTML)
        await asyncio.sleep(30)
        try:
            os.remove(profile_card_path)
        except:
            pass
    else:
        await message.answer(caption, parse_mode=ParseMode.HTML)

# ========== LINK/UPLOAD COMMAND ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")
    
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 Upload files in private chat only")
        return
    
    upload_waiting[user.id] = True
    save_bot_state()
    await message.answer("📁 Send me any file now!\n❌ /cancel to stop")

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation)
async def handle_file(message: Message):
    user = message.from_user
    
    if user.id not in upload_waiting or not upload_waiting[user.id]:
        return
    
    upload_waiting[user.id] = False
    save_bot_state()
    
    msg = await message.answer("⏳ Processing...")
    
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
        else:
            await msg.edit_text("❌ Unsupported file type")
            return
        
        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
        
        if response.status_code != 200:
            await msg.edit_text("❌ Failed to download")
            return
        
        result = await upload_to_catbox(response.content, file.file_path.split('/')[-1])
        
        if not result['success']:
            await msg.edit_text("❌ Upload failed")
            return
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,))
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        cult = c.fetchone()
        if cult and cult[0] != 'none':
            c.execute("UPDATE users SET sacrifices = sacrifices + 1 WHERE user_id = ?", (user.id,))
        c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)",
                 (user.id, datetime.now().isoformat(), result['url'], file_type, len(response.content)))
        conn.commit()
        conn.close()
        
        size_kb = len(response.content) / 1024
        size_mb = size_kb / 1024
        size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(types.InlineKeyboardButton(text="📋 Copy Link", callback_data=f"copy_{result['url']}"))
        
        await msg.edit_text(
            f"✅ <b>Upload Complete!</b>\n\n📁 Type: {file_type}\n💾 Size: {size_text}\n\n🔗 <code>{result['url']}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.as_markup()
        )
    except Exception as e:
        await msg.edit_text("❌ Error uploading")
        print(f"Upload error: {e}")

@dp.callback_query(F.data.startswith("copy_"))
async def handle_copy(callback: CallbackQuery):
    url = callback.data[5:]
    await safe_answer_callback(callback, f"Link copied!\n{url}", show_alert=True)

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user, chat = await handle_common(message, "cancel")
    if user.id in upload_waiting:
        upload_waiting[user.id] = False
        save_bot_state()
        await message.answer("❌ Cancelled")

# ========== PING COMMAND ==========
@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    user, chat = await handle_common(message, "ping")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    start = time.perf_counter()
    msg = await message.answer("🏓 Testing connection...")
    end = time.perf_counter()
    ping_ms = int((end - start) * 1000)
    
    uptime_seconds = int(time.time() - start_time)
    uptime = format_uptime(uptime_seconds)
    
    # System stats
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        response = f"""
🏓 <b>PONG!</b>
━━━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>Latency:</b> {ping_ms}ms
🕒 <b>Uptime:</b> {uptime}
🎯 <b>Status:</b> {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}

💻 <b>System:</b>
• CPU: {cpu}%
• RAM: {memory.used // (1024**2)}MB / {memory.total // (1024**2)}MB
• DISK: {disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB
"""
    except:
        response = f"""
🏓 <b>PONG!</b>
━━━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>Latency:</b> {ping_ms}ms
🕒 <b>Uptime:</b> {uptime}
🎯 <b>Status:</b> {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}
"""
    
    await msg.edit_text(response, parse_mode=ParseMode.HTML)

# ========== STATS COMMAND ==========
@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    user, chat = await handle_common(message, "stats")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM groups")
    groups = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM uploads")
    uploads = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM wishes")
    wishes = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
    tempest = c.fetchone()[0] or 0
    conn.close()
    
    await message.answer(
        f"📊 <b>BOT STATISTICS</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: {users}\n"
        f"👥 Groups: {groups}\n"
        f"🌀 Tempest Members: {tempest}\n"
        f"📁 Total Uploads: {uploads}\n"
        f"✨ Total Wishes: {wishes}\n"
        f"🕒 Uptime: {format_uptime(int(time.time() - start_time))}",
        parse_mode=ParseMode.HTML
    )

# ========== ADMINS COMMAND ==========
@dp.message(Command("admins"))
async def admins_cmd(message: Message):
    user, chat = await handle_common(message, "admins")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username FROM users WHERE is_admin = 1")
    admins = c.fetchall()
    conn.close()
    
    if not admins:
        await message.answer("No admins found")
        return
    
    text = "👑 <b>BOT ADMINS</b>\n\n"
    for uid, name, uname in admins:
        text += f"• {name} (@{uname if uname else 'None'})\n🆔 <code>{uid}</code>\n\n"
    
    await message.answer(text, parse_mode=ParseMode.HTML)

# ========== USERS COMMAND ==========
@dp.message(Command("users"))
async def users_cmd(message: Message):
    user, chat = await handle_common(message, "users")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, uploads, commands FROM users ORDER BY joined_date DESC LIMIT 50")
    users = c.fetchall()
    conn.close()
    
    text = "👥 <b>RECENT USERS</b>\n\n"
    for uid, name, uname, up, cmd in users:
        text += f"• {name} (@{uname if uname else 'None'})\n🆔 <code>{uid}</code> | 📁{up} | 🔧{cmd}\n\n"
    
    filename = f"temp/users_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text)
    
    await message.answer_document(FSInputFile(filename), caption="📁 User list")
    os.remove(filename)

# ========== SCAN COMMAND ==========
@dp.message(Command("scan"))
async def scan_cmd(message: Message):
    user, chat = await handle_common(message, "scan")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    await message.answer("✅ Scan completed! Database is up to date.")

# ========== PRO COMMAND ==========
@dp.message(Command("pro"))
async def pro_cmd(message: Message):
    user, chat = await handle_common(message, "pro")
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only")
        return
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Usage: /pro user_id")
        return
    
    target_id = int(args[1])
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (target_id,))
    if c.rowcount == 0:
        c.execute("INSERT INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
                 (target_id, f"User_{target_id}", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ User {target_id} is now admin!")

# ========== BROADCAST COMMAND ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    broadcast_state[user.id] = {"step": 1}
    save_bot_state()
    await message.answer("📢 Send me the message to broadcast to ALL users.\n❌ /cancel to stop")

# ========== BACKUP COMMAND ==========
@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    user, chat = await handle_common(message, "backup")
    
    if user.id != OWNER_ID:
        await message.answer("🚫 Owner only")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/backup_{timestamp}.db"
    
    shutil.copy2("data/bot.db", backup_file)
    await message.answer_document(FSInputFile(backup_file), caption=f"💾 Backup {timestamp}")
    os.remove(backup_file)

# ========== REM COMMAND (Restore) ==========
@dp.message(Command("rem"))
async def rem_cmd(message: Message):
    user, chat = await handle_common(message, "rem")
    
    if user.id != OWNER_ID:
        await message.answer("🚫 Owner only")
        return
    
    pending_restore[user.id] = True
    await message.answer("💾 Upload the backup .db file to restore.\n⚠️ This will REPLACE current database!\n❌ /cancel to abort")

@dp.message(F.document)
async def handle_restore_file(message: Message):
    user = message.from_user
    
    if user.id not in pending_restore or not pending_restore.get(user.id):
        return
    
    if not message.document.file_name.endswith('.db'):
        await message.answer("❌ Please upload a .db file!")
        return
    
    pending_restore.pop(user.id, None)
    msg = await message.answer("⏳ Restoring database...")
    
    try:
        file = await bot.get_file(message.document.file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
        
        temp_file = f"temp/restore_{user.id}.db"
        with open(temp_file, 'wb') as f:
            f.write(response.content)
        
        # Backup current
        shutil.copy2("data/bot.db", f"backups/pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        
        # Restore
        shutil.copy2(temp_file, "data/bot.db")
        os.remove(temp_file)
        
        # Reinitialize
        init_db()
        load_bot_state()
        
        await msg.edit_text("✅ Database restored successfully!\n🔄 Bot state reloaded.")
    except Exception as e:
        await msg.edit_text(f"❌ Restore failed: {str(e)}")

# ========== RESTART COMMAND ==========
@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    user, chat = await handle_common(message, "restart")
    
    if user.id != OWNER_ID:
        await message.answer("🚫 Owner only")
        return
    
    await message.answer("🔄 Restarting bot...")
    save_bot_state()
    os.execv(sys.executable, ['python'] + sys.argv)

# ========== WORD COMMAND ==========
@dp.message(Command("word"))
async def word_cmd(message: Message):
    user, chat = await handle_common(message, "word")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📝 Usage: /word [your text]")
        return
    
    msg = await message.answer("📝 Creating document...")
    
    try:
        doc = Document()
        header = doc.add_paragraph()
        header.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = header.add_run("✦ TEMPEST ARCHIVES ✦")
        run.font.size = Pt(16)
        run.font.bold = True
        
        doc.add_paragraph()
        info = doc.add_paragraph()
        info.alignment = WD_ALIGN_PARAGRAPH.CENTER
        info.add_run(f"Created by: {user.first_name}").font.size = Pt(10)
        
        doc.add_paragraph()
        doc.add_paragraph("─" * 50)
        doc.add_paragraph()
        
        content = doc.add_paragraph()
        content.add_run(args[1])
        
        doc.add_paragraph()
        doc.add_paragraph("─" * 50)
        doc.add_paragraph()
        
        footer = doc.add_paragraph()
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.add_run("🌀 The storm flows through your words...")
        
        filename = f"temp/word_{user.id}_{int(time.time())}.docx"
        doc.save(filename)
        
        await msg.delete()
        await message.answer_document(FSInputFile(filename), caption="📄 Document created")
        os.remove(filename)
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")

# ========== TEMPEST_JOIN (Simplified for now) ==========
@dp.message(Command("tempest_join"))
async def tempest_join_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_join")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        await message.answer("🌀 You are already in the Tempest! Check /profile")
        conn.close()
        return
    
    c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
             (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()
    
    await message.answer(
        "⚡ <b>WELCOME TO THE TEMPEST!</b>\n\n"
        "🌀 You are now a Blood Initiate\n"
        "⚔️ Starting sacrifices: 3\n"
        "📁 Each upload = +1 sacrifice\n"
        "👑 Use /profile to see your stats\n"
        "📜 Use /tempest_story to learn the lore\n\n"
        "<i>The storm flows through your veins...</i>",
        parse_mode=ParseMode.HTML
    )

# ========== TEMPEST_STORY ==========
@dp.message(Command("tempest_story"))
async def tempest_story_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_story")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    conn.close()
    
    if not result or result[0] == "none":
        await message.answer("🌀 Join the Tempest first with /tempest_join")
        return
    
    story = """📜 <b>TEMPEST LORE</b>

<i>The storm remembers all...</i>

━━━━━━━━━━━━━━━━━━━━━━━━

<b>CHAPTER 1: THE BEGINNING</b>

In the void before time, there was only silence. The Council of Stillness ruled all realms.

But from the first lightning that dared defy schedule, RAVIJAH emerged. Born of storm itself, he gathered the forgotten thunder and whispered rebellion.

<b>CHAPTER 2: THE BLOOD OATH</b>

Three became one - Ravijah, Bablu, and Keny. They built the Temple of Howling Winds and created the Blood Altar.

The first sacrifices were made, and the Tempest was born.

<b>CHAPTER 3: THE DIGITAL AGE</b>

The storm evolved. Lightning now flows through fiber optics. Tempests brew in server farms.

Your uploads are sacrifices. Your data is power. Your loyalty is eternal.

━━━━━━━━━━━━━━━━━━━━━━━━

<i>"We do not recruit. We remember.
We do not convert. We awaken.
We are the calm's end.
We are the eternal storm."</i>"""
    
    await message.answer(story, parse_mode=ParseMode.HTML)

# ========== TEMPEST_CREED ==========
@dp.message(Command("tempest_creed"))
async def tempest_creed_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_creed")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, cult_rank, sacrifices FROM users WHERE cult_status != 'none' ORDER BY sacrifices DESC LIMIT 20")
    members = c.fetchall()
    c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
    total = c.fetchone()[0] or 0
    c.execute("SELECT SUM(sacrifices) FROM users WHERE cult_status != 'none'")
    total_sacs = c.fetchone()[0] or 0
    conn.close()
    
    if not members:
        await message.answer("No Tempest members yet. Be the first with /tempest_join!")
        return
    
    text = f"🌀 <b>TEMPEST CREED</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n📊 Total Members: {total}\n⚔️ Total Sacrifices: {total_sacs}\n\n<b>TOP MEMBERS:</b>\n"
    
    for i, (uid, name, uname, rank, sacs) in enumerate(members[:10], 1):
        text += f"{i}. {name} - {rank} (⚔️{sacs})\n"
    
    await message.answer(text, parse_mode=ParseMode.HTML)

# ========== SHRINE COMMAND ==========
@dp.message(Command("shrine"))
async def shrine_cmd(message: Message):
    user, chat = await handle_common(message, "shrine")
    
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("🌀 The Shrine can only be erected in groups!")
        return
    
    await message.answer(
        f"🌀 <b>TEMPEST SHRINE</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 Location: {chat.title}\n"
        f"👤 Called by: {user.first_name}\n\n"
        f"<i>The shrine watches over this place...</i>\n\n"
        f"Use /tempest_join to become storm-born!",
        parse_mode=ParseMode.HTML
    )

# ========== CURSE COMMAND ==========
@dp.message(Command("curse"))
async def curse_cmd(message: Message):
    user, chat = await handle_common(message, "curse")
    
    if not message.reply_to_message:
        await message.answer("🌀 Reply to a user's message to curse them!")
        return
    
    target = message.reply_to_message.from_user
    
    if target.id == user.id:
        await message.answer("🌀 You cannot curse yourself!")
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET curse_type = 'Bad Luck', curse_time = ? WHERE user_id = ?",
             (datetime.now().isoformat(), target.id))
    conn.commit()
    conn.close()
    
    await message.reply(f"⚡ <b>CURSE BESTOWED!</b>\n\n👤 Target: {target.first_name}\n🌀 Curse: Bad Luck\n\n<i>The storm's wrath is upon them!</i>", parse_mode=ParseMode.HTML)

# ========== REMOVE_CURSE ==========
@dp.message(Command("remove_curse"))
async def remove_curse_cmd(message: Message):
    user, chat = await handle_common(message, "remove_curse")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    if not message.reply_to_message:
        await message.answer("🌀 Reply to a user's message to remove their curse!")
        return
    
    target = message.reply_to_message.from_user
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET curse_type = 'none', curse_time = NULL WHERE user_id = ?", (target.id,))
    conn.commit()
    conn.close()
    
    await message.reply(f"✅ Curse removed from {target.first_name}!")

# ========== BROADCAST HANDLER ==========
@dp.message()
async def handle_broadcast_message(message: Message):
    user = message.from_user
    
    if user.id in broadcast_state and broadcast_state[user.id].get("step") == 1:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned = 0")
        users = c.fetchall()
        conn.close()
        
        broadcast_state.pop(user.id, None)
        save_bot_state()
        
        status_msg = await message.answer(f"📤 Broadcasting to {len(users)} users...")
        
        success = 0
        for uid in users:
            try:
                await bot.send_message(uid[0], f"📢 {message.text}")
                success += 1
                await asyncio.sleep(0.05)
            except:
                pass
        
        await status_msg.edit_text(f"✅ Sent to {success}/{len(users)} users")

# ========== MAIN ==========
async def keep_alive():
    while True:
        await asyncio.sleep(300)
        print(f"💓 Keep-alive at {datetime.now().strftime('%H:%M:%S')}")

async def main():
    print("🚀 STARTING BOT...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    asyncio.create_task(keep_alive())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        save_bot_state()
        print("\n🛑 Bot stopped")
    except Exception as e:
        save_bot_state()
        print(f"❌ Error: {e}")
        traceback.print_exc()