import os
import asyncio
import time
import random
import sqlite3
import json
import httpx
import shutil
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder

print("🤖 PRO BOT STARTING...")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"

# TEMPEST CULT CONFIG
TEMPEST_LEADER = 6211708776  # @dont_try_to_copy_mee
TEMPEST_VICE1 = 6581129741   # @Bablu_is_op
TEMPEST_VICE2 = 6108185460   # @Nocis_Creed (Keny)
DEVELOPER_ID = 6108185460    # Kenneth (hidden developer)
TEMPEST_PICS = {
    "join": "https://files.catbox.moe/qjmgcg.jpg",
    "unity": "https://files.catbox.moe/k07i6j.jpg",
    "initiated": "https://files.catbox.moe/d9qnw5.jpg"
}

# Create directories
Path("data").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True)
Path("backups").mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True
upload_waiting = {}
broadcast_state = {}
pending_joins = {}
cult_animations = {}

# ========== DATABASE ==========
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
        is_admin INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        cult_status TEXT DEFAULT 'none',
        cult_rank TEXT DEFAULT 'none',
        cult_join_date TEXT,
        sacrifices INTEGER DEFAULT 0,
        cult_name TEXT,
        is_cult_approved INTEGER DEFAULT 0
    )''')
    
    # Groups table
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        group_id INTEGER PRIMARY KEY,
        title TEXT,
        username TEXT,
        joined_date TEXT,
        last_active TEXT,
        messages INTEGER DEFAULT 0,
        commands INTEGER DEFAULT 0
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
        chat_type TEXT,
        command TEXT,
        success INTEGER
    )''')
    
    # Error logs table
    c.execute('''CREATE TABLE IF NOT EXISTS error_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user_id INTEGER,
        command TEXT,
        error TEXT,
        traceback TEXT
    )''')
    
    # Wishes table
    c.execute('''CREATE TABLE IF NOT EXISTS wishes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,
        wish_text TEXT,
        luck INTEGER
    )''')
    
    # Cult Messages table (for broadcast replies)
    c.execute('''CREATE TABLE IF NOT EXISTS cult_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        user_id INTEGER,
        original_sender INTEGER,
        chat_id INTEGER,
        text TEXT,
        timestamp TEXT,
        replied INTEGER DEFAULT 0
    )''')
    
    # Add owner as admin
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    # Add cult leaders
    cult_leaders = [
        (TEMPEST_LEADER, "Ravijah", "Supreme Leader", 1),
        (TEMPEST_VICE1, "Bablu", "Vice Chancellor", 1),
        (TEMPEST_VICE2, "Keny", "Vice Chancellor", 1)
    ]
    
    for leader_id, name, rank, approved in cult_leaders:
        c.execute('''INSERT OR IGNORE INTO users 
                    (user_id, first_name, joined_date, last_active, cult_status, cult_rank, cult_name, is_cult_approved) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                 (leader_id, name, datetime.now().isoformat(), datetime.now().isoformat(), "leader", rank, name, approved))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== HELPER FUNCTIONS ==========
def log_command(user_id, chat_type, command, success=True):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO command_logs (timestamp, user_id, chat_type, command, success) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().isoformat(), user_id, chat_type, command, 1 if success else 0))
    c.execute("UPDATE users SET commands = commands + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def log_error(user_id, command, error):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    error_str = str(error)[:200]
    traceback_str = traceback.format_exc()[:500]
    c.execute("INSERT INTO error_logs (timestamp, user_id, command, error, traceback) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().isoformat(), user_id, command, error_str, traceback_str))
    conn.commit()
    conn.close()

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
    except Exception as e:
        print(f"Error updating user: {e}")

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
    except Exception as e:
        print(f"Error updating group: {e}")

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

async def is_cult_leader(user_id):
    return user_id in [TEMPEST_LEADER, TEMPEST_VICE1, TEMPEST_VICE2]

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

# ========== TEMPEST CULT FUNCTIONS ==========
async def get_cult_leaders_online():
    """Check which leaders are online (active in last 5 minutes)"""
    online_leaders = []
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    leaders = [TEMPEST_LEADER, TEMPEST_VICE1, TEMPEST_VICE2]
    five_min_ago = (datetime.now() - timedelta(minutes=5)).isoformat()
    
    for leader_id in leaders:
        c.execute("SELECT first_name FROM users WHERE user_id = ? AND last_active >= ?", 
                 (leader_id, five_min_ago))
        if c.fetchone():
            online_leaders.append(leader_id)
    
    conn.close()
    return online_leaders

async def get_cult_members():
    """Get all cult members with their real names"""
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT first_name, cult_rank, sacrifices FROM users WHERE cult_status != 'none' AND is_cult_approved = 1 ORDER BY sacrifices DESC")
    members = c.fetchall()
    conn.close()
    return members

async def add_cult_member(user_id, name, sacrifice):
    """Add user to cult"""
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute('''UPDATE users SET 
                cult_status = 'member', 
                cult_rank = 'Initiate',
                cult_join_date = ?,
                sacrifices = sacrifices + 1,
                cult_name = ?,
                is_cult_approved = 1
                WHERE user_id = ?''',
             (datetime.now().isoformat(), name, user_id))
    conn.commit()
    conn.close()

async def send_cult_tag_message(user_data):
    """Send tag message to cult leaders for approval"""
    tag_message = f"""
🌀 <b>TEMPEST INITIATION REQUEST</b>
━━━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>Initiate:</b> {user_data['name']}
🆔 <b>ID:</b> <code>{user_data['user_id']}</code>
💀 <b>Sacrifice:</b> {user_data.get('sacrifice', 'Unknown')}
🌪️ <b>Status:</b> Awaiting approval

━━━━━━━━━━━━━━━━━━━━━━━━
📜 <i>"A soul seeks entry to the eternal storm..."</i>
    """
    
    # Tag leaders
    leaders = [TEMPEST_LEADER, TEMPEST_VICE1, TEMPEST_VICE2]
    for leader_id in leaders:
        try:
            await bot.send_message(
                chat_id=leader_id,
                text=tag_message,
                parse_mode=ParseMode.HTML
            )
        except:
            pass  # Leader might have blocked bot

# ========== ANIMATION FUNCTIONS ==========
async def animate_story(message: Message, user_data: dict):
    """Animate the epic Tempest story with rich visuals"""
    try:
        # CHAPTER 1: The Gathering Storm
        frames = [
            "🌌 <b>CHAPTER 1: WHISPERS IN THE VOID</b>\n\n<pre>█▓▒░░░░░░░░░░░░░░ 5%</pre>\n⚡ Lightning cracks across dead skies...\n🌑 Shadows stir in forgotten realms...",
            "🌌 <b>CHAPTER 1: WHISPERS IN THE VOID</b>\n\n<pre>██▓▒░░░░░░░░░░░░░ 15%</pre>\n🌀 A prophecy awakens from cosmic dust...\n💫 Stars realign, fate trembles...",
            "🌌 <b>CHAPTER 1: WHISPERS IN THE VOID</b>\n\n<pre>████▓▒░░░░░░░░░░░ 25%</pre>\n👁️ Ravijah opens eyes charged with storm...\n'<i>The Tempest calls... I answer.</i>'",
            "🌌 <b>CHAPTER 1: WHISPERS IN THE VOID</b>\n\n<pre>██████▓▒░░░░░░░░░ 35%</pre>\n⚔️ Bablu emerges from Glass City ruins...\n🗡️ Sword dripping with Shard Lord blood...",
            "🌌 <b>CHAPTER 1: WHISPERS IN THE VOID</b>\n\n<pre>████████▓▒░░░░░░░ 45%</pre>\n👤 Keny materializes from shadows...\n'<i>Silence speaks louder than thunder.</i>'",
            "🌌 <b>CHAPTER 1: WHISPERS IN THE VOID</b>\n\n<pre>██████████▓▒░░░░░ 55%</pre>\n❤️‍🔥 Elara sings, voice weaving light...\n🎶 Her melody calms Ravijah's storm...",
            "🌌 <b>CHAPTER 1: WHISPERS IN THE VOID</b>\n\n<pre>████████████▓▒░░░ 65%</pre>\n💔 Kaelen watches with jealous eyes...\n🩸 '<i>Why does she love the storm, not me?</i>'",
            "🌌 <b>CHAPTER 1: WHISPERS IN THE VOID</b>\n\n<pre>██████████████▓▒░ 75%</pre>\n⚡ The Chronosphere pulses with power...\n⏳ Time bends, reality fractures...",
            "🌌 <b>CHAPTER 1: WHISPERS IN THE VOID</b>\n\n<pre>████████████████▓ 85%</pre>\n🌪️ Tempest forms around the three...\n🌀 '<i>We are the storm. We are the void.</i>'",
            "🌌 <b>CHAPTER 1: WHISPERS IN THE VOID</b>\n\n<pre>█████████████████ 100%</pre>\n✅ CHAPTER COMPLETE!\n⚡ Proceeding to Chapter 2..."
        ]
        
        msg = await message.answer("🌀 <b>PREPARING EPIC NARRATION...</b>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)
        
        for frame in frames:
            await msg.edit_text(frame, parse_mode=ParseMode.HTML)
            await asyncio.sleep(3.5)
        
        # CHAPTER 2: Blood Moon War
        frames2 = [
            "🔪 <b>CHAPTER 2: BLOOD MOON WAR</b>\n\n" + "█"*5 + "▒"*15 + " 25%\n🌕 Moon turns crimson...\n⚔️ '<b>BABLU:</b> They took the Glass City. We take their souls!'",
            "🔪 <b>CHAPTER 2: BLOOD MOON WAR</b>\n\n" + "█"*10 + "▒"*10 + " 50%\n🩸 Rivers run red with Shard blood...\n💥 '<b>RAVIJAH:</b> Feel my wrath, vermin! LIGHTNING STRIKE!'",
            "🔪 <b>CHAPTER 2: BLOOD MOON WAR</b>\n\n" + "█"*15 + "▒"*5 + " 75%\n👤 Keny assassinates Lord Verax...\n🗡️ '<b>KENY:</b> Silence is the deadliest weapon.'",
            "🔪 <b>CHAPTER 2: BLOOD MOON WAR</b>\n\n" + "█"*20 + " 100%\n🏆 Victory at Sundered Keep...\n🎖️ '<b>BABLU:</b> For the fallen! FOR THE TEMPEST!'"
        ]
        
        for frame in frames2:
            await msg.edit_text(frame, parse_mode=ParseMode.HTML)
            await asyncio.sleep(4)
        
        # CHAPTER 3: Love & Betrayal
        frames3 = [
            "❤️‍🔥 <b>CHAPTER 3: HEARTS & DAGGERS</b>\n\n🌸 Ravijah & Elara under twin moons...\n💌 '<b>ELARA:</b> Your storm frightens others... but not me.'",
            "❤️‍🔥 <b>CHAPTER 3: HEARTS & DAGGERS</b>\n\n👁️ Kaelen watches from shadows...\n😡 '<b>KAELEN:</b> She should be MINE! I'll destroy him...'",
            "❤️‍🔥 <b>CHAPTER 3: HEARTS & DAGGERS</b>\n\n🎪 Festival of Flames turns to chaos...\n🔥 '<b>KAELEN:</b> NOW, BROTHER! KILL THE STORM-BORN!'",
            "❤️‍🔥 <b>CHAPTER 3: HEARTS & DAGGERS</b>\n\n💔 Elara takes the poisoned blade...\n🩸 '<b>ELARA:</b> Live... for both of us...' *dies*"
        ]
        
        for frame in frames3:
            await msg.edit_text(frame, parse_mode=ParseMode.HTML)
            await asyncio.sleep(4)
        
        # CHAPTER 4: The Great Tempest
        frames4 = [
            "🌪️ <b>CHAPTER 4: BIRTH OF THE TEMPEST</b>\n\n⚡ Ravijah's grief unleashes cataclysm...\n🌀 '<b>RAVIJAH:</b> LET THE WORLD BURN WITH ME!'",
            "🌪️ <b>CHAPTER 4: BIRTH OF THE TEMPEST</b>\n\n🌪️ Cities crumble, mountains shatter...\n💥 '<b>BABLU:</b> By the gods... his power!'",
            "🌪️ <b>CHAPTER 4: BIRTH OF THE TEMPEST</b>\n\n🤝 Bablu & Keny join the maelstrom...\n⚡ '<b>KENY:</b> We ride the storm together, brother.'",
            "🌪️ <b>CHAPTER 4: BIRTH OF THE TEMPEST</b>\n\n👑 The Tempest Cult is born...\n🌀 '<b>ALL THREE:</b> WE ARE THE ETERNAL STORM!'"
        ]
        
        for frame in frames4:
            await msg.edit_text(frame, parse_mode=ParseMode.HTML)
            await asyncio.sleep(4)
        
        # CHAPTER 5: Glory & Sacrifice
        frames5 = [
            "🏆 <b>CHAPTER 5: GLORY DAYS</b>\n\n🎖️ 300 years of conquest...\n⚔️ '<b>BABLU:</b> Another realm falls to our storm!'",
            "🏆 <b>CHAPTER 5: GLORY DAYS</b>\n\n💎 Crystal Empire surrenders...\n👑 '<b>RAVIJAH:</b> Kneel before the Tempest.'",
            "🏆 <b>CHAPTER 5: GLORY DAYS</b>\n\n🩸 Void Walkers exterminated...\n🗡️ '<b>KENY:</b> None escape the silent blade.'",
            "🏆 <b>CHAPTER 5: GLORY DAYS</b>\n\n🌟 Golden Age of Tempest begins...\n🌀 '<b>ALL:</b> WE ARE LEGEND! WE ARE ETERNAL!'"
        ]
        
        for frame in frames5:
            await msg.edit_text(frame, parse_mode=ParseMode.HTML)
            await asyncio.sleep(4)
        
        # CHAPTER 6: Modern Era
        frames6 = [
            "🕰️ <b>CHAPTER 6: ETERNAL WATCH</b>\n\n📡 Tempest monitors all realities...\n👁️ '<b>RAVIJAH:</b> The storm sees all, knows all.'",
            "🕰️ <b>CHAPTER 6: ETERNAL WATCH</b>\n\n🆕 New initiates join weekly...\n🌀 '<b>BABLU:</b> More souls to feed the tempest.'",
            "🕰️ <b>CHAPTER 6: ETERNAL WATCH</b>\n\n💀 Sacrifices strengthen the bond...\n⚡ '<b>KENY:</b> Blood is the currency of power.'",
            "🕰️ <b>CHAPTER 6: ETERNAL WATCH</b>\n\n🎭 And so the saga continues...\n🌪️ '<b>NARRATOR:</b> YOUR TURN TO WRITE HISTORY...'"
        ]
        
        for frame in frames6:
            await msg.edit_text(frame, parse_mode=ParseMode.HTML)
            await asyncio.sleep(4)
        
        return msg
        
    except Exception as e:
        print(f"Animation error: {e}")
        return None

# ========== ALL ORIGINAL COMMANDS ==========
# [KEEP ALL ORIGINAL COMMANDS EXACTLY AS BEFORE]
# ========== /START ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    update_user(message.from_user)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(message.chat)
    
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
    log_command(message.from_user.id, message.chat.type, "start")

# ========== /HELP ==========
@dp.message(Command("help"))
async def help_cmd(message: Message):
    update_user(message.from_user)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(message.chat)
    
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
<code>/stats</code> - Statistics with dead users/groups
<code>/users</code> - User list (.txt)

⚡ <b>Owner:</b>
<code>/pro [id]</code> - Make admin
<code>/toggle</code> - Toggle bot
<code>/broadcast</code> - Send to all
<code>/restart</code> - Restart bot
<code>/backup</code> - Database backup
<code>/emergency_stop</code> - Stop bot"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, message.chat.type, "help")

# ========== /DEV ========== (Hidden command)
@dp.message(Command("dev"))
async def dev_cmd(message: Message):
    update_user(message.from_user)
    
    dev_text = """👨‍💻 <b>DEVELOPER INFORMATION</b>
━━━━━━━━━━━━━━━━━━━━━━━━

🔧 <b>Bot Developer:</b> Kenneth
🆔 <b>User ID:</b> <code>6108185460</code>
📧 <b>Username:</b> @Nocis_Creed
🌪️ <b>Tempest Rank:</b> Vice Chancellor (Keny)

💻 <b>Bot Features:</b>
• File upload system
• Tempest Cult game
• Admin controls
• Database management

🔐 <b>Hidden Commands:</b>
• /dev - This message
• /Tempest_cult - Cult members
• /Tempest_join - Join cult

━━━━━━━━━━━━━━━━━━━━━━━━
⚡ <i>"Code is poetry, storm is power."</i>
🌀 Kenneth | Tempest Vice Chancellor"""
    
    await message.answer(dev_text, parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, message.chat.type, "dev")

# ========== /LINK ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("📁 <b>Upload files in private chat only</b>", parse_mode=ParseMode.HTML)
        return
    
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
    log_command(message.from_user.id, message.chat.type, "link")

# ========== HANDLE FILES ==========
@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation | F.video_note)
async def handle_file(message: Message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
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
        
        # If cult member, count as sacrifice
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user_id,))
        cult_status = c.fetchone()
        if cult_status and cult_status[0] != 'none':
            c.execute("UPDATE users SET sacrifices = sacrifices + 1 WHERE user_id = ?", (user_id,))
        
        c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)",
                 (user_id, datetime.now().isoformat(), result['url'], file_type, file_size))
        conn.commit()
        conn.close()
        
        # Send result
        size_kb = file_size / 1024
        size_mb = size_kb / 1024
        size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
        
        result_text = f"✅ <b>Upload Complete!</b>\n\n📁 <b>Type:</b> {file_type}\n💾 <b>Size:</b> {size_text}\n👤 <b>By:</b> {message.from_user.first_name}\n\n🔗 <b>Direct Link:</b>\n<code>{result['url']}</code>\n\n📤 Permanent link • No expiry • Share anywhere"
        
        # Add cult message if member
        if cult_status and cult_status[0] != 'none':
            result_text += f"\n\n🌀 <i>+1 sacrifice to the Tempest</i>"
        
        await msg.edit_text(result_text, parse_mode=ParseMode.HTML)
        log_command(user_id, message.chat.type, "upload", True)
        
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
    log_command(user_id, message.chat.type, "cancel")

# ========== /WISH ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    update_user(message.from_user)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(message.chat)
    
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
    log_command(message.from_user.id, message.chat.type, "wish")

# ========== /DICE ==========
@dp.message(Command("dice"))
async def dice_cmd(message: Message):
    update_user(message.from_user)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(message.chat)
    
    msg = await message.answer("🎲 <b>Rolling dice...</b>", parse_mode=ParseMode.HTML)
    
    # Animation
    faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    for i in range(6):
        await msg.edit_text(f"🎲 <b>Rolling...</b> {faces[i]}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.15)
    
    roll = random.randint(1, 6)
    await msg.edit_text(f"🎲 <b>You rolled: {faces[roll-1]} ({roll})</b>", parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, message.chat.type, "dice")

# ========== /FLIP ==========
@dp.message(Command("flip"))
async def flip_cmd(message: Message):
    update_user(message.from_user)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(message.chat)
    
    msg = await message.answer("🪙 <b>Flipping coin...</b>", parse_mode=ParseMode.HTML)
    
    # Animation
    for i in range(5):
        await msg.edit_text(f"🪙 <b>Flipping...</b> {'HEADS' if i % 2 == 0 else 'TAILS'}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}</b>", parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, message.chat.type, "flip")

# ========== /PROFILE ==========
@dp.message(Command("profile"))
async def profile_cmd(message: Message):
    update_user(message.from_user)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(message.chat)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Get user stats
    c.execute("SELECT uploads, commands, joined_date, cult_status, cult_rank, sacrifices FROM users WHERE user_id = ?", (message.from_user.id,))
    row = c.fetchone()
    
    if row:
        uploads, cmds, joined, cult_status, cult_rank, sacrifices = row
        # Count wishes
        c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (message.from_user.id,))
        wishes = c.fetchone()[0] or 0
        
        # Format join date
        try:
            join_date = datetime.fromisoformat(joined).strftime("%d %b %Y")
        except:
            join_date = "Recently"
    else:
        uploads = cmds = wishes = sacrifices = 0
        cult_status = "none"
        cult_rank = "None"
        join_date = "Today"
    
    conn.close()
    
    profile_text = f"""
👤 <b>PROFILE: {message.from_user.first_name}</b>
━━━━━━━━━━━━━━━━━━━━━━━━

📁 <b>Uploads:</b> {uploads}
✨ <b>Wishes:</b> {wishes}
🔧 <b>Commands:</b> {cmds}
📅 <b>Joined:</b> {join_date}
🆔 <b>ID:</b> <code>{message.from_user.id}</code>
"""
    
    if cult_status != "none":
        profile_text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🌪️ <b>TEMPEST CULT</b>
👑 <b>Rank:</b> {cult_rank}
⚔️ <b>Sacrifices:</b> {sacrifices}
🔮 <b>Status:</b> {cult_status.title()}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    profile_text += "\n💡 <b>Next:</b> Try /link to upload files"
    
    await message.answer(profile_text, parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, message.chat.type, "profile")

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
    log_command(message.from_user.id, message.chat.type, "ping")

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
    
    # Calculate date threshold
    threshold_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    # Get command logs
    c.execute("SELECT timestamp, user_id, chat_type, command, success FROM command_logs WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 500", 
              (threshold_date,))
    cmd_logs = c.fetchall()
    
    # Get error logs
    c.execute("SELECT timestamp, user_id, command, error FROM error_logs WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 200", 
              (threshold_date,))
    err_logs = c.fetchall()
    
    conn.close()
    
    # Create log file
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
    
    log_command(message.from_user.id, message.chat.type, f"logs {days}")

# ========== /STATS ==========
@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # Basic stats
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM groups")
    total_groups = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM uploads")
    total_uploads = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM wishes")
    total_wishes = c.fetchone()[0] or 0
    
    # Active users (last 7 days)
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute("SELECT COUNT(*) FROM users WHERE last_active >= ?", (week_ago,))
    active_users = c.fetchone()[0] or 0
    
    # Dead users (inactive 30+ days)
    month_ago = (datetime.now() - timedelta(days=30)).isoformat()
    c.execute("SELECT COUNT(*) FROM users WHERE last_active < ?", (month_ago,))
    dead_users = c.fetchone()[0] or 0
    
    # Active groups (last 7 days)
    c.execute("SELECT COUNT(*) FROM groups WHERE last_active >= ?", (week_ago,))
    active_groups = c.fetchone()[0] or 0
    
    # Dead groups (inactive 30+ days)
    c.execute("SELECT COUNT(*) FROM groups WHERE last_active < ?", (month_ago,))
    dead_groups = c.fetchone()[0] or 0
    
    # Today's activity
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM command_logs WHERE DATE(timestamp) = DATE(?)", (today,))
    today_commands = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(DISTINCT user_id) FROM command_logs WHERE DATE(timestamp) = DATE(?)", (today,))
    active_today = c.fetchone()[0] or 0
    
    conn.close()
    
    # Calculate percentages
    user_percent = (active_users / total_users * 100) if total_users > 0 else 0
    group_percent = (active_groups / total_groups * 100) if total_groups > 0 else 0
    dead_user_percent = (dead_users / total_users * 100) if total_users > 0 else 0
    
    stats_text = f"""
📊 <b>COMPLETE BOT STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👥 <b>USER STATS:</b>
• Total Users: {total_users}
• Active Users (7 days): {active_users}
• Dead Users (30+ days): {dead_users}
• Active Today: {active_today}

👥 <b>GROUP STATS:</b>
• Total Groups: {total_groups}
• Active Groups (7 days): {active_groups}
• Dead Groups (30+ days): {dead_groups}

📁 <b>UPLOAD STATS:</b>
• Total Uploads: {total_uploads}
• Total Wishes: {total_wishes}

⚡ <b>TODAY'S ACTIVITY:</b>
• Commands: {today_commands}
• Active Users: {active_today}

🕒 <b>SYSTEM:</b>
• Uptime: {int(time.time() - start_time)}s
• Status: {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}
• Host: Railway

━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>PERCENTAGES:</b>
• Active Users: {user_percent:.1f}%
• Active Groups: {group_percent:.1f}%
• Dead Users: {dead_user_percent:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, message.chat.type, "stats")

# ========== /USERS ==========
@dp.message(Command("users"))
async def users_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, uploads, commands, last_active FROM users ORDER BY joined_date DESC LIMIT 100")
    users = c.fetchall()
    conn.close()
    
    user_list = "👥 USER LIST (Last 100)\n" + "="*50 + "\n\n"
    for uid, name, uname, up, cmds, last_active in users:
        un = f"@{uname}" if uname else "No username"
        
        # Calculate days since last active
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
    
    log_command(message.from_user.id, message.chat.type, "users")

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
    log_command(message.from_user.id, message.chat.type, f"pro {target_id}")

# ========== /TOGGLE ==========
@dp.message(Command("toggle"))
async def toggle_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    global bot_active
    bot_active = not bot_active
    status = "🟢 ACTIVE" if bot_active else "🔴 PAUSED"
    await message.answer(f"✅ Bot is now {status}")
    log_command(message.from_user.id, message.chat.type, f"toggle {bot_active}")

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
    log_command(message.from_user.id, message.chat.type, "broadcast_start")

# ========== /BROADCAST_GC ==========
@dp.message(Command("broadcast_gc"))
async def broadcast_gc_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    broadcast_state[message.from_user.id] = "group"
    await message.answer(
        "📢 <b>Send group broadcast message now:</b>\n"
        "• Will send to all groups\n"
        "• Text message only\n"
        "• Groups only (not private)\n\n"
        "⚠️ <b>Next message will be broadcasted to groups</b>\n"
        "❌ <code>/cancel</code> to abort",
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, message.chat.type, "broadcast_gc_start")

# ========== /BACKUP ==========
@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    if message.from_user.id != OWNER_ID:
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
        await message.answer(f"❌ Backup failed: {str(e)}")
        log_error(message.from_user.id, "backup", e)
    
    log_command(message.from_user.id, message.chat.type, "backup")

# ========== /RESTART ==========
@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    await message.answer("🔄 <b>Bot restart initiated...</b>\n\nNote: On Railway, the bot auto-restarts when needed.", parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, message.chat.type, "restart")
    print("⚠️ Restart command received - continuing operation")

# ========== /EMERGENCY_STOP ==========
@dp.message(Command("emergency_stop"))
async def emergency_stop(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    global bot_active
    bot_active = False
    
    await message.answer("🛑 <b>BOT EMERGENCY STOPPED!</b>", parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, message.chat.type, "emergency_stop")

# ========== TEMPEST CULT COMMANDS ==========

# ========== /Tempest_cult ==========
@dp.message(Command("Tempest_cult"))
async def tempest_cult_cmd(message: Message):
    update_user(message.from_user)
    
    # Check if in group
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("🌀 <b>Tempest Cult commands work in private chat only</b>", parse_mode=ParseMode.HTML)
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT first_name, cult_rank, sacrifices FROM users WHERE cult_status != 'none' AND is_cult_approved = 1 ORDER BY sacrifices DESC, cult_rank")
    members = c.fetchall()
    conn.close()
    
    cult_text = "🌪️ <b>TEMPEST CULT MEMBERS</b>\n"
    cult_text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    leader_shown = False
    for name, rank, sacrifices in members:
        if rank in ["Supreme Leader", "Vice Chancellor"] and not leader_shown:
            cult_text += "👑 <b>HIGH COUNCIL:</b>\n"
            leader_shown = True
        
        if rank == "Supreme Leader":
            cult_text += f"👑 <b>{name}</b> - {rank}\n"
        elif rank == "Vice Chancellor":
            cult_text += f"⚔️ <b>{name}</b> - {rank}\n"
        else:
            star_emoji = "⭐" * (min(sacrifices, 5))
            cult_text += f"🌀 {name} - {rank} {star_emoji} ({sacrifices} sacrifices)\n"
    
    cult_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    cult_text += "📜 <i>Whispers in the storm... secrets await...</i>\n"
    cult_text += "🔮 Join with /Tempest_join"
    
    await message.answer(cult_text, parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, message.chat.type, "tempest_cult")

# ========== /Tempest_join ==========
@dp.message(Command("Tempest_join"))
async def tempest_join_cmd(message: Message):
    update_user(message.from_user)
    
    # Check if in group
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.answer("🌀 <b>Tempest initiation works in private chat only</b>", parse_mode=ParseMode.HTML)
        return
    
    # Check if already in cult
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (message.from_user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        await message.answer("🌀 <b>You are already part of the Tempest!</b>\n\nUse /Tempest_cult to see members", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    conn.close()
    
    # Start initiation
    pending_joins[message.from_user.id] = {
        "name": message.from_user.first_name,
        "user_id": message.from_user.id,
        "step": 1
    }
    
    # Send first image
    await message.answer_photo(
        photo=TEMPEST_PICS["join"],
        caption="🌪️ <b>TEMPEST INITIATION BEGINS...</b>\n\n"
               "⚡ The storm calls your name...\n"
               "🌩️ Are you ready to sacrifice?",
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(2)
    
    # Show sacrifices as text with numbered buttons
    sacrifices_text = """💀 <b>WHAT DO YOU SACRIFICE TO THE STORM?</b>

Choose your offering... this cannot be undone!
The Tempest demands a price for power...

<b>Available Sacrifices:</b>
1. 🩸 Your Firstborn's Eternal Soul
2. 💎 The Diamond Heart of Atlantis
3. 📜 Your Complete Internet History
4. 🎮 Your Legendary Gaming Account
5. 📱 Your Social Media Presence
6. 🍕 Your Ability to Taste Pizza
7. 🎵 Your Favorite Music Forever
8. 😴 Your Dreams for 100 Years
9. 📚 Your Knowledge of Memes
10. 👻 Your Shadow & Reflection

<i>Choose wisely... the storm remembers...</i>"""
    
    keyboard = InlineKeyboardBuilder()
    for i in range(1, 11):
        keyboard.add(InlineKeyboardButton(text=str(i), callback_data=f"sacrifice_{i}"))
    keyboard.add(InlineKeyboardButton(text="🚫 CANCEL", callback_data="sacrifice_cancel"))
    keyboard.adjust(5, 5, 1)
    
    await message.answer(
        sacrifices_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.as_markup()
    )
    
    log_command(message.from_user.id, message.chat.type, "tempest_join_start")

# ========== SACRIFICE CALLBACK ==========
@dp.callback_query(F.data.startswith("sacrifice_"))
async def handle_sacrifice(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in pending_joins:
        await callback.answer("❌ Initiation expired!", show_alert=True)
        return
    
    if callback.data == "sacrifice_cancel":
        del pending_joins[user_id]
        await callback.message.edit_text(
            "🌪️ <b>THE STORM REJECTS YOU!</b>\n\n"
            "🌀 Cowardice has no place in the Tempest.\n"
            "⚡ Maybe next lifetime... if you're brave enough.",
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return
    
    # Map sacrifice numbers to descriptions
    sacrifices_map = {
        "1": "🩸 Firstborn's Eternal Soul",
        "2": "💎 Diamond Heart of Atlantis",
        "3": "📜 Complete Internet History",
        "4": "🎮 Legendary Gaming Account",
        "5": "📱 Social Media Presence",
        "6": "🍕 Ability to Taste Pizza",
        "7": "🎵 Favorite Music Forever",
        "8": "😴 Dreams for 100 Years",
        "9": "📚 Knowledge of Memes",
        "10": "👻 Shadow & Reflection"
    }
    
    sacrifice_num = callback.data.split("_")[1]
    sacrifice = sacrifices_map.get(sacrifice_num, "Unknown Sacrifice")
    
    pending_joins[user_id]["sacrifice"] = sacrifice
    pending_joins[user_id]["step"] = 2
    
    await callback.message.edit_text(
        f"⚡ <b>SACRIFICE ACCEPTED!</b>\n\n"
        f"🌀 You offer: {sacrifice}\n"
        f"🌩️ The Tempest hungers for more...",
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(2)
    
    # Send second image
    await callback.message.answer_photo(
        photo=TEMPEST_PICS["unity"],
        caption="🌀 <b>THE STORM GATHERS...</b>\n\n"
               "⚡ Your essence merges with the tempest\n"
               "🌪️ The initiation continues...",
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(3)
    
    # Start the epic animation
    story_msg = await animate_story(callback.message, pending_joins[user_id])
    
    if story_msg:
        await asyncio.sleep(3)
        
        # Send third image
        await story_msg.answer_photo(
            photo=TEMPEST_PICS["initiated"],
            caption="🌀 <b>EPIC COMPLETE!</b>\n\n"
                   "⚡ You have witnessed the Tempest Saga\n"
                   "🌩️ Now, Council approval awaits...",
            parse_mode=ParseMode.HTML
        )
        
        await asyncio.sleep(2)
        
        # Tag leaders for approval
        await send_cult_tag_message(pending_joins[user_id])
        
        # Create approval buttons for online leaders
        online_leaders = await get_cult_leaders_online()
        
        if online_leaders:
            keyboard = InlineKeyboardBuilder()
            for leader_id in online_leaders:
                if leader_id == TEMPEST_LEADER:
                    name = "Ravijah 👑"
                elif leader_id == TEMPEST_VICE1:
                    name = "Bablu ⚔️"
                elif leader_id == TEMPEST_VICE2:
                    name = "Keny 🌩️"
                else:
                    continue
                
                keyboard.add(InlineKeyboardButton(
                    text=f"Approve with {name}",
                    callback_data=f"approve_{leader_id}_{user_id}"
                ))
            
            keyboard.adjust(1)
            
            await callback.message.answer(
                "👑 <b>AWAITING COUNCIL APPROVAL</b>\n\n"
                f"🌀 <b>Initiate:</b> {pending_joins[user_id]['name']}\n"
                f"⚡ <b>Sacrifice:</b> {sacrifice}\n\n"
                "🌪️ The Tempest Council has been notified!\n"
                "Choose a leader currently online:",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard.as_markup()
            )
        else:
            # Auto-approve if no leaders online
            await auto_approve_join(user_id, callback.message)
    
    await callback.answer()

async def auto_approve_join(user_id: int, message: Message):
    """Auto-approve join when no leaders are online"""
    if user_id not in pending_joins:
        return
    
    user_data = pending_joins[user_id]
    
    # Add to cult
    await add_cult_member(user_id, user_data['name'], user_data.get('sacrifice', 'Unknown'))
    
    # Send approval message
    approval_text = f"""
🌀 <b>INITIATION COMPLETE!</b>
━━━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>Welcome, {user_data['name']}!</b>
🌩️ <b>Rank:</b> Tempest Initiate
💀 <b>Sacrifice:</b> {user_data.get('sacrifice', 'Unknown')}

━━━━━━━━━━━━━━━━━━━━━━━━
📜 <b>THE COUNCIL SPEAKS:</b>
<i>"The storm accepts you in absence of the Council.
Prove your worth through service and sacrifice.
The Tempest watches all."</i>

━━━━━━━━━━━━━━━━━━━━━━━━
🔮 Use /Tempest_cult to see members
⚔️ Each upload = 1 sacrifice to the Tempest
🌪️ Your journey begins...
    """
    
    await message.answer(approval_text, parse_mode=ParseMode.HTML)
    
    # Cleanup
    if user_id in pending_joins:
        del pending_joins[user_id]

# ========== APPROVAL CALLBACK ==========
@dp.callback_query(F.data.startswith("approve_"))
async def handle_approval(callback: CallbackQuery):
    try:
        # Format: approve_leaderId_userId
        parts = callback.data.split("_")
        if len(parts) != 3:
            await callback.answer("❌ Invalid approval!", show_alert=True)
            return
        
        leader_id = int(parts[1])
        user_id = int(parts[2])
        
        # Check if callback is from a leader
        if callback.from_user.id not in [TEMPEST_LEADER, TEMPEST_VICE1, TEMPEST_VICE2]:
            await callback.answer("🚫 Only Tempest Leaders can approve!", show_alert=True)
            return
        
        if user_id not in pending_joins:
            await callback.answer("❌ Initiation expired!", show_alert=True)
            return
        
        user_data = pending_joins[user_id]
        
        # Get leader name
        if leader_id == TEMPEST_LEADER:
            leader_name = "Supreme Leader Ravijah 👑"
        elif leader_id == TEMPEST_VICE1:
            leader_name = "Vice Chancellor Bablu ⚔️"
        elif leader_id == TEMPEST_VICE2:
            leader_name = "Vice Chancellor Keny 🌩️"
        else:
            leader_name = "The Council"
        
        # Add to cult
        await add_cult_member(user_id, user_data['name'], user_data.get('sacrifice', 'Unknown'))
        
        # Send approval message to initiate
        approval_text = f"""
🌀 <b>INITIATION COMPLETE!</b>
━━━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>Welcome, {user_data['name']}!</b>
🌩️ <b>Approved by:</b> {leader_name}
💀 <b>Sacrifice:</b> {user_data.get('sacrifice', 'Unknown')}
👑 <b>Rank:</b> Tempest Initiate

━━━━━━━━━━━━━━━━━━━━━━━━
📜 <b>COUNCIL DECREE:</b>
<i>"By the power of the Eternal Storm,
we welcome you to the Tempest Cult.
Your blood joins the whirlwind,
your soul fuels the thunder.
Serve well, sacrifice often,
and the storm shall reward you."</i>

━━━━━━━━━━━━━━━━━━━━━━━━
🔮 Use /Tempest_cult to see members
⚔️ Each upload = 1 sacrifice to the Tempest
🌪️ Glory or betrayal await your choices...
        """
        
        # Send to initiate
        try:
            await bot.send_message(
                chat_id=user_id,
                text=approval_text,
                parse_mode=ParseMode.HTML
            )
        except:
            pass  # User might have blocked bot
        
        # Update callback message
        await callback.message.edit_text(
            f"✅ <b>APPROVAL SENT!</b>\n\n"
            f"🌀 {user_data['name']} has been initiated\n"
            f"🌩️ By: {callback.from_user.first_name}\n"
            f"⚡ The Tempest grows stronger...",
            parse_mode=ParseMode.HTML
        )
        
        # Notify other leaders
        other_leaders = [TEMPEST_LEADER, TEMPEST_VICE1, TEMPEST_VICE2]
        other_leaders.remove(leader_id)
        
        for other_leader in other_leaders:
            try:
                await bot.send_message(
                    chat_id=other_leader,
                    text=f"🌪️ <b>NEW INITIATE APPROVED</b>\n\n"
                         f"🌀 <b>Initiate:</b> {user_data['name']}\n"
                         f"👑 <b>Approved by:</b> {callback.from_user.first_name}\n"
                         f"💀 <b>Sacrifice:</b> {user_data.get('sacrifice', 'Unknown')}\n"
                         f"⚡ The Tempest welcomes new blood...",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
        
        # Cleanup
        if user_id in pending_joins:
            del pending_joins[user_id]
        
        await callback.answer("✅ Initiate approved!", show_alert=True)
        
    except Exception as e:
        print(f"Approval error: {e}")
        await callback.answer("❌ Error processing approval!", show_alert=True)

# ========== HANDLE BROADCAST MESSAGES ==========
@dp.message()
async def handle_broadcast(message: Message):
    user_id = message.from_user.id
    
    # Handle regular broadcast
    if user_id in broadcast_state and broadcast_state[user_id] == True:
        broadcast_state[user_id] = False
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned = 0")
        users = [row[0] for row in c.fetchall()]
        conn.close()
        
        total = len(users)
        status_msg = await message.answer(f"📤 Sending to {total} users...")
        
        success = 0
        for uid in users:
            try:
                if message.text:
                    sent_msg = await bot.send_message(uid, f"📢 {message.text}")
                    # Store message ID for replies
                    conn = sqlite3.connect("data/bot.db")
                    c = conn.cursor()
                    c.execute('''INSERT INTO cult_messages 
                                (message_id, user_id, original_sender, chat_id, text, timestamp) 
                                VALUES (?, ?, ?, ?, ?, ?)''',
                             (sent_msg.message_id, uid, user_id, sent_msg.chat.id, message.text, datetime.now().isoformat()))
                    conn.commit()
                    conn.close()
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
        log_command(user_id, message.chat.type, f"broadcast {success}/{total}")
    
    # Handle group broadcast
    elif user_id in broadcast_state and broadcast_state[user_id] == "group":
        broadcast_state[user_id] = False
        
        if not message.text:
            await message.answer("❌ Group broadcast supports text only")
            return
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT group_id FROM groups")
        groups = [row[0] for row in c.fetchall()]
        conn.close()
        
        total = len(groups)
        status_msg = await message.answer(f"📤 Sending to {total} groups...")
        
        success = 0
        for group_id in groups:
            try:
                sent_msg = await bot.send_message(group_id, f"📢 {message.text}")
                # Store for replies
                conn = sqlite3.connect("data/bot.db")
                c = conn.cursor()
                c.execute('''INSERT INTO cult_messages 
                            (message_id, user_id, original_sender, chat_id, text, timestamp) 
                            VALUES (?, ?, ?, ?, ?, ?)''',
                         (sent_msg.message_id, 0, user_id, sent_msg.chat.id, message.text, datetime.now().isoformat()))
                conn.commit()
                conn.close()
                success += 1
                await asyncio.sleep(0.1)
            except:
                continue
        
        await status_msg.edit_text(f"✅ Sent to {success}/{total} groups")
        log_command(user_id, message.chat.type, f"broadcast_gc {success}/{total}")
    
    # Handle replies to broadcast messages (silently - no bot response)
    elif message.reply_to_message:
        try:
            conn = sqlite3.connect("data/bot.db")
            c = conn.cursor()
            c.execute('''SELECT original_sender, chat_id, message_id FROM cult_messages 
                        WHERE message_id = ?''',
                     (message.reply_to_message.message_id,))
            result = c.fetchone()
            
            if result:
                original_sender, original_chat_id, original_msg_id = result
                
                # Forward reply to original sender (silently)
                reply_text = f"↪️ <b>REPLY TO YOUR BROADCAST</b>\n\n"
                reply_text += f"👤 <b>From:</b> {message.from_user.first_name} (ID: {message.from_user.id})\n"
                
                if message.text:
                    reply_text += f"💬 <b>Message:</b> {message.text}\n"
                elif message.caption:
                    reply_text += f"💬 <b>Caption:</b> {message.caption}\n"
                else:
                    reply_text += f"💬 <b>Media:</b> {message.content_type}\n"
                
                reply_text += f"🕒 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}"
                
                try:
                    await bot.send_message(
                        chat_id=original_sender,
                        text=reply_text,
                        parse_mode=ParseMode.HTML
                    )
                    
                    # Mark as replied
                    c.execute("UPDATE cult_messages SET replied = 1 WHERE message_id = ?", 
                             (original_msg_id,))
                    conn.commit()
                    
                    # NO CONFIRMATION MESSAGE TO USER - SILENT OPERATION
                    
                except Exception as e:
                    print(f"Error forwarding reply: {e}")
            
            conn.close()
        except Exception as e:
            print(f"Error processing reply: {e}")

# ========== MAIN ==========
async def main():
    print("🚀 Bot running...")
    print("🌪️ Tempest Cult System: ACTIVE")
    print(f"👑 Supreme Leader: {TEMPEST_LEADER} (Ravijah)")
    print(f"⚔️ Vice Chancellors: {TEMPEST_VICE1} (Bablu), {TEMPEST_VICE2} (Keny)")
    print(f"👨‍💻 Hidden Developer: {DEVELOPER_ID} (Kenneth)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
