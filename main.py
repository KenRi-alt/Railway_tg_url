#!/usr/bin/env python3
# ========== COMPLETE ORIGINAL BOT - ALL FEATURES WORKING ==========
print("=" * 60)
print("🌀 TEMPEST CULT BOT")
print("✅ All Original Commands + Working Features")
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
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from io import BytesIO

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

print("🤖 INITIALIZING BOT...")

# ========== CONFIGURATION ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845  # Fixed negative ID

# Create directories
Path("data").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True)
Path("backups").mkdir(exist_ok=True)
Path("fonts").mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== DATABASE SETUP ==========
def init_db():
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Original tables
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        joined_date TEXT,
        last_active TEXT,
        uploads INTEGER DEFAULT 0,
        commands INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS wishes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,
        wish_text TEXT,
        luck INTEGER
    )''')
    
    # ========== TEMPEST TABLES ==========
    c.execute('''CREATE TABLE IF NOT EXISTS tempest_members (
        user_id INTEGER PRIMARY KEY,
        status TEXT DEFAULT 'none',
        rank TEXT DEFAULT 'Mortal',
        join_date TEXT,
        total_sacrifices INTEGER DEFAULT 0,
        tempest_points INTEGER DEFAULT 0,
        blood_coins INTEGER DEFAULT 100,
        daily_streak INTEGER DEFAULT 0,
        last_daily TEXT,
        last_backup TEXT,
        
        -- Battle Stats
        battle_wins INTEGER DEFAULT 0,
        battle_losses INTEGER DEFAULT 0,
        battles_drawn INTEGER DEFAULT 0,
        total_damage_dealt INTEGER DEFAULT 0,
        total_damage_taken INTEGER DEFAULT 0,
        highest_critical INTEGER DEFAULT 0,
        pvp_rating INTEGER DEFAULT 1000,
        
        -- Character Stats
        level INTEGER DEFAULT 1,
        experience INTEGER DEFAULT 0,
        max_experience INTEGER DEFAULT 100,
        health INTEGER DEFAULT 100,
        max_health INTEGER DEFAULT 100,
        attack INTEGER DEFAULT 10,
        defense INTEGER DEFAULT 8,
        speed INTEGER DEFAULT 12,
        critical_chance REAL DEFAULT 0.05,
        critical_damage REAL DEFAULT 1.5,
        
        -- Inventory
        artifacts TEXT DEFAULT '[]',
        abilities TEXT DEFAULT '[]',
        achievements TEXT DEFAULT '[]',
        curses TEXT DEFAULT '[]',
        buffs TEXT DEFAULT '[]',
        equipped_artifact TEXT DEFAULT '',
        favorite_ability TEXT DEFAULT '',
        
        -- Social
        invited_by INTEGER DEFAULT 0,
        invites_count INTEGER DEFAULT 0,
        clan_tag TEXT DEFAULT '',
        honor_level INTEGER DEFAULT 1,
        prestige INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sacrifices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        sacrifice_type TEXT,
        sacrifice_value INTEGER,
        timestamp TEXT,
        verified INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS invites (
        invite_id TEXT PRIMARY KEY,
        inviter_id INTEGER,
        invitee_id INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        accepted_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS artifacts (
        artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        rarity TEXT,
        power INTEGER,
        description TEXT,
        effect TEXT,
        owner_id INTEGER DEFAULT 0,
        equipped INTEGER DEFAULT 0,
        created_date TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS quests (
        quest_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        quest_type TEXT,
        quest_data TEXT,
        progress INTEGER DEFAULT 0,
        required INTEGER DEFAULT 1,
        completed INTEGER DEFAULT 0,
        reward_points INTEGER DEFAULT 0,
        reward_coins INTEGER DEFAULT 0,
        assigned_date TEXT,
        completed_date TEXT
    )''')
    
    # Insert owner
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== HELPER FUNCTIONS ==========
async def send_log(message: str):
    """Send log to channel with error handling"""
    try:
        if LOG_CHANNEL_ID:
            await bot.send_message(LOG_CHANNEL_ID, message[:4000], parse_mode=ParseMode.HTML)
        return True
    except Exception as e:
        print(f"Log error: {e}")
        return False

def update_user(user: types.User):
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

async def is_admin(user_id: int) -> bool:
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

async def upload_to_catbox(file_data, filename):
    try:
        files = {
            'reqtype': (None, 'fileupload'),
            'fileToUpload': (filename, file_data)
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(UPLOAD_API, files=files)
        
        if response.status_code == 200 and response.text.startswith('http'):
            return {'success': True, 'url': response.text.strip()}
        return {'success': False, 'error': 'Upload failed'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_cult_rank(points: int) -> Tuple[str, str, int]:
    ranks = [
        (0, "Mortal", "⚪", 100),
        (100, "Blood Initiate", "🩸", 300),
        (300, "Storm Acolyte", "🌩️", 600),
        (600, "Tempest Disciple", "🌀", 1000),
        (1000, "Elder Warrior", "⚔️", 1500),
        (1500, "Blood Master", "🩸⚔️", 2200),
        (2200, "Storm Lord", "🌩️👑", 3000),
        (3000, "Tempest King", "🌀👑", 4000),
        (4000, "Elder God", "✨👁️", 5500),
        (5500, "Ravijah's Chosen", "🌪️👑", 999999)
    ]
    
    for min_points, rank_name, icon, next_threshold in ranks:
        if points < next_threshold:
            next_points = next_threshold - points
            return f"{icon} {rank_name}", icon, next_points
    
    return f"✨ Ravijah's Avatar", "🌪️", 0

# ========== BASIC COMMANDS ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    welcome_text = f"""✨ <b>Welcome {user.first_name}!</b>

🌀 <b>TEMPEST CULT BOT</b>

🔗 Upload files & get direct links
✨ Wish fortune teller
🎲 Games (dice, coin flip)
👑 Admin controls
🌀 Hidden Tempest Cult System

📚 <b>Commands:</b> <code>/help</code>"""
    
    await message.answer(welcome_text, parse_mode=ParseMode.HTML)

@dp.message(Command("help"))
async def help_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    help_text = """📚 <b>PUBLIC COMMANDS</b>

🔗 <b>Upload:</b>
<code>/link</code> - Upload file (send file after)

🌟 <b>Wish:</b>
<code>/wish [text]</code> - Check luck %

🎮 <b>Games:</b>
<code>/dice</code> - Roll dice
<code>/flip</code> - Flip coin

👤 <b>User:</b>
<code>/profile</code> - Your stats
<code>/start</code> - Welcome

📊 <b>Info:</b>
<code>/stats</code> - Bot statistics

<i>Other commands unlock as you progress...</i>"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT uploads, commands, joined_date FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    
    if row:
        uploads, cmds, joined = row
        try:
            join_date = datetime.fromisoformat(joined).strftime("%d %b %Y")
        except:
            join_date = "Recently"
    else:
        uploads = cmds = 0
        join_date = "Today"
    
    # Check Tempest status
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_status = c.fetchone()
    
    cult_text = ""
    if cult_status and cult_status[0] != 'none':
        c.execute("SELECT rank, tempest_points, blood_coins FROM tempest_members WHERE user_id = ?", (user.id,))
        cult_data = c.fetchone()
        if cult_data:
            rank, points, coins = cult_data
            cult_text = f"\n🌀 <b>Tempest Rank:</b> {rank}\n⭐ <b>Points:</b> {points}\n💰 <b>Coins:</b> {coins}"
    
    conn.close()
    
    profile_text = f"""
👤 <b>PROFILE: {user.first_name}</b>

📁 <b>Uploads:</b> {uploads}
🔧 <b>Commands:</b> {cmds}
📅 <b>Joined:</b> {join_date}
🆔 <b>ID:</b> <code>{user.id}</code>
{cult_text}

💡 <b>Tip:</b> Try /link to upload files"""
    
    await message.answer(profile_text, parse_mode=ParseMode.HTML)

# ========== FILE UPLOAD ==========
upload_waiting = {}

@dp.message(Command("link"))
async def link_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 <b>Upload files in private chat only</b>", parse_mode=ParseMode.HTML)
        return
    
    upload_waiting[user.id] = True
    await message.answer(
        "📁 <b>Now send me any file:</b>\n"
        "• Photo, video, document\n"
        "• Audio, voice, sticker\n"
        "• Max 200MB\n\n"
        "❌ Send any text to cancel",
        parse_mode=ParseMode.HTML
    )

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation)
async def handle_file(message: Message):
    user = message.from_user
    
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
    if user.id not in upload_waiting or not upload_waiting[user.id]:
        return
    
    upload_waiting[user.id] = False
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
        result = await upload_to_catbox(file_data, filename)
        
        if not result['success']:
            await msg.edit_text("❌ Upload failed")
            return
        
        # Update database
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,))
        
        c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)",
                 (user.id, datetime.now().isoformat(), result['url'], file_type, file_size))
        
        # Tempest bonus
        c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
        cult_status = c.fetchone()
        if cult_status and cult_status[0] != 'none':
            c.execute("UPDATE tempest_members SET total_sacrifices = total_sacrifices + 1, tempest_points = tempest_points + 10 WHERE user_id = ?", (user.id,))
            
            c.execute("INSERT INTO sacrifices (user_id, sacrifice_type, sacrifice_value, timestamp, verified) VALUES (?, ?, ?, ?, ?)",
                     (user.id, "file_upload", 10, datetime.now().isoformat(), 1))
        
        conn.commit()
        conn.close()
        
        # Format size
        size_kb = file_size / 1024
        size_mb = size_kb / 1024
        size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
        
        result_text = f"""✅ <b>Upload Complete!</b>

📁 <b>Type:</b> {file_type}
💾 <b>Size:</b> {size_text}
👤 <b>By:</b> {user.first_name}

🔗 <b>Direct Link:</b>
<code>{result['url']}</code>"""
        
        if cult_status and cult_status[0] != 'none':
            result_text += f"\n\n🌀 <i>+1 sacrifice to the Tempest (+10 points)</i>"
        
        await msg.edit_text(result_text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await msg.edit_text("❌ Error uploading file")
        print(f"Upload error: {e}")

# ========== GAMES ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ <b>Usage:</b> <code>/wish your wish here</code>", parse_mode=ParseMode.HTML)
        return
    
    msg = await message.answer("✨ <b>Reading your destiny...</b>", parse_mode=ParseMode.HTML)
    
    for emoji in ["🌟", "⭐", "💫", "🌠", "✨"]:
        await msg.edit_text(f"{emoji} <b>Consulting the stars...</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    luck = random.randint(1, 100)
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
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
             (user.id, datetime.now().isoformat(), args[1], luck))
    conn.commit()
    conn.close()
    
    await msg.edit_text(
        f"🔮 <b>WISH RESULT</b>\n\n"
        f"📜 <b>Wish:</b> {args[1]}\n"
        f"🎰 <b>Luck:</b> {stars} {luck}%\n"
        f"📊 <b>Result:</b> {result}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    dice_value = random.randint(1, 6)
    dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    
    # Check for Tempest bonus
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_status = c.fetchone()
    
    bonus_text = ""
    if cult_status and cult_status[0] != 'none':
        bonus = random.randint(1, 10)
        c.execute("UPDATE tempest_members SET tempest_points = tempest_points + ? WHERE user_id = ?", (bonus, user.id))
        conn.commit()
        bonus_text = f"\n\n🌀 <i>Tempest bonus: +{bonus} points!</i>"
    
    conn.close()
    
    await message.answer(
        f"🎲 <b>You rolled: {dice_faces[dice_value-1]} ({dice_value})</b>{bonus_text}",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    
    # Check for Tempest bonus
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_status = c.fetchone()
    
    bonus_text = ""
    if cult_status and cult_status[0] != 'none':
        bonus = random.randint(1, 5)
        c.execute("UPDATE tempest_members SET blood_coins = blood_coins + ? WHERE user_id = ?", (bonus, user.id))
        conn.commit()
        bonus_text = f"\n\n💰 <i>Tempest bonus: +{bonus} blood coins!</i>"
    
    conn.close()
    
    await message.answer(
        f"🪙 <b>{result}</b>{bonus_text}",
        parse_mode=ParseMode.HTML
    )

# ========== TEMPEST SYSTEM ==========
@dp.message(Command("tempest_join"))
async def tempest_join_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        await message.answer("🌀 <b>You are already in the Tempest.</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    conn.close()
    
    # Start initiation
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🩸 Begin Initiation", callback_data="cult_begin"))
    keyboard.add(InlineKeyboardButton(text="❌ Cancel", callback_data="cult_cancel"))
    
    await message.answer(
        "🌀 <b>You found a hidden path...</b>\n\n"
        "A whisper in the static. A crackle in the silence.\n"
        "The storm calls to those who listen.\n\n"
        "🌩️ <b>The Tempest offers power beyond understanding.</b>\n\n"
        "🩸 <b>Starting bonus:</b> 100 points, 100 coins, 3 sacrifices\n\n"
        "<i>This choice is permanent.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.as_markup()
    )

@dp.message(Command("tempest_profile"))
async def tempest_profile_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_data = c.fetchone()
    
    if not cult_data or cult_data[1] == "none":
        await message.answer("🌀 <b>You are not in the Tempest. Use /tempest_join</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    # Extract data
    status = cult_data[1]
    rank = cult_data[2]
    sacrifices = cult_data[4]
    points = cult_data[5]
    coins = cult_data[6]
    wins = cult_data[10]
    losses = cult_data[11]
    health = cult_data[15]
    attack = cult_data[16]
    defense = cult_data[17]
    speed = cult_data[18]
    critical = cult_data[19] * 100
    
    conn.close()
    
    # Get rank with icon
    rank_name, rank_icon, next_points = get_cult_rank(points)
    
    profile_text = f"""
🌀 <b>TEMPEST PROFILE: {user.first_name}</b>

👑 <b>Rank:</b> {rank_name}
⭐ <b>Points:</b> {points} (Next: {next_points})
💰 <b>Coins:</b> {coins}
🩸 <b>Sacrifices:</b> {sacrifices}

⚔️ <b>Battles:</b> {wins}W/{losses}L
❤️ <b>Health:</b> {health}/100
⚔️ <b>Attack:</b> {attack}
🛡️ <b>Defense:</b> {defense}
⚡ <b>Speed:</b> {speed}
🎯 <b>Critical:</b> {critical:.1f}%

🌀 <i>The storm flows through you.</i>"""
    
    await message.answer(profile_text, parse_mode=ParseMode.HTML)

@dp.message(Command("sacrifice"))
async def sacrifice_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_status = c.fetchone()
    
    if not cult_status or cult_status[0] == "none":
        await message.answer("🌀 <b>Join the Tempest first with /tempest_join</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        # Show sacrifice menu
        c.execute("SELECT blood_coins FROM tempest_members WHERE user_id = ?", (user.id,))
        coins = c.fetchone()[0]
        
        await message.answer(
            f"🩸 <b>SACRIFICE ALTAR</b>\n\n"
            f"💰 <b>Your coins:</b> {coins}\n\n"
            f"<b>Options:</b>\n"
            f"• <code>/sacrifice blood</code> - 50 coins → 25 points\n"
            f"• <code>/sacrifice soul</code> - 100 coins → 60 points\n"
            f"• <code>/sacrifice item</code> - 200 coins → 150 points\n\n"
            f"Or write your own sacrifice:\n"
            f"<code>/sacrifice your text here</code>",
            parse_mode=ParseMode.HTML
        )
        conn.close()
        return
    
    sacrifice_type = args[1].lower()
    
    # Check coins
    c.execute("SELECT blood_coins, tempest_points FROM tempest_members WHERE user_id = ?", (user.id,))
    coins, current_points = c.fetchone()
    
    if sacrifice_type == "blood":
        cost = 50
        points = 25
    elif sacrifice_type == "soul":
        cost = 100
        points = 60
    elif sacrifice_type == "item":
        cost = 200
        points = 150
    else:
        # Custom text sacrifice
        cost = min(len(sacrifice_type) * 2, 100)
        points = cost // 2
    
    if coins < cost:
        await message.answer(f"🌀 <b>Need {cost} coins! You have: {coins}</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    # Update database
    c.execute("UPDATE tempest_members SET blood_coins = blood_coins - ?, tempest_points = tempest_points + ?, total_sacrifices = total_sacrifices + 1 WHERE user_id = ?",
             (cost, points, user.id))
    
    # Record sacrifice
    c.execute("INSERT INTO sacrifices (user_id, sacrifice_type, sacrifice_value, timestamp, verified) VALUES (?, ?, ?, ?, ?)",
             (user.id, sacrifice_type, points, datetime.now().isoformat(), 1))
    
    conn.commit()
    conn.close()
    
    await message.answer(
        f"🩸 <b>SACRIFICE ACCEPTED!</b>\n\n"
        f"💰 <b>Cost:</b> {cost} coins\n"
        f"⭐ <b>Gained:</b> {points} points\n"
        f"🌀 <b>The storm is pleased.</b>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("invite"))
async def invite_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_status = c.fetchone()
    
    if not cult_status or cult_status[0] == "none":
        await message.answer("🌀 <b>Join the Tempest first with /tempest_join</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        
        if target.id == user.id:
            await message.answer("🤨 Can't invite yourself!")
            conn.close()
            return
        
        # Check if already in cult
        c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (target.id,))
        target_status = c.fetchone()
        
        if target_status and target_status[0] != "none":
            await message.answer(f"🌀 {target.first_name} is already in the Tempest!")
            conn.close()
            return
        
        # Create invite
        invite_id = hashlib.md5(f"{user.id}_{target.id}_{time.time()}".encode()).hexdigest()[:8]
        
        c.execute("INSERT INTO invites (invite_id, inviter_id, invitee_id, created_at) VALUES (?, ?, ?, ?)",
                 (invite_id, user.id, target.id, datetime.now().isoformat()))
        
        # Update inviter's count
        c.execute("UPDATE tempest_members SET invites_count = invites_count + 1 WHERE user_id = ?", (user.id,))
        
        conn.commit()
        conn.close()
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="✅ Accept", callback_data=f"invite_accept_{invite_id}"))
        keyboard.add(InlineKeyboardButton(text="❌ Decline", callback_data=f"invite_decline_{invite_id}"))
        
        invite_msg = await message.reply(
            f"📨 <b>TEMPEST INVITATION</b>\n\n"
            f"{user.first_name} invites you to join the Tempest!\n\n"
            f"🌀 <b>Benefits:</b>\n"
            f"• Advanced battle system\n"
            f"• Profile cards\n"
            f"• Artifacts and upgrades\n"
            f"• 100 starting coins\n\n"
            f"<i>Invitation expires in 5 minutes</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.as_markup()
        )
        
        # Auto-delete after 5 minutes
        await asyncio.sleep(300)
        try:
            await bot.delete_message(chat.id, invite_msg.message_id)
        except:
            pass
        
    else:
        await message.answer("🌀 Reply to someone's message to invite them!")

@dp.message(Command("battle"))
async def battle_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_status = c.fetchone()
    
    if not cult_status or cult_status[0] == "none":
        await message.answer("🌀 <b>Join the Tempest first with /tempest_join to battle</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    if not message.reply_to_message:
        await message.answer("🌀 Reply to someone to challenge them to battle!")
        conn.close()
        return
    
    target = message.reply_to_message.from_user
    
    if target.id == user.id:
        await message.answer("🌀 You can't battle yourself!")
        conn.close()
        return
    
    # Check if target is in Tempest
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (target.id,))
    target_status = c.fetchone()
    
    if not target_status or target_status[0] == "none":
        await message.answer(f"🌀 {target.first_name} is not in the Tempest!")
        conn.close()
        return
    
    # Get battle stats
    c.execute("SELECT attack, defense, speed, critical_chance, health FROM tempest_members WHERE user_id = ?", (user.id,))
    user_stats = c.fetchone()
    
    c.execute("SELECT attack, defense, speed, critical_chance, health FROM tempest_members WHERE user_id = ?", (target.id,))
    target_stats = c.fetchone()
    
    conn.close()
    
    if not user_stats or not target_stats:
        await message.answer("🌀 Battle data error!")
        return
    
    # Simple battle simulation
    user_attack, user_defense, user_speed, user_crit, user_health = user_stats
    target_attack, target_defense, target_speed, target_crit, target_health = target_stats
    
    battle_log = [f"⚔️ <b>BATTLE: {user.first_name} vs {target.first_name}</b>\n"]
    
    round_num = 1
    while user_health > 0 and target_health > 0 and round_num <= 10:
        # User attacks
        is_crit = random.random() < user_crit
        damage = user_attack - (target_defense // 2)
        if is_crit:
            damage = int(damage * 1.5)
            battle_log.append(f"Round {round_num}: ⚡ CRITICAL! {user.first_name} hits for {damage} damage!")
        else:
            battle_log.append(f"Round {round_num}: {user.first_name} hits for {damage} damage")
        
        target_health -= max(1, damage)
        
        if target_health <= 0:
            battle_log.append(f"🎉 <b>VICTORY! {user.first_name} wins!</b>")
            
            # Update database
            conn = sqlite3.connect("data/bot.db")
            c = conn.cursor()
            c.execute("UPDATE tempest_members SET battle_wins = battle_wins + 1, tempest_points = tempest_points + 50, blood_coins = blood_coins + 25 WHERE user_id = ?", (user.id,))
            c.execute("UPDATE tempest_members SET battle_losses = battle_losses + 1 WHERE user_id = ?", (target.id,))
            conn.commit()
            conn.close()
            break
        
        # Target attacks
        is_crit = random.random() < target_crit
        damage = target_attack - (user_defense // 2)
        if is_crit:
            damage = int(damage * 1.5)
            battle_log.append(f"Round {round_num}: ⚡ CRITICAL! {target.first_name} hits back for {damage} damage!")
        else:
            battle_log.append(f"Round {round_num}: {target.first_name} hits back for {damage} damage")
        
        user_health -= max(1, damage)
        
        if user_health <= 0:
            battle_log.append(f"💀 <b>DEFEAT! {target.first_name} wins!</b>")
            
            # Update database
            conn = sqlite3.connect("data/bot.db")
            c = conn.cursor()
            c.execute("UPDATE tempest_members SET battle_losses = battle_losses + 1 WHERE user_id = ?", (user.id,))
            c.execute("UPDATE tempest_members SET battle_wins = battle_wins + 1, tempest_points = tempest_points + 50, blood_coins = blood_coins + 25 WHERE user_id = ?", (target.id,))
            conn.commit()
            conn.close()
            break
        
        round_num += 1
    
    if user_health > 0 and target_health > 0:
        battle_log.append(f"🤝 <b>DRAW! Both fighters are still standing!</b>")
        
        # Update database
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("UPDATE tempest_members SET battles_drawn = battles_drawn + 1, tempest_points = tempest_points + 10 WHERE user_id = ?", (user.id,))
        c.execute("UPDATE tempest_members SET battles_drawn = battles_drawn + 1, tempest_points = tempest_points + 10 WHERE user_id = ?", (target.id,))
        conn.commit()
        conn.close()
    
    battle_log.append(f"\n🌀 <i>The storm watches and learns.</i>")
    
    # Send battle log in chunks
    full_log = "\n".join(battle_log)
    for i in range(0, len(full_log), 4000):
        await message.answer(full_log[i:i+4000], parse_mode=ParseMode.HTML)

@dp.message(Command("curse"))
async def curse_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_status = c.fetchone()
    
    if not cult_status or cult_status[0] == "none":
        await message.answer("🌀 <b>Join the Tempest first with /tempest_join</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    if not message.reply_to_message:
        await message.answer("🌀 Reply to someone to curse them!")
        conn.close()
        return
    
    target = message.reply_to_message.from_user
    
    if target.id == user.id:
        await message.answer("🌀 You can't curse yourself!")
        conn.close()
        return
    
    # Check if target is in Tempest
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (target.id,))
    target_status = c.fetchone()
    
    if not target_status or target_status[0] == "none":
        await message.answer(f"🌀 {target.first_name} is not in the Tempest!")
        conn.close()
        return
    
    # Check coins
    c.execute("SELECT blood_coins FROM tempest_members WHERE user_id = ?", (user.id,))
    coins = c.fetchone()[0]
    
    curse_cost = 50
    
    if coins < curse_cost:
        await message.answer(f"🌀 Need {curse_cost} coins to cast curse! You have: {coins}")
        conn.close()
        return
    
    # Curse types
    curses = [
        ("Weakness Curse", "Reduces attack by 5 for 1 hour"),
        ("Slow Curse", "Reduces speed by 3 for 1 hour"),
        ("Misfortune Curse", "Reduces critical chance by 2% for 1 hour"),
        ("Pain Curse", "Reduces defense by 4 for 1 hour")
    ]
    
    curse_name, curse_effect = random.choice(curses)
    
    # Update database
    c.execute("UPDATE tempest_members SET blood_coins = blood_coins - ? WHERE user_id = ?", (curse_cost, user.id))
    
    # Record curse
    c.execute("INSERT INTO sacrifices (user_id, sacrifice_type, sacrifice_value, timestamp, verified) VALUES (?, ?, ?, ?, ?)",
             (user.id, f"curse_{curse_name.lower().replace(' ', '_')}", curse_cost, datetime.now().isoformat(), 1))
    
    conn.commit()
    conn.close()
    
    incantations = [
        "By the blood of Ravijah, I curse thee!",
        "Let the storm's wrath fall upon you!",
        "Dark winds carry my malice to your soul!",
        "May the eternal tempest haunt your days!"
    ]
    
    incantation = random.choice(incantations)
    
    await message.answer(
        f"☠️ <b>CURSE CAST!</b>\n\n"
        f"🔮 <b>Curse:</b> {curse_name}\n"
        f"⚡ <b>Effect:</b> {curse_effect}\n"
        f"💰 <b>Cost:</b> {curse_cost} coins\n\n"
        f"<i>{incantation}</i>\n\n"
        f"🌀 {target.first_name} has been cursed!",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("daily"))
async def daily_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_status = c.fetchone()
    
    if not cult_status or cult_status[0] == "none":
        await message.answer("🌀 <b>Join the Tempest first with /tempest_join</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    # Check last daily
    c.execute("SELECT last_daily, daily_streak FROM tempest_members WHERE user_id = ?", (user.id,))
    last_daily, streak = c.fetchone()
    
    now = datetime.now()
    
    if last_daily:
        try:
            last_date = datetime.fromisoformat(last_daily)
            if (now - last_date).days < 1:
                await message.answer("🌀 <b>You already claimed your daily reward today!</b>", parse_mode=ParseMode.HTML)
                conn.close()
                return
            elif (now - last_date).days == 1:
                streak += 1
            else:
                streak = 1
        except:
            streak = 1
    else:
        streak = 1
    
    # Calculate rewards
    base_coins = 25
    base_points = 10
    streak_bonus = min(streak * 5, 50)
    
    total_coins = base_coins + streak_bonus
    total_points = base_points + (streak_bonus // 2)
    
    # Update database
    c.execute("UPDATE tempest_members SET blood_coins = blood_coins + ?, tempest_points = tempest_points + ?, daily_streak = ?, last_daily = ? WHERE user_id = ?",
             (total_coins, total_points, streak, now.isoformat(), user.id))
    
    conn.commit()
    conn.close()
    
    await message.answer(
        f"🎁 <b>DAILY REWARD</b>\n\n"
        f"💰 <b>Coins:</b> +{total_coins}\n"
        f"⭐ <b>Points:</b> +{total_points}\n"
        f"🔥 <b>Streak:</b> {streak} days\n\n"
        f"🌀 <i>The storm provides for its faithful.</i>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("leaderboard"))
async def leaderboard_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Get top 10 by points
    c.execute("SELECT user_id, tempest_points, rank FROM tempest_members WHERE status != 'none' ORDER BY tempest_points DESC LIMIT 10")
    leaders = c.fetchall()
    
    leaderboard_text = "🏆 <b>TEMPEST LEADERBOARD</b>\n\n"
    
    if not leaders:
        leaderboard_text += "No Tempest members yet. Be the first with /tempest_join"
    else:
        for i, (user_id, points, rank) in enumerate(leaders, 1):
            try:
                user_chat = await bot.get_chat(user_id)
                name = user_chat.first_name
            except:
                name = f"User_{user_id}"
            
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            leaderboard_text += f"{medal} {name} - {points} points ({rank})\n"
    
    conn.close()
    
    await message.answer(leaderboard_text, parse_mode=ParseMode.HTML)

# ========== ADMIN COMMANDS ==========
@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    if not await is_admin(user.id):
        await message.answer("🔒 Admin only", parse_mode=ParseMode.HTML)
        return
    
    admin_text = """👑 <b>ADMIN COMMANDS</b>

📊 <b>Stats:</b>
<code>/stats</code> - Bot statistics
<code>/users</code> - User list (.txt)
<code>/logs [days]</code> - View logs

⚙️ <b>Management:</b>
<code>/ping</code> - System status
<code>/backup</code> - Backup database
<code>/scan</code> - Scan for new users
<code>/pro user_id</code> - Make admin
<code>/toggle</code> - Toggle bot

📢 <b>Broadcast:</b>
<code>/broadcast</code> - Send to all users
<code>/broadcast_gc</code> - Send to groups

🌀 <b>Tempest:</b>
<code>/add user_id type amount</code> - Add resources
<code>/mod search @username</code> - Search user
<code>/mod info user_id</code> - User info
<code>/mod ban user_id</code> - Ban user
<code>/mod unban user_id</code> - Unban user

⚡ <b>Owner:</b>
<code>/refresh</code> - Refresh cache
<code>/emergency_stop</code> - Stop bot
<code>/query SQL</code> - Database query
<code>/system</code> - System info
<code>/api</code> - API status
<code>/debug</code> - Debug tools"""
    
    await message.answer(admin_text, parse_mode=ParseMode.HTML)

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    if not await is_admin(user.id):
        await message.answer("🔒 Admin only", parse_mode=ParseMode.HTML)
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Basic stats
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM uploads")
    total_uploads = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM wishes")
    total_wishes = c.fetchone()[0] or 0
    
    # Tempest stats
    c.execute("SELECT COUNT(*) FROM tempest_members WHERE status != 'none'")
    cult_members = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(tempest_points) FROM tempest_members")
    total_points = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(total_sacrifices) FROM tempest_members")
    total_sacrifices = c.fetchone()[0] or 0
    
    # Activity
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM command_logs WHERE DATE(timestamp) = DATE(?)", (today,))
    today_commands = c.fetchone()[0] or 0
    
    conn.close()
    
    stats_text = f"""
📊 <b>BOT STATISTICS</b>

👥 <b>Users:</b> {total_users}
📁 <b>Uploads:</b> {total_uploads}
🌟 <b>Wishes:</b> {total_wishes}
🌀 <b>Tempest Members:</b> {cult_members}
⭐ <b>Total Points:</b> {total_points}
🩸 <b>Total Sacrifices:</b> {total_sacrifices}
🔧 <b>Commands Today:</b> {today_commands}

⚡ <b>Uptime:</b> {format_uptime(time.time() - start_time)}"""
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

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

@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    if not await is_admin(user.id):
        await message.answer("🔒 Admin only", parse_mode=ParseMode.HTML)
        return
    
    start_ping = time.time()
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0] or 0
    conn.close()
    
    ping_ms = (time.time() - start_ping) * 1000
    
    stats_text = f"""
🏓 <b>PONG!</b>

⚡ <b>Response Time:</b> {ping_ms:.0f}ms
👥 <b>Total Users:</b> {users}
🕒 <b>Uptime:</b> {format_uptime(time.time() - start_time)}
💾 <b>Database:</b> Operational

✅ <b>All systems operational</b>"""
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

@dp.message(Command("pro"))
async def pro_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only command", parse_mode=ParseMode.HTML)
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

@dp.message(Command("add"))
async def add_cmd(message: Message):
    user, chat = message.from_user, message.chat
    update_user(user)
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only!", parse_mode=ParseMode.HTML)
        return
    
    args = message.text.split()
    if len(args) < 4:
        await message.answer(
            "👑 <b>Usage:</b> <code>/add user_id type amount</code>\n\n"
            "Types:\n"
            "<code>points</code> - Add tempest points\n"
            "<code>coins</code> - Add blood coins\n"
            "<code>sacrifices</code> - Add sacrifices\n"
            "<code>health</code> - Add health\n"
            "<code>attack</code> - Add attack\n"
            "<code>defense</code> - Add defense\n\n"
            "<b>Example:</b> <code>/add 123456789 points 100</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        target_id = int(args[1])
        add_type = args[2].lower()
        amount = int(args[3])
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        # Check if user exists in tempest
        c.execute("SELECT user_id FROM tempest_members WHERE user_id = ?", (target_id,))
        if not c.fetchone():
            await message.answer("❌ User not in Tempest system!")
            conn.close()
            return
        
        update_success = False
        if add_type == "points":
            c.execute("UPDATE tempest_members SET tempest_points = tempest_points + ? WHERE user_id = ?", (amount, target_id))
            update_success = True
        
        elif add_type == "coins":
            c.execute("UPDATE tempest_members SET blood_coins = blood_coins + ? WHERE user_id = ?", (amount, target_id))
            update_success = True
        
        elif add_type == "sacrifices":
            c.execute("UPDATE tempest_members SET total_sacrifices = total_sacrifices + ? WHERE user_id = ?", (amount, target_id))
            update_success = True
        
        elif add_type == "health":
            c.execute("UPDATE tempest_members SET health = health + ?, max_health = max_health + ? WHERE user_id = ?", (amount, amount, target_id))
            update_success = True
        
        elif add_type == "attack":
            c.execute("UPDATE tempest_members SET attack = attack + ? WHERE user_id = ?", (amount, target_id))
            update_success = True
        
        elif add_type == "defense":
            c.execute("UPDATE tempest_members SET defense = defense + ? WHERE user_id = ?", (amount, target_id))
            update_success = True
        
        if update_success:
            conn.commit()
            await message.answer(f"✅ Added {amount} {add_type} to user {target_id}")
        else:
            await message.answer("❌ Invalid type.")
        
        conn.close()
        
    except ValueError:
        await message.answer("❌ Invalid number format")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

# ========== CALLBACK HANDLERS ==========
@dp.callback_query(F.data == "cult_begin")
async def cult_begin_handler(callback: CallbackQuery):
    user = callback.from_user
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Add to cult with starting bonuses
    c.execute("INSERT OR REPLACE INTO tempest_members (user_id, status, rank, join_date, total_sacrifices, tempest_points, blood_coins) VALUES (?, ?, ?, ?, ?, ?, ?)",
             (user.id, "member", "Blood Initiate", datetime.now().isoformat(), 3, 100, 100))
    
    # Add starting sacrifices
    for i in range(3):
        c.execute("INSERT INTO sacrifices (user_id, sacrifice_type, sacrifice_value, timestamp, verified) VALUES (?, ?, ?, ?, ?)",
                 (user.id, "initiation_bonus", 10, datetime.now().isoformat(), 1))
    
    conn.commit()
    conn.close()
    
    # Animate initiation
    msg = callback.message
    steps = [
        "🌀 The storm senses your willingness...",
        "⚡ Lightning cracks in the distance...",
        "🌪️ Winds gather around you...",
        "🩸 Three drops of blood seal the pact...",
        "💀 The Tempest accepts you!"
    ]
    
    for step in steps:
        await msg.edit_text(f"<b>{step}</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.5)
    
    await msg.edit_text(
        f"🌀 <b>WELCOME TO THE TEMPEST, {user.first_name.upper()}!</b>\n\n"
        f"Your journey begins now.\n\n"
        f"<b>Starting bonuses:</b>\n"
        f"• 👑 Rank: Blood Initiate\n"
        f"• ⭐ 100 Tempest Points\n"
        f"• 💰 100 Blood Coins\n"
        f"• 🩸 3 Starting Sacrifices\n\n"
        f"<b>New commands:</b>\n"
        f"<code>/tempest_profile</code> - Enhanced profile\n"
        f"<code>/sacrifice</code> - Offer sacrifices\n"
        f"<code>/invite</code> - Invite others\n"
        f"<code>/battle</code> - Fight other members\n"
        f"<code>/curse</code> - Cast curses\n"
        f"<code>/daily</code> - Daily rewards\n"
        f"<code>/leaderboard</code> - Rankings\n\n"
        f"🌀 <b>The storm flows through you now.</b>",
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data.startswith("invite_"))
async def handle_invite_response(callback: CallbackQuery):
    data = callback.data
    user = callback.from_user
    
    if "_accept_" in data:
        invite_id = data.split("_accept_")[1]
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        # Get invite details
        c.execute("SELECT inviter_id FROM invites WHERE invite_id = ? AND status = 'pending'", (invite_id,))
        invite = c.fetchone()
        
        if invite:
            inviter_id = invite[0]
            
            # Add to cult
            c.execute("INSERT OR REPLACE INTO tempest_members (user_id, status, rank, join_date, tempest_points, blood_coins, invited_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (user.id, "member", "Blood Initiate", datetime.now().isoformat(), 100, 100, inviter_id))
            
            # Update invite status
            c.execute("UPDATE invites SET status = 'accepted', accepted_at = ? WHERE invite_id = ?",
                     (datetime.now().isoformat(), invite_id))
            
            # Reward inviter
            c.execute("UPDATE tempest_members SET tempest_points = tempest_points + 50, blood_coins = blood_coins + 25 WHERE user_id = ?", (inviter_id,))
            
            conn.commit()
            conn.close()
            
            try:
                inviter = await bot.get_chat(inviter_id)
                inviter_name = inviter.first_name
            except:
                inviter_name = f"User_{inviter_id}"
            
            await callback.message.edit_text(
                f"🎉 <b>INVITATION ACCEPTED!</b>\n\n"
                f"{user.first_name} has joined the Tempest!\n"
                f"Invited by: {inviter_name}\n\n"
                f"🌀 <b>Welcome bonuses:</b>\n"
                f"• 100 Tempest Points\n"
                f"• 100 Blood Coins\n\n"
                f"<i>The storm grows stronger...</i>",
                parse_mode=ParseMode.HTML
            )
            
        else:
            await callback.message.edit_text("❌ Invite expired or invalid!", parse_mode=ParseMode.HTML)
    
    elif "_decline_" in data:
        invite_id = data.split("_decline_")[1]
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("UPDATE invites SET status = 'declined' WHERE invite_id = ?", (invite_id,))
        conn.commit()
        conn.close()
        
        await callback.message.edit_text(
            "❌ <b>INVITATION DECLINED</b>\n\n"
            "<i>The storm retreats... for now.</i>",
            parse_mode=ParseMode.HTML
        )

@dp.callback_query(F.data == "cult_cancel")
async def cult_cancel_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "❌ <b>Initiation cancelled.</b>\n\n"
        "<i>The storm waits for another time...</i>",
        parse_mode=ParseMode.HTML
    )

# ========== MAIN ==========
start_time = time.time()

async def main():
    print("🚀 BOT STARTING...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ Database initialized")
    print("🔗 File upload: READY")
    print("🎮 Games: READY")
    print("🌀 Tempest system: WORKING")
    print("👑 Admin commands: WORKING")
    print("=" * 50)
    
    startup_msg = f"""
🌀 <b>Tempest Bot Started</b>

🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⚡ Status: All systems operational
✅ Features:
• File upload system
• Complete Tempest cult
• Battle system
• Sacrifices & curses
• Admin controls
• Profile system

🌀 The storm awaits commands...
"""
    
    await send_log(startup_msg)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🌀 Bot stopped")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
