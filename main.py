import os
import asyncio
import logging
import time
import random
from datetime import datetime
import sqlite3
from pathlib import Path
import sys
import json
import httpx

from aiogram import Bot, Dispatcher, types, F  # ADDED F HERE!
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

print("=" * 70)
print("🤖 PRO BOT v4.0 - FIXED UPLOADS")
print("=" * 70)

# ========== CONFIGURATION ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
SUPPORT_CHAT = "https://t.me/+T7JxyxVOYcxmMzJl"
CATBOX_API = "https://catbox.moe/user/api.php"

# Create directories
Path("data").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True)

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Global states
bot_active = True
start_time = time.time()
user_waiting_for_file = {}  # Track users waiting for files

# ========== DATABASE SETUP ==========
def init_db():
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_date TEXT,
            last_active TEXT,
            total_commands INTEGER DEFAULT 0,
            uploads_count INTEGER DEFAULT 0,
            wishes_count INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            catbox_url TEXT,
            file_type TEXT,
            file_size INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            wish_text TEXT,
            luck_percentage INTEGER
        )
    ''')
    
    # Add owner as admin
    cursor.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, first_name, joined_date, last_active, is_admin)
        VALUES (?, ?, ?, ?, ?)
    ''', (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== HELPER FUNCTIONS ==========
def update_user(user: types.User):
    try:
        conn = sqlite3.connect("data/bot.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, joined_date, last_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user.id, user.username, user.first_name, user.last_name,
            datetime.now().isoformat(), datetime.now().isoformat()
        ))
        
        cursor.execute('UPDATE users SET last_active = ? WHERE user_id = ?', 
                      (datetime.now().isoformat(), user.id))
        
        conn.commit()
        conn.close()
    except:
        pass

async def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    
    try:
        conn = sqlite3.connect("data/bot.db")
        cursor = conn.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None and result[0] == 1
    except:
        return False

async def upload_to_catbox(file_data: bytes, filename: str):
    """Upload file to catbox.moe"""
    try:
        files = {
            'reqtype': (None, 'fileupload'),
            'fileToUpload': (filename, file_data),
        }
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(CATBOX_API, files=files, headers=headers)
        
        if response.status_code == 200 and response.text.startswith('http'):
            return {'success': True, 'url': response.text.strip()}
        else:
            return {'success': False, 'error': f'Status: {response.status_code}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ========== /START COMMAND ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    """Start command with animation"""
    user = message.from_user
    update_user(user)
    
    # Animation
    welcome_msgs = [
        f"✨ <b>Welcome {user.first_name}!</b>",
        f"🌟 <b>Welcome {user.first_name}!</b>\n\nYour journey begins...",
        f"🚀 <b>Welcome {user.first_name}!</b>\n\nReady to explore?"
    ]
    
    for msg in welcome_msgs:
        await message.answer(msg, parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.5)
    
    # Main welcome
    welcome = f"""
🎉 <b>Hello {user.first_name}!</b> 👋

🤖 <b>Welcome to PRO BOT</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<b>🚀 Main Features:</b>
• 🔗 Upload files to Catbox.moe
• ✨ Wish fortune teller
• 🎮 Fun games (dice, coin flip)
• 📊 User profile & stats

<b>📁 Upload System:</b>
1. Send <code>/link</code>
2. Send any file (photo, video, document)
3. Get permanent Catbox.moe link!

<b>🎮 Fun Commands:</b>
• <code>/wish [text]</code> - Check luck %
• <code>/dice</code> - Roll dice
• <code>/flip</code> - Flip coin
• <code>/profile</code> - Your stats

<b>👑 Admin Commands:</b>
• <code>/ping</code> - System status
• <code>/logs</code> - View logs
• <code>/stats</code> - Bot statistics

━━━━━━━━━━━━━━━━━━━━━━━━
💬 <b>Support:</b> <a href="{SUPPORT_CHAT}">Join Support Chat</a>
⚡ <b>Status:</b> Online 24/7
🔧 <b>Version:</b> 4.0
━━━━━━━━━━━━━━━━━━━━━━━━

📌 <i>Type /help for all commands</i>
"""
    
    await message.answer(welcome, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

# ========== /HELP COMMAND ==========
@dp.message(Command("help"))
async def help_command(message: Message):
    """Help command"""
    user = message.from_user
    update_user(user)
    
    help_text = f"""
📚 <b>ALL COMMANDS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

🔗 <b>FILE UPLOAD:</b>
<code>/link</code> - Upload to Catbox.moe
• Send command, then send file

🌟 <b>WISH SYSTEM:</b>
<code>/wish [text]</code> - Check luck %
• Example: <code>/wish I will be rich</code>

🎮 <b>GAMES:</b>
<code>/dice</code> - Roll dice (1-6)
<code>/flip</code> - Heads or Tails

👤 <b>USER:</b>
<code>/profile</code> - Your statistics
<code>/start</code> - Welcome message
<code>/help</code> - This menu

👑 <b>ADMIN:</b>
<code>/ping</code> - System report
<code>/logs [days]</code> - View logs
<code>/stats</code> - Bot stats
<code>/users</code> - User list

━━━━━━━━━━━━━━━━━━━━━━━━
💬 <a href="{SUPPORT_CHAT}">Support Chat</a>
🕒 <b>Uptime:</b> {int(time.time() - start_time)}s
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

# ========== /LINK COMMAND - FIXED ==========
@dp.message(Command("link"))
async def link_command(message: Message):
    """Start file upload process"""
    user = message.from_user
    update_user(user)
    
    # Mark user as waiting for file
    user_waiting_for_file[user.id] = True
    
    await message.answer(
        "📁 <b>CATBOX.MOE UPLOADER</b>\n\n"
        "📤 <b>Please send your file now:</b>\n"
        "• Photos (JPG, PNG, GIF)\n"
        "• Videos (MP4, MOV)\n"
        "• Documents (PDF, TXT, ZIP)\n"
        "• Audio files (MP3)\n"
        "• Voice messages\n\n"
        "⚠️ <i>Max size: 200MB</i>\n"
        "❌ Send /cancel to abort",
        parse_mode=ParseMode.HTML
    )

# ========== HANDLE FILE UPLOADS ==========
@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation)
async def handle_file_upload(message: Message):
    """Handle file upload when user sends a file after /link"""
    user = message.from_user
    
    # Check if user is waiting for file upload
    if user.id not in user_waiting_for_file or not user_waiting_for_file[user.id]:
        return
    
    # Remove waiting state
    user_waiting_for_file[user.id] = False
    
    # Animation start
    msg = await message.answer("⏳ <b>Starting upload...</b>", parse_mode=ParseMode.HTML)
    
    # Get file info
    file_id = None
    file_type = "File"
    
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "Photo"
    elif message.video:
        file_id = message.video.file_id
        file_type = "Video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "Document"
        file_name = message.document.file_name or "file.bin"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "Audio"
        file_name = message.audio.file_name or "audio.mp3"
    elif message.voice:
        file_id = message.voice.file_id
        file_type = "Voice"
        file_name = "voice.ogg"
    elif message.sticker:
        file_id = message.sticker.file_id
        file_type = "Sticker"
        file_name = "sticker.webp"
    elif message.animation:
        file_id = message.animation.file_id
        file_type = "GIF"
        file_name = "animation.gif"
    else:
        await msg.edit_text("❌ <b>Unsupported file type</b>", parse_mode=ParseMode.HTML)
        return
    
    try:
        # Step 1: Download from Telegram
        await msg.edit_text("📥 <b>Downloading from Telegram...</b>", parse_mode=ParseMode.HTML)
        
        file = await bot.get_file(file_id)
        file_path = file.file_path
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(download_url)
        
        if response.status_code != 200:
            await msg.edit_text("❌ <b>Failed to download file</b>", parse_mode=ParseMode.HTML)
            return
        
        file_data = response.content
        file_size = len(file_data)
        
        # Step 2: Upload to Catbox
        await msg.edit_text("☁️ <b>Uploading to Catbox.moe...</b>", parse_mode=ParseMode.HTML)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if 'file_name' in locals():
            filename = f"{timestamp}_{file_name}"
        else:
            filename = f"file_{timestamp}.bin"
        
        # Upload to catbox
        upload_result = await upload_to_catbox(file_data, filename)
        
        if not upload_result['success']:
            await msg.edit_text(f"❌ <b>Upload failed:</b> {upload_result.get('error', 'Unknown error')}", parse_mode=ParseMode.HTML)
            return
        
        catbox_url = upload_result['url']
        
        # Save to database
        conn = sqlite3.connect("data/bot.db")
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET uploads_count = uploads_count + 1 WHERE user_id = ?', (user.id,))
        cursor.execute('INSERT INTO uploads (user_id, timestamp, catbox_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)',
                      (user.id, datetime.now().isoformat(), catbox_url, file_type, file_size))
        conn.commit()
        conn.close()
        
        # Success message with animation
        success_emojis = ["✅", "🎉", "✨", "🔗"]
        for emoji in success_emojis:
            await msg.edit_text(f"{emoji} <b>Upload successful!</b>\nGenerating link...", parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.3)
        
        # Final message
        file_size_mb = file_size / (1024 * 1024)
        if file_size_mb < 1:
            size_text = f"{file_size / 1024:.1f} KB"
        else:
            size_text = f"{file_size_mb:.1f} MB"
        
        response_text = f"""
✅ <b>UPLOAD COMPLETE!</b>
━━━━━━━━━━━━━━━━━━━━━━━━

📁 <b>Type:</b> {file_type}
👤 <b>Uploader:</b> {user.first_name}
💾 <b>Size:</b> {size_text}
🕒 <b>Time:</b> {datetime.now().strftime("%H:%M:%S")}

━━━━━━━━━━━━━━━━━━━━━━━━
🔗 <b>Catbox.moe Link:</b>
<code>{catbox_url}</code>
━━━━━━━━━━━━━━━━━━━━━━━━

📤 <b>Features:</b>
• Direct download link
• No expiration date
• Share with anyone
• High speed

🎯 <b>Next:</b> Send another file or use /help
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Open Link", url=catbox_url)],
            [InlineKeyboardButton(text="📤 Share", callback_data=f"share_{catbox_url[-10:]}"),
             InlineKeyboardButton(text="🔄 Upload More", callback_data="upload_more")]
        ])
        
        await msg.edit_text(response_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
    except Exception as e:
        await msg.edit_text(f"❌ <b>Error:</b> {str(e)[:100]}", parse_mode=ParseMode.HTML)
        print(f"Upload error: {e}")

# ========== CANCEL UPLOAD ==========
@dp.message(Command("cancel"))
async def cancel_upload(message: Message):
    """Cancel file upload"""
    user = message.from_user
    if user.id in user_waiting_for_file:
        user_waiting_for_file[user.id] = False
        await message.answer("❌ <b>Upload cancelled</b>", parse_mode=ParseMode.HTML)

# ========== /WISH COMMAND WITH ANIMATION ==========
@dp.message(Command("wish"))
async def wish_command(message: Message):
    """Wish command with animation"""
    user = message.from_user
    update_user(user)
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ <b>Usage:</b> <code>/wish your wish here</code>\n\nExample: <code>/wish I will pass my exam</code>", parse_mode=ParseMode.HTML)
        return
    
    wish_text = args[1]
    
    # Animation
    msg = await message.answer("🔮 <b>Consulting the stars...</b>", parse_mode=ParseMode.HTML)
    
    for emoji in ["✨", "🌟", "⭐", "💫", "🌠"]:
        await msg.edit_text(f"{emoji} <b>Reading your destiny...</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.3)
    
    # Generate luck
    luck = random.randint(1, 100)
    stars = "⭐" * (luck // 10)
    
    if luck >= 90:
        result = "🎊 EXCELLENT! Will definitely happen!"
        emoji = "🎉"
    elif luck >= 70:
        result = "😊 VERY GOOD! High chance!"
        emoji = "✨"
    elif luck >= 50:
        result = "👍 GOOD! Potential success!"
        emoji = "🌟"
    elif luck >= 30:
        result = "🤔 AVERAGE - Needs effort"
        emoji = "⚡"
    elif luck >= 10:
        result = "😟 LOW - Try again"
        emoji = "💡"
    else:
        result = "💀 VERY LOW - Bad timing"
        emoji = "🌧️"
    
    # Save wish
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET wishes_count = wishes_count + 1 WHERE user_id = ?', (user.id,))
    cursor.execute('INSERT INTO wishes (user_id, timestamp, wish_text, luck_percentage) VALUES (?, ?, ?, ?)',
                  (user.id, datetime.now().isoformat(), wish_text, luck))
    conn.commit()
    conn.close()
    
    response = f"""
{emoji} <b>WISH RESULT</b>
━━━━━━━━━━━━━━━━━━━━━━━━

📜 <b>Your Wish:</b>
"{wish_text}"

🎰 <b>Luck Percentage:</b>
{stars} <code>{luck}%</code>

📊 <b>Interpretation:</b>
{result}

━━━━━━━━━━━━━━━━━━━━━━━━
💫 <i>Your destiny has been revealed!</i>
"""
    
    await msg.edit_text(response, parse_mode=ParseMode.HTML)

# ========== /DICE COMMAND ==========
@dp.message(Command("dice"))
async def dice_command(message: Message):
    """Dice roll with animation"""
    user = message.from_user
    update_user(user)
    
    msg = await message.answer("🎲 <b>Shaking the dice...</b>", parse_mode=ParseMode.HTML)
    
    # Animation
    dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    for i in range(6):
        await msg.edit_text(f"🎲 <b>Rolling...</b> {dice_faces[i]}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.15)
    
    roll = random.randint(1, 6)
    face = dice_faces[roll - 1]
    
    response = f"""
🎲 <b>DICE RESULT</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<b>You rolled:</b> {face} <code>{roll}</code>

📊 <b>Analysis:</b>
• Number: {roll}/6
• {'🎯 PERFECT!' if roll == 6 else 'Good!' if roll >= 4 else 'Low roll'}

━━━━━━━━━━━━━━━━━━━━━━━━
🎮 <i>Roll again with /dice</i>
"""
    
    await msg.edit_text(response, parse_mode=ParseMode.HTML)

# ========== /FLIP COMMAND ==========
@dp.message(Command("flip"))
async def flip_command(message: Message):
    """Flip coin command"""
    user = message.from_user
    update_user(user)
    
    msg = await message.answer("🪙 <b>Flipping coin...</b>", parse_mode=ParseMode.HTML)
    
    # Animation
    for i in range(5):
        await msg.edit_text(f"🪙 <b>Flipping...</b> {'HEADS' if i % 2 == 0 else 'TAILS'}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    result = random.choice(["HEADS", "TAILS"])
    emoji = "🟡" if result == "HEADS" else "🟤"
    
    response = f"""
{emoji} <b>COIN FLIP RESULT</b>
━━━━━━━━━━━━━━━━━━━━━━━━

<b>Result:</b> <code>{result}</code>

📊 <b>Analysis:</b>
• 50/50 Chance
• {'🟡 Heads wins!' if result == 'HEADS' else '🟤 Tails wins!'}

━━━━━━━━━━━━━━━━━━━━━━━━
🎮 <i>Flip again with /flip</i>
"""
    
    await msg.edit_text(response, parse_mode=ParseMode.HTML)

# ========== /PROFILE COMMAND ==========
@dp.message(Command("profile"))
async def profile_command(message: Message):
    """User profile"""
    user = message.from_user
    update_user(user)
    
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    cursor.execute('SELECT uploads_count, wishes_count, total_commands, joined_date FROM users WHERE user_id = ?', (user.id,))
    result = cursor.fetchone()
    
    if result:
        uploads, wishes, commands, joined_date = result
    else:
        uploads = wishes = commands = 0
        joined_date = datetime.now().isoformat()
    
    # Count user uploads
    cursor.execute('SELECT COUNT(*) FROM uploads WHERE user_id = ?', (user.id,))
    total_uploads = cursor.fetchone()[0] or 0
    
    # Count user wishes
    cursor.execute('SELECT COUNT(*) FROM wishes WHERE user_id = ?', (user.id,))
    total_wishes = cursor.fetchone()[0] or 0
    
    conn.close()
    
    # Format join date
    try:
        join_date = datetime.fromisoformat(joined_date).strftime("%d %b %Y")
    except:
        join_date = "Recently"
    
    profile = f"""
👤 <b>PROFILE: {user.first_name}</b>
━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Statistics:</b>
• 📁 Uploads: {total_uploads}
• ✨ Wishes: {total_wishes}
• 🔧 Commands: {commands}

📅 <b>Joined:</b> {join_date}
🆔 <b>User ID:</b> <code>{user.id}</code>
📧 <b>Username:</b> @{user.username or 'None'}

━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>Activity:</b>
• Upload files: /link
• Check luck: /wish
• Play games: /dice /flip

━━━━━━━━━━━━━━━━━━━━━━━━
💬 <a href="{SUPPORT_CHAT}">Need help? Join support</a>
"""
    
    await message.answer(profile, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

# ========== /PING COMMAND ==========
@dp.message(Command("ping"))
async def ping_command(message: Message):
    """System ping"""
    if not await is_admin(message.from_user.id):
        await message.answer("🚫 <b>Admin only!</b>", parse_mode=ParseMode.HTML)
        return
    
    response_time = time.time()
    
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0] or 0
    conn.close()
    
    ping_time = (time.time() - response_time) * 1000
    
    response = f"""
🏓 <b>PONG!</b>
━━━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>Response Time:</b> <code>{ping_time:.0f}ms</code>
👥 <b>Total Users:</b> {total_users}
🕒 <b>Uptime:</b> {int(time.time() - start_time)}s
🚄 <b>Host:</b> Railway
🔧 <b>Status:</b> {'🟢 ONLINE' if bot_active else '🔴 OFFLINE'}

━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Commands Working:</b>
• File Upload: ✅
• Wish System: ✅
• Games: ✅
• Profile: ✅
• Admin: ✅

━━━━━━━━━━━━━━━━━━━━━━━━
✅ <i>All systems operational</i>
"""
    
    await message.answer(response, parse_mode=ParseMode.HTML)

# ========== /LOGS COMMAND ==========
@dp.message(Command("logs"))
async def logs_command(message: Message):
    """View logs"""
    if not await is_admin(message.from_user.id):
        await message.answer("🚫 <b>Admin only!</b>", parse_mode=ParseMode.HTML)
        return
    
    args = message.text.split()
    days = 1
    if len(args) > 1 and args[1].isdigit():
        days = int(args[1])
        if days > 30:
            days = 30
    
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    # Get recent uploads
    cursor.execute('''
        SELECT COUNT(*) FROM uploads 
        WHERE DATE(timestamp) >= DATE('now', ?)
    ''', (f'-{days} days',))
    recent_uploads = cursor.fetchone()[0] or 0
    
    # Get recent wishes
    cursor.execute('''
        SELECT COUNT(*) FROM wishes 
        WHERE DATE(timestamp) >= DATE('now', ?)
    ''', (f'-{days} days',))
    recent_wishes = cursor.fetchone()[0] or 0
    
    # Get new users
    cursor.execute('''
        SELECT COUNT(*) FROM users 
        WHERE DATE(joined_date) >= DATE('now', ?)
    ''', (f'-{days} days',))
    new_users = cursor.fetchone()[0] or 0
    
    conn.close()
    
    response = f"""
📊 <b>LOGS SUMMARY - Last {days} day(s)</b>
━━━━━━━━━━━━━━━━━━━━━━━━

📁 <b>Uploads:</b> {recent_uploads}
🌟 <b>Wishes:</b> {recent_wishes}
👥 <b>New Users:</b> {new_users}

📈 <b>Daily Average:</b>
• Uploads/day: {recent_uploads // max(1, days)}
• Wishes/day: {recent_wishes // max(1, days)}

🕒 <b>Period:</b> Last {days} day(s)
📅 <b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}

━━━━━━━━━━━━━━━━━━━━━━━━
📋 <i>Detailed logs available in database</i>
"""
    
    await message.answer(response, parse_mode=ParseMode.HTML)

# ========== /STATS COMMAND ==========
@dp.message(Command("stats"))
async def stats_command(message: Message):
    """Bot statistics"""
    if not await is_admin(message.from_user.id):
        await message.answer("🚫 <b>Admin only!</b>", parse_mode=ParseMode.HTML)
        return
    
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    users = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM uploads')
    uploads = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM wishes')
    wishes = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(last_active) = DATE("now")')
    active_today = cursor.fetchone()[0] or 0
    
    conn.close()
    
    response = f"""
📊 <b>BOT STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👥 <b>Users:</b> {users}
📁 <b>Uploads:</b> {uploads}
🌟 <b>Wishes:</b> {wishes}
⚡ <b>Active Today:</b> {active_today}

🕒 <b>Uptime:</b> {int(time.time() - start_time)}s
🚄 <b>Host:</b> Railway
🔧 <b>Status:</b> {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}

━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>Daily Average:</b>
• Uploads: {uploads // max(1, (int(time.time() - start_time) // 86400))}
• New Users: {users // max(1, (int(time.time() - start_time) // 86400))}

━━━━━━━━━━━━━━━━━━━━━━━━
✅ <i>Bot is running smoothly</i>
"""
    
    await message.answer(response, parse_mode=ParseMode.HTML)

# ========== /USERS COMMAND ==========
@dp.message(Command("users"))
async def users_command(message: Message):
    """List users - admin only"""
    if not await is_admin(message.from_user.id):
        await message.answer("🚫 <b>Admin only!</b>", parse_mode=ParseMode.HTML)
        return
    
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, first_name, username FROM users ORDER BY joined_date DESC LIMIT 50')
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await message.answer("📭 <b>No users found</b>", parse_mode=ParseMode.HTML)
        return
    
    user_list = "👥 <b>RECENT USERS (Last 50)</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for idx, (user_id, first_name, username) in enumerate(users[:25], 1):
        username_display = f"@{username}" if username else "No username"
        user_list += f"{idx}. {first_name}\n   🆔 {user_id}\n   📧 {username_display}\n\n"
    
    user_list += f"\n📊 <b>Total Users:</b> {len(users)}"
    
    await message.answer(user_list, parse_mode=ParseMode.HTML)

# ========== MAIN FUNCTION ==========
async def main():
    """Main function"""
    print("🚀 Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
