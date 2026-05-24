#!/usr/bin/env python3
# ========== TEMPEST ENGINE: THE TITAN FORGE (45 CMD MATRIX) ==========
import os
import asyncio
import time
import random
import sqlite3
import httpx
from datetime import datetime
from pathlib import Path

# Media & Docs
from PIL import Image, ImageDraw, ImageFont
from docx import Document

# Telegram API
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode, ChatType

print("🚀 IGNITING TEMPEST ENGINE - TITAN STATE...")

# ========== CONFIGURATION ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
OWNER_ID = int(os.getenv("OWNER_ID", "6108185460"))
UPLOAD_API = "https://catbox.moe/user/api.php"
LOG_CHANNEL_ID = -1003662720845

# Ephemeral States
upload_waiting = {}
disabled_cmds = {}
active_battles = {}
start_time = time.time()
bot_active = True

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Directory Setup (Mobile-Optimized)
for folder in ["data", "temp", "backups", "profile_cards"]:
    Path(folder).mkdir(exist_ok=True)

# ========== DATABASE ENGINE ==========
def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect("data/bot.db")
    c = conn.cursor()
    c.execute(query, params)
    res = None
    if fetchone: res = c.fetchone()
    if fetchall: res = c.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, first_name TEXT, is_admin INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0, 
        warns INTEGER DEFAULT 0, commands INTEGER DEFAULT 0, uploads INTEGER DEFAULT 0, cult_rank TEXT DEFAULT 'none', 
        sacrifices INTEGER DEFAULT 0, curse TEXT DEFAULT 'none', hp INTEGER DEFAULT 100, atk INTEGER DEFAULT 10, 
        def INTEGER DEFAULT 5, spd INTEGER DEFAULT 5, status_effect TEXT DEFAULT 'none'
    )''', commit=True)
    db_query('''CREATE TABLE IF NOT EXISTS groups (group_id INTEGER PRIMARY KEY, title TEXT, commands INTEGER DEFAULT 0)''', commit=True)
    db_query('''CREATE TABLE IF NOT EXISTS uploads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, file_url TEXT)''', commit=True)
    db_query("INSERT OR IGNORE INTO users (user_id, first_name, is_admin) VALUES (?, ?, ?)", (OWNER_ID, "TEMPESTCREED", 1), commit=True)

init_db()

# ========== CORE MIDDLEWARE ==========
async def is_admin(user_id):
    if user_id == OWNER_ID: return True
    res = db_query("SELECT is_admin FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    return res and res[0] == 1

async def handle_sys(message: Message, cmd: str):
    if not bot_active and cmd != "toggle": return None
    if cmd in disabled_cmds and time.time() < disabled_cmds[cmd]:
        await message.answer("🔴 <b>COMMAND LOCKED</b>", parse_mode=ParseMode.HTML)
        return None
    
    user, chat = message.from_user, message.chat
    banned = db_query("SELECT is_banned FROM users WHERE user_id = ?", (user.id,), fetchone=True)
    if banned and banned[0] == 1: return None

    db_query("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user.id, user.first_name), commit=True)
    db_query("UPDATE users SET commands = commands + 1, first_name = ? WHERE user_id = ?", (user.first_name, user.id), commit=True)
    
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        db_query("INSERT OR IGNORE INTO groups (group_id, title) VALUES (?, ?)", (chat.id, chat.title), commit=True)
        db_query("UPDATE groups SET commands = commands + 1 WHERE group_id = ?", (chat.id,), commit=True)
    
    return user

async def log_action(text: str):
    try: await bot.send_message(LOG_CHANNEL_ID, f"📝 <b>ENGINE LOG</b>\n{text}", parse_mode=ParseMode.HTML)
    except: pass

# ========== 1. SYSTEM COMMANDS ==========
@dp.message(CommandStart())
async def cmd_start(message: Message):
    if await handle_sys(message, "start"): await message.answer("⚡ <b>TITAN ENGINE ONLINE.</b> /help to sync.")

def get_help_kb(page: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏪ Prev", callback_data=f"help_{page-1}"),
        InlineKeyboardButton(text="Next ⏩", callback_data=f"help_{page+1}")
    ]])
    return kb

@dp.message(Command("help"))
async def cmd_help(message: Message):
    if await handle_sys(message, "help"):
        await message.answer("📚 <b>COMMAND MATRIX [PAGE 1: Core]</b>\n\n/start, /ping, /stats, /scan, /status, /g_sync\n/debug, /refresh, /toggle, /disable", reply_markup=get_help_kb(1), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("help_"))
async def cb_help(call: CallbackQuery):
    page = int(call.data.split("_")[1])
    if page < 1: page = 4
    if page > 4: page = 1
    pages = {
        1: "📚 <b>[PAGE 1: Core]</b>\n/start, /ping, /stats, /scan, /status, /g_sync\n/debug, /refresh, /toggle, /disable",
        2: "🛠️ <b>[PAGE 2: Forge]</b>\n/link, /word, /profile, /publish, /cancel\n/backup, /relic, /echo, /forge_item",
        3: "🌀 <b>[PAGE 3: RPG & Lore]</b>\n/tempest_join, /progress, /creed, /story, /meditate\n/scavenge, /curse, /remove_curse, /reborn, /bounty\n/battle, /arena, /skill, /summon, /tribute, /feed",
        4: "⚖️ <b>[PAGE 4: Discipline]</b>\n/strike, /warn, /unwarn, /mute, /unmute, /ban, /unban\n/commune, /pro, /purge, /shrine, /logs"
    }
    await call.message.edit_text(pages[page], reply_markup=get_help_kb(page), parse_mode=ParseMode.HTML)

@dp.message(Command("ping"))
async def cmd_ping(message: Message):
    t = time.time(); msg = await message.answer("🏓...")
    await msg.edit_text(f"⚡ <b>PONG:</b> {int((time.time()-t)*1000)}ms\n⏱️ <b>Uptime:</b> {int(time.time()-start_time)}s", parse_mode=ParseMode.HTML)

@dp.message(Command("status", "stats", "scan", "g_sync"))
async def cmd_sys_info(message: Message):
    if await handle_sys(message, "stats"):
        u = db_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
        await message.answer(f"📊 <b>ENGINE STATUS</b>\n👥 Nodes: {u}\n🔥 DB: Stable", parse_mode=ParseMode.HTML)

@dp.message(Command("disable"))
async def cmd_disable(message: Message):
    if not await is_admin(message.from_user.id): return
    args = message.text.split()
    if len(args) == 3:
        disabled_cmds[args[1]] = time.time() + int(args[2])
        await message.answer(f"🔒 /{args[1]} locked for {args[2]}s.")

@dp.message(Command("refresh"))
async def cmd_refresh(message: Message):
    if not await is_admin(message.from_user.id): return
    db_query("DELETE FROM logs", commit=True)
    await message.answer("✅ Engine memory flushed. Logs wiped.")
    await log_action("Manual /refresh initiated.")

# ========== 2. FORGE & UTILITY ==========
@dp.message(Command("word"))
async def cmd_word(message: Message):
    user = await handle_sys(message, "word")
    if not user: return
    text = message.text.split(maxsplit=1)
    if len(text) < 2: return await message.answer("📝 Usage: /word [text]")
    msg = await message.answer("⏳ Forging...")
    doc = Document(); doc.add_paragraph("="*30); doc.add_paragraph(text[1])
    path = f"temp/doc_{user.id}.docx"; doc.save(path)
    await message.reply_document(FSInputFile(path), caption="📝 <b>Forged</b>", parse_mode=ParseMode.HTML)
    await msg.delete(); os.remove(path)

@dp.message(Command("link"))
async def cmd_link(message: Message):
    if await handle_sys(message, "link"):
        upload_waiting[message.from_user.id] = True
        await message.answer("📁 Send Media/Doc to link to Catbox. /cancel to abort.")

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    upload_waiting[message.from_user.id] = False
    await message.answer("❌ Aborted.")

@dp.message(F.photo | F.video | F.document)
async def process_media(message: Message):
    user = message.from_user
    if not upload_waiting.get(user.id): return
    upload_waiting[user.id] = False
    msg = await message.answer("⏳ Syncing...")
    try:
        file_id = message.photo[-1].file_id if message.photo else (message.video.file_id if message.video else message.document.file_id)
        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        async with httpx.AsyncClient() as c:
            r = await c.post(UPLOAD_API, files={'reqtype': (None, 'fileupload'), 'fileToUpload': ('f.jpg', (await c.get(url)).content)})
        if r.status_code == 200:
            db_query("UPDATE users SET uploads = uploads + 1 WHERE user_id = ?", (user.id,), commit=True)
            db_query("INSERT INTO uploads (user_id, file_url) VALUES (?, ?)", (user.id, r.text), commit=True)
            await msg.edit_text(f"✅ <b>Linked:</b> <code>{r.text}</code>", parse_mode=ParseMode.HTML)
    except: await msg.edit_text("❌ Upload Failed.")

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    user = await handle_sys(message, "profile")
    if not user: return
    data = db_query("SELECT cult_rank, sacrifices, atk, def, spd, curse FROM users WHERE user_id = ?", (user.id,), fetchone=True)
    img = Image.new('RGB', (600, 300), color='#111')
    d = ImageDraw.Draw(img); f = ImageFont.load_default()
    d.text((50, 50), f"USER: {user.first_name}", fill='white', font=f)
    d.text((50, 100), f"RANK: {data[0]} | SACRIFICES: {data[1]}", fill='red', font=f)
    d.text((50, 150), f"ATK: {data[2]} | DEF: {data[3]} | SPD: {data[4]}", fill='gold', font=f)
    if data[5] != 'none': d.text((50, 200), f"CURSE: {data[5]}", fill='purple', font=f)
    path = f"temp/p_{user.id}.png"; img.save(path)
    await message.answer_photo(FSInputFile(path), caption="👤 <b>Profile Node</b>", parse_mode=ParseMode.HTML)
    os.remove(path)

@dp.message(Command("backup"))
async def cmd_backup(message: Message):
    if await is_admin(message.from_user.id):
        await message.reply_document(FSInputFile("data/bot.db"), caption="💾 DB Backup")

# ========== 3. DOCTRINE & RPG ==========
@dp.message(Command("tempest_join"))
async def cmd_join(message: Message):
    if await handle_sys(message, "join"):
        db_query("UPDATE users SET cult_rank = 'Initiate', sacrifices = 5 WHERE user_id = ?", (message.from_user.id,), commit=True)
        await message.answer("⚡ <b>BLOOD PACT SEALED.</b>")

@dp.message(Command("bounty", "scavenge"))
async def cmd_bounty(message: Message):
    if await handle_sys(message, "bounty"):
        target = db_query("SELECT first_name, sacrifices FROM users ORDER BY RANDOM() LIMIT 1", fetchone=True)
        await message.answer(f"🎯 <b>BOUNTY DETECTED</b>\nTarget: {target[0]}\nWorth: {target[1]} Sacrifices", parse_mode=ParseMode.HTML)

@dp.message(Command("summon"))
async def cmd_summon(message: Message):
    if await handle_sys(message, "summon"):
        db_query("UPDATE users SET atk = atk + 15, status_effect = 'fire_aura' WHERE user_id = ?", (message.from_user.id,), commit=True)
        await message.answer("🔥 <b>Chestnut Rose Summoned!</b>\nElement: <i>Fire</i>. ATK boosted +15.", parse_mode=ParseMode.HTML)

@dp.message(Command("battle"))
async def cmd_battle(message: Message):
    if not message.reply_to_message: return await message.answer("⚔️ Reply to a target to /battle.")
    user, target = message.from_user, message.reply_to_message.from_user
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Strike", callback_data=f"atk_{target.id}"), InlineKeyboardButton(text="🛡️ Block", callback_data="def")]
    ])
    await message.answer(f"⚔️ <b>{user.first_name}</b> challenges <b>{target.first_name}</b>!", reply_markup=kb, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("atk_"))
async def cb_atk(call: CallbackQuery):
    target_id = call.data.split("_")[1]
    await call.message.edit_text(f"💥 <b>CRITICAL HIT!</b> The target sustains heavy damage.", parse_mode=ParseMode.HTML)

@dp.message(Command("tribute", "feed", "forge_item", "meditate", "reborn", "skill", "arena", "logs", "wish", "dice", "flip", "tempest_progress", "tempest_creed", "tempest_story"))
async def cmd_rpg_hooks(message: Message):
    await handle_sys(message, "rpg")
    await message.answer("🌀 <i>RPG Action Registered in the Tempest.</i>", parse_mode=ParseMode.HTML)

# ========== 4. DISCIPLINE & MODERATION ==========
@dp.message(Command("strike", "warn"))
async def cmd_strike(message: Message):
    if await is_admin(message.from_user.id) and message.reply_to_message:
        tgt = message.reply_to_message.from_user
        db_query("UPDATE users SET warns = warns + 1 WHERE user_id = ?", (tgt.id,), commit=True)
        await message.answer(f"⚡ <b>STRIKE ISSUED</b> against {tgt.first_name}.")
        await log_action(f"Strike: {tgt.id}")

@dp.message(Command("mute", "ban"))
async def cmd_restrict(message: Message):
    if await is_admin(message.from_user.id) and message.reply_to_message:
        tgt = message.reply_to_message.from_user
        try:
            if "mute" in message.text: await bot.restrict_chat_member(message.chat.id, tgt.id, permissions=ChatPermissions(can_send_messages=False))
            else: 
                await bot.ban_chat_member(message.chat.id, tgt.id)
                db_query("UPDATE users SET is_banned = 1 WHERE user_id = ?", (tgt.id,), commit=True)
            await message.answer(f"⚖️ <b>{tgt.first_name}</b> has been disciplined.", parse_mode=ParseMode.HTML)
        except: await message.answer("❌ Insufficient permissions.")

@dp.message(Command("unmute", "unban", "unwarn"))
async def cmd_forgive(message: Message):
    if await is_admin(message.from_user.id) and message.reply_to_message:
        tgt = message.reply_to_message.from_user
        db_query("UPDATE users SET warns = 0, is_banned = 0 WHERE user_id = ?", (tgt.id,), commit=True)
        try: await bot.restrict_chat_member(message.chat.id, tgt.id, permissions=ChatPermissions(can_send_messages=True))
        except: pass
        await message.answer(f"🕊️ <b>{tgt.first_name}</b> has been absolved.")

@dp.message(Command("curse", "remove_curse"))
async def cmd_curse(message: Message):
    if await is_admin(message.from_user.id) and message.reply_to_message:
        tgt = message.reply_to_message.from_user
        val = "Shadows Grip" if "remove" not in message.text else "none"
        db_query("UPDATE users SET curse = ? WHERE user_id = ?", (val, tgt.id), commit=True)
        await message.answer(f"🌀 Curse state altered for {tgt.first_name}.")

@dp.message(Command("shrine"))
async def cmd_shrine(message: Message):
    if await handle_sys(message, "shrine"):
        await message.answer(f"🏰 <b>SHRINE OF {message.chat.title}</b>\n🛡️ Integrity: [██████░░] 75%\n📜 <i>The storm is calm.</i>", parse_mode=ParseMode.HTML)

@dp.message(Command("commune", "echo", "publish"))
async def cmd_broadcast(message: Message):
    if await is_admin(message.from_user.id):
        text = message.text.split(maxsplit=1)
        if len(text) > 1: await message.answer(f"📢 <b>COMMUNE:</b>\n{text[1]}", parse_mode=ParseMode.HTML)

@dp.message(Command("purge"))
async def cmd_purge(message: Message):
    if await is_admin(message.from_user.id): await message.answer("🌪️ <b>PURGE INITIATED.</b> (API limitations prevent mass delete without specific IDs).")

@dp.message(Command("pro"))
async def cmd_pro(message: Message):
    if message.from_user.id == OWNER_ID and message.reply_to_message:
        db_query("UPDATE users SET is_admin = 1 WHERE user_id = ?", (message.reply_to_message.from_user.id,), commit=True)
        await message.answer("👑 Admin privileges granted.")

# ========== MAIN EXECUTION ==========
async def main():
    print("🤖 SYSTEM FULLY OPERATIONAL.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
