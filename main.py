#!/usr/bin/env python3
# ========== TEMPEST CREED: ADVANCED MATRIX ENGINE ==========
import os
import sys
import asyncio
import time
import sqlite3
import httpx
import traceback
from datetime import datetime
from pathlib import Path
from io import BytesIO

# Visual Engine
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Telegram Framework
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Keep-Alive Web Server
from aiohttp import web

# ========== CONFIGURATION ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
PORT = int(os.environ.get("PORT", 8080))
UPLOAD_API = "https://catbox.moe/user/api.php"

# Storage Directories
for directory in ["data", "temp", "profile_cards", "backups"]:
    Path(directory).mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
START_TIME = time.time()
upload_waiting = {}

# ========== DATABASE ARCHITECTURE (NEVER FORGETS) ==========
def init_db():
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_date TEXT,
            last_active TEXT,
            uploads INTEGER DEFAULT 0,
            commands INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            strikes INTEGER DEFAULT 0,
            cult_status TEXT DEFAULT 'none',
            cult_rank TEXT DEFAULT 'Wanderer',
            sacrifices INTEGER DEFAULT 0,
            vault_capacity INTEGER DEFAULT 20000000,
            extols INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            file_url TEXT,
            file_type TEXT,
            file_size INTEGER
        );
        CREATE TABLE IF NOT EXISTS story_scrolls (
            chapter_id INTEGER PRIMARY KEY,
            title TEXT,
            content TEXT,
            publish_date TEXT
        );
    ''')
    
    # Register Owner
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, is_admin, cult_rank) VALUES (?, ?, 1, 'Guild Minister')", (OWNER_ID, "TempestCreed"))
    
    # Initialize Story Archive if empty
    c.execute("SELECT COUNT(*) FROM story_scrolls")
    if c.fetchone()[0] == 0:
        genesis_lore = "The sands of Egypt hide ancient witchcraft, a pulse of power waiting for the worthy. The collective begins here..."
        c.execute("INSERT INTO story_scrolls (chapter_id, title, content, publish_date) VALUES (?, ?, ?, ?)",
                 (1, "The Midnight Archive", genesis_lore, datetime.now().isoformat()))
                 
    conn.commit()
    conn.close()

init_db()

# ========== SECURITY MIDDLEWARE (GHOSTING) ==========
class BlacklistMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id if getattr(event, "from_user", None) else None
        if user_id:
            conn = sqlite3.connect("data/bot.db")
            c = conn.cursor()
            c.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
            res = c.fetchone()
            conn.close()
            if res and res[0] == 1:
                return # Silently block
        return await handler(event, data)

dp.message.middleware(BlacklistMiddleware())
dp.callback_query.middleware(BlacklistMiddleware())

# ========== VISUAL GENERATOR (BOUNTY / PROFILE) ==========
async def generate_bounty_card(user_data, profile_bytes=None):
    user_id, first_name, username, uploads, strikes, cult_status, cult_rank, sacrifices, vault, extols = user_data
    
    width, height = 800, 950
    base = Image.new('RGB', (width, height), color='#12121a')
    draw = ImageDraw.Draw(base)
    
    # Draw Background Texture (Tethered Shadow Gradient)
    for i in range(height):
        r, g, b = max(10, int(20 - i*0.01)), max(10, int(20 - i*0.02)), max(20, int(35 - i*0.01))
        draw.line([(0, i), (width, i)], fill=(r, g, b))
    
    try:
        font_large = ImageFont.truetype("data/font.ttf", 65)
        font_med = ImageFont.truetype("data/font.ttf", 35)
        font_small = ImageFont.truetype("data/font.ttf", 25)
    except:
        font_large = font_med = font_small = ImageFont.load_default()

    # Draw Avatar Node
    avatar_size = 400
    if profile_bytes:
        try:
            avatar = Image.open(BytesIO(profile_bytes)).convert("RGBA")
            avatar = avatar.resize((avatar_size, avatar_size), Image.LANCZOS)
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
            
            # Glowing border
            border_radius = avatar_size + 10
            draw.ellipse((width//2 - border_radius//2, 120 - 5, width//2 + border_radius//2, 120 + border_radius - 5), fill='#8c00ff')
            
            avatar_x = width//2 - avatar_size//2
            base.paste(avatar, (avatar_x, 120), mask)
        except Exception as e:
            pass

    # Render Text Vectors
    safe_name = "".join([c for c in first_name if ord(c) < 128])[:15]
    draw.text((width//2, 50), "TEMPEST CREED MATRIX", fill='#ffffff', font=font_large, anchor="mm")
    
    text_y = 560
    draw.text((50, text_y), f"NODE: {safe_name} [{user_id}]", fill='#dcdcdc', font=font_med)
    draw.text((50, text_y + 50), f"RANK: ⚔️ {cult_rank}", fill='#a0a0ff', font=font_med)
    draw.text((50, text_y + 100), f"GLOBAL STRIKES: {strikes}/3", fill='#ff5555' if strikes > 0 else '#55ff55', font=font_med)
    
    draw.line([(50, text_y + 160), (width - 50, text_y + 160)], fill='#555577', width=3)
    
    draw.text((50, text_y + 190), f"DEVOTION: ฿{sacrifices * 15000:,}", fill='#ffcc00', font=font_med)
    draw.text((50, text_y + 240), f"EXTOLS: €{extols}", fill='#00ffcc', font=font_med)
    draw.text((50, text_y + 290), f"VAULT: ฿{sacrifices*1200:,} / {vault:,}", fill='#bbbbbb', font=font_med)
    
    # Progress Bar (XP System)
    xp_progress = (sacrifices % 10) / 10.0 if sacrifices > 0 else 0.05
    bar_x, bar_y, bar_w, bar_h = 50, 900, 700, 25
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], outline='#ffffff', width=2)
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * xp_progress), bar_y + bar_h], fill='#8c00ff')
    
    file_path = f"profile_cards/card_{user_id}.png"
    base.save(file_path, "PNG")
    return file_path

# ========== CORE COMMANDS ==========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "⚡ <b>TEMPEST ENGINE ONLINE.</b>\n\n"
        "<code>/link</code> - Allocate media to matrix\n"
        "<code>/bounty</code> - Extract visual node statistics\n"
        "<code>/story</code> - Read the Shadow Archive scrolls\n",
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("bounty", "profile"))
async def bounty_cmd(message: Message):
    msg = await message.answer("⏳ Rendering visual dashboard...")
    user = message.from_user
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, uploads, strikes, cult_status, cult_rank, sacrifices, vault_capacity, extols FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, first_name) VALUES (?, ?)", (user.id, user.first_name))
        conn.commit()
        row = (user.id, user.first_name, user.username, 0, 0, 'none', 'Wanderer', 0, 20000000, 0)
    conn.close()
    
    profile_bytes = None
    try:
        photos = await bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            file = await bot.get_file(photos.photos[0][-1].file_id)
            pfp_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
            async with httpx.AsyncClient() as client:
                res = await client.get(pfp_url)
                if res.status_code == 200: profile_bytes = res.content
    except: pass

    card_path = await generate_bounty_card(row, profile_bytes)
    await msg.delete()
    await message.answer_photo(FSInputFile(card_path), caption=f"🌀 <b>Manifest Data Extracted for {user.first_name}</b>", parse_mode=ParseMode.HTML)

# ========== MEDIA LINK PIPELINE ==========
@dp.message(Command("link"))
async def link_cmd(message: Message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]: return
    upload_waiting[message.from_user.id] = True
    await message.answer("📁 <b>Buffer open. Stream media file now:</b>\n• Photos, Videos, Audio vectors\n• Max payload: 20MB (Telegram limit)", parse_mode=ParseMode.HTML)

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.sticker | F.animation)
async def handle_file(message: Message):
    user = message.from_user
    if user.id not in upload_waiting or not upload_waiting[user.id]: return
    
    upload_waiting[user.id] = False
    msg = await message.answer("⏳ <b>Encrypting local payload strings...</b>", parse_mode=ParseMode.HTML)
    
    try:
        if message.photo: file_id, file_type = message.photo[-1].file_id, "Photo"
        elif message.video: file_id, file_type = message.video.file_id, "Video"
        elif message.document: file_id, file_type = message.document.file_id, "Document"
        elif message.audio: file_id, file_type = message.audio.file_id, "Audio"
        else: file_id, file_type = message.voice.file_id, "Voice"
        
        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.get(url)
        if res.status_code != 200:
            await msg.edit_text("❌ Data vector collection failed.")
            return
            
        file_data = res.content
        filename = f"matrix_{file_id}"
        files = {'reqtype': (None, 'fileupload'), 'fileToUpload': (filename, file_data)}
        
        await msg.edit_text("☁️ <b>Fusing payload into Catbox Storage Matrices...</b>", parse_mode=ParseMode.HTML)
        async with httpx.AsyncClient(timeout=60) as client:
            upload_res = await client.post(UPLOAD_API, files=files)
            
        if upload_res.status_code == 200 and upload_res.text.startswith('http'):
            final_url = upload_res.text.strip()
            
            conn = sqlite3.connect("data/bot.db")
            c = conn.cursor()
            c.execute("UPDATE users SET uploads = uploads + 1, sacrifices = sacrifices + 1 WHERE user_id = ?", (user.id,))
            c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)",
                     (user.id, datetime.now().isoformat(), final_url, file_type, len(file_data)))
            conn.commit()
            conn.close()
            
            kb = InlineKeyboardBuilder()
            kb.add(InlineKeyboardButton(text="🔗 Share Transmission", url=f"https://t.me/share/url?url={final_url}"))
            await msg.edit_text(f"✅ <b>TRANSMISSION LOCKED TO MATRIX</b>\n\n⚙️ <b>Type:</b> {file_type}\n🔗 <code>{final_url}</code>\n\n🌀 <i>+1 Devotion registered.</i>", parse_mode=ParseMode.HTML, reply_markup=kb.as_markup())
        else:
            await msg.edit_text("❌ Catbox rejection.")
    except Exception as e:
        await msg.edit_text("❌ Operational error encountered.")

# ========== THE SHADOW ARCHIVE (STORY) ==========
@dp.message(Command("story", "lore"))
async def story_cmd(message: Message):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT chapter_id, title FROM story_scrolls ORDER BY chapter_id ASC")
    chapters = c.fetchall()
    conn.close()
    
    if not chapters:
        await message.answer("📜 <b>The Shadow Archive is currently sealed.</b>", parse_mode=ParseMode.HTML)
        return
        
    kb = InlineKeyboardBuilder()
    for ch_id, title in chapters:
        kb.add(InlineKeyboardButton(text=f"📜 Ch {ch_id}: {title}", callback_data=f"read_{ch_id}"))
    kb.adjust(1) 
    
    await message.answer(
        "📖 <b>VOLUME 1: THE TETHERED AWAKENING</b>\n\n"
        "<i>Access the historical scrolls of the collective...</i>\n",
        parse_mode=ParseMode.HTML, reply_markup=kb.as_markup()
    )

@dp.callback_query(F.data.startswith("read_"))
async def read_chapter(callback: CallbackQuery):
    ch_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT title, content, publish_date FROM story_scrolls WHERE chapter_id = ?", (ch_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        title, content, pub_date = row
        try: date_fmt = datetime.fromisoformat(pub_date).strftime("%d %b %Y")
        except: date_fmt = "Ancient"
        text = f"📜 <b>{title}</b>\n<i>Published: {date_fmt}</i>\n\n{content}"
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML)

@dp.message(Command("publish"))
async def publish_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    try:
        raw_text = message.text.split(" ", 1)[1]
        title, content = raw_text.split("|", 1)
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT MAX(chapter_id) FROM story_scrolls")
        next_id = (c.fetchone()[0] or 0) + 1
        c.execute("INSERT INTO story_scrolls (chapter_id, title, content, publish_date) VALUES (?, ?, ?, ?)",
                 (next_id, title.strip(), content.strip(), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        await message.reply(f"✅ <b>SCROLL PUBLISHED.</b>\nChapter {next_id}: {title.strip()} added.", parse_mode=ParseMode.HTML)
    except:
        await message.reply("⚠️ <b>Format Error.</b> Use: <code>/publish Title Here | Story text...</code>", parse_mode=ParseMode.HTML)

# ========== ADVANCED SYSTEM COMMANDS ==========
@dp.message(Command("bfb"))
async def blacklist_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    if not message.reply_to_message: return await message.reply("Target required via reply.")
    target_id = message.reply_to_message.from_user.id
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,))
    conn.commit(); conn.close()
    await message.reply(f"💀 <b>TARGET BLACKLISTED.</b> Node {target_id} ghosted.", parse_mode=ParseMode.HTML)

@dp.message(Command("strike"))
async def strike_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target: return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET strikes = strikes + 1 WHERE user_id = ?", (target.id,))
    c.execute("SELECT strikes FROM users WHERE user_id = ?", (target.id,))
    strikes = c.fetchone()[0]
    
    if strikes >= 3:
        c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target.id,))
        await message.reply(f"⚖️ <b>MAXIMUM STRIKES.</b> {target.first_name} auto-banished.", parse_mode=ParseMode.HTML)
    else:
        await message.reply(f"⚠️ <b>STRIKE ISSUED.</b> {target.first_name}: {strikes}/3 strikes.", parse_mode=ParseMode.HTML)
    conn.commit(); conn.close()

@dp.message(Command("purge"))
async def purge_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    try:
        limit = int(message.text.split()[1])
        for i in range(limit):
            try: await bot.delete_message(message.chat.id, message.message_id - i)
            except: pass
    except: await message.reply("Format: `/purge [number]`", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("commune"))
async def commune_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    text = message.text.replace("/commune ", "")
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = c.fetchall()
    conn.close()
    
    sent = 0
    await message.answer("📡 Initiating global broadcast...")
    for (uid,) in users:
        try:
            await bot.send_message(uid, f"👑 <b>OVERSEER DECREE:</b>\n\n{text}", parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ Broadcast complete. Reached {sent} nodes.")

@dp.message(Command("scan"))
async def scan_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    try:
        search_term = message.text.split(" ", 1)[1]
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id, first_name, strikes, is_banned FROM users WHERE user_id LIKE ? OR first_name LIKE ?", 
                  (f"%{search_term}%", f"%{search_term}%"))
        results = c.fetchall()
        conn.close()
        
        if not results: return await message.reply("No nodes match.")
        res_text = "🔍 <b>SCAN RESULTS:</b>\n"
        for row in results[:10]:
            res_text += f"\nID: <code>{row[0]}</code> | Name: {row[1]} | Banned: {bool(row[3])}"
        await message.answer(res_text, parse_mode=ParseMode.HTML)
    except: await message.reply("Format: `/scan [Query]`", parse_mode=ParseMode.MARKDOWN)

# ========== DIAGNOSTICS ==========
@dp.message(Command("ping"))
async def ping_cmd(message: Message):
    start = time.time()
    msg = await message.answer("📡 Pinging server...")
    latency = round((time.time() - start) * 1000, 2)
    uptime_sec = int(time.time() - START_TIME)
    hours, remainder = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    try: db_size = round(os.path.getsize("data/bot.db") / 1024 / 1024, 2)
    except: db_size = 0.0
    
    stats = (
        f"🏓 <b>TEMPEST ENGINE METRICS</b>\n\n"
        f"⚡ <b>Latency:</b> {latency}ms\n"
        f"⏱️ <b>Uptime:</b> {hours}h {minutes}m {seconds}s\n"
        f"💾 <b>Storage:</b> {db_size} MB"
    )
    await msg.edit_text(stats, parse_mode=ParseMode.HTML)

@dp.message(Command("debug"))
async def debug_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM uploads"); total_up = c.fetchone()[0]
    conn.close()
    
    out = (
        "⚙️ <b>DEBUG MANIFEST</b>\n\n"
        f"Nodes: {total_users}\n"
        f"Vectors: {total_up}\n"
        f"Port: {PORT}"
    )
    await message.answer(out, parse_mode=ParseMode.HTML)

# ========== KEEP-ALIVE WEB SERVER ==========
async def web_handler(request):
    return web.Response(text="Tempest Engine Operating Nominally.")

# ========== MAIN BOOT SEQUENCE ==========
async def main():
    print("🚀 INITIALIZING TEMPEST ENGINE...")
    
    app = web.Application()
    app.router.add_get('/', web_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ Web Server running on port {PORT}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Pipeline aborted.")
