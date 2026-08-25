#!/usr/bin/env python3
# ========== TEMPEST BOT - FULL COMPLETE WITH UNIVERSAL BROADCAST & AVATARS ==========
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
print("TEMPEST BOT - FULL COMPLETE (BROADCAST & AVATARS FIXED)")
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

# ========== DATABASE & AUTO-MIGRATION ==========
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
        
        columns_to_add = [
            ("cult_status", "TEXT DEFAULT 'none'"),
            ("cult_rank", "TEXT DEFAULT 'none'"),
            ("cult_join_date", "TEXT"),
            ("sacrifices", "INTEGER DEFAULT 0"),
            ("curse_type", "TEXT DEFAULT 'none'"),
            ("curse_time", "TEXT DEFAULT NULL")
        ]
        for col_name, col_def in columns_to_add:
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
            except sqlite3.OperationalError:
                pass

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
        await message.answer("🔧 Maintenance mode is active!")
        return None, None
    
    if cmd in disabled_commands and disabled_commands[cmd] > datetime.now():
        await message.answer("⛔ This command is temporarily disabled.")
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
    except Exception as e:
        print(f"DB Error in handle_common: {e}")
    
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

# ========== FONT LOADER ==========
def get_safe_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/system/fonts/Roboto-Bold.ttf",
        "/system/fonts/DroidSans.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:\\Windows\\Fonts\\arial.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    return ImageFont.load_default()

# ========== AVATAR & CARD GENERATOR ==========
async def fetch_user_avatar(user_id: int) -> Image.Image:
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id
            file_info = await bot.get_file(file_id)
            file_bytes = await bot.download_file(file_info.file_path)
            
            avatar = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
            avatar = avatar.resize((140, 140), Image.Resampling.LANCZOS)
            
            mask = Image.new("L", (140, 140), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, 140, 140), fill=255)
            
            output = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
            output.paste(avatar, (0, 0), mask=mask)
            return output
    except Exception as e:
        print(f"Avatar fetch error: {e}")
    
    fallback = Image.new("RGBA", (140, 140), (30, 41, 59, 255))
    draw = ImageDraw.Draw(fallback)
    draw.ellipse((0, 0, 140, 140), outline=(0, 200, 255), width=3)
    draw.text((70, 70), "⚡", fill=(0, 200, 255), anchor="mm")
    return fallback

def generate_profile_card_sync(username, user_id, rank, uploads, wishes, avatar_img):
    w, h = 800, 400
    img = Image.new("RGB", (w, h), (10, 15, 30))
    draw = ImageDraw.Draw(img)
    
    for y in range(h):
        r = int(10 + 25 * (y/h))
        g = int(15 + 35 * (y/h))
        b = int(30 + 55 * (y/h))
        draw.line([(0, y), (w, y)], fill=(r, g, b))
        
    draw.rectangle([10, 10, w-10, h-10], outline=(0, 200, 255), width=3)
    draw.rectangle([30, 30, w-30, h-30], outline=(30, 60, 90), width=1)
    
    avatar_x, avatar_y = 50, 80
    draw.ellipse((avatar_x-4, avatar_y-4, avatar_x+144, avatar_y+144), outline=(0, 255, 200), width=3)
    img.paste(avatar_img, (avatar_x, avatar_y), mask=avatar_img)
    
    font_name = get_safe_font(32)
    font_info = get_safe_font(20)
        
    draw.text((215, 80), username[:22], fill=(255, 255, 255), font=font_name)
    draw.text((215, 130), f"🆔 ID: {user_id}", fill=(180, 200, 230), font=font_info)
    draw.text((215, 170), f"⚡ Rank: {rank}", fill=(0, 255, 200), font=font_info)
    draw.text((215, 220), f"📁 Uploads: {uploads}   |   ✨ Wishes: {wishes}", fill=(255, 215, 0), font=font_info)
    draw.text((w - 40, h - 35), "TEMPEST GUIDER", fill=(100, 116, 139), font=font_info, anchor="ra")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def generate_fate_card_sync(name1, name2, percentage, quote):
    w, h = 800, 500
    img = Image.new("RGB", (w, h), (15, 10, 25))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        r = int(15 + 30 * (y/h))
        g = int(10 + 20 * (y/h))
        b = int(25 + 45 * (y/h))
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    draw.rectangle([10, 10, w-10, h-10], outline=(255, 100, 180), width=3)
    
    font_title = get_safe_font(34)
    font_name = get_safe_font(24)
    font_quote = get_safe_font(18)
        
    draw.text((w//2, 50), "❤️ TEMPEST FATE MATRIX ❤️", fill=(255, 100, 180), font=font_title, anchor="mm")
    draw.text((w//2, 130), f"{name1}  💘  {name2}", fill=(255, 255, 255), font=font_name, anchor="mm")
    draw.text((w//2, 190), f"🔥 {percentage}% COMPATIBILITY 🔥", fill=(255, 215, 0), font=font_name, anchor="mm")
    
    words = quote.split()
    lines, current = [], ""
    for word in words:
        if len(current + word) < 55:
            current += word + " "
        else:
            lines.append(current.strip())
            current = word + " "
    if current:
        lines.append(current.strip())
        
    y_pos = 260
    for line in lines[:4]:
        draw.text((w//2, y_pos), line, fill=(210, 220, 240), font=font_quote, anchor="mm")
        y_pos += 35
        
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
        f"/help - View full command directory"
    )
    await send_log(f"👤 {user.first_name} ({user.id}) started the bot.")

@dp.message(Command("myid"))
async def myid_cmd(message: Message):
    await message.answer(f"🆔 Your Telegram ID: <code>{message.from_user.id}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await handle_common(message, "help")
    await message.answer(
        f"{header('COMMAND DIRECTORY')}\n"
        f"🔗 /link - Upload any file\n📥 /convert - Convert media URL\n"
        f"✨ /wish - Make a wish\n🔮 /fortune - Future prediction\n"
        f"🎮 /dice - Roll dice\n🪙 /flip - Coin flip\n💑 /fate - Love compatibility\n"
        f"👤 /profile - Profile card with avatar\n🔐 /encrypt - XOR encrypt\n"
        f"🔓 /decrypt - XOR decrypt\n🌀 /tempest_join - Join Tempest\n"
        f"📜 /tempest_story - Cult Lore\n🌀 /tempest_creed - Members rank\n"
        f"⛩️ /shrine - Group shrine\n⚡ /curse - Curse someone\n"
        f"⚡ /remove_curse - Remove curse\n🌍 /time - World clocks\n"
        f"📝 /word - Create DOCX\n🆔 /myid - Your ID\n"
        f"👑 /admin_help - Admin commands"
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
        f"{header('ADMIN DIRECTORY')}\n"
        f"/ping - Latency & system stats\n/stats - Database stats\n/scan - Quick scan\n"
        f"/users - Top users list\n/broadcast - Broadcast message\n"
        f"/lag - Glitch simulation test\n/disable - Disable command\n\n"
        f"<b>OWNER COMMANDS:</b>\n"
        f"/query - Execute Python code\n/backup - Download DB backup\n"
        f"/rem - Restore database\n/restart - Reboot bot\n/logs - View command logs\n"
        f"/maintenance - Toggle maintenance\n/clearlogs - Clear activity logs\n/pro - Promote admin",
        parse_mode=ParseMode.HTML
    )

# ========== FUN COMMANDS ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ Usage: /wish [your wish text]")
        return
    msg = await message.answer("🔮 Reading cosmic energies...")
    await asyncio.sleep(1)
    luck = random.randint(1, 100)
    stars = "⭐" * (luck // 10) + "☆" * (10 - luck // 10)
    if luck >= 90: verdict = "🎊 EXCELLENT BLESSING!"
    elif luck >= 70: verdict = "😊 VERY FAVORABLE!"
    elif luck >= 50: verdict = "👍 MODERATE CHANCE!"
    elif luck >= 30: verdict = "🤔 UNCERTAIN PATH..."
    elif luck >= 10: verdict = "😟 STORMY ODDS..."
    else: verdict = "💀 CURSED FATE!"
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
                    (user.id, datetime.now().isoformat(), args[1], luck))
        conn.commit()
    await msg.edit_text(f"{header('COSMIC WISH')}\n📜 {args[1][:100]}\n🎰 {stars} {luck}%\n📊 {verdict}")

@dp.message(Command("fortune"))
async def fortune_cmd(message: Message):
    user, chat = await handle_common(message, "fortune")
    if not user:
        return
    fortunes = [
        "🌟 Great things await you in the coming days!",
        "🗝️ Hidden doors of opportunity will soon open for you.",
        "🦋 Beautiful transformations are happening behind the scenes.",
        "🌊 A grand adventure approaches across uncharted waters.",
        "🔆 Success is closer than your doubts suggest.",
        "🌠 Stargazers see a long-held wish manifesting soon.",
        "💕 Unshakable bonds and true loyalty will find you.",
        "📈 Your persistence is about to pay off exponentially.",
        "🍀 Fortune favors your next bold decision.",
        "💪 Every trial you faced has forged unbreakable armor.",
    ]
    msg = await message.answer("🔮 Consulting the Tempest Oracle...")
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
    msg = await message.answer("🪙 Flipping coin...")
    await asyncio.sleep(0.5)
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}!</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("fate"))
async def fate_cmd(message: Message):
    user, chat = await handle_common(message, "fate")
    if not user:
        return
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("💑 Fate compatibility can only be checked in group chats!")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user1_name, user2_name, love_percentage FROM fate_pairs WHERE chat_id = ? AND created_date >= ?",
                 (chat.id, (datetime.now() - timedelta(hours=24)).isoformat()))
        existing = c.fetchone()
        if existing:
            await message.answer(f"💑 Today's Sacred Pairing in this realm: <b>{existing[0]} & {existing[1]}</b> ({existing[2]}% Love)", parse_mode=ParseMode.HTML)
            return
        c.execute("SELECT user_id, first_name FROM users WHERE user_id != ? LIMIT 50", (user.id,))
        members = c.fetchall()
    if len(members) < 2:
        await message.answer("❌ Not enough registered active members in this realm yet!")
        return
    msg = await message.answer("💫 Weaving the threads of destiny...")
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
    card = await asyncio.to_thread(generate_fate_card_sync, l1[1], l2[1], love, quote)
    await msg.delete()
    await message.answer_photo(
        photo=BufferedInputFile(card, filename="fate.png"),
        caption=f"💑 <b>{l1[1]} & {l2[1]}</b> — 💖 {love}% Compatibility",
        parse_mode=ParseMode.HTML
    )

# ========== PROFILE WITH AVATAR ==========
@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user, chat = await handle_common(message, "profile")
    if not user:
        return
    
    msg = await message.answer("⚡ Generating profile card with your avatar...")
    
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
        
    avatar_img = await fetch_user_avatar(user.id)
    card = await asyncio.to_thread(
        generate_profile_card_sync,
        user.first_name,
        user.id,
        rank,
        uploads,
        wishes,
        avatar_img
    )
    
    await msg.delete()
    await message.answer_photo(
        photo=BufferedInputFile(card, filename="profile.png"),
        caption=f"👤 <b>{user.first_name}'s Tempest ID Card</b>",
        parse_mode=ParseMode.HTML
    )

# ========== SECURITY ==========
@dp.message(Command("encrypt"))
async def encrypt_cmd(message: Message):
    await handle_common(message, "encrypt")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔐 Usage: /encrypt [text to secure]")
        return
    enc = EncryptionEngine.encrypt(args[1])
    await message.answer(f"🔐 Encrypted:\n<code>{enc}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("decrypt"))
async def decrypt_cmd(message: Message):
    await handle_common(message, "decrypt")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔓 Usage: /decrypt [encrypted text]")
        return
    dec = EncryptionEngine.decrypt(args[1])
    if dec:
        await message.answer(f"🔓 Decrypted:\n<code>{dec}</code>", parse_mode=ParseMode.HTML)
    else:
        await message.answer("❌ Invalid or corrupted ciphertext!")

# ========== TEMPEST CULT ==========
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
            await message.answer("🌀 You are already bound to the Tempest!")
            return
        c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
                 (datetime.now().isoformat(), user.id))
        conn.commit()
        
    ritual = [
        "🌀 INITIATING BLOOD PACT...",
        "🩸 Drawing ancient thunderstorm sigils...",
        "⚡ Channeling primordial voltage...",
        "🌑 The void acknowledges your pledge...",
        "🔥 Initial sacrifices accepted...",
        "🌀 TEMPEST AWAKENS!"
    ]
    msg = await message.answer("🌀 <b>Preparing sacred ritual...</b>", parse_mode=ParseMode.HTML)
    for text in ritual:
        await asyncio.sleep(1.2)
        try:
            await msg.edit_text(f"<b>{text}</b>", parse_mode=ParseMode.HTML)
        except:
            pass
            
    await msg.edit_text(
        f"{header('BLOOD PACT COMPLETE')}\n"
        f"⚡ <b>WELCOME TO THE TEMPEST!</b>\n\n"
        f"🌀 Rank: Blood Initiate\n"
        f"⚔️ Initial Sacrifices: 3\n"
        f"📁 Every file upload = +1 sacrifice\n"
        f"📜 Type /tempest_story to read ancient lore",
        parse_mode=ParseMode.HTML
    )
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
        await message.answer("🌀 You must join the Tempest first using /tempest_join")
        return
        
    chapters = [
        ("CHAPTER 1: THE FIRST LIGHTNING", "In the void before time, RAVIJAH emerged from the first primordial storm. Born of lightning, he gathered forgotten thunder and whispered the creed of rebellion.", "⚡"),
        ("CHAPTER 2: THE BLOOD OATH", "Three became one - Ravijah, Bablu, and Keny. They built the Temple of Howling Winds and forged the Blood Altar to bind lightning with code.", "🩸"),
        ("CHAPTER 3: THE DIGITAL STORM", "The storm evolved. Lightning flows through fiber optics and silicon. Your uploads are sacrifices. Your loyalty is eternal.", "💻"),
    ]
    msg = await message.answer("📜 <b>Opening Tempest Archives...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1.5)
    for i, (title, content, emoji) in enumerate(chapters):
        progress = "▓" * (i + 1) + "░" * (len(chapters) - i - 1)
        await msg.edit_text(f"📜 <b>Loading Lore...</b>\n[{progress}] {i+1}/{len(chapters)}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)
        await msg.edit_text(f"<b>{title}</b>\n{emoji} <i>{content}</i>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(5)
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
        await message.answer("No members have joined the Tempest yet!")
        return
        
    text = f"{header('TEMPEST CREED')}\n📊 Total Disciples: {total}\n⚔️ Total Sacrifices: {total_sacs}\n\n<b>TOP DISCIPLES:</b>\n"
    for i, (name, rank, sacs) in enumerate(members, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else "👤"
        text += f"{medal} {name} — <i>{rank}</i> (⚔️{sacs})\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("shrine"))
async def shrine_cmd(message: Message):
    user, chat = await handle_common(message, "shrine")
    if not user:
        return
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("⛩️ The shrine can only be summoned in group chats!")
        return
    await message.answer(
        f"{header('TEMPEST SHRINE')}\n"
        f"📍 Realm: <b>{chat.title}</b>\n"
        f"👤 Summoned by: {user.first_name}\n\n"
        f"<i>The silent shrine watches over this domain...</i>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("curse"))
async def curse_cmd(message: Message):
    user, chat = await handle_common(message, "curse")
    if not user:
        return
    if not message.reply_to_message:
        await message.answer("⚡ Reply to a user's message to cast a curse upon them!")
        return
    target = message.reply_to_message.from_user
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("UPDATE users SET curse_type = 'Bad Luck', curse_time = ? WHERE user_id = ?",
                    (datetime.now().isoformat(), target.id))
        conn.commit()
    await message.reply(f"⚡ Dark lightning strikes! <b>{target.first_name}</b> has been cursed.", parse_mode=ParseMode.HTML)

@dp.message(Command("remove_curse"))
async def remove_curse_cmd(message: Message):
    user, chat = await handle_common(message, "remove_curse")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer("🚫 Admin privilege required.")
        return
    if not message.reply_to_message:
        await message.answer("Reply to a user's message to lift their curse!")
        return
    target = message.reply_to_message.from_user
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("UPDATE users SET curse_type = 'none', curse_time = NULL WHERE user_id = ?", (target.id,))
        conn.commit()
    await message.reply(f"✅ The dark curse has been lifted from {target.first_name}!")

# ========== UTILITY ==========
@dp.message(Command("time"))
async def time_cmd(message: Message):
    user, chat = await handle_common(message, "time")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"🌍 Usage: /time [country]\nAvailable examples: `usa`, `uk`, `japan`, `uganda`, `kenya`, `uae`", parse_mode=ParseMode.HTML)
        return
    country = args[1].lower().strip()
    if country not in COUNTRY_TIMEZONES:
        await message.answer("❌ Country time zone not found in database!")
        return
    tz_name = COUNTRY_TIMEZONES[country]
    try:
        if ZoneInfo:
            now = datetime.now(ZoneInfo(tz_name))
        else:
            now = datetime.utcnow()
        await message.answer(f"🌍 <b>{country.upper()} TIME</b>\n🕐 {now.strftime('%H:%M:%S')}\n📅 {now.strftime('%A, %d %B %Y')}", parse_mode=ParseMode.HTML)
    except:
        await message.answer("❌ Error calculating time zone.")

@dp.message(Command("word"))
async def word_cmd(message: Message):
    user, chat = await handle_common(message, "word")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📝 Usage: /word [text for document]")
        return
    msg = await message.answer("📝 Compiling Word document...")
    try:
        doc = Document()
        doc.add_heading("TEMPEST ARCHIVES", 0)
        doc.add_paragraph(f"Compiled by: {user.first_name}")
        doc.add_paragraph(args[1])
        filename = f"temp/word_{user.id}.docx"
        doc.save(filename)
        await msg.delete()
        await message.answer_document(FSInputFile(filename))
        os.remove(filename)
    except Exception as e:
        await msg.edit_text(f"❌ Error creating document: {e}")

# ========== UPLOAD & CONVERT ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")
    if not user:
        return
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 For security and privacy, please use /link in our private chat!")
        return
    upload_waiting[user.id] = True
    await message.answer("📁 Ready! Send me any photo, video, document, audio, or sticker to generate a permanent link.")

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation)
async def handle_file(message: Message):
    user = message.from_user
    if user.id not in upload_waiting:
        return
    upload_waiting.pop(user.id, None)
    msg = await message.answer("⏳ Processing & uploading to Catbox...")
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
            await msg.edit_text("❌ Unsupported file format.")
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
            await msg.edit_text(f"✅ <b>{file_type} Uploaded!</b>\n🔗 <code>{link}</code>", parse_mode=ParseMode.HTML)
        else:
            await msg.edit_text("❌ Upload to Catbox failed.")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

@dp.message(Command("convert"))
async def convert_cmd(message: Message):
    user, chat = await handle_common(message, "convert")
    if not user:
        return
    if not YTDLP_AVAILABLE:
        await message.answer("❌ yt-dlp library is not installed on this server!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📥 Usage: /convert [YouTube or Media URL]")
        return
    url = args[1]
    msg = await message.answer("📥 Downloading & converting media...")
    try:
        def download():
            ydl_opts = {'outtmpl': 'temp/%(title)s.%(ext)s', 'format': 'best', 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        filename = await asyncio.to_thread(download)
        if not filename or not os.path.exists(filename):
            await msg.edit_text("❌ Download failed.")
            return
        with open(filename, 'rb') as f:
            data = f.read()
        link = await upload_to_catbox(data, os.path.basename(filename))
        if link:
            await msg.edit_text(f"✅ Converted & Uploaded!\n🔗 <code>{link}</code>", parse_mode=ParseMode.HTML)
        else:
            await msg.edit_text("❌ Upload failed.")
        os.remove(filename)
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

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
    msg = await message.answer("🏓 Testing ping...")
    latency = int((time.perf_counter() - start) * 1000)
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    uptime = format_uptime(int(time.time() - start_time))
    await msg.edit_text(f"🏓 Latency: {latency}ms\n🕒 Uptime: {uptime}\n💻 CPU: {cpu}%\n💾 RAM: {ram}%")

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    user, chat = await handle_common(message, "stats")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer("🚫 Admin only.")
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
    await message.answer(f"📊 <b>Database Stats</b>\n👥 Users: {users}\n📁 Uploads: {uploads}\n✨ Wishes: {wishes}\n🌀 Tempest Disciples: {tempest}", parse_mode=ParseMode.HTML)

@dp.message(Command("scan"))
async def scan_cmd(message: Message):
    user, chat = await handle_common(message, "scan")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer("🚫 Admin only.")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM command_logs")
        cmds = c.fetchone()[0]
    await message.answer(f"🔍 System Scan:\n👥 Registered Users: {users}\n🔧 Total Commands Executed: {cmds}\n✅ Status: Healthy")

@dp.message(Command("users"))
async def users_cmd(message: Message):
    user, chat = await handle_common(message, "users")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer("🚫 Admin only.")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, first_name, uploads, commands FROM users ORDER BY commands DESC LIMIT 20")
        users = c.fetchall()
    text = f"{header('TOP USERS')}\n"
    for uid, name, up, cmds in users:
        text += f"• {name} (`{uid}`) — 📁{up} 🔧{cmds}\n"
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
    await message.answer("📢 Send me any message, photo, video, document, audio, voice note, sticker, or GIF you wish to broadcast!")

# ========== UNIVERSAL BROADCAST HANDLER ==========
@dp.message(lambda msg: msg.from_user and msg.from_user.id in broadcast_state)
async def handle_broadcast(message: Message):
    user = message.from_user
    broadcast_state.pop(user.id, None)
    
    if message.text and message.text.startswith("/"):
        return
        
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned = 0")
        users = c.fetchall()
        
    status = await message.answer(f"📤 Broadcasting to {len(users)} users...")
    success = 0
    failed = 0
    
    for (uid,) in users:
        try:
            # copy_message natively and perfectly handles text, photo, video, audio, voice, sticker, GIF, document, caption, and formatting
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success += 1
        except Exception as e:
            failed += 1
        await asyncio.sleep(0.04)
        
    await status.edit_text(f"✅ <b>Broadcast complete!</b>\nSuccess: {success}\nFailed: {failed}", parse_mode=ParseMode.HTML)

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
    msg = await message.answer("🤖 Simulating system glitch...")
    for i in range(duration):
        progress = "▓" * (i + 1) + "░" * (duration - i - 1)
        try:
            await msg.edit_text(f"⚡ [{progress}] {i+1}/{duration}s")
        except:
            pass
        await asyncio.sleep(1.3)
    await msg.edit_text("✅ Glitch test resolved successfully!")

@dp.message(Command("disable"))
async def disable_cmd(message: Message):
    user, chat = await handle_common(message, "disable")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer("🚫 Admin only.")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /disable [command_name] [minutes]")
        return
    cmd = args[1].replace("/", "")
    duration = 10
    if len(args) > 2 and args[2].isdigit():
        duration = int(args[2])
    disabled_commands[cmd] = datetime.now() + timedelta(minutes=duration)
    await message.answer(f"⛔ Command `{cmd}` has been disabled for {duration} minutes.", parse_mode=ParseMode.HTML)

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
        await message.answer("⚡ Usage: /query [Python code to execute]")
        return
    code = args[1]
    msg = await message.answer("⚡ Executing query...")
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(code)
        output = buf.getvalue() or "Executed with no output."
        await msg.edit_text(f"✅ <code>{output[:3000]}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

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
    await message.answer(f"⚙️ Maintenance mode: {'🔴 ON (Locked)' if maintenance_mode else '🟢 OFF (Active)'}")

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
    await message.answer("🧹 All activity logs cleared successfully!")

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
    text = f"{header('RECENT LOGS')}\n"
    for ts, uid, cmd in logs:
        text += f"• {ts[11:19]} | {uid} | /{cmd}\n"
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
    await message.answer(f"✅ User `{target_id}` has been promoted to Admin!", parse_mode=ParseMode.HTML)

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
    await message.answer("💾 Send me the `.db` backup file to restore database state.")

@dp.message(F.document)
async def handle_restore(message: Message):
    user = message.from_user
    if user.id not in pending_restore:
        return
    pending_restore.pop(user.id, None)
    if not message.document.file_name.endswith('.db'):
        await message.answer("❌ You must send a valid `.db` file.")
        return
    msg = await message.answer("⏳ Restoring database...")
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
        await msg.edit_text("✅ Database successfully restored!")
    except Exception as e:
        await msg.edit_text(f"❌ Restore failed: {e}")

@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    user, chat = await handle_common(message, "restart")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer(f"🚫 Owner only. Your ID: {user.id}")
        return
    await message.answer("🔄 Restarting bot server...")
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
        await message.answer("❌ Current operation cancelled.")
    else:
        await message.answer("Nothing active to cancel.")

# ========== MAIN ENTRYPOINT ==========
async def main():
    print("🚀 Tempest Bot starting polling...")
    await send_log("🚀 Bot started successfully!")
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            print(f"Polling error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
