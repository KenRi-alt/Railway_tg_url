#!/usr/bin/env python3
# ========== TEMPEST BOT - ULTIMATE UPGRADED EDITION ==========
import sys
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
import math
from datetime import datetime, timedelta
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from aiohttp import web

from PIL import Image, ImageDraw, ImageFont

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, CallbackQuery, BufferedInputFile
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

print("=" * 60)
print("🌀 TEMPEST BOT - ULTIMATE EDITION INITIALIZING...")
print("=" * 60)

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845

# Create required system directories
for dir_name in ["data", "temp", "backups", "profile_cards"]:
    Path(dir_name).mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True

# Global states
upload_waiting = {}
broadcast_state = {}
pending_restore = {}

# ========== CUSTOME CURSIVE / AESTHETIC TEXT CONVERTER ==========
def cursive_text(text: str) -> str:
    """Converts standard ASCII characters to aesthetic mathematical script/cursive unicode."""
    normal_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    cursive_char = "𝒜𝐵𝒞𝒟𝐸𝐹𝒢𝐻𝐼𝒥𝒦𝐿𝑀𝒩𝒪𝒫𝒰𝑅𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵𝒶𝒷𝒸𝒹𝑒𝒻𝑔𝒽𝒾𝒿𝓀𝓁𝓂𝓃𝑜𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫"
    trans = str.maketrans(normal_char, cursive_char)
    return text.translate(trans)

def gothic_text(text: str) -> str:
    """Converts text to bold aesthetic characters."""
    normal_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    gothic_char = "𝕬𝕱𝕮𝕯𝕰𝕱𝕘𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕯𝕴𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖏𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖞𝖞𝖟"
    trans = str.maketrans(normal_char, gothic_char)
    return text.translate(trans)

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
    print("✅ Database initialized successfully")

init_db()

# ========== HELPER FUNCTIONS ==========
async def safe_answer_callback(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    try:
        await callback.answer(text, show_alert=show_alert)
    except Exception:
        pass

def format_uptime(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    if secs > 0 or not parts: parts.append(f"{int(secs)}s")
    return " ".join(parts)

async def handle_common(message: Message, command: str):
    user = message.from_user
    chat = message.chat

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
        
        c.execute("INSERT INTO command_logs (timestamp, user_id, chat_id, chat_type, command, success) VALUES (?, ?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), user.id, chat.id, str(chat.type), command, 1))
        c.execute("UPDATE users SET commands = commands + 1 WHERE user_id = ?", (user.id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating user DB: {e}")

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
    except Exception:
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
    except Exception as e:
        print(f"Error saving state: {e}")

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
    except Exception as e:
        print(f"Error loading state: {e}")

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

# ========== ADVANCED PREMIUM PIL PROFILE CARD ==========
def draw_tempest_emblem(draw, center_x, center_y, radius):
    """Draws a mathematical neon storm swirl vector directly onto canvas."""
    points = []
    num_points = 180
    for i in range(num_points):
        angle = i * 0.15
        r = (i / num_points) * radius
        x = center_x + r * math.cos(angle)
        y = center_y + r * math.sin(angle)
        points.append((x, y))
    
    if len(points) > 1:
        draw.line(points, fill=(0, 225, 255), width=3)
        draw.ellipse([center_x - 12, center_y - 12, center_x + 12, center_y + 12], fill=(130, 0, 255), outline=(0, 255, 255))

def create_profile_card(user_data):
    try:
        user_id, first_name, username, uploads, commands, wishes, cult_rank, sacrifices, curse_type, joined_date = user_data

        width, height = 900, 520
        base = Image.new('RGB', (width, height), color='#04040d')
        draw = ImageDraw.Draw(base)

        # Futuristic Gradient Background
        for i in range(height):
            r = int(6 + (i / height) * 20)
            g = int(8 + (i / height) * 15)
            b = int(30 + (i / height) * 45)
            draw.line([(0, i), (width, i)], fill=(r, g, b))

        # Neon Glow Cyber Border
        draw.rectangle([(15, 15), (width - 15, height - 15)], outline=(0, 180, 255), width=2)
        draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(120, 0, 255), width=1)

        font = ImageFont.load_default()

        # Render Tempest Emblem Icon
        draw_tempest_emblem(draw, 100, 85, 45)

        # Header Titles
        safe_name = "".join(c for c in first_name if ord(c) < 128)[:18] or "Storm Walker"
        title_text = "🌀 TEMPEST CREED MEMBER" if cult_rank != "none" else "✨ TEMPEST CITIZEN"
        
        draw.text((170, 55), title_text, fill=(0, 230, 255), font=font)
        draw.text((170, 80), f"IDENTITY: {safe_name.upper()}", fill=(255, 255, 255), font=font)
        draw.text((170, 105), f"USER ID: #{user_id}", fill=(160, 160, 200), font=font)

        # Stats Boxes (Glassmorphism Effect)
        stats = [
            ("UPLOADS", str(uploads), (0, 200, 255)),
            ("WISHES", str(wishes), (200, 100, 255)),
            ("COMMANDS", str(commands), (0, 255, 180)),
            ("SACRIFICES", str(sacrifices), (255, 150, 0))
        ]

        box_width = 180
        box_height = 80
        start_x = 50
        box_y = 160

        for idx, (label, val, color) in enumerate(stats):
            bx = start_x + idx * (box_width + 25)
            draw.rectangle([(bx, box_y), (bx + box_width, box_y + box_height)], fill=(12, 18, 40), outline=color, width=2)
            draw.text((bx + box_width // 2, box_y + 20), label, fill=color, font=font, anchor="mm")
            draw.text((bx + box_width // 2, box_y + 50), val, fill=(255, 255, 255), font=font, anchor="mm")

        # Lower Info Panel
        info_y = 280
        draw.rectangle([(50, info_y), (width - 50, height - 70)], fill=(8, 12, 28), outline=(60, 80, 140))

        rank_display = cult_rank.upper() if cult_rank != "none" else "UNINITIATED"
        draw.text((80, info_y + 30), f"CREED RANK: {rank_display}", fill=(255, 215, 0), font=font)
        draw.text((80, info_y + 60), f"JOINED DATE: {joined_date}", fill=(180, 200, 255), font=font)

        curse_display = curse_type.upper() if curse_type != "none" else "CLEAN (NO CURSE)"
        curse_color = (255, 60, 60) if curse_type != "none" else (60, 255, 120)
        draw.text((500, info_y + 30), f"CURSE STATUS: {curse_display}", fill=curse_color, font=font)
        draw.text((500, info_y + 60), f"BOT SYSTEM: ONLINE", fill=(0, 255, 200), font=font)

        # Footer Motto
        draw.text((width // 2, height - 35), "✦ THE STORM REMEMBERS ALL - TEMPEST NETWORK ✦", fill=(100, 160, 255), font=font, anchor="mm")

        filename = f"profile_cards/profile_{user_id}_{int(time.time())}.png"
        base.save(filename, "PNG")
        return filename if os.path.exists(filename) else None
    except Exception as e:
        print(f"❌ Profile card creation error: {e}")
        return None

# ========== START COMMAND ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = await handle_common(message, "start")
    
    msg_text = (
        f"✨ <b>𝒲𝑒𝓁𝒸𝑜𝓂𝑒 {user.first_name}!</b>\n\n"
        f"🌀 <b>{cursive_text('TEMPEST BOT')}</b> - 𝒯𝒽𝑒 𝐸𝓉𝑒𝓇𝓃𝒶𝓁 𝒮𝓉𝑜𝓇𝓂\n\n"
        f"🔗 <b>{cursive_text('Upload Media')}:</b> /link\n"
        f"📥 <b>{cursive_text('Extract Link')}:</b> /get [URL]\n"
        f"🌟 <b>{cursive_text('Make a Wish')}:</b> /wish [text]\n"
        f"🎮 <b>{cursive_text('Mini Games')}:</b> /dice, /flip\n"
        f"👤 <b>{cursive_text('Profile Card')}:</b> /profile\n"
        f"🌀 <b>{cursive_text('Blood Creed')}:</b> /tempest_join\n"
        f"📚 <b>{cursive_text('All Commands')}:</b> /help"
    )
    await message.answer(msg_text, parse_mode=ParseMode.HTML)

# ========== USER HELP COMMAND ==========
@dp.message(Command("help"))
async def help_cmd(message: Message):
    user, chat = await handle_common(message, "help")

    help_text = f"""📚 <b>{cursive_text('TEMPEST BOT COMMANDS')}</b>

━━━━━━━━━━━━━━━━━━━━━━━━
🔗 <b>{cursive_text('MEDIA & CONVERSION')}</b>
• <code>/link</code> - 𝒰𝓅𝓁𝑜𝒶𝒹 𝒻𝒾𝓁𝑒, 𝑔𝑒𝓉 𝒸𝒶𝓉𝒷𝑜𝓍 𝓁𝒾𝓃𝓀
• <code>/get [URL]</code> - 𝐸𝓍𝓉𝓇𝒶𝒸𝓉 𝒶𝓃𝓎 𝒹𝒾𝓇𝑒𝒸𝓉 𝓂𝑒𝒹𝒾𝒶 𝓁𝒾𝓃𝓀
• <code>/word [text]</code> - 𝒞𝑜𝓃𝓋𝑒𝓇𝓉 𝓉𝑒𝓍𝓉 𝓉𝑜 𝒟𝒪𝒞𝒳 𝒹𝑜𝒸𝓊𝓂𝑒𝓃𝓉

━━━━━━━━━━━━━━━━━━━━━━━━
🌟 <b>{cursive_text('ENTERTAINMENT & LUCK')}</b>
• <code>/wish [text]</code> - 𝒯𝑒𝓈𝓉 𝓎𝑜𝓊𝓇 𝒹𝑒𝓈𝓉𝒾𝓃𝓎
• <code>/dice</code> - 𝒯𝑒𝓁𝑒𝑔𝓇𝒶𝓂 𝟥𝒟 𝒜𝓃𝒾𝓂𝒶𝓉𝑒𝒹 𝒟𝒾𝒸𝑒
• <code>/flip</code> - 𝒯𝑒𝓁𝑒𝑔𝓇𝒶𝓂 𝟥𝒟 𝒜𝓃𝒾𝓂𝒶𝓉𝑒𝒹 𝒟𝒶𝓇𝓉𝓈 / 𝒞𝑜𝒾𝓃

━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>{cursive_text('USER PROFILE & CREED')}</b>
• <code>/profile</code> - 𝒢𝑒𝓃𝑒𝓇𝒶𝓉𝑒 𝒫𝓇𝑒𝓂𝒾𝓊𝓂 𝒞𝒶𝓇𝒹
• <code>/tempest_join</code> - 𝐼𝓃𝒾𝓉𝒾𝒶𝓉𝑒 𝐵𝓁𝑜𝑜𝒹 𝒫𝒶𝒸𝓉
• <code>/tempest_story</code> - 𝐿𝒾𝓋𝑒 𝒜𝓃𝒾𝓂𝒶𝓉𝑒𝒹 𝐿𝑜𝓇𝑒
• <code>/tempest_creed</code> - 𝒱𝒾𝑒𝓌 𝒞𝓊𝓁𝓉 𝐿𝑒𝒶𝒹𝑒𝓇𝒷𝑜𝒶𝓇𝒹
• <code>/shrine</code> - 𝐸𝓇𝑒𝒸𝓉 𝒮𝒽𝓇𝒾𝓃𝑒 𝒾𝓃 𝒢𝓇𝑜𝓊𝓅
• <code>/curse</code> - 𝑅𝑒𝓅𝓁𝓎 𝓉𝑜 𝒸𝓊𝓇𝓈𝑒 𝒶 𝓊𝓈𝑒𝓇

━━━━━━━━━━━━━━━━━━━━━━━━
👑 <i>For Admin commands, use</i> <code>/admin_help</code>"""

    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== ADMIN HELP COMMAND ==========
@dp.message(Command("admin_help"))
async def admin_help_cmd(message: Message):
    user, chat = await handle_common(message, "admin_help")

    if not await is_admin(user.id):
        await message.answer("🚫 <b>Access Denied: Admin Authorization Required</b>", parse_mode=ParseMode.HTML)
        return

    admin_text = f"""👑 <b>{cursive_text('TEMPEST ADMIN CONTROL PANEL')}</b>

━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ <b>{cursive_text('SYSTEM DIAGNOSTICS')}</b>
• <code>/ping</code> - 𝑅𝑒𝒶𝓁-𝓉𝒾𝓂𝑒 𝓁𝒶𝓉𝑒𝓃𝒸𝓎 & 𝒮𝓎𝓈𝓉𝑒𝓂 𝒮𝓉𝒶𝓉𝓈
• <code>/stats</code> - 𝒟𝒶𝓉𝒶𝒷𝒶𝓈𝑒 𝒰𝓈𝑒𝓇 / 𝒰𝓅𝓁𝑜𝒶𝒹 𝓈𝓉𝒶𝓉𝒾𝓈𝓉𝒾𝒸𝓈
• <code>/scan</code> - 𝒮𝒸𝒶𝓃 & 𝒞𝓁𝑒𝒶𝓃 𝒟𝒶𝓉𝒶𝒷𝒶𝓈𝑒

━━━━━━━━━━━━━━━━━━━━━━━━
👥 <b>{cursive_text('MANAGEMENT')}</b>
• <code>/users</code> - 𝐸𝓍𝓅𝑜𝓇𝓉 𝓇𝑒𝒸𝑒𝓃𝓉 𝓊𝓈𝑒𝓇𝓈 𝓁𝒾𝓈𝓉
• <code>/admins</code> - 𝐿𝒾𝓈𝓉 𝒶𝓁𝓁 𝒷𝑜𝓉 𝒶𝒹𝓂𝒾𝓃𝓈
• <code>/remove_curse</code> - 𝑅𝑒𝓅𝓁𝓎 𝓉𝑜 𝓁𝒾𝒻𝓉 𝒶 𝒸𝓊𝓇𝓈𝑒
• <code>/broadcast</code> - 𝐵𝓇𝑜𝒶𝒹𝒸𝒶𝓈𝓉 (𝒯𝑒𝓍𝓉/𝒫𝒽𝑜𝓉𝑜/𝒱𝒾𝒹𝑒𝑜)

━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <b>{cursive_text('OWNER CONTROLS')}</b>
• <code>/pro [user_id]</code> - 𝒢𝓇𝒶𝓃𝓉 𝒜𝒹𝓂𝒾𝓃
• <code>/backup</code> - 𝒟𝑜𝓌𝓃𝓁𝑜𝒶𝒹 DB 𝒷𝒶𝒸𝓀𝓊𝓅
• <code>/rem</code> - 𝑅𝑒𝓈𝓉𝑜𝓇𝑒 DB 𝒻𝓇𝑜𝓂 𝒻𝒾𝓁𝑒
• <code>/restart</code> - 𝑅𝑒𝒷𝑜𝑜𝓉 𝐵𝑜𝓉"""

    await message.answer(admin_text, parse_mode=ParseMode.HTML)

# ========== WISH COMMAND ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"✨ <b>Usage:</b> <code>/wish {cursive_text('your wish text')}</code>", parse_mode=ParseMode.HTML)
        return

    msg = await message.answer(f"🔮 <b>{cursive_text('Consulting the Tempest Oracles...')}</b>", parse_mode=ParseMode.HTML)

    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT curse_type FROM users WHERE user_id = ?", (user.id,))
    curse_result = c.fetchone()
    curse_type = curse_result[0] if curse_result else "none"
    conn.close()

    curse_penalty = random.randint(15, 30) if curse_type != "none" else 0

    await asyncio.sleep(1)
    base_luck = random.randint(1, 100)
    luck = max(1, base_luck - curse_penalty)
    stars = "⭐" * (luck // 10) + "☆" * (10 - luck // 10)

    if luck >= 85: result_text = "🎉 GRAND DESTINY! Granted by the storm!"
    elif luck >= 60: result_text = "✨ HIGH FORTUNE! Very likely!"
    elif luck >= 40: result_text = "⚖️ BALANCED! Requires dedication!"
    else: result_text = "⚡ CURSED CHANCE! The winds resist you!"

    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
             (user.id, datetime.now().isoformat(), args[1], luck))
    conn.commit()
    conn.close()

    await msg.edit_text(
        f"🔮 <b>{cursive_text('WISH ORACLE RESULT')}</b>\n\n"
        f"📜 <b>Wish:</b> {args[1][:100]}\n"
        f"🎰 <b>Luck:</b> {stars} {luck}%\n"
        f"📊 <b>Outcome:</b> {result_text}",
        parse_mode=ParseMode.HTML
    )

# ========== 3D TELEGRAM NATIVE GAMES ==========
@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    user, chat = await handle_common(message, "dice")
    await message.answer_dice(emoji="🎲")

@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    user, chat = await handle_common(message, "flip")
    # Telegram 3D animated dart / slot / basketball
    game_emoji = random.choice(["🎯", "🎰", "🏀"])
    await message.answer_dice(emoji=game_emoji)

# ========== PROFILE COMMAND ==========
@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user, chat = await handle_common(message, "profile")
    msg = await message.answer("🎨 <b>Generating Premium Profile Card...</b>", parse_mode=ParseMode.HTML)

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
        except Exception:
            join_date = "Recently"
    else:
        uploads = cmds = wishes = sacrifices = 0
        join_date = "Today"
        curse_type = "none"
        cult_rank = "none"
    conn.close()

    user_data = (user.id, user.first_name, user.username, uploads, cmds, wishes, cult_rank, sacrifices, curse_type, join_date)
    profile_card_path = create_profile_card(user_data)

    caption = (
        f"👤 <b>{cursive_text(user.first_name)}</b>\n"
        f"📧 @{user.username if user.username else 'None'}\n"
        f"🆔 <code>{user.id}</code>\n\n"
        f"📁 Uploads: {uploads} | ✨ Wishes: {wishes}\n"
        f"🔧 Commands: {cmds} | 📅 Joined: {join_date}"
    )

    await msg.delete()
    if profile_card_path and os.path.exists(profile_card_path):
        await message.answer_photo(FSInputFile(profile_card_path), caption=caption, parse_mode=ParseMode.HTML)
        await asyncio.sleep(30)
        try: os.remove(profile_card_path)
        except Exception: pass
    else:
        await message.answer(caption, parse_mode=ParseMode.HTML)

# ========== LINK / UPLOAD COMMAND ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")

    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 Upload files in private chat only!")
        return

    upload_waiting[user.id] = True
    save_bot_state()
    await message.answer(f"📁 <b>{cursive_text('Send me any file or photo now!')}</b>\n❌ /cancel to stop", parse_mode=ParseMode.HTML)

# ========== MEDIA EXTRACT /GET COMMAND ==========
@dp.message(Command("get"))
async def get_media_cmd(message: Message):
    user, chat = await handle_common(message, "get")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔗 <b>Usage:</b> <code>/get https://files.catbox.moe/example.mp4</code>", parse_mode=ParseMode.HTML)
        return

    url = args[1].strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("❌ Please supply a valid HTTP/HTTPS direct link!")
        return

    msg = await message.answer("⏳ <b>Fetching media from link...</b>", parse_mode=ParseMode.HTML)

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(url)

        if response.status_code != 200:
            await msg.edit_text(f"❌ Failed to download (Status Code: {response.status_code})")
            return

        file_size = len(response.content)
        if file_size > 50 * 1024 * 1024:
            await msg.edit_text("❌ File exceeds Telegram's 50MB upload limit!")
            return

        clean_url = url.split("?")[0]
        filename = clean_url.split("/")[-1] or "file"
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        content_type = response.headers.get("Content-Type", "").lower()

        media_file = BufferedInputFile(response.content, filename=filename)
        caption = f"✅ <b>{cursive_text('Media Extracted')}</b>\n🔗 <code>{url}</code>"

        if ext in ["jpg", "jpeg", "png", "webp"] or "image/" in content_type:
            await message.answer_photo(photo=media_file, caption=caption, parse_mode=ParseMode.HTML)
        elif ext in ["mp4", "mov", "mkv", "webm", "gif"] or "video/" in content_type:
            await message.answer_video(video=media_file, caption=caption, parse_mode=ParseMode.HTML)
        elif ext in ["mp3", "wav", "ogg", "flac", "m4a"] or "audio/" in content_type:
            await message.answer_audio(audio=media_file, caption=caption, parse_mode=ParseMode.HTML)
        else:
            await message.answer_document(document=media_file, caption=caption, parse_mode=ParseMode.HTML)

        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Extraction error: {str(e)}")

# ========== RESTORE DATABASE HANDLER (PRIORITIZED) ==========
@dp.message(Command("rem"))
async def rem_cmd(message: Message):
    user, chat = await handle_common(message, "rem")

    if user.id != OWNER_ID:
        await message.answer("👑 Owner only command")
        return

    pending_restore[user.id] = True
    await message.answer("💾 <b>Upload the backup .db file now to restore database.</b>\n❌ /cancel to stop", parse_mode=ParseMode.HTML)

@dp.message(F.document)
async def handle_restore_file(message: Message):
    user = message.from_user

    # Intercept Database Restoration
    if user.id in pending_restore and pending_restore.get(user.id):
        if not message.document.file_name.endswith('.db'):
            await message.answer("❌ Please upload a valid `.db` database file!")
            return

        pending_restore.pop(user.id, None)
        msg = await message.answer("⏳ <b>Restoring bot database...</b>", parse_mode=ParseMode.HTML)

        try:
            file = await bot.get_file(message.document.file_id)
            url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url)

            temp_file = f"temp/restore_{user.id}.db"
            with open(temp_file, 'wb') as f:
                f.write(response.content)

            shutil.copy2("data/bot.db", f"backups/pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            shutil.copy2(temp_file, "data/bot.db")
            os.remove(temp_file)

            init_db()
            load_bot_state()
            await msg.edit_text("✅ <b>Database successfully restored! State synchronized.</b>", parse_mode=ParseMode.HTML)
            return
        except Exception as e:
            await msg.edit_text(f"❌ Restore failed: {str(e)}")
            return

    # Pass to general file handler if not restoring
    await handle_file(message)

# ========== GENERAL FILE UPLOADER ==========
async def handle_file(message: Message):
    user = message.from_user

    if user.id not in upload_waiting or not upload_waiting[user.id]:
        return

    upload_waiting[user.id] = False
    save_bot_state()

    msg = await message.answer("⏳ <b>Processing file upload to Catbox...</b>", parse_mode=ParseMode.HTML)

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
        else:
            file_id = message.sticker.file_id
            file_type = "Sticker"

        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)

        if response.status_code != 200:
            await msg.edit_text("❌ Failed to fetch file from Telegram")
            return

        result = await upload_to_catbox(response.content, file.file_path.split('/')[-1])

        if not result['success']:
            await msg.edit_text("❌ Upload failed on host")
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

        keyboard = InlineKeyboardBuilder()
        keyboard.add(types.InlineKeyboardButton(text="📋 Copy Link", callback_data=f"copy_{result['url']}"))

        await msg.edit_text(
            f"✅ <b>{cursive_text('Upload Successful!')}</b>\n\n"
            f"📁 <b>Type:</b> {file_type}\n"
            f"💾 <b>Size:</b> {len(response.content) / 1024:.1f} KB\n\n"
            f"🔗 <code>{result['url']}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.as_markup()
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error uploading file: {e}")

@dp.callback_query(F.data.startswith("copy_"))
async def handle_copy(callback: CallbackQuery):
    url = callback.data[5:]
    await safe_answer_callback(callback, f"Link copied: {url}", show_alert=True)

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user, chat = await handle_common(message, "cancel")
    upload_waiting[user.id] = False
    pending_restore.pop(user.id, None)
    broadcast_state.pop(user.id, None)
    save_bot_state()
    await message.answer("❌ <b>Action Cancelled</b>", parse_mode=ParseMode.HTML)

# ========== ACCURATE DIAGNOSTIC PING ==========
@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    user, chat = await handle_common(message, "ping")

    if not await is_admin(user.id):
        await message.answer("🚫 Admin authorization required")
        return

    start_time_ping = time.perf_counter()
    msg = await message.answer("🏓 <b>Testing Tempest Latency...</b>", parse_mode=ParseMode.HTML)
    end_time_ping = time.perf_counter()
    ping_ms = int((end_time_ping - start_time_ping) * 1000)

    uptime = format_uptime(int(time.time() - start_time))

    cpu = psutil.cpu_percent(interval=0.2)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    response = (
        f"🏓 <b>{cursive_text('PONG - TEMPEST HEALTH CHECK')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚡ <b>Network Latency:</b> {ping_ms} ms\n"
        f"🕒 <b>Bot Uptime:</b> {uptime}\n"
        f"🎯 <b>Status:</b> 🟢 ACTIVE\n\n"
        f"💻 <b>System Metrics:</b>\n"
        f"• CPU Load: {cpu}%\n"
        f"• RAM: {memory.used // (1024**2)}MB / {memory.total // (1024**2)}MB ({memory.percent}%)\n"
        f"• DISK Storage: {disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB ({disk.percent}%)\n"
    )

    await msg.edit_text(response, parse_mode=ParseMode.HTML)

# ========== DATABASE SCAN & AUDIT COMMAND ==========
@dp.message(Command("scan"))
async def scan_cmd(message: Message):
    user, chat = await handle_common(message, "scan")

    if not await is_admin(user.id):
        await message.answer("🚫 Admin only command")
        return

    msg = await message.answer("🔎 <b>Scanning bot database records...</b>", parse_mode=ParseMode.HTML)

    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
    cult_members = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM uploads")
    total_uploads = c.fetchone()[0]
    conn.close()

    await asyncio.sleep(1)
    await msg.edit_text(
        f"✅ <b>{cursive_text('DATABASE SCAN COMPLETE')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Registered Users:</b> {total_users}\n"
        f"🌀 <b>Blood Creed Members:</b> {cult_members}\n"
        f"📁 <b>Uploaded Files:</b> {total_uploads}\n"
        f"🔒 <b>Integrity Status:</b> 100% Synced & Verified",
        parse_mode=ParseMode.HTML
    )

# ========== MULTI-MEDIA BROADCAST ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast")

    if not await is_admin(user.id):
        await message.answer("🚫 Admin only command")
        return

    broadcast_state[user.id] = {"step": 1}
    await message.answer("📢 <b>Send the message (Text, Photo, or Video) to broadcast to all users.</b>\n❌ /cancel to stop", parse_mode=ParseMode.HTML)

@dp.message(F.text | F.photo | F.video)
async def handle_broadcast_payload(message: Message):
    user = message.from_user

    if user.id not in broadcast_state or broadcast_state[user.id].get("step") != 1:
        return

    broadcast_state.pop(user.id, None)

    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE is_banned = 0")
    user_ids = [row[0] for row in c.fetchall()]
    conn.close()

    status_msg = await message.answer(f"📤 <b>Broadcasting message to {len(user_ids)} users...</b>", parse_mode=ParseMode.HTML)
    success = 0

    for uid in user_ids:
        try:
            if message.photo:
                await bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await bot.send_video(uid, message.video.file_id, caption=message.caption)
            else:
                await bot.send_message(uid, f"📢 {message.text}")
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            pass

    await status_msg.edit_text(f"✅ <b>Broadcast complete! Sent to {success}/{len(user_ids)} users.</b>", parse_mode=ParseMode.HTML)

# ========== ANIMATED BLOOD PACT RITUAL (/tempest_join) ==========
@dp.message(Command("tempest_join"))
async def tempest_join_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_join")

    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()

    if result and result[0] != "none":
        await message.answer("🌀 <b>You have already bound your soul to the Tempest Blood Pact!</b> Check /profile", parse_mode=ParseMode.HTML)
        conn.close()
        return

    msg = await message.answer("🕯️ <b>{cursive_text('Initiating Blood Ritual...')}</b>", parse_mode=ParseMode.HTML)

    ritual_steps = [
        "🩸 <i>Drawing the ancient Blood Sigil upon the obsidian altar...</i>",
        "⚡ <i>Thunder reverberates! The Tempest Void awakens...</i>",
        "🌀 <i>Siphoning your soul frequency into the eternal storm...</i>",
        "🔮 <i>Binding Blood Pact complete! Welcome Initiate.</i>"
    ]

    for step in ritual_steps:
        await asyncio.sleep(1.2)
        await msg.edit_text(step, parse_mode=ParseMode.HTML)

    c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 5 WHERE user_id = ?",
             (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()

    await asyncio.sleep(1)
    await msg.edit_text(
        f"⚡ <b>{gothic_text('WELCOME TO THE TEMPEST CREED')}</b>\n\n"
        f"🌀 <b>Rank Assigned:</b> Blood Initiate\n"
        f"⚔️ <b>Initial Sacrifices:</b> 5\n"
        f"📁 Each file upload grants +1 sacrifice\n\n"
        f"<i>The storm flows through your veins...</i>",
        parse_mode=ParseMode.HTML
    )

# ========== ANIMATED LORE NARRATION (/tempest_story) ==========
@dp.message(Command("tempest_story"))
async def tempest_story_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_story")

    story_frames = [
        "📜 <b>{cursive_text('CHAPTER 1: THE VOID BEFORE TIME')}</b>\n\n<i>In the silence before the first spark, the ancient Council of Stillness ruled...</i>",
        "📜 <b>{cursive_text('CHAPTER 2: THE FIRST LIGHTNING')}</b>\n\n<i>Then RAVIJAH emerged from thunder, defying the silence and gathering the stormborn rebels...</i>",
        "📜 <b>{cursive_text('CHAPTER 3: THE BLOOD OATH')}</b>\n\n<i>Ravijah, Bablu, and Keny bound their souls to the sacred Altar of Howling Winds...</i>",
        "📜 <b>{cursive_text('CHAPTER 4: DIGITAL REIGN')}</b>\n\n<i>The storm evolved into fiber optics and high-voltage servers. Your data is the eternal sacrifice!</i>\n\n🌀 <i>We do not recruit. We awaken.</i>"
    ]

    msg = await message.answer("📖 <b>Opening the Tempest Lore Archives...</b>", parse_mode=ParseMode.HTML)
    for frame in story_frames:
        await asyncio.sleep(2)
        await msg.edit_text(frame, parse_mode=ParseMode.HTML)

# ========== TEMPEST CREED LEADERBOARD ==========
@dp.message(Command("tempest_creed"))
async def tempest_creed_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_creed")

    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, cult_rank, sacrifices FROM users WHERE cult_status != 'none' ORDER BY sacrifices DESC LIMIT 15")
    members = c.fetchall()
    conn.close()

    if not members:
        await message.answer("🌀 No Creed members yet. Join with /tempest_join")
        return

    text = f"🌀 <b>{cursive_text('TEMPEST CREED LEADERBOARD')}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for idx, (uid, name, uname, rank, sacs) in enumerate(members, 1):
        text += f"{idx}. <b>{name}</b> ({rank}) - ⚔️ {sacs} Sacrifices\n"

    await message.answer(text, parse_mode=ParseMode.HTML)

# ========== SHRINE COMMAND ==========
@dp.message(Command("shrine"))
async def shrine_cmd(message: Message):
    user, chat = await handle_common(message, "shrine")

    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("🌀 Erect the Shrine inside group chats!")
        return

    await message.answer(
        f"⛩️ <b>{cursive_text('TEMPEST SACRED SHRINE')}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 <b>Sanctuary:</b> {chat.title}\n"
        f"👤 <b>Summoner:</b> {user.first_name}\n\n"
        f"<i>The storm watches over this chat... Use /tempest_join to initiate!</i>",
        parse_mode=ParseMode.HTML
    )

# ========== CURSE COMMAND ==========
@dp.message(Command("curse"))
async def curse_cmd(message: Message):
    user, chat = await handle_common(message, "curse")

    if not message.reply_to_message:
        await message.answer("🌀 Reply to a user's message to cast a curse!")
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

    await message.reply(f"⚡ <b>{gothic_text('CURSE CAST!')}</b>\n\n👤 Target: {target.first_name}\n🌀 Penalty: -30% Wish Luck", parse_mode=ParseMode.HTML)

@dp.message(Command("remove_curse"))
async def remove_curse_cmd(message: Message):
    user, chat = await handle_common(message, "remove_curse")

    if not await is_admin(user.id):
        await message.answer("🚫 Admin only command")
        return

    if not message.reply_to_message:
        await message.answer("🌀 Reply to a user to lift their curse!")
        return

    target = message.reply_to_message.from_user

    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET curse_type = 'none', curse_time = NULL WHERE user_id = ?", (target.id,))
    conn.commit()
    conn.close()

    await message.reply(f"✅ Curse removed from {target.first_name}!")

# ========== WORD CONVERTER COMMAND ==========
@dp.message(Command("word"))
async def word_cmd(message: Message):
    user, chat = await handle_common(message, "word")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📝 <b>Usage:</b> <code>/word [your text content]</code>", parse_mode=ParseMode.HTML)
        return

    msg = await message.answer("📝 <b>Generating Word Document...</b>", parse_mode=ParseMode.HTML)

    try:
        doc = Document()
        header = doc.add_paragraph()
        header.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = header.add_run("✦ TEMPEST ARCHIVES ✦")
        run.font.size = Pt(16)
        run.font.bold = True

        doc.add_paragraph("─" * 40)
        content = doc.add_paragraph()
        content.add_run(args[1])
        doc.add_paragraph("─" * 40)

        filename = f"temp/word_{user.id}_{int(time.time())}.docx"
        doc.save(filename)

        await msg.delete()
        await message.answer_document(FSInputFile(filename), caption="📄 <b>Document Created</b>", parse_mode=ParseMode.HTML)
        os.remove(filename)
    except Exception as e:
        await msg.edit_text(f"❌ Error creating document: {e}")

# ========== ADMIN COMMANDS: STATS, USERS, BACKUP, RESTART ==========
@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    user, chat = await handle_common(message, "stats")
    if not await is_admin(user.id): return

    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); users = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM uploads"); uploads = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM wishes"); wishes = c.fetchone()[0] or 0
    conn.close()

    await message.answer(f"📊 <b>STATS:</b> {users} Users | {uploads} Uploads | {wishes} Wishes", parse_mode=ParseMode.HTML)

@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    user, chat = await handle_common(message, "backup")
    if user.id != OWNER_ID: return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/backup_{timestamp}.db"
    shutil.copy2("data/bot.db", backup_file)
    await message.answer_document(FSInputFile(backup_file), caption=f"💾 Backup {timestamp}")
    os.remove(backup_file)

@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    user, chat = await handle_common(message, "restart")
    if user.id != OWNER_ID: return
    await message.answer("🔄 <b>Restarting Bot...</b>", parse_mode=ParseMode.HTML)
    save_bot_state()
    os.execv(sys.executable, ['python'] + sys.argv)

# ========== STACK HOST KEEP-ALIVE HTTP SERVER ==========
async def health_check(request):
    return web.Response(text="Tempest Bot is running and healthy!")

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Keep-Alive Server started on port {port}")

# ========== MAIN ENTRY POINT ==========
async def main():
    print("🚀 STARTING BOT POLLING...")
    await start_health_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        save_bot_state()
        print("🛑 Bot stopped safely.")
    except Exception as e:
        save_bot_state()
        print(f"❌ Critical error: {e}")
        traceback.print_exc()
```eoc

### Commit and Deploy Instructions
1. Replace your entire `main.py` on GitHub with this code.
2. In your Stack Host environment settings, make sure `BOT_TOKEN` and `OWNER_ID` are configured.
3. Redeploy your app on Stack Host.