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

print("🤖 PRO BOT INITIALIZING...")

# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"

# TEMPEST CULT LEADERS (Auto-detected from Telegram)
TEMPEST_LEADER = 6211708776  # @dont_try_to_copy_mee
TEMPEST_VICE1 = 6581129741   # @Bablu_is_op
TEMPEST_VICE2 = 6108185460   # @Nocis_Creed (Developer)

# TEMPEST PICTURES
TEMPEST_PICS = [
    "https://files.catbox.moe/qjmgcg.jpg",  # Join picture
    "https://files.catbox.moe/k07i6j.jpg",  # Unity picture  
    "https://files.catbox.moe/d9qnw5.jpg",  # Initiated picture
]

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
leader_names = {}  # Store leader names from Telegram

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
        sacrifices INTEGER DEFAULT 0
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
        chat_id INTEGER,
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
    
    # Add owner as admin
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, joined_date, last_active, is_admin) VALUES (?, ?, ?, ?, ?)",
              (OWNER_ID, "Owner", datetime.now().isoformat(), datetime.now().isoformat(), 1))
    
    # Add Tempest leaders permanently
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, cult_status, cult_rank, cult_join_date, sacrifices) VALUES (?, ?, 'member', 'Supreme Leader', ?, 999)",
              (TEMPEST_LEADER, "Ravijah", datetime.now().isoformat()))
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, cult_status, cult_rank, cult_join_date, sacrifices) VALUES (?, ?, 'member', 'Vice Chancellor', ?, 500)",
              (TEMPEST_VICE1, "Bablu", datetime.now().isoformat()))
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, cult_status, cult_rank, cult_join_date, sacrifices) VALUES (?, ?, 'member', 'Vice Chancellor', ?, 500)",
              (TEMPEST_VICE2, "Nocis_Creed", datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized with Tempest leaders")

init_db()

# ========== HELPER FUNCTIONS ==========
def log_command(user_id, chat_id, chat_type, command, success=True):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO command_logs (timestamp, user_id, chat_id, chat_type, command, success) VALUES (?, ?, ?, ?, ?, ?)",
              (datetime.now().isoformat(), user_id, chat_id, chat_type, command, 1 if success else 0))
    c.execute("UPDATE users SET commands = commands + 1 WHERE user_id = ?", (user_id,))
    
    # Update group command count if in group
    if chat_type in ['group', 'supergroup']:
        c.execute("UPDATE groups SET commands = commands + 1 WHERE group_id = ?", (chat_id,))
    
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
    """Check if user is bot admin"""
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
    """Get all bot admins with proper usernames"""
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

async def get_leader_names():
    """Get leader names from Telegram"""
    global leader_names
    try:
        # Get Supreme Leader
        leader_chat = await bot.get_chat(TEMPEST_LEADER)
        leader_names[TEMPEST_LEADER] = leader_chat.first_name
        
        # Get Vice Chancellor 1
        vc1_chat = await bot.get_chat(TEMPEST_VICE1)
        leader_names[TEMPEST_VICE1] = vc1_chat.first_name
        
        # Get Vice Chancellor 2
        vc2_chat = await bot.get_chat(TEMPEST_VICE2)
        leader_names[TEMPEST_VICE2] = vc2_chat.first_name
        
        print(f"✅ Leader names loaded: {leader_names}")
    except Exception as e:
        print(f"❌ Error loading leader names: {e}")
        # Fallback names
        leader_names = {
            TEMPEST_LEADER: "Ravijah",
            TEMPEST_VICE1: "Bablu",
            TEMPEST_VICE2: "Nocis_Creed"
        }

# ========== ANIMATED STORY SYSTEM ==========
async def animate_tempest_story(chat_id: int, user_name: str):
    """Show animated story in ONE message"""
    try:
        print(f"🌀 Starting Tempest story for {user_name}")
        
        # Start with first image
        try:
            story_message = await bot.send_photo(
                chat_id=chat_id,
                photo=TEMPEST_PICS[0],
                caption="🌌 <b>THE TEMPEST SAGA BEGINS...</b>\n\n"
                       "⚡ <b>RAVIJAH:</b> \"The silence... it's deafening.\"\n\n"
                       "▰▱▱▱▱▱▱▱▱▱ 20%",
                parse_mode=ParseMode.HTML
            )
        except:
            story_message = await bot.send_message(
                chat_id=chat_id,
                text="🌌 <b>THE TEMPEST SAGA BEGINS...</b>\n\n"
                     "⚡ <b>RAVIJAH:</b> \"The silence... it's deafening.\"\n\n"
                     "▰▱▱▱▱▱▱▱▱▱ 20%",
                parse_mode=ParseMode.HTML
            )
        
        await asyncio.sleep(3)
        
        # Update to second chapter
        try:
            await bot.edit_message_media(
                chat_id=chat_id,
                message_id=story_message.message_id,
                media=types.InputMediaPhoto(
                    media=TEMPEST_PICS[1],
                    caption="🔥 <b>COUNCIL OF STORMS FORMS</b>\n\n"
                           "🗡️ <b>BABLU:</b> \"When do we strike back?\"\n\n"
                           "👤 <b>KENY:</b> \"We prepare...\"\n\n"
                           "▰▰▱▱▱▱▱▱▱▱ 40%",
                    parse_mode=ParseMode.HTML
                )
            )
        except:
            await story_message.edit_text(
                text="🔥 <b>COUNCIL OF STORMS FORMS</b>\n\n"
                     "🗡️ <b>BABLU:</b> \"When do we strike back?\"\n\n"
                     "👤 <b>KENY:</b> \"We prepare...\"\n\n"
                     "▰▰▱▱▱▱▱▱▱▱ 40%",
                parse_mode=ParseMode.HTML
            )
        
        await asyncio.sleep(3)
        
        # Update to final chapter
        try:
            await bot.edit_message_media(
                chat_id=chat_id,
                message_id=story_message.message_id,
                media=types.InputMediaPhoto(
                    media=TEMPEST_PICS[2],
                    caption="💔 <b>BETRAYAL & SACRIFICE</b>\n\n"
                           "🔪 <b>KAELEN:</b> \"KILL THE STORM-BORN!\"\n\n"
                           "👑 <b>GOLDEN AGE DAWNS</b>\n\n"
                           f"🌀 <b>NARRATOR:</b> And now, {user_name}...\n\n"
                           "▰▰▰▰▰▰▰▰▱▱ 80%",
                    parse_mode=ParseMode.HTML
                )
            )
        except:
            await story_message.edit_text(
                text="💔 <b>BETRAYAL & SACRIFICE</b>\n\n"
                     "🔪 <b>KAELEN:</b> \"KILL THE STORM-BORN!\"\n\n"
                     "👑 <b>GOLDEN AGE DAWNS</b>\n\n"
                     f"🌀 <b>NARRATOR:</b> And now, {user_name}...\n\n"
                     "▰▰▰▰▰▰▰▰▱▱ 80%",
                parse_mode=ParseMode.HTML
            )
        
        await asyncio.sleep(3)
        
        # Final update
        try:
            await story_message.edit_caption(
                caption="📡 <b>THE ETERNAL STORM</b>\n\n"
                       "<code>Present Day</code>\n\n"
                       "⚡ <b>RAVIJAH:</b> \"The storm adapts...\"\n\n"
                       "💻 <b>KENY:</b> \"Our network spans continents.\"\n\n"
                       f"🌀 <b>NARRATOR:</b> {user_name}, your story begins.\n\n"
                       "<i>The eternal storm welcomes you...</i>\n\n"
                       "▰▰▰▰▰▰▰▰▰▰ 100%\n\n"
                       "⚡ <i>Will you join the legend?</i>",
                parse_mode=ParseMode.HTML
            )
        except:
            await story_message.edit_text(
                text="📡 <b>THE ETERNAL STORM</b>\n\n"
                     "<code>Present Day</code>\n\n"
                     "⚡ <b>RAVIJAH:</b> \"The storm adapts...\"\n\n"
                     "💻 <b>KENY:</b> \"Our network spans continents.\"\n\n"
                     f"🌀 <b>NARRATOR:</b> {user_name}, your story begins.\n\n"
                     "<i>The eternal storm welcomes you...</i>\n\n"
                     "▰▰▰▰▰▰▰▰▰▰ 100%\n\n"
                     "⚡ <i>Will you join the legend?</i>",
                parse_mode=ParseMode.HTML
            )
        
        print("✅ Story completed")
        
        # Auto-delete after 8 seconds
        await asyncio.sleep(8)
        try:
            await bot.delete_message(chat_id, story_message.message_id)
            print("✅ Story deleted")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"❌ Story error: {e}")
        return False

# ========== SCAN FUNCTION ==========
async def scan_users_and_groups():
    """Scan database to update user and group information"""
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        
        # First update leader names
        await get_leader_names()
        
        # Update leader names in database
        for leader_id, name in leader_names.items():
            c.execute("UPDATE users SET first_name = ? WHERE user_id = ?", (name, leader_id))
        
        # Get all user IDs from command logs
        c.execute("SELECT DISTINCT user_id FROM command_logs WHERE user_id IS NOT NULL")
        user_ids = [row[0] for row in c.fetchall()]
        
        updated_users = 0
        for user_id in user_ids:
            if user_id and user_id > 0:  # Valid user ID
                try:
                    user = await bot.get_chat(user_id)
                    if user.type == 'private':
                        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                        if not c.fetchone():
                            c.execute("INSERT INTO users (user_id, username, first_name, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                                     (user_id, user.username, user.first_name, datetime.now().isoformat(), datetime.now().isoformat()))
                            updated_users += 1
                            print(f"✅ Added user: {user.first_name} ({user_id})")
                        else:
                            c.execute("UPDATE users SET username = ?, first_name = ?, last_active = ? WHERE user_id = ?",
                                     (user.username, user.first_name, datetime.now().isoformat(), user_id))
                            updated_users += 1
                except Exception as e:
                    print(f"⚠️ Can't access user {user_id}: {e}")
                    continue
        
        # Get groups from command logs
        c.execute("SELECT DISTINCT chat_id FROM command_logs WHERE chat_type IN ('group', 'supergroup') AND chat_id IS NOT NULL")
        chat_ids = [row[0] for row in c.fetchall()]
        
        updated_groups = 0
        for chat_id in chat_ids:
            if chat_id and chat_id < 0:  # Group IDs are negative
                try:
                    chat = await bot.get_chat(chat_id)
                    if chat.type in ['group', 'supergroup']:
                        c.execute("SELECT group_id FROM groups WHERE group_id = ?", (chat_id,))
                        if not c.fetchone():
                            c.execute("INSERT INTO groups (group_id, title, username, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
                                     (chat_id, chat.title, chat.username, datetime.now().isoformat(), datetime.now().isoformat()))
                            updated_groups += 1
                            print(f"✅ Added group: {chat.title} ({chat_id})")
                        else:
                            c.execute("UPDATE groups SET title = ?, username = ?, last_active = ? WHERE group_id = ?",
                                     (chat.title, chat.username, datetime.now().isoformat(), chat_id))
                            updated_groups += 1
                except Exception as e:
                    print(f"⚠️ Can't access group {chat_id}: {e}")
                    continue
        
        conn.commit()
        conn.close()
        
        return f"✅ Scan complete!\n👥 Users updated: {updated_users}\n👥 Groups updated: {updated_groups}"
        
    except Exception as e:
        return f"❌ Scan error: {str(e)}"

# ========== COMMON MESSAGE HANDLER ==========
async def handle_common(message: Message, command: str):
    """Common handler for all commands"""
    user = message.from_user
    chat = message.chat
    
    # Always update user
    update_user(user)
    
    # Update group if in group
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        update_group(chat)
        print(f"📝 Group detected: {chat.title} ({chat.id})")
    
    log_command(user.id, chat.id, chat.type, command)
    return user, chat

# ========== ORIGINAL COMMANDS ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user, chat = await handle_common(message, "start")
    
    welcome_text = f"""✨ <b>Hey {user.first_name}!</b>

🤖 <b>PRO TELEGRAM BOT</b>

🔗 Upload files & get direct links
✨ Wish fortune teller
🎮 Fun games (dice, coin flip)
👑 Admin controls
🌀 Hidden Tempest Cult

📁 <b>Upload:</b> Send <code>/link</code> then any file
🎮 <b>Games:</b> <code>/dice</code> <code>/flip</code> <code>/wish [text]</code>
👤 <b>Profile:</b> <code>/profile</code>
🌀 <b>Tempest:</b> <code>/Tempest_join</code>
📚 <b>All commands:</b> <code>/help</code>"""
    
    await message.answer(welcome_text, parse_mode=ParseMode.HTML)

@dp.message(Command("help"))
async def help_cmd(message: Message):
    user, chat = await handle_common(message, "help")
    
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

🌀 <b>Tempest Cult:</b>
<code>/Tempest_cult</code> - View members
<code>/Tempest_join</code> - Join the cult
<code>/Tempest_progress</code> - Your progress

👑 <b>Admin:</b>
<code>/ping</code> - System status
<code>/logs [days]</code> - View logs (.txt)
<code>/stats</code> - Statistics
<code>/users</code> - User list (.txt)
<code>/admins</code> - List bot admins
<code>/backup</code> - Backup database
<code>/scan</code> - Scan for new users/groups

⚡ <b>Owner:</b>
<code>/pro [id]</code> - Make admin
<code>/toggle</code> - Toggle bot
<code>/broadcast</code> - Send to all users
<code>/broadcast_gc</code> - Send to groups only
<code>/restart</code> - Restart bot
<code>/emergency_stop</code> - Stop bot"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== ADMIN COMMANDS (WORK IN GROUPS TOO) ==========
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
    
    c.execute("SELECT uploads, commands, joined_date, cult_status, cult_rank, sacrifices FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    
    if row:
        uploads, cmds, joined, cult_status, cult_rank, sacrifices = row
        c.execute("SELECT COUNT(*) FROM wishes WHERE user_id = ?", (user.id,))
        wishes = c.fetchone()[0] or 0
        
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
👤 <b>PROFILE: {user.first_name}</b>

📁 <b>Uploads:</b> {uploads}
✨ <b>Wishes:</b> {wishes}
🔧 <b>Commands:</b> {cmds}
📅 <b>Joined:</b> {join_date}
🆔 <b>ID:</b> <code>{user.id}</code>
"""
    
    if cult_status != "none":
        profile_text += f"""
━━━━━━━━━━━━━━━━━━━━
🌪️ <b>TEMPEST CULT</b>
👑 <b>Rank:</b> {cult_rank}
⚔️ <b>Sacrifices:</b> {sacrifices}
━━━━━━━━━━━━━━━━━━━━
"""
    
    profile_text += "\n💡 <b>Next:</b> Try /link to upload files"
    
    await message.answer(profile_text, parse_mode=ParseMode.HTML)

@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    user, chat = await handle_common(message, "stats")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
    # User stats
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM users WHERE cult_status != 'none'")
    cult_members = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    total_admins = c.fetchone()[0] or 0
    
    # Group stats
    c.execute("SELECT COUNT(*) FROM groups")
    total_groups = c.fetchone()[0] or 0
    
    # Upload stats
    c.execute("SELECT COUNT(*) FROM uploads")
    total_uploads = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM wishes")
    total_wishes = c.fetchone()[0] or 0
    
    # Active users (last 7 days)
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute("SELECT COUNT(*) FROM users WHERE last_active >= ?", (week_ago,))
    active_users = c.fetchone()[0] or 0
    
    # Today's activity
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM command_logs WHERE DATE(timestamp) = DATE(?)", (today,))
    today_commands = c.fetchone()[0] or 0
    
    conn.close()
    
    stats_text = f"""
📊 <b>COMPLETE BOT STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👥 <b>USER STATS:</b>
• Total Users: {total_users}
• Active Users (7 days): {active_users}
• Bot Admins: {total_admins}
• Tempest Members: {cult_members}

👥 <b>GROUP STATS:</b>
• Total Groups: {total_groups}

📁 <b>ACTIVITY STATS:</b>
• Total Uploads: {total_uploads}
• Total Wishes: {total_wishes}
• Today's Commands: {today_commands}

━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>PERCENTAGES:</b>
• Active Users: {(active_users/total_users*100 if total_users > 0 else 0):.1f}%
• Tempest Members: {(cult_members/total_users*100 if total_users > 0 else 0):.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    user, chat = await handle_common(message, "ping")
    
    if not await is_admin(user.id):
        await message.answer("🚫 Admin only")
        return
    
    start_ping = time.time()
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM groups")
    groups = c.fetchone()[0] or 0
    conn.close()
    
    ping_ms = (time.time() - start_ping) * 1000
    
    await message.answer(
        f"🏓 <b>PONG!</b>\n\n"
        f"⚡ <b>Response:</b> {ping_ms:.0f}ms\n"
        f"👥 <b>Users:</b> {users}\n"
        f"👥 <b>Groups:</b> {groups}\n"
        f"🕒 <b>Uptime:</b> {int(time.time() - start_time)}s\n"
        f"🔧 <b>Status:</b> {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}",
        parse_mode=ParseMode.HTML
    )

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
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    
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

@dp.message(Command("pro"))
async def pro_cmd(message: Message):
    user, chat = await handle_common(message, "pro")
    
    if user.id != OWNER_ID:
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

@dp.message(Command("toggle"))
async def toggle_cmd(message: Message):
    user, chat = await handle_common(message, "toggle")
    
    if not await is_admin(user.id):
        return
    
    global bot_active
    bot_active = not bot_active
    status = "🟢 ACTIVE" if bot_active else "🔴 PAUSED"
    await message.answer(f"✅ Bot is now {status}")

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast_start")
    
    if not await is_admin(user.id):
        return
    
    broadcast_state[user.id] = True
    await message.answer(
        "📢 <b>Send broadcast message now:</b>\n"
        "• Text message\n"
        "• Photo with caption\n"
        "• Video with caption\n\n"
        "⚠️ <b>Next message will be broadcasted to ALL USERS</b>\n"
        "❌ <code>/cancel</code> to abort",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("broadcast_gc"))
async def broadcast_gc_cmd(message: Message):
    user, chat = await handle_common(message, "broadcast_gc_start")
    
    if not await is_admin(user.id):
        return
    
    broadcast_state[user.id] = "group"
    await message.answer(
        "📢 <b>Send group broadcast message now:</b>\n"
        "• Text message only\n"
        "• Will send to ALL GROUPS\n\n"
        "⚠️ <b>Next message will be broadcasted to GROUPS</b>\n"
        "❌ <code>/cancel</code> to abort",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("backup"))
async def backup_cmd(message: Message):
    user, chat = await handle_common(message, "backup")
    
    if not await is_admin(user.id):
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/backup_{timestamp}.db"
    
    try:
        shutil.copy2("data/bot.db", backup_file)
        await message.answer_document(
            FSInputFile(backup_file),
            caption=f"💾 Backup {timestamp}\n✅ Database backed up successfully"
        )
    except Exception as e:
        await message.answer(f"❌ Backup failed: {str(e)}")
        log_error(user.id, "backup", e)

@dp.message(Command("restart"))
async def restart_cmd(message: Message):
    user, chat = await handle_common(message, "restart")
    
    if user.id != OWNER_ID:
        return
    
    await message.answer("🔄 <b>Bot restart initiated...</b>\n\nNote: On Railway, the bot auto-restarts when needed.", parse_mode=ParseMode.HTML)
    print("⚠️ Restart command received - continuing operation")

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
        c.execute("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,))
        
        # If cult member, add sacrifice
        c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
        cult_status = c.fetchone()
        if cult_status and cult_status[0] != 'none':
            c.execute("UPDATE users SET sacrifices = sacrifices + 1 WHERE user_id = ?", (user.id,))
        
        c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)",
                 (user.id, datetime.now().isoformat(), result['url'], file_type, file_size))
        conn.commit()
        conn.close()
        
        # Send result
        size_kb = file_size / 1024
        size_mb = size_kb / 1024
        size_text = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{size_kb:.1f} KB"
        
        result_text = f"""✅ <b>Upload Complete!</b>

📁 <b>Type:</b> {file_type}
💾 <b>Size:</b> {size_text}
👤 <b>By:</b> {user.first_name}

🔗 <b>Direct Link:</b>
<code>{result['url']}</code>

📤 Permanent link • No expiry • Share anywhere"""
        
        # Add cult message if member
        if cult_status and cult_status[0] != 'none':
            result_text += f"\n\n🌀 <i>+1 sacrifice to the Tempest</i>"
        
        await msg.edit_text(result_text, parse_mode=ParseMode.HTML)
        log_command(user.id, chat.id, chat.type, "upload", True)
        
    except Exception as e:
        await msg.edit_text("❌ Error uploading file")
        log_error(user.id, "upload", e)

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    user, chat = await handle_common(message, "cancel")
    
    if user.id in upload_waiting:
        upload_waiting[user.id] = False
        await message.answer("❌ Upload cancelled")

# ========== GAMES ==========
@dp.message(Command("wish"))
async def wish_cmd(message: Message):
    user, chat = await handle_common(message, "wish")
    
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
    user, chat = await handle_common(message, "dice")
    
    msg = await message.answer("🎲 <b>Rolling dice...</b>", parse_mode=ParseMode.HTML)
    
    # Animation
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
    
    # Animation
    for i in range(5):
        await msg.edit_text(f"🪙 <b>Flipping...</b> {'HEADS' if i % 2 == 0 else 'TAILS'}", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.2)
    
    result = random.choice(["HEADS 🟡", "TAILS 🟤"])
    await msg.edit_text(f"🪙 <b>{result}</b>", parse_mode=ParseMode.HTML)

# ========== TEMPEST CULT COMMANDS ==========
@dp.message(Command("Tempest_cult"))
async def tempest_cult_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_cult")
    
    # Load latest leader names
    await get_leader_names()
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, cult_rank, sacrifices FROM users WHERE cult_status != 'none' ORDER BY sacrifices DESC, cult_rank")
    members = c.fetchall()
    conn.close()
    
    cult_text = "🌀 <b>TEMPEST CULT</b>\n\n"
    
    leader_shown = False
    for user_id, name, rank, sacrifices in members:
        # Use latest name from Telegram for leaders
        if user_id in leader_names:
            name = leader_names[user_id]
        
        if rank in ["Supreme Leader", "Vice Chancellor"] and not leader_shown:
            cult_text += "👑 <b>LEADERS:</b>\n"
            leader_shown = True
        
        if rank == "Supreme Leader":
            cult_text += f"👑 {name} - {rank}\n"
        elif rank == "Vice Chancellor":
            cult_text += f"⚔️ {name} - {rank}\n"
        else:
            star_emoji = "⭐" * (min(sacrifices, 5))
            cult_text += f"🌀 {name} - {rank} ({sacrifices}⚔️)\n"
    
    cult_text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    cult_text += "<i>Hidden from ordinary eyes...</i>"
    
    await message.answer(cult_text, parse_mode=ParseMode.HTML)

@dp.message(Command("Tempest_join"))
async def tempest_join_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_join")
    
    # Check if already in cult
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        await message.answer("🌀 <b>Already part of the Tempest!</b>\nUse /Tempest_progress to check your status.", parse_mode=ParseMode.HTML)
        conn.close()
        return
    
    conn.close()
    
    # Start initiation
    pending_joins[user.id] = {
        "name": user.first_name,
        "step": 1
    }
    
    await message.answer(
        "🌀 <b>TEMPEST INITIATION</b>\n\n"
        "⚡ The storm senses your presence...\n"
        "🌩️ Choose your sacrifice:",
        parse_mode=ParseMode.HTML
    )
    
    # Sacrifice selection
    keyboard = InlineKeyboardBuilder()
    for i in range(1, 5):
        keyboard.add(InlineKeyboardButton(text=f"{i}", callback_data=f"sacrifice_{i}"))
    keyboard.add(InlineKeyboardButton(text="❌", callback_data="sacrifice_cancel"))
    keyboard.adjust(5)
    
    await message.answer(
        "<b>What do you sacrifice?</b>\n\n"
        "1. Your firstborn's eternal soul\n"
        "2. A diamond worth a kingdom\n"  
        "3. Your complete internet history\n"
        "4. Your legendary gaming account\n\n"
        "<i>Choose a number...</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data.startswith("sacrifice_"))
async def handle_sacrifice(callback: CallbackQuery):
    user = callback.from_user
    chat_id = callback.message.chat.id
    
    if user.id not in pending_joins:
        await callback.answer("❌ Initiation expired!", show_alert=True)
        return
    
    if callback.data == "sacrifice_cancel":
        del pending_joins[user.id]
        await callback.message.edit_text("🌀 <b>Initiation cancelled.</b>", parse_mode=ParseMode.HTML)
        await callback.answer()
        return
    
    # Map sacrifice numbers
    sacrifices = {
        "1": "🩸 Firstborn's Soul",
        "2": "💎 Diamond Collection",
        "3": "📜 Internet History", 
        "4": "🎮 Gaming Account"
    }
    
    sacrifice_num = callback.data.split("_")[1]
    sacrifice = sacrifices.get(sacrifice_num, "Unknown")
    
    pending_joins[user.id]["sacrifice"] = sacrifice
    
    await callback.message.edit_text(
        f"⚡ <b>Sacrifice Accepted:</b> {sacrifice}\n\n"
        f"🌀 Beginning the Tempest Saga...",
        parse_mode=ParseMode.HTML
    )
    
    # Show animated story
    await animate_tempest_story(chat_id, pending_joins[user.id]["name"])
    
    # Add to cult after story
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cult_status = 'member', cult_rank = 'Initiate', cult_join_date = ?, sacrifices = 1 WHERE user_id = ?",
             (datetime.now().isoformat(), user.id))
    conn.commit()
    conn.close()
    
    # Send completion message
    await callback.message.answer(
        f"✅ <b>INITIATION COMPLETE!</b>\n\n"
        f"🌀 Welcome to the Tempest, {pending_joins[user.id]['name']}!\n"
        f"⚡ Rank: Initiate\n"
        f"💀 Sacrifice: {sacrifice}\n\n"
        f"<i>The eternal storm welcomes you...</i>\n\n"
        f"Use /Tempest_progress to track your growth",
        parse_mode=ParseMode.HTML
    )
    
    # Cleanup
    if user.id in pending_joins:
        del pending_joins[user.id]
    
    await callback.answer()

@dp.message(Command("Tempest_progress"))
async def tempest_progress_cmd(message: Message):
    user, chat = await handle_common(message, "tempest_progress")
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT cult_status, cult_rank, sacrifices, cult_join_date FROM users WHERE user_id = ?", (user.id,))
    result = c.fetchone()
    
    if result and result[0] != "none":
        status, rank, sacrifices, join_date = result
        
        try:
            join_dt = datetime.fromisoformat(join_date)
            days = (datetime.now() - join_dt).days
            time_text = f"{days} days" if days > 0 else "Today"
        except:
            time_text = "Recently"
        
        # Progress calculation
        next_rank = "Adept" if sacrifices < 10 else "Master"
        needed = max(0, 10 - sacrifices)
        progress = min(sacrifices * 10, 100)
        
        progress_text = f"""
🌀 <b>TEMPEST PROGRESS</b>

👤 <b>Member:</b> {user.first_name}
👑 <b>Rank:</b> {rank}
⚔️ <b>Sacrifices:</b> {sacrifices}
📅 <b>Member Since:</b> {time_text}

<b>Progress:</b> [{'▓' * (progress // 10)}{'░' * (10 - progress // 10)}] {progress}%
<b>Next Rank:</b> {next_rank}
<b>Sacrifices Needed:</b> {needed}

⚡ <i>Each upload = 1 sacrifice</i>
        """
    else:
        progress_text = """
🌀 <b>TEMPEST PROGRESS</b>

👤 <b>Status:</b> Not a member

⚡ Use /Tempest_join to begin
🌩️ The storm awaits worthy souls...
        """
    
    conn.close()
    await message.answer(progress_text, parse_mode=ParseMode.HTML)

# ========== BROADCAST HANDLERS ==========
@dp.message()
async def handle_broadcast(message: Message):
    user = message.from_user
    chat = message.chat
    
    # Handle user broadcast
    if user.id in broadcast_state and broadcast_state[user.id] is True:
        broadcast_state[user.id] = False
        
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
    
    # Handle group broadcast
    elif user.id in broadcast_state and broadcast_state[user.id] == "group":
        broadcast_state[user.id] = False
        
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
                await bot.send_message(group_id, f"📢 {message.text}")
                success += 1
                await asyncio.sleep(0.1)
            except:
                continue
        
        await status_msg.edit_text(f"✅ Sent to {success}/{total} groups")

# ========== MAIN ==========
async def main():
    print("🚀 PRO BOT v4.0 STARTING...")
    print("✅ Database initialized")
    print("🌀 Tempest Leaders added permanently")
    
    # Load leader names from Telegram
    await get_leader_names()
    
    print(f"👑 Supreme Leader: {leader_names.get(TEMPEST_LEADER, 'Ravijah')}")
    print(f"⚔️ Vice Chancellor 1: {leader_names.get(TEMPEST_VICE1, 'Bablu')}")
    print(f"⚔️ Vice Chancellor 2: {leader_names.get(TEMPEST_VICE2, 'Nocis_Creed')}")
    
    print("👥 User/Group detection: ACTIVE")
    print("🎬 Story: ONE MESSAGE ONLY")
    print("📡 All commands: READY")
    print("━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔧 Ready for Railway deployment!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped gracefully")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
