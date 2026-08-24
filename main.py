#!/usr/bin/env python3
# ========== TEMPEST BOT - COMPLETE ==========
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

print("=" * 60)
print("TEMPEST BOT - COMPLETE")
print("=" * 60)

# ========== CONFIG ==========
BOT_TOKEN = "8017048722:AAGs1HNsyX-UobN6PVq7u4iPMxGnOX14AAg"
OWNER_ID = 6108185460
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except:
    YTDLP_AVAILABLE = False

try:
    from zoneinfo import ZoneInfo
except:
    ZoneInfo = None

for d in ["data", "temp", "backups", "fonts"]:
    Path(d).mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
upload_waiting = {}
broadcast_state = {}
pending_restore = {}
disabled_commands = {}
maintenance_mode = False

# ========== ART STYLE ==========
def header(t):
    return f"◤━━━━━━━━━━━━━━━━━━━━◥\n◇ {t} ◇\n◣━━━━━━━━━━━━━━━━━━━━◢"

def divider():
    return "━━━━━━━━━━━━━━━━━━━━"

# ========== ANIME QUOTES ==========
ANIME_QUOTES = [
    "「Wake up to reality! Nothing ever goes as planned in this accursed world.」\n— Madara Uchiha",
    "「The longer you live, the more you realize that reality is just made of pain.」\n— Madara Uchiha",
    "「People cannot show each other their true feelings.」\n— Madara Uchiha",
    "「The only thing we're allowed to do is believe we won't regret our choice.」\n— Levi Ackerman",
    "「If you don't take risks, you can't create a future.」\n— Monkey D. Luffy",
    "「Power isn't determined by your size, but by the size of your heart.」\n— Luffy",
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
    "south korea": "Asia/Seoul", "pakistan": "Asia/Karachi",
    "bangladesh": "Asia/Dhaka", "nigeria": "Africa/Lagos",
    "egypt": "Africa/Cairo", "south africa": "Africa/Johannesburg",
    "kenya": "Africa/Nairobi", "uganda": "Africa/Kampala",
    "uae": "Asia/Dubai", "saudi arabia": "Asia/Riyadh",
    "turkey": "Europe/Istanbul", "thailand": "Asia/Bangkok",
    "philippines": "Asia/Manila", "singapore": "Asia/Singapore",
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
        await message.answer("🔧 Maintenance!")
        return None, None
    
    if cmd in disabled_commands and disabled_commands[cmd] > datetime.now():
        await message.answer("⛔ Disabled!")
        return None, None
    
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date) VALUES (?, ?, ?, ?)",
                     (user.id, user.username or "", user.first_name or "", datetime.now().isoformat()))
            c.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (datetime.now().isoformat(), user.id))
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

# ========== CARD GENERATOR - LARGE TEXT ==========
def generate_profile_card(username, user_id, rank, uploads=0, wishes=0):
    w, h = 800, 400
    img = Image.new("RGB", (w, h), (10, 15, 30))
    draw = ImageDraw.Draw(img)
    
    for y in range(h):
        r = int(10 + 25 * (y/h))
        g = int(15 + 35 * (y/h))
        b = int(30 + 55 * (y/h))
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    
    draw.rectangle([10, 10, w-10, h-10], outline=(0, 200, 255), width=3)
    
    try:
        font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_info = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        try:
            font_name = ImageFont.truetype("arial.ttf", 36)
            font_info = ImageFont.truetype("arial.ttf", 24)
        except:
            font_name = ImageFont.load_default()
            font_info = ImageFont.load_default()
    
    draw.text((30, 40), username, fill=(255, 255, 255), font=font_name)
    draw.text((30, 90), f"ID: {user_id}", fill=(180, 200, 230), font=font_info)
    draw.text((30, 130), f"Rank: {rank}", fill=(0, 255, 200), font=font_info)
    draw.text((30, 170), f"Uploads: {uploads}  |  Wishes: {wishes}", fill=(255, 215, 0), font=font_info)
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def generate_fate_card(name1, name2, percentage, quote):
    w, h = 800, 500
    img = Image.new("RGB", (w, h), (10, 15, 30))
    draw = ImageDraw.Draw(img)
    
    for y in range(h):
        r = int(10 + 25 * (y/h))
        g = int(15 + 35 * (y/h))
        b = int(30 + 55 * (y/h))
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    
    draw.rectangle([10, 10, w-10, h-10], outline=(0, 200, 255), width=3)
    
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_quote = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        try:
            font_title = ImageFont.truetype("arial.ttf", 40)
            font_name = ImageFont.truetype("arial.ttf", 28)
            font_quote = ImageFont.truetype("arial.ttf", 18)
        except:
            font_title = ImageFont.load_default()
            font_name = ImageFont.load_default()
            font_quote = ImageFont.load_default()
    
    draw.text((w//2, 50), "TEMPEST FATE", fill=(0, 200, 255), font=font_title, anchor="mm")
    draw.text((w//2, 130), f"{name1}  💘  {name2}", fill=(255, 255, 255), font=font_name, anchor="mm")
    draw.text((w//2, 190), f"{percentage}% LOVE", fill=(255, 100, 150), font=font_name, anchor="mm")
    
    words = quote.split()
    lines = []
    current = ""
    for word in words:
        if len(current + word) < 50:
            current += word + " "
        else:
            lines.append(current.strip())
            current = word + " "
    if current:
        lines.append(current.strip())
    
    y_pos = 250
    for line in lines[:4]:
        draw.text((w//2, y_pos), line, fill=(200, 210, 230), font=font_quote, anchor="mm")
        y_pos += 30
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

# ========== BASIC COMMANDS ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = await handle_common(message, "start")
    if not user:
        return
    await message.answer(
        f"{header('TEMPEST BOT')}\n"
        f"✨ Welcome {user.first_name}!\n\n"
        f"/help - Commands"
    )
    await send_log(f"👤 {user.first_name} ({user.id}) started bot")

@dp.message(Command("myid"))
async def myid_cmd(message: Message):
    await message.answer(f"🆔 Your ID: <code>{message.from_user.id}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await handle_common(message, "help")
    await message.answer(
        f"{header('COMMANDS')}\n"
        f"🔗 /link - Upload\n"
        f"📥 /convert - Media URL\n"
        f"✨ /wish - Wish\n"
        f"🔮 /fortune - Future\n"
        f"🎮 /dice - Dice\n"
        f"🪙 /flip - Coin\n"
        f"💑 /fate - Love\n"
        f"👤 /profile - Stats\n"
        f"🔐 /encrypt - Encrypt\n"
        f"🔓 /decrypt - Decrypt\n"
        f"🌀 /tempest_join - Cult\n"
        f"📜 /tempest_story - Lore\n"
        f"🌀 /tempest_creed - Members\n"
        f"⛩️ /shrine - Shrine\n"
        f"⚡ /curse - Curse\n"
        f"⚡ /remove_curse - Uncurse\n"
        f"🌍 /time - World time\n"
        f"📝 /word - DOCX\n"
        f"🆔 /myid - Your ID\n"
        f"👑 /admin_help - Admin"
    )

@dp.message(Command("admin_help"))
async def admin_help_cmd(message: Message):
    user, chat = await handle_common(message, "admin_help")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    await message.answer(
        f"{header('ADMIN')}\n"
        f"/ping - Status\n/stats - Stats\n/scan - Scan\n"
        f"/users - Users\n/broadcast - Msg all\n"
        f"/lag - Glitch\n/disable - Disable\n\n"
        f"OWNER:\n/query - Code\n/backup - Backup\n"
        f"/rem - Restore\n/restart - Reboot\n/logs - Logs\n"
        f"/maintenance - Toggle\n/clearlogs - Clear\n/pro - Admin"
    )

# ========== FUN COMMANDS ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ Usage: /wish [text]")
        return
    msg = await message.answer("🔮 Reading...")
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
    await msg.edit_text(f"{header('WISH')}\n📜 {args[1][:100]}\n🎰 {stars} {luck}%\n📊 {verdict}")

@dp.message(Command("fortune"))
async def fortune_cmd(message: Message):
    user, chat = await handle_common(message, "fortune")
    if not user:
        return
    fortunes = [
        "🌟 Great things await you!",
        "🗝️ New doors will open!",
        "🦋 Beautiful changes coming!",
        "🌊 Adventure awaits!",
        "🔆 Success is near!",
        "🌠 A wish may come true!",
        "💕 Love will find you!",
        "📈 Promotion coming!",
        "🍀 Lucky week ahead!",
        "💪 You grow stronger!",
    ]
    msg = await message.answer("🔮 Reading...")
    await asyncio.sleep(1.5)
    f = random.choice(fortunes)
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("INSERT INTO fortunes (user_id, timestamp, fortune_text) VALUES (?, ?, ?)",
                    (user.id, datetime.now().isoformat(), f))
        conn.commit()
    await msg.edit_text(f"{header('FORTUNE')}\n<i>\"{f}\"</i>", parse_mode=ParseMode.HTML)

@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    await handle_common(message, "dice")
    await message.answer_dice(emoji="🎲")

@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    await handle_common(message, "flip")
    msg = await message.answer("🪙 Flipping...")
    await asyncio.sleep(0.5)
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}!</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("fate"))
async def fate_cmd(message: Message):
    user, chat = await handle_common(message, "fate")
    if not user:
        return
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("💑 Groups only!")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user1_name, user2_name, love_percentage FROM fate_pairs WHERE chat_id = ? AND created_date >= ?",
                 (chat.id, (datetime.now() - timedelta(hours=24)).isoformat()))
        existing = c.fetchone()
        if existing:
            await message.answer(f"💑 Today: {existing[0]} & {existing[1]} ({existing[2]}%)")
            return
        c.execute("SELECT user_id, first_name FROM users WHERE user_id != ? LIMIT 50", (user.id,))
        members = c.fetchall()
    if len(members) < 2:
        await message.answer("❌ Not enough members!")
        return
    msg = await message.answer("💫 Choosing...")
    await asyncio.sleep(2)
    l1 = random.choice(members)
    l2 = random.choice(members)
    while l2[0] == l1[0]:
        l2 = random.choice(members)
    love = random.randint(50, 100)
    quote = random.choice(ANIME_QUOTES)
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("INSERT INTO fate_pairs (chat_id, user1_id, user1_name, user2_id, user2_name, love_percentage, created_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (chat.id, l1[0], l1[1], l2[0], l2[1], love, datetime.now().isoformat()))
        conn.commit()
    card = await asyncio.to_thread(generate_fate_card, l1[1], l2[1], love, quote)
    await msg.delete()
    await message.answer_photo(
        photo=BufferedInputFile(card, filename="fate.png"),
        caption=f"💑 <b>{l1[1]} & {l2[1]}</b>\n💖 {love}% Love",
        parse_mode=ParseMode.HTML
    )

# ========== PROFILE ==========
@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user, chat = await handle_common(message, "profile")
    if not user:
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT uploads, commands, cult_rank, sacrifices, curse_type FROM users WHERE user_id = ?", (user.id,))
        r = c.fetchone()
        c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (user.id,))
        wishes = c.fetchone()[0]
    if r:
        uploads, cmds, rank, sacs, curse = r
    else:
        uploads = cmds = sacs = 0
        rank = "Mortal"
        curse = "none"
    card = await asyncio.to_thread(generate_profile_card, user.first_name, user.id, rank, uploads, wishes)
    await message.answer_photo(
        photo=BufferedInputFile(card, filename="profile.png"),
        caption=f"👤 <b>{user.first_name}</b>",
        parse_mode=ParseMode.HTML
    )

# ========== SECURITY ==========
@dp.message(Command("encrypt"))
async def encrypt_cmd(message: Message):
    await handle_common(message, "encrypt")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔐 Usage: /encrypt [text]")
        return
    enc = EncryptionEngine.encrypt(args[1])
    await message.answer(f"🔐 <code>{enc}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("decrypt"))
async def decrypt_cmd(message: Message):
    await handle_common(message, "decrypt")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔓 Usage: /decrypt [text]")
        return
    dec = EncryptionEngine.decrypt(args[1])
    if dec:
        await message.answer(f"🔓 {dec}")
    else:
        await message.answer("❌ Invalid!")

# ========== TEMPEST ==========
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
        c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
                 (datetime.now().isoformat(), user.id))
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
        f"{header('BLOOD PACT COMPLETE')}\n"
        f"⚡ <b>WELCOME TO THE TEMPEST!</b>\n\n"
        f"🌀 Rank: Blood Initiate\n"
        f"⚔️ Sacrifices: 3\n"
        f"📁 Uploads = +1 sacrifice\n"
        f"📜 /tempest_story for lore",
        parse_mode=ParseMode.HTML
    )
    await message.answer("🩸⚡🌀🔥🌑✨")
    await send_log(f"🌀 {user.first_name} joined Tempest!")

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
    text = f"{header('TEMPEST CREED')}\n📊 Members: {total}\n⚔️ Sacrifices: {total_sacs}\n\n<b>TOP MEMBERS:</b>\n"
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
        f"{header('TEMPEST SHRINE')}\n"
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
        await message.answer("⚡ Reply to curse!")
        return
    target = message.reply_to_message.from_user
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("UPDATE users SET curse_type = 'Bad Luck', curse_time = ? WHERE user_id = ?",
                    (datetime.now().isoformat(), target.id))
        conn.commit()
    await message.reply(f"⚡ <b>{target.first_name}</b> is cursed!", parse_mode=ParseMode.HTML)

@dp.message(Command("remove_curse"))
async def remove_curse_cmd(message: Message):
    user, chat = await handle_common(message, "remove_curse")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    if not message.reply_to_message:
        await message.answer("Reply to remove curse!")
        return
    target = message.reply_to_message.from_user
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("UPDATE users SET curse_type = 'none', curse_time = NULL WHERE user_id = ?", (target.id,))
        conn.commit()
    await message.reply(f"✅ Curse removed from {target.first_name}!")

# ========== UTILITY ==========
@dp.message(Command("time"))
async def time_cmd(message: Message):
    user, chat = await handle_common(message, "time")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"🌍 Usage: /time [country]\nAvailable: {', '.join(list(COUNTRY_TIMEZONES.keys())[:10])}...")
        return
    country = args[1].lower().strip()
    if country not in COUNTRY_TIMEZONES:
        await message.answer("❌ Not found!")
        return
    tz_name = COUNTRY_TIMEZONES[country]
    try:
        if ZoneInfo:
            now = datetime.now(ZoneInfo(tz_name))
        else:
            now = datetime.utcnow()
        await message.answer(f"🌍 <b>{country.upper()}</b>\n🕐 {now.strftime('%H:%M:%S')}\n📅 {now.strftime('%A, %d %B %Y')}", parse_mode=ParseMode.HTML)
    except:
        await message.answer("❌ Error!")

@dp.message(Command("word"))
async def word_cmd(message: Message):
    user, chat = await handle_common(message, "word")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📝 Usage: /word [text]")
        return
    msg = await message.answer("📝 Creating...")
    try:
        doc = Document()
        doc.add_heading("TEMPEST ARCHIVES", 0)
        doc.add_paragraph(f"By: {user.first_name}")
        doc.add_paragraph(args[1])
        filename = f"temp/word_{user.id}.docx"
        doc.save(filename)
        await msg.delete()
        await message.answer_document(FSInputFile(filename))
        os.remove(filename)
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

# ========== UPLOAD ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")
    if not user:
        return
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 Private chat only!")
        return
    upload_waiting[user.id] = True
    await message.answer("📁 Send me any file!")

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation)
async def handle_file(message: Message):
    user = message.from_user
    if user.id not in upload_waiting:
        return
    upload_waiting.pop(user.id, None)
    msg = await message.answer("⏳ Processing...")
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
                cult = conn.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,)).fetchone()
                if cult and cult[0] != 'none':
                    conn.execute("UPDATE users SET sacrifices = sacrifices + 1 WHERE user_id = ?", (user.id,))
                conn.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type) VALUES (?, ?, ?, ?)",
                            (user.id, datetime.now().isoformat(), link, file_type))
                conn.commit()
            await msg.edit_text(f"✅ {file_type}!\n🔗 <code>{link}</code>", parse_mode=ParseMode.HTML)
        else:
            await msg.edit_text("❌ Failed")
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
    msg = await message.answer("📥 Downloading...")
    try:
        def download():
            ydl_opts = {'outtmpl': 'temp/%(title)s.%(ext)s', 'format': 'best', 'quiet': True}
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
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    start = time.perf_counter()
    msg = await message.answer("🏓 Testing...")
    latency = int((time.perf_counter() - start) * 1000)
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    uptime = format_uptime(int(time.time() - start_time))
    await msg.edit_text(f"🏓 {latency}ms\n🕒 {uptime}\n💻 CPU: {cpu}%\n💾 RAM: {ram}%")

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    user, chat = await handle_common(message, "stats")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
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
    await message.answer(f"👥 Users: {users}\n📁 Uploads: {uploads}\n✨ Wishes: {wishes}\n🌀 Tempest: {tempest}")

@dp.message(Command("scan"))
async def scan_cmd(message: Message):
    user, chat = await handle_common(message, "scan")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM command_logs")
        cmds = c.fetchone()[0]
    await message.answer(f"🔍 Users: {users}\n🔧 Commands: {cmds}\n✅ Scan complete!")

@dp.message(Command("users"))
async def users_cmd(message: Message):
    user, chat = await handle_common(message, "users")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, first_name, uploads, commands FROM users ORDER BY commands DESC LIMIT 20")
        users = c.fetchall()
    text = f"{header('TOP USERS')}\n"
    for uid, name, up, cmds in users:
        text += f"• {name} ({uid}) - 📁{up} 🔧{cmds}\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    broadcast_state[user.id] = {"step": 1}
    await message.answer("📢 Send me text, photo, video, or document!")

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
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    args = message.text.split()
    duration = 5
    if len(args) > 1 and args[1].isdigit():
        duration = min(int(args[1]), 15)
    msg = await message.answer("🤖 Glitching...")
    for i in range(duration):
        progress = "▓" * (i + 1) + "░" * (duration - i - 1)
        try:
            await msg.edit_text(f"⚡ [{progress}] {i+1}/{duration}s")
        except:
            pass
        await asyncio.sleep(1.3)
    await msg.edit_text("✅ Recovered!")

@dp.message(Command("disable"))
async def disable_cmd(message: Message):
    user, chat = await handle_common(message, "disable")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
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
    text = f"{header('LOGS')}\n"
    for ts, uid, cmd in logs:
        text += f"• {ts[:19]} | {uid} | /{cmd}\n"
    await message.answer(text)

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
    await message.answer(f"✅ User {target_id} is admin!")

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
    await message.answer("💾 Upload .db file!")

@dp.message(F.document)
async def handle_restore(message: Message):
    user = message.from_user
    if user.id not in pending_restore:
        return
    pending_restore.pop(user.id, None)
    if not message.document.file_name.endswith('.db'):
        await message.answer("❌ Need .db file!")
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
        await msg.edit_text("✅ Restored!")
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
    print("🚀 Starting...")
    await send_log("🚀 Bot started!")
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())