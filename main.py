#!/usr/bin/env python3
# ========== TEMPEST BOT - ULTIMATE STABLE ==========
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
from datetime import datetime, timedelta
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, CallbackQuery, BufferedInputFile
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError

print("=" * 60)
print("🌀 TEMPEST BOT - ULTIMATE STABLE")
print("=" * 60)

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845  # Ensure this is correct

# Try importing yt-dlp
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False
    print("⚠️ yt-dlp not installed")

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
last_activity = datetime.now()

# ========== COMPACT ART STYLE ==========
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

# ========== DATABASE INIT ==========
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

        c.execute('''CREATE TABLE IF NOT EXISTS encrypted_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            original_text TEXT,
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

        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
                  (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))

        conn.commit()
        print("✅ Database initialized")

init_db()

# ========== FIXED LOG FUNCTION ==========
async def send_log(message: str):
    try:
        print(f"📢 LOG: {message[:100]}")
        await bot.send_message(LOG_CHANNEL_ID, message[:4000], parse_mode=ParseMode.HTML)
    except Exception as e:
        print(f"❌ Log error: {e}")

# ========== HELPER FUNCTIONS ==========
async def safe_answer_callback(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    try:
        await callback.answer(text, show_alert=show_alert)
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

    # Check disabled commands
    if command in disabled_commands:
        disabled_until = disabled_commands[command]
        if disabled_until > datetime.now():
            await message.answer(f"⛔ This command is disabled for {format_uptime(int((disabled_until - datetime.now()).total_seconds()))}")
            return None, None

    # Update user in DB
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE user_id = ?", (user.id,))
            if not c.fetchone():
                c.execute("INSERT INTO users (user_id, username, first_name, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                         (user.id, user.username, user.first_name, datetime.now().isoformat(), datetime.now().isoformat()))
            else:
                c.execute("UPDATE users SET last_active = ?, username = ?, first_name = ? WHERE user_id = ?",
                         (datetime.now().isoformat(), user.username, user.first_name, user.id))
            conn.commit()
    except:
        pass

    # Update group if in group
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        try:
            with sqlite3.connect("data/bot.db") as conn:
                c = conn.cursor()
                c.execute("SELECT group_id FROM groups WHERE group_id = ?", (chat.id,))
                if not c.fetchone():
                    c.execute("INSERT INTO groups (group_id, title, username, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                             (chat.id, chat.title, chat.username, datetime.now().isoformat(), datetime.now().isoformat()))
                else:
                    c.execute("UPDATE groups SET last_active = ?, title = ?, username = ? WHERE group_id = ?",
                             (datetime.now().isoformat(), chat.title, chat.username, chat.id))
                conn.commit()
        except:
            pass

    # Log command
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("INSERT INTO command_logs (timestamp, user_id, chat_id, chat_type, command, success) VALUES (?, ?, ?, ?, ?, ?)",
                      (datetime.now().isoformat(), user.id, chat.id, str(chat.type), command, 1))
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
            result = c.fetchone()
        return result and result[0] == 1
    except:
        return False

def save_bot_state():
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            now = datetime.now().isoformat()
            c.execute("DELETE FROM bot_state")
            for user_id, waiting in upload_waiting.items():
                if waiting:
                    c.execute("INSERT INTO bot_state (key, value, timestamp) VALUES (?, ?, ?)",
                             (f"upload_{user_id}", "1", now))
            conn.commit()
    except:
        pass

def load_bot_state():
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            upload_waiting.clear()
            c.execute("SELECT key FROM bot_state WHERE key LIKE 'upload_%'")
            for (key,) in c.fetchall():
                user_id = int(key.split("_")[1])
                upload_waiting[user_id] = True
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

# ========== PREMIUM PROFILE CARD ==========
class PremiumProfileCard:
    @staticmethod
    def create_gradient_background(width, height, color1=(15, 15, 35), color2=(45, 25, 85), color3=(25, 45, 75)):
        base = Image.new('RGBA', (width, height), color1)
        draw = ImageDraw.Draw(base)
        for y in range(height):
            ratio = y / height
            if ratio < 0.5:
                r = int(color1[0] + (color2[0] - color1[0]) * (ratio * 2))
                g = int(color1[1] + (color2[1] - color1[1]) * (ratio * 2))
                b = int(color1[2] + (color2[2] - color1[2]) * (ratio * 2))
            else:
                r = int(color2[0] + (color3[0] - color2[0]) * ((ratio - 0.5) * 2))
                g = int(color2[1] + (color3[1] - color2[1]) * ((ratio - 0.5) * 2))
                b = int(color2[2] + (color3[2] - color2[2]) * ((ratio - 0.5) * 2))
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        return base
    
    @staticmethod
    def create_vortex_pattern(draw, center_x, center_y, max_radius=200, color=(0, 255, 200, 40)):
        for angle in range(0, 360, 15):
            rad = math.radians(angle)
            x1 = center_x + int(max_radius * 0.3 * math.cos(rad))
            y1 = center_y + int(max_radius * 0.3 * math.sin(rad))
            x2 = center_x + int(max_radius * math.cos(rad))
            y2 = center_y + int(max_radius * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
    
    @staticmethod
    def generate_premium_card_sync(username, user_id, rank, avatar_bytes=None, stats=None):
        width, height = 900, 520
        canvas = PremiumProfileCard.create_gradient_background(width, height)
        draw = ImageDraw.Draw(canvas)
        
        # Grid
        for i in range(0, width, 40):
            draw.line([(i, 0), (i, height)], fill=(30, 35, 60, 50), width=1)
        for i in range(0, height, 40):
            draw.line([(0, i), (width, i)], fill=(30, 35, 60, 50), width=1)
        
        # Vortex
        PremiumProfileCard.create_vortex_pattern(draw, 730, 260, 180, (0, 255, 200, 30))
        
        # Glass panels
        glass_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass_layer)
        glass_draw.rounded_rectangle(
            [30, 30, width - 30, height - 30],
            radius=25, fill=(25, 25, 45, 180), outline=(138, 43, 226, 200), width=2
        )
        glass_draw.rounded_rectangle(
            [320, 320, 840, 440],
            radius=15, fill=(10, 10, 20, 150), outline=(0, 255, 200, 120), width=1
        )
        canvas = Image.alpha_composite(canvas, glass_layer)
        draw = ImageDraw.Draw(canvas)
        
        # Avatar
        avatar_size = 180
        avatar_x, avatar_y = 60, 70
        if avatar_bytes:
            try:
                avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
                avatar_img = ImageOps.fit(avatar_img, (avatar_size, avatar_size), Image.Resampling.LANCZOS)
            except:
                avatar_img = Image.new("RGBA", (avatar_size, avatar_size), (50, 50, 80, 255))
        else:
            avatar_img = Image.new("RGBA", (avatar_size, avatar_size), (50, 50, 80, 255))
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        draw.ellipse(
            [avatar_x - 5, avatar_y - 5, avatar_x + avatar_size + 5, avatar_y + avatar_size + 5],
            outline=(0, 255, 200, 255), width=4
        )
        canvas.paste(avatar_img, (avatar_x, avatar_y), mask)
        
        # Text
        try:
            title_font = ImageFont.truetype("fonts/Gothic.ttf", 42)
            body_font = ImageFont.truetype("fonts/Roboto.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
        draw.text((320, 80), username, fill=(255, 255, 255, 255), font=title_font)
        draw.text((320, 140), f"ID: {user_id}", fill=(180, 180, 210, 255), font=body_font)
        draw.text((320, 180), f"Rank: {rank}", fill=(0, 255, 200, 255), font=body_font)
        if stats:
            stats_text = f"Uploads: {stats.get('uploads', 0)} | Wishes: {stats.get('wishes', 0)}"
            draw.text((340, 345), "STATISTICS", fill=(140, 140, 170, 255), font=body_font)
            draw.text((340, 380), stats_text, fill=(255, 215, 0, 255), font=body_font)
        
        output_buffer = io.BytesIO()
        canvas.convert("RGB").save(output_buffer, format="PNG", quality=95)
        output_buffer.seek(0)
        return output_buffer.getvalue()
    
    @staticmethod
    async def generate_premium_card(username, user_id, rank, avatar_bytes=None, stats=None):
        return await asyncio.to_thread(
            PremiumProfileCard.generate_premium_card_sync,
            username, user_id, rank, avatar_bytes, stats
        )

# ========== ENCRYPTION ==========
class EncryptionEngine:
    @staticmethod
    def xor_encrypt(text, key="TEMPEST"):
        result = []
        key_length = len(key)
        for i, char in enumerate(text):
            result.append(chr(ord(char) ^ ord(key[i % key_length])))
        return ''.join(result)
    
    @staticmethod
    def base64_encode(text):
        return base64.b64encode(text.encode()).decode()
    
    @staticmethod
    def base64_decode(text):
        try:
            return base64.b64decode(text.encode()).decode()
        except:
            return None
    
    @staticmethod
    def multi_layer_encrypt(text):
        encrypted = EncryptionEngine.xor_encrypt(text)
        return EncryptionEngine.base64_encode(encrypted)
    
    @staticmethod
    def multi_layer_decrypt(text):
        decoded = EncryptionEngine.base64_decode(text)
        if decoded is None:
            return None
        return EncryptionEngine.xor_encrypt(decoded)

# ========== START COMMAND ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = await handle_common(message, "start")
    if not user:
        return
    await message.answer(
        f"{ArtStyle.header('TEMPEST BOT')}\n"
        f"✨ <b>Welcome {user.first_name}!</b>\n\n"
        f"🔗 Upload - /link\n"
        f"✨ Wish - /wish\n"
        f"🎮 Games - /dice /flip\n"
        f"👤 Profile - /profile\n"
        f"🔐 Encrypt - /encrypt\n"
        f"📥 Convert - /convert\n"
        f"🌀 Tempest - /tempest_join\n"
        f"📚 Help - /help",
        parse_mode=ParseMode.HTML
    )
    await send_log(f"👤 New user: {user.first_name} ({user.id})")

# ========== HELP COMMAND ==========
@dp.message(Command("help"))
async def help_cmd(message: Message):
    user, chat = await handle_common(message, "help")
    if not user:
        return
    help_text = f"""{ArtStyle.header('COMMANDS')}
🔗 <b>UPLOAD</b>
<code>/link</code> - Upload file
<code>/convert</code> - Media from URL
🌟 <b>FUN</b>
<code>/wish</code> - Make wish
<code>/dice</code> - Roll dice
<code>/flip</code> - Flip coin
<code>/fate</code> - Find love
👤 <b>PROFILE</b>
<code>/profile</code> - View stats
🔐 <b>SECURITY</b>
<code>/encrypt</code> - Encrypt msg
<code>/decrypt</code> - Decrypt msg
🌀 <b>TEMPEST</b>
<code>/tempest_join</code> - Join cult
<code>/tempest_story</code> - Read lore
<code>/tempest_creed</code> - Members
<code>/shrine</code> - Group shrine
<code>/curse</code> - Curse user
📝 <b>UTILITY</b>
<code>/word</code> - Text to DOCX
{ArtStyle.divider()}
🌀 <i>The storm flows through you</i>"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== ADMIN HELP ==========
@dp.message(Command("admin_help"))
async def admin_help_cmd(message: Message):
    user, chat = await handle_common(message, "admin_help")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    help_text = f"""{ArtStyle.header('ADMIN COMMANDS')}
👑 <b>ADMIN</b>
<code>/ping</code> - System status
<code>/stats</code> - Statistics
<code>/users</code> - User list
<code>/scan</code> - Scan database
<code>/broadcast</code> - Message all
<code>/disable</code> - Disable cmd
<code>/lag</code> - Glitch effect
⚡ <b>OWNER</b>
<code>/pro</code> - Make admin
<code>/backup</code> - Backup DB
<code>/rem</code> - Restore DB
<code>/restart</code> - Reboot
{ArtStyle.divider()}"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== DISABLE COMMAND ==========
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
        await message.answer("Usage: /disable [command] [duration_minutes]\nExample: /disable wish 30")
        return
    command = args[1].replace("/", "")
    duration = 10
    if len(args) > 2 and args[2].isdigit():
        duration = int(args[2])
    disabled_until = datetime.now() + timedelta(minutes=duration)
    disabled_commands[command] = disabled_until
    await message.answer(f"⛔ <b>{command}</b> disabled for {duration} minutes!")
    await send_log(f"⛔ Command {command} disabled for {duration}min by {user.first_name}")

# ========== WISH COMMAND ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"{ArtStyle.header('WISH')}\n✨ <b>Usage:</b> <code>/wish your wish</code>", parse_mode=ParseMode.HTML)
        return
    # Curse check
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT curse_type FROM users WHERE user_id = ?", (user.id,))
        curse_result = c.fetchone()
        curse_type = curse_result[0] if curse_result else "none"
    curse_penalty = 0
    curse_message = ""
    if curse_type != "none":
        curse_penalty = random.randint(15, 30)
        curse_message = f"\n⚡ Curse: -{curse_penalty}%"
    msg = await message.answer("🔮 <b>Consulting the storm...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    await msg.edit_text("✨ <b>Reading destiny...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    base_luck = random.randint(1, 100)
    luck = max(1, base_luck - curse_penalty)
    stars = "⭐" * (luck // 10) + "☆" * (10 - luck // 10)
    if luck >= 90:
        result_text = "🎊 EXCELLENT!"
    elif luck >= 70:
        result_text = "😊 VERY GOOD!"
    elif luck >= 50:
        result_text = "👍 GOOD!"
    elif luck >= 30:
        result_text = "🤔 AVERAGE"
    elif luck >= 10:
        result_text = "😟 LOW"
    else:
        result_text = "💀 VERY LOW"
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
                 (user.id, datetime.now().isoformat(), args[1], luck))
        conn.commit()
    await msg.edit_text(
        f"{ArtStyle.header('WISH RESULT')}\n"
        f"📜 <b>Wish:</b> {args[1][:100]}\n"
        f"🎰 <b>Luck:</b> {stars} {luck}%{curse_message}\n"
        f"📊 <b>Verdict:</b> {result_text}",
        parse_mode=ParseMode.HTML
    )

# ========== DICE COMMAND (Native Telegram dice) ==========
@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    user, chat = await handle_common(message, "dice")
    if not user:
        return
    await message.answer_dice(emoji="🎲")

# ========== FLIP COMMAND (Native Telegram dart for heads/tails) ==========
@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    user, chat = await handle_common(message, "flip")
    if not user:
        return
    # Use dart emoji as a coin flip alternative (heads/tails via result)
    sent = await message.answer_dice(emoji="🎯")
    # The result will be 1-6; we can map to heads/tails later if needed, but native animation is fine.

# ========== PROFILE COMMAND ==========
@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user, chat = await handle_common(message, "profile")
    if not user:
        return
    msg = await message.answer("🎨 <b>Generating profile...</b>", parse_mode=ParseMode.HTML)
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT uploads, commands, joined_date, curse_type, cult_rank, sacrifices FROM users WHERE user_id = ?", (user.id,))
        row = c.fetchone()
        if row:
            uploads, cmds, joined, curse_type, cult_rank, sacrifices = row
            c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (user.id,))
            wishes = c.fetchone()[0] or 0
        else:
            uploads = cmds = wishes = sacrifices = 0
            curse_type = "none"
            cult_rank = "none"
    # Get avatar
    avatar_bytes = None
    try:
        user_photos = await bot.get_user_profile_photos(user.id, limit=1)
        if user_photos.total_count > 0:
            file_id = user_photos.photos[0][-1].file_id
            file_info = await bot.get_file(file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            avatar_bytes = downloaded_file.read()
    except:
        pass
    stats = {'uploads': uploads, 'wishes': wishes, 'commands': cmds, 'sacrifices': sacrifices}
    rank = cult_rank if cult_rank != "none" else "Mortal"
    image_bytes = await PremiumProfileCard.generate_premium_card(
        username=user.first_name,
        user_id=user.id,
        rank=rank,
        avatar_bytes=avatar_bytes,
        stats=stats
    )
    photo_file = BufferedInputFile(image_bytes, filename=f"profile_{user.id}.png")
    await msg.delete()
    await message.answer_photo(photo=photo_file, caption=f"👤 <b>{user.first_name}</b>\n🌀 Tempest Profile", parse_mode=ParseMode.HTML)

# ========== ENCRYPT/DECRYPT ==========
@dp.message(Command("encrypt"))
async def encrypt_cmd(message: Message):
    user, chat = await handle_common(message, "encrypt")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔐 Usage: /encrypt [text]")
        return
    encrypted = EncryptionEngine.multi_layer_encrypt(args[1])
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO encrypted_messages (user_id, timestamp, original_text, encrypted_text, method) VALUES (?, ?, ?, ?, ?)",
                 (user.id, datetime.now().isoformat(), args[1], encrypted, "xor"))
        conn.commit()
    await message.answer(f"🔐 <b>Encrypted:</b>\n<code>{encrypted}</code>", parse_mode=ParseMode.HTML)

@dp.message(Command("decrypt"))
async def decrypt_cmd(message: Message):
    user, chat = await handle_common(message, "decrypt")
    if not user:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔓 Usage: /decrypt [text]")
        return
    decrypted = EncryptionEngine.multi_layer_decrypt(args[1])
    if decrypted:
        await message.answer(f"🔓 <b>Decrypted:</b>\n{decrypted}", parse_mode=ParseMode.HTML)
    else:
        await message.answer("❌ Invalid encrypted text!")

# ========== CONVERT COMMAND ==========
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
        # Run yt-dlp in executor
        def download():
            ydl_opts = {
                'outtmpl': 'media/%(title)s.%(ext)s',
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
    save_bot_state()
    await message.answer("📁 <b>Send me any file now!</b>\n❌ /cancel to stop", parse_mode=ParseMode.HTML)

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation | F.video_note)
async def handle_file(message: Message):
    user = message.from_user
    if user.id not in upload_waiting or not upload_waiting[user.id]:
        return
    upload_waiting[user.id] = False
    save_bot_state()
    msg = await message.answer("⏳ <b>Processing...</b>", parse_mode=ParseMode.HTML)
    try:
        file_id = None
        file_type = "Unknown"
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
            file_name = message.audio.file_name or file_name + ".mp3"
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
            file_name = message.animation.file_name or file_name + ".gif"
        elif message.video_note:
            file_id = message.video_note.file_id
            file_type = "Video Note"
            file_name += ".mp4"
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
            await msg.edit_text(f"❌ Upload failed: {result.get('error', 'Unknown')}")
            return
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,))
            c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
            cult = c.fetchone()
            if cult and cult[0] != 'none':
                c.execute("UPDATE users SET sacrifices = sacrifices + 1 WHERE user_id = ?", (user.id,))
            c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)",
                     (user.id, datetime.now().isoformat(), result['url'], file_type, len(response.content)))
            conn.commit()
        size_kb = len(response.content) / 1024
        size_mb = size_kb / 1024
        size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
        keyboard = InlineKeyboardBuilder()
        keyboard.add(types.InlineKeyboardButton(text="📋 Copy Link", callback_data=f"copy_{result['url']}"))
        await msg.edit_text(
            f"✅ <b>Upload Complete!</b>\n"
            f"📁 Type: {file_type}\n"
            f"💾 Size: {size_text}\n\n"
            f"🔗 <code>{result['url']}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.as_markup()
        )
        await send_log(f"📁 Upload by {user.first_name}: {result['url']}")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")
        traceback.print_exc()

@dp.callback_query(F.data.startswith("copy_"))
async def handle_copy(callback: CallbackQuery):
    url = callback.data[5:]
    await safe_answer_callback(callback, f"Link copied!\n{url}", show_alert=True)

# ========== CANCEL ==========
@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user, chat = await handle_common(message, "cancel")
    if not user:
        return
    cancelled = False
    if user.id in upload_waiting:
        upload_waiting.pop(user.id, None)
        save_bot_state()
        cancelled = True
    if user.id in broadcast_state:
        broadcast_state.pop(user.id, None)
        cancelled = True
    if user.id in pending_restore:
        pending_restore.pop(user.id, None)
        cancelled = True
    if cancelled:
        await message.answer("❌ Operation cancelled!")
    else:
        await message.answer("🤔 Nothing to cancel!")

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
        if result and result[0] != "none":
            await message.answer("🌀 You are already in the Tempest!")
            return
    ritual_msgs = [
        "🌀 <b>INITIATING BLOOD PACT...</b>",
        "🩸 <b>Drawing sigils...</b>",
        "⚡ <b>Channeling storm...</b>",
        "🌑 <b>The void responds...</b>",
        "🔥 <b>Sacrifice offered...</b>",
        "🌀 <b>TEMPEST AWAKENS...</b>"
    ]
    msg = await message.answer("🌀 <b>Preparing ritual...</b>", parse_mode=ParseMode.HTML)
    for text in ritual_msgs:
        await asyncio.sleep(1.5)
        try:
            await msg.edit_text(text, parse_mode=ParseMode.HTML)
        except:
            pass
    await asyncio.sleep(1)
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
                 (datetime.now().isoformat(), user.id))
        conn.commit()
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
    await send_log(f"🌀 {user.first_name} joined the Tempest!")

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
    if not result or result[0] == "none":
        await message.answer("🌀 Join the Tempest first with /tempest_join")
        return
    chapters = [
        {"title": "CHAPTER 1: THE BEGINNING",
         "content": "In the void before time, there was only silence.\n\nBut from the first lightning, RAVIJAH emerged. Born of storm itself, he gathered the forgotten thunder and whispered rebellion.",
         "emoji": "⚡"},
        {"title": "CHAPTER 2: THE BLOOD OATH",
         "content": "Three became one - Ravijah, Bablu, and Keny.\n\nThey built the Temple of Howling Winds and created the Blood Altar. The first sacrifices were made.",
         "emoji": "🩸"},
        {"title": "CHAPTER 3: THE DIGITAL AGE",
         "content": "The storm evolved. Lightning now flows through fiber optics.\n\nYour uploads are sacrifices. Your data is power. Your loyalty is eternal.",
         "emoji": "💻"}
    ]
    msg = await message.answer("📜 <b>Opening Tempest Archives...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(2)
    for i, chapter in enumerate(chapters):
        progress = "▓" * (i + 1) + "░" * (len(chapters) - i - 1)
        await msg.edit_text(f"📜 <b>Loading...</b>\n[{progress}] {i+1}/{len(chapters)}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)
        await msg.edit_text(
            f"{ArtStyle.header(chapter['title'])}\n"
            f"{chapter['emoji']} <i>{chapter['content']}</i>",
            parse_mode=ParseMode.HTML
        )
        await asyncio.sleep(6)
    await msg.edit_text(
        f"{ArtStyle.header('TEMPEST LORE')}\n"
        f"<i>\"We do not recruit. We remember.\n"
        f"We do not convert. We awaken.\n"
        f"We are the eternal storm.\"</i>",
        parse_mode=ParseMode.HTML
    )

# ========== TEMPEST CREED ==========
@dp.message(Command("tempest_creed"))
async def tempest_creed_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_creed")
    if not user:
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, first_name, username, cult_rank, sacrifices FROM users WHERE cult_status != 'none' ORDER BY sacrifices DESC LIMIT 20")
        members = c.fetchall()
        c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
        total = c.fetchone()[0] or 0
        c.execute("SELECT SUM(sacrifices) FROM users WHERE cult_status != 'none'")
        total_sacs = c.fetchone()[0] or 0
    if not members:
        await message.answer("No Tempest members yet. Be the first with /tempest_join!")
        return
    text = f"{ArtStyle.header('TEMPEST CREED')}\n"
    text += f"📊 Members: {total}\n"
    text += f"⚔️ Sacrifices: {total_sacs}\n\n"
    text += "<b>TOP MEMBERS:</b>\n"
    ranks = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, (uid, name, uname, rank, sacs) in enumerate(members[:10], 1):
        medal = ranks.get(i, "👤")
        username = f"@{uname}" if uname else ""
        text += f"{medal} <b>{name}</b> - {rank} (⚔️{sacs}) {username}\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

# ========== SHRINE ==========
@dp.message(Command("shrine"))
async def shrine_cmd(message: Message):
    user, chat = await handle_common(message, "shrine")
    if not user:
        return
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("🌀 The Shrine can only be erected in groups!")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("""
            SELECT u.first_name, u.cult_rank, u.sacrifices 
            FROM users u 
            WHERE u.cult_status != 'none' 
            AND u.user_id IN (
                SELECT user_id FROM command_logs WHERE chat_id = ?
            )
            ORDER BY u.sacrifices DESC
        """, (chat.id,))
        members = c.fetchall()
    if members:
        members_text = "\n".join([f"• {name} - {rank} (⚔️{sacs})" for name, rank, sacs in members[:5]])
    else:
        members_text = "No Tempest members here yet!"
    await message.answer(
        f"{ArtStyle.header('TEMPEST SHRINE')}\n"
        f"📍 <b>{chat.title}</b>\n"
        f"👤 Called by: {user.first_name}\n\n"
        f"<b>Members:</b>\n{members_text}\n\n"
        "<i>The shrine watches over...</i>",
        parse_mode=ParseMode.HTML
    )

# ========== CURSE ==========
@dp.message(Command("curse"))
async def curse_cmd(message: Message):
    user, chat = await handle_common(message, "curse")
    if not user:
        return
    if not message.reply_to_message:
        await message.answer("🌀 Reply to a user's message to curse them!")
        return
    target = message.reply_to_message.from_user
    if target.id == user.id:
        await message.answer("🌀 You cannot curse yourself!")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET curse_type = 'Bad Luck', curse_time = ? WHERE user_id = ?",
                 (datetime.now().isoformat(), target.id))
        conn.commit()
    await message.reply(f"⚡ <b>CURSE BESTOWED!</b>\n👤 Target: {target.first_name}\n🌀 Curse: Bad Luck", parse_mode=ParseMode.HTML)

# ========== REMOVE CURSE ==========
@dp.message(Command("remove_curse"))
async def remove_curse_cmd(message: Message):
    user, chat = await handle_common(message, "remove_curse")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    if not message.reply_to_message:
        await message.answer("🌀 Reply to a user's message to remove curse!")
        return
    target = message.reply_to_message.from_user
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET curse_type = 'none', curse_time = NULL WHERE user_id = ?", (target.id,))
        conn.commit()
    await message.reply(f"✅ Curse removed from {target.first_name}!")

# ========== FATE (Couple Pairing) ==========
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
        c.execute("""
            SELECT user1_name, user2_name, love_percentage 
            FROM fate_pairs 
            WHERE chat_id = ? AND created_date >= ?
        """, (chat.id, (datetime.now() - timedelta(hours=24)).isoformat()))
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
        # Get members
        c.execute("""
            SELECT DISTINCT u.user_id, u.first_name 
            FROM users u 
            WHERE u.user_id IN (
                SELECT user_id FROM command_logs WHERE chat_id = ?
            )
            AND u.is_banned = 0
            LIMIT 100
        """, (chat.id,))
        members = c.fetchall()
    if len(members) < 2:
        await message.answer("❌ Not enough members! Need at least 2 active users.")
        return
    msg = await message.answer("💫 <b>The storm is choosing lovers...</b>", parse_mode=ParseMode.HTML)
    animations = [
        "💘 <b>Scanning members...</b>",
        "💝 <b>Analyzing compatibility...</b>",
        "💖 <b>Calculating love...</b>",
        "💕 <b>Consulting tempest...</b>",
        "💗 <b>Fate is deciding...</b>"
    ]
    for anim in animations:
        await asyncio.sleep(1)
        await msg.edit_text(anim, parse_mode=ParseMode.HTML)
    lover1 = random.choice(members)
    lover2 = random.choice(members)
    while lover2[0] == lover1[0]:
        lover2 = random.choice(members)
    love_percentage = random.randint(50, 100)
    if love_percentage >= 90:
        love_message = "💞 SOULMATES!"
    elif love_percentage >= 80:
        love_message = "💖 PERFECT MATCH!"
    elif love_percentage >= 70:
        love_message = "💕 GREAT MATCH!"
    elif love_percentage >= 60:
        love_message = "💗 GOOD MATCH!"
    else:
        love_message = "💓 MODERATE MATCH!"
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO fate_pairs (chat_id, user1_id, user1_name, user2_id, user2_name, love_percentage, created_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (chat.id, lover1[0], lover1[1], lover2[0], lover2[1], love_percentage, datetime.now().isoformat()))
        conn.commit()
    await msg.edit_text(
        f"{ArtStyle.header('FATE DECIDED')}\n"
        f"💑 <b>COUPLE OF THE STORM</b>\n\n"
        f"💘 <b>Lover 1:</b> {lover1[1]}\n"
        f"💘 <b>Lover 2:</b> {lover2[1]}\n\n"
        f"💖 <b>Love:</b> {love_percentage}%\n"
        f"✨ <b>Verdict:</b> {love_message}\n\n"
        "<i>Love conquers all!</i>",
        parse_mode=ParseMode.HTML
    )

# ========== WORD COMMAND ==========
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

# ========== PING ==========
@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    user, chat = await handle_common(message, "ping")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    msg = await message.answer("🏓 <b>Testing...</b>", parse_mode=ParseMode.HTML)
    start = time.perf_counter()
    await bot.get_me()
    bot_latency = int((time.perf_counter() - start) * 1000)
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    uptime = format_uptime(int(time.time() - start_time))
    await msg.edit_text(
        f"{ArtStyle.header('SYSTEM STATUS')}\n"
        f"⚡ Latency: {bot_latency}ms\n"
        f"🕒 Uptime: {uptime}\n\n"
        f"💻 CPU: {cpu}%\n"
        f"💾 RAM: {memory.used // (1024**2)}MB / {memory.total // (1024**2)}MB\n"
        f"💿 Disk: {disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB\n"
        f"🎯 Status: {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}",
        parse_mode=ParseMode.HTML
    )

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
        users = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM groups")
        groups = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM uploads")
        uploads = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM wishes")
        wishes = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
        tempest = c.fetchone()[0] or 0
    await message.answer(
        f"{ArtStyle.header('STATISTICS')}\n"
        f"👥 Users: {users}\n"
        f"👥 Groups: {groups}\n"
        f"🌀 Tempest: {tempest}\n"
        f"📁 Uploads: {uploads}\n"
        f"✨ Wishes: {wishes}\n"
        f"🕒 Uptime: {format_uptime(int(time.time() - start_time))}",
        parse_mode=ParseMode.HTML
    )

# ========== SCAN ==========
@dp.message(Command("scan"))
async def scan_cmd(message: Message):
    user, chat = await handle_common(message, "scan")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    msg = await message.answer("🔍 <b>Scanning database...</b>", parse_mode=ParseMode.HTML)
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE last_active >= ?", ((datetime.now() - timedelta(days=7)).isoformat(),))
        active_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
        tempest_members = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM uploads")
        total_uploads = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM command_logs")
        total_commands = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM groups")
        total_groups = c.fetchone()[0]
    await msg.edit_text(
        f"{ArtStyle.header('DATABASE SCAN')}\n"
        f"👥 Users: {total_users}\n"
        f"🟢 Active (7d): {active_users}\n"
        f"🌀 Tempest: {tempest_members}\n"
        f"👥 Groups: {total_groups}\n"
        f"📁 Uploads: {total_uploads}\n"
        f"🔧 Commands: {total_commands}\n\n"
        "✅ Scan complete!",
        parse_mode=ParseMode.HTML
    )

# ========== USERS ==========
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
        c.execute("SELECT user_id, first_name, username, uploads, commands FROM users ORDER BY last_active DESC LIMIT 50")
        users = c.fetchall()
    text = f"{ArtStyle.header('RECENT USERS')}\n"
    for uid, name, uname, up, cmd in users:
        text += f"• {name} (@{uname or 'None'}) - 📁{up} 🔧{cmd}\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

# ========== ADMINS ==========
@dp.message(Command("admins"))
async def admins_cmd(message: Message):
    user, chat = await handle_common(message, "admins")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user_id, first_name, username FROM users WHERE is_admin = 1")
        admins = c.fetchall()
    text = f"{ArtStyle.header('BOT ADMINS')}\n"
    for uid, name, uname in admins:
        text += f"👑 {name} (@{uname or 'None'})\n"
    await message.answer(text, parse_mode=ParseMode.HTML)

# ========== BROADCAST ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    broadcast_state[user.id] = {"step": 1}
    await message.answer("📢 <b>Send me text, photo, video, or document to broadcast!</b>\n❌ /cancel to stop", parse_mode=ParseMode.HTML)

@dp.message(F.photo | F.video | F.document | F.text)
async def handle_broadcast_content(message: Message):
    user = message.from_user
    if user.id not in broadcast_state:
        return
    if broadcast_state[user.id].get("step") != 1:
        return
    broadcast_state.pop(user.id, None)
    with sqlite3.connect("data/bot.db") as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned = 0")
        users = c.fetchall()
    status_msg = await message.answer(f"📤 <b>Broadcasting to {len(users)} users...</b>", parse_mode=ParseMode.HTML)
    success = 0
    failed = 0
    for (uid,) in users:
        try:
            if message.photo:
                await bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption or "")
            elif message.video:
                await bot.send_video(uid, message.video.file_id, caption=message.caption or "")
            elif message.document:
                await bot.send_document(uid, message.document.file_id, caption=message.caption or "")
            else:
                await bot.send_message(uid, message.text)
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    await status_msg.edit_text(
        f"{ArtStyle.header('BROADCAST COMPLETE')}\n"
        f"✅ Sent: {success}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Total: {len(users)}",
        parse_mode=ParseMode.HTML
    )
    await send_log(f"📢 Broadcast sent to {success} users by {user.first_name}")

# ========== LAG ==========
@dp.message(Command("lag"))
async def lag_cmd(message: Message):
    user, chat = await handle_common(message, "lag")
    if not user:
        return
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    args = message.text.split()
    duration = 5
    if len(args) > 1 and args[1].isdigit():
        duration = min(int(args[1]), 30)
    msg = await message.answer("🤖 <b>Initiating lag...</b>", parse_mode=ParseMode.HTML)
    glitch_emojis = ["⚡", "🔌", "💥", "🌀", "⚠️", "🔄", "📡", "🔋"]
    for i in range(duration):
        emoji = random.choice(glitch_emojis)
        progress = "▓" * (i + 1) + "░" * (duration - i - 1)
        glitch_text = f"{emoji} <b>SYSTEM GLITCH</b> {emoji}\n[{progress}]\n⚠️ <b>Lagging:</b> {i+1}/{duration}s"
        try:
            await msg.edit_text(glitch_text, parse_mode=ParseMode.HTML)
        except:
            pass
        await asyncio.sleep(1)
    await msg.edit_text(
        f"{ArtStyle.header('LAG COMPLETE')}\n"
        f"✅ <b>Bot recovered!</b>\n"
        f"⚡ Duration: {duration}s",
        parse_mode=ParseMode.HTML
    )

# ========== BACKUP ==========
@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    user, chat = await handle_common(message, "backup")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer("🚫 Owner only")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/backup_{timestamp}.db"
    shutil.copy2("data/bot.db", backup_file)
    await message.answer_document(FSInputFile(backup_file), caption=f"💾 Backup {timestamp}")
    os.remove(backup_file)
    await send_log(f"💾 Backup created: {timestamp}")

# ========== RESTORE ==========
@dp.message(Command("rem"))
async def rem_cmd(message: Message):
    user, chat = await handle_common(message, "rem")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer("🚫 Owner only")
        return
    pending_restore[user.id] = True
    await message.answer("💾 <b>Upload the .db file to restore.</b>\n⚠️ This will REPLACE current database!\n❌ /cancel to abort", parse_mode=ParseMode.HTML)

@dp.message(F.document)
async def handle_restore_file(message: Message):
    user = message.from_user
    if user.id not in pending_restore or not pending_restore.get(user.id):
        return
    file_name = message.document.file_name or ""
    if not (file_name.endswith('.db') or file_name.endswith('.sqlite') or file_name.endswith('.sqlite3')):
        await message.answer("❌ Please upload a .db file!")
        return
    pending_restore.pop(user.id, None)
    msg = await message.answer("⏳ <b>Restoring...</b>", parse_mode=ParseMode.HTML)
    try:
        file = await bot.get_file(message.document.file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
        temp_file = f"temp/restore_{user.id}.db"
        with open(temp_file, 'wb') as f:
            f.write(response.content)
        # Verify
        conn = sqlite3.connect(temp_file)
        conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        conn.close()
        shutil.copy2("data/bot.db", f"backups/pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(temp_file, "data/bot.db")
        os.remove(temp_file)
        init_db()
        load_bot_state()
        await msg.edit_text("✅ <b>Database restored successfully!</b>", parse_mode=ParseMode.HTML)
        await send_log("💾 Database restored from backup")
    except Exception as e:
        await msg.edit_text(f"❌ Restore failed: {str(e)}")

# ========== RESTART ==========
@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    user, chat = await handle_common(message, "restart")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer("🚫 Owner only")
        return
    await message.answer("🔄 <b>Restarting bot...</b>", parse_mode=ParseMode.HTML)
    save_bot_state()
    await send_log("🔄 Bot restarting...")
    os.execv(sys.executable, ['python'] + sys.argv)

# ========== PRO ==========
@dp.message(Command("pro"))
async def pro_cmd(message: Message):
    user, chat = await handle_common(message, "pro")
    if not user:
        return
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only")
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
            c.execute("INSERT INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
                     (target_id, f"User_{target_id}", datetime.now().isoformat(), datetime.now().isoformat(), 1))
        conn.commit()
    await message.answer(f"✅ User {target_id} is now admin!")
    await send_log(f"👑 {target_id} promoted to admin")

# ========== AUTO-RECONNECT ==========
async def keep_alive():
    global bot_active, last_activity
    while True:
        await asyncio.sleep(60)
        try:
            await bot.get_me()
            bot_active = True
            last_activity = datetime.now()
        except Exception as e:
            bot_active = False
            print(f"⚠️ Connection issue: {e}")
            try:
                await bot.session.close()
                await asyncio.sleep(5)
                await bot.get_me()
                bot_active = True
                print("✅ Reconnected")
            except:
                print("❌ Reconnection failed")

# ========== ERROR HANDLER ==========
@dp.errors()
async def error_handler(update, exception):
    print(f"❌ Error: {exception}")
    try:
        with sqlite3.connect("data/bot.db") as conn:
            c = conn.cursor()
            c.execute("INSERT INTO error_logs (timestamp, command, error, traceback) VALUES (?, ?, ?, ?)",
                     (datetime.now().isoformat(), "unknown", str(exception), traceback.format_exc()))
            conn.commit()
    except:
        pass
    return True

# ========== MAIN ==========
async def main():
    print("🚀 STARTING TEMPEST BOT...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    asyncio.create_task(keep_alive())
    await send_log("🚀 Bot started successfully!")
    while True:
        try:
            await dp.start_polling(bot)
        except (TelegramNetworkError, Exception) as e:
            print(f"⚠️ Connection lost: {e}")
            print("🔄 Restarting in 10 seconds...")
            await asyncio.sleep(10)
            print("🔄 Reconnecting...")

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