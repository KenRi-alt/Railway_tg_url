#!/usr/bin/env python3
# ========== TEMPEST CREED: SUPREME MATRIX CORE ENGINE ==========
import os
import sys
import asyncio
import time
import random
import sqlite3
import json
import httpx
from datetime import datetime
from pathlib import Path
from io import BytesIO

# Visual Engine
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Document Engine
from docx import Document
from docx.shared import Inches

# Telegram Framework
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, CallbackQuery, InlineKeyboardButton
from aiogram.enums import ParseMode, ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Keep-Alive Web Server
from aiohttp import web

# ========== CONFIGURATION & GLOBAL STATE ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "8017048722:AAFVRZytQIWAq6S3r6NXM-CvPbt_agGMk4Y")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
PORT = int(os.environ.get("PORT", 8080))
UPLOAD_API = "https://catbox.moe/user/api.php"

# Ensure all system directories exist perfectly
for directory in ["data", "temp", "profile_cards", "backups"]:
    Path(directory).mkdir(exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
START_TIME = time.time()

# Memory state captures (Backed up persistently)
upload_waiting = {}
broadcast_state = {}
word_conversion_waiting = {}

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
            extols INTEGER DEFAULT 0,
            curse_type TEXT DEFAULT 'none'
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
        CREATE TABLE IF NOT EXISTS bot_state (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    ''')
    
    # Auto-establish the Overseer/Guild Minister account
    c.execute("""
        INSERT INTO users (user_id, first_name, is_admin, cult_rank, vault_capacity) 
        VALUES (?, 'TempestCreed', 1, 'Guild Minister', 999999999)
        ON CONFLICT(user_id) DO UPDATE SET is_admin=1, cult_rank='Guild Minister'
    """, (OWNER_ID,))
    
    # Auto-seed the Genesis Chapter of your novel if it's a fresh boot
    c.execute("SELECT COUNT(*) FROM story_scrolls")
    if c.fetchone()[0] == 0:
        genesis_text = (
            "The sands of Egypt hide ancient witchcraft, a pulse of power waiting for the worthy. "
            "In the depths of the Midnight Archive, the tethered awakening begins. "
            "The collective calls, and the matrix answers."
        )
        c.execute("INSERT INTO story_scrolls (chapter_id, title, content, publish_date) VALUES (?, ?, ?, ?)",
                 (1, "The Midnight Archive", genesis_text, datetime.now().isoformat()))
                 
    conn.commit()
    conn.close()

init_db()

# ========== STATE PERSISTENCE HELPERS ==========
def save_bot_state():
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        state_data = {
            "upload_waiting": upload_waiting, 
            "broadcast_state": broadcast_state,
            "word_conversion_waiting": word_conversion_waiting
        }
        c.execute("INSERT OR REPLACE INTO bot_state (key, value) VALUES ('engine_state', ?)", (json.dumps(state_data),))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"State save failure: {e}")

def load_bot_state():
    global upload_waiting, broadcast_state, word_conversion_waiting
    try:
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT value FROM bot_state WHERE key = 'engine_state'")
        row = c.fetchone()
        conn.close()
        if row:
            data = json.loads(row[0])
            upload_waiting = data.get("upload_waiting", {})
            broadcast_state = data.get("broadcast_state", {})
            word_conversion_waiting = data.get("word_conversion_waiting", {})
    except Exception as e:
        print(f"State load failure: {e}")

load_bot_state()

# ========== SECURITY MIDDLEWARE (GHOST PROTECTION SHIELD) ==========
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
                return  # Silently drop all payloads from banned users
        return await handler(event, data)

dp.message.middleware(BlacklistMiddleware())
dp.callback_query.middleware(BlacklistMiddleware())

# ========== UPGRADED VISUAL GENERATOR (DYNAMIC PFPS + LAYOUT) ==========
async def generate_bounty_card(user_data, profile_bytes=None):
    user_id, username, first_name, _, _, uploads, commands, _, _, strikes, cult_status, cult_rank, sacrifices, vault, extols, curse_type = user_data
    
    width, height = 800, 950
    base = Image.new('RGB', (width, height), color='#12121a')
    draw = ImageDraw.Draw(base)
    
    # Premium Dark Shadow Canvas Gradients
    for i in range(height):
        r = max(10, int(22 - i * 0.015))
        g = max(10, int(18 - i * 0.012))
        b = max(22, int(40 - i * 0.02))
        draw.line([(0, i), (width, i)], fill=(r, g, b))
    
    try:
        font_large = ImageFont.truetype("data/font.ttf", 60)
        font_med = ImageFont.truetype("data/font.ttf", 34)
        font_small = ImageFont.truetype("data/font.ttf", 24)
    except:
        font_large = font_med = font_small = ImageFont.load_default()

    # Dynamic Telegram Profile Photo Circle Placement
    avatar_size = 320
    avatar_x = width // 2 - avatar_size // 2
    avatar_y = 130
    
    if profile_bytes:
        try:
            avatar = Image.open(BytesIO(profile_bytes)).convert("RGBA")
            avatar = avatar.resize((avatar_size, avatar_size), Image.LANCZOS)
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
            
            # Premium Neon Aura Ring Border
            border_glow = '#8c00ff' if curse_type == 'none' else '#ff0055'
            draw.ellipse((avatar_x - 6, avatar_y - 6, avatar_x + avatar_size + 6, avatar_y + avatar_size + 6), fill=border_glow)
            draw.ellipse((avatar_x - 2, avatar_y - 2, avatar_x + avatar_size + 2, avatar_y + avatar_size + 2), fill='#12121a')
            
            base.paste(avatar, (avatar_x, avatar_y), mask)
        except Exception as e:
            print(f"PFP Rendering trace skipped: {e}")
    else:
        # Placeholder Node Vector if user has no avatar
        draw.ellipse((avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size), outline='#444466', width=4)
        draw.text((width//2, avatar_y + avatar_size//2), "NO AVATAR NODE", fill='#555577', font=font_small, anchor="mm")

    # Render Visual Text Elements (Matching your explicit image structure)
    draw.text((width // 2, 60), "TEMPEST CREED MATRIX", fill='#ffffff', font=font_large, anchor="mm")
    
    text_y = 510
    safe_name = "".join([c for c in first_name if ord(c) < 128])[:18]
    
    draw.text((60, text_y), f"👤 NODE IDENTITY: {safe_name}", fill='#ffffff', font=font_med)
    draw.text((60, text_y + 45), f"🆔 SOUL MATRIX ID: [{user_id}]", fill='#8888aa', font=font_small)
    draw.text((60, text_y + 90), f"⚔️ ALIGNMENT RANK: {cult_rank}", fill='#a0a0ff', font=font_med)
    draw.text((60, text_y + 135), f"⚠️ SYSTEM STRIKES: {strikes}/3", fill='#ff5555' if strikes > 0 else '#55ff55', font=font_med)
    
    # Divider Rule Line
    draw.line([(60, text_y + 195), (width - 60, text_y + 195)], fill='#444466', width=3)
    
    # Ledger Vault Metrics
    draw.text((60, text_y + 220), f"💰 DEVOTION BOUNTY: ฿{sacrifices * 15000:,}", fill='#ffcc00', font=font_med)
    draw.text((60, text_y + 265), f"💎 MATRIX EXTOLS: €{extols}", fill='#00ffcc', font=font_med)
    draw.text((60, text_y + 310), f"📦 STORAGE VAULT: ฿{uploads * 1200:,} / {vault:,} BYTES", fill='#bbbbbb', font=font_small)
    
    # Progress Bar (XP System to next Rank tier)
    progress = (sacrifices % 10) / 10.0 if sacrifices > 0 else 0.05
    bar_x, bar_y, bar_w, bar_h = 60, 870, 680, 24
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], outline='#ffffff', width=2)
    draw.rectangle([bar_x + 3, bar_y + 3, bar_x + int((bar_w - 3) * progress), bar_y + bar_h - 3], fill='#8c00ff')
    
    # Cursed Matrix Glitch Shader Overlay
    if curse_type != 'none':
        for _ in range(25):
            g_y = random.randint(0, height)
            draw.line([(0, g_y), (width, g_y)], fill=(random.randint(150, 255), 0, 50), width=random.randint(1, 3))
            
    file_path = f"profile_cards/bounty_{user_id}_{int(time.time())}.png"
    base.save(file_path, "PNG")
    return file_path

# ========== CORE COMMAND PIPELINE ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    await message.answer(
        "⚡ <b>TEMPEST CORE ENGINE INITIALIZED COMPLETELY.</b>\n\n"
        "• Use <code>/bounty</code> to draw your profile card.\n"
        "• Use <code>/link</code> to interface and store media.\n"
        "• Use <code>/story</code> to open the ancient witchcraft archive.", 
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("bounty", "profile"))
async def bounty_manifest_cmd(message: Message):
    msg = await message.answer("🌀 Interrogating data streams... Rendering layout...")
    user = message.from_user
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    
    if not row:
        c.execute("""
            INSERT INTO users (user_id, username, first_name, joined_date, last_active) 
            VALUES (?, ?, ?, ?, ?)
        """, (user.id, user.username, user.first_name, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
        row = c.fetchone()
    conn.close()
    
    # Fetch user's real Telegram PFP dynamically
    profile_bytes = None
    try:
        photos = await bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            file_info = await bot.get_file(photos.photos[0][-1].file_id)
            pfp_endpoint = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
            async with httpx.AsyncClient() as client:
                res = await client.get(pfp_endpoint)
                if res.status_code == 200:
                    profile_bytes = res.content
    except Exception as pfp_err:
        print(f"PFP Fetching bypass engaged: {pfp_err}")

    card_file = await generate_bounty_card(row, profile_bytes)
    await msg.delete()
    await message.answer_photo(
        FSInputFile(card_file), 
        caption=f"🌀 <b>Manifest Data Frame Synchronized for {user.first_name}</b>", 
        parse_mode=ParseMode.HTML
    )

# ========== MEDIA INTERACTION PIPELINE ==========
@dp.message(Command("link"))
async def link_allocation_cmd(message: Message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]: return
    upload_waiting[message.from_user.id] = True
    save_bot_state()
    await message.answer("📁 <b>Data Buffer Open.</b> Send any media file (Photo, Video, Doc) to bind to Catbox:", parse_mode=ParseMode.HTML)

@dp.message(F.photo | F.video | F.document | F.audio | F.voice | F.animation)
async def process_media_stream(message: Message):
    user = message.from_user
    if not upload_waiting.get(user.id): return
    
    upload_waiting[user.id] = False
    save_bot_state()
    msg = await message.answer("⏳ <b>Encrypting stream vectors...</b>", parse_mode=ParseMode.HTML)
    
    try:
        if message.photo: file_id, file_type = message.photo[-1].file_id, "Photo"
        elif message.video: file_id, file_type = message.video.file_id, "Video"
        elif message.document: file_id, file_type = message.document.file_id, "Document"
        else: file_id, file_type = message.animation.file_id, "Animation"
        
        file_obj = await bot.get_file(file_id)
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_obj.file_path}"
        
        async with httpx.AsyncClient(timeout=60) as client:
            file_bytes = await client.get(download_url)
            
        if file_bytes.status_code != 200:
            return await msg.edit_text("❌ Connection vector timed out.")
            
        payload = {'reqtype': (None, 'fileupload'), 'fileToUpload': (f"temp_{file_id}", file_bytes.content)}
        await msg.edit_text("☁️ <b>Injecting payload into Catbox cloud matrix...</b>", parse_mode=ParseMode.HTML)
        
        async with httpx.AsyncClient(timeout=60) as client:
            upload_response = await client.post(UPLOAD_API, files=payload)
            
        if upload_response.status_code == 200 and upload_response.text.startswith("http"):
            final_link = upload_response.text.strip()
            
            conn = sqlite3.connect("data/bot.db")
            c = conn.cursor()
            c.execute("UPDATE users SET uploads = uploads + 1, sacrifices = sacrifices + 1 WHERE user_id = ?", (user.id,))
            c.execute("INSERT INTO uploads (user_id, timestamp, file_url, file_type, file_size) VALUES (?, ?, ?, ?, ?)",
                     (user.id, datetime.now().isoformat(), final_link, file_type, len(file_bytes.content)))
            conn.commit()
            conn.close()
            
            kb = InlineKeyboardBuilder()
            kb.add(InlineKeyboardButton(text="🔗 Share Transmission Link", url=f"https://t.me/share/url?url={final_link}"))
            await msg.edit_text(f"✅ <b>TRANSMISSION EMBEDDED</b>\n\n⚙️ <b>Matrix Class:</b> {file_type}\n🔗 <code>{final_link}</code>\n\n🌀 <i>+1 Devotion recorded.</i>", parse_mode=ParseMode.HTML, reply_markup=kb.as_markup())
        else:
            await msg.edit_text("❌ Catbox api processing error.")
    except Exception as e:
        await msg.edit_text(f"❌ Internal loop crash: {str(e)}")

# ========== THE SHADOW ARCHIVE LORE MOVEMENT ==========
@dp.message(Command("story", "lore"))
async def open_story_archive(message: Message):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT chapter_id, title FROM story_scrolls ORDER BY chapter_id ASC")
    chapters = c.fetchall()
    conn.close()
    
    if not chapters:
        return await message.answer("📜 The historical columns are empty.")
        
    builder = InlineKeyboardBuilder()
    for ch_id, title in chapters:
        builder.add(InlineKeyboardButton(text=f"📜 Scroll {ch_id}: {title}", callback_data=f"read_ch_{ch_id}"))
    builder.adjust(1)
    
    await message.answer(
        "📖 <b>VOLUME 1: THE TETHERED AWAKENING</b>\n"
        "<i>Witchcraft chronicles of the ancient Egyptian sands...</i>\n\n"
        "Select an active node column to read:", 
        parse_mode=ParseMode.HTML, reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("read_ch_"))
async def read_archived_scroll(callback: CallbackQuery):
    ch_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT title, content, publish_date FROM story_scrolls WHERE chapter_id = ?", (ch_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        title, content, pub_date = row
        text = f"📜 <b>CHAPTER {ch_id}: {title}</b>\n\n{content}"
        await callback.message.edit_text(text, parse_mode=ParseMode.HTML)

@dp.message(Command("publish"))
async def publish_lore_chapter(message: Message):
    if message.from_user.id != OWNER_ID: return
    try:
        raw_payload = message.text.split(" ", 1)[1]
        title, content = raw_payload.split("|", 1)
        
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT MAX(chapter_id) FROM story_scrolls")
        next_id = (c.fetchone()[0] or 0) + 1
        c.execute("INSERT INTO story_scrolls (chapter_id, title, content, publish_date) VALUES (?, ?, ?, ?)",
                 (next_id, title.strip(), content.strip(), datetime.now().isoformat()))
        conn.commit(); conn.close()
        await message.reply(f"📜 <b>Volume 1 Chapter Published:</b> {title.strip()} added successfully.")
    except:
        await message.reply("⚠️ Syntax layout: <code>/publish Chapter Name | Story content text...</code>", parse_mode=ParseMode.HTML)

# ========== ADVANCED SYSTEMS MATRIX COMMANDS ==========
@dp.message(Command("excommunicate"))
async def excommunicate_logic(message: Message):
    if message.from_user.id != OWNER_ID: return
    if not message.reply_to_message: return await message.reply("Target identity tracking requires a direct reply.")
    
    target_id = message.reply_to_message.from_user.id
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cult_status='none', cult_rank='Exiled', sacrifices=0, is_banned=1 WHERE user_id = ?", (target_id,))
    conn.commit(); conn.close()
    await message.reply(f"⚡ <b>ALIGNMENT TERMINATED.</b> User {target_id} hard reset and excommunicated.", parse_mode=ParseMode.HTML)

@dp.message(Command("bfb"))
async def blacklist_from_bot_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    if not message.reply_to_message: return await message.reply("Reply to the entity you wish to ghost.")
    
    target_id = message.reply_to_message.from_user.id
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,))
    conn.commit(); conn.close()
    await message.reply(f"💀 <b>SHIELD TERMINAL GHOST ENGAGED.</b> ID {target_id} is dead to the system.")

@dp.message(Command("strike"))
async def automated_strike_cmd(message: Message):
    if message.from_user.id != OWNER_ID: return
    if not message.reply_to_message: return
    target = message.reply_to_message.from_user
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET strikes = strikes + 1 WHERE user_id = ?", (target.id,))
    c.execute("SELECT strikes FROM users WHERE user_id = ?", (target.id,))
    strikes = c.fetchone()[0]
    
    if strikes >= 3:
        c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target.id,))
        await message.reply(f"⚖️ <b>MATRIX MAXIMUM OVERFLOW.</b> {target.first_name} reached 3/3 strikes and has been ban-hammered.")
    else:
        await message.reply(f"⚠️ <b>STRIKE ALLOCATED.</b> {target.first_name} now possesses [{strikes}/3] warnings.")
    conn.commit(); conn.close()

@dp.message(Command("purge"))
async def mass_clean_purge(message: Message):
    if message.from_user.id != OWNER_ID: return
    try:
        limit = int(message.text.split()[1])
        for i in range(limit + 1):
            try: await bot.delete_message(message.chat.id, message.message_id - i)
            except: pass
    except: await message.reply("Syntax: `/purge [integer]`")

@dp.message(Command("commune"))
async def global_commune_decree(message: Message):
    if message.from_user.id != OWNER_ID: return
    decree = message.text.replace("/commune ", "")
    if not decree or decree == "/commune": return
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE is_banned = 0")
    nodes = c.fetchall()
    conn.close()
    
    successful = 0
    await message.answer("📡 Spreading matrix broadcast pulses...")
    for (node_id,) in nodes:
        try:
            await bot.send_message(node_id, f"👑 <b>OVERSEER DIVINE DECREE:</b>\n\n{decree}", parse_mode=ParseMode.HTML)
            successful += 1
            await asyncio.sleep(0.04)
        except: pass
    await message.answer(f"✅ Pulse stream delivery complete to {successful} channels.")

@dp.message(Command("meditate"))
async def meditate_transmission(message: Message):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT file_url, file_type FROM uploads ORDER BY RANDOM() LIMIT 1")
    row = c.fetchone()
    conn.close()
    
    if row: await message.answer(f"🔮 <b>HISTORICAL TRANSMISSION DATASTREAM DETECTED:</b>\nClass: {row[1]}\n🔗 {row[0]}", parse_mode=ParseMode.HTML)
    else: await message.answer("🌀 The archive streams are dry. Populate data strings using <code>/link</code> first.", parse_mode=ParseMode.HTML)

@dp.message(Command("scavenge"))
async def top_scavenge_nodes(message: Message):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT first_name, sacrifices FROM users ORDER BY sacrifices DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    
    manifest = "🌀 <b>HIGHEST DEVOTION LEADERBOARD NODES</b>\n"
    for idx, row in enumerate(rows, 1):
        manifest += f"\n{idx}. {row[0]} — ฿{row[1]*15000:,} Devotion Bounty"
    await message.answer(manifest, parse_mode=ParseMode.HTML)

@dp.message(Command("scan"))
async def scan_data_nodes(message: Message):
    if message.from_user.id != OWNER_ID: return
    try:
        query = message.text.split(" ", 1)[1]
        conn = sqlite3.connect("data/bot.db")
        c = conn.cursor()
        c.execute("SELECT user_id, first_name, strikes, is_banned FROM users WHERE user_id LIKE ? OR first_name LIKE ?", (f"%{query}%", f"%{query}%"))
        items = c.fetchall()
        conn.close()
        
        if not items: return await message.reply("Zero vectors match query parameters.")
        out = "🔍 <b>NODE ANALYSIS READOUT:</b>\n"
        for row in items[:10]:
            out += f"\nID: <code>{row[0]}</code> | Name: {row[1]} | Banned Status: {bool(row[3])}"
        await message.answer(out, parse_mode=ParseMode.HTML)
    except: await message.reply("Syntax: `/scan [Identity/ID]`")

@dp.message(Command("curse"))
async def allocate_matrix_curse(message: Message):
    if message.from_user.id != OWNER_ID: return
    if not message.reply_to_message: return
    target = message.reply_to_message.from_user
    
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET curse_type = 'Static Glitch' WHERE user_id = ?", (target.id,))
    conn.commit(); conn.close()
    await message.reply(f"🛑 <b>CORRUPTION MATRIX DELIVERED.</b> {target.first_name}'s card profile has been heavily static glitched.")

# ========== SECRET WORD ARCHIVE TRANSMISSION ==========
@dp.message(Command("word"))
async def secret_word_command(message: Message):
    word_conversion_waiting[message.from_user.id] = True
    save_bot_state()
    await message.answer(
        "🔮 <b>SECRET SCROLL INTERFACE ENGAGED.</b>\n\n"
        "Send the raw text manifest you wish to convert into an elegant handwriting document script.",
        parse_mode=ParseMode.HTML
    )

# ========== SYSTEM DIAGNOSTICS ==========
@dp.message(Command("ping"))
async def ping_latency_metrics(message: Message):
    t_start = time.time()
    msg = await message.answer("📡 Querying core processor...")
    ms_lat = round((time.time() - t_start) * 1000, 2)
    
    up_seconds = int(time.time() - START_TIME)
    h, rem = divmod(up_seconds, 3600)
    m, s = divmod(rem, 60)
    
    try: storage_mb = round(os.path.getsize("data/bot.db") / 1024 / 1024, 3)
    except: storage_mb = 0.0
    
    readout = (
        f"🏓 <b>TEMPEST KERNEL READOUT:</b>\n\n"
        f"⚡ <b>Latency:</b> {ms_lat}ms\n"
        f"⏱️ <b>System Uptime:</b> {h}h {m}m {s}s\n"
        f"💾 <b>SQL Database Volume:</b> {storage_mb} MB\n"
        f"🛡️ <b>Keep-Alive Gateway:</b> ACTIVE [Port {PORT}]"
    )
    await msg.edit_text(readout, parse_mode=ParseMode.HTML)

@dp.message(Command("debug"))
async def system_debug_manifest(message: Message):
    if message.from_user.id != OWNER_ID: return
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users"); total_n = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM uploads"); total_u = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1"); total_b = c.fetchone()[0]
    conn.close()
    
    manifest = (
        "⚙️ <b>INTERNAL CODENAME CORE DEBUG MANIFEST</b>\n\n"
        f"Registered System Nodes: {total_n}\n"
        f"Stored Cloud Links: {total_u}\n"
        f"Quarantined/Banned Nodes: {total_b}\n"
        f"Current Python Build Environment: {sys.version.split(' ')[0]}"
    )
    await message.answer(manifest, parse_mode=ParseMode.HTML)

# ========== UNIVERSAL TEXT INTERCEPTOR (FOR STATE ENGINES) ==========
@dp.message(F.text)
async def handle_text_fallbacks(message: Message):
    user_id = message.from_user.id
    
    # Process secret /word script parsing
    if word_conversion_waiting.get(user_id):
        word_conversion_waiting[user_id] = False
        save_bot_state()
        
        msg = await message.answer("✒️ <b>Fabricating digital parchment and mapping handwriting vectors...</b>", parse_mode=ParseMode.HTML)
        try:
            raw_text = message.text
            img_w, img_h = 800, 1000
            parchment = Image.new('RGB', (img_w, img_h), color='#fbf6ec')
            draw = ImageDraw.Draw(parchment)
            
            draw.rectangle([20, 20, img_w - 20, img_h - 20], outline='#5c4033', width=3)
            draw.rectangle([28, 28, img_w - 28, img_h - 28], outline='#d4af37', width=1)
            
            try:
                hand_font = ImageFont.truetype("data/font.ttf", 28)
                header_font = ImageFont.truetype("data/font.ttf", 36)
            except:
                hand_font = header_font = ImageFont.load_default()
                
            draw.text((img_w // 2, 70), "~ Tempest Creed Archives ~", fill='#8c00ff', font=header_font, anchor="mm")
            draw.line([(150, 100), (img_w - 150, 100)], fill='#5c4033', width=1)
            
            margin_x, start_y, max_width = 60, 150, img_w - 120
            lines, words = [], raw_text.split()
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if draw.textbbox((0, 0), test_line, font=hand_font)[2] <= max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line: lines.append(current_line)
                
            current_y = start_y
            for line in lines[:25]:
                draw.text((margin_x, current_y), line, fill='#1c110b', font=hand_font)
                current_y += 35
                
            image_path = f"temp/rendered_page_{user_id}.png"
            parchment.save(image_path, "PNG")
            
            await msg.edit_text("📄 <b>Binding the visual scripts into the Word document skeleton...</b>", parse_mode=ParseMode.HTML)
            
            doc = Document()
            for section in doc.sections:
                section.top_margin = Inches(0.5)
                section.bottom_margin = Inches(0.5)
                section.left_margin = Inches(0.5)
                section.right_margin = Inches(0.5)
                
            doc.add_heading(f"Transmission Protocol [{user_id}]", level=1)
            doc.add_paragraph("This data stream was securely handled and transcribed by the Tempest Core Engine.")
            doc.add_picture(image_path, width=Inches(6.5))
            
            doc_output_path = f"temp/Scroll_{user_id}.docx"
            doc.save(doc_output_path)
            
            await msg.delete()
            await message.reply_document(
                FSInputFile(doc_output_path),
                caption="🔮 <b>SECRET SCROLL ARCHIVE COMPILED</b>\n\nYour text vector has been converted successfully into a customized script frame.",
                parse_mode=ParseMode.HTML
            )
            
            if os.path.exists(image_path): os.remove(image_path)
            if os.path.exists(doc_output_path): os.remove(doc_output_path)
        except Exception as err:
            await msg.edit_text(f"❌ Secret Archive Pipeline Failure: {str(err)}")
        return

# ========== KEEP-ALIVE INTERFACE GATEWAY ROUTE ==========
async def web_alive_ping_route(request):
    return web.Response(text="Tempest Creed Supreme Engine Operating Matrix Securely 24/7.")

# ========== COMPREHENSIVE INITIALIZATION TRUNK ==========
async def main():
    print("🚀 INITIALIZING COMPLETE UNCOMPROMISED TEMPEST ENGINE CORE...")
    
    # Fire up background keep-alive loop architecture instantly
    app = web.Application()
    app.router.add_get('/', web_alive_ping_route)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ Persistent Keep-Alive Server processing incoming streams on Port: {PORT}")
    
    # Launch absolute continuous polling pipelines
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Pipeline core manual drop sequence reached.")
