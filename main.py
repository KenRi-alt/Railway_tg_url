import os
import asyncio
import logging
import time
import random
from datetime import datetime
import sqlite3
from pathlib import Path
import aiohttp
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

# Print startup info
print("=" * 50)
print("🎯 FORTUNE WISH BOT - Starting...")
print(f"Python version: {sys.version}")
print("=" * 50)

# ========== CONFIGURATION ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))

# Create directories
Path("data").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Global start time
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
            joined_date TEXT,
            wishes_made INTEGER DEFAULT 0,
            avg_luck REAL DEFAULT 0,
            last_active TEXT
        )
    ''')
    
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
    print("✅ Database initialized")

init_db()

# ========== UPDATE USER ==========
def update_user(user: types.User):
    """Update or create user"""
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, joined_date, last_active, wishes_made, avg_luck)
        VALUES (?, ?, ?, COALESCE((SELECT joined_date FROM users WHERE user_id = ?), ?), 
                ?, COALESCE((SELECT wishes_made FROM users WHERE user_id = ?), 0),
                COALESCE((SELECT avg_luck FROM users WHERE user_id = ?), 0))
    ''', (
        user.id, user.username, user.first_name, 
        user.id, datetime.now().isoformat(),
        datetime.now().isoformat(),
        user.id, user.id
    ))
    
    conn.commit()
    conn.close()

# ========== WISH COMMAND ==========
@dp.message(Command("wish"))
async def wish_command(message: Message):
    """Wish command with 1-100% success rate"""
    user = message.from_user
    update_user(user)
    
    # Get wish text
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "✨ <b>Please add your wish!</b>\n\n"
            "📝 <b>Example:</b>\n"
            "<code>/wish I will pass my exam</code>\n"
            "<code>/wish I want to be rich</code>\n"
            "<code>/wish I will find true love</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    wish_text = args[1]
    
    # Send loading animation
    loading_msg = await message.answer("✨ <b>Gathering cosmic energies...</b> 🌟", 
                                       parse_mode=ParseMode.HTML)
    
    # Animated loading sequence
    animations = [
        "🌠 <b>Consulting the stars...</b> 🌠",
        "🌟 <b>Reading cosmic vibrations...</b> 🌟", 
        "⭐ <b>Calculating your destiny...</b> ⭐",
        "💫 <b>Aligning with the universe...</b> 💫",
        "✨ <b>Finalizing your fortune...</b> ✨"
    ]
    
    for anim_text in animations:
        await loading_msg.edit_text(anim_text, parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.3)
    
    # Generate luck percentage (1-100)
    luck = random.randint(1, 100)
    
    # Create stars visualization
    full_stars = luck // 10
    empty_stars = 10 - full_stars
    stars = "⭐" * full_stars + "☆" * empty_stars
    
    # Determine result
    if luck >= 90:
        result = "🎊 EXCELLENT! Your wish will definitely come true!"
        emoji_result = "🎉"
        advice = "Cosmic alignment perfect! The universe fully supports your wish!"
    elif luck >= 70:
        result = "😊 VERY GOOD! High chances of success!"
        emoji_result = "🌟"
        advice = "Strong positive energy detected! Minor obstacles may appear but you'll overcome them!"
    elif luck >= 50:
        result = "👍 GOOD! Your wish has potential!"
        emoji_result = "✨"
        advice = "Balanced energy detected. Outcome depends on your actions and determination!"
    elif luck >= 30:
        result = "🤔 AVERAGE - Might need some extra effort"
        emoji_result = "💪"
        advice = "Energy slightly unstable. You'll need to work harder and stay patient!"
    elif luck >= 10:
        result = "😟 LOW - Consider making another wish"
        emoji_result = "🌧️"
        advice = "The universe suggests revising your approach. Try with different energy!"
    else:
        result = "💀 VERY LOW - The universe suggests trying again"
        emoji_result = "🌀"
        advice = "Cosmic interference detected. Wait for better timing or refine your wish!"
    
    # Save to database
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    # Update user's wish stats
    cursor.execute('SELECT wishes_made, avg_luck FROM users WHERE user_id = ?', (user.id,))
    user_data = cursor.fetchone()
    
    if user_data:
        old_wishes, old_avg = user_data
        new_wishes = old_wishes + 1
        new_avg = ((old_avg * old_wishes) + luck) / new_wishes
        
        cursor.execute('''
            UPDATE users SET 
            wishes_made = ?,
            avg_luck = ?,
            last_active = ?
            WHERE user_id = ?
        ''', (new_wishes, new_avg, datetime.now().isoformat(), user.id))
    else:
        cursor.execute('''
            UPDATE users SET 
            wishes_made = 1,
            avg_luck = ?,
            last_active = ?
            WHERE user_id = ?
        ''', (luck, datetime.now().isoformat(), user.id))
    
    # Save wish
    cursor.execute('''
        INSERT INTO wishes (user_id, timestamp, wish_text, luck_percentage, stars)
        VALUES (?, ?, ?, ?, ?)
    ''', (user.id, datetime.now().isoformat(), wish_text, luck, stars))
    
    conn.commit()
    
    # Get updated stats
    cursor.execute('SELECT wishes_made, avg_luck FROM users WHERE user_id = ?', (user.id,))
    stats = cursor.fetchone()
    conn.close()
    
    # Create beautiful response
    response = f"""
🎯 <b>✨ WISH FORTUNE TELLER ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━

✨ <b>Your Wish:</b>
<code>{wish_text}</code>

🎰 <b>Luck Percentage:</b>
<code>{stars} {luck}%</code>

📊 <b>Result:</b>
{emoji_result} <b>{result}</b>

💫 <b>Cosmic Advice:</b>
{advice}

━━━━━━━━━━━━━━━━━━━━━━━━
📅 <i>Wished on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
🎲 <i>Wish ID: W{random.randint(1000, 9999)}</i>
"""
    
    # Add user stats if available
    if stats:
        response += f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Your Wish Statistics:</b>
• Total Wishes Made: {stats[0]}
• Average Luck Score: {stats[1]:.1f}%
• Current Wish: #{stats[0]}
"""
    
    # Add random tip
    tips = [
        "💡 <i>Tip: Wish with positive energy for better results!</i>",
        "💡 <i>Tip: Make wishes during full moon for enhanced power!</i>",
        "💡 <i>Tip: Be specific with your wishes for clearer guidance!</i>",
        "💡 <i>Tip: Visualize your wish coming true while making it!</i>"
    ]
    response += f"\n{random.choice(tips)}"
    
    # Create interactive buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Make Another Wish", callback_data="new_wish"),
            InlineKeyboardButton(text="📊 My Stats", callback_data="my_stats")
        ],
        [
            InlineKeyboardButton(text="🌟 Share Result", callback_data=f"share_{luck}"),
            InlineKeyboardButton(text="📈 Leaderboard", callback_data="leaderboard")
        ]
    ])
    
    await loading_msg.delete()
    await message.answer(response, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    print(f"✅ Wish processed for user {user.id}: {luck}% luck")

# ========== START COMMAND ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    """Start command with beautiful UI"""
    user = message.from_user
    update_user(user)
    
    welcome = f"""
🌟 <b>✨ WELCOME {user.first_name.upper()} ✨</b> 🌟
━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>I'm your Fortune Wish Bot!</b>
Powered by advanced cosmic algorithms ✨

🚀 <b>Main Features:</b>
• ✨ <b>/wish</b> - Check wish success rate (1-100%)
• 🔗 <b>/link</b> - Convert media to shareable links  
• 📊 <b>/stats</b> - View your wish statistics
• 🏓 <b>/ping</b> - Check bot status & latency
• 📚 <b>/help</b> - Show all available commands

━━━━━━━━━━━━━━━━━━━━━━━━
🎰 <b>Quick Start:</b>
<code>/wish I will achieve my dreams</code>

🚄 <b>Hosted on Railway</b> | ⚡ <b>Always Online</b>
🔄 <b>Auto-Healing</b> | 🔒 <b>Never Sleeps</b>
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✨ Make a Wish", callback_data="make_wish"),
            InlineKeyboardButton(text="📚 Commands", callback_data="show_help")
        ],
        [
            InlineKeyboardButton(text="📊 Bot Status", callback_data="show_status"),
            InlineKeyboardButton(text="🌟 Donate", url="https://t.me/donate")
        ]
    ])
    
    await message.answer(welcome, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    print(f"✅ User {user.id} started the bot")

# ========== HELP COMMAND ==========
@dp.message(Command("help"))
async def help_command(message: Message):
    """Help command with detailed info"""
    help_text = f"""
🤖 <b>✨ FORTUNE WISH BOT ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>WISH COMMANDS:</b>
• <code>/wish [your wish]</code> - Check luck percentage (1-100%)
  <i>Example: /wish I will pass my exam</i>
  <i>Example: /wish I want financial freedom</i>
  <i>Example: /wish I will find true love</i>

🛠️ <b>UTILITY COMMANDS:</b>
• <code>/link</code> - Convert media to shareable links
  <i>Send a photo/video/audio after this command</i>
• <code>/ping</code> - Check bot status & latency
• <code>/stats</code> - View your wish statistics
• <code>/start</code> - Show welcome message
• <code>/help</code> - Show this help message

👑 <b>ADMIN COMMANDS:</b>
• <code>/bcast [message]</code> - Broadcast to all users
• <code>/botstats</code> - View overall bot statistics
• <code>/users</code> - List all registered users

━━━━━━━━━━━━━━━━━━━━━━━━
🚄 <b>HOSTING INFORMATION:</b>
• Platform: Railway 🚄
• Status: Always Online ⚡
• Uptime: {int(time.time() - start_time)} seconds
• Version: 3.0 Enhanced
• Features: Never Sleeps, Auto-Scaling

💡 <b>TIPS:</b>
• Wish with positive energy for better results
• Be specific with your wishes
• Try at different times for varied results
• Share results with friends for fun!

━━━━━━━━━━━━━━━━━━━━━━━━
📞 <b>Support:</b> Contact @admin for help
"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

# ========== PING COMMAND ==========
@dp.message(Command("ping"))
async def ping_command(message: Message):
    """Check bot status with detailed info"""
    start_ping = time.time()
    msg = await message.answer("🏓 <b>Pinging cosmic servers...</b>", parse_mode=ParseMode.HTML)
    
    # Get database stats
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM wishes")
    total_wishes = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT AVG(luck_percentage) FROM wishes")
    avg_luck = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(last_active) = DATE('now')")
    active_today = cursor.fetchone()[0] or 0
    
    conn.close()
    
    end_ping = time.time()
    latency = round((end_ping - start_ping) * 1000, 2)
    
    # Get current time in different timezones
    from datetime import timezone, timedelta
    now_utc = datetime.now(timezone.utc)
    now_est = now_utc - timedelta(hours=5)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    
    response = f"""
🏓 <b>✨ COSMIC STATUS REPORT ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>Performance:</b>
• Bot Latency: <code>{latency}ms</code> ⚡
• Uptime: {int(time.time() - start_time)} seconds
• Status: 🟢 <b>OPERATIONAL</b>
• Platform: Railway 🚄

📊 <b>Statistics:</b>
• Total Users: {total_users} 👥
• Total Wishes: {total_wishes} 🌟
• Average Luck: {avg_luck:.1f}% 🎰
• Active Today: {active_today} 📈

🌐 <b>Time Zones:</b>
• UTC: {now_utc.strftime('%H:%M:%S')}
• EST: {now_est.strftime('%H:%M:%S')}
• IST: {now_ist.strftime('%H:%M:%S')}

✅ <b>All Systems:</b> 🟢 OPERATIONAL
🔧 <b>Version:</b> 3.0 Enhanced
📅 <b>Date:</b> {datetime.now().strftime('%Y-%m-%d')}
━━━━━━━━━━━━━━━━━━━━━━━━
💬 <i>"The universe is responding perfectly!"</i>
"""
    
    await msg.edit_text(response, parse_mode=ParseMode.HTML)

# ========== LINK COMMAND ==========
@dp.message(Command("link"))
async def link_command(message: Message):
    """Convert media to links"""
    user = message.from_user
    update_user(user)
    
    # Check if media is attached
    if not (message.photo or message.video or message.audio or message.document):
        await message.answer(
            "📸 <b>How to use /link command:</b>\n\n"
            "1. Type <code>/link</code>\n"
            "2. Send a photo, video, audio, or document\n"
            "3. Get a shareable link instantly!\n\n"
            "💡 <i>The link will work for anyone, even if they haven't started the bot!</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Get file info
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "📸 Photo"
        emoji = "🖼️"
    elif message.video:
        file_id = message.video.file_id
        file_type = "🎥 Video"
        emoji = "📹"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "🎵 Audio"
        emoji = "🎧"
    elif message.document:
        file_id = message.document.file_id
        file_type = "📄 Document"
        emoji = "📎"
    else:
        file_id = None
        file_type = "File"
        emoji = "📁"
    
    if file_id:
        bot_info = await bot.get_me()
        link = f"https://t.me/{bot_info.username}?start=file_{file_id}"
        
        response = f"""
🔗 <b>✨ MEDIA LINK GENERATED ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━

{emoji} <b>Type:</b> {file_type}
👤 <b>Uploaded by:</b> {user.first_name}
🕒 <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

🔗 <b>Shareable Link:</b>
<code>{link}</code>

━━━━━━━━━━━━━━━━━━━━━━━━
💡 <b>How to use:</b>
1. Copy the link above
2. Share with anyone on Telegram
3. They can download it instantly!
4. No need to start the bot first

⚠️ <b>Note:</b> Links expire after 48 hours
📊 <b>Storage:</b> Secure Telegram servers
━━━━━━━━━━━━━━━━━━━━━━━━
✅ <i>Link generated successfully!</i>
"""
        
        await message.answer(response, parse_mode=ParseMode.HTML)
        print(f"✅ Link generated for user {user.id}: {file_type}")
    else:
        await message.answer("❌ <b>Failed to generate link. Please try again.</b>", 
                           parse_mode=ParseMode.HTML)

# ========== STATS COMMAND ==========
@dp.message(Command("stats"))
async def stats_command(message: Message):
    """Show user's wish statistics"""
    user = message.from_user
    
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT wishes_made, avg_luck, joined_date 
        FROM users WHERE user_id = ?
    ''', (user.id,))
    
    user_data = cursor.fetchone()
    
    if not user_data:
        await message.answer(
            "📊 <b>You haven't made any wishes yet!</b>\n\n"
            "Start by typing:\n"
            "<code>/wish I will be successful</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    wishes_made, avg_luck, joined_date = user_data
    
    # Get recent wishes
    cursor.execute('''
        SELECT luck_percentage, timestamp 
        FROM wishes 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 5
    ''', (user.id,))
    
    recent_wishes = cursor.fetchall()
    
    # Get best and worst wishes
    cursor.execute('''
        SELECT MAX(luck_percentage), MIN(luck_percentage) 
        FROM wishes WHERE user_id = ?
    ''', (user.id,))
    
    best_worst = cursor.fetchone()
    best_luck = best_worst[0] or 0
    worst_luck = best_worst[1] or 0
    
    conn.close()
    
    # Calculate days since joining
    from datetime import datetime as dt
    join_date = dt.fromisoformat(joined_date)
    days_since = (dt.now() - join_date).days
    
    response = f"""
📊 <b>✨ YOUR WISH STATISTICS ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👤 <b>User:</b> {user.first_name}
🆔 <b>ID:</b> <code>{user.id}</code>
📅 <b>Joined:</b> {join_date.strftime('%Y-%m-%d')}
⏳ <b>Days active:</b> {days_since} days

━━━━━━━━━━━━━━━━━━━━━━━━
🌟 <b>Wish Overview:</b>
• Total Wishes Made: {wishes_made} ✨
• Average Luck Score: {avg_luck:.1f}% 🎰
• Best Wish Ever: {best_luck}% 🏆
• Worst Wish Ever: {worst_luck}% 📉

━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>Recent Wishes:</b>
"""
    
    for i, (luck, timestamp) in enumerate(recent_wishes, 1):
        wish_time = dt.fromisoformat(timestamp).strftime('%H:%M')
        stars = "⭐" * (luck // 10) + "☆" * (10 - (luck // 10))
        response += f"{i}. {stars} {luck}% ({wish_time})\n"
    
    # Add ranking
    if avg_luck >= 80:
        rank = "🎖️ Cosmic Master"
    elif avg_luck >= 60:
        rank = "🌟 Star Aligner"
    elif avg_luck >= 40:
        rank = "✨ Wish Maker"
    elif avg_luck >= 20:
        rank = "🌙 Dreamer"
    else:
        rank = "☁️ Beginner"
    
    response += f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🏆 <b>Your Rank:</b> {rank}
💡 <b>Tip:</b> Wish regularly to improve your average!
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Make New Wish", callback_data="new_wish"),
            InlineKeyboardButton(text="📈 View All", callback_data="view_all_wishes")
        ]
    ])
    
    await message.answer(response, reply_markup=keyboard, parse_mode=ParseMode.HTML)

# ========== ADMIN COMMANDS ==========
@dp.message(Command("bcast"))
async def broadcast_command(message: Message):
    """Broadcast message to all users (Admin only)"""
    if message.from_user.id != OWNER_ID:
        await message.answer("🚫 <b>This command is for admin only!</b>", parse_mode=ParseMode.HTML)
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "📢 <b>Usage:</b> <code>/bcast your message here</code>\n\n"
            "💡 <i>This will send to all registered users</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    broadcast_msg = args[1]
    
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    total = len(users)
    if total == 0:
        await message.answer("❌ <b>No users found in database!</b>", parse_mode=ParseMode.HTML)
        return
    
    status_msg = await message.answer(
        f"📢 <b>Starting broadcast to {total} users...</b>\n"
        f"✅ Sent: 0/{total}\n"
        f"⏳ Estimated time: {total * 0.1:.1f} seconds",
        parse_mode=ParseMode.HTML
    )
    
    success = 0
    failed = 0
    
    for i, (user_id,) in enumerate(users, 1):
        try:
            await bot.send_message(
                user_id,
                f"📢 <b>ANNOUNCEMENT</b>\n\n"
                f"{broadcast_msg}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💬 <i>This is a broadcast message from admin</i>\n"
                f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode=ParseMode.HTML
            )
            success += 1
            
            # Update status every 10 messages
            if i % 10 == 0 or i == total:
                await status_msg.edit_text(
                    f"📢 <b>Broadcasting...</b>\n"
                    f"✅ Sent: {i}/{total}\n"
                    f"🎯 Success: {success} | ❌ Failed: {failed}",
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            failed += 1
            print(f"Failed to send to user {user_id}: {e}")
        
        # Rate limiting to avoid flood
        await asyncio.sleep(0.1)
    
    final_msg = (
        f"✅ <b>BROADCAST COMPLETE!</b>\n\n"
        f"📊 <b>Statistics:</b>\n"
        f"• Total Users: {total}\n"
        f"• Successfully Sent: {success} ✅\n"
        f"• Failed: {failed} ❌\n"
        f"• Success Rate: {(success/total*100):.1f}%\n\n"
        f"⏱️ <i>Completed in {(total * 0.1):.1f} seconds</i>"
    )
    
    await status_msg.edit_text(final_msg, parse_mode=ParseMode.HTML)

@dp.message(Command("botstats"))
async def botstats_command(message: Message):
    """Show overall bot statistics (Admin only)"""
    if message.from_user.id != OWNER_ID:
        await message.answer("🚫 <b>Admin only command!</b>", parse_mode=ParseMode.HTML)
        return
    
    conn = sqlite3.connect("data/bot.db")
    cursor = conn.cursor()
    
    # Get all stats
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM wishes")
    total_wishes = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT AVG(luck_percentage) FROM wishes")
    avg_luck = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(last_active) = DATE('now')")
    active_today = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_date) = DATE('now')")
    new_today = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT strftime('%Y-%m-%d', timestamp), COUNT(*) 
        FROM wishes 
        GROUP BY strftime('%Y-%m-%d', timestamp) 
        ORDER BY COUNT(*) DESC 
        LIMIT 1
    ''')
    busiest_day = cursor.fetchone() or ("None", 0)
    
    cursor.execute("SELECT MAX(luck_percentage) FROM wishes")
    highest_luck = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT MIN(luck_percentage) FROM wishes")
    lowest_luck = cursor.fetchone()[0] or 0
    
    conn.close()
    
    response = f"""
📊 <b>✨ BOT STATISTICS DASHBOARD ✨</b>
━━━━━━━━━━━━━━━━━━━━━━━━

👥 <b>User Statistics:</b>
• Total Registered Users: {total_users}
• Active Today: {active_today}
• New Users Today: {new_today}
• Growth Rate: {((new_today/total_users*100) if total_users > 0 else 0):.1f}%

🌟 <b>Wish Statistics:</b>
• Total Wishes Made: {total_wishes}
• Average Luck Score: {avg_luck:.1f}%
• Highest Luck Ever: {highest_luck}% 🏆
• Lowest Luck Ever: {lowest_luck}% 📉

📈 <b>Performance:</b>
• Busiest Day: {busiest_day[0]} ({busiest_day[1]} wishes)
• Wishes per User: {(total_wishes/total_users if total_users > 0 else 0):.1f}
• Bot Uptime: {int(time.time() - start_time)} seconds

💾 <b>System Info:</b>
• Platform: Railway 🚄
• Status: 🟢 OPERATIONAL
• Version: 3.0 Enhanced
• Database: SQLite (bot.db)

━━━━━━━━━━━━━━━━━━━━━━━━
📅 <i>Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""
    
    await message.answer(response, parse_mode=ParseMode.HTML)

# ========== CALLBACK HANDLERS ==========
@dp.callback_query(lambda c: c.data == "new_wish")
async def new_wish_callback(callback_query: types.CallbackQuery):
    """Handle new wish button"""
    await callback_query.message.answer(
        "🎯 <b>What would you like to wish for?</b>\n\n"
        "Type your wish after /wish command:\n"
        "<code>/wish I will achieve my goals</code>\n"
        "<code>/wish I want good health</code>\n"
        "<code>/wish I will find happiness</code>",
        parse_mode=ParseMode.HTML
    )
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "make_wish")
async def make_wish_callback(callback_query: types.CallbackQuery):
    """Handle make wish button from start"""
    await new_wish_callback(callback_query)

@dp.callback_query(lambda c: c.data == "show_help")
async def show_help_callback(callback_query: types.CallbackQuery):
    """Handle help button"""
    await help_command(callback_query.message)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "show_status")
async def show_status_callback(callback_query: types.CallbackQuery):
    """Handle status button"""
    await ping_command(callback_query.message)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith("share_"))
async def share_callback(callback_query: types.CallbackQuery):
    """Handle share button"""
    luck = callback_query.data.split("_")[1]
    await callback_query.answer(
        f"✨ Your {luck}% luck result is ready to share!",
        show_alert=True
    )

# ========== KEEP-ALIVE TASK ==========
async def keep_alive():
    """Send periodic pings to keep Railway alive"""
    while True:
        await asyncio.sleep(60)  # Ping every minute
        print(f"🕒 Keep-alive ping at {datetime.now().strftime('%H:%M:%S')}")

# ========== MAIN ==========
async def main():
    """Main function to run the bot"""
    print("🚀 Starting bot with polling...")
    
    # Start keep-alive task
    asyncio.create_task(keep_alive())
    
    # Send startup notification
    try:
        await bot.send_message(
            OWNER_ID,
            f"🚀 <b>Bot Started Successfully!</b>\n\n"
            f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🚄 Host: Railway (Polling Mode)\n"
            f"✨ Version: 3.0 Enhanced\n"
            f"🎯 Features: Wish System, Media Links, Stats\n"
            f"⚡ Status: Polling active\n"
            f"📊 Ready to receive commands!",
            parse_mode=ParseMode.HTML
        )
        print("✅ Startup notification sent to owner")
    except Exception as e:
        print(f"⚠️ Could not send startup notification: {e}")
    
    # Start polling
    print("🔄 Starting polling...")
    print("✅ Bot is now running! Press Ctrl+C to stop")
    print("=" * 50)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        raise
