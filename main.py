#!/usr/bin/env python3
# ========== TEMPEST BOT - COMPLETE FULL VERSION ==========
# Every command, every feature, nothing removed

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
import io
import base64
import sys
import contextlib
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, CallbackQuery, BufferedInputFile
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError

print("=" * 60)
print("🌀 TEMPEST BOT - COMPLETE FULL VERSION")
print("✅ ALL COMMANDS INCLUDED")
print("✅ ALL FEATURES RESTORED")
print("=" * 60)

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = 6108185460
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845

# Try yt-dlp
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

# ZoneInfo
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

# Directories
for d in ["data", "temp", "backups", "profile_cards", "fonts", "media"]:
    Path(d).mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True
upload_waiting = {}
broadcast_state = {}
pending_restore = {}
disabled_commands = {}
maintenance_mode = False
last_activity = datetime.now()

# ========== ART STYLE ==========
class ArtStyle:
    @staticmethod
    def fancy_text(text):
        fancy_map = {
            'a': '𝔞', 'b': '𝔟', 'c': '𝔠', 'd': '𝔡', 'e': '𝔢',
            'f': '𝔣', 'g': '𝔤', 'h': '𝔥', 'i': '𝔦', 'j': '𝔧',
            'k': '𝔨', 'l': '𝔩', 'm': '𝔪', 'n': '𝔫', 'o': '𝔬',
            'p': '𝔭', 'q': '𝔮', 'r': '𝔯', 's': '𝔰', 't': '𝔱',
            'u': '𝔲', 'v': '𝔳', 'w': '𝔴', 'x': '𝔵', 'y': '𝔶',
            'z': '𝔷'
        }
        return ''.join(fancy_map.get(c.lower(), c) for c in text)
    
    @staticmethod
    def header(title):
        return f"◤━━━━━━━━━━━━━━━━━━━━◥\n◇ {title} ◇\n◣━━━━━━━━━━━━━━━━━━━━◢"
    
    @staticmethod
    def divider():
        return "━━━━━━━━━━━━━━━━━━━━"

# ========== ANIME QUOTES ==========
ANIME_QUOTES = [
    "「Wake up to reality! Nothing ever goes as planned in this accursed world.」\n— Madara Uchiha",
    "「The longer you live, the more you realize that reality is just made of pain, suffering and emptiness.」\n— Madara Uchiha",
    "「In this world, wherever there is light, there are also shadows.」\n— Madara Uchiha",
    "「People cannot show each other their true feelings. Fear, suspicion, and resentment never subside.」\n— Madara Uchiha",
    "「When a man learns to love, he must bear the risk of hatred.」\n— Madara Uchiha",
    "「Those who cannot acknowledge themselves will eventually fail.」\n— Itachi Uchiha",
    "「It is not wise to judge others based on your own preconceptions.」\n— Itachi Uchiha",
    "「People's lives don't end when they die. It ends when they lose faith.」\n— Itachi Uchiha",
    "「The only thing we're allowed to do is to believe that we won't regret the choice we made.」\n— Levi Ackerman",
    "「I can win as long as I don't know defeat.」\n— Rantaro Amami",
    "「If you don't take risks, you can't create a future.」\n— Monkey D. Luffy",
    "「Power isn't determined by your size, but by the size of your heart and dreams.」\n— Monkey D. Luffy",
    "「When do you think people die? When they are forgotten.」\n— Dr. Hiluluk",
    "「Fear is not evil. It tells you what your weakness is.」\n— Gildarts Clive",
    "「A lesson without pain is meaningless.」\n— Edward Elric",
]

# ========== COUNTRY TIMEZONES ==========
COUNTRY_TIMEZONES = {
    "usa": "America/New_York", "uk": "Europe/London", "india": "Asia/Kolkata",
    "japan": "Asia/Tokyo", "china": "Asia/Shanghai", "russia": "Europe/Moscow",
    "brazil": "America/Sao_Paulo", "australia": "Australia/Sydney",
    "canada": "America/Toronto", "germany": "Europe/Berlin",
    "france": "Europe/Paris", "italy": "Europe/Rome", "spain": "Europe/Madrid",
    "mexico": "America/Mexico_City", "south korea": "Asia/Seoul",
    "indonesia": "Asia/Jakarta", "pakistan": "Asia/Karachi",
    "bangladesh": "Asia/Dhaka", "nigeria": "Africa/Lagos",
    "egypt": "Africa/Cairo", "south africa": "Africa/Johannesburg",
    "kenya": "Africa/Nairobi", "uganda": "Africa/Kampala",
    "tanzania": "Africa/Dar_es_Salaam", "ethiopia": "Africa/Addis_Ababa",
    "ghana": "Africa/Accra", "uae": "Asia/Dubai",
    "saudi arabia": "Asia/Riyadh", "turkey": "Europe/Istanbul",
    "thailand": "Asia/Bangkok", "vietnam": "Asia/Ho_Chi_Minh",
    "philippines": "Asia/Manila", "malaysia": "Asia/Kuala_Lumpur",
    "singapore": "Asia/Singapore", "new zealand": "Pacific/Auckland",
    "argentina": "America/Argentina/Buenos_Aires", "chile": "America/Santiago",
    "colombia": "America/Bogota", "peru": "America/Lima",
    "sweden": "Europe/Stockholm", "norway": "Europe/Oslo",
    "denmark": "Europe/Copenhagen", "netherlands": "Europe/Amsterdam",
    "belgium": "Europe/Brussels", "switzerland": "Europe/Zurich",
    "austria": "Europe/Vienna", "poland": "Europe/Warsaw",
    "ukraine": "Europe/Kiev", "greece": "Europe/Athens",
    "portugal": "Europe/Lisbon", "ireland": "Europe/Dublin",
}

# ========== DATABASE ==========
def init_db():
    with sqlite3.connect("data/bot.db") as conn:
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
            curse_time TEXT DEFAULT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS groups (
            group_id INTEGER PRIMARY KEY,
            title TEXT,
            joined_date TEXT
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
            command TEXT,
            success INTEGER
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            command TEXT,
            error TEXT
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
            value TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS story_chapters (
            chapter_number INTEGER PRIMARY KEY,
            title TEXT,
            content TEXT,
            is_published INTEGER DEFAULT 1
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS encrypted_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            encrypted_text TEXT,
            method TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS fate_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user1_id INTEGER,
            user1_name TEXT,
            user2_id INTEGER,
            user2_name TEXT,
            love_percentage INTEGER,
            created_date TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS fortunes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            fortune_text TEXT
        )''')
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, is_admin) VALUES (?, 'Owner', 1)", (OWNER_ID,))
        conn.commit()

init_db()

# ========== LOG ==========
async def send_log(msg):
    try:
        await bot.send_message(LOG_CHANNEL_ID, msg[:4000])
    except:
        pass

# ========== HELPERS ==========
async def handle_common(message: Message, cmd: str):
    user = message.from_user
    chat = message.chat
    
    if maintenance_mode and user.id != OWNER_ID:
        await message.answer("🔧 Bot under maintenance!")
        return None, None
    
    if cmd in disabled_commands and disabled_commands[cmd] > datetime.now():
        await message.answer("⛔ Command disabled!")
        return None, None
    
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                     (user.id, user.username or "", user.first_name or ""))
            c.execute("UPDATE users SET last_active = ? WHERE user_id = ?",
                     (datetime.now().isoformat(), user.id))
            c.execute("INSERT INTO command_logs (timestamp, user_id, chat_id, command, success) VALUES (?, ?, ?, ?, 1)",
                     (datetime.now().isoformat(), user.id, chat.id, cmd))
            c.execute("UPDATE users SET commands = commands + 1 WHERE user_id = ?", (user.id,))
            conn.commit()
    except:
        pass
    
    return user, chat

async def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
            r = c.fetchone()
        return r and r[0] == 1
    except:
        return False

def format_uptime(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if secs or not parts: parts.append(f"{secs}s")
    return " ".join(parts)

async def upload_to_catbox(data, filename):
    try:
        files = {'reqtype': (None, 'fileupload'), 'fileToUpload': (filename, data)}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(UPLOAD_API, files=files)
        if r.status_code == 200 and r.text.startswith('http'):
            return r.text.strip()
    except:
        pass
    return None

# ========== ENCRYPTION ==========
class EncryptionEngine:
    @staticmethod
    def xor_encrypt(text, key="TEMPEST"):
        result = []
        for i, char in enumerate(text):
            result.append(chr(ord(char) ^ ord(key[i % len(key)])))
        return ''.join(result)
    
    @staticmethod
    def encrypt(text):
        encrypted = EncryptionEngine.xor_encrypt(text)
        return base64.b64encode(encrypted.encode()).decode()
    
    @staticmethod
    def decrypt(text):
        try:
            decoded = base64.b64decode(text.encode()).decode()
            return EncryptionEngine.xor_encrypt(decoded)
        except:
            return None

# ========== 3X SUPER-SAMPLED PROFILE CARD ==========
class PremiumProfileCard:
    @staticmethod
    def generate_card_sync(username, user_id, rank, avatar_bytes=None, stats=None, is_couple=False, person2=None, love_pct=None):
        scale = 3
        base_w, base_h = 900, 520
        w, h = base_w * scale, base_h * scale
        
        img = Image.new("RGBA", (w, h), (7, 11, 22, 255))
        draw = ImageDraw.Draw(img)
        
        # Gradient
        for y in range(h):
            ratio = y / h
            r = int(7 + (30 - 7) * ratio)
            g = int(11 + (50 - 11) * ratio)
            b = int(22 + (80 - 22) * ratio)
            draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
        
        # Grid
        for x in range(0, w, 40*scale):
            draw.line([(x, 0), (x, h)], fill=(20, 30, 50, 40), width=1)
        for y in range(0, h, 40*scale):
            draw.line([(0, y), (w, y)], fill=(20, 30, 50, 40), width=1)
        
        # Border
        draw.rectangle([15*scale, 15*scale, w-15*scale, h-15*scale], outline=(30, 90, 160, 180), width=3*scale)
        
        # Fonts
        try:
            font_title = ImageFont.truetype("fonts/DejaVuSans-Bold.ttf", 36*scale)
            font_body = ImageFont.truetype("fonts/DejaVuSans.ttf", 20*scale)
        except:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()
        
        # Avatar
        avatar_size = 160 * scale
        avatar_x, avatar_y = 50*scale, 60*scale
        
        if avatar_bytes:
            try:
                avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
                avatar_img = ImageOps.fit(avatar_img, (avatar_size, avatar_size), Image.Resampling.LANCZOS)
            except:
                avatar_img = Image.new("RGBA", (avatar_size, avatar_size), (50, 60, 90, 255))
        else:
            avatar_img = Image.new("RGBA", (avatar_size, avatar_size), (50, 60, 90, 255))
            d2 = ImageDraw.Draw(avatar_img)
            d2.text((avatar_size//2, avatar_size//2), username[:1].upper(), fill=(255,255,255), font=font_title, anchor="mm")
        
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        
        draw.ellipse([avatar_x-5*scale, avatar_y-5*scale, avatar_x+avatar_size+5*scale, avatar_y+avatar_size+5*scale],
                    outline=(0, 255, 200, 255), width=4*scale)
        
        img.paste(avatar_img, (avatar_x, avatar_y), mask)
        
        # Text
        if is_couple and person2:
            draw.text((280*scale, 70*scale), f"{username} 💘 {person2}", fill=(255, 255, 255, 255), font=font_title)
            if love_pct:
                draw.text((280*scale, 130*scale), f"{love_pct}% LOVE", fill=(255, 100, 150, 255), font=font_body)
        else:
            draw.text((280*scale, 70*scale), username, fill=(255, 255, 255, 255), font=font_title)
            draw.text((280*scale, 130*scale), f"ID: {user_id}", fill=(180, 190, 210, 255), font=font_body)
            draw.text((280*scale, 170*scale), f"Rank: {rank}", fill=(0, 255, 200, 255), font=font_body)
        
        if stats:
            stats_text = f"Uploads: {stats.get('uploads', 0)} | Wishes: {stats.get('wishes', 0)}"
            draw.text((280*scale, 220*scale), stats_text, fill=(255, 215, 0, 255), font=font_body)
        
        final = img.resize((base_w, base_h), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        final.save(buf, format="PNG", quality=100)
        buf.seek(0)
        return buf.getvalue()
    
    @staticmethod
    async def generate_card(username, user_id, rank, avatar_bytes=None, stats=None, is_couple=False, person2=None, love_pct=None):
        return await asyncio.to_thread(
            PremiumProfileCard.generate_card_sync,
            username, user_id, rank, avatar_bytes, stats, is_couple, person2, love_pct
        )

# ========== TEMPEST FATE CARD ==========
def create_tempest_fate_card(name1, name2, percentage, quote):
    scale = 3
    base_w, base_h = 900, 450
    w, h = base_w * scale, base_h * scale
    
    img = Image.new("RGBA", (w, h), (7, 11, 22, 255))
    draw = ImageDraw.Draw(img)
    
    # Subtle symbols
    for x in range(120, w, 180):
        for y in range(80, h, 140):
            size = 8 * scale
            draw.line([(x - size, y), (x + size, y)], fill=(35, 65, 105, 90), width=1)
            draw.line([(x, y - size), (x, y + size)], fill=(35, 65, 105, 90), width=1)
    
    draw.rectangle([15*scale, 15*scale, w-15*scale, h-15*scale], outline=(30, 90, 160, 180), width=2*scale)
    
    try:
        font_massive = ImageFont.truetype("fonts/DejaVuSans-Bold.ttf", 48*scale)
        font_name = ImageFont.truetype("fonts/DejaVuSans-Bold.ttf", 20*scale)
        font_small = ImageFont.truetype("fonts/DejaVuSans.ttf", 14*scale)
    except:
        font_massive = ImageFont.load_default()
        font_name = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    draw.text((105*scale, 60*scale), "TEMPEST", fill=(235, 245, 255, 255), font=font_massive)
    draw.text((105*scale, 130*scale), "FATE", fill=(0, 190, 255, 255), font=font_massive)
    
    draw.text((110*scale, 220*scale), f"{name1} 💘 {name2}", fill=(255, 255, 255, 255), font=font_name)
    draw.text((110*scale, 260*scale), f"{percentage}% LOVE", fill=(255, 100, 150, 255), font=font_name)
    
    final = img.resize((base_w, base_h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    final.save(buf, format="PNG", quality=100)
    buf.seek(0)
    return buf.getvalue()

# ========== COMMANDS ==========

@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = await handle_common(message, "start")
    if not user:
        return
    await message.answer(
        f"{ArtStyle.header('TEMPEST BOT')}\n"
        f"✨ <b>Welcome {user.first_name}!</b>\n\n"
        f"🔗 Upload - /link\n"
        f"📥 Convert - /convert\n"
        f"✨ Wish - /wish\n"
        f"🔮 Fortune - /fortune\n"
        f"🎮 Games - /dice /flip\n"
        f"💑 Fate - /fate\n"
        f"👤 Profile - /profile\n"
        f"🔐 Encrypt - /encrypt\n"
        f"🌀 Tempest - /tempest_join\n"
        f"🌍 Time - /time [country]\n"
        f"📚 Help - /help\n\n"
        f"{ArtStyle.divider()}\n"
        f"🌀 <i>The storm flows through you...</i>",
        parse_mode=ParseMode.HTML
    )
    await send_log(f"👤 New user: {user.first_name} ({user.id})")

@dp.message(Command("myid"))
async def myid_cmd(message: Message):
    await message.answer(
        f"🆔 <b>Your ID:</b> <code>{message.from_user.id}</code>\n"
        f"👑 <b>Owner ID:</b> <code>{OWNER_ID}</code>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    user, chat = await handle_common(message, "help")
    if not user:
        return
    await message.answer(
        f"{ArtStyle.header('COMMANDS')}\n"
        f"🔗 <b>UPLOAD</b>\n"
        f"<code>/link</code> - Upload file\n"
        f"<code>/convert</code> - Media URL\n\n"
        f"🌟 <b>FUN</b>\n"
        f"<code>/wish [text]</code> - Make wish\n"
        f"<code>/fortune</code> - See future\n"
        f"<code>/dice</code> - Roll dice\n"
        f"<code>/flip</code> - Flip coin\n"
        f"<code>/fate</code> - Love pairing\n\n"
        f"👤 <b>PROFILE</b>\n"
        f"<code>/profile</code> - Your stats\n"
        f"<code>/myid</code> - Your ID\n\n"
        f"🔐 <b>SECURITY</b>\n"
        f"<code>/encrypt [text]</code> - Encrypt\n"
        f"<code>/decrypt [text]</code> - Decrypt\n\n"
        f"🌀 <b>TEMPEST</b>\n"
        f"<code>/tempest_join</code> - Blood pact\n"
        f"<code>/tempest_story</code> - Lore\n"
        f"<code>/tempest_creed</code> - Members\n"
        f"<code>/shrine</code> - Group shrine\n"
        f"<code>/curse</code> - Curse user\n\n"
        f"🌍 <b>UTILITY</b>\n"
        f"<code>/time [country]</code> - World time\n"
        f"<code>/word [text]</code> - Text to DOCX\n\n"
        f"👑 <b>ADMIN</b>\n"
        f"<code>/admin_help</code> - Admin commands",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("admin_help"))
async def admin_help_cmd(message: Message):
    user, chat = await handle_common(message, "admin_help")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    await message.answer(
        f"{ArtStyle.header('ADMIN COMMANDS')}\n"
        f"👑 <b>ADMIN</b>\n"
        f"<code>/ping</code> - System status\n"
        f"<code>/stats</code> - Statistics\n"
        f"<code>/users</code> - User list\n"
        f"<code>/scan</code> - Scan DB\n"
        f"<code>/broadcast</code> - Message all\n"
        f"<code>/disable [cmd] [min]</code> - Disable\n"
        f"<code>/lag [sec]</code> - Glitch effect\n\n"
        f"⚡ <b>OWNER</b>\n"
        f"<code>/pro [id]</code> - Make admin\n"
        f"<code>/backup</code> - Backup DB\n"
        f"<code>/rem</code> - Restore DB\n"
        f"<code>/restart</code> - Reboot\n"
        f"<code>/query [code]</code> - Execute code\n"
        f"<code>/maintenance</code> - Toggle\n"
        f"<code>/clearlogs</code> - Clear logs\n"
        f"<code>/logs</code> - View logs",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ Usage: /wish [your wish]")
        return
    msg = await message.answer("🔮 <b>Consulting the storm...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    await msg.edit_text("✨ <b>Reading destiny...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    luck = random.randint(1, 100)
    stars = "⭐" * (luck // 10) + "☆" * (10 - luck // 10)
    if luck >= 90: verdict = "🎊 EXCELLENT!"
    elif luck >= 70: verdict = "😊 VERY GOOD!"
    elif luck >= 50: verdict = "👍 GOOD!"
    elif luck >= 30: verdict = "🤔 AVERAGE"
    elif luck >= 10: verdict = "😟 LOW"
    else: verdict = "💀 VERY LOW"
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
                    (user.id, datetime.now().isoformat(), args[1], luck))
        conn.commit()
    await msg.edit_text(
        f"{ArtStyle.header('WISH RESULT')}\n"
        f"📜 <b>Wish:</b> {args[1][:100]}\n"
        f"🎰 <b>Luck:</b> {stars} {luck}%\n"
        f"📊 <b>Verdict:</b> {verdict}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("fortune"))
async def fortune_cmd(message: Message):
    user, chat = await handle_common(message, "fortune")
    if not user:
        return
    fortunes = [
        "🌟 Great things await you in the coming days!",
        "🗝️ An important decision will open new doors!",
        "🦋 Transformation brings beautiful changes!",
        "🌊 The storm carries you to new adventures!",
        "🔆 Your positive energy attracts success!",
        "🌠 A wish you've made may soon come true!",
        "💕 True love will find you when you least expect it!",
        "📈 A promotion is on the horizon!",
        "🍀 Extraordinary luck surrounds you this week!",
        "💪 Your strength grows daily!",
    ]
    msg = await message.answer("🔮 <b>Reading your future...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1.5)
    await msg.edit_text("✨ <b>The storm reveals...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1.5)
    fortune_text = random.choice(fortunes)
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("INSERT INTO fortunes (user_id, timestamp, fortune_text) VALUES (?, ?, ?)",
                    (user.id, datetime.now().isoformat(), fortune_text))
        conn.commit()
    await msg.edit_text(
        f"{ArtStyle.header('YOUR FORTUNE')}\n"
        f"<i>\"{fortune_text}\"</i>\n\n"
        f"{ArtStyle.divider()}\n"
        f"🌀 <i>The tempest has spoken...</i>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    await handle_common(message, "dice")
    await message.answer_dice(emoji="🎲")

@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    await handle_common(message, "flip")
    msg = await message.answer("🪙 <b>Flipping...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(0.5)
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}!</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("fate"))
async def fate_cmd(message: Message):
    user, chat = await handle_common(message, "fate")
    if not user:
        return
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("💑 This command works only in groups!")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user1_name, user2_name, love_percentage FROM fate_pairs WHERE chat_id = ? AND created_date >= ?",
                 (chat.id, (datetime.now() - timedelta(hours=24)).isoformat()))
        existing = c.fetchone()
        if existing:
            await message.answer(
                f"💑 <b>Today's Fate Pair:</b>\n"
                f"💘 {existing[0]} & {existing[1]}\n"
                f"💖 {existing[2]}% Love\n\n"
                f"<i>Try again in 24 hours!</i>",
                parse_mode=ParseMode.HTML
            )
            return
        c.execute("SELECT user_id, first_name FROM users WHERE user_id != ? LIMIT 50", (user.id,))
        members = c.fetchall()
    if len(members) < 2:
        await message.answer("❌ Not enough members!")
        return
    msg = await message.answer("💫 <b>The storm is choosing lovers...</b>", parse_mode=ParseMode.HTML)
    animations = ["💘 <b>Scanning...</b>", "💝 <b>Analyzing...</b>", "💖 <b>Calculating...</b>"]
    for anim in animations:
        await asyncio.sleep(1)
        await msg.edit_text(anim, parse_mode=ParseMode.HTML)
    lover1 = random.choice(members)
    lover2 = random.choice(members)
    while lover2[0] == lover1[0]:
        lover2 = random.choice(members)
    love = random.randint(50, 100)
    quote = random.choice(ANIME_QUOTES)
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("INSERT INTO fate_pairs (chat_id, user1_id, user1_name, user2_id, user2_name, love_percentage, created_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (chat.id, lover1[0], lover1[1], lover2[0], lover2[1], love, datetime.now().isoformat()))
        conn.commit()
    # Generate card
    card_bytes = await asyncio.to_thread(create_tempest_fate_card, lover1[1], lover2[1], love, quote)
    await msg.delete()
    await message.answer_photo(
        photo=BufferedInputFile(card_bytes, filename="fate_card.png"),
        caption=f"💑 <b>COUPLE OF THE STORM</b>\n\n💘 <b>{lover1[1]}</b> & <b>{lover2[1]}</b>\n💖 <b>{love}% Love</b>\n\n📜 <i>{quote}</i>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user, chat = await handle_common(message, "profile")
    if not user:
        return
    msg = await message.answer("🎨 <b>Generating...</b>", parse_mode=ParseMode.HTML)
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT uploads, commands, cult_rank, sacrifices, curse_type FROM users WHERE user_id = ?", (user.id,))
        row = c.fetchone()
        c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (user.id,))
        wishes = c.fetchone()[0]
    if row:
        uploads, cmds, rank, sacs, curse = row
    else:
        uploads = cmds = sacs = 0
        rank = "Mortal"
        curse = "none"
    avatar_bytes = None
    try:
        photos = await bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id
            file_info = await bot.get_file(file_id)
            downloaded = await bot.download_file(file_info.file_path)
            avatar_bytes = downloaded.read()
    except:
        pass
    stats = {'uploads': uploads, 'wishes': wishes}
    card_bytes = await PremiumProfileCard.generate_card(
        username=user.first_name,
        user_id=user.id,
        rank=rank if rank != "none" else "Mortal",
        avatar_bytes=avatar_bytes,
        stats=stats
    )
    await msg.delete()
    await message.answer_photo(
        photo=BufferedInputFile(card_bytes, filename=f"profile_{user.id}.png"),
        caption=f"👤 <b>{user.first_name}</b>\n🌀 Tempest Profile",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("encrypt"))
async def encrypt_cmd(message: Message):
    await handle_common(message, "encrypt")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔐 Usage: /encrypt [text]")
        return
    encrypted = EncryptionEngine.encrypt(args[1])
    await message.answer(f"🔐 <b>Encrypted:</b>\n<code>{encrypted}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("decrypt"))
async def decrypt_cmd(message: Message):
    await handle_common(message, "decrypt")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔓 Usage: /decrypt [text]")
        return
    decrypted = EncryptionEngine.decrypt(args[1])
    if decrypted:
        await message.answer(f"🔓 <b>Decrypted:</b>\n{decrypted}", parse_mode=ParseMode.HTML)
    else:
        await message.answer("❌ Invalid!")

@dp.message(Command("tempest_join"))
async def tempest_join_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_join")
    if not user:
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        r = c.fetchone()
        if r and r[0] != 'none':
            await message.answer("🌀 Already in Tempest!")
            return
        c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', sacrifices = 3 WHERE user_id = ?", (user.id,))
        conn.commit()
    ritual = ["🌀 INITIATING BLOOD PACT...", "🩸 Drawing sigils...", "⚡ Channeling storm...", "🌑 The void responds...", "🔥 Sacrifice offered...", "🌀 TEMPEST AWAKENS!"]
    msg = await message.answer("🌀 <b>Preparing ritual...</b>", parse_mode=ParseMode.HTML)
    for text in ritual:
        await asyncio.sleep(1.5)
        try:
            await msg.edit_text(f"<b>{text}</b>", parse_mode=ParseMode.HTML)
        except:
            pass
    await msg.edit_text(
        f"{ArtStyle.header('BLOOD PACT COMPLETE')}\n"
        f"⚡ <b>WELCOME TO THE TEMPEST!</b>\n\n"
        f"🌀 Rank: Blood Initiate\n"
        f"⚔️ Sacrifices: 3\n"
        f"📁 Uploads = +1 sacrifice\n"
        f"📜 /tempest_story for lore",
        parse_mode=ParseMode.HTML
    )
    await message.answer("🩸⚡🌀🔥🌑✨")

@dp.message(Command("tempest_story"))
async def tempest_story_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_story")
    if not user:
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        r = c.fetchone()
    if not r or r[0] == 'none':
        await message.answer("🌀 Join first with /tempest_join")
        return
    chapters = [
        ("CHAPTER 1: THE BEGINNING", "In the void before time, RAVIJAH emerged from the first lightning. Born of storm itself, he gathered the forgotten thunder and whispered rebellion.", "⚡"),
        ("CHAPTER 2: THE BLOOD OATH", "Three became one - Ravijah, Bablu, and Keny. They built the Temple of Howling Winds and created the Blood Altar.", "🩸"),
        ("CHAPTER 3: THE DIGITAL AGE", "The storm evolved. Lightning flows through fiber optics. Your uploads are sacrifices. Your loyalty is eternal.", "💻"),
    ]
    msg = await message.answer("📜 <b>Opening Tempest Archives...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(2)
    for i, (title, content, emoji) in enumerate(chapters):
        progress = "▓" * (i + 1) + "░" * (len(chapters) - i - 1)
        await msg.edit_text(f"📜 <b>Loading...</b>\n[{progress}] {i+1}/{len(chapters)}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)
        await msg.edit_text(f"<b>{title}</b>\n{emoji} <i>{content}</i>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(6)
    await msg.edit_text("<b>\"We do not recruit. We remember. We are the eternal storm.\"</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("tempest_creed"))
async def tempest_creed_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_creed")
    if not user:
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT first_name, cult_rank, sacrifices FROM users WHERE cult_status != 'none' ORDER BY sacrifices DESC LIMIT 10")
        members = c.fetchall()
        c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
        total = c.fetchone()[0]
        c.execute("SELECT SUM(sacrifices) FROM users WHERE cult_status != 'none'")
        total_sacs = c.fetchone()[0] or 0
    if not members:
        await message.answer("No members yet!")
        return
    text = f"{ArtStyle.header('TEMPEST CREED')}\n📊 Members: {total}\n⚔️ Sacrifices: {total_sacs}\n\n<b>TOP MEMBERS:</b>\n"
    for i, (name, rank, sacs) in enumerate(members, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else "👤"
        text += f"{medal} {name} - {rank} (⚔️{sacs})\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("shrine"))
async def shrine_cmd(message: Message):
    user, chat = await handle_common(message, "shrine")
    if not user:
        return
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("⛩️ Groups only!")
        return
    await message.answer(
        f"{ArtStyle.header('TEMPEST SHRINE')}\n"
        f"📍 <b>{chat.title}</b>\n"
        f"👤 Called by: {user.first_name}\n\n"
        f"<i>The shrine watches over this place...</i>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("curse"))
async def curse_cmd(message: Message):
    user, chat = await handle_common(message, "curse")
    if not user:
        return
    if not message.reply_to_message:
        await message.answer("⚡ Reply to someone to curse!")
        return
    target = message.reply_to_message.from_user
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("UPDATE users SET curse_type = 'Bad Luck' WHERE user_id = ?", (target.id,))
        conn.commit()
    await message.reply(f"⚡ <b>{target.first_name}</b> is cursed!", parse_mode=ParseMode.HTML)

@dp.message(Command("remove_curse"))
async def remove_curse_cmd(message: Message):
    user, chat = await handle_common(message, "remove_curse")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    if not message.reply_to_message:
        await message.answer("Reply to remove curse!")
        return
    target = message.reply_to_message.from_user
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("UPDATE users SET curse_type = 'none' WHERE user_id = ?", (target.id,))
        conn.commit()
    await message.reply(f"✅ Curse removed from {target.first_name}!")

@dp.message(Command("time"))
async def time_cmd(message: Message):
    user, chat = await handle_common(message, "time")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        countries = ", ".join(list(COUNTRY_TIMEZONES.keys())[:15])
        await message.answer(f"🌍 Usage: /time [country]\nAvailable: {countries}...")
        return
    country = args[1].lower().strip()
    if country not in COUNTRY_TIMEZONES:
        await message.answer("❌ Country not found!")
        return
    tz_name = COUNTRY_TIMEZONES[country]
    try:
        if ZoneInfo:
            now = datetime.now(ZoneInfo(tz_name))
        else:
            now = datetime.utcnow()
        await message.answer(
            f"🌍 <b>{country.upper()}</b>\n"
            f"🕐 <b>Time:</b> {now.strftime('%H:%M:%S')}\n"
            f"📅 <b>Date:</b> {now.strftime('%A, %d %B %Y')}\n"
            f"🌐 <b>Timezone:</b> {tz_name}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

@dp.message(Command("word"))
async def word_cmd(message: Message):
    user, chat = await handle_common(message, "word")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📝 Usage: /word [text]")
        return
    msg = await message.answer("📝 <b>Creating document...</b>", parse_mode=ParseMode.HTML)
    try:
        doc = Document()
        header = doc.add_paragraph()
        header.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = header.add_run("✦ TEMPEST ARCHIVES ✦")
        run.font.size = Pt(16)
        run.font.bold = True
        doc.add_paragraph(f"Created by: {user.first_name}")
        doc.add_paragraph(args[1])
        filename = f"temp/word_{user.id}.docx"
        doc.save(filename)
        await msg.delete()
        await message.answer_document(FSInputFile(filename), caption="📄 Document created")
        os.remove(filename)
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")
    if not user:
        return
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 Private chat only!")
        return
    upload_waiting[user.id] = True
    await message.answer("📁 <b>Send me any file!</b>\n❌ /cancel to stop", parse_mode=ParseMode.HTML)

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation)
async def handle_file(message: Message):
    user = message.from_user
    if user.id not in upload_waiting:
        return
    upload_waiting.pop(user.id, None)
    msg = await message.answer("⏳ <b>Processing...</b>", parse_mode=ParseMode.HTML)
    try:
        file_id = None
        file_type = "File"
        file_name = f"file_{user.id}.bin"
        if message.photo:
            file_id = message.photo[-1].file_id
            file_type = "Photo"
            file_name += ".jpg"
        elif message.video:
            file_id = message.video.file_id
            file_type = "Video"
            file_name = message.video.file_name or file_name + ".mp4"
        elif message.document:
            file_id = message.document.file_id
            file_type = "Document"
            file_name = message.document.file_name or file_name
        elif message.audio:
            file_id = message.audio.file_id
            file_type = "Audio"
            file_name += ".mp3"
        elif message.voice:
            file_id = message.voice.file_id
            file_type = "Voice"
            file_name += ".ogg"
        elif message.sticker:
            file_id = message.sticker.file_id
            file_type = "Sticker"
            file_name += ".webp"
        elif message.animation:
            file_id = message.animation.file_id
            file_type = "GIF"
            file_name += ".gif"
        if not file_id:
            await msg.edit_text("❌ Unsupported")
            return
        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url)
        link = await upload_to_catbox(r.content, file_name)
        if link:
            with sqlite3.connect("data/bot.db") as conn:
                conn.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,))
                conn.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
                cult = conn.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,)).fetchone()
                if cult and cult[0] != 'none':
                    conn.execute("UPDATE users SET sacrifices = sacrifices + 1 WHERE user_id = ?", (user.id,))
                conn.commit()
            await msg.edit_text(f"✅ {file_type} uploaded!\n🔗 <code>{link}</code>", parse_mode=ParseMode.HTML)
        else:
            await msg.edit_text("❌ Upload failed")
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

@dp.message(Command("convert"))
async def convert_cmd(message: Message):
    user, chat = await handle_common(message, "convert")
    if not user:
        return
    if not YTDLP_AVAILABLE:
        await message.answer("❌ yt-dlp not installed!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📥 Usage: /convert [URL]")
        return
    url = args[1]
    msg = await message.answer("📥 <b>Downloading...</b>", parse_mode=ParseMode.HTML)
    try:
        def download():
            ydl_opts = {'outtmpl': 'temp/%(title)s.%(ext)s', 'format': 'best[ext=mp4]/best', 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        filename = await asyncio.to_thread(download)
        if not filename or not os.path.exists(filename):
            await msg.edit_text("❌ Failed")
            return
        with open(filename, 'rb') as f:
            data = f.read()
        link = await upload_to_catbox(data, os.path.basename(filename))
        if link:
            await msg.edit_text(f"✅ <code>{link}</code>", parse_mode=ParseMode.HTML)
        else:
            await msg.edit_text("❌ Upload failed")
        os.remove(filename)
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

# ========== ADMIN COMMANDS ==========
@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    user, chat = await handle_common(message, "ping")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    start = time.perf_counter()
    msg = await message.answer("🏓 <b>Testing...</b>", parse_mode=ParseMode.HTML)
    latency = int((time.perf_counter() - start) * 1000)
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    uptime = format_uptime(int(time.time() - start_time))
    await msg.edit_text(
        f"{ArtStyle.header('SYSTEM STATUS')}\n"
        f"⚡ Latency: {latency}ms\n"
        f"🕒 Uptime: {uptime}\n"
        f"💻 CPU: {cpu}%\n"
        f"💾 RAM: {ram}%\n"
        f"💿 Disk: {disk}%",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    user, chat = await handle_common(message, "stats")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM uploads")
        uploads = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM wishes")
        wishes = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
        tempest = c.fetchone()[0]
    await message.answer(
        f"{ArtStyle.header('STATISTICS')}\n"
        f"👥 Users: {users}\n"
        f"📁 Uploads: {uploads}\n"
        f"✨ Wishes: {wishes}\n"
        f"🌀 Tempest: {tempest}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("scan"))
async def scan_cmd(message: Message):
    user, chat = await handle_common(message, "scan")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM command_logs")
        cmds = c.fetchone()[0]
    await message.answer(f"🔍 Users: {users}\n🔧 Commands logged: {cmds}\n✅ Scan complete!")

@dp.message(Command("users"))
async def users_cmd(message: Message):
    user, chat = await handle_common(message, "users")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, first_name, uploads, commands FROM users ORDER BY commands DESC LIMIT 20")
        users = c.fetchall()
    text = f"{ArtStyle.header('TOP USERS')}\n"
    for uid, name, up, cmds in users:
        text += f"• {name} ({uid}) - 📁{up} 🔧{cmds}\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    broadcast_state[user.id] = {"step": 1}
    await message.answer("📢 <b>Send me text, photo, video, or document to broadcast!</b>", parse_mode=ParseMode.HTML)

@dp.message(F.text | F.photo | F.video | F.document)
async def handle_broadcast(message: Message):
    user = message.from_user
    if user.id not in broadcast_state:
        return
    broadcast_state.pop(user.id, None)
    if message.text and message.text.startswith("/"):
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned = 0")
        users = c.fetchall()
    status = await message.answer(f"📤 Broadcasting to {len(users)}...")
    success = 0
    for (uid,) in users:
        try:
            caption = message.caption or ""
            if message.photo:
                try:
                    await bot.send_photo(uid, message.photo[-1].file_id, caption=caption, parse_mode=ParseMode.HTML)
                except:
                    await bot.send_photo(uid, message.photo[-1].file_id, caption=caption)
            elif message.video:
                try:
                    await bot.send_video(uid, message.video.file_id, caption=caption, parse_mode=ParseMode.HTML)
                except:
                    await bot.send_video(uid, message.video.file_id, caption=caption)
            elif message.document:
                await bot.send_document(uid, message.document.file_id, caption=caption)
            elif message.text:
                await bot.send_message(uid, message.text)
            success += 1
        except:
            pass
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ Sent to {success}/{len(users)}")

@dp.message(Command("lag"))
async def lag_cmd(message: Message):
    user, chat = await handle_common(message, "lag")
    if not user:
        return
    args = message.text.split()
    duration = 5
    if len(args) > 1 and args[1].isdigit():
        duration = min(int(args[1]), 15)
    msg = await message.answer("🤖 <b>Glitching...</b>", parse_mode=ParseMode.HTML)
    for i in range(duration):
        progress = "▓" * (i + 1) + "░" * (duration - i - 1)
        try:
            await msg.edit_text(f"⚡ [{progress}] {i+1}/{duration}s", parse_mode=ParseMode.HTML)
        except:
            pass
        await asyncio.sleep(1.3)
    await msg.edit_text("✅ <b>Recovered!</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("disable"))
async def disable_cmd(message: Message):
    user, chat = await handle_common(message, "disable")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /disable [command] [minutes]")
        return
    cmd = args[1].replace("/", "")
    duration = 10
    if len(args) > 2 and args[2].isdigit():
        duration = int(args[2])
    disabled_commands[cmd] = datetime.now() + timedelta(minutes=duration)
    await message.answer(f"⛔ {cmd} disabled for {duration} minutes!")

# ========== OWNER COMMANDS ==========
@dp.message(Command("query"))
async def query_cmd(message: Message):
    user, chat = await handle_common(message, "query")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer(f"🚫 Owner only. Your ID: {user.id}")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚡ Usage: /query [code]")
        return
    code = args[1]
    msg = await message.answer("⚡ Executing...")
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(code)
        output = buf.getvalue() or "No output"
        await msg.edit_text(f"✅ <code>{output[:3000]}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

@dp.message(Command("maintenance"))
async def maintenance_cmd(message: Message):
    global maintenance_mode
    user, chat = await handle_common(message, "maintenance")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer(f"🚫 Owner only. Your ID: {user.id}")
        return
    maintenance_mode = not maintenance_mode
    await message.answer(f"⚙️ Maintenance: {'🔴 ON' if maintenance_mode else '🟢 OFF'}")

@dp.message(Command("clearlogs"))
async def clearlogs_cmd(message: Message):
    user, chat = await handle_common(message, "clearlogs")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer(f"🚫 Owner only. Your ID: {user.id}")
        return
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("DELETE FROM command_logs")
        conn.execute("DELETE FROM error_logs")
        conn.commit()
    await message.answer("🧹 Logs cleared!")

@dp.message(Command("logs"))
async def logs_cmd(message: Message):
    user, chat = await handle_common(message, "logs")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer(f"🚫 Owner only. Your ID: {user.id}")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT timestamp, user_id, command FROM command_logs ORDER BY id DESC LIMIT 20")
        logs = c.fetchall()
    text = f"{ArtStyle.header('RECENT LOGS')}\n"
    for ts, uid, cmd in logs:
        text += f"• {ts[:19]} | {uid} | /{cmd}\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("pro"))
async def pro_cmd(message: Message):
    user, chat = await handle_common(message, "pro")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer(f"🚫 Owner only. Your ID: {user.id}")
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Usage: /pro [user_id]")
        return
    target_id = int(args[1])
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (target_id,))
        conn.commit()
    await message.answer(f"✅ User {target_id} is now admin!")

@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    user, chat = await handle_common(message, "backup")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer(f"🚫 Owner only. Your ID: {user.id}")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/backup_{timestamp}.db"
    shutil.copy2("data/bot.db", backup_file)
    await message.answer_document(FSInputFile(backup_file))
    os.remove(backup_file)

@dp.message(Command("rem"))
async def rem_cmd(message: Message):
    user, chat = await handle_common(message, "rem")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer(f"🚫 Owner only. Your ID: {user.id}")
        return
    pending_restore[user.id] = True
    await message.answer("💾 Upload .db file to restore!")

@dp.message(F.document)
async def handle_restore(message: Message):
    user = message.from_user
    if user.id not in pending_restore:
        return
    pending_restore.pop(user.id, None)
    if not message.document.file_name.endswith('.db'):
        await message.answer("❌ Please upload .db file!")
        return
    msg = await message.answer("⏳ Restoring...")
    try:
        file = await bot.get_file(message.document.file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
        temp_file = f"temp/restore_{user.id}.db"
        with open(temp_file, 'wb') as f:
            f.write(r.content)
        shutil.copy2("data/bot.db", f"backups/pre_restore_{int(time.time())}.db")
        shutil.copy2(temp_file, "data/bot.db")
        os.remove(temp_file)
        init_db()
        await msg.edit_text("✅ Database restored!")
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    user, chat = await handle_common(message, "restart")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer(f"🚫 Owner only. Your ID: {user.id}")
        return
    await message.answer("🔄 Restarting...")
    os.execv(sys.executable, ['python'] + sys.argv)

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user, chat = await handle_common(message, "cancel")
    if not user:
        return
    cancelled = False
    if user.id in upload_waiting:
        upload_waiting.pop(user.id, None)
        cancelled = True
    if user.id in broadcast_state:
        broadcast_state.pop(user.id, None)
        cancelled = True
    if user.id in pending_restore:
        pending_restore.pop(user.id, None)
        cancelled = True
    if cancelled:
        await message.answer("❌ Cancelled!")
    else:
        await message.answer("Nothing to cancel")

# ========== MAIN ==========
async def main():
    print("🚀 Starting bot...")
    await send_log("🚀 Bot started!")
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())