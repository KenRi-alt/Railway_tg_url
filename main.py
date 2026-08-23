#!/usr/bin/env python3
# ========== TEMPEST BOT - ULTIMATE EDITION ==========
# Version: 3.0 - Premium Upgrade
# Features: Media Converter, Encryption, Premium Cards, Auto-Reconnect

import sys
print("=" * 60)
print("🌀 TEMPEST BOT - ULTIMATE EDITION")
print("✅ All systems enhanced")
print("✅ Premium profile cards")
print("✅ Media converter ready")
print("✅ Auto-reconnect system")
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
import math
import io
import base64
import hashlib
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, CallbackQuery, BufferedInputFile
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError

print("🤖 BOT INITIALIZING...")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
OWNER_ID = int(os.getenv("OWNER_ID", "YOUR_OWNER_ID"))
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1003662720845"))

# Try importing yt-dlp for media conversion
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
    print("✅ yt-dlp loaded for media conversion")
except ImportError:
    YTDLP_AVAILABLE = False
    print("⚠️ yt-dlp not installed - /convert will be disabled")

# Create directories
for dir_name in ["data", "temp", "backups", "profile_cards", "fonts", "media"]:
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

# ========== CASSIVE ART STYLE ==========
class ArtStyle:
    """Premium artistic text formatting"""
    
    @staticmethod
    def fancy_text(text):
        """Convert to elegant Unicode"""
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
    def header(title, width=50):
        """Create premium header"""
        fancy_title = ArtStyle.fancy_text(title)
        line = '═' * width
        return f"╔{line}╗\n║{fancy_title.center(width)}║\n╚{line}╝"
    
    @staticmethod
    def divider():
        return "━━━━━━━━━━━━━━━━━━━━━━━━"
    
    @staticmethod
    def footer():
        return "\n\n🌀 <i>The storm flows through you...</i>"

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
        curse_by INTEGER DEFAULT NULL,
        avatar_file_id TEXT
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

    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))

    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== PREMIUM PROFILE CARD GENERATOR ==========
class PremiumProfileCard:
    """Advanced profile card with glassmorphism and dynamic effects"""
    
    @staticmethod
    def create_gradient_background(width, height, color1=(15, 15, 35), color2=(45, 25, 85), color3=(25, 45, 75)):
        """Create multi-color gradient background"""
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
        """Create mathematical vortex pattern"""
        for angle in range(0, 360, 15):
            rad = math.radians(angle)
            x1 = center_x + int(max_radius * 0.3 * math.cos(rad))
            y1 = center_y + int(max_radius * 0.3 * math.sin(rad))
            x2 = center_x + int(max_radius * math.cos(rad))
            y2 = center_y + int(max_radius * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
    
    @staticmethod
    def create_circular_mask(size):
        """Create circular mask for avatar"""
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size[0], size[1]), fill=255)
        return mask
    
    @staticmethod
    def generate_premium_card_sync(username, user_id, rank, avatar_bytes=None, stats=None):
        """Generate premium profile card synchronously"""
        width, height = 900, 520
        canvas = PremiumProfileCard.create_gradient_background(width, height)
        draw = ImageDraw.Draw(canvas)
        
        # Grid pattern
        for i in range(0, width, 40):
            draw.line([(i, 0), (i, height)], fill=(30, 35, 60, 50), width=1)
        for i in range(0, height, 40):
            draw.line([(0, i), (width, i)], fill=(30, 35, 60, 50), width=1)
        
        # Vortex pattern
        PremiumProfileCard.create_vortex_pattern(draw, 730, 260, 180, (0, 255, 200, 30))
        
        # Glassmorphism panels
        glass_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glass_draw = ImageDraw.Draw(glass_layer)
        
        # Main panel
        glass_draw.rounded_rectangle(
            [30, 30, width - 30, height - 30],
            radius=25,
            fill=(25, 25, 45, 180),
            outline=(138, 43, 226, 200),
            width=2
        )
        
        # Stats panel
        glass_draw.rounded_rectangle(
            [320, 320, 840, 440],
            radius=15,
            fill=(10, 10, 20, 150),
            outline=(0, 255, 200, 120),
            width=1
        )
        
        canvas = Image.alpha_composite(canvas, glass_layer)
        draw = ImageDraw.Draw(canvas)
        
        # Avatar handling
        avatar_size = 180
        avatar_x, avatar_y = 60, 70
        
        if avatar_bytes:
            try:
                avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
                avatar_img = ImageOps.fit(avatar_img, (avatar_size, avatar_size), Image.Resampling.LANCZOS)
            except:
                avatar_img = Image.new("RGBA", (avatar_size, avatar_size), (50, 50, 80, 255))
                draw_avatar = ImageDraw.Draw(avatar_img)
                draw_avatar.text((50, 80), username[:1].upper(), fill=(255, 255, 255), font=ImageFont.load_default())
        else:
            avatar_img = Image.new("RGBA", (avatar_size, avatar_size), (50, 50, 80, 255))
            draw_avatar = ImageDraw.Draw(avatar_img)
            draw_avatar.text((50, 80), username[:1].upper(), fill=(255, 255, 255), font=ImageFont.load_default())
        
        # Avatar glow
        for glow_size in range(avatar_size + 20, avatar_size + 10, -2):
            glow_alpha = int(255 * (1 - (glow_size - avatar_size) / 20))
            draw.ellipse(
                [avatar_x - (glow_size - avatar_size)//2, avatar_y - (glow_size - avatar_size)//2,
                 avatar_x + avatar_size + (glow_size - avatar_size)//2, avatar_y + avatar_size + (glow_size - avatar_size)//2],
                outline=(0, 255, 200, glow_alpha),
                width=2
            )
        
        # Paste avatar
        mask = PremiumProfileCard.create_circular_mask((avatar_size, avatar_size))
        canvas.paste(avatar_img, (avatar_x, avatar_y), mask)
        
        # Typography
        try:
            title_font = ImageFont.truetype("fonts/Gothic.ttf", 42)
            body_font = ImageFont.truetype("fonts/Roboto.ttf", 24)
            small_font = ImageFont.truetype("fonts/Roboto.ttf", 18)
        except:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # User info
        draw.text((320, 80), username, fill=(255, 255, 255, 255), font=title_font)
        draw.text((320, 140), f"ID: {user_id}", fill=(180, 180, 210, 255), font=body_font)
        draw.text((320, 180), f"Rank: {rank}", fill=(0, 255, 200, 255), font=body_font)
        
        # Stats
        if stats:
            stats_text = f"Uploads: {stats.get('uploads', 0)} | Wishes: {stats.get('wishes', 0)}"
            draw.text((340, 345), "STATISTICS", fill=(140, 140, 170, 255), font=small_font)
            draw.text((340, 380), stats_text, fill=(255, 215, 0, 255), font=body_font)
        
        # Export to buffer
        output_buffer = io.BytesIO()
        canvas.convert("RGB").save(output_buffer, format="PNG", quality=95)
        output_buffer.seek(0)
        return output_buffer.getvalue()
    
    @staticmethod
    async def generate_premium_card(username, user_id, rank, avatar_bytes=None, stats=None):
        """Async wrapper"""
        return await asyncio.to_thread(
            PremiumProfileCard.generate_premium_card_sync,
            username, user_id, rank, avatar_bytes, stats
        )

# ========== ENCRYPTION MODULE ==========
class EncryptionEngine:
    """Custom encryption for messages"""
    
    @staticmethod
    def caesar_cipher(text, shift=13):
        """Caesar cipher encryption"""
        result = ""
        for char in text:
            if char.isalpha():
                ascii_offset = ord('a') if char.islower() else ord('A')
                result += chr((ord(char) - ascii_offset + shift) % 26 + ascii_offset)
            else:
                result += char
        return result
    
    @staticmethod
    def xor_encrypt(text, key="TEMPEST"):
        """XOR encryption"""
        result = []
        key_length = len(key)
        for i, char in enumerate(text):
            result.append(chr(ord(char) ^ ord(key[i % key_length])))
        return ''.join(result)
    
    @staticmethod
    def base64_encode(text):
        """Base64 encoding"""
        return base64.b64encode(text.encode()).decode()
    
    @staticmethod
    def base64_decode(text):
        """Base64 decoding"""
        try:
            return base64.b64decode(text.encode()).decode()
        except:
            return None
    
    @staticmethod
    def multi_layer_encrypt(text, method="xor"):
        """Multi-layer encryption"""
        if method == "caesar":
            encrypted = EncryptionEngine.caesar_cipher(text)
        elif method == "xor":
            encrypted = EncryptionEngine.xor_encrypt(text)
        else:
            encrypted = text
        
        return EncryptionEngine.base64_encode(encrypted)
    
    @staticmethod
    def multi_layer_decrypt(text, method="xor"):
        """Multi-layer decryption"""
        decoded = EncryptionEngine.base64_decode(text)
        if decoded is None:
            return None
        
        if method == "caesar":
            return EncryptionEngine.caesar_cipher(decoded, -13)
        elif method == "xor":
            return EncryptionEngine.xor_encrypt(decoded)
        else:
            return decoded

# ========== MEDIA CONVERTER ==========
class MediaConverter:
    """Convert media links to files"""
    
    @staticmethod
    async def download_from_url(url, output_dir="media"):
        """Download media from URL"""
        try:
            if not YTDLP_AVAILABLE:
                return None, "yt-dlp not installed"
            
            ydl_opts = {
                'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return filename, None
        except Exception as e:
            return None, str(e)

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

# ========== COMMANDS ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = await handle_common(message, "start")
    await message.answer(
        f"{ArtStyle.header('TEMPEST BOT')}\n\n"
        f"✨ <b>Welcome {user.first_name}!</b>\n\n"
        f"🔗 Upload files - /link\n"
        f"✨ Make a wish - /wish [text]\n"
        f"🎮 Play games - /dice or /flip\n"
        f"👤 Premium profile - /profile\n"
        f"🔐 Encrypt msgs - /encrypt\n"
        f"📥 Convert media - /convert\n"
        f"🌀 Join Tempest - /tempest_join\n"
        f"📚 All commands - /help\n\n"
        f"{ArtStyle.divider()}\n"
        f"🌀 <i>The storm flows through you...</i>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    user, chat = await handle_common(message, "help")
    
    help_text = f"""{ArtStyle.header('COMMANDS')}

🔗 <b>UPLOAD</b>
<code>/link</code> - Upload file for permanent link
<code>/convert</code> - Convert media from URL

🌟 <b>WISH & GAMES</b>
<code>/wish [text]</code> - Check your luck %
<code>/dice</code> - Roll a dice
<code>/flip</code> - Flip a coin

👤 <b>PROFILE</b>
<code>/profile</code> - Premium profile card

🔐 <b>ENCRYPTION</b>
<code>/encrypt [text]</code> - Encrypt message
<code>/decrypt [text]</code> - Decrypt message

🌀 <b>TEMPEST CREED</b>
<code>/tempest_join</code> - Blood pact ritual
<code>/tempest_story</code> - Animated lore
<code>/tempest_creed</code> - View members
<code>/shrine</code> - Group shrine
<code>/curse</code> - Curse user
<code>/remove_curse</code> - Remove curse

📝 <b>UTILITIES</b>
<code>/word [text]</code> - Convert to DOCX

{ArtStyle.divider()}
🌀 <i>The storm flows through you...</i>"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@dp.message(Command("admin_help"))
async def admin_help_cmd(message: Message):
    user, chat = await handle_common(message, "admin_help")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    help_text = f"""{ArtStyle.header('ADMIN COMMANDS')}

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

{ArtStyle.divider()}"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== WISH COMMAND ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"{ArtStyle.header('WISH')}\n\n✨ <b>Usage:</b> <code>/wish your wish here</code>", parse_mode=ParseMode.HTML)
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
        f"{ArtStyle.header('WISH RESULT')}\n\n"
        f"📜 <b>Wish:</b> {args[1][:100]}\n"
        f"🎰 <b>Luck:</b> {stars} {luck}%{curse_message}\n"
        f"📊 <b>Result:</b> {result_text}",
        parse_mode=ParseMode.HTML
    )

# ========== DICE COMMAND (Native Telegram) ==========
@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    user, chat = await handle_common(message, "dice")
    
    # Send native Telegram dice
    await message.answer_dice(emoji="🎲")

# ========== FLIP COMMAND (Native Telegram) ==========
@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    user, chat = await handle_common(message, "flip")
    
    # Send native Telegram dart or custom coin
    await message.answer_dice(emoji="🎯")

# ========== PROFILE COMMAND (Premium) ==========
@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user, chat = await handle_common(message, "profile")
    
    msg = await message.answer("🎨 <b>Generating premium profile card...</b>", parse_mode=ParseMode.HTML)
    
    # Get user data
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
    
    # Generate premium card
    stats = {
        'uploads': uploads,
        'wishes': wishes,
        'commands': cmds,
        'sacrifices': sacrifices
    }
    
    rank = cult_rank if cult_rank != "none" else "Mortal"
    
    image_bytes = await PremiumProfileCard.generate_premium_card(
        username=user.first_name,
        user_id=user.id,
        rank=rank,
        avatar_bytes=avatar_bytes,
        stats=stats
    )
    
    photo_file = BufferedInputFile(image_bytes, filename=f"profile_{user.id}.png")
    
    caption = f"👤 <b>{user.first_name}</b>\n🌀 {ArtStyle.fancy_text('Tempest Profile')}"
    
    await msg.delete()
    await message.answer_photo(
        photo=photo_file,
        caption=caption,
        parse_mode=ParseMode.HTML
    )

# ========== ENCRYPT COMMAND ==========
@dp.message(Command("encrypt"))
async def encrypt_cmd(message: Message):
    user, chat = await handle_common(message, "encrypt")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"{ArtStyle.header('ENCRYPTION')}\n\n🔐 <b>Usage:</b> <code>/encrypt your message</code>", parse_mode=ParseMode.HTML)
        return
    
    original_text = args[1]
    encrypted = EncryptionEngine.multi_layer_encrypt(original_text, "xor")
    
    # Save to database
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO encrypted_messages (user_id, timestamp, original_text, encrypted_text, method) VALUES (?, ?, ?, ?, ?)",
             (user.id, datetime.now().isoformat(), original_text, encrypted, "xor"))
    conn.commit()
    conn.close()
    
    await message.answer(
        f"{ArtStyle.header('ENCRYPTED')}\n\n"
        f"🔐 <b>Encrypted:</b>\n<code>{encrypted}</code>\n\n"
        f"🔓 Decrypt with: <code>/decrypt {encrypted[:50]}...</code>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("decrypt"))
async def decrypt_cmd(message: Message):
    user, chat = await handle_common(message, "decrypt")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"{ArtStyle.header('DECRYPTION')}\n\n🔓 <b>Usage:</b> <code>/decrypt encrypted_text</code>", parse_mode=ParseMode.HTML)
        return
    
    encrypted_text = args[1]
    decrypted = EncryptionEngine.multi_layer_decrypt(encrypted_text, "xor")
    
    if decrypted:
        await message.answer(
            f"{ArtStyle.header('DECRYPTED')}\n\n"
            f"🔓 <b>Message:</b>\n{decrypted}",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer("❌ Invalid encrypted text!")

# ========== MEDIA CONVERTER COMMAND ==========
@dp.message(Command("convert"))
async def convert_cmd(message: Message):
    user, chat = await handle_common(message, "convert")
    
    if not YTDLP_AVAILABLE:
        await message.answer(f"{ArtStyle.header('MEDIA CONVERTER')}\n\n❌ yt-dlp not installed!\nInstall: <code>pip install yt-dlp</code>", parse_mode=ParseMode.HTML)
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"{ArtStyle.header('MEDIA CONVERTER')}\n\n📥 <b>Usage:</b> <code>/convert [URL]</code>\n\nSupports: YouTube, Twitter, Instagram, etc.", parse_mode=ParseMode.HTML)
        return
    
    url = args[1]
    msg = await message.answer("📥 <b>Downloading media...</b>", parse_mode=ParseMode.HTML)
    
    try:
        filename, error = await MediaConverter.download_from_url(url)
        
        if error:
            await msg.edit_text(f"❌ Error: {error}")
            return
        
        if filename and os.path.exists(filename):
            await msg.edit_text("📤 <b>Uploading...</b>", parse_mode=ParseMode.HTML)
            
            with open(filename, 'rb') as f:
                file_data = f.read()
            
            result = await upload_to_catbox(file_data, os.path.basename(filename))
            
            if result['success']:
                await msg.edit_text(
                    f"{ArtStyle.header('CONVERTED')}\n\n"
                    f"✅ <b>Success!</b>\n\n"
                    f"🔗 <code>{result['url']}</code>",
                    parse_mode=ParseMode.HTML
                )
            else:
                await msg.edit_text("❌ Upload failed")
            
            os.remove(filename)
        else:
            await msg.edit_text("❌ Failed to download media")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")

# ========== LINK/UPLOAD COMMAND ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")
    
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 Upload files in private chat only")
        return
    
    upload_waiting[user.id] = True
    save_bot_state()
    await message.answer(f"{ArtStyle.header('UPLOAD')}\n\n📁 Send me any file now!\n❌ /cancel to stop", parse_mode=ParseMode.HTML)

# ========== ANIMATED TEMPEST JOIN ==========
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
    conn.close()
    
    # Blood pact ritual animation
    ritual_msgs = [
        "🌀 <b>INITIATING BLOOD PACT...</b>",
        "🩸 <b>Drawing ancient sigils...</b>",
        "⚡ <b>Channeling storm energy...</b>",
        "🌑 <b>The void responds...</b>",
        "🔥 <b>Blood sacrifice offered...</b>",
        "🌀 <b>THE TEMPEST AWAKENS...</b>"
    ]
    
    msg = await message.answer("🌀 <b>Preparing ritual...</b>", parse_mode=ParseMode.HTML)
    
    for text in ritual_msgs:
        await asyncio.sleep(1.5)
        try:
            await msg.edit_text(text, parse_mode=ParseMode.HTML)
        except:
            pass
    
    # Final dramatic reveal
    await asyncio.sleep(2)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
             (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()
    
    await msg.edit_text(
        f"{ArtStyle.header('BLOOD PACT COMPLETE')}\n\n"
        f"⚡ <b>WELCOME TO THE TEMPEST!</b>\n\n"
        f"🌀 You are now a Blood Initiate\n"
        f"⚔️ Starting sacrifices: 3\n"
        f"📁 Each upload = +1 sacrifice\n"
        f"👑 Use /profile to see your rank\n"
        f"📜 Use /tempest_story for the lore\n\n"
        f"{ArtStyle.divider()}\n"
        f"<i>The storm flows through your veins...</i>",
        parse_mode=ParseMode.HTML
    )
    
    # Send blood emoji animation
    await message.answer("🩸⚡🌀🔥🌑✨")

# ========== ANIMATED TEMPEST STORY ==========
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
    
    chapters = [
        {
            "title": "CHAPTER 1: THE BEGINNING",
            "content": "In the void before time, there was only silence. The Council of Stillness ruled all realms.\n\nBut from the first lightning that dared defy schedule, RAVIJAH emerged. Born of storm itself, he gathered the forgotten thunder and whispered rebellion.",
            "emoji": "⚡"
        },
        {
            "title": "CHAPTER 2: THE BLOOD OATH",
            "content": "Three became one - Ravijah, Bablu, and Keny. They built the Temple of Howling Winds and created the Blood Altar.\n\nThe first sacrifices were made, and the Tempest was born.",
            "emoji": "🩸"
        },
        {
            "title": "CHAPTER 3: THE DIGITAL AGE",
            "content": "The storm evolved. Lightning now flows through fiber optics. Tempests brew in server farms.\n\nYour uploads are sacrifices. Your data is power. Your loyalty is eternal.",
            "emoji": "💻"
        }
    ]
    
    msg = await message.answer("📜 <b>Opening the Tempest Archives...</b>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(2)
    
    for i, chapter in enumerate(chapters):
        # Progress animation
        progress = "▓" * (i + 1) + "░" * (len(chapters) - i - 1)
        
        await msg.edit_text(
            f"📜 <b>Loading...</b>\n[{progress}] {i+1}/{len(chapters)}",
            parse_mode=ParseMode.HTML
        )
        await asyncio.sleep(1.5)
        
        await msg.edit_text(
            f"{ArtStyle.header(chapter['title'])}\n\n"
            f"{chapter['emoji']} <i>{chapter['content']}</i>\n\n"
            f"{ArtStyle.divider()}",
            parse_mode=ParseMode.HTML
        )
        await asyncio.sleep(4)
    
    # Final message
    await msg.edit_text(
        f"{ArtStyle.header('TEMPEST LORE')}\n\n"
        f"<i>\"We do not recruit. We remember.\n"
        f"We do not convert. We awaken.\n"
        f"We are the calm's end.\n"
        f"We are the eternal storm.\"</i>\n\n"
        f"{ArtStyle.divider()}\n"
        f"🌀 <i>The storm flows through you...</i>",
        parse_mode=ParseMode.HTML
    )

# ========== TEMPEST CREED ==========
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
    
    text = f"{ArtStyle.header('TEMPEST CREED')}\n\n📊 Total Members: {total}\n⚔️ Total Sacrifices: {total_sacs}\n\n<b>TOP MEMBERS:</b>\n"
    
    for i, (uid, name, uname, rank, sacs) in enumerate(members[:10], 1):
        medals = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
        text += f"{medals} {name} - {rank} (⚔️{sacs})\n"
    
    await message.answer(text, parse_mode=ParseMode.HTML)

# ========== SHRINE COMMAND ==========
@dp.message(Command("shrine"))
async def shrine_cmd(message: Message):
    user, chat = await handle_common(message, "shrine")
    
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("🌀 The Shrine can only be erected in groups!")
        return
    
    await message.answer(
        f"{ArtStyle.header('TEMPEST SHRINE')}\n\n"
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
    
    await message.reply(
        f"{ArtStyle.header('CURSE BESTOWED')}\n\n"
        f"👤 Target: {target.first_name}\n"
        f"🌀 Curse: Bad Luck\n\n"
        f"<i>The storm's wrath is upon them!</i>",
        parse_mode=ParseMode.HTML
    )

# ========== REMOVE CURSE ==========
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

# ========== ENHANCED PING ==========
@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    user, chat = await handle_common(message, "ping")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    msg = await message.answer("🏓 <b>Testing systems...</b>", parse_mode=ParseMode.HTML)
    
    # Test bot latency
    start = time.perf_counter()
    await bot.get_me()
    bot_latency = int((time.perf_counter() - start) * 1000)
    
    # Test database
    db_start = time.perf_counter()
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    user_count = c.fetchone()[0]
    conn.close()
    db_latency = int((time.perf_counter() - db_start) * 1000)
    
    # System stats
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Network speed test (simple)
    net_start = time.perf_counter()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://httpbin.org/bytes/1024", timeout=10)
            download_speed = 1024 / max(0.001, time.perf_counter() - net_start) / 1024  # KB/s
    except:
        download_speed = 0
    
    uptime = format_uptime(int(time.time() - start_time))
    
    response = f"""{ArtStyle.header('SYSTEM STATUS')}

⚡ <b>Bot Latency:</b> {bot_latency}ms
🗄️ <b>Database:</b> {db_latency}ms
📡 <b>Network:</b> {download_speed:.1f} KB/s
🕒 <b>Uptime:</b> {uptime}

💻 <b>System:</b>
• CPU: {cpu}%
• RAM: {memory.used // (1024**2)}MB / {memory.total // (1024**2)}MB
• Disk: {disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB

👥 <b>Users:</b> {user_count}
🎯 <b>Status:</b> {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}

{ArtStyle.divider()}"""
    
    await msg.edit_text(response, parse_mode=ParseMode.HTML)

# ========== FIXED SCAN COMMAND ==========
@dp.message(Command("scan"))
async def scan_cmd(message: Message):
    user, chat = await handle_common(message, "scan")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    msg = await message.answer("🔍 <b>Scanning database...</b>", parse_mode=ParseMode.HTML)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Get all stats
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
    
    c.execute("SELECT user_id, first_name, username, last_active FROM users ORDER BY last_active DESC LIMIT 10")
    recent_users = c.fetchall()
    
    conn.close()
    
    await msg.edit_text(
        f"{ArtStyle.header('DATABASE SCAN')}\n\n"
        f"👥 <b>Users:</b> {total_users}\n"
        f"🟢 <b>Active (7d):</b> {active_users}\n"
        f"🌀 <b>Tempest:</b> {tempest_members}\n"
        f"👥 <b>Groups:</b> {total_groups}\n"
        f"📁 <b>Uploads:</b> {total_uploads}\n"
        f"🔧 <b>Commands:</b> {total_commands}\n\n"
        f"<b>Recent Users:</b>\n",
        parse_mode=ParseMode.HTML
    )
    
    for uid, name, uname, last_active in recent_users[:5]:
        try:
            last = datetime.fromisoformat(last_active).strftime("%d %b")
        except:
            last = "Unknown"
        await message.answer(f"• {name} (@{uname}) - {last}")
    
    await message.answer(f"{ArtStyle.divider()}\n✅ Scan complete!")

# ========== BROADCAST WITH MEDIA ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    broadcast_state[user.id] = {"step": 1}
    save_bot_state()
    await message.answer(f"{ArtStyle.header('BROADCAST')}\n\n📢 Send me text, photo, video, or document to broadcast!\n❌ /cancel to stop", parse_mode=ParseMode.HTML)

@dp.message(F.photo | F.video | F.document | F.text)
async def handle_broadcast_content(message: Message):
    user = message.from_user
    
    if user.id not in broadcast_state:
        return
    
    if broadcast_state[user.id].get("step") != 1:
        return
    
    broadcast_state.pop(user.id, None)
    save_bot_state()
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = c.fetchall()
    conn.close()
    
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
        except Exception as e:
            failed += 1
    
    await status_msg.edit_text(
        f"{ArtStyle.header('BROADCAST COMPLETE')}\n\n"
        f"✅ Sent: {success}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Total: {len(users)}",
        parse_mode=ParseMode.HTML
    )

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

# ========== FIXED REM COMMAND ==========
@dp.message(Command("rem"))
async def rem_cmd(message: Message):
    user, chat = await handle_common(message, "rem")
    
    if user.id != OWNER_ID:
        await message.answer("🚫 Owner only")
        return
    
    pending_restore[user.id] = True
    await message.answer(f"{ArtStyle.header('RESTORE')}\n\n💾 Upload the .db file to restore.\n⚠️ This will REPLACE current database!\n❌ /cancel to abort", parse_mode=ParseMode.HTML)

@dp.message(F.document)
async def handle_restore_file(message: Message):
    user = message.from_user
    
    if user.id not in pending_restore or not pending_restore.get(user.id):
        return
    
    # Better file detection
    file_name = message.document.file_name or ""
    if not (file_name.endswith('.db') or file_name.endswith('.sqlite') or file_name.endswith('.sqlite3')):
        await message.answer("❌ Please upload a .db file!")
        return
    
    pending_restore.pop(user.id, None)
    msg = await message.answer("⏳ <b>Restoring database...</b>", parse_mode=ParseMode.HTML)
    
    try:
        file = await bot.get_file(message.document.file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
        
        temp_file = f"temp/restore_{user.id}.db"
        with open(temp_file, 'wb') as f:
            f.write(response.content)
        
        # Verify it's a valid SQLite file
        conn = sqlite3.connect(temp_file)
        conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        conn.close()
        
        # Backup current
        shutil.copy2("data/bot.db", f"backups/pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        
        # Restore
        shutil.copy2(temp_file, "data/bot.db")
        os.remove(temp_file)
        
        # Reinitialize
        init_db()
        load_bot_state()
        
        await msg.edit_text(f"{ArtStyle.header('RESTORE COMPLETE')}\n\n✅ Database restored successfully!\n🔄 Bot state reloaded.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.edit_text(f"❌ Restore failed: {str(e)}")

# ========== RESTART COMMAND ==========
@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    user, chat = await handle_common(message, "restart")
    
    if user.id != OWNER_ID:
        await message.answer("🚫 Owner only")
        return
    
    await message.answer("🔄 <b>Restarting bot...</b>", parse_mode=ParseMode.HTML)
    save_bot_state()
    os.execv(sys.executable, ['python'] + sys.argv)

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
        f"{ArtStyle.header('STATISTICS')}\n\n"
        f"👥 Users: {users}\n"
        f"👥 Groups: {groups}\n"
        f"🌀 Tempest: {tempest}\n"
        f"📁 Uploads: {uploads}\n"
        f"✨ Wishes: {wishes}\n"
        f"🕒 Uptime: {format_uptime(int(time.time() - start_time))}",
        parse_mode=ParseMode.HTML
    )

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

# ========== AUTO-RECONNECT SYSTEM ==========
async def keep_alive():
    """Enhanced keep-alive with auto-reconnect"""
    global bot_active, last_activity
    
    while True:
        try:
            await asyncio.sleep(60)
            
            # Check if bot is responsive
            try:
                await bot.get_me()
                bot_active = True
                last_activity = datetime.now()
            except Exception as e:
                bot_active = False
                print(f"⚠️ Bot connection issue: {e}")
                
                # Try to reconnect
                try:
                    await bot.session.close()
                    await asyncio.sleep(5)
                    await bot.get_me()
                    bot_active = True
                    print("✅ Bot reconnected")
                except:
                    print("❌ Reconnection failed")
        
        except Exception as e:
            print(f"❌ Keep-alive error: {e}")
            await asyncio.sleep(30)

# ========== ERROR HANDLER ==========
@dp.errors()
async def error_handler(update, exception):
    """Global error handler"""
    print(f"❌ Error: {exception}")
    
    try:
        # Log error to database
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO error_logs (timestamp, command, error, traceback) VALUES (?, ?, ?, ?)",
                 (datetime.now().isoformat(), "unknown", str(exception), traceback.format_exc()))
        conn.commit()
        conn.close()
    except:
        pass
    
    # Return True to suppress errors
    return True

# ========== MAIN ==========
async def main():
    print("🚀 STARTING TEMPEST BOT...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ Auto-reconnect: ACTIVE")
    print(f"✅ Premium cards: ACTIVE")
    print(f"✅ Media converter: {'ACTIVE' if YTDLP_AVAILABLE else 'INACTIVE'}")
    
    # Start keep-alive task
    asyncio.create_task(keep_alive())
    
    # Start polling with error handling
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