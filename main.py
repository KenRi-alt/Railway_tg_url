import os
import asyncio
import time
import random
import sqlite3
import json
import httpx
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

print("🤖 PRO BOT STARTING...")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"

# Create directories
Path("data").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True
upload_waiting = {}
broadcast_state = {}

# ========== DATABASE - FIXED ==========
def init_db():
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        joined_date TEXT,
        last_active TEXT,
        uploads INTEGER DEFAULT 0,
        commands INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0
    )''')
    
    # Uploads table
    c.execute('''CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,
        file_url TEXT,
        file_type TEXT,
        file_size INTEGER
    )''')
    
    # Command logs table
    c.execute('''CREATE TABLE IF NOT EXISTS command_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user_id INTEGER,
        command TEXT,
        success INTEGER
    )''')
    
    # Error logs table
    c.execute('''CREATE TABLE IF NOT EXISTS error_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user_id INTEGER,
        command TEXT,
        error TEXT
    )''')
    
    # Wishes table
    c.execute('''CREATE TABLE IF NOT EXISTS wishes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,
        wish_text TEXT,
        luck INTEGER
    )''')
    
    # Add owner as admin
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (OWNER_ID,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
                 (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== HELPER FUNCTIONS ==========
def log_command(user_id, command, success=True):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO command_logs (timestamp, user_id, command, success) VALUES (?, ?, ?, ?)",
              (datetime.now().isoformat(), user_id, command, 1 if success else 0))
    c.execute("UPDATE users SET commands = commands + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def log_error(user_id, command, error):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO error_logs (timestamp, user_id, command, error) VALUES (?, ?, ?, ?)",
              (datetime.now().isoformat(), user_id, command, str(error)[:200]))
    conn.commit()
    conn.close()

def update_user(user):
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

async def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

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

# ========== ALL ORIGINAL COMMANDS ==========

# ========== /START ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    update_user(message.from_user)
    await message.answer(
        f"✨ <b>Hey {message.from_user.first_name}!</b>\n\n"
        "🤖 <b>PRO TELEGRAM BOT</b>\n\n"
        "🔗 Upload files & get direct links\n"
        "✨ Wish fortune teller\n"
        "🎮 Fun games (dice, coin flip)\n"
        "👑 Admin controls\n\n"
        "📁 <b>Upload:</b> Send <code>/link</code> then any file\n"
        "🎮 <b>Games:</b> <code>/dice</code> <code>/flip</code> <code>/wish [text]</code>\n"
        "👤 <b>Profile:</b> <code>/profile</code>\n"
        "📚 <b>All commands:</b> <code>/help</code>",
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "start")

# ========== /HELP ==========
@dp.message(Command("help"))
async def help_cmd(message: Message):
    update_user(message.from_user)
    help_text = """📚 <b>ALL COMMANDS</b>

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

👑 <b>Admin:</b>
<code>/ping</code> - System status
<code>/logs [days]</code> - View logs (.txt)
<code>/stats</code> - Statistics
<code>/users</code> - User list (.txt)

⚡ <b>Owner:</b>
<code>/pro [id]</code> - Make admin
<code>/toggle</code> - Toggle bot
<code>/broadcast</code> - Send to all
<code>/restart</code> - Restart bot
<code>/backup</code> - Database backup
<code>/emergency_stop</code> - Stop bot"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, "help")

# ========== /LINK ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    update_user(message.from_user)
    upload_waiting[message.from_user.id] = True
    await message.answer(
        "📁 <b>Now send me any file:</b>\n"
        "• Photo, video, document\n"
        "• Audio, voice, sticker\n"
        "• Max 200MB\n\n"
        "❌ <code>/cancel</code> to stop",
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "link")

# ========== HANDLE FILES ==========
@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation | F.video_note)
async def handle_file(message: Message):
    user_id = message.from_user.id
    if user_id not in upload_waiting or not upload_waiting[user_id]:
        return
    
    upload_waiting[user_id] = False
    msg = await message.answer("⏳ <b>Processing...</b>", parse_mode=ParseMode.HTML)
    
    try:
        # Get file
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
        
        # Download file
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
        
        # Upload to Catbox
        await msg.edit_text("☁️ <b>Uploading...</b>", parse_mode=ParseMode.HTML)
        filename = file.file_path.split('/')[-1] if '/' in file.file_path else f"file_{file_id}"
        result = await upload_to_catbox(file_data, filename)
        
        if not result['success']:
            await msg.edit_text("❌ Upload failed")
            return
        
        # Save to database
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user_id,))
        c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)",
                 (user_id, datetime.now().isoformat(), result['url'], file_type, file_size))
        conn.commit()
        conn.close()
        
        # Send result
        size_kb = file_size / 1024
        size_mb = size_kb / 1024
        size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
        
        await msg.edit_text(
            f"✅ <b>Upload Complete!</b>\n\n"
            f"📁 <b>Type:</b> {file_type}\n"
            f"💾 <b>Size:</b> {size_text}\n"
            f"👤 <b>By:</b> {message.from_user.first_name}\n\n"
            f"🔗 <b>Direct Link:</b>\n<code>{result['url']}</code>\n\n"
            f"📤 Permanent link • No expiry • Share anywhere",
            parse_mode=ParseMode.HTML
        )
        log_command(user_id, "upload", True)
        
    except Exception as e:
        await msg.edit_text("❌ Error uploading file")
        log_error(user_id, "upload", e)

# ========== /CANCEL ==========
@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user_id = message.from_user.id
    if user_id in upload_waiting:
        upload_waiting[user_id] = False
        await message.answer("❌ Upload cancelled")
    log_command(user_id, "cancel")

# ========== /WISH ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    update_user(message.from_user)
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ <b>Usage:</b> <code>/wish your wish here</code>", parse_mode=ParseMode.HTML)
        return
    
    msg = await message.answer("✨ <b>Reading your destiny...</b>", parse_mode=ParseMode.HTML)
    
    # Animation
    for emoji in ["🌟", "⭐", "💫", "🌠", "✨"]:
        await msg.edit_text(f"{emoji} <b>Consulting the stars...</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    # Generate result
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
    
    # Save to database
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO wishes (user_id, timestamp, wish_text, luck) VALUES (?, ?, ?, ?)",
             (message.from_user.id, datetime.now().isoformat(), args[1], luck))
    conn.commit()
    conn.close()
    
    await msg.edit_text(
        f"🔮 <b>WISH RESULT</b>\n\n"
        f"📜 <b>Wish:</b> {args[1]}\n"
        f"🎰 <b>Luck:</b> {stars} {luck}%\n"
        f"📊 <b>Result:</b> {result}",
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "wish")

# ========== /DICE ==========
@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    update_user(message.from_user)
    msg = await message.answer("🎲 <b>Rolling dice...</b>", parse_mode=ParseMode.HTML)
    
    # Animation
    faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    for i in range(6):
        await msg.edit_text(f"🎲 <b>Rolling...</b> {faces[i]}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.15)
    
    roll = random.randint(1, 6)
    await msg.edit_text(f"🎲 <b>You rolled: {faces[roll-1]} ({roll})</b>", parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, "dice")

# ========== /FLIP ==========
@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    update_user(message.from_user)
    msg = await message.answer("🪙 <b>Flipping coin...</b>", parse_mode=ParseMode.HTML)
    
    # Animation
    for i in range(5):
        await msg.edit_text(f"🪙 <b>Flipping...</b> {'HEADS' if i % 2 == 0 else 'TAILS'}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}</b>", parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, "flip")

# ========== /PROFILE ==========
@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    update_user(message.from_user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Get user stats
    c.execute("SELECT uploads, commands, joined_date FROM users WHERE user_id = ?", (message.from_user.id,))
    row = c.fetchone()
    
    if row:
        uploads, cmds, joined = row
        # Count wishes
        c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (message.from_user.id,))
        wishes = c.fetchone()[0] or 0
        
        # Format join date
        try:
            join_date = datetime.fromisoformat(joined).strftime("%d %b %Y")
        except:
            join_date = "Recently"
    else:
        uploads = cmds = wishes = 0
        join_date = "Today"
    
    conn.close()
    
    await message.answer(
        f"👤 <b>PROFILE: {message.from_user.first_name}</b>\n\n"
        f"📁 <b>Uploads:</b> {uploads}\n"
        f"✨ <b>Wishes:</b> {wishes}\n"
        f"🔧 <b>Commands:</b> {cmds}\n"
        f"📅 <b>Joined:</b> {join_date}\n"
        f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n\n"
        f"💡 <b>Next:</b> Try /link to upload files",
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "profile")

# ========== /PING ==========
@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("🚫 Admin only")
        return
    
    start_ping = time.time()
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM uploads")
    uploads = c.fetchone()[0] or 0
    conn.close()
    
    ping_ms = (time.time() - start_ping) * 1000
    
    await message.answer(
        f"🏓 <b>PONG!</b>\n\n"
        f"⚡ <b>Response:</b> {ping_ms:.0f}ms\n"
        f"👥 <b>Users:</b> {users}\n"
        f"📁 <b>Uploads:</b> {uploads}\n"
        f"🕒 <b>Uptime:</b> {int(time.time() - start_time)}s\n"
        f"🔧 <b>Status:</b> {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}",
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "ping")

# ========== /LOGS ==========
@dp.message(Command("logs"))
async def logs_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    days = 1
    if len(args) > 1 and args[1].isdigit():
        days = int(args[1])
        if days > 30:
            days = 30
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Get command logs
    c.execute("SELECT timestamp, user_id, command, success FROM command_logs WHERE DATE(timestamp) >= DATE('now', '-? days') ORDER BY timestamp DESC LIMIT 500", (days,))
    cmd_logs = c.fetchall()
    
    # Get error logs
    c.execute("SELECT timestamp, user_id, command, error FROM error_logs WHERE DATE(timestamp) >= DATE('now', '-? days') ORDER BY timestamp DESC LIMIT 200", (days,))
    err_logs = c.fetchall()
    
    conn.close()
    
    # Create log file
    log_content = f"📊 BOT LOGS - Last {days} day(s)\n"
    log_content += "=" * 40 + "\n\n"
    log_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    log_content += f"Total Commands: {len(cmd_logs)}\n"
    log_content += f"Total Errors: {len(err_logs)}\n\n"
    
    log_content += "📝 COMMAND LOGS:\n"
    for ts, uid, cmd, succ in cmd_logs[:100]:
        time_str = datetime.fromisoformat(ts).strftime("%m/%d %H:%M")
        status = "✅" if succ else "❌"
        log_content += f"[{time_str}] {uid} {status} {cmd}\n"
    
    log_content += "\n\n❌ ERROR LOGS:\n"
    for ts, uid, cmd, err in err_logs[:50]:
        time_str = datetime.fromisoformat(ts).strftime("%m/%d %H:%M")
        log_content += f"[{time_str}] {uid} {cmd}: {err}\n"
    
    # Save and send file
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
    
    log_command(message.from_user.id, f"logs {days}")

# ========== /STATS ==========
@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM uploads")
    uploads = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM wishes")
    wishes = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM command_logs WHERE DATE(timestamp) = DATE('now')")
    today_cmds = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM users WHERE DATE(last_active) = DATE('now')")
    active = c.fetchone()[0] or 0
    
    conn.close()
    
    await message.answer(
        f"📊 <b>BOT STATISTICS</b>\n\n"
        f"👥 <b>Users:</b> {users}\n"
        f"📁 <b>Uploads:</b> {uploads}\n"
        f"✨ <b>Wishes:</b> {wishes}\n"
        f"🔧 <b>Commands Today:</b> {today_cmds}\n"
        f"⚡ <b>Active Today:</b> {active}\n\n"
        f"🕒 <b>Uptime:</b> {int(time.time() - start_time)}s\n"
        f"🔧 <b>Status:</b> {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}",
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "stats")

# ========== /USERS ==========
@dp.message(Command("users"))
async def users_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, uploads, commands FROM users ORDER BY joined_date DESC LIMIT 100")
    users = c.fetchall()
    conn.close()
    
    user_list = "👥 USER LIST\n" + "="*40 + "\n\n"
    for uid, name, uname, up, cmds in users:
        un = f"@{uname}" if uname else "No username"
        user_list += f"🆔 {uid}\n👤 {name}\n📧 {un}\n📁 {up} | 🔧 {cmds}\n" + "-"*30 + "\n"
    
    filename = f"temp/users_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(user_list)
    
    await message.answer_document(
        FSInputFile(filename),
        caption="📁 User list (last 100)"
    )
    
    try:
        os.remove(filename)
    except:
        pass
    
    log_command(message.from_user.id, "users")

# ========== /PRO ==========
@dp.message(Command("pro"))
async def pro_cmd(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("👑 <b>Usage:</b> <code>/pro user_id</code>", parse_mode=ParseMode.HTML)
        return
    
    target_id = int(args[1])
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ User {target_id} is now admin")
    log_command(message.from_user.id, f"pro {target_id}")

# ========== /TOGGLE ==========
@dp.message(Command("toggle"))
async def toggle_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    global bot_active
    bot_active = not bot_active
    status = "🟢 ACTIVE" if bot_active else "🔴 PAUSED"
    await message.answer(f"✅ Bot is now {status}")
    log_command(message.from_user.id, f"toggle {bot_active}")

# ========== /BROADCAST ==========
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    broadcast_state[message.from_user.id] = True
    await message.answer(
        "📢 <b>Send broadcast message now:</b>\n"
        "• Text message\n"
        "• Photo with caption\n"
        "• Video with caption\n\n"
        "⚠️ <b>Next message will be broadcasted</b>\n"
        "❌ <code>/cancel</code> to abort",
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "broadcast_start")

# ========== /BACKUP ==========
@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    import shutil
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{timestamp}.db"
    
    shutil.copy2("data/bot.db", backup_file)
    await message.answer_document(
        FSInputFile(backup_file),
        caption=f"💾 Backup {timestamp}"
    )
    
    try:
        os.remove(backup_file)
    except:
        pass
    
    log_command(message.from_user.id, "backup")

# ========== /RESTART ==========
@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    restart_data = {
        "time": datetime.now().isoformat(),
        "user_id": message.from_user.id
    }
    
    with open("data/restart.json", "w") as f:
        json.dump(restart_data, f)
    
    await message.answer("🔄 <b>Restarting bot...</b>", parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, "restart")
    import sys
    sys.exit(0)

# ========== /EMERGENCY_STOP ==========
@dp.message(Command("emergency_stop"))
async def emergency_stop(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    global bot_active
    bot_active = False
    
    await message.answer("🛑 <b>BOT EMERGENCY STOPPED!</b>", parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, "emergency_stop")

# ========== HANDLE BROADCAST MESSAGES ==========
@dp.message()
async def handle_broadcast(message: Message):
    user_id = message.from_user.id
    if user_id in broadcast_state and broadcast_state[user_id]:
        broadcast_state[user_id] = False
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = [row[0] for row in c.fetchall()]
        conn.close()
        
        total = len(users)
        status_msg = await message.answer(f"📤 Sending to {total} users...")
        
        success = 0
        for uid in users:
            try:
                if message.text:
                    await bot.send_message(uid, f"📢 {message.text}")
                elif message.photo:
                    await bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption or "📢 Broadcast")
                elif message.video:
                    await bot.send_video(uid, message.video.file_id, caption=message.caption or "📢 Broadcast")
                elif message.document:
                    await bot.send_document(uid, message.document.file_id, caption=message.caption or "📢 Broadcast")
                success += 1
                await asyncio.sleep(0.05)
            except:
                continue
        
        await status_msg.edit_text(f"✅ Sent to {success}/{total} users")
        log_command(user_id, f"broadcast {success}/{total}")

# ========== MAIN ==========
async def main():
    print("🚀 Bot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
