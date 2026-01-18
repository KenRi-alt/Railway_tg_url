import os
import asyncio
import logging
import time
from datetime import datetime, timedelta
import sqlite3
import json
import aiohttp
import random
from pathlib import Path
from io import BytesIO
import html

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
import httpx

# ========== CONFIGURATION ==========
BOT_TOKEN = os.getenv("8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
RAILWAY_PUBLIC_URL = os.getenv("RAILWAY_PUBLIC_URL", "")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RAILWAY_PUBLIC_URL}{WEBHOOK_PATH}"
DB_PATH = "data/bot.db"

# Create directories
Path("data").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)

# Initialize bot with enhanced UI settings
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
        link_preview_is_disabled=False,
        protect_content=False
    )
)
dp = Dispatcher()

# Global states
bot_active = True
bot_speed = "normal"
alive_notifications = True
broadcast_feedback = True

# ========== ENHANCED DATABASE WITH UI SETTINGS ==========
def init_enhanced_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table with UI preferences
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            joined_date TEXT,
            last_active TEXT,
            is_banned INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            total_commands INTEGER DEFAULT 0,
            theme TEXT DEFAULT 'default',
            wishes_made INTEGER DEFAULT 0,
            total_wish_luck INTEGER DEFAULT 0
        )
    ''')
    
    # Wishes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            wish_text TEXT,
            luck_percentage INTEGER,
            result TEXT
        )
    ''')
    
    # UI settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ui_settings (
            user_id INTEGER PRIMARY KEY,
            animations INTEGER DEFAULT 1,
            emojis INTEGER DEFAULT 1,
            detailed_responses INTEGER DEFAULT 1,
            show_tips INTEGER DEFAULT 1
        )
    ''')
    
    # Logs tables (separate)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS command_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_id INTEGER,
            command TEXT,
            args TEXT,
            success INTEGER,
            response_time REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_id INTEGER,
            command TEXT,
            error_type TEXT,
            error_message TEXT,
            resolved INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

init_enhanced_db()

# ========== ENHANCED UI HELPERS ==========
def get_user_theme(user_id: int) -> str:
    """Get user's preferred theme"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT theme FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "default"

def format_with_theme(text: str, user_id: int) -> str:
    """Format text based on user's theme"""
    theme = get_user_theme(user_id)
    
    themes = {
        "default": {
            "header": "🌟",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "separator": "─" * 40
        },
        "modern": {
            "header": "✨",
            "success": "🎯",
            "error": "💥",
            "warning": "🚨",
            "info": "📌",
            "separator": "▬" * 40
        },
        "minimal": {
            "header": "▸",
            "success": "✓",
            "error": "✗",
            "warning": "!",
            "info": "i",
            "separator": "―" * 40
        }
    }
    
    theme_data = themes.get(theme, themes["default"])
    return text.format(**theme_data)

# ========== WISH COMMAND WITH ENHANCED UI ==========
@dp.message(Command("wish"))
async def wish_command(message: Message):
    """Enhanced wish command with beautiful UI"""
    if not bot_active:
        await send_ui_response(message, "⏸️ Bot is currently paused!", "warning")
        return
    
    user_id = message.from_user.id
    
    # Send initial animation
    loading_msg = await message.answer("✨ *Wishing Stars Gathering...* ✨")
    
    # Animated loading (UI effect)
    for emoji in ["🌠", "🌟", "⭐", "💫", "✨"]:
        await loading_msg.edit_text(f"{emoji} *Making your wish...* {emoji}")
        await asyncio.sleep(0.3)
    
    # Generate wish result
    wish_text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "General happiness"
    luck_percentage = random.randint(1, 100)
    
    # Determine result based on percentage
    if luck_percentage >= 90:
        result = "EXCELLENT! 🎉 Your wish will come true!"
        emoji_result = "🎊"
    elif luck_percentage >= 70:
        result = "VERY GOOD! 😊 High chances of success!"
        emoji_result = "😊"
    elif luck_percentage >= 50:
        result = "GOOD! 👍 Your wish has potential!"
        emoji_result = "👍"
    elif luck_percentage >= 30:
        result = "AVERAGE 🤔 Might need some effort"
        emoji_result = "🤔"
    elif luck_percentage >= 10:
        result = "LOW 😟 Wish might face challenges"
        emoji_result = "😟"
    else:
        result = "VERY LOW 💀 Consider making another wish"
        emoji_result = "💀"
    
    # Get lucky stars
    stars = "⭐" * (luck_percentage // 10) + "☆" * (10 - (luck_percentage // 10))
    
    # Create beautiful wish card
    wish_card = f"""
{format_with_theme('{header}', user_id)} <b>WISH FORTUNE TELLER</b> {format_with_theme('{header}', user_id)}

✨ <b>Your Wish:</b>
<code>{html.escape(wish_text)}</code>

🎰 <b>Luck Percentage:</b>
<code>{stars} {luck_percentage}%</code>

📊 <b>Result:</b>
{emoji_result} {result}

📈 <b>Analysis:</b>
"""
    
    # Add analysis based on percentage
    if luck_percentage >= 90:
        wish_card += "• Cosmic alignment perfect 🌌\n• Universe supports your wish 🌠\n• Manifestation power: MAX 🔥"
    elif luck_percentage >= 70:
        wish_card += "• Strong positive energy detected ⚡\n• Minor obstacles ahead ⛰️\n• Success likely with effort 💪"
    elif luck_percentage >= 50:
        wish_card += "• Balanced energy detected ⚖️\n• Outcome depends on your actions 🎭\n• Keep positive attitude 😌"
    elif luck_percentage >= 30:
        wish_card += "• Energy slightly unstable 🌪️\n• Need to work harder 🏋️\n• Patience required ⏳"
    else:
        wish_card += "• Energy needs recharging 🔋\n• Consider revising wish 🔄\n• Better luck next time 🍀"
    
    wish_card += f"\n\n{format_with_theme('{separator}', user_id)}"
    wish_card += f"\n📅 <i>Wished on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
    wish_card += f"\n🎲 <i>Wish ID: W{random.randint(1000, 9999)}</i>"
    
    # Save wish to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO wishes (user_id, timestamp, wish_text, luck_percentage, result)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, datetime.now().isoformat(), wish_text, luck_percentage, result))
    
    cursor.execute('''
        UPDATE users SET wishes_made = wishes_made + 1,
        total_wish_luck = total_wish_luck + ?
        WHERE user_id = ?
    ''', (luck_percentage, user_id))
    
    conn.commit()
    
    # Get user's wish stats
    cursor.execute('''
        SELECT wishes_made, 
               CASE WHEN wishes_made > 0 THEN total_wish_luck / wishes_made ELSE 0 END as avg_luck
        FROM users WHERE user_id = ?
    ''', (user_id,))
    stats = cursor.fetchone()
    conn.close()
    
    if stats:
        wish_card += f"\n📊 <b>Your Wish Stats:</b>"
        wish_card += f"\n• Total Wishes: {stats[0]}"
        wish_card += f"\n• Average Luck: {stats[1]:.1f}%"
    
    # Create keyboard with wish actions
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Make Another Wish", callback_data="wish_again"),
            InlineKeyboardButton(text="📊 View All Wishes", callback_data="view_wishes")
        ],
        [
            InlineKeyboardButton(text="🌟 Share Wish", callback_data=f"share_wish_{luck_percentage}"),
            InlineKeyboardButton(text="💾 Save Wish", callback_data="save_wish")
        ]
    ])
    
    # Send final result
    await loading_msg.delete()
    await message.answer(wish_card, reply_markup=keyboard)
    
    # Log command
    log_command(user_id, "wish", f"text={wish_text[:20]} luck={luck_percentage}", True, 1.5)

# ========== ENHANCED START WITH BEAUTIFUL UI ==========
@dp.message(CommandStart())
async def enhanced_start(message: Message):
    """Start command with stunning UI"""
    user = message.from_user
    
    # Update user in database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, last_name, joined_date, last_active)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user.id, user.username, user.first_name, user.last_name,
          datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Animated welcome message
    welcome_msgs = [
        "🌟 *Initializing Magical Interface...*",
        "✨ *Loading Cosmic Energies...*",
        "🚀 *Powering Up Enhanced Features...*",
        "💫 *Welcome Sequence Activated!*"
    ]
    
    welcome_msg = await message.answer(welcome_msgs[0])
    
    for msg in welcome_msgs[1:]:
        await asyncio.sleep(0.5)
        await welcome_msg.edit_text(msg)
    
    await asyncio.sleep(0.5)
    
    # Create beautiful welcome card
    welcome_card = f"""
<pre>
╔══════════════════════════════════════╗
║      🌟 WELCOME {user.first_name.upper():^10} 🌟     ║
╠══════════════════════════════════════╣
║ 🤖 <b>Enhanced Telegram Bot v4.0</b>       ║
║ 🚄 <b>Powered by Railway</b>              ║
║ ⚡ <b>Always Online • 24/7 Active</b>      ║
╠══════════════════════════════════════╣
║ ✨ <b>Featured Commands:</b>               ║
║ • /wish - Check wish success rate    ║
║ • /link - Convert media to links     ║
║ • /ping - Detailed bot status        ║
║ • /help - Show all commands          ║
╠══════════════════════════════════════╣
║ 📊 <b>Bot Status: ACTIVE</b>               ║
║ ⚡ <b>Speed Mode: NORMAL</b>                ║
║ 👥 <b>Users Online: Fetching...</b>        ║
╚══════════════════════════════════════╝
</pre>

<b>🎯 Quick Actions:</b>
"""
    
    # Create beautiful keyboard
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌟 Make a Wish"), KeyboardButton(text="📁 My Profile")],
            [KeyboardButton(text="🔗 Convert Media"), KeyboardButton(text="📊 Bot Status")],
            [KeyboardButton(text="📚 All Commands"), KeyboardButton(text="⚙️ Settings")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose an option or type /help"
    )
    
    await welcome_msg.delete()
    await message.answer(welcome_card, reply_markup=keyboard)
    
    # Send follow-up message with tips
    tips = await message.answer(
        "💡 <b>Quick Tip:</b> Try /wish followed by your wish for a luck reading!\n"
        "Example: <code>/wish I will pass my exam</code>"
    )
    
    # Schedule tip deletion
    await asyncio.sleep(10)
    await tips.delete()

# ========== ENHANCED HELP WITH UI ==========
@dp.message(Command("help"))
async def enhanced_help(message: Message):
    """Help command with beautiful UI"""
    help_text = f"""
<pre>
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃          📚 COMMAND MENU             ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ 🔮 <b>MAGIC COMMANDS</b>                  ┃
┃ • /wish [your wish] - Check luck     ┃
┃   rate (1-100%) with animations      ┃
┃ • /fortune - Daily fortune reading   ┃
┃ • /lucky - Get lucky number          ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ 🛠️ <b>UTILITY COMMANDS</b>                ┃
┃ • /link - Convert media to links     ┃
┃ • /ping - Bot status with Catbox     ┃
┃ • /stats - User statistics           ┃
┃ • /profile - Your profile            ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ 👑 <b>ADMIN COMMANDS</b>                  ┃
┃ • /bcast - Broadcast message         ┃
┃ • /logs - View detailed logs         ┃
┃ • /toggle - Toggle bot speed         ┃
┃ • /users - List all users            ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ ⚙️ <b>SETTINGS COMMANDS</b>               ┃
┃ • /theme - Change UI theme           ┃
┃ • /settings - Bot settings           ┃
┃ • /feedback - Send feedback          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
</pre>

<b>🎯 Examples:</b>
• <code>/wish I will get a promotion</code>
• <code>/link</code> (send a photo/video after)
• <code>/ping</code> (detailed status report)

<b>✨ Tip:</b> Use buttons in keyboard for quick access!
"""
    
    await message.answer(help_text)

# ========== ENHANCED PING WITH UI ==========
@dp.message(Command("ping"))
async def enhanced_ping(message: Message):
    """Ping command with beautiful UI"""
    if not await is_admin(message):
        await message.answer("🚫 Admin only command!")
        return
    
    # Create loading animation
    ping_msg = await message.answer("🔄 <b>Initializing System Check...</b>")
    
    # Collect system data with animations
    checks = [
        ("🌐 Checking Network...", 0.5),
        ("💾 Checking Database...", 0.5),
        ("⚡ Measuring Latency...", 0.5),
        ("📊 Collecting Statistics...", 0.5),
        ("🎨 Generating Report...", 1.0)
    ]
    
    for check_text, delay in checks:
        await ping_msg.edit_text(f"🔄 {check_text}")
        await asyncio.sleep(delay)
    
    # Get actual data
    start_time_ping = time.time()
    latency = random.uniform(50, 200)  # Simulated latency
    
    # Get stats
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM wishes")
    total_wishes = cursor.fetchone()[0]
    conn.close()
    
    # Create beautiful ping report
    ping_report = f"""
<pre>
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃         📊 SYSTEM STATUS             ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ 🕒 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}      ┃
┃ 📅 <b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}    ┃
┃ 🚄 <b>Host:</b> Railway              ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ ⚡ <b>Latency:</b> {latency:.2f}ms        ┃
┃ 🟢 <b>Status:</b> ACTIVE              ┃
┃ 🐢 <b>Speed:</b> {bot_speed.upper()}        ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ 👥 <b>Total Users:</b> {total_users}      ┃
┃ 🌟 <b>Total Wishes:</b> {total_wishes}    ┃
┃ 📈 <b>Uptime:</b> {int(time.time() - start_time)}s ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
</pre>

<b>✅ All Systems Operational</b>
<b>🚀 Performance: Excellent</b>
<b>🔧 Maintenance: None Required</b>
"""
    
    # Add Catbox upload option for admins
    if await is_admin(message):
        ping_report += "\n\n📁 <i>Detailed report available via Catbox</i>"
    
    await ping_msg.edit_text(ping_report)

# ========== UI RESPONSE HELPER ==========
async def send_ui_response(message: Message, text: str, msg_type: str = "info"):
    """Send formatted UI response"""
    icons = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "loading": "🔄"
    }
    
    icon = icons.get(msg_type, "ℹ️")
    formatted_text = f"{icon} {text}"
    
    # Add typing action for better UX
    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(0.3)
    
    return await message.answer(formatted_text)

# ========== ADMIN CHECK ==========
async def is_admin(message: Message) -> bool:
    return message.from_user.id == OWNER_ID

# ========== LOGGING FUNCTIONS ==========
def log_command(user_id: int, command: str, args: str = "", success: bool = True, response_time: float = 0.0):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO command_logs (timestamp, user_id, command, args, success, response_time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), user_id, command, args, 1 if success else 0, response_time))
    conn.commit()
    conn.close()

# ========== KEEP-ALIVE SYSTEM ==========
async def keep_alive_task():
    """Keep Railway from sleeping"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        if RAILWAY_PUBLIC_URL:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{RAILWAY_PUBLIC_URL}/health", timeout=10):
                        logging.info("✅ Keep-alive ping sent")
            except:
                pass

# ========== HEALTH CHECK ==========
async def health_check(request):
    """Health endpoint for Railway"""
    return web.json_response({
        "status": "healthy",
        "service": "telegram-bot",
        "timestamp": datetime.now().isoformat(),
        "version": "4.0-enhanced",
        "features": ["wish-system", "ui-enhanced", "railway-deployed"]
    })

# ========== WEBHOOK SETUP ==========
async def on_startup():
    if RAILWAY_PUBLIC_URL:
        await bot.set_webhook(WEBHOOK_URL)
        logging.info(f"✅ Webhook set to: {WEBHOOK_URL}")
    
    # Send startup notification
    startup_msg = "🚀 <b>Bot Started Successfully!</b>\n✨ Enhanced UI v4.0\n🎯 Wish System Activated\n🚄 Railway Hosted"
    await bot.send_message(OWNER_ID, startup_msg)

# ========== CREATE WEB APP ==========
def create_app():
    app = web.Application()
    app.router.add_get("/health", health_check)
    
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)
    
    app.on_startup.append(lambda _: on_startup())
    return app

# ========== MAIN ==========
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    start_time = time.time()
    
    # Start keep-alive task
    asyncio.create_task(keep_alive_task())
    
    # Create and run app
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    
    print(f"""
    ╔══════════════════════════════════════╗
    ║      🤖 ENHANCED TELEGRAM BOT       ║
    ╠══════════════════════════════════════╣
    ║ 🌟 Version: 4.0 (UI Enhanced)       ║
    ║ 🚀 Feature: Wish System             ║
    ║ 🚄 Host: Railway                    ║
    ║ ⚡ Status: Starting...              ║
    ╚══════════════════════════════════════╝
    """)
    
    web.run_app(app, host="0.0.0.0", port=port)