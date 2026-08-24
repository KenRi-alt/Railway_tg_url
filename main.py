#!/usr/bin/env python3
# ========== TEMPEST BOT - CLEAN & FAST ==========
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
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, CallbackQuery, BufferedInputFile
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError

print("=" * 60)
print("TEMPEST BOT - CLEAN & FAST")
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

# Create directories
for dir_name in ["data", "temp", "backups", "profile_cards"]:
    Path(dir_name).mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
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

# ========== DATABASE - FAST ==========
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
            sacrifices INTEGER DEFAULT 0,
            curse_type TEXT DEFAULT 'none'
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
            command TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            wish_text TEXT,
            luck INTEGER
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS fate_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user1_name TEXT,
            user2_name TEXT,
            love_percentage INTEGER,
            created_date TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS fortunes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
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

# ========== FAST handle_common - NO ADS, NO LAG ==========
async def handle_common(message: Message, command_name: str):
    user = message.from_user
    chat = message.chat
    
    # Fast database update - no blocking
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                     (user.id, user.username or "", user.first_name or ""))
            c.execute("UPDATE users SET last_active = ? WHERE user_id = ?",
                     (datetime.now().isoformat(), user.id))
            conn.commit()
    except:
        pass
    
    # Log command
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("INSERT INTO command_logs (timestamp, user_id, command) VALUES (?, ?, ?)",
                     (datetime.now().isoformat(), user.id, command_name))
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

# ========== ANIME QUOTES ==========
ANIME_QUOTES = [
    "「Wake up to reality! Nothing ever goes as planned in this accursed world.」\n— Madara Uchiha",
    "「The longer you live, the more you realize that reality is just made of pain, suffering and emptiness.」\n— Madara Uchiha",
    "「People cannot show each other their true feelings. Fear, suspicion, and resentment never subside.」\n— Madara Uchiha",
    "「The only thing we're allowed to do is to believe that we won't regret the choice we made.」\n— Levi Ackerman",
    "「If you don't take risks, you can't create a future.」\n— Monkey D. Luffy",
    "「Power isn't determined by your size, but by the size of your heart and dreams.」\n— Monkey D. Luffy",
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

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

# ========== START ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = await handle_common(message, "start")
    if not user:
        return
    await message.answer(
        f"{ArtStyle.header('TEMPEST BOT')}\n"
        f"✨ Welcome {user.first_name}!\n\n"
        f"/help - Commands\n/profile - Stats\n/wish - Wish\n/tempest_join - Join"
    )

# ========== MYID ==========
@dp.message(Command("myid"))
async def myid_cmd(message: Message):
    await message.answer(f"🆔 Your ID: <code>{message.from_user.id}</code>\n👑 Owner: <code>{OWNER_ID}</code>", parse_mode=ParseMode.HTML)

# ========== HELP ==========
@dp.message(Command("help"))
async def help_cmd(message: Message):
    user, chat = await handle_common(message, "help")
    if not user:
        return
    await message.answer(
        f"{ArtStyle.header('COMMANDS')}\n"
        f"🔗 /link - Upload\n📥 /convert - Media URL\n"
        f"✨ /wish - Wish\n🔮 /fortune - Future\n"
        f"🎮 /dice - Dice\n🪙 /flip - Coin\n"
        f"💑 /fate - Love\n👤 /profile - Stats\n"
        f"🔐 /encrypt - Encrypt\n🌀 /tempest_join - Cult\n"
        f"📜 /tempest_story - Lore\n🌀 /tempest_creed - Members\n"
        f"⛩️ /shrine - Group shrine\n⚡ /curse - Curse\n"
        f"🌍 /time [country] - World time\n📝 /word - DOCX"
    )

# ========== ADMIN HELP ==========
@dp.message(Command("admin_help"))
async def admin_help_cmd(message: Message):
    user, chat = await handle_common(message, "admin_help")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    await message.answer(
        f"{ArtStyle.header('ADMIN')}\n"
        f"/ping - Status\n/stats - Stats\n/broadcast - Msg all\n"
        f"/lag - Glitch\n/disable - Disable cmd\n\n"
        f"👑 OWNER:\n/query - Code\n/backup - Backup\n"
        f"/rem - Restore\n/restart - Reboot\n/logs - View logs\n"
        f"/maintenance - Toggle\n/clearlogs - Clear"
    )

# ========== TIME ==========
@dp.message(Command("time"))
async def time_cmd(message: Message):
    user, chat = await handle_common(message, "time")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🌍 Usage: /time japan\nAvailable: " + ", ".join(list(COUNTRY_TIMEZONES.keys())[:15]))
        return
    country = args[1].lower().strip()
    if country not in COUNTRY_TIMEZONES:
        await message.answer("❌ Country not found!")
        return
    tz_name = COUNTRY_TIMEZONES[country]
    try:
        if ZoneInfo:
            tz = ZoneInfo(tz_name)
            now = datetime.now(tz)
        else:
            now = datetime.utcnow()
        await message.answer(
            f"🌍 <b>{country.upper()}</b>\n🕐 {now.strftime('%H:%M:%S')}\n📅 {now.strftime('%A, %d %B %Y')}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

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
    msg = await message.answer("🔮 Reading destiny...")
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
        c.execute("INSERT INTO wishes (user_id, wish_text, luck) VALUES (?, ?, ?)", (user.id, args[1], luck))
        conn.commit()
    await msg.edit_text(f"{ArtStyle.header('WISH')}\n📜 {args[1][:100]}\n🎰 {stars} {luck}%\n📊 {result}")

# ========== FORTUNE ==========
@dp.message(Command("fortune"))
async def fortune_cmd(message: Message):
    user, chat = await handle_common(message, "fortune")
    if not user:
        return
    fortunes = [
        "🌟 Great things await you!",
        "🗝️ An important decision opens new doors!",
        "🦋 Transformation brings beautiful changes!",
        "🌊 The storm carries you to new adventures!",
        "🔆 Your positive energy attracts success!",
        "🌠 A wish you've made may soon come true!",
        "💕 True love will find you!",
        "📈 A promotion is on the horizon!",
        "🍀 Extraordinary luck surrounds you!",
        "💪 Your strength grows daily!",
    ]
    msg = await message.answer("🔮 Reading future...")
    await asyncio.sleep(1.5)
    fortune = random.choice(fortunes)
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO fortunes (user_id, fortune_text) VALUES (?, ?)", (user.id, fortune))
        conn.commit()
    await msg.edit_text(f"{ArtStyle.header('FORTUNE')}\n<i>\"{fortune}\"</i>", parse_mode=ParseMode.HTML)

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
    msg = await message.answer("🪙 Flipping...")
    await asyncio.sleep(0.5)
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}!</b>", parse_mode=ParseMode.HTML)

# ========== FATE ==========
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
        c.execute("SELECT DISTINCT user_id, first_name FROM users WHERE user_id IN (SELECT user_id FROM command_logs WHERE command = 'fate') LIMIT 50")
        members = c.fetchall()
    if len(members) < 2:
        await message.answer("❌ Not enough members!")
        return
    msg = await message.answer("💫 Choosing lovers...")
    await asyncio.sleep(2)
    lover1 = random.choice(members)
    lover2 = random.choice(members)
    while lover2[0] == lover1[0]:
        lover2 = random.choice(members)
    love = random.randint(50, 100)
    quote = random.choice(ANIME_QUOTES)
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO fate_pairs (chat_id, user1_name, user2_name, love_percentage, created_date) VALUES (?, ?, ?, ?, ?)",
                 (chat.id, lover1[1], lover2[1], love, datetime.now().isoformat()))
        conn.commit()
    await msg.edit_text(
        f"{ArtStyle.header('FATE')}\n"
        f"💘 <b>{lover1[1]}</b> & <b>{lover2[1]}</b>\n"
        f"💖 {love}% Love\n\n"
        f"<i>{quote}</i>",
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
        row = c.fetchone()
    if row:
        uploads, cmds, rank, sacs, curse = row
    else:
        uploads = cmds = sacs = 0
        rank = "Mortal"
        curse = "none"
    text = f"{ArtStyle.header('PROFILE')}\n👤 {user.first_name}\n🆔 {user.id}\n📁 Uploads: {uploads}\n🌀 Rank: {rank}\n⚔️ Sacrifices: {sacs}\n⚡ Curse: {curse}"
    await message.answer(text, parse_mode=ParseMode.HTML)

# ========== ENCRYPT ==========
@dp.message(Command("encrypt"))
async def encrypt_cmd(message: Message):
    user, chat = await handle_common(message, "encrypt")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔐 Usage: /encrypt [text]")
        return
    encrypted = base64.b64encode(args[1].encode()).decode()
    await message.answer(f"🔐 <code>{encrypted}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("decrypt"))
async def decrypt_cmd(message: Message):
    user, chat = await handle_common(message, "decrypt")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔓 Usage: /decrypt [text]")
        return
    try:
        decrypted = base64.b64decode(args[1].encode()).decode()
        await message.answer(f"🔓 {decrypted}")
    except:
        await message.answer("❌ Invalid!")

# ========== TEMPEST JOIN ==========
@dp.message(Command("tempest_join"))
async def tempest_join_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_join")
    if not user:
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        result = c.fetchone()
        if result and result[0] != 'none':
            await message.answer("🌀 Already in Tempest!")
            return
        c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', sacrifices = 3 WHERE user_id = ?", (user.id,))
        conn.commit()
    msg = await message.answer("🌀 <b>INITIATING BLOOD PACT...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1.5)
    await msg.edit_text("🩸 <b>Drawing sigils...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1.5)
    await msg.edit_text("⚡ <b>TEMPEST AWAKENS!</b>\n\n🌀 Welcome, Blood Initiate!\n⚔️ Sacrifices: 3", parse_mode=ParseMode.HTML)

# ========== TEMPEST STORY ==========
@dp.message(Command("tempest_story"))
async def tempest_story_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_story")
    if not user:
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        result = c.fetchone()
    if not result or result[0] == 'none':
        await message.answer("🌀 Join first with /tempest_join")
        return
    msg = await message.answer("📜 Opening archives...")
    await asyncio.sleep(2)
    chapters = [
        ("CHAPTER 1", "In the void, RAVIJAH emerged from the first lightning..."),
        ("CHAPTER 2", "Three became one. The Blood Altar was built..."),
        ("CHAPTER 3", "The storm evolved. Your uploads are sacrifices..."),
    ]
    for title, content in chapters:
        await msg.edit_text(f"<b>{title}</b>\n<i>{content}</i>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(6)
    await msg.edit_text("<b>We are the eternal storm.</b>", parse_mode=ParseMode.HTML)

# ========== TEMPEST CREED ==========
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
    text = f"{ArtStyle.header('TEMPEST CREED')}\n"
    for i, (name, rank, sacs) in enumerate(members, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else "👤"
        text += f"{medal} {name} - {rank} (⚔️{sacs})\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

# ========== SHRINE ==========
@dp.message(Command("shrine"))
async def shrine_cmd(message: Message):
    user, chat = await handle_common(message, "shrine")
    if not user:
        return
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("⛩️ Groups only!")
        return
    await message.answer(f"⛩️ <b>TEMPEST SHRINE</b>\n📍 {chat.title}\n<i>The shrine watches over...</i>", parse_mode=ParseMode.HTML)

# ========== CURSE ==========
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
        c = conn.cursor()
        c.execute("UPDATE users SET curse_type = 'Bad Luck' WHERE user_id = ?", (target.id,))
        conn.commit()
    await message.reply(f"⚡ <b>{target.first_name}</b> is cursed!", parse_mode=ParseMode.HTML)

# ========== WORD ==========
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
        doc.add_paragraph(f"Created by: {user.first_name}")
        doc.add_paragraph(args[1])
        filename = f"temp/word_{user.id}.docx"
        doc.save(filename)
        await msg.delete()
        await message.answer_document(FSInputFile(filename))
        os.remove(filename)
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

# ========== LINK/UPLOAD ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")
    if not user:
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
            response = await client.get(url)
        
        result = await upload_to_catbox(response.content, file_name)
        if result['success']:
            with sqlite3.connect("data/bot.db") as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,))
                conn.commit()
            await msg.edit_text(f"✅ {file_type} uploaded!\n🔗 <code>{result['url']}</code>", parse_mode=ParseMode.HTML)
        else:
            await msg.edit_text("❌ Upload failed")
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

# ========== CONVERT ==========
@dp.message(Command("convert"))
async def convert_cmd(message: Message):
    user, chat = await handle_common(message, "convert")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📥 Usage: /convert [URL]\nOr reply to a photo with /convert")
        return
    if not YTDLP_AVAILABLE:
        await message.answer("❌ yt-dlp not installed!")
        return
    url = args[1]
    msg = await message.answer("📥 Downloading...")
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
        result = await upload_to_catbox(data, os.path.basename(filename))
        if result['success']:
            await msg.edit_text(f"✅ <code>{result['url']}</code>", parse_mode=ParseMode.HTML)
        else:
            await msg.edit_text("❌ Upload failed")
        os.remove(filename)
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

# ========== PING ==========
@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    user, chat = await handle_common(message, "ping")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer(f"🚫 Admin only. Your ID: {user.id}")
        return
    start = time.perf_counter()
    msg = await message.answer("🏓 Testing...")
    latency = int((time.perf_counter() - start) * 1000)
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    await msg.edit_text(f"🏓 {latency}ms\n💻 CPU: {cpu}%\n💾 RAM: {ram}%")

# ========== STATS ==========
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
    await message.answer(f"👥 Users: {users}\n📁 Uploads: {uploads}\n✨ Wishes: {wishes}")

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
    await message.answer("📢 Send me text, photo, video, or document to broadcast!")

@dp.message(F.text | F.photo | F.video | F.document)
async def handle_broadcast_content(message: Message):
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

# ========== LAG ==========
@dp.message(Command("lag"))
async def lag_cmd(message: Message):
    user, chat = await handle_common(message, "lag")
    if not user:
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

# ========== QUERY ==========
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

# ========== MAINTENANCE ==========
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

# ========== CLEARLOGS ==========
@dp.message(Command("clearlogs"))
async def clearlogs_cmd(message: Message):
    user, chat = await handle_common(message, "clearlogs")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer(f"🚫 Owner only. Your ID: {user.id}")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM command_logs")
        conn.commit()
    await message.answer("🧹 Logs cleared!")

# ========== LOGS ==========
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
    text = "📋 <b>RECENT LOGS</b>\n"
    for ts, uid, cmd in logs:
        text += f"• {ts[:19]} | {uid} | /{cmd}\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

# ========== BACKUP ==========
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

# ========== RESTART ==========
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

# ========== CANCEL ==========
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