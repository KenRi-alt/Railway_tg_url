import os
import asyncio
import logging
import time
import random
from datetime import datetime
import sqlite3
from pathlib import Path
import aiohttp
from fuzzywuzzy import fuzz

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

# ========== CONFIGURATION ==========
BOT_TOKEN = os.getenv("8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
RAILWAY_PUBLIC_URL = os.getenv("RAILWAY_PUBLIC_URL", "")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RAILWAY_PUBLIC_URL}{WEBHOOK_PATH}"

# Create directories
Path("data").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)

# Initialize bot
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Global states
bot_active = True

# ========== DATABASE ==========
def init_db():
    """Initialize database"""
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_date TEXT,
            wishes_made INTEGER DEFAULT 0,
            avg_luck REAL DEFAULT 0
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
            stars TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ========== WISH COMMAND ==========
@dp.message(Command("wish"))
async def wish_command(message: Message):
    """Enhanced wish command with beautiful UI"""
    user = message.from_user
    
    # Get wish text
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("✨ Please add your wish! Example:\n<code>/wish I will pass my exam</code>")
        return
    
    wish_text = args[1]
    
    # Send loading animation
    loading_msg = await message.answer("✨ *Gathering cosmic energies...* 🌟")
    
    # Animated loading sequence
    animations = ["🌠", "🌟", "⭐", "💫", "✨", "☄️", "🌌", "🪐"]
    for emoji in animations:
        await loading_msg.edit_text(f"{emoji} *Making your wish...* {emoji}")
        await asyncio.sleep(0.2)
    
    # Generate luck percentage (1-100)
    luck = random.randint(1, 100)
    
    # Create stars visualization
    full_stars = luck // 10
    empty_stars = 10 - full_stars
    stars = "⭐" * full_stars + "☆" * empty_stars
    
    # Determine result message
    if luck >= 90:
        result = "🎊 EXCELLENT! Your wish will definitely come true!"
        emoji = "🎉"
    elif luck >= 70:
        result = "😊 VERY GOOD! High chances of success!"
        emoji = "🌟"
    elif luck >= 50:
        result = "👍 GOOD! Your wish has potential!"
        emoji = "✨"
    elif luck >= 30:
        result = "🤔 AVERAGE - Might need some extra effort"
        emoji = "💪"
    elif luck >= 10:
        result = "😟 LOW - Consider making another wish"
        emoji = "🌧️"
    else:
        result = "💀 VERY LOW - The universe suggests trying again"
        emoji = "🌀"
    
    # Save to database
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    # Update user stats
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, joined_date, wishes_made, avg_luck)
        VALUES (?, ?, ?, COALESCE((SELECT joined_date FROM users WHERE user_id = ?), ?), 
                COALESCE((SELECT wishes_made FROM users WHERE user_id = ?), 0) + 1,
                (COALESCE((SELECT avg_luck FROM users WHERE user_id = ?), 0) + ?) / 2)
    ''', (user.id, user.username, user.first_name, user.id, datetime.now().isoformat(), 
          user.id, user.id, luck))
    
    # Save wish
    cursor.execute('''
        INSERT INTO wishes (user_id, timestamp, wish_text, luck_percentage, stars)
        VALUES (?, ?, ?, ?, ?)
    ''', (user.id, datetime.now().isoformat(), wish_text, luck, stars))
    
    conn.commit()
    
    # Get user stats
    cursor.execute('SELECT wishes_made, avg_luck FROM users WHERE user_id = ?', (user.id,))
    stats = cursor.fetchone()
    conn.close()
    
    # Create beautiful response
    response = f"""
🎯 <b>WISH FORTUNE TELLER</b> 🎯

✨ <b>Your Wish:</b>
<code>{wish_text}</code>

🎰 <b>Luck Percentage:</b>
<code>{stars} {luck}%</code>

📊 <b>Result:</b>
{emoji} {result}

📈 <b>Wish Analysis:</b>"""
    
    # Add analysis based on luck
    if luck >= 90:
        response += "\n• Cosmic alignment perfect 🌌"
        response += "\n• Universe fully supports your wish 🌠"
        response += "\n• Manifestation power: MAXIMUM 🔥"
    elif luck >= 70:
        response += "\n• Strong positive energy detected ⚡"
        response += "\n• Minor obstacles ahead ⛰️"
        response += "\n• Success likely with effort 💪"
    elif luck >= 50:
        response += "\n• Balanced energy detected ⚖️"
        response += "\n• Outcome depends on your actions 🎭"
        response += "\n• Keep positive attitude 😌"
    elif luck >= 30:
        response += "\n• Energy slightly unstable 🌪️"
        response += "\n• Need to work harder 🏋️"
        response += "\n• Patience required ⏳"
    else:
        response += "\n• Energy needs recharging 🔋"
        response += "\n• Consider revising wish 🔄"
        response += "\n• Better luck next time 🍀"
    
    response += f"\n\n📅 <i>Wished on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
    response += f"\n🎲 <i>Wish ID: W{random.randint(1000, 9999)}</i>"
    
    if stats:
        response += f"\n\n📊 <b>Your Wish Stats:</b>"
        response += f"\n• Total Wishes: {stats[0]}"
        response += f"\n• Average Luck: {stats[1]:.1f}%"
    
    # Create buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Make Another Wish", callback_data="wish_again")],
        [InlineKeyboardButton(text="📊 View All Wishes", callback_data="my_wishes"),
         InlineKeyboardButton(text="🌟 Share", callback_data=f"share_{luck}")]
    ])
    
    await loading_msg.delete()
    await message.answer(response, reply_markup=keyboard)

# ========== START COMMAND ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    """Start command with beautiful UI"""
    user = message.from_user
    
    # Create welcome message
    welcome = f"""
🌟 <b>Welcome {user.first_name}!</b> 🌟

🎯 <b>I'm your Fortune Wish Bot!</b>
Powered by Railway 🚄 | Always Online ⚡

✨ <b>Main Features:</b>
• /wish - Check wish success rate (1-100%)
• /link - Convert media to shareable links
• /help - Show all commands
• /ping - Check bot status

🎰 <b>Try it now:</b>
<code>/wish I will achieve my dreams</code>

🚀 <b>Hosted on Railway</b> - Never sleeps!
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌟 Make a Wish", callback_data="make_wish")],
        [InlineKeyboardButton(text="📚 Commands", callback_data="help"),
         InlineKeyboardButton(text="📊 Status", callback_data="status")]
    ])
    
    await message.answer(welcome, reply_markup=keyboard)

# ========== HELP COMMAND ==========
@dp.message(Command("help"))
async def help_command(message: Message):
    """Help command"""
    help_text = """
🤖 <b>FORTUNE WISH BOT COMMANDS</b>

🎯 <b>Wish Commands:</b>
/wish [your wish] - Check luck percentage (1-100%)
Example: <code>/wish I will pass my exam</code>

🛠️ <b>Utility Commands:</b>
/link - Convert media to shareable links
/ping - Check bot status and latency
/start - Show welcome message
/help - Show this help

👑 <b>Admin Commands:</b>
/bcast [message] - Broadcast to all users
/stats - View bot statistics
/users - List all users
/logs - View bot logs

🚄 <b>Hosted on Railway</b>
• Always online 24/7
• Auto-healing
• Never sleeps
"""
    
    await message.answer(help_text)

# ========== LINK COMMAND ==========
@dp.message(Command("link"))
async def link_command(message: Message):
    """Convert media to links"""
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    else:
        await message.answer("📸 Please send a photo, video, audio, or document with /link command!")
        return
    
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=file_{file_id}"
    
    await message.answer(
        f"🔗 <b>{file_type.upper()} LINK</b>\n\n"
        f"<code>{link}</code>\n\n"
        f"📤 Share this link with anyone!\n"
        f"🚀 Direct download available"
    )

# ========== PING COMMAND ==========
@dp.message(Command("ping"))
async def ping_command(message: Message):
    """Check bot status"""
    start_time = time.time()
    msg = await message.answer("🏓 Pinging...")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    
    # Get bot stats
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM wishes")
    wishes = cursor.fetchone()[0]
    conn.close()
    
    response = f"""
🏓 <b>PONG!</b>

⚡ <b>Latency:</b> <code>{latency}ms</code>
🚄 <b>Host:</b> Railway
🕒 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

📊 <b>Statistics:</b>
• Total Users: {users}
• Total Wishes: {wishes}
• Status: {'🟢 ACTIVE' if bot_active else '🔴 PAUSED'}

✅ <b>All systems operational</b>
🔧 <b>Version:</b> 2.0 Enhanced
"""
    
    await msg.edit_text(response)

# ========== ADMIN COMMANDS ==========
@dp.message(Command("bcast"))
async def broadcast_command(message: Message):
    """Broadcast message to all users"""
    if message.from_user.id != OWNER_ID:
        await message.answer("🚫 Admin only command!")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📢 Usage: /bcast <message>")
        return
    
    broadcast_msg = args[1]
    
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    total = len(users)
    success = 0
    
    status_msg = await message.answer(f"📢 Broadcasting to {total} users...")
    
    for user_id, in users:
        try:
            await bot.send_message(
                user_id,
                f"📢 <b>BROADCAST</b>\n\n{broadcast_msg}\n\n"
                f"<i>Reply to this message for feedback</i>"
            )
            success += 1
        except:
            pass
        
        # Update status every 10 messages
        if success % 10 == 0:
            await status_msg.edit_text(f"📢 Broadcasting: {success}/{total}")
        await asyncio.sleep(0.1)
    
    await status_msg.edit_text(f"✅ Broadcast complete!\nSent to {success}/{total} users")

# ========== HEALTH CHECK ==========
async def health_check(request):
    """Health endpoint for Railway"""
    return web.json_response({
        "status": "healthy",
        "service": "fortune-wish-bot",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0",
        "uptime": time.time() - start_time
    })

# ========== KEEP-ALIVE TASK ==========
async def keep_alive_task():
    """Prevent Railway from sleeping"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        if RAILWAY_PUBLIC_URL:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{RAILWAY_PUBLIC_URL}/health", timeout=10):
                        logging.info("✅ Keep-alive ping sent")
            except:
                pass

# ========== WEBHOOK SETUP ==========
async def on_startup():
    """Set webhook on startup"""
    if RAILWAY_PUBLIC_URL:
        await bot.set_webhook(WEBHOOK_URL)
        logging.info(f"✅ Webhook set to: {WEBHOOK_URL}")
    
    # Send startup notification
    try:
        await bot.send_message(
            OWNER_ID,
            f"🚀 <b>Bot Started Successfully!</b>\n\n"
            f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🚄 Host: Railway\n"
            f"✨ Version: 2.0 Enhanced\n"
            f"🎯 Features: Wish System, Media Links"
        )
    except:
        pass

# ========== CREATE WEB APP ==========
def create_app():
    app = web.Application()
    app.router.add_get("/health", health_check)
    
    # Register webhook handler
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler
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
    ║      🎯 FORTUNE WISH BOT            ║
    ╠══════════════════════════════════════╣
    ║ 🌟 Version: 2.0 (Enhanced)          ║
    ║ 🚀 Feature: Wish System (1-100%)    ║
    ║ 🚄 Host: Railway                    ║
    ║ ⚡ Status: Starting...              ║
    ╚══════════════════════════════════════╝
    """)
    
    web.run_app(app, host="0.0.0.0", port=port)
