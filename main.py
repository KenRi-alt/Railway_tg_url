#!/usr/bin/env python3
# ========== TEMPEST BOT - FINAL COMPLETE ==========
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
from datetime import datetime, timedelta
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, CallbackQuery, BufferedInputFile
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError

# Timezone support
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

print("=" * 60)
print("🌀 TEMPEST BOT - FINAL COMPLETE")
print("✅ All systems operational")
print("=" * 60)

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = 6108185460  # YOUR ID
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845

# Try yt-dlp
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

# Create directories
for dir_name in ["data", "temp", "backups", "profile_cards", "fonts"]:
    Path(dir_name).mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True
upload_waiting = {}
broadcast_state = {}
pending_restore = {}
disabled_commands = {}
maintenance_mode = False

# ========== ART STYLE ==========
class ArtStyle:
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
    "「The concept of hope is nothing more than giving up. A word that holds no true meaning.」\n— Madara Uchiha",
    "「When a man learns to love, he must bear the risk of hatred.」\n— Madara Uchiha",
    "「Those who cannot acknowledge themselves will eventually fail.」\n— Itachi Uchiha",
    "「It is not wise to judge others based on your own preconceptions and by their appearances.」\n— Itachi Uchiha",
    "「People's lives don't end when they die. It ends when they lose faith.」\n— Itachi Uchiha",
    "「If you want to know who you are, you have to look at your real self and acknowledge what you see.」\n— Itachi Uchiha",
    "「The only thing we're allowed to do is to believe that we won't regret the choice we made.」\n— Levi Ackerman",
    "「I can win as long as I don't know defeat.」\n— Rantaro Amami",
    "「If you don't want to be betrayed anymore, then start by not trusting people.」\n— Rantaro Amami",
    "「Even if I die, I'll protect my comrades.」\n— Roronoa Zoro",
    "「When you're hungry, eat. When you're tired, sleep.」\n— Roronoa Zoro",
    "「Fear is not evil. It tells you what your weakness is.」\n— Gildarts Clive",
    "「A lesson without pain is meaningless.」\n— Edward Elric",
    "「Nothing's perfect, the world's not perfect, but it's there for us, trying the best it can.」\n— Roy Mustang",
    "「If you don't take risks, you can't create a future.」\n— Monkey D. Luffy",
    "「Power isn't determined by your size, but by the size of your heart and dreams.」\n— Monkey D. Luffy",
    "「When do you think people die? When they are shot? No. When they are forgotten.」\n— Dr. Hiluluk",
    "「The world isn't perfect. But it's there for us, doing the best it can. That's what makes it so damn beautiful.」\n— Roy Mustang",
]

# ========== COUNTRY TIMEZONES ==========
COUNTRY_TIMEZONES = {
    "usa": "America/New_York",
    "uk": "Europe/London",
    "india": "Asia/Kolkata",
    "japan": "Asia/Tokyo",
    "china": "Asia/Shanghai",
    "russia": "Europe/Moscow",
    "brazil": "America/Sao_Paulo",
    "australia": "Australia/Sydney",
    "canada": "America/Toronto",
    "germany": "Europe/Berlin",
    "france": "Europe/Paris",
    "italy": "Europe/Rome",
    "spain": "Europe/Madrid",
    "mexico": "America/Mexico_City",
    "south korea": "Asia/Seoul",
    "indonesia": "Asia/Jakarta",
    "pakistan": "Asia/Karachi",
    "bangladesh": "Asia/Dhaka",
    "nigeria": "Africa/Lagos",
    "egypt": "Africa/Cairo",
    "south africa": "Africa/Johannesburg",
    "kenya": "Africa/Nairobi",
    "uganda": "Africa/Kampala",
    "tanzania": "Africa/Dar_es_Salaam",
    "ethiopia": "Africa/Addis_Ababa",
    "ghana": "Africa/Accra",
    "uae": "Asia/Dubai",
    "saudi arabia": "Asia/Riyadh",
    "turkey": "Europe/Istanbul",
    "thailand": "Asia/Bangkok",
    "vietnam": "Asia/Ho_Chi_Minh",
    "philippines": "Asia/Manila",
    "malaysia": "Asia/Kuala_Lumpur",
    "singapore": "Asia/Singapore",
    "new zealand": "Pacific/Auckland",
    "argentina": "America/Argentina/Buenos_Aires",
    "chile": "America/Santiago",
    "colombia": "America/Bogota",
    "peru": "America/Lima",
    "sweden": "Europe/Stockholm",
    "norway": "Europe/Oslo",
    "denmark": "Europe/Copenhagen",
    "netherlands": "Europe/Amsterdam",
    "belgium": "Europe/Brussels",
    "switzerland": "Europe/Zurich",
    "austria": "Europe/Vienna",
    "poland": "Europe/Warsaw",
    "ukraine": "Europe/Kiev",
    "greece": "Europe/Athens",
    "portugal": "Europe/Lisbon",
    "ireland": "Europe/Dublin",
    "scotland": "Europe/London",
    "wales": "Europe/London",
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
            curse_type TEXT DEFAULT 'none'
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS groups (
            group_id INTEGER PRIMARY KEY,
            title TEXT,
            joined_date TEXT,
            last_active TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            file_url TEXT,
            file_type TEXT
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
    except Exception as e:
        print(f"Log error: {e}")

# ========== HELPERS ==========
async def handle_common(message: Message, command: str):
    user = message.from_user
    chat = message.chat
    
    if maintenance_mode and user.id != OWNER_ID:
        await message.answer("🔧 Bot under maintenance!")
        return None, None
    
    if command in disabled_commands and disabled_commands[command] > datetime.now():
        await message.answer("⛔ Command disabled!")
        return None, None
    
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE user_id = ?", (user.id,))
            if not c.fetchone():
                c.execute("INSERT INTO users (user_id, username, first_name, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                         (user.id, user.username, user.first_name, datetime.now().isoformat(), datetime.now().isoformat()))
            else:
                c.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (datetime.now().isoformat(), user.id))
            conn.commit()
    except:
        pass
    
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("INSERT INTO command_logs (timestamp, user_id, chat_id, command, success) VALUES (?, ?, ?, ?, 1)",
                     (datetime.now().isoformat(), user.id, chat.id, command))
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
            result = c.fetchone()
        return result and result[0] == 1
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

# ========== 3X SUPER-SAMPLED PROFILE CARD ==========
class PremiumProfileCard:
    @staticmethod
    def generate_card_sync(username, user_id, rank, avatar_bytes=None, stats=None, is_couple=False, person2=None):
        scale = 3
        base_w, base_h = 900, 520
        w, h = base_w * scale, base_h * scale
        
        # Deep dark blue background
        img = Image.new("RGBA", (w, h), (7, 11, 22, 255))
        draw = ImageDraw.Draw(img)
        
        # Subtle grid
        for x in range(0, w, 40*scale):
            draw.line([(x, 0), (x, h)], fill=(20, 30, 50, 40), width=1)
        for y in range(0, h, 40*scale):
            draw.line([(0, y), (w, y)], fill=(20, 30, 50, 40), width=1)
        
        # Border
        draw.rectangle([15*scale, 15*scale, w-15*scale, h-15*scale], outline=(30, 90, 160, 180), width=3*scale)
        
        # Load fonts
        try:
            font_title = ImageFont.truetype("fonts/DejaVuSans-Bold.ttf", 36*scale)
            font_body = ImageFont.truetype("fonts/DejaVuSans.ttf", 20*scale)
            font_small = ImageFont.truetype("fonts/DejaVuSans.ttf", 14*scale)
        except:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
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
        
        # Circular mask
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        
        # Glow ring
        draw.ellipse([avatar_x-5*scale, avatar_y-5*scale, avatar_x+avatar_size+5*scale, avatar_y+avatar_size+5*scale],
                    outline=(0, 255, 200, 255), width=4*scale)
        
        img.paste(avatar_img, (avatar_x, avatar_y), mask)
        
        # Text
        if is_couple and person2:
            draw.text((280*scale, 70*scale), f"{username} 💘 {person2}", fill=(255, 255, 255, 255), font=font_title)
            draw.text((280*scale, 130*scale), "FATE PAIR", fill=(0, 190, 255, 255), font=font_body)
        else:
            draw.text((280*scale, 70*scale), username, fill=(255, 255, 255, 255), font=font_title)
            draw.text((280*scale, 130*scale), f"ID: {user_id}", fill=(180, 190, 210, 255), font=font_body)
            draw.text((280*scale, 170*scale), f"Rank: {rank}", fill=(0, 255, 200, 255), font=font_body)
        
        if stats:
            stats_text = f"Uploads: {stats.get('uploads', 0)} | Wishes: {stats.get('wishes', 0)}"
            draw.text((280*scale, 220*scale), stats_text, fill=(255, 215, 0, 255), font=font_body)
        
        # Downscale with LANCZOS
        final = img.resize((base_w, base_h), Image.Resampling.LANCZOS)
        
        buf = io.BytesIO()
        final.save(buf, format="PNG", quality=100)
        buf.seek(0)
        return buf.getvalue()
    
    @staticmethod
    async def generate_card(username, user_id, rank, avatar_bytes=None, stats=None, is_couple=False, person2=None):
        return await asyncio.to_thread(
            PremiumProfileCard.generate_card_sync,
            username, user_id, rank, avatar_bytes, stats, is_couple, person2
        )

# ========== TEMPEST FATE CARD ==========
def create_tempest_fate_card(name1, name2, percentage, quote):
    scale = 3
    base_w, base_h = 900, 450
    w, h = base_w * scale, base_h * scale
    
    img = Image.new("RGBA", (w, h), (7, 11, 22, 255))
    draw = ImageDraw.Draw(img)
    
    # Subtle symbols
    symbol_color = (35, 65, 105, 90)
    for x in range(120, w, 180):
        for y in range(80, h, 140):
            size = 8 * scale
            draw.line([(x - size, y), (x + size, y)], fill=symbol_color, width=1)
            draw.line([(x, y - size), (x, y + size)], fill=symbol_color, width=1)
    
    # Border
    draw.rectangle([15*scale, 15*scale, w-15*scale, h-15*scale], outline=(30, 90, 160, 180), width=2*scale)
    
    # Fonts
    try:
        font_massive = ImageFont.truetype("fonts/DejaVuSans-Bold.ttf", 48*scale)
        font_sub = ImageFont.truetype("fonts/DejaVuSans.ttf", 14*scale)
        font_name = ImageFont.truetype("fonts/DejaVuSans-Bold.ttf", 20*scale)
    except:
        font_massive = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_name = ImageFont.load_default()
    
    # Massive text
    draw.text((105*scale, 60*scale), "TEMPEST", fill=(235, 245, 255, 255), font=font_massive)
    draw.text((105*scale, 130*scale), "FATE", fill=(0, 190, 255, 255), font=font_massive)
    
    # Names
    draw.text((110*scale, 220*scale), f"{name1} 💘 {name2}", fill=(255, 255, 255, 255), font=font_name)
    draw.text((110*scale, 260*scale), f"{percentage}% LOVE", fill=(255, 100, 150, 255), font=font_name)
    
    # Anime quote
    draw.text((110*scale, 310*scale), "— THE STORM AWAKENS —", fill=(120, 150, 190, 255), font=font_sub)
    
    # Downscale
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
        f"✨ Welcome {user.first_name}!\n\n"
        f"/help - All commands\n/profile - Your stats\n/wish - Make wish\n/tempest_join - Join cult"
    )

@dp.message(Command("myid"))
async def myid_cmd(message: Message):
    await message.answer(
        f"🆔 Your ID: <code>{message.from_user.id}</code>\n"
        f"👑 Owner ID: <code>{OWNER_ID}</code>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    user, chat = await handle_common(message, "help")
    if not user:
        return
    await message.answer(
        f"{ArtStyle.header('COMMANDS')}\n"
        f"🔗 /link - Upload file\n"
        f"📥 /convert - Convert media\n"
        f"✨ /wish - Make wish\n"
        f"🔮 /fortune - See future\n"
        f"🎮 /dice - Roll dice\n"
        f"🪙 /flip - Flip coin\n"
        f"💑 /fate - Find love\n"
        f"👤 /profile - Your stats\n"
        f"🔐 /encrypt - Encrypt msg\n"
        f"🌀 /tempest_join - Join cult\n"
        f"📜 /tempest_story - Read lore\n"
        f"🌍 /time [country] - World time\n"
        f"📝 /word - Text to DOCX"
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
        f"/ping - System status\n/stats - Stats\n/users - User list\n"
        f"/scan - Scan DB\n/broadcast - Message all\n/disable - Disable cmd\n"
        f"/lag - Glitch effect\n\n"
        f"👑 OWNER:\n/pro - Make admin\n/backup - Backup DB\n"
        f"/rem - Restore DB\n/restart - Reboot\n/query - Execute code\n"
        f"/maintenance - Toggle maintenance\n/clearlogs - Clear logs\n"
        f"/logs - View recent logs"
    )

# ========== TIME COMMAND ==========
@dp.message(Command("time"))
async def time_cmd(message: Message):
    user, chat = await handle_common(message, "time")
    if not user:
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            f"🌍 <b>Usage:</b> /time [country]\n"
            f"Example: /time japan\n\n"
            f"<b>Available countries:</b>\n"
            f"{', '.join(list(COUNTRY_TIMEZONES.keys())[:20])}...",
            parse_mode=ParseMode.HTML
        )
        return
    
    country = args[1].lower().strip()
    
    if country not in COUNTRY_TIMEZONES:
        await message.answer(f"❌ Country not found! Use /time for list.")
        return
    
    tz_name = COUNTRY_TIMEZONES[country]
    
    try:
        if ZoneInfo:
            tz = ZoneInfo(tz_name)
            current_time = datetime.now(tz)
        else:
            # Fallback: use UTC offset approximation
            current_time = datetime.utcnow()
        
        await message.answer(
            f"🌍 <b>{country.upper()}</b>\n"
            f"🕐 <b>Time:</b> {current_time.strftime('%H:%M:%S')}\n"
            f"📅 <b>Date:</b> {current_time.strftime('%A, %d %B %Y')}\n"
            f"🌐 <b>Timezone:</b> {tz_name}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")

# ========== FORTUNE ==========
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
        c = conn.cursor()
        c.execute("INSERT INTO fortunes (user_id, timestamp, fortune_text) VALUES (?, ?, ?)",
                 (user.id, datetime.now().isoformat(), fortune_text))
        conn.commit()
    
    await msg.edit_text(
        f"{ArtStyle.header('YOUR FORTUNE')}\n"
        f"<i>\"{fortune_text}\"</i>\n\n"
        f"{ArtStyle.divider()}\n"
        f"🌀 <i>The tempest has spoken...</i>",
        parse_mode=ParseMode.HTML
    )

# ========== FATE WITH CARD & QUOTE ==========
@dp.message(Command("fate"))
async def fate_cmd(message: Message):
    user, chat = await handle_common(message, "fate")
    if not user:
        return
    
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("💑 This command works only in groups!")
        return
    
    # Check 24h lock
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
                "<i>Fate has already decided! Try again in 24 hours.</i>",
                parse_mode=ParseMode.HTML
            )
            return
        
        c.execute("SELECT DISTINCT u.user_id, u.first_name FROM users u WHERE u.user_id IN (SELECT user_id FROM command_logs WHERE chat_id = ?) AND u.is_banned = 0 LIMIT 100",
                 (chat.id,))
        members = c.fetchall()
    
    if len(members) < 2:
        await message.answer("❌ Not enough members! Need at least 2 active users.")
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
    
    love_percentage = random.randint(50, 100)
    quote = random.choice(ANIME_QUOTES)
    
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO fate_pairs (chat_id, user1_id, user1_name, user2_id, user2_name, love_percentage, created_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (chat.id, lover1[0], lover1[1], lover2[0], lover2[1], love_percentage, datetime.now().isoformat()))
        conn.commit()
    
    # Generate Fate Card
    card_bytes = await asyncio.to_thread(
        create_tempest_fate_card,
        lover1[1], lover2[1], love_percentage, quote
    )
    
    await msg.delete()
    await message.answer_photo(
        photo=BufferedInputFile(card_bytes, filename="fate_card.png"),
        caption=(
            f"💑 <b>COUPLE OF THE STORM</b>\n\n"
            f"💘 <b>{lover1[1]}</b> & <b>{lover2[1]}</b>\n"
            f"💖 <b>Love:</b> {love_percentage}%\n\n"
            f"📜 <i>{quote}</i>"
        ),
        parse_mode=ParseMode.HTML
    )

# ========== PROFILE ==========
@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user, chat = await handle_common(message, "profile")
    if not user:
        return
    
    msg = await message.answer("🎨 <b>Generating profile...</b>", parse_mode=ParseMode.HTML)
    
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT uploads, commands, curse_type, cult_rank, sacrifices FROM users WHERE user_id = ?", (user.id,))
        row = c.fetchone()
        if row:
            uploads, cmds, curse_type, cult_rank, sacrifices = row
            c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (user.id,))
            wishes = c.fetchone()[0]
        else:
            uploads = cmds = wishes = sacrifices = 0
            curse_type = "none"
            cult_rank = "none"
    
    avatar_bytes = None
    try:
        user_photos = await bot.get_user_profile_photos(user.id, limit=1)
        if user_photos.total_count > 0:
            file_id = user_photos.photos[0][-1].file_id
            file_info = await bot.get_file(file_id)
            downloaded = await bot.download_file(file_info.file_path)
            avatar_bytes = downloaded.read()
    except:
        pass
    
    stats = {'uploads': uploads, 'wishes': wishes}
    rank = cult_rank if cult_rank != "none" else "Mortal"
    
    card_bytes = await PremiumProfileCard.generate_card(
        username=user.first_name,
        user_id=user.id,
        rank=rank,
        avatar_bytes=avatar_bytes,
        stats=stats
    )
    
    await msg.delete()
    await message.answer_photo(
        photo=BufferedInputFile(card_bytes, filename=f"profile_{user.id}.png"),
        caption=f"👤 <b>{user.first_name}</b>\n🌀 Tempest Profile",
        parse_mode=ParseMode.HTML
    )

# ========== WISH ==========
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
    
    if luck >= 90: result = "🎊 EXCELLENT!"
    elif luck >= 70: result = "😊 VERY GOOD!"
    elif luck >= 50: result = "👍 GOOD!"
    elif luck >= 30: result = "🤔 AVERAGE"
    elif luck >= 10: result = "😟 LOW"
    else: result = "💀 VERY LOW"
    
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
                 (user.id, datetime.now().isoformat(), args[1], luck))
        conn.commit()
    
    await msg.edit_text(
        f"{ArtStyle.header('WISH RESULT')}\n"
        f"📜 Wish: {args[1][:100]}\n"
        f"🎰 Luck: {stars} {luck}%\n"
        f"📊 Verdict: {result}",
        parse_mode=ParseMode.HTML
    )

# ========== DICE ==========
@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    user, chat = await handle_common(message, "dice")
    if not user:
        return
    await message.answer_dice(emoji="🎲")

# ========== FLIP ==========
@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    user, chat = await handle_common(message, "flip")
    if not user:
        return
    
    msg = await message.answer("🪙 <b>Flipping...</b>", parse_mode=ParseMode.HTML)
    
    for _ in range(3):
        await asyncio.sleep(0.4)
        await msg.edit_text("🪙 <b>Flipping...</b>", parse_mode=ParseMode.HTML)
    
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}!</b>", parse_mode=ParseMode.HTML)

# ========== CONVERT (Bulletproof) ==========
@dp.message(Command("convert"))
async def convert_cmd(message: Message):
    user, chat = await handle_common(message, "convert")
    if not user:
        return
    
    args = message.text.split(maxsplit=1)
    
    # Check for reply to media
    if message.reply_to_message and message.reply_to_message.photo:
        status_msg = await message.answer("🔄 <b>Processing image...</b>", parse_mode=ParseMode.HTML)
        try:
            file_id = message.reply_to_message.photo[-1].file_id
            file = await bot.get_file(file_id)
            url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
            
            if response.status_code == 200:
                # Upload to catbox
                result = await upload_to_catbox(response.content, f"converted_{user.id}.jpg")
                if result['success']:
                    await status_msg.edit_text(
                        f"✅ <b>Image processed!</b>\n🔗 <code>{result['url']}</code>",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await status_msg.edit_text("❌ Upload failed")
            else:
                await status_msg.edit_text("❌ Failed to download image")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {str(e)}")
        return
    
    # Check for URL argument
    if len(args) < 2:
        await message.answer(
            "📥 <b>Usage:</b>\n"
            "• /convert [URL] - Download media\n"
            "• Reply to a photo with /convert - Process image",
            parse_mode=ParseMode.HTML
        )
        return
    
    if not YTDLP_AVAILABLE:
        await message.answer("❌ yt-dlp not installed!")
        return
    
    url = args[1]
    msg = await message.answer("📥 <b>Downloading...</b>", parse_mode=ParseMode.HTML)
    
    try:
        def download():
            ydl_opts = {
                'outtmpl': 'temp/%(title)s.%(ext)s',
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        
        filename = await asyncio.to_thread(download)
        
        if not filename or not os.path.exists(filename):
            await msg.edit_text("❌ Download failed")
            return
        
        await msg.edit_text("📤 <b>Uploading...</b>", parse_mode=ParseMode.HTML)
        
        with open(filename, 'rb') as f:
            file_data = f.read()
        
        result = await upload_to_catbox(file_data, os.path.basename(filename))
        
        if result['success']:
            await msg.edit_text(f"✅ <b>Success!</b>\n🔗 <code>{result['url']}</code>", parse_mode=ParseMode.HTML)
        else:
            await msg.edit_text("❌ Upload failed")
        
        os.remove(filename)
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")

# ========== LINK/UPLOAD ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")
    if not user:
        return
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 Upload files in private chat only")
        return
    upload_waiting[user.id] = True
    await message.answer("📁 <b>Send me any file now!</b>\n❌ /cancel to stop", parse_mode=ParseMode.HTML)

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
        file_name = f"file_{user.id}_{int(time.time())}"
        
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
            await msg.edit_text("❌ Unsupported file type")
            return
        
        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
        
        if response.status_code != 200:
            await msg.edit_text("❌ Failed to download")
            return
        
        await msg.edit_text("📤 <b>Uploading...</b>", parse_mode=ParseMode.HTML)
        
        result = await upload_to_catbox(response.content, file_name)
        
        if not result['success']:
            await msg.edit_text("❌ Upload failed")
            return
        
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,))
            c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
            cult = c.fetchone()
            if cult and cult[0] != 'none':
                c.execute("UPDATE users SET sacrifices = sacrifices + 1 WHERE user_id = ?", (user.id,))
            c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type) VALUES (?, ?, ?, ?)",
                     (user.id, datetime.now().isoformat(), result['url'], file_type))
            conn.commit()
        
        size_kb = len(response.content) / 1024
        size_text = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
        
        await msg.edit_text(
            f"✅ <b>Upload Complete!</b>\n"
            f"📁 Type: {file_type}\n"
            f"💾 Size: {size_text}\n\n"
            f"🔗 <code>{result['url']}</code>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")

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
        await message.answer("⚡ Usage: /query [python code]")
        return
    
    code = args[1]
    msg = await message.answer("⚡ <b>Executing...</b>", parse_mode=ParseMode.HTML)
    
    stdout_buffer = io.StringIO()
    indented = "\n".join(f"    {line}" for line in code.splitlines())
    wrapped = f"async def __q():\n{indented}"
    
    sandbox = {'bot': bot, 'dp': dp, 'message': message, 'user': user,
               'asyncio': asyncio, 'sqlite3': sqlite3, 'datetime': datetime,
               'os': os, 'sys': sys, 'time': time, 'random': random, 'json': json, 'httpx': httpx}
    
    try:
        with contextlib.redirect_stdout(stdout_buffer):
            exec(wrapped, sandbox)
            result = await asyncio.wait_for(sandbox['__q'](), timeout=15)
        
        output = stdout_buffer.getvalue() or str(result) or "No output"
        await msg.edit_text(f"✅ <b>Output:</b>\n<code>{output[:3000]}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.edit_text(f"❌ <b>Error:</b>\n<code>{traceback.format_exc()[-1000:]}</code>", parse_mode=ParseMode.HTML)

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
    status = "🔴 ENABLED" if maintenance_mode else "🟢 DISABLED"
    await message.answer(f"⚙️ Maintenance mode: {status}")

@dp.message(Command("clearlogs"))
async def clearlogs_cmd(message: Message):
    user, chat = await handle_common(message, "clearlogs")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer(f"🚫 Owner only. Your ID: {user.id}")
        return
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("DELETE FROM command_logs")
            c.execute("DELETE FROM error_logs")
            conn.commit()
        await message.answer("🧹 Logs cleared!")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

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
        cmd_logs = c.fetchall()
        c.execute("SELECT timestamp, error FROM error_logs ORDER BY id DESC LIMIT 10")
        err_logs = c.fetchall()
    
    text = f"{ArtStyle.header('RECENT LOGS')}\n\n<b>COMMANDS:</b>\n"
    for ts, uid, cmd in cmd_logs:
        text += f"• {ts[:19]} | {uid} | /{cmd}\n"
    
    if err_logs:
        text += "\n<b>ERRORS:</b>\n"
        for ts, err in err_logs:
            text += f"• {ts[:19]} | {err[:50]}\n"
    
    await message.answer(text[:4000], parse_mode=ParseMode.HTML)

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
        await message.answer("Usage: /pro user_id")
        return
    target_id = int(args[1])
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (target_id,))
        if c.rowcount == 0:
            c.execute("INSERT INTO users (user_id, first_name, is_admin) VALUES (?, 'Admin', 1)", (target_id,))
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
    await message.answer_document(FSInputFile(backup_file), caption=f"💾 Backup {timestamp}")
    os.remove(backup_file)

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

# ========== LAG (Bulletproof) ==========
@dp.message(Command("lag"))
async def lag_cmd(message: Message):
    user, chat = await handle_common(message, "lag")
    if not user:
        return
    
    args = message.text.split()
    duration = 5
    if len(args) > 1 and args[1].isdigit():
        duration = min(int(args[1]), 15)
    
    msg = await message.answer("🤖 <b>Glitch simulation...</b>", parse_mode=ParseMode.HTML)
    
    for i in range(duration):
        progress = "▓" * (i + 1) + "░" * (duration - i - 1)
        try:
            await msg.edit_text(f"⚡ <b>LAG:</b> [{progress}] {i+1}/{duration}s", parse_mode=ParseMode.HTML)
        except:
            pass
        await asyncio.sleep(1.3)
    
    try:
        await msg.edit_text("✅ <b>System recovered!</b>", parse_mode=ParseMode.HTML)
    except:
        pass

# ========== BROADCAST ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    broadcast_state[user.id] = {"step": 1}
    await message.answer("📢 <b>Send me text, photo, or video to broadcast!</b>", parse_mode=ParseMode.HTML)

@dp.message(F.text | F.photo | F.video | F.document)
async def handle_broadcast(message: Message):
    user = message.from_user
    if user.id not in broadcast_state:
        return
    broadcast_state.pop(user.id, None)
    
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned = 0")
        users = c.fetchall()
    
    status = await message.answer(f"📤 Broadcasting to {len(users)} users...")
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
            await asyncio.sleep(0.05)
        except:
            pass
    
    await status.edit_text(f"✅ Sent to {success}/{len(users)} users")

# ========== MAIN ==========
async def main():
    print("🚀 Starting bot...")
    await send_log("🚀 Bot started!")
    
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            print(f"Connection lost: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()