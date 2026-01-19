import os
import asyncio
import time
import random
import sqlite3
import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

print("🤖 BOT STARTING...")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True
upload_waiting = {}
broadcast_state = {}

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
        is_admin INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,
        file_url TEXT,
        file_type TEXT,
        file_size INTEGER
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user_id INTEGER,
        command TEXT,
        success INTEGER
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user_id INTEGER,
        command TEXT,
        error TEXT
    )''')
    
    c.execute('INSERT OR IGNORE INTO users (user_id, first_name, is_admin) VALUES (?, ?, ?)', 
              (OWNER_ID, "Owner", 1))
    conn.commit()
    conn.close()

init_db()

# ========== HELPERS ==========
def log_command(user_id, command, success=True):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute('INSERT INTO logs (timestamp, user_id, command, success) VALUES (?, ?, ?, ?)',
              (datetime.now().isoformat(), user_id, command, 1 if success else 0))
    c.execute('UPDATE users SET commands = commands + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def log_error(user_id, command, error):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute('INSERT INTO errors (timestamp, user_id, command, error) VALUES (?, ?, ?, ?)',
              (datetime.now().isoformat(), user_id, command, str(error)[:200]))
    conn.commit()
    conn.close()

def update_user(user):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date, last_active) 
                 VALUES (?, ?, ?, ?, ?)''',
              (user.id, user.username, user.first_name, datetime.now().isoformat(), datetime.now().isoformat()))
    c.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()

async def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

async def upload_file(file_data, filename):
    try:
        files = {'reqtype': (None, 'fileupload'), 'fileToUpload': (filename, file_data)}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(UPLOAD_API, files=files)
        if r.status_code == 200 and r.text.startswith('http'):
            return {'success': True, 'url': r.text.strip()}
        return {'success': False, 'error': 'Upload failed'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ========== COMMANDS ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    update_user(message.from_user)
    await message.answer(
        f"👋 <b>Hey {message.from_user.first_name}!</b>\n\n"
        "🤖 <b>Pro Bot - File Hosting</b>\n"
        "• Upload files & get direct links\n"
        "• Games & fun commands\n"
        "• Admin controls\n\n"
        "📁 <b>Upload:</b> /link then send file\n"
        "🎮 <b>Games:</b> /dice /flip /wish\n"
        "👤 <b>Profile:</b> /profile\n"
        "📚 <b>Help:</b> /help", 
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "start")

@dp.message(Command("help"))
async def help_cmd(message: Message):
    update_user(message.from_user)
    text = """📚 <b>Commands</b>

🔗 <b>Upload:</b>
/link - Upload file (send file after)

🎮 <b>Games:</b>
/wish [text] - Check luck
/dice - Roll dice
/flip - Flip coin

👤 <b>User:</b>
/profile - Your stats
/start - Welcome

👑 <b>Admin:</b>
/ping - System status
/logs [days] - View logs
/stats - Statistics
/users - User list
/pro [id] - Make admin
/toggle - Toggle bot
/broadcast - Send to all
/restart - Restart bot"""
    
    await message.answer(text, parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, "help")

# ========== FILE UPLOAD ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    update_user(message.from_user)
    upload_waiting[message.from_user.id] = True
    await message.answer(
        "📁 <b>Send me any file</b>\n"
        "• Photo, video, document, audio\n"
        "• Max 200MB\n"
        "❌ /cancel to stop", 
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "link")

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation | F.video_note)
async def handle_file(message: Message):
    if message.from_user.id not in upload_waiting or not upload_waiting[message.from_user.id]:
        return
    
    upload_waiting[message.from_user.id] = False
    msg = await message.answer("⏳ <b>Processing...</b>", parse_mode=ParseMode.HTML)
    
    try:
        # Get file
        if message.photo:
            file_id = message.photo[-1].file_id
            ftype = "Photo"
        elif message.video:
            file_id = message.video.file_id
            ftype = "Video"
        elif message.document:
            file_id = message.document.file_id
            ftype = "Document"
        elif message.audio:
            file_id = message.audio.file_id
            ftype = "Audio"
        elif message.voice:
            file_id = message.voice.file_id
            ftype = "Voice"
        elif message.sticker:
            file_id = message.sticker.file_id
            ftype = "Sticker"
        elif message.animation:
            file_id = message.animation.file_id
            ftype = "GIF"
        elif message.video_note:
            file_id = message.video_note.file_id
            ftype = "Video Note"
        else:
            await msg.edit_text("❌ Unsupported file")
            return
        
        # Download
        await msg.edit_text("📥 Downloading...")
        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
        
        if r.status_code != 200:
            await msg.edit_text("❌ Download failed")
            return
        
        # Upload
        await msg.edit_text("☁️ Uploading...")
        filename = file.file_path.split('/')[-1] if '/' in file.file_path else f"file_{file_id}"
        result = await upload_file(r.content, filename)
        
        if not result['success']:
            await msg.edit_text(f"❌ Upload failed")
            return
        
        # Save to DB
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute('UPDATE users SET uploads = uploads + 1 WHERE user_id = ?', (message.from_user.id,))
        c.execute('INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)',
                  (message.from_user.id, datetime.now().isoformat(), result['url'], ftype, len(r.content)))
        conn.commit()
        conn.close()
        
        # Send result
        size = len(r.content)
        size_text = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/(1024*1024):.1f} MB"
        
        await msg.edit_text(
            f"✅ <b>Upload Complete!</b>\n\n"
            f"📁 Type: {ftype}\n"
            f"💾 Size: {size_text}\n"
            f"👤 By: {message.from_user.first_name}\n\n"
            f"🔗 <b>Link:</b>\n<code>{result['url']}</code>\n\n"
            f"📤 Shareable link • No expiry",
            parse_mode=ParseMode.HTML
        )
        log_command(message.from_user.id, "upload", True)
        
    except Exception as e:
        await msg.edit_text("❌ Error uploading file")
        log_error(message.from_user.id, "upload", e)

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    if message.from_user.id in upload_waiting:
        upload_waiting[message.from_user.id] = False
        await message.answer("❌ Upload cancelled")
    log_command(message.from_user.id, "cancel")

# ========== GAMES ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    update_user(message.from_user)
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ <b>Usage:</b> <code>/wish your wish</code>", parse_mode=ParseMode.HTML)
        return
    
    msg = await message.answer("🔮 Thinking...")
    await asyncio.sleep(0.5)
    
    luck = random.randint(1, 100)
    stars = "⭐" * (luck // 20)
    
    if luck >= 90: res = "🎊 EXCELLENT!"
    elif luck >= 70: res = "😊 VERY GOOD!"
    elif luck >= 50: res = "👍 GOOD!"
    elif luck >= 30: res = "🤔 AVERAGE"
    else: res = "😟 LOW"
    
    await msg.edit_text(
        f"✨ <b>Wish Result</b>\n\n"
        f"📜 {args[1]}\n"
        f"🎰 Luck: {stars} {luck}%\n"
        f"📊 {res}", 
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "wish")

@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    update_user(message.from_user)
    msg = await message.answer("🎲 Rolling...")
    
    faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    for f in faces:
        await msg.edit_text(f"🎲 {f}")
        await asyncio.sleep(0.1)
    
    roll = random.randint(1, 6)
    await msg.edit_text(f"🎲 <b>You rolled: {faces[roll-1]} ({roll})</b>", parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, "dice")

@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    update_user(message.from_user)
    msg = await message.answer("🪙 Flipping...")
    await asyncio.sleep(0.5)
    
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}</b>", parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, "flip")

# ========== PROFILE ==========
@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    update_user(message.from_user)
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute('SELECT uploads, commands, joined_date FROM users WHERE user_id = ?', (message.from_user.id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        uploads, cmds, joined = row
        try:
            join_date = datetime.fromisoformat(joined).strftime("%d %b %Y")
        except:
            join_date = "Recent"
    else:
        uploads = cmds = 0
        join_date = "Today"
    
    await message.answer(
        f"👤 <b>Profile: {message.from_user.first_name}</b>\n\n"
        f"📁 Uploads: {uploads}\n"
        f"🔧 Commands: {cmds}\n"
        f"📅 Joined: {join_date}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n\n"
        f"💡 Use /link to upload files",
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "profile")

# ========== ADMIN COMMANDS ==========
@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("🚫 Admin only")
        return
    
    start = time.time()
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    users = c.fetchone()[0] or 0
    c.execute('SELECT COUNT(*) FROM uploads')
    uploads = c.fetchone()[0] or 0
    conn.close()
    
    ping = (time.time() - start) * 1000
    await message.answer(
        f"🏓 <b>PONG!</b>\n"
        f"⚡ {ping:.0f}ms\n"
        f"👥 {users} users\n"
        f"📁 {uploads} uploads\n"
        f"🕒 {int(time.time() - start_time)}s uptime", 
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "ping")

@dp.message(Command("logs"))
async def logs_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    days = 7 if len(args) < 2 or not args[1].isdigit() else min(int(args[1]), 30)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Get command logs
    c.execute('SELECT timestamp, user_id, command, success FROM logs WHERE DATE(timestamp) >= DATE(?, ?) ORDER BY timestamp DESC LIMIT 500', 
              (datetime.now().isoformat(), f'-{days} days'))
    logs = c.fetchall()
    
    # Get error logs
    c.execute('SELECT timestamp, user_id, command, error FROM errors WHERE DATE(timestamp) >= DATE(?, ?) ORDER BY timestamp DESC LIMIT 200',
              (datetime.now().isoformat(), f'-{days} days'))
    errors = c.fetchall()
    
    conn.close()
    
    # Create log file
    content = f"📊 BOT LOGS - Last {days} days\n{'='*40}\n\n"
    content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    content += f"Commands: {len(logs)}\nErrors: {len(errors)}\n\n"
    
    content += "📝 COMMAND LOGS:\n"
    for ts, uid, cmd, succ in logs[:100]:  # Limit to 100
        time_str = datetime.fromisoformat(ts).strftime("%m/%d %H:%M")
        status = "✅" if succ else "❌"
        content += f"[{time_str}] {uid} {status} {cmd}\n"
    
    content += "\n\n❌ ERROR LOGS:\n"
    for ts, uid, cmd, err in errors[:50]:  # Limit to 50
        time_str = datetime.fromisoformat(ts).strftime("%m/%d %H:%M")
        content += f"[{time_str}] {uid} {cmd}: {err[:80]}\n"
    
    # Save and send
    filename = f"temp/logs_{int(time.time())}.txt"
    Path("temp").mkdir(exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    await message.answer_document(
        FSInputFile(filename),
        caption=f"📁 Logs ({days} days)"
    )
    
    try:
        os.remove(filename)
    except:
        pass
    
    log_command(message.from_user.id, f"logs {days}")

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM users')
    users = c.fetchone()[0] or 0
    c.execute('SELECT COUNT(*) FROM uploads')
    uploads = c.fetchone()[0] or 0
    c.execute('SELECT COUNT(*) FROM logs WHERE DATE(timestamp) = DATE("now")')
    today_cmds = c.fetchone()[0] or 0
    c.execute('SELECT COUNT(*) FROM users WHERE DATE(last_active) = DATE("now")')
    active = c.fetchone()[0] or 0
    
    conn.close()
    
    await message.answer(
        f"📊 <b>Bot Stats</b>\n\n"
        f"👥 Users: {users}\n"
        f"📁 Uploads: {uploads}\n"
        f"🔧 Commands today: {today_cmds}\n"
        f"⚡ Active today: {active}\n"
        f"🕒 Uptime: {int(time.time() - start_time)}s\n"
        f"🔧 Status: {'🟢 ON' if bot_active else '🔴 OFF'}", 
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "stats")

@dp.message(Command("users"))
async def users_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute('SELECT user_id, first_name, username, uploads, commands FROM users ORDER BY joined_date DESC LIMIT 100')
    users = c.fetchall()
    conn.close()
    
    content = "👥 USERS LIST\n"
    for uid, name, uname, up, cmds in users:
        un = f"@{uname}" if uname else "No username"
        content += f"{uid} | {name} | {un} | 📁{up} | 🔧{cmds}\n"
    
    filename = f"temp/users_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    await message.answer_document(FSInputFile(filename), caption="📁 User list")
    
    try:
        os.remove(filename)
    except:
        pass
    
    log_command(message.from_user.id, "users")

@dp.message(Command("pro"))
async def pro_cmd(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Usage: /pro user_id")
        return
    
    target = int(args[1])
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (target,))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ User {target} is now admin")
    log_command(message.from_user.id, f"pro {target}")

@dp.message(Command("toggle"))
async def toggle_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    global bot_active
    bot_active = not bot_active
    status = "🟢 ON" if bot_active else "🔴 OFF"
    await message.answer(f"✅ Bot is now {status}")
    log_command(message.from_user.id, f"toggle {bot_active}")

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    broadcast_state[message.from_user.id] = True
    await message.answer(
        "📢 <b>Send broadcast message</b>\n"
        "• Text, photo, video, document\n"
        "• Include caption for media\n"
        "❌ /cancel to stop", 
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, "broadcast_start")

@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    with open("data/restart.json", "w") as f:
        json.dump({"time": datetime.now().isoformat(), "user": message.from_user.id}, f)
    
    await message.answer("🔄 Restarting bot...")
    log_command(message.from_user.id, "restart")
    import sys
    sys.exit(0)

# ========== BROADCAST HANDLER ==========
@dp.message()
async def handle_broadcast(message: Message):
    if message.from_user.id in broadcast_state and broadcast_state[message.from_user.id]:
        broadcast_state[message.from_user.id] = False
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute('SELECT user_id FROM users WHERE is_admin = 0')
        users = [row[0] for row in c.fetchall()]
        conn.close()
        
        total = len(users)
        status = await message.answer(f"📤 Sending to {total} users...")
        
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
        
        await status.edit_text(f"✅ Sent to {success}/{total} users")
        log_command(message.from_user.id, f"broadcast_sent {success}/{total}")

# ========== START ==========
async def main():
    print("🚀 Bot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    Path("data").mkdir(exist_ok=True)
    Path("temp").mkdir(exist_ok=True)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped")
    except Exception as e:
        print(f"Error: {e}")
