#!/usr/bin/env python3
# ========== TEMPEST BOT - ULTIMATE RESTORED EDITION ==========
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

print("=" * 60)
print("TEMPEST BOT - ULTIMATE RESTORED EDITION INITIALIZING...")
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

# ========== ENSURE FONT EXISTS LOCALLY ==========
async def ensure_font():
    font_path = "fonts/font.ttf"
    if not os.path.exists(font_path):
        print("📥 Downloading reliable TTF font for card rendering...")
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Regular.ttf"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, follow_redirects=True)
                if r.status_code == 200:
                    with open(font_path, "wb") as f:
                        f.write(r.content)
                    print("✅ Font downloaded successfully!")
        except Exception as e:
            print(f"⚠️ Font download warning: {e}")

# ========== ART STYLE ==========
def header(t):
    return f"◤━━━━━━━━━━━━━━━━━━━━◥\n◇ {t} ◇\n◣━━━━━━━━━━━━━━━━━━━━◢"

def divider():
    return "━━━━━━━━━━━━━━━━━━━━"

ANIME_QUOTES = [
    "「Wake up to reality! Nothing ever goes as planned in this accursed world.」\n— Madara Uchiha",
    "「The longer you live, the more you realize that reality is just made of pain.」\n— Madara Uchiha",
    "「People cannot show each other their true feelings.」\n— Madara Uchiha",
    "「The only thing we're allowed to do is believe we won't regret our choice.」\n— Levi Ackerman",
    "「If you don't take risks, you can't create a future.」\n— Monkey D. Luffy",
]

COUNTRY_TIMEZONES = {
    "usa": "America/New_York", "uk": "Europe/London", "india": "Asia/Kolkata",
    "japan": "Asia/Tokyo", "china": "Asia/Shanghai", "uganda": "Africa/Kampala",
    "kenya": "Africa/Nairobi", "uae": "Asia/Dubai", "nigeria": "Africa/Lagos",
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

        c.execute('''CREATE TABLE IF NOT EXISTS groups (group_id INTEGER PRIMARY KEY, title TEXT, joined_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS uploads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, timestamp TEXT, file_url TEXT, file_type TEXT, file_size INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS command_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user_id INTEGER, chat_id INTEGER, command TEXT, success INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS wishes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, timestamp TEXT, wish_text TEXT, luck INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS fate_pairs (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user1_id INTEGER, user1_name TEXT, user2_id INTEGER, user2_name TEXT, love_percentage INTEGER, created_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS fortunes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, timestamp TEXT, fortune_text TEXT)''')
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, is_admin) VALUES (?, 'Owner', 1)", (OWNER_ID,))
        conn.commit()

init_db()

async def send_log(msg):
    try:
        await bot.send_message(LOG_CHANNEL_ID, msg[:4000])
    except:
        pass

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

# ========== 100% BULLETPROOF FONT LOADER ==========
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

# ========== FIXED PROFILE PICTURE FETCHER ==========
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
                avatar = avatar.resize((140, 140), Image.Resampling.LANCZOS)
                
                mask = Image.new("L", (140, 140), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, 140, 140), fill=255)
                
                output = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
                output.paste(avatar, (0, 0), mask=mask)
                return output
    except Exception as e:
        print(f"Avatar fetch error: {e}")
    
    # Styled fallback avatar badge if profile photo is private or unavailable
    fallback = Image.new("RGBA", (140, 140), (20, 30, 50, 255))
    draw = ImageDraw.Draw(fallback)
    draw.ellipse((0, 0, 140, 140), outline=(0, 255, 200), width=4)
    initial = first_name[0].upper() if first_name else "⚡"
    font = get_safe_font(65)
    draw.text((70, 70), initial, fill=(0, 255, 200), font=font, anchor="mm")
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
    
    font_name = get_safe_font(30)
    font_info = get_safe_font(20)
        
    draw.text((215, 80), str(username)[:22], fill=(255, 255, 255), font=font_name)
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
    
    font_title = get_safe_font(30)
    font_name = get_safe_font(22)
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

# ========== COMMANDS ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = await handle_common(message, "start")
    if not user:
        return
    await message.answer(f"{header('TEMPEST BOT')}\n✨ Welcome {user.first_name}!\n\n/help - View full command directory")

@dp.message(Command("myid"))
async def myid_cmd(message: Message):
    await message.answer(f"🆔 Your Telegram ID: <code>{message.from_user.id}</code>", parse_mode=ParseMode.HTML)

# ========== STORY RESTORED WITH BABLU & RAVIJAH ==========
@dp.message(Command("story"))
async def story_cmd(message: Message):
    user, chat = await handle_common(message, "story")
    if not user: return
    
    chapters = [
        ("📖 Chapter 1: Awakening in the Dark Eclipse", 
         "Keny Marcus opened his eyes in the obsidian realm of Tempest. Beside him stood his loyal companions Bablu and Ravijah. The sky burned with violet aura as a mysterious system interface flickered into existence."),
        ("⚔️ Chapter 2: The Guild of Shadows", 
         "With Bablu holding the vanguard and Ravijah orchestrating tactical formations, Keny forged the Tempest Guild. Shadows responded instantly as elite warriors aligned under their banner."),
        ("⚡ Chapter 3: Breach of the Citadel", 
         "Ravijah bypassed the enemy firewall while Bablu smashed through the fortress gates. Keny unleashed full kinetic voltage, shattering the defense grid in their first major victory."),
        ("👑 Chapter 4: Reign of the Tempest King", 
         "Standing atop the conquered spire together, Keny, Bablu, and Ravijah gazed across the infinite grid. The system synchronization reached 100%. The era of Tempest Guider had truly begun.")
    ]
    
    msg = await message.answer("🌀 Initiating Tempest Chronicles...")
    await asyncio.sleep(1)
    
    for title, text in chapters:
        await msg.edit_text(f"{header(title)}\n\n{text}")
        await asyncio.sleep(6)

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await handle_common(message, "help")
    await message.answer(
        f"{header('COMMAND DIRECTORY')}\n"
        f"🔗 /link - Upload any file\n📥 /convert - Convert media URL\n"
        f"✨ /wish - Make a wish\n🔮 /fortune - Future prediction\n"
        f"🎮 /dice - Roll dice\n🪙 /flip - Coin flip\n💑 /fate - Love compatibility\n"
        f"👤 /profile - Profile card with avatar\n📖 /story - Tempest Chronicles\n"
        f"🔐 /encrypt - XOR encrypt\n🔓 /decrypt - XOR decrypt\n🌍 /time - World clocks\n"
        f"👑 /admin_help - Admin commands"
    )

@dp.message(Command("admin_help"))
async def admin_help_cmd(message: Message):
    user, chat = await handle_common(message, "admin_help")
    if not user or (user.id != OWNER_ID and not await is_admin(user.id)):
        await message.answer("🚫 Admin only.")
        return
    await message.answer(
        f"{header('ADMIN DIRECTORY')}\n"
        f"/ping - Latency & system stats\n/stats - Database stats\n/broadcast - Broadcast message\n"
        f"/backup - Download database backup\n/rem - Restore database from file\n"
        f"/clearlogs - Clear command logs\n/cm - Custom manager utility\n\n"
        f"<b>OWNER COMMANDS:</b>\n"
        f"/query - Execute Python code (e.g. /query print(2+2))\n/restart - Reboot bot\n/maintenance - Toggle maintenance",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")
    if not user: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ Usage: /wish [your wish text]")
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
    if not user: return
    fortunes = ["🌟 Great things await you!", "🗝️ Hidden doors will open.", "🌊 A grand adventure approaches.", "📈 Success is near."]
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
    if not user: return
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("💑 Fate can only be checked in group chats!")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, first_name FROM users WHERE user_id != ? LIMIT 50", (user.id,))
        members = c.fetchall()
    if len(members) < 2:
        await message.answer("❌ Not enough registered members in this realm yet!")
        return
    msg = await message.answer("💫 Weaving threads of destiny...")
    l1, l2 = random.sample(members, 2)
    love = random.randint(50, 100)
    quote = random.choice(ANIME_QUOTES)
    card = await asyncio.to_thread(generate_fate_card_sync, l1[1], l2[1], love, quote)
    await msg.delete()
    await message.answer_photo(photo=BufferedInputFile(card, filename="fate.png"), caption=f"💑 <b>{l1[1]} & {l2[1]}</b> — 💖 {love}% Compatibility", parse_mode=ParseMode.HTML)

@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user, chat = await handle_common(message, "profile")
    if not user: return
    
    msg = await message.answer("⚡ Generating profile card...")
    
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT uploads, cult_rank FROM users WHERE user_id = ?", (user.id,))
        r = c.fetchone()
        c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (user.id,))
        wishes = c.fetchone()[0]
        
    uploads, rank = (r[0], r[1]) if r else (0, "Mortal")
    if rank == 'none' or not rank: rank = "Mortal"
        
    avatar_img = await fetch_user_avatar(user.id, user.first_name)
    card = await asyncio.to_thread(generate_profile_card_sync, user.first_name, user.id, rank, uploads, wishes, avatar_img)
    
    await msg.delete()
    await message.answer_photo(photo=BufferedInputFile(card, filename="profile.png"), caption=f"👤 <b>{user.first_name}'s Tempest ID Card</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("encrypt"))
async def encrypt_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔐 Usage: /encrypt [text]")
        return
    await message.answer(f"🔐 Encrypted:\n<code>{EncryptionEngine.encrypt(args[1])}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("decrypt"))
async def decrypt_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔓 Usage: /decrypt [cipher]")
        return
    dec = EncryptionEngine.decrypt(args[1])
    await message.answer(f"🔓 Decrypted:\n<code>{dec}</code>" if dec else "❌ Invalid ciphertext!", parse_mode=ParseMode.HTML)

@dp.message(Command("time"))
async def time_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or args[1].lower().strip() not in COUNTRY_TIMEZONES:
        await message.answer("🌍 Usage: /time [usa/uk/uganda/kenya/uae/japan/india]")
        return
    tz = COUNTRY_TIMEZONES[args[1].lower().strip()]
    now = datetime.now(ZoneInfo(tz)) if ZoneInfo else datetime.utcnow()
    await message.answer(f"🌍 <b>{args[1].upper()} TIME</b>\n🕐 {now.strftime('%H:%M:%S')}", parse_mode=ParseMode.HTML)

@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")
    if not user: return
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 Please use /link in our private chat!")
        return
    upload_waiting[user.id] = True
    await message.answer("📁 Ready! Send me any photo, video, document, audio, voice note, or sticker.")

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation)
async def handle_file(message: Message):
    user = message.from_user
    
    # Check if restoring DB
    if user.id in pending_restore:
        pending_restore.pop(user.id, None)
        if not message.document or not message.document.file_name.endswith(".db"):
            await message.answer("❌ Please send a valid `.db` file for restoration.")
            return
        msg = await message.answer("⏳ Restoring database...")
        try:
            file = await bot.get_file(message.document.file_id)
            url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.get(url)
            with open("data/bot.db", "wb") as f:
                f.write(r.content)
            await msg.edit_text("✅ Database restored successfully! Restart recommended (/restart).")
        except Exception as e:
            await msg.edit_text(f"❌ Restore failed: {e}")
        return

    if user.id not in upload_waiting:
        return
    upload_waiting.pop(user.id, None)
    msg = await message.answer("⏳ Uploading to Catbox...")
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
            await msg.edit_text(f"✅ <b>{file_type} Uploaded!</b>\n🔗 <code>{link}</code>", parse_mode=ParseMode.HTML)
        else:
            await msg.edit_text("❌ Catbox upload failed.")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    if message.from_user.id != OWNER_ID and not await is_admin(message.from_user.id): return
    start = time.perf_counter()
    msg = await message.answer("🏓 Testing...")
    latency = int((time.perf_counter() - start) * 1000)
    await msg.edit_text(f"🏓 Latency: {latency}ms\n💻 CPU: {psutil.cpu_percent()}%\n💾 RAM: {psutil.virtual_memory().percent}%")

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    if message.from_user.id != OWNER_ID and not await is_admin(message.from_user.id): return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        users = c.fetchone()[0] if c.execute("SELECT COUNT(*) FROM users").fetchone() else 0
        uploads = c.fetchone()[0] if c.execute("SELECT COUNT(*) FROM uploads").fetchone() else 0
    await message.answer(f"📊 <b>Stats</b>\n👥 Users: {users}\n📁 Uploads: {uploads}", parse_mode=ParseMode.HTML)

# ========== RESTORED ADMIN COMMANDS (/backup, /rem, /clearlogs, /cm) ==========
@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    if message.from_user.id != OWNER_ID and not await is_admin(message.from_user.id): return
    db_path = "data/bot.db"
    if os.path.exists(db_path):
        await message.answer_document(FSInputFile(db_path), caption="📦 <b>Tempest Database Backup</b>", parse_mode=ParseMode.HTML)
    else:
        await message.answer("❌ Database file not found!")

@dp.message(Command("rem"))
async def rem_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    pending_restore[message.from_user.id] = True
    await message.answer("📥 Please send the `.db` database file you want to restore.")

@dp.message(Command("clearlogs"))
async def clearlogs_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    with sqlite3.connect("data/bot.db") as conn:
        conn.execute("DELETE FROM command_logs")
        conn.commit()
    await message.answer("🧹 Command activity logs cleared successfully!")

@dp.message(Command("cm"))
async def cm_cmd(message: Message):
    if message.from_user.id != OWNER_ID and not await is_admin(message.from_user.id): return
    await message.answer(
        f"{header('CUSTOM MANAGER (CM)')}\n"
        f"⚙️ Active modules:\n"
        f"• Broadcast Engine: ONLINE\n"
        f"• Card Renderer: ONLINE\n"
        f"• Database Engine: ONLINE\n"
        f"• File Uploader: ONLINE",
        parse_mode=ParseMode.HTML
    )

# ========== BROADCAST SECTION ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    if message.from_user.id != OWNER_ID and not await is_admin(message.from_user.id): return
    broadcast_state[message.from_user.id] = "waiting"
    await message.answer("📢 Send me ANY message, photo, video, document, audio, voice note, sticker, or GIF to broadcast!")

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation)
async def handle_broadcast_media(message: Message):
    user = message.from_user
    if user.id not in broadcast_state or broadcast_state[user.id] != "waiting":
        return
    broadcast_state.pop(user.id, None)
    
    with sqlite3.connect("data/bot.db") as conn:
        users = conn.cursor().execute("SELECT user_id FROM users WHERE is_banned = 0").fetchall()
        
    status = await message.answer(f"📤 Broadcasting media to {len(users)} users...")
    success, failed = 0, 0
    
    for (uid,) in users:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
        except Exception as e:
            failed += 1
        await asyncio.sleep(0.03)
        
    await status.edit_text(f"✅ <b>Broadcast complete!</b>\nSuccess: {success}\nFailed: {failed}", parse_mode=ParseMode.HTML)

@dp.message(lambda msg: msg.from_user and msg.from_user.id in broadcast_state and broadcast_state[msg.from_user.id] == "waiting" and msg.text)
async def handle_broadcast_text(message: Message):
    user = message.from_user
    broadcast_state.pop(user.id, None)
    if message.text and message.text.startswith("/"): return
        
    with sqlite3.connect("data/bot.db") as conn:
        users = conn.cursor().execute("SELECT user_id FROM users WHERE is_banned = 0").fetchall()
        
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

@dp.message(Command("query"))
async def query_cmd(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("🚫 Owner only.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚡ Usage: /query [Python code]", parse_mode=ParseMode.HTML)
        return
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(args[1])
        output = buf.getvalue() or "Executed with no output."
        await message.answer(f"✅ <code>{output[:3000]}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    await message.answer("🔄 Restarting bot server now...")
    await send_log("🔄 Bot is restarting...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user = message.from_user
    upload_waiting.pop(user.id, None)
    broadcast_state.pop(user.id, None)
    pending_restore.pop(user.id, None)
    await message.answer("❌ Current operation cancelled.")

# ========== MAIN ENTRYPOINT ==========
async def main():
    await ensure_font()
    print("🚀 Tempest Bot starting polling...")
    await send_log("🚀 Bot started successfully!")
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            print(f"Polling error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
