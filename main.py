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

print("⚡ PRO BOT INITIALIZING...")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"

# TEMPEST CULT CONFIG
TEMPEST_LEADER = 6211708776  # @dont_try_to_copy_mee (Ravijah)
TEMPEST_VICE1 = 6581129741   # @Bablu_is_op (Bablu)
TEMPEST_VICE2 = 6108185460   # @Nocis_Creed (Keny/Developer)
TEMPEST_PICS = {
    "join": "https://files.catbox.moe/qjmgcg.jpg",
    "unity": "https://files.catbox.moe/k07i6j.jpg",
    "initiated": "https://files.catbox.moe/d9qnw5.jpg",
    "storm": "https://files.catbox.moe/4h9p8x.jpg",
    "council": "https://files.catbox.moe/7b2v1y.jpg",
    "ritual": "https://files.catbox.moe/3k5m6n.jpg"
}

# Create directories
Path("data").mkdir(exist_ok=True)
Path("temp").mkdir(exist_ok=True)
Path("backups").mkdir(exist_ok=True)
Path("cult_cache").mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

start_time = time.time()
bot_active = True
upload_waiting = {}
broadcast_state = {}
pending_joins = {}
tempest_invites = {}
message_cache = {}  # Store message IDs for auto-deletion

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
        is_cult_approved INTEGER DEFAULT 0,
        invited_by INTEGER DEFAULT 0
    )''')
    
    # Groups table
    c.execute('''CREATE TABLE IF NOT EXISTS groups (
        group_id INTEGER PRIMARY KEY,
        title TEXT,
        username TEXT,
        joined_date TEXT,
        last_active TEXT,
        messages INTEGER DEFAULT 0,
        commands INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
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
    
    # Cult Messages table
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
    
    # Invitations table
    c.execute('''CREATE TABLE IF NOT EXISTS invitations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_id INTEGER,
        invitee_id INTEGER,
        invitee_name TEXT,
        status TEXT DEFAULT 'pending',
        timestamp TEXT
    )''')
    
    # Add owner as admin
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    # Add cult leaders
    cult_leaders = [
        (TEMPEST_LEADER, "Ravijah", "Supreme Leader", 1),
        (TEMPEST_VICE1, "Bablu", "Vice Chancellor", 1),
        (TEMPEST_VICE2, "Keny", "Vice Chancellor & Developer", 1)
    ]
    
    for leader_id, name, rank, approved in cult_leaders:
        c.execute('''INSERT OR IGNORE INTO users 
                    (user_id, first_name, joined_date, last_active, cult_status, cult_rank, cult_name, is_cult_approved, is_admin) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (leader_id, name, datetime.now().isoformat(), datetime.now().isoformat(), "leader", rank, name, approved, 1))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized with backup system")

init_db()

# ========== AUTO-BACKUP SYSTEM ==========
async def auto_backup():
    """Automatically backup database daily"""
    while True:
        try:
            timestamp = datetime.now().strftime("%Y%m%d")
            backup_file = f"backups/auto_backup_{timestamp}.db"
            
            if not os.path.exists(backup_file):
                shutil.copy2("data/bot.db", backup_file)
                print(f"✅ Auto-backup created: {backup_file}")
                
                # Keep only last 7 backups
                backups = sorted([f for f in os.listdir("backups") if f.startswith("auto_backup_")])
                if len(backups) > 7:
                    for old_backup in backups[:-7]:
                        os.remove(f"backups/{old_backup}")
                        
        except Exception as e:
            print(f"⚠️ Auto-backup error: {e}")
        
        # Sleep for 24 hours
        await asyncio.sleep(24 * 3600)

# ========== HELPER FUNCTIONS ==========
async def delete_message_later(chat_id: int, message_id: int, delay: int = 10):
    """Auto-delete message after delay"""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass

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
        print(f"⚠️ Update user error: {e}")

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
        print(f"⚠️ Update group error: {e}")

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

async def get_admins():
    """Get all bot admins"""
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username FROM users WHERE is_admin = 1")
    admins = c.fetchall()
    conn.close()
    return admins

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

# ========== SCAN FUNCTIONS ==========
async def scan_users():
    """Scan and update all users from command logs"""
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        # Get unique users from command logs
        c.execute("SELECT DISTINCT user_id FROM command_logs")
        user_ids = [row[0] for row in c.fetchall()]
        
        updated = 0
        for user_id in user_ids:
            try:
                # Try to get user info from Telegram
                chat = await bot.get_chat(user_id)
                c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                if not c.fetchone():
                    c.execute("INSERT INTO users (user_id, username, first_name, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                             (user_id, chat.username, chat.first_name, datetime.now().isoformat(), datetime.now().isoformat()))
                    updated += 1
            except:
                continue
        
        conn.commit()
        conn.close()
        return f"✅ Scan complete. Updated {updated} users."
        
    except Exception as e:
        return f"❌ Scan error: {str(e)[:100]}"

async def scan_groups():
    """Scan and update all groups from command logs"""
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        # Get unique groups from command logs where chat_type is group/supergroup
        c.execute("SELECT DISTINCT user_id FROM command_logs WHERE chat_type IN ('group', 'supergroup')")
        group_ids = [row[0] for row in c.fetchall()]
        
        updated = 0
        for group_id in group_ids:
            try:
                # Try to get group info from Telegram
                chat = await bot.get_chat(group_id)
                if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    c.execute("SELECT group_id FROM groups WHERE group_id = ?", (group_id,))
                    if not c.fetchone():
                        c.execute("INSERT INTO groups (group_id, title, username, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                                 (group_id, chat.title, chat.username, datetime.now().isoformat(), datetime.now().isoformat()))
                        updated += 1
            except:
                continue
        
        conn.commit()
        conn.close()
        return f"✅ Group scan complete. Updated {updated} groups."
        
    except Exception as e:
        return f"❌ Group scan error: {str(e)[:100]}"

# ========== TEMPEST CULT FUNCTIONS ==========
async def get_cult_leaders_online():
    """Check which leaders are online (active in last 10 minutes)"""
    online_leaders = []
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    leaders = [TEMPEST_LEADER, TEMPEST_VICE1, TEMPEST_VICE2]
    ten_min_ago = (datetime.now() - timedelta(minutes=10)).isoformat()
    
    for leader_id in leaders:
        c.execute("SELECT first_name FROM users WHERE user_id = ? AND last_active >= ?", 
                 (leader_id, ten_min_ago))
        if c.fetchone():
            online_leaders.append(leader_id)
    
    conn.close()
    return online_leaders

async def get_cult_members():
    """Get all cult members with their real names"""
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT first_name, cult_rank, sacrifices, cult_join_date FROM users WHERE cult_status != 'none' AND is_cult_approved = 1 ORDER BY sacrifices DESC")
    members = c.fetchall()
    conn.close()
    return members

async def add_cult_member(user_id, name, sacrifice, inviter_id=0):
    """Add user to cult"""
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute('''UPDATE users SET 
                cult_status = 'member', 
                cult_rank = 'Initiate',
                cult_join_date = ?,
                sacrifices = sacrifices + 1,
                cult_name = ?,
                is_cult_approved = 1,
                invited_by = ?
                WHERE user_id = ?''',
             (datetime.now().isoformat(), name, inviter_id, user_id))
    
    # Update invitation status
    if inviter_id:
        c.execute("UPDATE invitations SET status = 'accepted' WHERE invitee_id = ? AND status = 'pending'", (user_id,))
    
    conn.commit()
    conn.close()

async def create_ascii_art(art_type: str):
    """Create ASCII art for cult messages"""
    arts = {
        "storm": """
    ⠀⠀⠀⠀⠀⣀⣤⣤⣤⣀⠀⠀⠀⠀
    ⠀⠀⠀⣴⣿⣿⣿⣿⣿⣿⣷⡄⠀⠀
    ⠀⠀⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⡆⠀
    ⠀⢀⣿⣿⡿⠛⠛⠛⢿⣿⣿⣿⣿⡀
    ⠀⣾⣿⣿⣇⣀⣀⣀⣸⣿⣿⣿⣿⣷
    ⢠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
    ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
    ⠈⠛⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠛⠁
        """,
        "ritual": """
    🔥───────⚡───────🌀
    │                 │
    │    TEMPEST     │
    │     RITUAL     │
    │                 │
    🌪️───────⚡───────🌩️
        """,
        "council": """
    ┏━━━━━━━━━━━━━━━━┓
    ┃   HIGH COUNCIL  ┃
    ┣━━━━━━━━━━━━━━━━┫
    ┃ 👑 Ravijah     ┃
    ┃ ⚔️ Bablu       ┃
    ┃ 🌩️ Keny        ┃
    ┗━━━━━━━━━━━━━━━━┛
        """,
        "progress": """
    ╔════════════════╗
    ║  TEMPEST PROG  ║
    ╠════════════════╣
    ║ ▓▓▓▓▓▓▓▓▓░░░░░ ║ 65%
    ║ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ ║ 100%
    ╚════════════════╝
        """
    }
    return arts.get(art_type, "🌀")

# ========== STORY SYSTEM ==========
async def tell_tempest_story(message: Message, user_name: str):
    """Tell the Tempest Cult story with dialogue and auto-deletion"""
    story_messages = []
    
    try:
        # CHAPTER 1: The Gathering
        part1 = await message.answer_photo(
            photo=TEMPEST_PICS["storm"],
            caption=f"""🌌 <b>THE TEMPEST SAGA - CHAPTER 1</b>

{create_ascii_art("storm")}

<code>Year 0 - The Void Era</code>

⚡ <b>RAVIJAH:</b> "The silence... it's deafening. This world needs a storm."

🌑 <b>NARRATOR:</b> Ravijah wandered the shattered realms, power crackling at his fingertips. The Great Calm had lasted centuries, but change was coming...

🗡️ <b>BABLU:</b> "Another village fallen to the Shard Lords. When do we fight back, brother?"

👤 <b>KENY:</b> *appears from shadows* "Patience. The right moment comes. I've seen it in the stars."

⚡ <b>RAVIJAH:</b> "Then we prepare. Gather the worthy. The Tempest begins."
""",
            parse_mode=ParseMode.HTML
        )
        story_messages.append(part1.message_id)
        await asyncio.sleep(8)
        
        # CHAPTER 2: First Ritual
        part2 = await message.answer_photo(
            photo=TEMPEST_PICS["ritual"],
            caption=f"""🔥 <b>CHAPTER 2 - BLOOD MOON RITUAL</b>

{create_ascii_art("ritual")}

<code>Year 47 - The Awakening</code>

❤️‍🔥 <b>ELARA:</b> "Your eyes... they hold entire storms, Ravijah. It's beautiful and terrifying."

⚡ <b>RAVIJAH:</b> "Stay close to me tonight. The Blood Moon rises. Kaelen grows jealous."

😡 <b>KAELEN:</b> *watching from shadows* "She should be mine! That storm-wielder will pay..."

🗡️ <b>BABLU:</b> "The ritual is ready! Brothers, to the Circle of Storms!"

👤 <b>KENY:</b> "I feel it... power gathering. Tonight, we become more than men."
""",
            parse_mode=ParseMode.HTML
        )
        story_messages.append(part2.message_id)
        await asyncio.sleep(8)
        
        # CHAPTER 3: Betrayal & Sacrifice
        part3 = await message.answer_photo(
            photo=TEMPEST_PICS["unity"],
            caption=f"""💔 <b>CHAPTER 3 - THE BETRAYAL</b>

{create_ascii_art("storm")}

<code>The Festival of Twin Moons</code>

🎪 <b>ELARA:</b> *singing* "May the moons guide us, may the stars protect—"

🔪 <b>KAELEN:</b> "NOW! KILL THE STORM-BORN!"

⚡ <b>RAVIJAH:</b> "ELARA, NO—!"

🩸 <b>ELARA:</b> *takes the poisoned blade* "Live... for both of us... promise me..."

🌪️ <b>RAVIJAH:</b> *screams echo through reality* "LET THE WORLD BURN WITH ME!"

🌀 <b>NARRATOR:</b> And so, the First Tempest was born from grief and love.
""",
            parse_mode=ParseMode.HTML
        )
        story_messages.append(part3.message_id)
        await asyncio.sleep(8)
        
        # CHAPTER 4: The Council Forms
        part4 = await message.answer_photo(
            photo=TEMPEST_PICS["council"],
            caption=f"""👑 <b>CHAPTER 4 - COUNCIL OF STORMS</b>

{create_ascii_art("council")}

<code>Year 150 - Golden Age</code>

⚡ <b>RAVIJAH:</b> "300 years... and the Tempest grows stronger. What say you, brothers?"

🗡️ <b>BABLU:</b> "The Crystal Empire kneels before us! Their princess offered her crown as tribute!"

👤 <b>KENY:</b> "The Void Walkers are eliminated. None escaped my silent blades."

⚡ <b>RAVIJAH:</b> "Good. Now we look to the stars. New initiates, new power. The Tempest is eternal."

🌀 <b>NARRATOR:</b> And so the legend grew, century after century, storm after storm...
""",
            parse_mode=ParseMode.HTML
        )
        story_messages.append(part4.message_id)
        await asyncio.sleep(8)
        
        # CHAPTER 5: Modern Era
        part5 = await message.answer_photo(
            photo=TEMPEST_PICS["initiated"],
            caption=f"""📡 <b>CHAPTER 5 - THE ETERNAL WATCH</b>

{create_ascii_art("progress")}

<code>Present Day - Digital Age</code>

⚡ <b>RAVIJAH:</b> "The storm adapts. Now it flows through cables and codes."

💻 <b>KENY:</b> "Our network spans continents. Every upload, a digital sacrifice."

📱 <b>BABLU:</b> "New initiates join daily. The Tempest grows in this digital realm."

🌀 <b>NARRATOR:</b> And now, {user_name}... your story begins. Will you join the eternal storm?

<code>The choice is yours. The Tempest awaits.</code>
""",
            parse_mode=ParseMode.HTML
        )
        story_messages.append(part5.message_id)
        
        # Auto-delete all story messages after delay
        for msg_id in story_messages:
            asyncio.create_task(delete_message_later(message.chat.id, msg_id, 15))
            
    except Exception as e:
        print(f"Story error: {e}")

# ========== ORIGINAL COMMANDS ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    update_user(message.from_user)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(message.chat)
    
    welcome = await message.answer(
        f"✨ <b>Welcome, {message.from_user.first_name}!</b>\n\n"
        "🤖 <b>PRO TELEGRAM BOT v2.1</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 File Upload System\n"
        "✨ Fortune & Games\n"
        "🌪️ Tempest Cult (hidden)\n"
        "👑 Admin Controls\n\n"
        "📚 <code>/help</code> for commands\n"
        "🌀 <code>/tempest</code> for cult info",
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, message.chat.type, "start")
    asyncio.create_task(delete_message_later(message.chat.id, welcome.message_id, 30))

@dp.message(Command("help"))
async def help_cmd(message: Message):
    update_user(message.from_user)
    
    help_msg = await message.answer(
        """📚 <b>BOT COMMANDS</b>
━━━━━━━━━━━━━━━━━━━━

🔗 <b>UPLOAD:</b>
<code>/link</code> - Upload any file

🎮 <b>GAMES:</b>
<code>/dice</code> - Roll dice
<code>/flip</code> - Coin flip
<code>/wish [text]</code> - Fortune

👤 <b>USER:</b>
<code>/profile</code> - Your stats
<code>/admins</code> - Bot admins

👑 <b>ADMIN:</b>
<code>/ping</code> - Status
<code>/stats</code> - Statistics
<code>/logs [days]</code> - View logs
<code>/users</code> - User list
<code>/scan</code> - Rescan users/groups
<code>/backup</code> - Create backup

⚡ <b>OWNER:</b>
<code>/pro [id]</code> - Make admin
<code>/broadcast</code> - Send to all
<code>/broadcast_gc</code> - Groups only
<code>/toggle</code> - Toggle bot
<code>/restart</code> - Restart
<code>/emergency_stop</code> - Stop bot

🌀 <b>TEMPEST (Hidden):</b>
<code>/tempest</code> - Cult info
<code>/tempest_join</code> - Join cult
<code>/tempest_progress</code> - Your progress""",
        parse_mode=ParseMode.HTML
    )
    log_command(message.from_user.id, message.chat.type, "help")
    asyncio.create_task(delete_message_later(message.chat.id, help_msg.message_id, 45))

# ========== NEW COMMANDS ==========
@dp.message(Command("admins"))
async def admins_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    admins = await get_admins()
    admin_text = "👑 <b>BOT ADMINISTRATORS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for user_id, name, username in admins:
        uname = f"@{username}" if username else "No username"
        admin_text += f"• {name} ({uname})\n   🆔 <code>{user_id}</code>\n\n"
    
    admin_msg = await message.answer(admin_text, parse_mode=ParseMode.HTML)
    log_command(message.from_user.id, message.chat.type, "admins")
    asyncio.create_task(delete_message_later(message.chat.id, admin_msg.message_id, 30))

@dp.message(Command("scan"))
async def scan_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    scan_msg = await message.answer("🔍 <b>Scanning database for updates...</b>", parse_mode=ParseMode.HTML)
    
    # Scan users
    user_result = await scan_users()
    await scan_msg.edit_text(f"{user_result}\n\n🔍 <b>Scanning groups...</b>", parse_mode=ParseMode.HTML)
    
    # Scan groups
    group_result = await scan_groups()
    
    result_msg = await message.answer(
        f"✅ <b>SCAN COMPLETE</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{user_result}\n{group_result}\n\n"
        f"📊 Database is now synced with latest activity.",
        parse_mode=ParseMode.HTML
    )
    
    log_command(message.from_user.id, message.chat.type, "scan")
    asyncio.create_task(delete_message_later(message.chat.id, result_msg.message_id, 20))
    asyncio.create_task(delete_message_later(message.chat.id, scan_msg.message_id, 5))

@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/manual_backup_{timestamp}.db"
    
    try:
        # Create backup
        shutil.copy2("data/bot.db", backup_file)
        
        # Count records
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM users")
        users = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM groups")
        groups = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM uploads")
        uploads = c.fetchone()[0] or 0
        
        conn.close()
        
        backup_info = await message.answer_document(
            FSInputFile(backup_file),
            caption=f"💾 <b>DATABASE BACKUP</b>\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n"
                   f"📅 {timestamp}\n"
                   f"👥 Users: {users}\n"
                   f"👥 Groups: {groups}\n"
                   f"📁 Uploads: {uploads}\n\n"
                   f"✅ Backup saved successfully\n"
                   f"🔒 Auto-backup runs daily",
            parse_mode=ParseMode.HTML
        )
        
        log_command(message.from_user.id, message.chat.type, "backup")
        
        # Auto-delete info message
        asyncio.create_task(delete_message_later(message.chat.id, backup_info.message_id, 30))
        
    except Exception as e:
        error_msg = await message.answer(f"❌ Backup failed: {str(e)[:100]}")
        log_error(message.from_user.id, "backup", e)
        asyncio.create_task(delete_message_later(message.chat.id, error_msg.message_id, 10))

# ========== TEMPEST CULT COMMANDS ==========
@dp.message(Command("tempest"))
async def tempest_cmd(message: Message):
    update_user(message.from_user)
    
    cult_info = await message.answer_photo(
        photo=TEMPEST_PICS["storm"],
        caption="""🌀 <b>TEMPEST CULT</b>
━━━━━━━━━━━━━━━━━━━━

<code>The Eternal Storm | Since Year 0</code>

📜 <b>ABOUT:</b>
A digital brotherhood spanning centuries, now adapted to the modern age. Power through unity, strength through sacrifice.

👑 <b>HIGH COUNCIL:</b>
• Ravijah - Supreme Leader
• Bablu - Vice Chancellor
• Keny - Vice Chancellor & Developer

🎮 <b>HOW TO JOIN:</b>
1. Use <code>/tempest_join</code>
2. Choose your sacrifice
3. Witness the saga
4. Get Council approval

⚡ <b>FEATURES:</b>
• Digital rituals
• Sacrifice tracking
• Rank progression
• Eternal brotherhood

🔮 <code>/tempest_progress</code> - Check your status
💀 <code>/tempest_join</code> - Begin initiation""",
        parse_mode=ParseMode.HTML
    )
    
    log_command(message.from_user.id, message.chat.type, "tempest")
    asyncio.create_task(delete_message_later(message.chat.id, cult_info.message_id, 45))

@dp.message(Command("tempest_join"))
async def tempest_join_cmd(message: Message):
    update_user(message.from_user)
    
    # Check if replying to invite someone
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        
        # Store invitation
        tempest_invites[target_user.id] = {
            "inviter_id": message.from_user.id,
            "inviter_name": message.from_user.first_name,
            "timestamp": time.time()
        }
        
        # Send invitation
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="✅ Accept Invitation", callback_data=f"invite_accept_{target_user.id}"))
        keyboard.add(InlineKeyboardButton(text="❌ Decline", callback_data=f"invite_decline_{target_user.id}"))
        
        invite_msg = await message.reply(
            f"🌀 <b>TEMPEST INVITATION</b>\n\n"
            f"👤 {target_user.first_name}, you've been invited to join the Tempest Cult!\n"
            f"📜 By: {message.from_user.first_name}\n\n"
            f"⚡ The eternal storm calls... will you answer?",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard.as_markup()
        )
        
        # Auto-delete invitation
        asyncio.create_task(delete_message_later(message.chat.id, invite_msg.message_id, 60))
        return
    
    # Check if already in cult
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (message.from_user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        already_msg = await message.answer("🌀 <b>You are already part of the Tempest!</b>\nUse /tempest_progress to check your status.")
        asyncio.create_task(delete_message_later(message.chat.id, already_msg.message_id, 10))
        conn.close()
        return
    
    conn.close()
    
    # Start initiation
    pending_joins[message.from_user.id] = {
        "name": message.from_user.first_name,
        "user_id": message.from_user.id,
        "step": 1
    }
    
    # Send initiation start
    init_msg = await message.answer_photo(
        photo=TEMPEST_PICS["join"],
        caption=f"""🌪️ <b>TEMPEST INITIATION</b>
━━━━━━━━━━━━━━━━━━━━

👤 <b>Initiate:</b> {message.from_user.first_name}
🌀 <b>Status:</b> Beginning Ritual...

⚡ The eternal storm senses your presence.
🌩️ A journey of 300 years awaits in moments.

<code>Preparing sacrificial offering...</code>""",
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(3)
    
    # Sacrifice selection
    sacrifices = [
        "🩸 Your Firstborn's Shadow",
        "💎 Memory of Your First Love",
        "📜 Your Digital Anonymity",
        "🎮 1000 Hours of Game Progress",
        "📱 Your Social Media Legacy",
        "🍕 Ability to Taste Sweetness",
        "🎵 Your Favorite Song Forever",
        "😴 Dreams of Flying",
        "📚 Knowledge of Tomorrow's News",
        "👻 Your Reflection in Mirrors"
    ]
    
    keyboard = InlineKeyboardBuilder()
    for i, sacrifice in enumerate(sacrifices, 1):
        keyboard.add(InlineKeyboardButton(text=f"{i}. {sacrifice[:15]}...", callback_data=f"sacrifice_{i}"))
    keyboard.adjust(2)
    
    sacrifice_msg = await message.answer(
        f"""💀 <b>SACRIFICE SELECTION</b>
━━━━━━━━━━━━━━━━━━━━

The Tempest demands a price for power.
Choose what you offer to the eternal storm:

{sacrifices[0]}
{sacrifices[1]}
{sacrifices[2]}
{sacrifices[3]}
{sacrifices[4]}
{sacrifices[5]}
{sacrifices[6]}
{sacrifices[7]}
{sacrifices[8]}
{sacrifices[9]}

<code>Choose wisely... the storm remembers all.</code>""",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.as_markup()
    )
    
    log_command(message.from_user.id, message.chat.type, "tempest_join")
    asyncio.create_task(delete_message_later(message.chat.id, init_msg.message_id, 5))

@dp.message(Command("tempest_progress"))
async def tempest_progress_cmd(message: Message):
    update_user(message.from_user)
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status, cult_rank, sacrifices, cult_join_date FROM users WHERE user_id = ?", (message.from_user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        status, rank, sacrifices, join_date = result
        
        # Calculate time in cult
        try:
            join_dt = datetime.fromisoformat(join_date)
            days_in_cult = (datetime.now() - join_dt).days
            time_text = f"{days_in_cult} days" if days_in_cult > 0 else "Today"
        except:
            time_text = "Recently"
        
        # Create progress bar
        progress = min(sacrifices * 10, 100)
        bar = "▓" * (progress // 10) + "░" * (10 - progress // 10)
        
        progress_msg = await message.answer(
            f"""🌀 <b>TEMPEST PROGRESS</b>
━━━━━━━━━━━━━━━━━━━━

👤 <b>Member:</b> {message.from_user.first_name}
👑 <b>Rank:</b> {rank}
⚔️ <b>Sacrifices:</b> {sacrifices}
📅 <b>Member Since:</b> {time_text}

{create_ascii_art("progress")}

<b>PROGRESS TO NEXT RANK:</b>
[{bar}] {progress}%

<b>NEXT MILESTONE:</b>
{sacrifices}/10 sacrifices for promotion

<code>Every upload = 1 sacrifice to the Tempest</code>

🔮 Continue your journey with /link""",
            parse_mode=ParseMode.HTML
        )
    else:
        progress_msg = await message.answer(
            """🌀 <b>TEMPEST PROGRESS</b>
━━━━━━━━━━━━━━━━━━━━

👤 <b>Status:</b> Not Initiated

⚡ You haven't joined the Tempest yet.
🌩️ Begin your journey with /tempest_join

<code>The eternal storm awaits worthy souls...</code>""",
            parse_mode=ParseMode.HTML
        )
    
    conn.close()
    log_command(message.from_user.id, message.chat.type, "tempest_progress")
    asyncio.create_task(delete_message_later(message.chat.id, progress_msg.message_id, 30))

# ========== INVITATION HANDLERS ==========
@dp.callback_query(F.data.startswith("invite_"))
async def handle_invitation(callback: CallbackQuery):
    try:
        _, action, target_id = callback.data.split("_")
        target_id = int(target_id)
        
        if callback.from_user.id != target_id:
            await callback.answer("🚫 This invitation isn't for you!", show_alert=True)
            return
        
        if action == "accept":
            # Start initiation for invited user
            pending_joins[target_id] = {
                "name": callback.from_user.first_name,
                "user_id": target_id,
                "inviter_id": tempest_invites.get(target_id, {}).get("inviter_id", 0),
                "step": 1
            }
            
            await callback.message.edit_text(
                f"✅ <b>INVITATION ACCEPTED!</b>\n\n"
                f"🌀 {callback.from_user.first_name} has accepted the Tempest invitation!\n"
                f"⚡ Proceeding to initiation...",
                parse_mode=ParseMode.HTML
            )
            
            # Send sacrifice selection
            await callback.answer("🌀 Beginning initiation...")
            
            # Continue with sacrifice selection (similar to tempest_join)
            await asyncio.sleep(2)
            
            sacrifices = [
                "🩸 Your Firstborn's Shadow",
                "💎 Memory of Your First Love",
                "📜 Your Digital Anonymity",
                "🎮 1000 Hours of Game Progress",
                "📱 Your Social Media Legacy"
            ]
            
            keyboard = InlineKeyboardBuilder()
            for i, sacrifice in enumerate(sacrifices, 1):
                keyboard.add(InlineKeyboardButton(text=f"{i}. {sacrifice[:15]}...", callback_data=f"sacrifice_{i}"))
            keyboard.adjust(2)
            
            await callback.message.answer(
                f"""💀 <b>SACRIFICE SELECTION</b>
━━━━━━━━━━━━━━━━━━━━

Choose your offering to the Tempest:

{sacrifices[0]}
{sacrifices[1]}
{sacrifices[2]}
{sacrifices[3]}
{sacrifices[4]}

<code>The storm demands its price...</code>""",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard.as_markup()
            )
            
        else:  # decline
            await callback.message.edit_text(
                f"❌ <b>INVITATION DECLINED</b>\n\n"
                f"🌀 {callback.from_user.first_name} has declined the Tempest invitation.\n"
                f"🌪️ The storm respects your choice... for now.",
                parse_mode=ParseMode.HTML
            )
            await callback.answer("Invitation declined")
        
        # Cleanup
        if target_id in tempest_invites:
            del tempest_invites[target_id]
            
    except Exception as e:
        print(f"Invitation error: {e}")
        await callback.answer("❌ Error processing invitation", show_alert=True)

# ========== SACRIFICE CALLBACK ==========
@dp.callback_query(F.data.startswith("sacrifice_"))
async def handle_sacrifice(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in pending_joins:
        await callback.answer("❌ Initiation expired!", show_alert=True)
        return
    
    sacrifice_num = callback.data.split("_")[1]
    sacrifices_map = {
        "1": "🩸 Your Firstborn's Shadow",
        "2": "💎 Memory of Your First Love",
        "3": "📜 Your Digital Anonymity",
        "4": "🎮 1000 Hours of Game Progress",
        "5": "📱 Your Social Media Legacy",
        "6": "🍕 Ability to Taste Sweetness",
        "7": "🎵 Your Favorite Song Forever",
        "8": "😴 Dreams of Flying",
        "9": "📚 Knowledge of Tomorrow's News",
        "10": "👻 Your Reflection in Mirrors"
    }
    
    sacrifice = sacrifices_map.get(sacrifice_num, "Unknown Offering")
    pending_joins[user_id]["sacrifice"] = sacrifice
    
    await callback.message.edit_text(
        f"⚡ <b>SACRIFICE ACCEPTED</b>\n\n"
        f"🌀 Offering: {sacrifice}\n"
        f"🌩️ The Tempest consumes your tribute...",
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(3)
    
    # Tell the story
    await tell_tempest_story(callback.message, pending_joins[user_id]["name"])
    
    await asyncio.sleep(5)
    
    # Auto-approve (since we're doing fun group invites)
    await add_cult_member(
        user_id,
        pending_joins[user_id]["name"],
        sacrifice,
        pending_joins[user_id].get("inviter_id", 0)
    )
    
    # Send completion message
    completion = await callback.message.answer(
        f"""✅ <b>INITIATION COMPLETE!</b>
━━━━━━━━━━━━━━━━━━━━

👤 <b>Welcome, {pending_joins[user_id]['name']}!</b>
🌀 <b>Rank:</b> Tempest Initiate
💀 <b>Sacrifice:</b> {sacrifice}
⚡ <b>Status:</b> Full Member

<code>The eternal storm welcomes you.
Your journey begins now.</code>

🔮 Use /tempest_progress to track growth
📁 Each upload = 1 sacrifice to the Tempest
🌪️ The saga continues with you...""",
        parse_mode=ParseMode.HTML
    )
    
    # Notify inviter if applicable
    inviter_id = pending_joins[user_id].get("inviter_id")
    if inviter_id:
        try:
            await bot.send_message(
                inviter_id,
                f"🌀 <b>INITIATION SUCCESS</b>\n\n"
                f"👤 {pending_joins[user_id]['name']} has joined the Tempest!\n"
                f"💀 Sacrifice: {sacrifice}\n"
                f"⚡ The storm grows stronger...",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
    
    # Cleanup
    if user_id in pending_joins:
        del pending_joins[user_id]
    
    await callback.answer()
    asyncio.create_task(delete_message_later(callback.message.chat.id, completion.message_id, 30))

# ========== FILE UPLOAD SYSTEM ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        group_msg = await message.answer("📁 <b>Upload files in private chat only</b>", parse_mode=ParseMode.HTML)
        asyncio.create_task(delete_message_later(message.chat.id, group_msg.message_id, 10))
        return
    
    update_user(message.from_user)
    upload_waiting[message.from_user.id] = True
    
    link_msg = await message.answer(
        """📁 <b>FILE UPLOAD SYSTEM</b>
━━━━━━━━━━━━━━━━━━━━

⚡ <b>Send me any file:</b>
• Photos, videos, documents
• Audio, voice messages
• Stickers, animations
• Max 200MB

🌪️ <b>For Tempest Members:</b>
Each upload = 1 sacrifice

❌ <code>/cancel</code> to stop""",
        parse_mode=ParseMode.HTML
    )
    
    log_command(message.from_user.id, message.chat.type, "link")
    asyncio.create_task(delete_message_later(message.chat.id, link_msg.message_id, 45))

# [Rest of the original commands remain the same - dice, flip, wish, profile, etc.]
# Just add auto-delete to all response messages

# ========== OTHER COMMANDS ==========
@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    if not await is_admin(message.from_user.id):
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
    
    ping_msg = await message.answer(
        f"🏓 <b>PONG! System Status</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Response: {ping_ms:.0f}ms\n"
        f"👥 Users: {users}\n"
        f"📁 Uploads: {uploads}\n"
        f"🕒 Uptime: {int(time.time() - start_time)}s\n"
        f"🔧 Status: {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}\n"
        f"🌀 Tempest: Online",
        parse_mode=ParseMode.HTML
    )
    
    log_command(message.from_user.id, message.chat.type, "ping")
    asyncio.create_task(delete_message_later(message.chat.id, ping_msg.message_id, 20))

# [Include all other original commands with same logic, just add auto-delete]

# ========== MAIN ==========
async def main():
    # Start auto-backup system
    asyncio.create_task(auto_backup())
    
    print("🚀 PRO BOT v2.1 STARTING...")
    print("✅ Database initialized")
    print("💾 Auto-backup system: ACTIVE")
    print("🌀 Tempest Cult: ENABLED")
    print(f"👑 Supreme Leader: {TEMPEST_LEADER}")
    print(f"⚔️ Vice Chancellors: {TEMPEST_VICE1}, {TEMPEST_VICE2}")
    print("🔧 Developer: Kenneth (@Nocis_Creed)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped gracefully")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
