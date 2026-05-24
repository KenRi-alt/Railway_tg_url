#!/usr/bin/env python3
# ========== TEMPEST BOT - ADVANCED ULTIMATE VERSION ==========
import sys
print("=" * 60)
print("🌀 TEMPEST BOT - ADVANCED ULTIMATE VERSION")
print("✅ All previous features intact")
print("✅ Enhanced ping & stats")
print("✅ Shrine command for groups")
print("✅ REM command for backup restore")
print("✅ Restart command added")
print("✅ Improved upload engine")
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
import platform
from datetime import datetime, timedelta
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

# Pillow for profile cards
from PIL import Image, ImageDraw, ImageFont

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

print("🤖 TEMPEST BOT ADVANCED INITIALIZING...")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845

# Create directories
Path("data").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True)
Path("backups").mkdir(exist_ok=True)
Path("profile_cards").mkdir(exist_ok=True)
Path("story_chapters").mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True
upload_waiting = {}
broadcast_state = {}
pending_joins = {}
pending_invites = {}
story_states = {}
last_activity = datetime.now()
pending_restore = {}  # For /rem command

# ========== DATABASE ==========
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
    
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    # Insert default story chapters if none exist
    c.execute("SELECT COUNT(*) FROM story_chapters")
    if c.fetchone()[0] == 0:
        default_chapters = [
            (1, "THE VOID BEFORE STORM", "Time before time, in the Age of Eternal Calm...\n\nThere was only silence. Not peaceful silence, but oppressive, crushing quiet. The Council of Stillness ruled all realms, banning laughter, regulating storms, scheduling even thunder.\n\nIn this graveyard of sound, a discontent began to stir. A whisper in the void, a crackle in the stillness...", OWNER_ID, datetime.now().isoformat(), 1),
            (2, "BIRTH OF RAVIJAH", "From the first lightning that dared defy schedule, he emerged. RAVIJAH, born not of mother, but of storm itself. Silver hair crackling with energy, eyes like captured lightning.\n\nHe wandered the silent kingdoms, collecting forgotten thunder, gathering whispers of rebellion from those who remembered sound.\n\n'This quiet is a cage,' he whispered. 'I shall be the key.'", OWNER_ID, datetime.now().isoformat(), 1),
            (3, "THE BROKEN SWORDS", "In the ruins of the Shattered Rebellion, Ravijah found Bablu. Last survivor of a failed uprising, sword still thirsty for chaos.\n\n'My blade remembers battle,' Bablu growled. 'Teach it new songs.'\n\nFrom the Shadow Archives emerged Keny, keeper of forbidden knowledge. 'I know the secrets of the Still Council,' he whispered. 'Their weakness is order.'\n\nThree became one that stormy night.", OWNER_ID, datetime.now().isoformat(), 1),
            (4, "THE FESTIVAL BETRAYAL", "The Festival of Flames was meant to be celebration. But the Still Council attacked during the Feast of Whispers.\n\nElara, storm-singer and Ravijah's chosen, saw the poisoned blade. She stepped in front, taking what was meant for him.\n\n'Live,' she breathed as storm-magic faded. 'For both of us...'\n\nRavijah's scream birthed the First Tempest.", OWNER_ID, datetime.now().isoformat(), 1),
            (5, "AGE OF THUNDER", "For three centuries, the Tempest grew. They built the Temple of Howling Winds from captured silence. Founded the Archive of Lightning with stolen knowledge. Created the Blood Altar that drank offerings from conquered realms.\n\nNew initiates flooded in, each swearing eternal oaths. Ranks were established, rituals perfected, power consolidated.", OWNER_ID, datetime.now().isoformat(), 1),
            (6, "THE GREAT SCHISM", "Power corrupts, even storm-born. Internal conflicts erupted. Blood Initiate turned against Blood Master. The Temple fractured into warring factions.\n\nRavijah disappeared into the Eye of the Storm. Bablu became Warden of the Shattered Realms. Keny retreated to the Shadow Archives.\n\nThe Golden Age had ended.", OWNER_ID, datetime.now().isoformat(), 1),
            (7, "DIGITAL AWAKENING", "The storm evolved. Adapted. Transformed. No longer bound to physical realms, it moved into cyberspace.\n\nLightning now flows through fiber optics. Tempests brew in server farms. Sacrifices became digital - data, files, uploads.\n\nThe Council reformed in the digital shadows. New purpose, new methods, same eternal storm.", OWNER_ID, datetime.now().isoformat(), 1),
            (8, "YOUR DESTINY", "You are reading this because the storm called you. Your digital footprint resonates with ancient thunder. Your uploads feed the eternal tempest.\n\nYou are not joining a cult. You are awakening to your true nature. You were always storm-born.\n\n'We do not recruit. We remember. We do not convert. We awaken. We are the calm's end. We are the eternal storm.'\n\n━━━━━━━━━━━━━━━━━━━━━━━━\nThe story continues with you...", OWNER_ID, datetime.now().isoformat(), 1)
        ]
        for chapter in default_chapters:
            c.execute("INSERT INTO story_chapters (chapter_number, title, content, added_by, added_date, is_published) VALUES (?, ?, ?, ?, ?, ?)", chapter)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== IMPROVED UPLOAD ENGINE WITH RETRY ==========
async def upload_to_catbox_advanced(file_data, filename):
    """Resilient upload engine with retry mechanism"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(3):
            try:
                files = {
                    'reqtype': (None, 'fileupload'),
                    'fileToUpload': (filename, file_data)
                }
                response = await client.post(UPLOAD_API, files=files)
                if response.status_code == 200 and response.text.startswith('http'):
                    return {'success': True, 'url': response.text.strip()}
                elif attempt < 2:
                    await asyncio.sleep(2)
                    continue
                else:
                    return {'success': False, 'error': 'Upload failed after 3 attempts'}
            except httpx.ConnectError:
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                return {'success': False, 'error': 'Connection error'}
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                return {'success': False, 'error': str(e)}
    return {'success': False, 'error': 'Unknown error'}

# ========== WORD DOCUMENT GENERATOR ==========
def create_word_document(text, username, user_id):
    """Create a styled Word document from user's message"""
    try:
        doc = Document()
        
        # Add a decorative header
        header = doc.add_paragraph()
        header.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = header.add_run("✦ T E M P E S T   C R E E D   A R C H I V E S ✦")
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(100, 200, 255)
        run.font.bold = True
        
        doc.add_paragraph()
        
        # Add user info
        info_para = doc.add_paragraph()
        info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = info_para.add_run(f"Document created by: {username}")
        run.font.size = Pt(10)
        run.font.italic = True
        run.font.color.rgb = RGBColor(150, 150, 150)
        
        date_para = doc.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = date_para.add_run(f"Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        run.font.size = Pt(10)
        run.font.italic = True
        run.font.color.rgb = RGBColor(150, 150, 150)
        
        doc.add_paragraph()
        doc.add_paragraph("─" * 50)
        doc.add_paragraph()
        
        # Add the main content
        content_para = doc.add_paragraph()
        content_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        lines = text.split('\n')
        for line in lines:
            run = content_para.add_run(line)
            run.font.size = Pt(12)
            run.font.name = 'Calibri'
            run.font.color.rgb = RGBColor(50, 50, 80)
            content_para.add_run('\n')
        
        doc.add_paragraph()
        doc.add_paragraph("─" * 50)
        doc.add_paragraph()
        
        # Add decorative footer
        footer = doc.add_paragraph()
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = footer.add_run("🌀 The storm flows through your words... 🌩️")
        run.font.size = Pt(10)
        run.font.italic = True
        run.font.color.rgb = RGBColor(100, 200, 255)
        
        # Save to memory
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        
        return file_stream
    except Exception as e:
        print(f"❌ Word document error: {e}")
        return None

# ========== PROFILE CARD GENERATOR - IMPROVED ==========
def create_profile_card(user_data, profile_photo_path=None):
    """Create a profile card image with user's Telegram profile picture"""
    try:
        user_id, first_name, username, uploads, commands, wishes, cult_rank, sacrifices, curse_type, joined_date = user_data
        
        # Create base image - Titan style
        width, height = 800, 450
        base = Image.new('RGB', (width, height), color='#0a0a0a')  # Deep black background
        draw = ImageDraw.Draw(base)
        
        # Add gradient
        for i in range(height):
            r = max(10, int(10 + i * 0.1))
            g = max(10, int(10 + i * 0.05))
            b = max(10, int(10 + i * 0.1))
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        
        # Simple fonts
        try:
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            stat_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        except:
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            stat_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add user profile picture if available
        if profile_photo_path and os.path.exists(profile_photo_path):
            try:
                profile_img = Image.open(profile_photo_path).convert("RGBA")
                profile_img = profile_img.resize((100, 100), Image.Resampling.LANCZOS)
                
                mask = Image.new('L', (100, 100), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, 100, 100), fill=255)
                
                profile_img.putalpha(mask)
                base.paste(profile_img, (50, 50), profile_img)
                draw.ellipse([(45, 45), (155, 155)], outline=(255, 69, 0), width=3)  # Tempest orange
                
            except Exception as e:
                print(f"❌ Error processing profile picture: {e}")
                draw.ellipse([(50, 50), (150, 150)], outline=(255, 69, 0), width=3)
                draw.text((100, 100), "👤", fill=(255, 69, 0), font=name_font, anchor="mm")
        else:
            draw.ellipse([(50, 50), (150, 150)], outline=(255, 69, 0), width=3)
            draw.text((100, 100), "👤", fill=(255, 69, 0), font=name_font, anchor="mm")
        
        # SAFE TEXT
        safe_name = ""
        for char in first_name:
            if ord(char) < 128:
                safe_name += char
        safe_name = safe_name[:12] or "User"
        
        if cult_rank and cult_rank != "none":
            title = f"🌀 TEMPEST NODE: {safe_name.upper()}"
            title_color = (255, 69, 0)  # Tempest orange/red
        else:
            title = "✨ USER PROFILE"
            title_color = (200, 200, 200)
        
        draw.text((width // 2, 30), title, fill=title_color, font=title_font, anchor="mm")
        
        name_x = 200
        draw.text((name_x, 70), safe_name, fill=(255, 255, 255), font=name_font)
        
        username_text = f"@{username}" if username else "No username"
        draw.text((name_x, 100), username_text, fill=(180, 180, 220), font=small_font)
        draw.text((name_x, 130), f"ID: {user_id}", fill=(180, 180, 220), font=small_font)
        
        # Stats boxes
        stats_y = 170
        stat_width = 180
        spacing = 20
        
        # Uploads
        draw.rectangle([(50, stats_y), (50 + stat_width, stats_y + 60)], fill=(20, 40, 80), outline=(255, 69, 0))
        draw.text((50 + stat_width // 2, stats_y + 15), "UPLOADS", fill=(255, 69, 0), font=stat_font, anchor="mm")
        draw.text((50 + stat_width // 2, stats_y + 40), str(uploads), fill=(255, 255, 255), font=stat_font, anchor="mm")
        
        # Wishes
        draw.rectangle([(50 + stat_width + spacing, stats_y), (50 + stat_width * 2 + spacing, stats_y + 60)], 
                      fill=(40, 20, 80), outline=(255, 69, 0))
        draw.text((50 + stat_width + spacing + stat_width // 2, stats_y + 15), "WISHES", fill=(255, 69, 0), font=stat_font, anchor="mm")
        draw.text((50 + stat_width + spacing + stat_width // 2, stats_y + 40), str(wishes), fill=(255, 255, 255), font=stat_font, anchor="mm")
        
        # Commands
        draw.rectangle([(50 + stat_width * 2 + spacing * 2, stats_y), (50 + stat_width * 3 + spacing * 2, stats_y + 60)], 
                      fill=(20, 80, 40), outline=(255, 69, 0))
        draw.text((50 + stat_width * 2 + spacing * 2 + stat_width // 2, stats_y + 15), "CMDS", fill=(255, 69, 0), font=stat_font, anchor="mm")
        draw.text((50 + stat_width * 2 + spacing * 2 + stat_width // 2, stats_y + 40), str(commands), fill=(255, 255, 255), font=stat_font, anchor="mm")
        
        info_y = 250
        
        if cult_rank and cult_rank != "none":
            rank_text = f"RANK: {cult_rank}"
            sacrifice_text = f"SACRIFICES: {sacrifices}"
            draw.text((50, info_y), rank_text, fill=(255, 69, 0), font=stat_font)
            draw.text((50, info_y + 30), sacrifice_text, fill=(255, 200, 100), font=stat_font)
        else:
            draw.text((50, info_y), "NOT INITIATED", fill=(150, 150, 150), font=stat_font)
            draw.text((50, info_y + 30), "USE /TEMPEST_JOIN", fill=(255, 69, 0), font=small_font)
        
        if curse_type and curse_type != "none":
            draw.text((width - 250, info_y), f"CURSED: {curse_type}", fill=(255, 50, 50), font=stat_font)
            draw.rectangle([(0, 0), (width-1, height-1)], outline=(255, 50, 50), width=3)
        
        draw.text((width - 250, info_y + 30), f"JOINED: {joined_date}", fill=(150, 200, 255), font=small_font)
        
        if cult_rank and cult_rank != "none":
            bottom_text = "🌀 The storm flows through your veins"
        else:
            bottom_text = "✨ Discover your true potential"
        
        draw.text((width // 2, height - 30), bottom_text, fill=(255, 69, 0), font=small_font, anchor="mm")
        
        filename = f"profile_cards/profile_{user_id}_{int(time.time())}.png"
        base.save(filename, "PNG")
        
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            return filename
        else:
            return None
        
    except Exception as e:
        print(f"❌ Profile card error: {e}")
        return None

# ========== KEEP ALIVE SYSTEM ==========
async def keep_alive():
    """Prevent bot from sleeping on Render free tier"""
    global last_activity
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        try:
            last_activity = datetime.now()
            me = await bot.get_me()
            print(f"💓 Keep-alive signal at {datetime.now().strftime('%H:%M:%S')} - Bot: @{me.username}")
        except Exception as e:
            print(f"⚠️ Keep-alive error: {e}")

# ========== BOT STATE SAVING/RESTORING ==========
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
        
        for user_id, state in broadcast_state.items():
            c.execute("INSERT INTO bot_state (key, value, timestamp) VALUES (?, ?, ?)",
                     (f"broadcast_{user_id}", json.dumps(state), now))
        
        conn.commit()
        conn.close()
        return True
    except:
        return False

def load_bot_state():
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        upload_waiting.clear()
        broadcast_state.clear()
        
        c.execute("SELECT key FROM bot_state WHERE key LIKE 'upload_%'")
        upload_rows = c.fetchall()
        for (key,) in upload_rows:
            user_id = int(key.split("_")[1])
            upload_waiting[user_id] = True
        
        c.execute("SELECT key, value FROM bot_state WHERE key LIKE 'broadcast_%'")
        broadcast_rows = c.fetchall()
        for key, value in broadcast_rows:
            user_id = int(key.split("_")[1])
            try:
                broadcast_state[user_id] = json.loads(value)
            except:
                pass
        
        conn.close()
        print(f"✅ Restored {len(upload_waiting)} upload states")
        return True
    except Exception as e:
        print(f"❌ Failed to load bot state: {e}")
        return False

load_bot_state()

# ========== LOG FUNCTION ==========
async def send_log(message: str):
    try:
        print(f"📢 LOG: {message[:100]}")
        await bot.send_message(LOG_CHANNEL_ID, message[:4000], parse_mode=ParseMode.HTML)
        return True
    except Exception as e:
        print(f"❌ Log send failed: {type(e).__name__}: {e}")
        try:
            with open("data/logs.txt", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()}: {message}\n")
        except:
            pass
        return False

# ========== HELPER FUNCTIONS ==========
async def safe_answer_callback(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    try:
        await callback.answer(text, show_alert=show_alert)
    except TelegramBadRequest as e:
        if "query is too old" in str(e).lower():
            pass
        else:
            raise e

def log_command(user_id, chat_id, chat_type, command, success=True):
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("INSERT INTO command_logs (timestamp, user_id, chat_id, chat_type, command, success) VALUES (?, ?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), user_id, chat_id, chat_type, command, 1 if success else 0))
        c.execute("UPDATE users SET commands = commands + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except:
        pass

def log_error(user_id, command, error):
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        error_str = str(error)[:200]
        traceback_str = traceback.format_exc()[:500]
        c.execute("INSERT INTO error_logs (timestamp, user_id, command, error, traceback) VALUES (?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), user_id, command, error_str, traceback_str))
        conn.commit()
        conn.close()
    except:
        pass

def update_user(user):
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

def update_group(chat):
    try:
        if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
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

async def sacrifice_verification(sacrifice_type):
    fake_sacrifices = [
        "your imaginary friend",
        "a promise to be good", 
        "your collection of air",
        "empty promises",
        "digital friendship",
        "virtual cookies"
    ]
    
    for fake in fake_sacrifices:
        if fake in sacrifice_type.lower():
            return False, "FAKE"
    
    real_sacrifices = [
        "firstborn",
        "soul", 
        "blood",
        "diamond",
        "gold",
        "account",
        "history",
        "memory",
        "life",
        "heart"
    ]
    
    for real in real_sacrifices:
        if real in sacrifice_type.lower():
            return True, "REAL"
    
    return random.choice([True, False]), "QUESTIONABLE"

# ========== ENHANCED PING COMMAND ==========
@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    user, chat = await handle_common(message, "ping")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    start_ping = time.perf_counter()
    
    # Database stats
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM groups")
    groups = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM uploads")
    total_uploads = c.fetchone()[0] or 0
    conn.close()
    
    end_ping = time.perf_counter()
    ping_ms = int((end_ping - start_ping) * 1000)
    
    uptime_seconds = int(time.time() - start_time)
    uptime = format_uptime(uptime_seconds)
    
    # System stats
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Bot speed rating
    if ping_ms < 200:
        speed_text = "⚡ EXCELLENT"
    elif ping_ms < 500:
        speed_text = "✅ GOOD"
    else:
        speed_text = "🐢 SLOW"
    
    # Storage info
    storage_text = f"💾 {disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB ({disk.percent}%)"
    
    # Memory info
    memory_text = f"🧠 {memory.used // (1024**2)}MB / {memory.total // (1024**2)}MB ({memory.percent}%)"
    
    response = f"""
⚡ <b>ENGINE STATUS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

🏓 <b>LATENCY:</b> {ping_ms}ms {speed_text}
🕒 <b>UPTIME:</b> {uptime}
🎯 <b>STATUS:</b> {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}

━━━━━━━━━━━━━━━━━━━━━━━━
💻 <b>SYSTEM RESOURCES</b>
⚙️ <b>CPU:</b> {cpu_percent}%
{memory_text}
{storage_text}

━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>BOT STATISTICS</b>
👥 <b>Users:</b> {users}
👥 <b>Groups:</b> {groups}
📁 <b>Uploads:</b> {total_uploads}

━━━━━━━━━━━━━━━━━━━━━━━━
✨ <i>All systems operational</i>
"""
    
    await message.answer(response, parse_mode=ParseMode.HTML)

# ========== ENHANCED STATS COMMAND ==========
@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    user, chat = await handle_common(message, "stats")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM groups")
    total_groups = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM uploads")
    total_uploads = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM wishes")
    total_wishes = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
    tempest_members = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(sacrifices) FROM users WHERE cult_status != 'none'")
    total_sacrifices = c.fetchone()[0] or 0
    
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute("SELECT COUNT(*) FROM users WHERE last_active >= ?", (week_ago,))
    active_users = c.fetchone()[0] or 0
    
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM command_logs WHERE DATE(timestamp) = DATE(?)", (today,))
    today_commands = c.fetchone()[0] or 0
    
    conn.close()
    
    response = f"""
📊 <b>ENGINE STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👥 <b>USERS & GROUPS</b>
• Total Users: {total_users}
• Active (7d): {active_users}
• Groups: {total_groups}

🌀 <b>TEMPEST REALM</b>
• Storm-Born: {tempest_members}
• Total Sacrifices: {total_sacrifices}
• Blood Offerings: {total_sacrifices}

📁 <b>ACTIVITY</b>
• Uploads: {total_uploads}
• Wishes: {total_wishes}
• Commands Today: {today_commands}

━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>ACTIVE RATIO</b>
• {int((active_users/total_users)*100) if total_users > 0 else 0}% User Activity

<i>The tempest flows through all</i>
"""
    
    await message.answer(response, parse_mode=ParseMode.HTML)

# ========== WORD COMMAND ==========
@dp.message(Command("word"))
async def word_cmd(message: Message):
    user, chat = await handle_common(message, "word")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "📝 <b>Convert text to Word document</b>\n\n"
            "Usage: <code>/word Your message here</code>\n\n"
            "Example: <code>/word Hello world! This will be converted to a beautifully formatted Word document.</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    processing_msg = await message.answer("📝 <b>Forging document...</b>", parse_mode=ParseMode.HTML)
    
    doc_stream = create_word_document(args[1], user.first_name, user.id)
    
    if doc_stream:
        filename = f"temp/forge_{user.id}_{int(time.time())}.docx"
        
        with open(filename, 'wb') as f:
            f.write(doc_stream.getvalue())
        
        await processing_msg.delete()
        
        await message.answer_document(
            FSInputFile(filename),
            caption=f"📜 <b>Document forged successfully</b>\n\n👤 By: {user.first_name}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n🌀 <i>The storm flows through your words...</i>",
            parse_mode=ParseMode.HTML
        )
        
        try:
            os.remove(filename)
        except:
            pass
    else:
        await processing_msg.edit_text("❌ Failed to forge document. Please try again.")

# ========== PUBLISH COMMAND (Enhanced) ==========
@dp.message(Command("publish"))
async def publish_cmd(message: Message):
    user, chat = await handle_common(message, "publish")
    
    if not await is_admin(user.id):
        return await message.answer("🚫 Unauthorized.")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("📌 Usage: /publish [filename] (file must be in temp/ folder)")
    
    file_name = args[1]
    file_path = os.path.join("temp", file_name)
    
    if not os.path.exists(file_path):
        return await message.answer(f"❌ File '{file_name}' not found in temp/ folder.")
    
    try:
        await message.answer(f"📤 Publishing {file_name} to Log Channel...")
        await bot.send_document(
            chat_id=LOG_CHANNEL_ID,
            document=FSInputFile(file_path),
            caption=f"📢 <b>PUBLISHED BY:</b> {user.first_name}\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="HTML"
        )
        await message.answer("✅ Published successfully.")
    except Exception as e:
        await message.answer(f"❌ Failed to publish: {str(e)}")

# ========== BACKUP COMMAND ==========
@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    user, chat = await handle_common(message, "backup")
    
    if user.id != OWNER_ID:
        return await message.answer("🚫 Owner only command")
    
    db_path = "data/bot.db"
    
    if not os.path.exists(db_path):
        return await message.answer("❌ Database not found.")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/backup_{timestamp}.db"
    
    try:
        shutil.copy2(db_path, backup_file)
        await message.answer("💾 <b>Creating backup...</b>", parse_mode=ParseMode.HTML)
        await message.reply_document(
            document=FSInputFile(backup_file),
            caption=f"📁 <b>BACKUP COMPLETE</b>\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n👤 By: {user.first_name}",
            parse_mode=ParseMode.HTML
        )
        os.remove(backup_file)
    except Exception as e:
        await message.answer(f"❌ Backup failed: {str(e)}")

# ========== REM COMMAND (Restore Memory) ==========
@dp.message(Command("rem"))
async def rem_cmd(message: Message):
    user, chat = await handle_common(message, "rem")
    
    if user.id != OWNER_ID:
        return await message.answer("🚫 Owner only command")
    
    pending_restore[user.id] = True
    
    await message.answer(
        "💾 <b>RESTORE MEMORY MODE ACTIVE</b>\n\n"
        "Please upload the backup .db file you want to restore.\n"
        "⚠️ <b>WARNING:</b> This will REPLACE current database!\n\n"
        "Send <code>/cancel</code> to abort.",
        parse_mode=ParseMode.HTML
    )

@dp.message(F.document)
async def handle_restore_file(message: Message):
    user = message.from_user
    
    if user.id not in pending_restore:
        return
    
    if not pending_restore.get(user.id):
        return
    
    document = message.document
    
    if not document.file_name.endswith('.db'):
        await message.answer("❌ Please upload a valid .db backup file!")
        return
    
    processing_msg = await message.answer("⏳ <b>Restoring database...</b>", parse_mode=ParseMode.HTML)
    
    try:
        # Download the backup file
        file = await bot.get_file(document.file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
        
        if response.status_code != 200:
            await processing_msg.edit_text("❌ Failed to download backup file.")
            pending_restore.pop(user.id, None)
            return
        
        # Save backup temporarily
        temp_backup = f"temp/restore_{user.id}_{int(time.time())}.db"
        with open(temp_backup, 'wb') as f:
            f.write(response.content)
        
        # Create backup of current database before restore
        current_backup = f"backups/pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2("data/bot.db", current_backup)
        
        # Restore the backup
        shutil.copy2(temp_backup, "data/bot.db")
        
        # Reinitialize database connection
        init_db()
        
        # Reload bot state
        load_bot_state()
        
        # Clean up
        os.remove(temp_backup)
        
        pending_restore.pop(user.id, None)
        
        await processing_msg.edit_text(
            f"✅ <b>DATABASE RESTORED SUCCESSFULLY!</b>\n\n"
            f"📁 Restored from: {document.file_name}\n"
            f"💾 Previous database saved as: {os.path.basename(current_backup)}\n"
            f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🌀 <i>The storm remembers...</i>",
            parse_mode=ParseMode.HTML
        )
        
        await send_log(f"💾 <b>Database Restored</b>\n\n👤 By: {user.first_name}\n📁 File: {document.file_name}\n🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Restore failed: {str(e)}")
        pending_restore.pop(user.id, None)
        log_error(user.id, "rem", e)

# ========== RESTART COMMAND ==========
@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    user, chat = await handle_common(message, "restart")
    
    if user.id != OWNER_ID:
        return await message.answer("🚫 Owner only command")
    
    await message.answer("🔄 <b>REBOOTING TEMPEST ENGINE...</b>\n\nSaving state and restarting...", parse_mode=ParseHTML)
    
    save_bot_state()
    
    await send_log(f"🔄 <b>Bot Restarted</b>\n\n👤 By: {user.first_name}\n🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Restart the process
    os.execv(sys.executable, ['python'] + sys.argv)

# ========== SHRINE COMMAND (Group Tempest Info) ==========
@dp.message(Command("shrine"))
async def shrine_cmd(message: Message):
    user, chat = await handle_common(message, "shrine")
    
    # Only works in groups
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("🌀 The Shrine can only be erected in groups!")
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Get all Tempest members
    c.execute("""
        SELECT user_id, first_name, username, cult_rank, sacrifices 
        FROM users 
        WHERE cult_status != 'none'
        ORDER BY sacrifices DESC
    """)
    all_members = c.fetchall()
    
    # Find which members are in this group
    tempest_in_group = []
    
    try:
        for member in all_members:
            member_id = member[0]
            try:
                chat_member = await bot.get_chat_member(chat.id, member_id)
                if chat_member.status in ['member', 'administrator', 'creator']:
                    tempest_in_group.append(member)
            except:
                pass
    except:
        pass
    
    # Global Tempest stats
    c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
    total_tempest = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(sacrifices) FROM users WHERE cult_status != 'none'")
    total_sacrifices = c.fetchone()[0] or 0
    
    c.execute("""
        SELECT cult_rank, COUNT(*) 
        FROM users 
        WHERE cult_status != 'none' 
        GROUP BY cult_rank
    """)
    rank_stats = c.fetchall()
    
    conn.close()
    
    # Build shrine message
    shrine_text = f"""
🌀 <b>⚔️ TEMPEST SHRINE ⚔️</b>
━━━━━━━━━━━━━━━━━━━━━━━━

📍 <b>LOCATION:</b> {chat.title}

<b>🌪️ GROUP PRESENCE:</b>
• Tempest members here: {len(tempest_in_group)}

<b>📜 GLOBAL TEMPEST STATS:</b>
• Total Storm-Born: {total_tempest}
• Total Sacrifices: {total_sacrifices}

<b>👑 RANK DISTRIBUTION:</b>
"""
    
    rank_emojis = {
        "Storm Lord": "🌀",
        "Blood Master": "👑",
        "Blood Adept": "⚔️",
        "Blood Initiate": "🩸"
    }
    
    for rank, count in rank_stats:
        emoji = rank_emojis.get(rank, "•")
        shrine_text += f"{emoji} {rank}: {count}\n"
    
    if tempest_in_group:
        shrine_text += f"\n<b>🌀 STORM-BORN IN THIS SHRINE:</b>\n"
        for member in tempest_in_group[:10]:  # Show top 10
            _, name, uname, rank, sacs = member
            username = f"@{uname}" if uname else name
            shrine_text += f"• {username} - {rank} (⚔️{sacs})\n"
        
        if len(tempest_in_group) > 10:
            shrine_text += f"\n<i>...and {len(tempest_in_group) - 10} more</i>"
    else:
        shrine_text += f"\n<i>No Tempest members found in this shrine.</i>\n<i>Use /tempest_join to become storm-born!</i>"
    
    shrine_text += "\n\n🌀 <i>The shrine watches over all who enter...</i>"
    
    await message.answer(shrine_text, parse_mode=ParseMode.HTML)

# ========== SCAN FUNCTION ==========
async def scan_users_and_groups():
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        c.execute("SELECT DISTINCT user_id FROM command_logs WHERE chat_type = 'private'")
        user_ids = [row[0] for row in c.fetchall()]
        
        updated_users = 0
        new_users = 0
        
        for user_id in user_ids:
            if user_id:
                try:
                    user = await bot.get_chat(user_id)
                    if user.type == 'private':
                        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                        if not c.fetchone():
                            c.execute("INSERT INTO users (user_id, username, first_name, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                                     (user_id, user.username, user.first_name, datetime.now().isoformat(), datetime.now().isoformat()))
                            updated_users += 1
                            new_users += 1
                        else:
                            c.execute("UPDATE users SET username = ?, first_name = ?, last_active = ? WHERE user_id = ?",
                                     (user.username, user.first_name, datetime.now().isoformat(), user_id))
                            updated_users += 1
                except:
                    continue
        
        c.execute("SELECT DISTINCT chat_id FROM command_logs WHERE chat_type IN ('group', 'supergroup')")
        chat_ids = [row[0] for row in c.fetchall()]
        
        updated_groups = 0
        new_groups = 0
        
        for chat_id in chat_ids:
            if chat_id:
                try:
                    chat = await bot.get_chat(chat_id)
                    if chat.type in ['group', 'supergroup']:
                        c.execute("SELECT group_id FROM groups WHERE group_id = ?", (chat_id,))
                        if not c.fetchone():
                            c.execute("INSERT INTO groups (group_id, title, username, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                                     (chat_id, chat.title, chat.username, datetime.now().isoformat(), datetime.now().isoformat()))
                            updated_groups += 1
                            new_groups += 1
                        else:
                            c.execute("UPDATE groups SET title = ?, username = ?, last_active = ? WHERE group_id = ?",
                                     (chat.title, chat.username, datetime.now().isoformat(), chat_id))
                            updated_groups += 1
                except:
                    continue
        
        conn.commit()
        conn.close()
        
        return f"""✅ <b>Scan Complete!</b>

👥 <b>User Statistics:</b>
• Total scanned: {len(user_ids)}
• Updated users: {updated_users}
• New users found: {new_users}

👥 <b>Group Statistics:</b>
• Total scanned: {len(chat_ids)}
• Updated groups: {updated_groups}
• New groups found: {new_groups}

⚡ <i>Database refreshed successfully!</i>"""
        
    except Exception as e:
        return f"❌ Scan error: {str(e)[:100]}"

# ========== COMMON MESSAGE HANDLER ==========
async def handle_common(message: Message, command: str):
    user = message.from_user
    chat = message.chat
    
    update_user(user)
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(chat)
    
    log_command(user.id, chat.id, chat.type, command)
    return user, chat

# ========== START COMMAND ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = await handle_common(message, "start")
    
    await send_log(f"👤 <b>User Started Bot</b>\n\nID: <code>{user.id}</code>\nName: {user.first_name}\nUsername: @{user.username if user.username else 'None'}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await message.answer(
        f"✨ <b>Hey {user.first_name}!</b>\n\n"
        "🌀 <b>TEMPEST BOT - ADVANCED EDITION</b>\n\n"
        "🔗 <b>Upload files</b> - Permanent links\n"
        "📝 <b>Word converter</b> - Text to DOCX\n"
        "✨ <b>Wish fortune teller</b> - Check luck\n"
        "🎮 <b>Fun games</b> - Dice & coin flip\n"
        "👑 <b>Admin controls</b> - Manage bot\n"
        "🌀 <b>Tempest Creed</b> - Join the secret society\n"
        "🏛️ <b>Shrine</b> - Group Tempest stats\n\n"
        "📁 <b>Upload:</b> <code>/link</code> then file\n"
        "📝 <b>Word:</b> <code>/word Your text</code>\n"
        "🎮 <b>Games:</b> <code>/dice</code> <code>/flip</code> <code>/wish</code>\n"
        "👤 <b>Profile:</b> <code>/profile</code>\n"
        "🏛️ <b>Shrine:</b> <code>/shrine</code> (in groups)\n"
        "📚 <b>All commands:</b> <code>/help</code>",
        parse_mode=ParseMode.HTML
    )

# ========== HELP COMMAND ==========
@dp.message(Command("help"))
async def help_cmd(message: Message):
    user, chat = await handle_common(message, "help")
    
    help_text = """📚 <b>TEMPEST BOT - COMPLETE GUIDE</b>

━━━━━━━━━━━━━━━━━━━━━━━━
🔗 <b>UPLOAD SYSTEM</b>
<code>/link</code> - Upload file (send file after)

📝 <b>WORD CONVERTER</b>
<code>/word [text]</code> - Convert text to DOCX

━━━━━━━━━━━━━━━━━━━━━━━━
🌟 <b>WISH & GAMES</b>
<code>/wish [text]</code> - Check luck %
<code>/dice</code> - Roll dice
<code>/flip</code> - Flip coin

━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>USER PROFILE</b>
<code>/profile</code> - Your stats
<code>/start</code> - Welcome message

━━━━━━━━━━━━━━━━━━━━━━━━
🌀 <b>TEMPEST CREED</b>
<code>/tempest_join</code> - Join the cult
<code>/tempest_story</code> - Read the lore
<code>/tempest_creed</code> - View all members
<code>/shrine</code> - Group Tempest stats
<code>/curse</code> - Curse a user
<code>/remove_curse</code> - Remove curse

━━━━━━━━━━━━━━━━━━━━━━━━
👑 <b>ADMIN COMMANDS</b>
<code>/ping</code> - System status & resources
<code>/stats</code> - Bot statistics
<code>/logs [days]</code> - View logs (.txt)
<code>/users</code> - User list (.txt)
<code>/admins</code> - List admins
<code>/scan</code> - Scan for new users
<code>/publish</code> - Publish file to log channel
<code>/backup</code> - Backup database
<code>/toggle</code> - Pause/resume bot

━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <b>OWNER COMMANDS</b>
<code>/pro [id]</code> - Make admin
<code>/rem</code> - Restore from backup
<code>/restart</code> - Reboot bot
<code>/broadcast</code> - Send to all users
<code>/broadcast_gc</code> - Send to groups
<code>/refresh</code> - Refresh cache
<code>/emergency_stop</code> - Stop bot

━━━━━━━━━━━━━━━━━━━━━━━━
📖 <b>STORY PUBLISHING</b>
Chapters can be added via database directly
Contact owner for new story chapters

🌀 <i>The storm flows through all commands</i>
"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== ADMIN COMMANDS ==========
@dp.message(Command("admins"))
async def admins_cmd(message: Message):
    user, chat = await handle_common(message, "admins")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    admins = await get_admins()
    if not admins:
        await message.answer("👑 <b>No admins found</b>", parse_mode=ParseMode.HTML)
        return
    
    admin_text = "👑 <b>BOT ADMINISTRATORS</b>\n\n"
    for user_id, name, username in admins:
        admin_text += f"• {name} {username}\n🆔 <code>{user_id}</code>\n\n"
    
    await message.answer(admin_text, parse_mode=ParseMode.HTML)

async def get_admins():
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name FROM users WHERE is_admin = 1")
    admins = c.fetchall()
    conn.close()
    
    admin_list = []
    for user_id, username, first_name in admins:
        try:
            chat = await bot.get_chat(user_id)
            current_username = f"@{chat.username}" if chat.username else "No username"
            admin_list.append((user_id, chat.first_name, current_username))
        except:
            old_username = f"@{username}" if username else "No username"
            admin_list.append((user_id, first_name, old_username))
    
    return admin_list

@dp.message(Command("scan"))
async def scan_cmd(message: Message):
    user, chat = await handle_common(message, "scan")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    scan_msg = await message.answer("🔍 <b>Scanning database for updates...</b>", parse_mode=ParseMode.HTML)
    result = await scan_users_and_groups()
    await scan_msg.edit_text(result, parse_mode=ParseMode.HTML)

@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user, chat = await handle_common(message, "profile")
    
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
    
    # Try to get user's profile photo
    profile_photo_path = None
    try:
        photos = await bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo = photos.photos[0][-1]
            file = await bot.get_file(photo.file_id)
            profile_photo_path = f"temp/profile_{user.id}_{int(time.time())}.jpg"
            
            url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
            
            if response.status_code == 200:
                with open(profile_photo_path, 'wb') as f:
                    f.write(response.content)
    except Exception as e:
        print(f"❌ Could not get profile photo: {e}")
    
    user_data = (user.id, user.first_name, user.username, uploads, cmds, wishes, 
                cult_rank, sacrifices, curse_type, join_date)
    
    profile_card_path = create_profile_card(user_data, profile_photo_path)
    
    if profile_photo_path and os.path.exists(profile_photo_path):
        try:
            os.remove(profile_photo_path)
        except:
            pass
    
    if profile_card_path and os.path.exists(profile_card_path):
        caption = f"""
👤 <b>Name:</b> {user.first_name}
📧 <b>Username:</b> @{user.username if user.username else 'None'}
🆔 <b>ID:</b> <code>{user.id}</code>

📁 <b>Uploads:</b> {uploads}
✨ <b>Wishes:</b> {wishes}
🔧 <b>Commands:</b> {cmds}
📅 <b>Joined:</b> {join_date}
"""
        
        if cult_rank != "none":
            caption += f"\n🌀 <b>Tempest Rank:</b> {cult_rank}"
            caption += f"\n⚔️ <b>Sacrifices:</b> {sacrifices}"
        
        if curse_type != "none":
            caption += f"\n⚡ <b>Curse:</b> {curse_type}"
        
        if cult_rank != "none":
            caption += "\n\n🌀 <i>The storm flows through your veins...</i>"
        else:
            caption += "\n\n✨ <i>Discover your true potential with /tempest_join</i>"
        
        try:
            await message.answer_photo(
                FSInputFile(profile_card_path),
                caption=caption,
                parse_mode=ParseMode.HTML
            )
            
            async def cleanup():
                await asyncio.sleep(30)
                try:
                    os.remove(profile_card_path)
                except:
                    pass
            
            asyncio.create_task(cleanup())
            return
            
        except Exception as e:
            print(f"❌ Failed to send profile card: {e}")
    
    curse_text = ""
    if curse_type != "none":
        curse_text = f"\n🔮 <b>Curse Status:</b> ⚡ {curse_type}"
    
    cult_text = ""
    if cult_rank != "none":
        cult_text = f"\n🌀 <b>Tempest Rank:</b> {cult_rank}"
        cult_text += f"\n⚔️ <b>Sacrifices:</b> {sacrifices}"
    else:
        cult_text = f"\n🌀 <b>Tempest Status:</b> Not initiated\n💡 Use /tempest_join to begin"
    
    profile_text = f"""
👤 <b>PROFILE</b>

<b>Name:</b> {user.first_name}
<b>Username:</b> @{user.username if user.username else 'None'}
<b>ID:</b> <code>{user.id}</code>

<b>Uploads:</b> {uploads}
<b>Wishes:</b> {wishes}
<b>Commands:</b> {cmds}
<b>Joined:</b> {join_date}{cult_text}{curse_text}
"""
    
    if cult_rank != "none":
        profile_text += "\n🌀 <i>The storm flows through your veins...</i>"
    else:
        profile_text += "\n✨ <i>Discover your true potential...</i>"
    
    await message.answer(profile_text, parse_mode=ParseMode.HTML)

@dp.message(Command("logs"))
async def logs_cmd(message: Message):
    user, chat = await handle_common(message, "logs")
    
    if not await is_admin(user.id):
        return
    
    args = message.text.split()
    days = 1
    if len(args) > 1 and args[1].isdigit():
        days = int(args[1])
        if days > 30:
            days = 30
    
    log_command(user.id, chat.id, chat.type, f"logs {days}")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    threshold_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    c.execute("SELECT timestamp, user_id, chat_type, command, success FROM command_logs WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 500", 
              (threshold_date,))
    cmd_logs = c.fetchall()
    
    c.execute("SELECT timestamp, user_id, command, error FROM error_logs WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 200", 
              (threshold_date,))
    err_logs = c.fetchall()
    
    conn.close()
    
    log_content = f"📊 BOT LOGS - Last {days} day(s)\n"
    log_content += "=" * 50 + "\n\n"
    log_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    log_content += f"Total Commands: {len(cmd_logs)}\n"
    log_content += f"Total Errors: {len(err_logs)}\n\n"
    
    log_content += "📝 COMMAND LOGS:\n"
    log_content += "-" * 30 + "\n"
    for ts, uid, chat_type, cmd, succ in cmd_logs[:100]:
        try:
            time_str = datetime.fromisoformat(ts).strftime("%m/%d %H:%M")
        except:
            time_str = ts[:16]
        status = "✅" if succ else "❌"
        chat = {"private": "PRV", "group": "GRP", "supergroup": "SGR"}.get(chat_type, "UNK")
        log_content += f"[{time_str}] {chat} {uid} {status} {cmd}\n"
    
    log_content += "\n\n❌ ERROR LOGS:\n"
    log_content += "-" * 30 + "\n"
    for ts, uid, cmd, err in err_logs[:50]:
        try:
            time_str = datetime.fromisoformat(ts).strftime("%m/%d %H:%M")
        except:
            time_str = ts[:16]
        log_content += f"[{time_str}] {uid} {cmd}: {err}\n"
    
    filename = f"temp/logs_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(log_content)
    
    await message.answer_document(
        FSInputFile(filename),
        caption=f"📁 Logs file ({days} day(s))"
    )
    
    try:
        os.remove(filename)
    except:
        pass

@dp.message(Command("users"))
async def users_cmd(message: Message):
    user, chat = await handle_common(message, "users")
    
    if not await is_admin(user.id):
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, uploads, commands, last_active FROM users ORDER BY joined_date DESC LIMIT 100")
    users = c.fetchall()
    conn.close()
    
    user_list = "👥 USER LIST (Last 100)\n" + "="*50 + "\n\n"
    for uid, name, uname, up, cmds, last_active in users:
        un = f"@{uname}" if uname else "No username"
        
        try:
            last_date = datetime.fromisoformat(last_active)
            days_ago = (datetime.now() - last_date).days
            if days_ago == 0:
                activity = "Today"
            elif days_ago == 1:
                activity = "Yesterday"
            else:
                activity = f"{days_ago}d ago"
        except:
            activity = "Unknown"
        
        user_list += f"🆔 {uid}\n👤 {name}\n📧 {un}\n📁 {up} | 🔧 {cmds}\n🕒 {activity}\n" + "-"*40 + "\n"
    
    filename = f"temp/users_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(user_list)
    
    await message.answer_document(
        FSInputFile(filename),
        caption="📁 User list with activity"
    )
    
    try:
        os.remove(filename)
    except:
        pass

# ========== PRO COMMAND ==========
@dp.message(Command("pro"))
async def pro_cmd(message: Message):
    user, chat = await handle_common(message, "pro")
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only command")
        return
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("👑 <b>Usage:</b> <code>/pro user_id</code>", parse_mode=ParseMode.HTML)
        return
    
    target_id = int(args[1])
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
    if not c.fetchone():
        try:
            target_user = await bot.get_chat(target_id)
            c.execute("INSERT INTO users (user_id, username, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                     (target_id, target_user.username, target_user.first_name, datetime.now().isoformat(), datetime.now().isoformat(), 1))
        except:
            c.execute("INSERT INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
                     (target_id, f"User_{target_id}", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    else:
        c.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (target_id,))
    
    conn.commit()
    conn.close()
    
    await send_log(f"👑 <b>Admin Promotion</b>\n\nPromoted by: {user.first_name}\nPromoted user: {target_id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await message.answer(f"✅ User {target_id} promoted to admin!")

@dp.message(Command("toggle"))
async def toggle_cmd(message: Message):
    user, chat = await handle_common(message, "toggle")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    global bot_active
    bot_active = not bot_active
    status = "🟢 ACTIVE" if bot_active else "🔴 PAUSED"
    await message.answer(f"✅ Bot is now {status}")

# ========== BROADCAST COMMANDS ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast_start")
    
    if not await is_admin(user.id):
        return
    
    broadcast_state[user.id] = {"type": "users", "step": 1}
    save_bot_state()
    
    await message.answer(
        "📢 <b>BROADCAST TO ALL USERS</b>\n\n"
        "Send any message now:\n"
        "• Text message\n"
        "• Photo with caption\n"
        "• Video with caption\n"
        "• Document with caption\n\n"
        "⚠️ <b>Next message will be sent to ALL USERS</b>\n"
        "❌ <code>/cancel</code> to abort",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("broadcast_gc"))
async def broadcast_gc_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast_gc_start")
    
    if not await is_admin(user.id):
        return
    
    broadcast_state[user.id] = {"type": "groups", "step": 1}
    save_bot_state()
    
    await message.answer(
        "📢 <b>BROADCAST TO ALL GROUPS</b>\n\n"
        "Send any message now:\n"
        "• Text message\n"
        "• Photo with caption\n"
        "• Video with caption\n"
        "• Document with caption\n\n"
        "⚠️ <b>Next message will be sent to ALL GROUPS</b>\n"
        "❌ <code>/cancel</code> to abort",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("refresh"))
async def refresh_cmd(message: Message):
    user, chat = await handle_common(message, "refresh")
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only command")
        return
    
    global broadcast_state, pending_joins, pending_invites, story_states
    broadcast_state.clear()
    pending_joins.clear()
    pending_invites.clear()
    story_states.clear()
    
    save_bot_state()
    
    await message.answer("🔄 <b>Bot cache refreshed!</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("emergency_stop"))
async def emergency_stop(message: Message):
    user, chat = await handle_common(message, "emergency_stop")
    
    if user.id != OWNER_ID:
        return
    
    global bot_active
    bot_active = False
    
    await message.answer("🛑 <b>BOT EMERGENCY STOPPED!</b>", parse_mode=ParseMode.HTML)

# ========== FILE UPLOAD ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = await handle_common(message, "link")
    
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 <b>Upload files in private chat only</b>", parse_mode=ParseMode.HTML)
        return
    
    upload_waiting[user.id] = True
    save_bot_state()
    
    await message.answer(
        "📁 <b>Now send me any file:</b>\n"
        "• Photo, video, document\n"
        "• Audio, voice, sticker\n"
        "• Max 200MB\n\n"
        "❌ <code>/cancel</code> to stop",
        parse_mode=ParseMode.HTML
    )

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation | F.video_note)
async def handle_file(message: Message):
    user = message.from_user
    chat = message.chat
    
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
    if user.id not in upload_waiting or not upload_waiting[user.id]:
        return
    
    upload_waiting[user.id] = False
    save_bot_state()
    
    msg = await message.answer("⏳ <b>Processing...</b>", parse_mode=ParseMode.HTML)
    
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
        elif message.sticker:
            file_id = message.sticker.file_id
            file_type = "Sticker"
        elif message.animation:
            file_id = message.animation.file_id
            file_type = "GIF"
        elif message.video_note:
            file_id = message.video_note.file_id
            file_type = "Video Note"
        else:
            await msg.edit_text("❌ Unsupported file type")
            return
        
        await msg.edit_text("📥 <b>Downloading...</b>", parse_mode=ParseMode.HTML)
        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
        
        if response.status_code != 200:
            await msg.edit_text("❌ Failed to download file")
            return
        
        file_data = response.content
        file_size = len(file_data)
        
        await msg.edit_text("☁️ <b>Uploading...</b>", parse_mode=ParseMode.HTML)
        filename = file.file_path.split('/')[-1] if '/' in file.file_path else f"file_{file_id}"
        result = await upload_to_catbox_advanced(file_data, filename)
        
        if not result['success']:
            await msg.edit_text("❌ Upload failed")
            return
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,))
        
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        cult_status = c.fetchone()
        if cult_status and cult_status[0] != 'none':
            c.execute("UPDATE users SET sacrifices = sacrifices + 1 WHERE user_id = ?", (user.id,))
        
        c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)",
                 (user.id, datetime.now().isoformat(), result['url'], file_type, file_size))
        conn.commit()
        conn.close()
        
        size_kb = file_size / 1024
        size_mb = size_kb / 1024
        size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="📋 Copy Link", callback_data=f"copy_{result['url']}"))
        keyboard.add(InlineKeyboardButton(text="🔗 Share", url=f"https://t.me/share/url?url={result['url']}"))
        
        result_text = f"""✅ <b>Upload Complete!</b>

📁 <b>Type:</b> {file_type}
💾 <b>Size:</b> {size_text}
👤 <b>By:</b> {user.first_name}

🔗 <b>Direct Link:</b>
<code>{result['url']}</code>

📤 Permanent link • No expiry • Share anywhere"""
        
        if cult_status and cult_status[0] != 'none':
            result_text += f"\n\n🌀 <i>+1 sacrifice to the Tempest</i>"
        
        await msg.edit_text(result_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
        log_command(user.id, chat.id, chat.type, "upload", True)
        
    except Exception as e:
        await msg.edit_text("❌ Error uploading file")
        log_error(user.id, "upload", e)

@dp.callback_query(F.data.startswith("copy_"))
async def handle_copy(callback: CallbackQuery):
    url = callback.data[5:]
    await safe_answer_callback(callback, f"Link copied to clipboard!\n{url}", show_alert=True)

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user, chat = await handle_common(message, "cancel")
    
    if user.id in upload_waiting:
        upload_waiting[user.id] = False
        save_bot_state()
        await message.answer("❌ Upload cancelled")
    
    if user.id in broadcast_state:
        broadcast_state.pop(user.id, None)
        save_bot_state()
        await message.answer("❌ Broadcast cancelled")
    
    if user.id in story_states:
        story_states.pop(user.id, None)
        await message.answer("❌ Story cancelled")
    
    if user.id in pending_restore:
        pending_restore.pop(user.id, None)
        await message.answer("❌ Restore cancelled")

# ========== GAMES ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ <b>Usage:</b> <code>/wish your wish here</code>", parse_mode=ParseMode.HTML)
        return
    
    msg = await message.answer("✨ <b>Reading your destiny...</b>", parse_mode=ParseMode.HTML)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT curse_type FROM users WHERE user_id = ?", (user.id,))
    curse_result = c.fetchone()
    curse_type = curse_result[0] if curse_result else "none"
    
    curse_penalty = 0
    curse_message = ""
    if curse_type != "none":
        curse_penalty = random.randint(15, 30)
        curse_message = f"\n⚡ <b>Curse penalty:</b> -{curse_penalty}%"
    
    for emoji in ["🌟", "⭐", "💫", "🌠", "✨"]:
        await msg.edit_text(f"{emoji} <b>Consulting the stars...</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    base_luck = random.randint(1, 100)
    luck = max(1, base_luck - curse_penalty)
    stars = "⭐" * (luck // 10)
    
    if luck >= 90:
        result = "🎊 EXCELLENT! Will definitely happen!"
    elif luck >= 70:
        result = "😊 VERY GOOD! High chance!"
    elif luck >= 50:
        result = "👍 GOOD! Potential success!"
    elif luck >= 30:
        result = "🤔 AVERAGE - Needs effort"
    elif luck >= 10:
        result = "😟 LOW - Try again"
    else:
        result = "💀 VERY LOW - Bad timing"
    
    c.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
             (user.id, datetime.now().isoformat(), args[1], luck))
    conn.commit()
    conn.close()
    
    await msg.edit_text(
        f"🔮 <b>WISH RESULT</b>\n\n"
        f"📜 <b>Wish:</b> {args[1]}\n"
        f"🎰 <b>Luck:</b> {stars} {luck}%{curse_message}\n"
        f"📊 <b>Result:</b> {result}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    user, chat = await handle_common(message, "dice")
    
    msg = await message.answer("🎲 <b>Rolling dice...</b>", parse_mode=ParseMode.HTML)
    
    faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    for i in range(6):
        await msg.edit_text(f"🎲 <b>Rolling...</b> {faces[i]}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.15)
    
    roll = random.randint(1, 6)
    await msg.edit_text(f"🎲 <b>You rolled: {faces[roll-1]} ({roll})</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    user, chat = await handle_common(message, "flip")
    
    msg = await message.answer("🪙 <b>Flipping coin...</b>", parse_mode=ParseMode.HTML)
    
    for i in range(5):
        await msg.edit_text(f"🪙 <b>Flipping...</b> {'HEADS' if i % 2 == 0 else 'TAILS'}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}</b>", parse_mode=ParseMode.HTML)

# ========== CURSE COMMAND ==========
@dp.message(Command("curse", ignore_case=True))
async def curse_cmd(message: Message):
    user, chat = await handle_common(message, "curse")
    
    if not await is_admin(user.id):
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        result = c.fetchone()
        if not result or result[0] == "none":
            await message.answer("🌀 This command is for Tempest members only.")
            conn.close()
            return
        conn.close()
    
    if not message.reply_to_message:
        await message.answer("🌀 <b>Reply to a user's message to curse them!</b>", parse_mode=ParseMode.HTML)
        return
    
    target_user = message.reply_to_message.from_user
    
    if target_user.id == user.id:
        await message.reply("🌀 You cannot curse yourself!")
        return
    
    if await is_admin(target_user.id):
        await message.reply("🌀 You cannot curse an admin!")
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT curse_type FROM users WHERE user_id = ?", (target_user.id,))
    existing_curse = c.fetchone()
    
    if existing_curse and existing_curse[0] != "none":
        await message.reply(f"🌀 {target_user.first_name} is already cursed with {existing_curse[0]}!")
        conn.close()
        return
    
    curses = [
        ("Misfortune", "May misfortune follow your every step!"),
        ("Bad Luck", "Bad luck shall be your constant companion!"),
        ("Storm's Wrath", "The storm's wrath shall rain upon you!"),
        ("Eternal Suffering", "May you know eternal suffering!"),
        ("Ravijah's Displeasure", "You have earned Ravijah's displeasure!"),
        ("Shadow's Grip", "The shadows shall never release you!")
    ]
    
    curse_type, curse_quote = random.choice(curses)
    
    c.execute("UPDATE users SET curse_type = ?, curse_time = ?, curse_by = ? WHERE user_id = ?",
             (curse_type, datetime.now().isoformat(), user.id, target_user.id))
    conn.commit()
    conn.close()
    
    msg = await message.reply(f"🌀 <b>INITIATING CURSE RITUAL...</b>")
    
    curse_steps = [
        f"🌀 <b>GATHERING DARK ENERGY...</b>\nTarget: {target_user.first_name}",
        f"⚡ <b>SUMMONING RAVIJAH'S WRATH...</b>\nCurse: {curse_type}",
        f"🌪️ <b>WEAVING THE CURSE SPELL...</b>\nBinding to {target_user.first_name}'s soul",
        f"🔥 <b>ETERNAL FLAMES CONSUME...</b>\nThe curse takes hold",
        f"💀 <b>CURSE SEALED FOR ETERNITY!</b>\n{target_user.first_name} is now cursed!"
    ]
    
    for step in curse_steps:
        await msg.edit_text(step, parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.5)
    
    final_message = f"""
⚡ <b>ETERNAL CURSE BESTOWED!</b>

👤 <b>Target:</b> {target_user.first_name}
🌀 <b>Curse Type:</b> {curse_type}
👑 <b>Cursed By:</b> {user.first_name}
⏰ <b>Time:</b> {datetime.now().strftime("%H:%M:%S")}

📜 <b>The Curse:</b>
"{curse_quote}"

⚡ <i>You shall suffer the great Ravijah's wrath!</i>
🌀 <i>The storm remembers all offenses...</i>

💀 <b>Effects:</b>
• -15 to -30% wish luck penalty
• Visible in /profile
• Lasts until removed by admin
"""
    
    await msg.edit_text(final_message, parse_mode=ParseMode.HTML)
    
    await send_log(f"⚡ <b>Curse Cast</b>\n\n👤 Target: {target_user.first_name}\n🆔 Target ID: {target_user.id}\n🌀 Curse: {curse_type}\n👑 Cursed by: {user.first_name}\n⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ========== REMOVE CURSE COMMAND ==========
@dp.message(Command("remove_curse", ignore_case=True))
async def remove_curse_cmd(message: Message):
    user, chat = await handle_common(message, "remove_curse")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    if not message.reply_to_message:
        await message.answer("🌀 <b>Reply to a user's message to remove their curse!</b>", parse_mode=ParseMode.HTML)
        return
    
    target_user = message.reply_to_message.from_user
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT curse_type FROM users WHERE user_id = ?", (target_user.id,))
    existing_curse = c.fetchone()
    
    if not existing_curse or existing_curse[0] == "none":
        await message.reply(f"🌀 {target_user.first_name} is not cursed!")
        conn.close()
        return
    
    c.execute("UPDATE users SET curse_type = 'none', curse_time = NULL, curse_by = NULL WHERE user_id = ?",
             (target_user.id,))
    conn.commit()
    conn.close()
    
    await message.reply(f"""
✅ <b>CURSE REMOVED!</b>

👤 <b>Target:</b> {target_user.first_name}
👑 <b>Removed by:</b> {user.first_name}
⏰ <b>Time:</b> {datetime.now().strftime("%H:%M:%S")}

🌀 <i>The storm's wrath has been appeased.
May you walk in the light once more...</i>
""", parse_mode=ParseMode.HTML)

# ========== TEMPEST JOIN ==========
@dp.message(Command("tempest_join", ignore_case=True))
async def tempest_join_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_join")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        await message.answer("🌀 <b>Already part of the Tempest!</b>\nCheck your status in /profile", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    conn.close()
    
    pending_joins[user.id] = {
        "name": user.first_name,
        "step": 1,
        "chat_id": chat.id
    }
    
    keyboard = InlineKeyboardBuilder()
    
    for i in range(1, 9):
        keyboard.add(InlineKeyboardButton(text=f"{i}", callback_data=f"sacrifice_{i}"))
    keyboard.add(InlineKeyboardButton(text="❌ CANCEL", callback_data="sacrifice_cancel"))
    keyboard.adjust(4, 4, 2)
    
    await message.answer(
        "⚡ <b>TEMPEST BLOOD CEREMONY</b>\n\n"
        "🌩️ <i>The storm demands a REAL sacrifice...</i>\n\n"
        "<b>Choose your offering:</b>\n\n"
        "1. 🩸 Your firstborn's eternal soul\n"
        "2. 💎 A diamond worth a kingdom\n"  
        "3. 📜 Your complete internet history\n"
        "4. 🎮 Your legendary gaming account\n"
        "5. 👻 Your soul (no refunds)\n"
        "6. 💳 Your credit card details\n"
        "7. 📱 Your phone (with all data)\n"
        "8. 🔐 Your deepest secret\n\n"
        "<i>Warning: Fake sacrifices will be rejected!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data.startswith("sacrifice_"))
async def handle_sacrifice(callback: CallbackQuery):
    user = callback.from_user
    chat_id = callback.message.chat.id
    
    if user.id not in pending_joins:
        await safe_answer_callback(callback, "❌ Initiation expired!", show_alert=True)
        return
    
    if callback.data == "sacrifice_cancel":
        del pending_joins[user.id]
        await callback.message.edit_text("🌀 <b>Initiation cancelled. The storm is disappointed.</b>", parse_mode=ParseMode.HTML)
        await safe_answer_callback(callback)
        return
    
    sacrifice_num = callback.data.split("_")[1]
    
    sacrifices = {
        "1": "🩸 Your firstborn's eternal soul",
        "2": "💎 A diamond worth a kingdom",
        "3": "📜 Your complete internet history", 
        "4": "🎮 Your legendary gaming account",
        "5": "👻 Your soul (no refunds)",
        "6": "💳 Your credit card details",
        "7": "📱 Your phone (with all data)",
        "8": "🔐 Your deepest secret"
    }
    
    sacrifice = sacrifices.get(sacrifice_num, "Mysterious offering")
    
    msg = callback.message
    await msg.edit_text(f"🌀 <b>VERIFYING SACRIFICE...</b>\n\n⚡ {sacrifice}", parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    
    is_real, status = await sacrifice_verification(sacrifice)
    
    if not is_real:
        del pending_joins[user.id]
        
        rejection = random.choice([
            f"❌ <b>SACRIFICE REJECTED!</b>\n\n⚡ '{sacrifice}' is FAKE!\n🌩️ The storm LAUGHS at your pathetic offering!\n🌀 <i>Banned from initiation for 24 hours!</i>",
            f"💀 <b>THE STORM ANGERED!</b>\n\n⚡ Fake: '{sacrifice}'\n🌪️ The Tempest SPITS on your worthless offering!\n🌀 <i>Return when you have REAL value...</i>",
            f"👁️ <b>COUNCIL VERDICT: UNWORTHY!</b>\n\n⚡ '{sacrifice}'? Really?\n🌩️ Even the shadows mock your attempt!\n🌀 <i>The storm remembers this insult...</i>"
        ])
        
        await msg.edit_text(rejection, parse_mode=ParseMode.HTML)
        await safe_answer_callback(callback, "❌ Fake sacrifice detected!", show_alert=True)
        return
    
    pending_joins[user.id]["sacrifice"] = sacrifice
    pending_joins[user.id]["verified"] = status
    
    ceremony_steps = [
        "🩸 <b>STEP 1: BLOOD OATH</b>\n\nA black obsidian blade materializes...\nYour palm is cut, blood flows into ancient bowl...",
        "🔥 <b>STEP 2: ETERNAL FLAMES</b>\n\nDark flames consume your offering...\nThe sacrifice burns with green fire...",
        "👁️ <b>STEP 3: ELDER GAZE</b>\n\nAncient eyes watch from shadows...\nThe Council approves your blood...",
        "⚡ <b>STEP 4: LIGHTNING BRANDING</b>\n\nLightning strikes your chest...\nThe Tempest sigil burns into your soul...",
        "🌪️ <b>STEP 5: STORM CONSUMPTION</b>\n\nThe vortex opens...\nYour sacrifice is consumed by eternal tempest...",
        "🌀 <b>STEP 6: BLOOD BOND</b>\n\nYour blood mixes with the storm...\nThe tempest flows through your veins...",
        "💀 <b>STEP 7: FINAL RITE</b>\n\nYour name is carved in the Book of Shadows...\nThe blood pact is sealed for eternity..."
    ]
    
    for step in ceremony_steps:
        await msg.edit_text(step, parse_mode=ParseMode.HTML)
        await asyncio.sleep(2.5)
    
    final_message = f"""⚡ <b>ETERNAL INITIATION COMPLETE!</b>

🌀 <b>WELCOME TO THE TEMPEST, {pending_joins[user.id]['name'].upper()}!</b>

🩸 <b>Sacrifice:</b> {sacrifice}
👑 <b>Rank:</b> Blood Initiate
⚔️ <b>Starting Sacrifices:</b> 3
🌪️ <b>Blood Oath:</b> ETERNAL

<i>The storm now flows through your veins.
Each upload feeds the Tempest.
Your journey of darkness begins...</i>

🌀 Use /profile to track your bloody path"""
    
    await msg.edit_text(final_message, parse_mode=ParseMode.HTML)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
             (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()
    
    await send_log(f"🌀 <b>New Tempest Member</b>\n\n👤 Name: {user.first_name}\n🆔 ID: {user.id}\n🩸 Sacrifice: {sacrifice}\n🌪️ Joined: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if user.id in pending_joins:
        del pending_joins[user.id]
    
    await safe_answer_callback(callback, "✅ Sacrifice accepted! Welcome to the Tempest!", show_alert=True)

# ========== TEMPEST STORY (Database Driven) ==========
@dp.message(Command("tempest_story", ignore_case=True))
async def tempest_story_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_story")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if not result or result[0] == "none":
        await message.answer("🌀 This command is for Tempest members only.")
        conn.close()
        return
    
    c.execute("SELECT COUNT(*) FROM story_chapters WHERE is_published = 1")
    total_chapters = c.fetchone()[0]
    
    if total_chapters == 0:
        await message.answer("📖 No story chapters available yet.")
        conn.close()
        return
    
    c.execute("SELECT chapter_number, title, content FROM story_chapters WHERE is_published = 1 ORDER BY chapter_number LIMIT 1")
    first_chapter = c.fetchone()
    
    conn.close()
    
    if first_chapter:
        chapter_num, title, content = first_chapter
        
        chapter_text = f"📜 <b>CHAPTER {chapter_num}: {title}</b>\n\n<i>{content}</i>"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🌪️ Next Chapter", callback_data=f"story_next_db_{chapter_num}"))
        
        story_msg = await message.answer("🌀 <b>Loading ancient scrolls...</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)
        await story_msg.edit_text(chapter_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())

@dp.callback_query(F.data.startswith("story_next_db_"))
async def handle_story_next_db(callback: CallbackQuery):
    user = callback.from_user
    current_chapter = int(callback.data.split("_")[-1])
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT chapter_number, title, content FROM story_chapters WHERE is_published = 1 AND chapter_number > ? ORDER BY chapter_number LIMIT 1", (current_chapter,))
    next_chapter = c.fetchone()
    
    if next_chapter:
        chapter_num, title, content = next_chapter
        
        chapter_text = f"📜 <b>CHAPTER {chapter_num}: {title}</b>\n\n<i>{content}</i>"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"story_prev_db_{chapter_num}"))
        
        c.execute("SELECT COUNT(*) FROM story_chapters WHERE is_published = 1 AND chapter_number > ?", (chapter_num,))
        has_next = c.fetchone()[0] > 0
        
        if has_next:
            keyboard.add(InlineKeyboardButton(text="🌪️ Next", callback_data=f"story_next_db_{chapter_num}"))
        
        keyboard.adjust(2)
        
        await callback.message.edit_text(chapter_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
        await safe_answer_callback(callback)
    else:
        end_text = """📜 <b>THE END (FOR NOW)</b>

<i>Your journey through the storm's history is complete.
But remember... the story continues with you.

New chapters may be added by the Council.
The eternal storm always has more tales to tell.</i>

🌀 <b>THE STORM NEVER ENDS</b>

<code>"We are the calm's end. We are the eternal storm."</code>"""
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🔄 Start Over", callback_data="story_restart"))
        
        await callback.message.edit_text(end_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
        await safe_answer_callback(callback)
    
    conn.close()

@dp.callback_query(F.data.startswith("story_prev_db_"))
async def handle_story_prev_db(callback: CallbackQuery):
    user = callback.from_user
    current_chapter = int(callback.data.split("_")[-1])
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT chapter_number, title, content FROM story_chapters WHERE is_published = 1 AND chapter_number < ? ORDER BY chapter_number DESC LIMIT 1", (current_chapter,))
    prev_chapter = c.fetchone()
    
    if prev_chapter:
        chapter_num, title, content = prev_chapter
        
        chapter_text = f"📜 <b>CHAPTER {chapter_num}: {title}</b>\n\n<i>{content}</i>"
        
        keyboard = InlineKeyboardBuilder()
        
        c.execute("SELECT COUNT(*) FROM story_chapters WHERE is_published = 1 AND chapter_number < ?", (chapter_num,))
        has_prev = c.fetchone()[0] > 0
        
        if has_prev:
            keyboard.add(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"story_prev_db_{chapter_num}"))
        
        keyboard.add(InlineKeyboardButton(text="🌪️ Next", callback_data=f"story_next_db_{chapter_num}"))
        keyboard.adjust(2)
        
        await callback.message.edit_text(chapter_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
        await safe_answer_callback(callback)
    
    conn.close()

@dp.callback_query(F.data == "story_restart")
async def handle_story_restart(callback: CallbackQuery):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT chapter_number, title, content FROM story_chapters WHERE is_published = 1 ORDER BY chapter_number LIMIT 1")
    first_chapter = c.fetchone()
    
    conn.close()
    
    if first_chapter:
        chapter_num, title, content = first_chapter
        
        chapter_text = f"📜 <b>CHAPTER {chapter_num}: {title}</b>\n\n<i>{content}</i>"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="🌪️ Next Chapter", callback_data=f"story_next_db_{chapter_num}"))
        
        await callback.message.edit_text(chapter_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
        await safe_answer_callback(callback)

# ========== TEMPEST CREED COMMAND ==========
@dp.message(Command("tempest_creed"))
async def tempest_creed_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_creed")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("""
        SELECT user_id, first_name, username, cult_rank, sacrifices 
        FROM users 
        WHERE is_admin = 1 AND cult_status != 'none' 
        ORDER BY sacrifices DESC
    """)
    founders = c.fetchall()
    
    c.execute("""
        SELECT user_id, first_name, username, cult_rank, sacrifices 
        FROM users 
        WHERE cult_status != 'none' 
        ORDER BY 
            CASE cult_rank
                WHEN 'Storm Lord' THEN 1
                WHEN 'Blood Master' THEN 2
                WHEN 'Blood Adept' THEN 3
                WHEN 'Blood Initiate' THEN 4
                ELSE 5
            END,
            sacrifices DESC
    """)
    members = c.fetchall()
    
    conn.close()
    
    if not members:
        await message.answer("🌀 <b>TEMPEST CREED</b>\n\nNo members have joined the Tempest yet.\n\nUse <code>/tempest_join</code> to become the first!")
        return
    
    creed_text = "🌀 <b>TEMPEST CREED - BLOODLINE</b>\n\n"
    
    if founders:
        creed_text += "👑 <b>FOUNDERS & LEADERS</b>\n"
        for user_id, name, uname, rank, sacrifices in founders:
            username = f"@{uname}" if uname else "No username"
            creed_text += f"• {name} ({username})\n"
            creed_text += f"  👑 {rank} | ⚔️ {sacrifices} sacrifices\n"
            creed_text += f"  🆔 <code>{user_id}</code>\n\n"
    
    total_members = len(members)
    total_sacrifices = sum(m[4] for m in members)
    
    creed_text += f"📊 <b>STATISTICS</b>\n"
    creed_text += f"• Total Members: {total_members}\n"
    creed_text += f"• Total Sacrifices: {total_sacrifices}\n\n"
    
    rank_counts = {}
    for _, _, _, rank, _ in members:
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
    
    creed_text += "👥 <b>RANK DISTRIBUTION</b>\n"
    for rank in ["Blood Initiate", "Blood Adept", "Blood Master", "Storm Lord"]:
        if rank in rank_counts:
            count = rank_counts[rank]
            emoji = {"Blood Initiate": "🩸", "Blood Adept": "⚔️", "Blood Master": "👑", "Storm Lord": "🌀"}.get(rank, "•")
            creed_text += f"{emoji} {rank}: {count}\n"
    
    creed_text += "\n📜 <b>BLOOD OATH</b>\n"
    creed_text += "<i>We remember. We awaken. We are the eternal storm.</i>\n\n"
    creed_text += "⚡ <b>Top Sacrificers</b>:\n"
    
    sorted_members = sorted(members, key=lambda x: x[4], reverse=True)[:10]
    for i, (user_id, name, uname, rank, sacrifices) in enumerate(sorted_members, 1):
        username = f"@{uname}" if uname else ""
        creed_text += f"{i}. {name} {username} - ⚔️ {sacrifices}\n"
    
    creed_text += "\n🌀 <i>The storm grows stronger with each sacrifice...</i>"
    
    await message.answer(creed_text, parse_mode=ParseMode.HTML)

# ========== REPLY INVITATION SYSTEM ==========
@dp.message(F.reply_to_message)
async def handle_reply_invite(message: Message):
    user, chat = await handle_common(message, "reply_invite")
    
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
    if "tempest_join" in message.text.lower() or "join tempest" in message.text.lower():
        replied_user = message.reply_to_message.from_user
        
        if replied_user.id == user.id:
            await message.reply("🤨 You can't invite yourself!")
            return
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (replied_user.id,))
        result = c.fetchone()
        
        if result and result[0] != "none":
            await message.reply(f"🌀 {replied_user.first_name} is already in the Tempest!")
            conn.close()
            return
        conn.close()
        
        invite_id = f"invite_{int(time.time())}_{user.id}_{replied_user.id}"
        pending_invites[invite_id] = {
            "inviter_id": user.id,
            "inviter_name": user.first_name,
            "target_id": replied_user.id,
            "target_name": replied_user.first_name,
            "group_id": chat.id,
            "timestamp": datetime.now().isoformat()
        }
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="✅ Accept Blood Pact", callback_data=f"reply_invite_accept_{invite_id}"))
        keyboard.add(InlineKeyboardButton(text="❌ Decline", callback_data=f"reply_invite_decline_{invite_id}"))
        
        invite_text = f"""📨 <b>TEMPEST BLOOD INVITATION!</b>

👤 <b>{user.first_name}</b> invites <b>{replied_user.first_name}</b> to join the Tempest!
🌀 <i>This is a BLOOD PACT - choose wisely...</i>

⚡ What awaits:
• 🩸 Blood initiation ceremony
• 💀 Eternal membership
• 🌪️ Power through sacrifice
• 👑 Rank: Blood Initiate
• ⚔️ +3 starting sacrifices

🌩️ <b>Will you accept the storm's call?</b>

<i>Invitation expires in 2 minutes...</i>"""
        
        invite_msg = await message.reply(invite_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
        
        await asyncio.sleep(120)
        try:
            await bot.delete_message(chat.id, invite_msg.message_id)
            if invite_id in pending_invites:
                del pending_invites[invite_id]
        except:
            pass

@dp.callback_query(F.data.startswith("reply_invite_"))
async def handle_reply_invite_response(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    if len(data_parts) < 5:
        await safe_answer_callback(callback, "Invalid invite!")
        return
    
    action = data_parts[3]
    invite_id = "_".join(data_parts[4:])
    
    if invite_id not in pending_invites:
        await safe_answer_callback(callback, "Invite expired!")
        return
    
    invite_data = pending_invites[invite_id]
    user = callback.from_user
    
    if user.id != invite_data["target_id"]:
        await safe_answer_callback(callback, "This invitation isn't for you!", show_alert=True)
        return
    
    if action == "accept":
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        result = c.fetchone()
        
        if result and result[0] != "none":
            await safe_answer_callback(callback, "You're already in the cult!", show_alert=True)
            conn.close()
            return
        
        c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Blood Initiate', cult_join_date = ?, sacrifices = 3 WHERE user_id = ?",
                 (datetime.now().isoformat(), user.id))
        conn.commit()
        conn.close()
        
        await safe_answer_callback(callback, "✅ Blood pact accepted!", show_alert=True)
        
        await callback.message.edit_text(
            f"🎉 <b>BLOOD PACT SEALED!</b>\n\n"
            f"👤 <b>{user.first_name}</b> has accepted {invite_data['inviter_name']}'s invitation!\n"
            f"🩸 Blood oath sworn to the Tempest\n"
            f"🌀 Rank: Blood Initiate\n"
            f"⚔️ Starting sacrifices: 3\n\n"
            f"<i>The storm grows stronger with new blood...</i>",
            parse_mode=ParseMode.HTML
        )
        
        await send_log(f"🌀 <b>Invitation Accepted</b>\n\n👤 Invited: {user.first_name}\n👑 Inviter: {invite_data['inviter_name']}\n🆔 User ID: {user.id}\n🌪️ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    elif action == "decline":
        await safe_answer_callback(callback, "❌ Invitation declined", show_alert=True)
        await callback.message.edit_text(
            f"🚫 <b>INVITATION REJECTED</b>\n\n"
            f"👤 <b>{user.first_name}</b> rejected the Tempest's call.\n"
            f"👑 Invited by: {invite_data['inviter_name']}\n\n"
            f"<i>Their blood remains unspilled... for now.</i>",
            parse_mode=ParseMode.HTML
        )
    
    if invite_id in pending_invites:
        del pending_invites[invite_id]
    
    await asyncio.sleep(30)
    try:
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
    except:
        pass

# ========== BROADCAST HANDLER ==========
@dp.message()
async def handle_broadcast(message: Message):
    user = message.from_user
    chat = message.chat
    
    update_user(user)
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(chat)
    
    if user.id in broadcast_state:
        if broadcast_state[user.id].get("step") == 1:
            broadcast_data = broadcast_state[user.id]
            broadcast_type = broadcast_data["type"]
            
            broadcast_state[user.id]["step"] = 2
            save_bot_state()
            
            if broadcast_type == "users":
                conn = sqlite3.connect("data/bot.db")
                c = conn.cursor()
                c.execute("SELECT user_id FROM users WHERE is_banned = 0")
                targets = [row[0] for row in c.fetchall()]
                conn.close()
                target_type = "users"
            else:
                conn = sqlite3.connect("data/bot.db")
                c = conn.cursor()
                c.execute("SELECT group_id FROM groups")
                targets = [row[0] for row in c.fetchall()]
                conn.close()
                target_type = "groups"
            
            total = len(targets)
            if total == 0:
                await message.answer(f"❌ No {target_type} found to broadcast!")
                broadcast_state.pop(user.id, None)
                save_bot_state()
                return
            
            status_msg = await message.answer(f"📤 Sending to {total} {target_type}...")
            
            success = 0
            failed = 0
            
            for target_id in targets:
                try:
                    if message.text:
                        await bot.send_message(target_id, f"📢 {message.text}")
                    elif message.photo:
                        caption = message.caption or "📢 Broadcast"
                        await bot.send_photo(target_id, message.photo[-1].file_id, caption=caption)
                    elif message.video:
                        caption = message.caption or "📢 Broadcast"
                        await bot.send_video(target_id, message.video.file_id, caption=caption)
                    elif message.document:
                        caption = message.caption or "📢 Broadcast"
                        await bot.send_document(target_id, message.document.file_id, caption=caption)
                    elif message.audio:
                        caption = message.caption or "📢 Broadcast"
                        await bot.send_audio(target_id, message.audio.file_id, caption=caption)
                    elif message.sticker:
                        await bot.send_sticker(target_id, message.sticker.file_id)
                    elif message.animation:
                        caption = message.caption or "📢 Broadcast"
                        await bot.send_animation(target_id, message.animation.file_id, caption=caption)
                    elif message.voice:
                        await bot.send_voice(target_id, message.voice.file_id)
                    
                    success += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    failed += 1
                    continue
            
            broadcast_state.pop(user.id, None)
            save_bot_state()
            
            await status_msg.edit_text(f"✅ Sent to {success}/{total} {target_type}\n❌ Failed: {failed}")
            
            await send_log(f"📢 <b>Broadcast Sent</b>\n\nBy: {user.first_name}\nType: {target_type}\nSent: {success}/{total}\nFailed: {failed}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ========== MAIN ==========
async def main():
    print("🚀 TEMPEST BOT ADVANCED STARTING...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ Database initialized")
    print("🌀 Tempest: ALL COMMANDS WORKING")
    print("📡 Scan: WORKING")
    print("📊 Log Channel: FIXED")
    print("📢 Broadcast: WORKING")
    print("🔗 Upload: ENHANCED")
    print("📜 Story: DATABASE DRIVEN")
    print("⚡ Curse System: WORKING")
    print("💾 State Saving: ENABLED")
    print("🖼️ Profile Cards: WITH PFP")
    print("📝 Word Converter: ADDED")
    print("💓 Keep-Alive: ENABLED")
    print("🏛️ Shrine: ADDED")
    print("💾 REM Restore: ADDED")
    print("🔄 Restart: ADDED")
    print("📊 Enhanced Stats: ADDED")
    print("=" * 50)
    
    # Start keep-alive task
    asyncio.create_task(keep_alive())
    
    startup_log = f"🤖 <b>Tempest Bot - Advanced Version</b>\n\n🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🌀 Version: Advanced\n⚡ Status: ALL SYSTEMS ACTIVE\n💾 State Restored: YES\n🖼️ Profile Cards: WITH PFP\n📝 Word Converter: READY\n💓 Keep-Alive: RUNNING\n🏛️ Shrine: ACTIVE\n💾 REM Restore: READY\n🔄 Restart: READY"
    await send_log(startup_log)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        save_bot_state()
        print("\n🛑 Bot stopped gracefully (state saved)")
    except Exception as e:
        save_bot_state()
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()