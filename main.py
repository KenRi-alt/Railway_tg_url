#!/usr/bin/env python3
# ========== TEMPEST GUIDER - COMPLETE EDITION ==========
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
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, CallbackQuery, BufferedInputFile
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError

print("=" * 60)
print("TEMPEST GUIDER - COMPLETE EDITION")
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

# ========== FONT AUTO-DOWNLOAD ==========
async def ensure_font():
    font_path = "fonts/font.ttf"
    if not os.path.exists(font_path):
        print("📥 Downloading font...")
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Regular.ttf"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, follow_redirects=True)
                if r.status_code == 200:
                    with open(font_path, "wb") as f:
                        f.write(r.content)
                    print("✅ Font downloaded!")
        except Exception as e:
            print(f"⚠️ Font warning: {e}")

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
        
        for col_name, col_def in [
            ("cult_status", "TEXT DEFAULT 'none'"),
            ("cult_rank", "TEXT DEFAULT 'none'"),
            ("cult_join_date", "TEXT"),
            ("sacrifices", "INTEGER DEFAULT 0"),
            ("curse_type", "TEXT DEFAULT 'none'"),
            ("curse_time", "TEXT DEFAULT NULL")
        ]:
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
            except sqlite3.OperationalError:
                pass

        c.execute('''CREATE TABLE IF NOT EXISTS groups (group_id INTEGER PRIMARY KEY, title TEXT, joined_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS uploads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, timestamp TEXT, file_url TEXT, file_type TEXT, file_size INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS command_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user_id INTEGER, chat_id INTEGER, command TEXT, success INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS wishes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, timestamp TEXT, wish_text TEXT, luck INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS fate_pairs (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user1_id INTEGER, user1_name TEXT, user2_id INTEGER, user2_name TEXT, love_percentage INTEGER, created_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS fortunes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, timestamp TEXT, fortune_text TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS shrines (user_id INTEGER PRIMARY KEY, power_level INTEGER DEFAULT 10, title TEXT DEFAULT 'Novice')''')
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
        print(f"DB Error: {e}")
    
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
        return ''.join(chr(ord(char) ^ ord(key[i % len(key)])) for i, char in enumerate(text))
    
    @staticmethod
    def encrypt(text):
        return base64.b64encode(EncryptionEngine.xor_encrypt(text).encode()).decode()
    
    @staticmethod
    def decrypt(text):
        try:
            return EncryptionEngine.xor_encrypt(base64.b64decode(text.encode()).decode())
        except:
            return None

# ========== FONT LOADER ==========
def get_safe_font(size):
    font_path = "fonts/font.ttf"
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except:
            pass
    for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/system/fonts/Roboto-Bold.ttf"]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    return ImageFont.load_default()

# ========== AVATAR FETCHER ==========
async def fetch_user_avatar(user_id: int, first_name: str = "User") -> Image.Image:
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id
            file_info = await bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(file_url)
            if r.status_code == 200:
                avatar = Image.open(io.BytesIO(r.content)).convert("RGBA")
                avatar = avatar.resize((120, 120), Image.Resampling.LANCZOS)
                mask = Image.new("L", (120, 120), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 120, 120), fill=255)
                output = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
                output.paste(avatar, (0, 0), mask=mask)
                return output
    except Exception as e:
        print(f"Avatar error: {e}")
    
    fallback = Image.new("RGBA", (120, 120), (20, 30, 50, 255))
    draw = ImageDraw.Draw(fallback)
    draw.ellipse((0, 0, 120, 120), outline=(0, 255, 200), width=3)
    initial = first_name[0].upper() if first_name else "⚡"
    font = get_safe_font(50)
    draw.text((60, 60), initial, fill=(0, 255, 200), font=font, anchor="mm")
    return fallback

# ========== PROFILE CARD WITH AVATAR ==========
def generate_profile_card_sync(username, user_id, rank, uploads, wishes, avatar_img):
    w, h = 800, 360
    img = Image.new("RGB", (w, h), (10, 15, 30))
    draw = ImageDraw.Draw(img)
    
    for y in range(h):
        r = int(10 + 25 * (y/h))
        g = int(15 + 35 * (y/h))
        b = int(30 + 55 * (y/h))
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    
    draw.rectangle([10, 10, w-10, h-10], outline=(0, 200, 255), width=3)
    
    avatar_x, avatar_y = 50, 80
    draw.ellipse((avatar_x-3, avatar_y-3, avatar_x+123, avatar_y+123), outline=(0, 255, 200), width=3)
    img.paste(avatar_img, (avatar_x, avatar_y), mask=avatar_img)
    
    font_name = get_safe_font(24)
    font_info = get_safe_font(18)
    
    draw.text((200, 75), str(username)[:22], fill=(255, 255, 255), font=font_name)
    draw.text((200, 120), f"🆔 ID: {user_id}", fill=(180, 200, 230), font=font_info)
    draw.text((200, 160), f"⚡ Rank: {rank}", fill=(0, 255, 200), font=font_info)
    draw.text((200, 205), f"📁 Uploads: {uploads}   |   ✨ Wishes: {wishes}", fill=(255, 215, 0), font=font_info)
    draw.text((w - 30, h - 30), "TEMPEST GUIDER", fill=(100, 116, 139), font=font_info, anchor="ra")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

# ========== FATE CARD WITH QUOTE IN IMAGE ==========
def generate_fate_card_sync(name1, name2, percentage, quote):
    w, h = 800, 450
    img = Image.new("RGB", (w, h), (15, 10, 25))
    draw = ImageDraw.Draw(img)
    
    for y in range(h):
        r = int(15 + 30 * (y/h))
        g = int(10 + 20 * (y/h))
        b = int(25 + 45 * (y/h))
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    
    draw.rectangle([10, 10, w-10, h-10], outline=(255, 100, 180), width=3)
    
    font_title = get_safe_font(28)
    font_name = get_safe_font(20)
    font_quote = get_safe_font(16)
    
    draw.text((w//2, 45), "❤️ TEMPEST FATE MATRIX ❤️", fill=(255, 100, 180), font=font_title, anchor="mm")
    draw.text((w//2, 110), f"{name1}  💘  {name2}", fill=(255, 255, 255), font=font_name, anchor="mm")
    draw.text((w//2, 160), f"🔥 {percentage}% COMPATIBILITY 🔥", fill=(255, 215, 0), font=font_name, anchor="mm")
    
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
    
    y_pos = 220
    for line in lines[:4]:
        draw.text((w//2, y_pos), line, fill=(210, 220, 240), font=font_quote, anchor="mm")
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
        f"{header('TEMPEST GUIDER')}\n"
        f"✨ Welcome {user.first_name}!\n\n"
        f"/help - View full command directory"
    )
    await send_log(f"👤 {user.first_name} ({user.id}) started")

@dp.message(Command("myid"))
async def myid_cmd(message: Message):
    await message.answer(f"🆔 Your Telegram ID: <code>{message.from_user.id}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await handle_common(message, "help")
    await message.answer(
        f"{header('COMMAND DIRECTORY')}\n"
        f"🔗 /link - Upload file\n📥 /convert - Convert media URL\n"
        f"✨ /wish - Make a wish\n🔮 /fortune - Future prediction\n"
        f"🎮 /dice - Roll dice\n🪙 /flip - Coin flip\n💑 /fate - Love compatibility\n"
        f"👤 /profile - Profile card with avatar\n📖 /tempest_story - Tempest lore\n"
        f"⚡ /tempest_join - Join order\n👑 /tempest_creed - Creed members\n"
        f"⛩️ /shrine - Group shrine\n🔮 /curse - Cast curse\n"
        f"🔐 /encrypt - XOR encrypt\n🔓 /decrypt - XOR decrypt\n🌍 /time - World clocks\n"
        f"📝 /word - Create DOCX\n👑 /admin_help - Admin commands"
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
        f"/ping - Latency & stats\n/stats - Database stats\n/scan - Quick scan\n"
        f"/users - Top users\n/broadcast - Broadcast\n"
        f"/lag - Glitch test\n/disable - Disable cmd\n/cm - Custom manager\n"
        f"/clearlogs - Clear logs\n/backup - Backup DB\n/rem - Restore DB\n\n"
        f"<b>OWNER:</b>\n"
        f"/query - Execute code\n/restart - Reboot\n/maintenance - Toggle\n/pro - Promote admin",
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
        await message.answer("✨ Usage: /wish [your wish]")
        return
    luck = random.randint(1, 100)
    stars = "⭐" * (luck // 10) + "☆" * (10 - luck // 10)
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
                    (user.id, datetime.now().isoformat(), args[1], luck))
        conn.commit()
    await message.answer(f"{header('COSMIC WISH')}\n📜 {args[1][:100]}\n🎰 {stars} {luck}%")

@dp.message(Command("fortune"))
async def fortune_cmd(message: Message):
    user, chat = await handle_common(message, "fortune")
    if not user:
        return
    fortunes = [
        "🌟 Great things await you!",
        "🗝️ Hidden doors will open!",
        "🦋 Beautiful transformations coming!",
        "🌊 Adventure approaches!",
        "🔆 Success is near!",
        "🌠 A wish may come true!",
        "💕 Love will find you!",
        "📈 Promotion coming!",
        "🍀 Lucky week ahead!",
        "💪 You grow stronger!",
    ]
    f = random.choice(fortunes)
    await message.answer(f"{header('FORTUNE')}\n<i>\"{f}\"</i>", parse_mode=ParseMode.HTML)

@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    await handle_common(message, "dice")
    await message.answer_dice(emoji="🎲")

@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    await handle_common(message, "flip")
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await message.answer(f"🪙 <b>{result}!</b>", parse_mode=ParseMode.HTML)

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
    msg = await message.answer("💫 Weaving destiny...")
    await asyncio.sleep(1.5)
    l1, l2 = random.sample(members, 2)
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
    msg = await message.answer("⚡ Generating profile card...")
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT uploads, cult_rank FROM users WHERE user_id = ?", (user.id,))
        r = c.fetchone()
        c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (user.id,))
        wishes = c.fetchone()[0]
    uploads, rank = (r[0], r[1]) if r else (0, "Mortal")
    if rank == 'none' or not rank:
        rank = "Mortal"
    avatar_img = await fetch_user_avatar(user.id, user.first_name)
    card = await asyncio.to_thread(generate_profile_card_sync, user.first_name, user.id, rank, uploads, wishes, avatar_img)
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
        await message.answer("🔐 Usage: /encrypt [text]")
        return
    enc = EncryptionEngine.encrypt(args[1])
    await message.answer(f"🔐 <code>{enc}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("decrypt"))
async def decrypt_cmd(message: Message):
    await handle_common(message, "decrypt")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔓 Usage: /decrypt [cipher]")
        return
    dec = EncryptionEngine.decrypt(args[1])
    if dec:
        await message.answer(f"🔓 <code>{dec}</code>", parse_mode=ParseMode.HTML)
    else:
        await message.answer("❌ Invalid!")

# ========== TEMPEST COMMANDS ==========
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
        await asyncio.sleep(1.2)
        try:
            await msg.edit_text(f"<b>{text}</b>", parse_mode=ParseMode.HTML)
        except:
            pass
    await msg.edit_text(f"{header('BLOOD PACT COMPLETE')}\n⚡ <b>WELCOME TO THE TEMPEST!</b>\n\n🌀 Rank: Blood Initiate\n⚔️ Sacrifices: 3", parse_mode=ParseMode.HTML)

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
        ("📖 Chapter 1: Awakening", "Keny Marcus opened his eyes in the obsidian realm of Tempest alongside Bablu and Ravijah. The sky burned with violet aura as a mysterious system interface flickered into existence."),
        ("⚔️ Chapter 2: Guild of Shadows", "With Bablu holding the vanguard and Ravijah orchestrating tactics, Keny forged the Tempest Guild. Shadows responded as elite warriors aligned under their banner."),
        ("⚡ Chapter 3: Breach of Citadel", "Ravijah bypassed the firewall while Bablu smashed through the fortress gates. Keny unleashed full kinetic voltage, shattering the defense grid."),
        ("👑 Chapter 4: Reign of King", "Standing atop the conquered spire together, Keny, Bablu, and Ravijah gazed across the infinite grid. The Tempest Guider era had truly begun."),
        ("🌌 Chapter 5: The Void Calls", "Beyond the digital horizon, an ancient entity stirred. The Void whispered promises of infinite power, but demanded unwavering loyalty from the three founders."),
        ("🔱 Chapter 6: Eternal Storm", "United, the three founders bound their souls to the storm. Lightning became their blood, thunder their voice, and the Tempest would never fade."),
    ]
    msg = await message.answer("📜 <b>Opening Tempest Archives...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1.5)
    for i, (title, content) in enumerate(chapters):
        progress = "▓" * (i + 1) + "░" * (len(chapters) - i - 1)
        await msg.edit_text(f"📜 <b>Loading...</b>\n[{progress}] {i+1}/{len(chapters)}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)
        await msg.edit_text(f"{header(title)}\n\n{content}", parse_mode=ParseMode.HTML)
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
    if not members:
        await message.answer("No members yet!")
        return
    text = f"{header('TEMPEST CREED')}\n"
    for i, (name, rank, sacs) in enumerate(members, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else "👤"
        text += f"{medal} {name} — {rank} (⚔️{sacs})\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command("shrine"))
async def shrine_cmd(message: Message):
    user, chat = await handle_common(message, "shrine")
    if not user:
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO shrines (user_id) VALUES (?)", (user.id,))
        c.execute("SELECT power_level, title FROM shrines WHERE user_id = ?", (user.id,))
        power, title = c.fetchone()
        conn.commit()
    await message.answer(f"{header('TEMPEST SHRINE')}\n📍 Rank: {title}\n⚡ Spiritual Power: {power} XP")

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
        conn.execute("UPDATE users SET curse_type = 'Bad Luck' WHERE user_id = ?", (target.id,))
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
        conn.execute("UPDATE users SET curse_type = 'none' WHERE user_id = ?", (target.id,))
        conn.commit()
    await message.reply(f"✅ Curse removed from {target.first_name}!")

# ========== UTILITY ==========
@dp.message(Command("time"))
async def time_cmd(message: Message):
    user, chat = await handle_common(message, "time")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or args[1].lower().strip() not in COUNTRY_TIMEZONES:
        await message.answer("🌍 Usage: /time [usa/uk/japan/uganda/kenya/uae]")
        return
    country = args[1].lower().strip()
    tz_name = COUNTRY_TIMEZONES[country]
    try:
        now = datetime.now(ZoneInfo(tz_name)) if ZoneInfo else datetime.utcnow()
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
    if user.id in pending_restore:
        pending_restore.pop(user.id, None)
        if not message.document or not message.document.file_name.endswith(".db"):
            await message.answer("❌ Send .db file!")
            return
        msg = await message.answer("⏳ Restoring...")
        try:
            file = await bot.get_file(message.document.file_id)
            url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.get(url)
            with open("data/bot.db", "wb") as f:
                f.write(r.content)
            await msg.edit_text("✅ Restored!")
        except Exception as e:
            await msg.edit_text(f"❌ {e}")
        return
    
    if user.id not in upload_waiting:
        return
    upload_waiting.pop(user.id, None)
    msg = await message.answer("⏳ Uploading...")
    try:
        file_id, file_type, file_name = None, "File", f"file_{user.id}.bin"
        if message.photo: file_id, file_type, file_name = message.photo[-1].file_id, "Photo", f"file_{user.id}.jpg"
        elif message.video: file_id, file_type, file_name = message.video.file_id, "Video", message.video.file_name or f"file_{user.id}.mp4"
        elif message.document: file_id, file_type, file_name = message.document.file_id, "Document", message.document.file_name or f"file_{user.id}.bin"
        elif message.audio: file_id, file_type, file_name = message.audio.file_id, "Audio", f"file_{user.id}.mp3"
        elif message.voice: file_id, file_type, file_name = message.voice.file_id, "Voice", f"file_{user.id}.ogg"
        elif message.sticker: file_id, file_type, file_name = message.sticker.file_id, "Sticker", f"file_{user.id}.webp"
        elif message.animation: file_id, file_type, file_name = message.animation.file_id, "GIF", f"file_{user.id}.gif"
        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url)
        link = await upload_to_catbox(r.content, file_name)
        if link:
            with sqlite3.connect("data/bot.db") as conn:
                conn.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,))
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
    await message.answer(f"👥 Users: {users}\n📁 Uploads: {uploads}\n✨ Wishes: {wishes}")

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
    await message.answer(f"🔍 Users: {users}\n🔧 Commands: {cmds}\n✅ Healthy!")

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

# ========== BROADCAST (FIXED - copy_message for ALL media) ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    broadcast_state[user.id] = "waiting"
    await message.answer("📢 Send me ANY message, photo, video, document, audio, voice note, sticker, or GIF to broadcast!")

@dp.message(lambda msg: msg.from_user and msg.from_user.id in broadcast_state and broadcast_state[msg.from_user.id] == "waiting")
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
    success, failed = 0, 0
    
    for (uid,) in users:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
        except Exception as e:
            failed += 1
        await asyncio.sleep(0.03)
    
    await status.edit_text(f"✅ <b>Broadcast complete!</b>\nSuccess: {success}\nFailed: {failed}", parse_mode=ParseMode.HTML)

# ========== LAG ==========
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

# ========== ADVANCED /cm - CUSTOM MANAGER ==========
@dp.message(Command("cm"))
async def cm_cmd(message: Message):
    user, chat = await handle_common(message, "cm")
    if not user:
        return
    if user.id != OWNER_ID and not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            f"{header('CUSTOM MANAGER')}\n"
            f"⚙️ <b>Subcommands:</b>\n\n"
            f"<code>/cm status</code> - System overview\n"
            f"<code>/cm users</code> - User management\n"
            f"<code>/cm broadcast</code> - Broadcast tools\n"
            f"<code>/cm maintenance</code> - Maintenance\n"
            f"<code>/cm database</code> - Database tools\n"
            f"<code>/cm cult</code> - Tempest management",
            parse_mode=ParseMode.HTML
        )
        return
    
    sub = args[1].lower().strip()
    
    if sub == "status":
        uptime = format_uptime(int(time.time() - start_time))
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            users = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM command_logs")
            cmds = c.fetchone()[0]
        await message.answer(
            f"{header('SYSTEM STATUS')}\n"
            f"🕒 Uptime: {uptime}\n"
            f"💻 CPU: {cpu}%\n"
            f"💾 RAM: {ram}%\n"
            f"👥 Users: {users}\n"
            f"🔧 Commands: {cmds}",
            parse_mode=ParseMode.HTML
        )
    
    elif sub == "users":
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("SELECT user_id, first_name, uploads, commands, is_admin FROM users ORDER BY commands DESC LIMIT 15")
            users = c.fetchall()
        text = f"{header('USER MANAGEMENT')}\n"
        for uid, name, up, cmds, admin in users:
            badge = "👑" if admin else "👤"
            text += f"{badge} {name} ({uid})\n   📁{up} 🔧{cmds}\n"
        await message.answer(text, parse_mode=ParseMode.HTML)
    
    elif sub == "broadcast":
        await message.answer(
            f"{header('BROADCAST TOOLS')}\n"
            f"📢 /broadcast - Send message\n"
            f"Supports: Text, Photo, Video, Document, Audio, Voice, Sticker, GIF",
            parse_mode=ParseMode.HTML
        )
    
    elif sub == "maintenance":
        status = "🔴 ON" if maintenance_mode else "🟢 OFF"
        await message.answer(f"{header('MAINTENANCE')}\nStatus: {status}\nUse /maintenance to toggle", parse_mode=ParseMode.HTML)
    
    elif sub == "database":
        db_size = os.path.getsize("data/bot.db") / 1024
        await message.answer(
            f"{header('DATABASE TOOLS')}\n"
            f"📦 Size: {db_size:.1f} KB\n"
            f"💾 /backup - Download\n"
            f"📥 /rem - Restore\n"
            f"🧹 /clearlogs - Clear",
            parse_mode=ParseMode.HTML
        )
    
    elif sub == "cult":
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
            members = c.fetchone()[0]
            c.execute("SELECT SUM(sacrifices) FROM users WHERE cult_status != 'none'")
            total_sacs = c.fetchone()[0] or 0
        await message.answer(
            f"{header('TEMPEST CULT')}\n"
            f"🌀 Members: {members}\n"
            f"⚔️ Sacrifices: {total_sacs}",
            parse_mode=ParseMode.HTML
        )
    
    else:
        await message.answer("❌ Unknown! Use /cm for list.")

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
    await ensure_font()
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