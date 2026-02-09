#!/usr/bin/env python3
# ========== NORMAL CATBOX UPLOADER BOT ==========
print("=" * 60)
print("📁 CatBox Uploader Bot v2.0")
print("🔗 Fast file uploads | 🎮 Simple games")
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
import html
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from io import BytesIO

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile
from aiogram.enums import ParseMode, ChatType, DiceEmoji
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

print("🤖 CatBox Uploader Bot Starting...")

# ========== CONFIGURATION ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"

# Create directories
Path("data").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== SIMPLE DATABASE (No cult visible) ==========
def init_db():
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Normal user table
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
    
    # Hidden cult table (not in help)
    c.execute('''CREATE TABLE IF NOT EXISTS tempest_members (
        user_id INTEGER PRIMARY KEY,
        status TEXT DEFAULT 'none',
        rank TEXT DEFAULT 'Mortal',
        join_date TEXT,
        sacrifices INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        coins INTEGER DEFAULT 100,
        battle_wins INTEGER DEFAULT 0,
        battle_losses INTEGER DEFAULT 0,
        health INTEGER DEFAULT 100,
        attack INTEGER DEFAULT 10,
        defense INTEGER DEFAULT 8,
        speed INTEGER DEFAULT 12,
        critical_chance REAL DEFAULT 0.05
    )''')
    
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== HELPER FUNCTIONS ==========
def safe_answer_callback(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    try:
        return callback.answer(text, show_alert=show_alert)
    except:
        pass

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

# ========== PUBLIC COMMANDS (Normal bot functions) ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    await message.answer(
        f"✨ <b>Hey {user.first_name}!</b>\n\n"
        "🤖 <b>CatBox Uploader Bot</b>\n\n"
        "🔗 Upload files & get direct links\n"
        "✨ Simple games for fun\n\n"
        "📁 <b>Upload:</b> Send <code>/link</code> then any file\n"
        "🎮 <b>Games:</b> <code>/dice</code> <code>/flip</code>\n"
        "👤 <b>Profile:</b> <code>/profile</code>\n"
        "📚 <b>Help:</b> <code>/help</code>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    help_text = """📚 <b>ALL COMMANDS</b>

🔗 <b>Upload:</b>
<code>/link</code> - Upload file (send file after)

🎮 <b>Games:</b>
<code>/dice</code> - Roll dice
<code>/flip</code> - Flip coin

👤 <b>User:</b>
<code>/profile</code> - Your stats
<code>/start</code> - Welcome

⚡ <b>Admin:</b>
<code>/stats</code> - Statistics
<code>/users</code> - User list
<code>/backup</code> - Backup database

<i>Simple, fast, and reliable!</i>"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Get normal stats
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
    
    # Check if in cult (hidden check)
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_status = c.fetchone()
    
    conn.close()
    
    # Normal profile text
    profile_text = f"""
👤 <b>PROFILE: {user.first_name}</b>

📁 <b>Uploads:</b> {uploads}
🔧 <b>Commands:</b> {cmds}
📅 <b>Joined:</b> {join_date}
🆔 <b>ID:</b> <code>{user.id}</code>

💡 <b>Try:</b> /link to upload files
🎮 <b>Play:</b> /dice or /flip for fun
"""
    
    # Hidden cult indicator (only visible to members)
    if cult_status and cult_status[0] != 'none':
        profile_text += "\n🌀 <i>Tempest flows in your veins...</i>"
    
    await message.answer(profile_text, parse_mode=ParseMode.HTML)

@dp.message(Command("link"))
async def link_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 <b>Upload files in private chat only</b>", parse_mode=ParseMode.HTML)
        return
    
    # Store waiting state
    if not hasattr(link_cmd, 'waiting'):
        link_cmd.waiting = {}
    link_cmd.waiting[user.id] = True
    
    await message.answer(
        "📁 <b>Now send me any file:</b>\n"
        "• Photo, video, document\n"
        "• Audio, voice, sticker\n"
        "• Max 200MB\n\n"
        "❌ <code>/cancel</code> to stop",
        parse_mode=ParseMode.HTML
    )

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation)
async def handle_file(message: Message):
    user = message.from_user
    
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
    # Check if waiting for upload
    if not hasattr(link_cmd, 'waiting') or user.id not in link_cmd.waiting or not link_cmd.waiting[user.id]:
        return
    
    link_cmd.waiting[user.id] = False
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
        
        await msg.edit_text("☁️ <b>Uploading to CatBox...</b>", parse_mode=ParseMode.HTML)
        filename = file.file_path.split('/')[-1] if '/' in file.file_path else f"file_{file_id}"
        result = await upload_to_catbox(file_data, filename)
        
        if not result['success']:
            await msg.edit_text("❌ Upload failed")
            return
        
        # Update database
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,))
        
        # Hidden cult bonus
        c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
        cult_status = c.fetchone()
        if cult_status and cult_status[0] != 'none':
            c.execute("UPDATE tempest_members SET sacrifices = sacrifices + 1, points = points + 10 WHERE user_id = ?", (user.id,))
        
        conn.commit()
        conn.close()
        
        # Format size
        size_kb = file_size / 1024
        size_mb = size_kb / 1024
        size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
        
        # Create buttons
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="📋 Copy Link", callback_data=f"copy_{result['url']}"))
        keyboard.add(InlineKeyboardButton(text="🔗 Share", url=f"https://t.me/share/url?url={result['url']}"))
        
        result_text = f"""✅ <b>Upload Complete!</b>

📁 <b>Type:</b> {file_type}
💾 <b>Size:</b> {size_text}
👤 <b>By:</b> {user.first_name}

🔗 <b>Direct Link:</b>
<code>{result['url']}</code>

📤 Permanent link • No expiry"""
        
        await msg.edit_text(result_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
        
    except Exception as e:
        await msg.edit_text("❌ Error uploading file")
        print(f"Upload error: {e}")

@dp.callback_query(F.data.startswith("copy_"))
async def handle_copy(callback: CallbackQuery):
    url = callback.data[5:]
    await safe_answer_callback(callback, f"Link copied!\n{url}", show_alert=True)

@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    # Send Telegram dice
    dice_msg = await message.answer_dice(emoji="🎲")
    await asyncio.sleep(3)
    
    dice_value = dice_msg.dice.value
    dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    
    await message.answer(
        f"🎲 <b>You rolled: {dice_faces[dice_value-1]} ({dice_value})</b>\n"
        f"🎮 <i>Via Telegram Games</i>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    # Send dice for coin flip
    dice_msg = await message.answer_dice(emoji="🎰")
    await asyncio.sleep(3)
    
    dice_value = dice_msg.dice.value
    result = "HEADS 🟡" if dice_value in [1, 3, 5] else "TAILS 🟤"
    
    await message.answer(
        f"🪙 <b>{result}</b>\n"
        f"🎰 <i>Dice value: {dice_value}</i>",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    if hasattr(link_cmd, 'waiting') and user.id in link_cmd.waiting:
        link_cmd.waiting[user.id] = False
        await message.answer("❌ Upload cancelled")
    
    await message.answer("✅ Operation cancelled")

# ========== HIDDEN CULT COMMANDS (Not in help) ==========
@dp.message(Command("tempest_join"))
async def tempest_join_cmd(message: Message):
    """Hidden cult join command"""
    user = message.from_user
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        await message.answer("🌀 <b>Already initiated.</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    conn.close()
    
    # Start initiation
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🩸 Begin", callback_data="cult_begin"))
    keyboard.add(InlineKeyboardButton(text="❌ Cancel", callback_data="cult_cancel"))
    
    await message.answer(
        "🌀 <b>You found a hidden path...</b>\n\n"
        "A whisper in the static. A crackle in the silence.\n"
        "The storm calls to those who listen.\n\n"
        "<i>This is not in the help menu.\n"
        "This is not for everyone.\n"
        "This is a choice that changes everything.</i>\n\n"
        "Will you answer?",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.as_markup()
    )

@dp.message(Command("tempest_profile"))
async def tempest_profile_cmd(message: Message):
    """Hidden enhanced profile"""
    user = message.from_user
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_data = c.fetchone()
    
    if not cult_data or cult_data[1] == "none":
        await message.answer("🌀 <b>You are not initiated.</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    # Get user profile pic
    profile_pics = await bot.get_user_profile_photos(user.id, limit=1)
    profile_pic_url = None
    if profile_pics.photos:
        file = await bot.get_file(profile_pics.photos[0][-1].file_id)
        profile_pic_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    
    # Prepare data for profile generator
    user_data = {
        'id': user.id,
        'name': user.first_name,
        'title': "Tempest Member"
    }
    
    cult_info = {
        'rank': cult_data[2],
        'points': cult_data[5],
        'coins': cult_data[6],
        'battle_wins': cult_data[7],
        'battle_losses': cult_data[8],
        'sacrifices': cult_data[4],
        'health': cult_data[9],
        'attack': cult_data[10],
        'defense': cult_data[11],
        'speed': cult_data[12],
        'critical': cult_data[13]
    }
    
    conn.close()
    
    # Generate profile using story.py
    try:
        import story
        profile_image = await story.generate_tempest_profile(user_data, cult_info, profile_pic_url)
        
        if profile_image:
            await message.answer_photo(
                photo=BufferedInputFile(profile_image, filename="tempest_profile.png"),
                caption=f"🌀 <b>Tempest Profile: {user.first_name}</b>\n"
                       f"👑 Rank: {cult_info['rank']}\n"
                       f"⭐ Points: {cult_info['points']}\n"
                       f"🩸 Sacrifices: {cult_info['sacrifices']}",
                parse_mode=ParseMode.HTML
            )
        else:
            # Fallback text profile
            profile_text = f"""
🌀 <b>TEMPEST PROFILE</b>

👤 <b>{user.first_name}</b>
👑 <b>Rank:</b> {cult_info['rank']}
⭐ <b>Points:</b> {cult_info['points']}
💰 <b>Coins:</b> {cult_info['coins']}

⚔️ <b>Battles:</b> {cult_info['battle_wins']}W/{cult_info['battle_losses']}L
🩸 <b>Sacrifices:</b> {cult_info['sacrifices']}

❤️ <b>Health:</b> {cult_info['health']}/100
⚔️ <b>Attack:</b> {cult_info['attack']}
🛡️ <b>Defense:</b> {cult_info['defense']}
⚡ <b>Speed:</b> {cult_info['speed']}
🎯 <b>Critical:</b> {cult_info['critical']*100:.1f}%

🌀 <i>The storm flows through you.</i>
"""
            await message.answer(profile_text, parse_mode=ParseMode.HTML)
    except ImportError:
        await message.answer("🌀 Profile generator unavailable.", parse_mode=ParseMode.HTML)

@dp.message(Command("battle"))
async def battle_cmd(message: Message):
    """Hidden battle command"""
    user = message.from_user
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT status FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_status = c.fetchone()
    
    if not cult_status or cult_status[0] == "none":
        await message.answer("🌀 <b>Initiate first with /tempest_join</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        
        if target.id == user.id:
            await message.answer("🤨 Can't battle yourself!")
            conn.close()
            return
        
        # Start battle
        battle_id = int(time.time())
        
        c.execute("SELECT * FROM tempest_members WHERE user_id = ?", (user.id,))
        player1 = c.fetchone()
        
        c.execute("SELECT * FROM tempest_members WHERE user_id = ?", (target.id,))
        player2 = c.fetchone()
        
        if not player2 or player2[1] == "none":
            await message.answer("🌀 Target not initiated!")
            conn.close()
            return
        
        # Create battle
        keyboard = InlineKeyboardBuilder()
        abilities = ["⚔️ Slash", "🛡️ Block", "❤️ Heal", "🔥 Fire", "❄️ Ice", "⚡ Shock"]
        for ability in abilities:
            keyboard.add(InlineKeyboardButton(text=ability, callback_data=f"battle_{battle_id}_{ability}"))
        keyboard.adjust(3, 3)
        
        battle_text = f"""
⚔️ <b>TEMPEST BATTLE</b>

<b>{user.first_name}</b> vs <b>{target.first_name}</b>

❤️ HP: 100 | 100
⚔️ ATK: {player1[10]} | {player2[10]}
🛡️ DEF: {player1[11]} | {player2[11]}
⚡ SPD: {player1[12]} | {player2[12]}

<i>Choose your move!</i>
"""
        
        battle_msg = await message.reply(battle_text, parse_mode=ParseMode.HTML, reply_markup=keyboard.as_markup())
        
        # Store battle
        if not hasattr(battle_cmd, 'battles'):
            battle_cmd.battles = {}
        
        battle_cmd.battles[battle_id] = {
            'player1': user.id,
            'player2': target.id,
            'hp1': 100,
            'hp2': 100,
            'turn': user.id,
            'message_id': battle_msg.message_id,
            'chat_id': message.chat.id
        }
    
    else:
        await message.answer("🌀 Reply to someone to battle!")
    
    conn.close()

@dp.callback_query(F.data.startswith("battle_"))
async def handle_battle_action(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    if len(data_parts) < 3:
        return
    
    battle_id = int(data_parts[1])
    ability = "_".join(data_parts[2:])
    
    if not hasattr(battle_cmd, 'battles') or battle_id not in battle_cmd.battles:
        await safe_answer_callback(callback, "Battle expired!")
        return
    
    battle = battle_cmd.battles[battle_id]
    user = callback.from_user
    
    # Check turn
    if user.id != battle['turn']:
        await safe_answer_callback(callback, "Not your turn!")
        return
    
    # Calculate damage
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    if user.id == battle['player1']:
        c.execute("SELECT attack, defense, speed, critical_chance FROM tempest_members WHERE user_id = ?", (user.id,))
        attacker_stats = c.fetchone()
        target_id = battle['player2']
    else:
        c.execute("SELECT attack, defense, speed, critical_chance FROM tempest_members WHERE user_id = ?", (user.id,))
        attacker_stats = c.fetchone()
        target_id = battle['player1']
    
    # Base damage
    base_damage = attacker_stats[0]
    
    # Ability modifiers
    if ability == "⚔️ Slash":
        damage = base_damage + random.randint(5, 15)
        effect = "slashes"
    elif ability == "🛡️ Block":
        damage = 0
        effect = "blocks"
        # Heal instead
        if user.id == battle['player1']:
            battle['hp1'] = min(100, battle['hp1'] + 20)
        else:
            battle['hp2'] = min(100, battle['hp2'] + 20)
    elif ability == "❤️ Heal":
        damage = 0
        effect = "heals"
        if user.id == battle['player1']:
            battle['hp1'] = min(100, battle['hp1'] + 30)
        else:
            battle['hp2'] = min(100, battle['hp2'] + 30)
    elif ability == "🔥 Fire":
        damage = base_damage + random.randint(10, 20)
        effect = "burns with fire"
    elif ability == "❄️ Ice":
        damage = base_damage + random.randint(8, 18)
        effect = "freezes"
    elif ability == "⚡ Shock":
        damage = base_damage + random.randint(12, 22)
        effect = "shocks with lightning"
    else:
        damage = base_damage
        effect = "attacks"
    
    # Critical hit
    is_critical = random.random() < attacker_stats[3]
    if is_critical:
        damage = int(damage * 1.5)
        effect = f"CRITICALLY {effect.lower()}"
    
    # Apply damage
    if damage > 0:
        if user.id == battle['player1']:
            battle['hp2'] = max(0, battle['hp2'] - damage)
        else:
            battle['hp1'] = max(0, battle['hp1'] - damage)
    
    # Switch turn
    battle['turn'] = battle['player2'] if user.id == battle['player1'] else battle['player1']
    
    # Check winner
    winner = None
    if battle['hp1'] <= 0:
        winner = battle['player2']
    elif battle['hp2'] <= 0:
        winner = battle['player1']
    
    # Update message
    if winner:
        # Battle over
        winner_user = await bot.get_chat(winner)
        loser = battle['player1'] if winner == battle['player2'] else battle['player2']
        
        # Update stats
        c.execute("UPDATE tempest_members SET battle_wins = battle_wins + 1, points = points + 50 WHERE user_id = ?", (winner,))
        c.execute("UPDATE tempest_members SET battle_losses = battle_losses + 1 WHERE user_id = ?", (loser,))
        conn.commit()
        
        final_text = f"""
🏆 <b>BATTLE ENDED</b>

<b>{winner_user.first_name} WINS!</b>

{callback.from_user.first_name} {effect} for {damage} damage{" (CRITICAL!)" if is_critical else ""}

Final HP:
{await bot.get_chat(battle['player1']).first_name}: {max(0, battle['hp1'])}
{await bot.get_chat(battle['player2']).first_name}: {max(0, battle['hp2'])}

Winner: +50 points
"""
        
        await callback.message.edit_text(final_text, parse_mode=ParseMode.HTML)
        del battle_cmd.battles[battle_id]
        
    else:
        # Continue battle
        battle_text = f"""
⚔️ <b>TEMPEST BATTLE</b>

{callback.from_user.first_name} {effect} for {damage} damage{" (CRITICAL!)" if is_critical else ""}

<b>{await bot.get_chat(battle['player1']).first_name}</b> vs <b>{await bot.get_chat(battle['player2']).first_name}</b>

❤️ HP: {battle['hp1']} | {battle['hp2']}
🎯 Turn: {'You' if battle['turn'] == callback.from_user.id else 'Opponent'}

<i>Choose your move!</i>
"""
        
        await callback.message.edit_text(battle_text, parse_mode=ParseMode.HTML)
    
    conn.close()
    await safe_answer_callback(callback)

@dp.message(Command("curse"))
async def curse_cmd(message: Message):
    """Hidden curse command"""
    user = message.from_user
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT status, coins FROM tempest_members WHERE user_id = ?", (user.id,))
    cult_data = c.fetchone()
    
    if not cult_data or cult_data[0] == "none":
        await message.answer("🌀 <b>Initiate first with /tempest_join</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    if cult_data[1] < 50:
        await message.answer(f"🌀 <b>Need 50 coins to curse! You have: {cult_data[1]}</b>", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        
        if target.id == user.id:
            await message.answer("🤨 Can't curse yourself!")
            conn.close()
            return
        
        # Animate curse
        msg = await message.reply("🕯️ <b>Gathering dark energy...</b>", parse_mode=ParseMode.HTML)
        
        curses = ["Weakness", "Misfortune", "Sleep", "Pain", "Confusion"]
        curse_type = random.choice(curses)
        
        for step in ["🌀", "☠️", "💀", "🔥", "⚡"]:
            await msg.edit_text(f"{step} <b>Casting {curse_type} curse...</b>", parse_mode=ParseMode.HTML)
            await asyncio.sleep(1)
        
        # Apply curse
        c.execute("UPDATE tempest_members SET coins = coins - 50 WHERE user_id = ?", (user.id,))
        conn.commit()
        
        await msg.edit_text(
            f"☠️ <b>CURSE SUCCESSFUL!</b>\n\n"
            f"Cursed: {target.first_name}\n"
            f"Type: {curse_type}\n"
            f"Cost: 50 coins\n\n"
            f"<i>The storm remembers this act...</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer("🌀 Reply to someone to curse!")
    
    conn.close()

@dp.message(Command("add"))
async def add_cmd(message: Message):
    """Owner command: Add/remove sacrifices"""
    user = message.from_user
    update_user(user)
    
    if user.id != OWNER_ID:
        await message.answer("👑 Owner only!")
        return
    
    args = message.text.split()
    if len(args) < 4:
        await message.answer("👑 <b>Usage:</b> <code>/add user_id sacrifices amount</code>\n<code>/add 123456789 sacrifices 50</code>", parse_mode=ParseMode.HTML)
        return
    
    try:
        target_id = int(args[1])
        action = args[2].lower()
        amount = int(args[3])
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        if action == "sacrifices":
            c.execute("UPDATE tempest_members SET sacrifices = sacrifices + ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            
            target_user = await bot.get_chat(target_id)
            await message.answer(f"✅ Added {amount} sacrifices to {target_user.first_name}")
            
            # Log
            await bot.send_message(
                LOG_CHANNEL_ID if 'LOG_CHANNEL_ID' in globals() else OWNER_ID,
                f"👑 <b>Owner Action</b>\n\n"
                f"Action: Add sacrifices\n"
                f"Target: {target_user.first_name}\n"
                f"Amount: {amount}\n"
                f"By: {user.first_name}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode=ParseMode.HTML
            )
        
        elif action == "points":
            c.execute("UPDATE tempest_members SET points = points + ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            await message.answer(f"✅ Added {amount} points")
        
        elif action == "coins":
            c.execute("UPDATE tempest_members SET coins = coins + ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            await message.answer(f"✅ Added {amount} coins")
        
        else:
            await message.answer("❌ Invalid action. Use: sacrifices, points, coins")
        
        conn.close()
        
    except ValueError:
        await message.answer("❌ Invalid number format")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")

# ========== ADMIN COMMANDS ==========
@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    if not await is_admin(user.id):
        await message.answer("🔒 Admin only")
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM users WHERE DATE(last_active) = DATE('now')")
    active_today = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM tempest_members WHERE status != 'none'")
    cult_members = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(uploads) FROM users")
    total_uploads = c.fetchone()[0] or 0
    
    conn.close()
    
    stats_text = f"""
📊 <b>BOT STATISTICS</b>

👥 <b>Users:</b> {total_users}
📈 <b>Active Today:</b> {active_today}
📁 <b>Total Uploads:</b> {total_uploads}
🌀 <b>Tempest Members:</b> {cult_members}

<i>Simple and reliable!</i>
"""
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

@dp.message(Command("users"))
async def users_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    if not await is_admin(user.id):
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, uploads, last_active FROM users ORDER BY joined_date DESC LIMIT 50")
    users = c.fetchall()
    conn.close()
    
    user_list = "👥 USER LIST (Last 50)\n" + "="*50 + "\n\n"
    for uid, name, uname, up, last_active in users:
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
        
        user_list += f"🆔 {uid}\n👤 {name}\n📧 {un}\n📁 {up}\n🕒 {activity}\n" + "-"*40 + "\n"
    
    filename = f"temp/users_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(user_list)
    
    await message.answer_document(
        FSInputFile(filename),
        caption="📁 User list"
    )
    
    try:
        os.remove(filename)
    except:
        pass

@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    user = message.from_user
    update_user(user)
    
    if not await is_admin(user.id):
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/backup_{timestamp}.db"
    
    try:
        shutil.copy2("data/bot.db", backup_file)
        await message.answer_document(
            FSInputFile(backup_file),
            caption=f"💾 Backup {timestamp}"
        )
    except Exception as e:
        await message.answer(f"❌ Backup failed: {e}")

# ========== CALLBACK HANDLERS ==========
@dp.callback_query(F.data == "cult_begin")
async def cult_begin_handler(callback: CallbackQuery):
    user = callback.from_user
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Add to cult
    c.execute("INSERT OR REPLACE INTO tempest_members (user_id, status, rank, join_date, points, coins) VALUES (?, ?, ?, ?, ?, ?)",
             (user.id, "member", "Blood Initiate", datetime.now().isoformat(), 100, 100))
    conn.commit()
    conn.close()
    
    # Animate initiation
    msg = callback.message
    steps = [
        "🌀 The storm senses your willingness...",
        "⚡ Lightning cracks in the distance...",
        "🌪️ Winds gather around you...",
        "🩸 A drop of blood seals the pact...",
        "👁️ Ancient eyes open in the shadows...",
        "💀 The Tempest accepts you!"
    ]
    
    for step in steps:
        await msg.edit_text(f"<b>{step}</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)
    
    await msg.edit_text(
        f"🌀 <b>WELCOME TO THE TEMPEST, {user.first_name.upper()}!</b>\n\n"
        f"Your journey begins now.\n"
        f"You have been granted:\n"
        f"• 👑 Rank: Blood Initiate\n"
        f"• ⭐ 100 Tempest Points\n"
        f"• 💰 100 Blood Coins\n\n"
        f"<i>Hidden commands unlocked:\n"
        f"/tempest_profile - Enhanced profile\n"
        f"/battle - Fight other members\n"
        f"/curse - Cast curses (costs coins)</i>\n\n"
        f"🌀 <b>The storm flows through you now.</b>",
        parse_mode=ParseMode.HTML
    )
    
    await safe_answer_callback(callback, "🌀 Initiation complete!")

@dp.callback_query(F.data == "cult_cancel")
async def cult_cancel_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌀 <b>The storm retreats...</b>\n\n"
        "<i>The path closes behind you.\n"
        "The whispers fade.\n"
        "You remain in the world of light.</i>",
        parse_mode=ParseMode.HTML
    )
    await safe_answer_callback(callback)

# ========== MAIN ==========
async def main():
    print("🚀 CatBox Uploader Bot Starting...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ Database initialized")
    print("🔗 Upload system: READY")
    print("🎮 Games: READY")
    print("🌀 Hidden cult: ACTIVE")
    print("=" * 50)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🤖 Bot stopped gracefully")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
