import os
import asyncio
import logging
import time
import random
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import aiohttp
import sys
import json
import httpx
from io import BytesIO
import html
import base64
import mimetypes

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    FSInputFile
)
from aiogram.enums import ParseMode

print("=" * 70)
print("🤖 ULTIMATE MEDIA BOT v6.0 - Starting...")
print(f"🐍 Python: {sys.version.split()[0]}")
print("=" * 70)

# ========== CONFIGURATION ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
CATBOX_API = "https://catbox.moe/user/api.php"

# Create directories
Path("data").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True)

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Global states
bot_active = True
bot_speed = "normal"
start_time = time.time()

# ========== DATABASE ==========
def init_db():
    """Initialize database"""
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
            total_uploads INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            file_type TEXT,
            file_size INTEGER,
            catbox_url TEXT,
            telegram_url TEXT,
            views INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            wish_text TEXT,
            luck_percentage INTEGER,
            stars TEXT,
            result TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== CATBOX UPLOAD FUNCTION ==========
async def upload_to_catbox(file_data: bytes, filename: str) -> dict:
    """
    Upload any file to Catbox.moe using proper API
    Returns: {'success': bool, 'url': str, 'error': str}
    """
    try:
        # Prepare multipart form data
        files = {
            'reqtype': (None, 'fileupload'),
            'fileToUpload': (filename, file_data),
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                CATBOX_API,
                files=files,
                headers=headers
            )
            
        if response.status_code == 200 and response.text:
            url = response.text.strip()
            if url.startswith('http'):
                return {
                    'success': True,
                    'url': url,
                    'filename': filename,
                    'size': len(file_data)
                }
            else:
                return {
                    'success': False,
                    'error': 'Invalid response from Catbox',
                    'details': response.text[:100]
                }
        else:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}',
                'details': response.text[:100] if response.text else 'No response'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'details': 'Upload failed'
        }

# ========== DOWNLOAD TELEGRAM FILE ==========
async def download_telegram_file(file_id: str) -> tuple:
    """
    Download file from Telegram and return (data, filename, file_type)
    """
    try:
        # Get file info
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        # Generate filename
        filename = file_path.split('/')[-1] if '/' in file_path else f"file_{file_id}"
        
        # Download file
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(file_url)
            
        if response.status_code == 200:
            return (response.content, filename, file_path)
        else:
            return (None, None, None)
            
    except Exception as e:
        print(f"❌ Download error: {e}")
        return (None, None, None)

# ========== ENHANCED /LINK COMMAND WITH CATBOX ==========
@dp.message(Command("link"))
async def enhanced_link_command(message: Message):
    """Upload any media to Catbox.moe and provide links"""
    user = message.from_user
    
    # Update user
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, joined_date, last_active)
        VALUES (?, ?, ?, ?, COALESCE((SELECT joined_date FROM users WHERE user_id = ?), ?), ?)
    ''', (user.id, user.username, user.first_name, user.last_name,
          user.id, datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Check for media
    media_types = {
        'photo': (message.photo, "📸 Photo"),
        'video': (message.video, "🎥 Video"),
        'audio': (message.audio, "🎵 Audio"),
        'document': (message.document, "📄 Document"),
        'voice': (message.voice, "🎤 Voice"),
        'sticker': (message.sticker, "😀 Sticker"),
        'video_note': (message.video_note, "⭕ Video Note"),
        'animation': (message.animation, "🎬 Animation"),
    }
    
    # Find which media type is present
    file_id = None
    file_type_display = "File"
    file_emoji = "📁"
    file_details = {}
    
    for media_type, (media, display_name) in media_types.items():
        if media:
            if media_type == 'photo':
                file_id = media[-1].file_id
                file_type_display = display_name
                file_emoji = "📸"
                file_details = {
                    'width': media[-1].width,
                    'height': media[-1].height,
                    'size': media[-1].file_size
                }
            else:
                file_id = media.file_id
                file_type_display = display_name
                file_emoji = "📸🎥🎵📄🎤😀⭕🎬"["photo video audio document voice sticker video_note animation".split().index(media_type)]
                
                if media_type == 'video' and hasattr(media, 'duration'):
                    file_details['duration'] = f"{media.duration // 60}:{media.duration % 60:02d}"
                if media_type == 'audio' and hasattr(media, 'duration'):
                    file_details['duration'] = f"{media.duration // 60}:{media.duration % 60:02d}"
                if hasattr(media, 'file_size'):
                    file_details['size'] = media.file_size
                if hasattr(media, 'file_name'):
                    file_details['name'] = media.file_name
                if hasattr(media, 'mime_type'):
                    file_details['mime'] = media.mime_type
            break
    
    if not file_id:
        # Send help message
        await message.answer(
            "📁 <b>MEDIA UPLOADER TO CATBOX.MOE</b>\n\n"
            "📸 <b>Supported Files:</b>\n"
            "• Photos (JPG, PNG, GIF, etc.)\n"
            "• Videos (MP4, MOV, AVI, etc.)\n"
            "• Audio files (MP3, WAV, etc.)\n"
            "• Documents (PDF, DOC, XLS, etc.)\n"
            "• Voice messages\n"
            "• Stickers\n"
            "• Video Notes\n"
            "• Animations (GIFs)\n\n"
            "🚀 <b>How to use:</b>\n"
            "1. Type <code>/link</code>\n"
            "2. Send any file\n"
            "3. Get Catbox.moe link\n\n"
            "⚡ <b>Features:</b>\n"
            "• Direct Catbox links\n"
            "• No expiration\n"
            "• High speed\n"
            "• Bypass Telegram limits\n\n"
            "⚠️ <i>Max file size: 200MB (Catbox limit)</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Send processing message
    processing_msg = await message.answer(
        f"🔄 <b>Processing {file_type_display}...</b>\n"
        f"⏳ Downloading from Telegram...",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Step 1: Download from Telegram
        await processing_msg.edit_text(
            f"🔄 <b>Processing {file_type_display}...</b>\n"
            f"📥 Downloading from Telegram servers...",
            parse_mode=ParseMode.HTML
        )
        
        file_data, original_filename, file_path = await download_telegram_file(file_id)
        
        if not file_data:
            await processing_msg.edit_text(
                "❌ <b>Failed to download file from Telegram!</b>\n"
                "Please try again with a smaller file.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Step 2: Upload to Catbox
        await processing_msg.edit_text(
            f"🔄 <b>Processing {file_type_display}...</b>\n"
            f"☁️ Uploading to Catbox.moe...",
            parse_mode=ParseMode.HTML
        )
        
        # Generate filename
        file_ext = original_filename.split('.')[-1] if '.' in original_filename else 'bin'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        catbox_filename = f"file_{timestamp}.{file_ext}"
        
        # Upload to Catbox
        upload_result = await upload_to_catbox(file_data, catbox_filename)
        
        if not upload_result['success']:
            await processing_msg.edit_text(
                f"❌ <b>Upload to Catbox failed!</b>\n"
                f"Error: {upload_result.get('error', 'Unknown error')}",
                parse_mode=ParseMode.HTML
            )
            return
        
        catbox_url = upload_result['url']
        file_size_mb = len(file_data) / (1024 * 1024)
        
        # Step 3: Generate Telegram link
        bot_info = await bot.get_me()
        telegram_url = f"https://t.me/{bot_info.username}?start=file_{file_id}"
        
        # Step 4: Save to database
        conn = sqlite3.connect("data/bot.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET total_uploads = total_uploads + 1 
            WHERE user_id = ?
        ''', (user.id,))
        
        cursor.execute('''
            INSERT INTO uploads 
            (user_id, timestamp, file_type, file_size, catbox_url, telegram_url, views)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user.id,
            datetime.now().isoformat(),
            file_type_display,
            len(file_data),
            catbox_url,
            telegram_url,
            0
        ))
        
        conn.commit()
        
        # Get user stats
        cursor.execute('SELECT total_uploads FROM users WHERE user_id = ?', (user.id,))
        user_stats = cursor.fetchone()
        total_uploads = user_stats[0] if user_stats else 1
        
        conn.close()
        
        # Step 5: Create response
        # Format file size
        if file_size_mb < 1:
            size_display = f"{len(file_data) / 1024:.1f} KB"
        else:
            size_display = f"{file_size_mb:.1f} MB"
        
        # Build details string
        details_lines = []
        if 'width' in file_details and 'height' in file_details:
            details_lines.append(f"📐 Resolution: {file_details['width']}x{file_details['height']}")
        if 'duration' in file_details:
            details_lines.append(f"⏱️ Duration: {file_details['duration']}")
        if 'name' in file_details:
            details_lines.append(f"📝 Name: {file_details['name']}")
        if 'mime' in file_details:
            details_lines.append(f"📄 Type: {file_details['mime']}")
        
        details_lines.append(f"💾 Size: {size_display}")
        details_lines.append(f"📅 Uploaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        details_text = "\n".join(details_lines)
        
        response = f"""
🔗 <b>✨ FILE UPLOADED SUCCESSFULLY! ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━

{file_emoji} <b>File Type:</b> {file_type_display}
👤 <b>Uploaded by:</b> {user.first_name}
🆔 <b>User ID:</b> <code>{user.id}</code>

📋 <b>File Details:</b>
{details_text}

━━━━━━━━━━━━━━━━━━━━━━━━
🔗 <b>Catbox.moe Link:</b>
<code>{catbox_url}</code>

🔗 <b>Telegram Link:</b>
<code>{telegram_url}</code>
━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>Your Upload Stats:</b>
• Total Uploads: {total_uploads}
• This File: #{total_uploads}
• Storage: Catbox.moe ☁️

⚡ <b>Download Options:</b>
1. <b>Catbox Link</b> - Direct download, no expiration
2. <b>Telegram Link</b> - Works within Telegram

💡 <b>Tips:</b>
• Catbox links never expire
• Share with anyone
• High speed downloads
━━━━━━━━━━━━━━━━━━━━━━━━
✅ <i>Upload completed in {time.time() - start_time:.1f}s</i>
"""
        
        # Create keyboard with actions
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔗 Copy Catbox Link", callback_data=f"copy_catbox_{catbox_url[-10:]}"),
                InlineKeyboardButton(text="📤 Share", callback_data=f"share_{catbox_url[-10:]}")
            ],
            [
                InlineKeyboardButton(text="📊 View Stats", callback_data="upload_stats"),
                InlineKeyboardButton(text="🔄 Upload Another", callback_data="upload_another")
            ]
        ])
        
        await processing_msg.delete()
        await message.answer(response, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        
        print(f"✅ File uploaded by {user.id}: {file_type_display} → {catbox_url}")
        
    except Exception as e:
        await processing_msg.edit_text(
            f"❌ <b>Error processing file!</b>\n"
            f"Error: {str(e)}",
            parse_mode=ParseMode.HTML
        )
        print(f"❌ Upload error: {e}")

# ========== /WISH COMMAND ==========
@dp.message(Command("wish"))
async def wish_command(message: Message):
    """Wish command with 1-100% success rate"""
    user = message.from_user
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "✨ <b>How to use /wish:</b>\n\n"
            "<code>/wish I will pass my exam</code>\n"
            "<code>/wish I want to be rich</code>\n"
            "<code>/wish I will find true love</code>\n\n"
            "🎯 <i>Be specific for better results!</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    wish_text = args[1]
    
    # Animated loading
    loading_msg = await message.answer("✨ <b>Consulting the cosmic oracle...</b>")
    
    animations = ["🌠", "🌟", "⭐", "💫", "✨", "☄️", "🌌"]
    for emoji in animations:
        await loading_msg.edit_text(f"{emoji} <b>Reading your destiny...</b> {emoji}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.3)
    
    # Generate luck
    luck = random.randint(1, 100)
    stars = "⭐" * (luck // 10) + "☆" * (10 - (luck // 10))
    
    # Determine result
    if luck >= 90:
        result = "🎊 EXCELLENT! Your wish will definitely come true!"
        advice = "The universe fully supports you! Take action now!"
    elif luck >= 70:
        result = "😊 VERY GOOD! High chances of success!"
        advice = "Stay positive and work towards your goal!"
    elif luck >= 50:
        result = "👍 GOOD! Your wish has potential!"
        advice = "Be consistent and patient!"
    elif luck >= 30:
        result = "🤔 AVERAGE - Might need some effort"
        advice = "Consider refining your approach!"
    elif luck >= 10:
        result = "😟 LOW - Consider making another wish"
        advice = "The universe suggests trying again later!"
    else:
        result = "💀 VERY LOW - Cosmic interference detected"
        advice = "Wait for better timing!"
    
    # Save to database
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO wishes (user_id, timestamp, wish_text, luck_percentage, stars, result)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user.id, datetime.now().isoformat(), wish_text, luck, stars, result))
    conn.commit()
    conn.close()
    
    response = f"""
🎯 <b>✨ WISH FORTUNE ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━

✨ <b>Your Wish:</b>
<code>{wish_text}</code>

🎰 <b>Luck Percentage:</b>
{stars} <code>{luck}%</code>

📊 <b>Result:</b>
{result}

💫 <b>Cosmic Advice:</b>
{advice}

━━━━━━━━━━━━━━━━━━━━━━━━
📅 <i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
🎲 <i>Wish ID: W{random.randint(1000, 9999)}</i>
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await loading_msg.delete()
    await message.answer(response, parse_mode=ParseMode.HTML)

# ========== /PING WITH CATBOX ==========
@dp.message(Command("ping"))
async def ping_command(message: Message):
    """Ping command with Catbox upload"""
    start_ping = time.time()
    
    # Get bot stats
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM uploads")
    total_uploads = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM wishes")
    total_wishes = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(file_size) FROM uploads")
    total_storage = cursor.fetchone()[0] or 0
    
    conn.close()
    
    # Create detailed report
    report = f"""
╔══════════════════════════════════════════════╗
║           🤖 BOT STATUS REPORT               ║
╠══════════════════════════════════════════════╣
║ 📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
║ 🚄 Host: Railway
║ 🐍 Python: {sys.version.split()[0]}
║ 🔧 Version: 6.0 Catbox Edition
╠══════════════════════════════════════════════╣
║ 📊 STATISTICS:
║ • Total Users: {total_users}
║ • Total Uploads: {total_uploads}
║ • Total Wishes: {total_wishes}
║ • Storage Used: {total_storage / (1024*1024):.1f} MB
║ • Bot Uptime: {int(time.time() - start_time)}s
╠══════════════════════════════════════════════╣
║ ⚡ PERFORMANCE:
║ • Status: {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}
║ • Speed Mode: {bot_speed.upper()}
║ • Platform: Railway
║ • Memory: Stable
╠══════════════════════════════════════════════╣
║ 🌟 FEATURES:
║ • Catbox.moe Uploads
║ • Wish Fortune System
║ • Admin Controls
║ • Always Online
╚══════════════════════════════════════════════╝
    """
    
    # Upload to Catbox
    ping_msg = await message.answer("🏓 <b>Generating status report...</b>", parse_mode=ParseMode.HTML)
    
    catbox_result = await upload_to_catbox(
        report.encode('utf-8'),
        f"bot_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    
    end_ping = time.time()
    latency = round((end_ping - start_ping) * 1000, 2)
    
    if catbox_result['success']:
        response = f"""
🏓 <b>✨ PONG! ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>Latency:</b> <code>{latency}ms</code>
🚄 <b>Host:</b> Railway
🕒 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

📊 <b>Quick Stats:</b>
• Users: {total_users}
• Uploads: {total_uploads}
• Wishes: {total_wishes}
• Storage: {total_storage / (1024*1024):.1f} MB

📄 <b>Detailed Report:</b>
🔗 <a href="{catbox_result['url']}">View Full Report on Catbox</a>

━━━━━━━━━━━━━━━━━━━━━━━━
✅ <i>All systems operational!</i>
"""
    else:
        response = f"""
🏓 <b>✨ PONG! ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>Latency:</b> <code>{latency}ms</code>
🚄 <b>Host:</b> Railway

📊 <b>Statistics:</b>
• Total Users: {total_users}
• Total Uploads: {total_uploads}
• Total Wishes: {total_wishes}

❌ <i>Catbox upload failed, showing text report:</i>

{report[:1500]}...
"""
    
    await ping_msg.edit_text(response, parse_mode=ParseMode.HTML)

# ========== /PRO COMMAND ==========
@dp.message(Command("pro"))
async def pro_command(message: Message):
    """Give admin rights to user"""
    if message.from_user.id != OWNER_ID:
        await message.answer("🚫 <b>Owner only command!</b>", parse_mode=ParseMode.HTML)
        return
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer(
            "👑 <b>Usage:</b> <code>/pro user_id</code>\n\n"
            "💡 <i>Gives admin rights to the user</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    user_id = int(args[1])
    
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ <b>User {user_id} is now an admin!</b>", parse_mode=ParseMode.HTML)

# ========== /TOGGLE COMMAND ==========
@dp.message(Command("toggle"))
async def toggle_command(message: Message):
    """Toggle bot speed"""
    global bot_speed
    
    if message.from_user.id != OWNER_ID:
        await message.answer("🚫 <b>Owner only!</b>", parse_mode=ParseMode.HTML)
        return
    
    bot_speed = "slow" if bot_speed == "normal" else "normal"
    await message.answer(f"⚡ <b>Bot speed set to: {bot_speed.upper()}</b>", parse_mode=ParseMode.HTML)

# ========== CRITICAL OWNER COMMANDS ==========
@dp.message(Command("emergency_stop"))
async def emergency_stop(message: Message):
    """Emergency stop bot"""
    if message.from_user.id != OWNER_ID:
        return
    
    global bot_active
    bot_active = False
    await message.answer("🛑 <b>BOT EMERGENCY STOPPED!</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("restart"))
async def restart_command(message: Message):
    """Restart bot functionality"""
    if message.from_user.id != OWNER_ID:
        return
    
    global bot_active, start_time
    bot_active = True
    start_time = time.time()
    await message.answer("🔄 <b>Bot restarted successfully!</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("wipe"))
async def wipe_command(message: Message):
    """Wipe all data (DANGEROUS)"""
    if message.from_user.id != OWNER_ID:
        return
    
    args = message.text.split()
    if len(args) < 2 or args[1] != "CONFIRM":
        await message.answer(
            "⚠️ <b>DANGER: This will delete ALL data!</b>\n\n"
            "To confirm, type:\n"
            "<code>/wipe CONFIRM</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Backup first
    import shutil
    shutil.copy2("data/bot.db", f"data/bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    
    # Recreate database
    init_db()
    
    await message.answer("🧹 <b>All data wiped! Fresh start.</b>", parse_mode=ParseMode.HTML)

@dp.message(Command("broadcast"))
async def broadcast_command(message: Message):
    """Broadcast to all users"""
    if message.from_user.id != OWNER_ID:
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📢 <b>Usage:</b> <code>/broadcast message</code>", parse_mode=ParseMode.HTML)
        return
    
    broadcast_msg = args[1]
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    total = len(users)
    success = 0
    
    status = await message.answer(f"📢 Broadcasting to {total} users...")
    
    for user_id, in users:
        try:
            await bot.send_message(
                user_id,
                f"📢 <b>BROADCAST</b>\n\n{broadcast_msg}",
                parse_mode=ParseMode.HTML
            )
            success += 1
        except:
            pass
        
        if success % 10 == 0:
            await status.edit_text(f"📢 Sent: {success}/{total}")
        await asyncio.sleep(0.1)
    
    await status.edit_text(f"✅ Broadcast complete! Sent to {success}/{total} users")

@dp.message(Command("stats"))
async def stats_command(message: Message):
    """Detailed bot statistics"""
    if message.from_user.id != OWNER_ID:
        return
    
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM uploads")
    uploads = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM wishes")
    wishes = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    admins = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(last_active) = DATE('now')")
    active_today = cursor.fetchone()[0] or 0
    
    conn.close()
    
    response = f"""
📊 <b>BOT STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👥 <b>Users:</b> {users}
📈 <b>Active Today:</b> {active_today}
👑 <b>Admins:</b> {admins}

📁 <b>Uploads:</b> {uploads}
🌟 <b>Wishes:</b> {wishes}

⚡ <b>Performance:</b>
• Uptime: {int(time.time() - start_time)}s
• Speed: {bot_speed.upper()}
• Status: {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}

🚄 <b>Host:</b> Railway
🔧 <b>Version:</b> 6.0
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.answer(response, parse_mode=ParseMode.HTML)

# ========== START COMMAND ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    """Start command"""
    user = message.from_user
    
    welcome = f"""
🌟 <b>Welcome {user.first_name}!</b> 🌟

🤖 <b>ULTIMATE MEDIA BOT</b>
Version 6.0 | Catbox.moe Edition

🚀 <b>Features:</b>
• Upload any file to Catbox.moe
• Wish fortune teller (1-100%)
• Admin controls
• Always online

🎯 <b>Commands:</b>
• /link - Upload files to Catbox
• /wish - Check luck percentage
• /help - Show all commands

💡 <b>Quick Start:</b>
1. Send a file with /link
2. Get Catbox download link
3. Share with anyone!

🚄 <b>Hosted on Railway</b>
⚡ Always Online | 🔒 Secure
"""
    
    await message.answer(welcome, parse_mode=ParseMode.HTML)

# ========== HELP COMMAND ==========
@dp.message(Command("help"))
async def help_command(message: Message):
    """Help command"""
    help_text = """
📚 <b>BOT COMMANDS</b>

🔗 <b>Media Commands:</b>
/link - Upload any file to Catbox.moe
  <i>Send a file after this command</i>

🌟 <b>Wish Commands:</b>
/wish [your wish] - Check luck (1-100%)
  <i>Example: /wish I will be successful</i>

👑 <b>Owner Commands:</b>
/pro [user_id] - Make someone admin
/toggle - Toggle bot speed
/broadcast - Send message to all users
/stats - View bot statistics
/restart - Restart bot
/emergency_stop - Stop bot
/wipe - Delete all data (dangerous)

🛠️ <b>Utility Commands:</b>
/ping - Check bot status with Catbox
/start - Show welcome message
/help - Show this help

🚄 <b>Powered by:</b>
• Catbox.moe for file hosting
• Railway for 24/7 hosting
• Python + aiogram
"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== KEEP-ALIVE ==========
async def keep_alive():
    """Keep Railway from sleeping"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        print(f"💓 Keep-alive at {datetime.now().strftime('%H:%M:%S')}")

# ========== MAIN ==========
async def main():
    """Main function"""
    print("🚀 Starting bot with polling...")
    
    # Start keep-alive
    asyncio.create_task(keep_alive())
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
