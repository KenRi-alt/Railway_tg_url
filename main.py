#!/usr/bin/env python3
# TEMPEST GUIDER - COMPLETE
import os,asyncio,time,random,sqlite3,json,httpx,shutil,traceback,psutil,math,io,base64,sys,contextlib,urllib.request
from datetime import datetime,timedelta
from pathlib import Path
from docx import Document
from PIL import Image,ImageDraw,ImageFont,ImageOps
from aiogram import Bot,Dispatcher,types,F
from aiogram.filters import Command,CommandStart
from aiogram.types import Message,FSInputFile,CallbackQuery,BufferedInputFile
from aiogram.enums import ParseMode,ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder
BOT_TOKEN=os.getenv("BOT_TOKEN","8017048722:AAGs1HNsyX-UobN6PVq7u4iPMxGnOX14AAg")
OWNER_ID=int(os.getenv("OWNER_ID","6108185460"))
LOG_CHANNEL_ID=int(os.getenv("LOG_CHANNEL_ID","-1003662720845"))
GROQ_API_KEY=os.getenv("GROQ_API_KEY","")
try:
 import yt_dlp;YTDLP_AVAILABLE=True
except:YTDLP_AVAILABLE=False
try:
 from zoneinfo import ZoneInfo
except:ZoneInfo=None
for d in["data","temp","backups","fonts"]:Path(d).mkdir(exist_ok=True)
bot=Bot(token=BOT_TOKEN);dp=Dispatcher()
start_time=time.time();upload_waiting={};broadcast_state={};pending_restore={};disabled_commands={};maintenance_mode=False;conversation_memory={};ai_enabled=True
def header(t):return f"◤━━━━━━━━━━━━━━━━━━━━◥\n◇ {t} ◇\n◣━━━━━━━━━━━━━━━━━━━━◢"
def divider():return "━━━━━━━━━━━━━━━━━━━━"
def get_safe_font(size):
 for p in["fonts/font.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
  if os.path.exists(p):
   try:return ImageFont.truetype(p,size)
   except:pass
 return ImageFont.load_default()
def draw_visible_text(draw,pos,text,font,fill,outline=(0,0,0),w=2,anchor=None):
 x,y=pos
 for ox in range(-w,w+1):
  for oy in range(-w,w+1):
   if ox!=0 or oy!=0:
    if anchor:draw.text((x+ox,y+oy),text,font=font,fill=outline,anchor=anchor)
    else:draw.text((x+ox,y+oy),text,font=font,fill=outline)
 if anchor:draw.text((x,y),text,font=font,fill=fill,anchor=anchor)
 else:draw.text((x,y),text,font=font,fill=fill)
ANIME_QUOTES=["Wake up to reality! Nothing ever goes as planned in this accursed world.\n- Madara Uchiha","The longer you live, the more you realize that reality is just made of pain.\n- Madara Uchiha","People cannot show each other their true feelings.\n- Madara Uchiha","The only thing we're allowed to do is believe we won't regret our choice.\n- Levi Ackerman","If you don't take risks, you can't create a future.\n- Monkey D. Luffy","Power isn't determined by your size, but by the size of your heart.\n- Luffy","Fear is not evil. It tells you what your weakness is.\n- Gildarts Clive","A lesson without pain is meaningless.\n- Edward Elric"]
COUNTRY_TIMEZONES={"usa":"America/New_York","uk":"Europe/London","india":"Asia/Kolkata","japan":"Asia/Tokyo","china":"Asia/Shanghai","russia":"Europe/Moscow","brazil":"America/Sao_Paulo","australia":"Australia/Sydney","canada":"America/Toronto","germany":"Europe/Berlin","france":"Europe/Paris","italy":"Europe/Rome","spain":"Europe/Madrid","south korea":"Asia/Seoul","pakistan":"Asia/Karachi","bangladesh":"Asia/Dhaka","nigeria":"Africa/Lagos","egypt":"Africa/Cairo","south africa":"Africa/Johannesburg","kenya":"Africa/Nairobi","uganda":"Africa/Kampala","uae":"Asia/Dubai","saudi arabia":"Asia/Riyadh","turkey":"Europe/Istanbul","thailand":"Asia/Bangkok","philippines":"Asia/Manila","singapore":"Asia/Singapore"}
def init_db():
 with sqlite3.connect("data/bot.db")as conn:
  c=conn.cursor()
  c.execute('''CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,username TEXT,first_name TEXT,joined_date TEXT,last_active TEXT,uploads INTEGER DEFAULT 0,commands INTEGER DEFAULT 0,is_admin INTEGER DEFAULT 0,is_banned INTEGER DEFAULT 0,cult_status TEXT DEFAULT 'none',cult_rank TEXT DEFAULT 'none',cult_join_date TEXT,sacrifices INTEGER DEFAULT 0,curse_type TEXT DEFAULT 'none')''')
  for col,defn in[("cult_status","TEXT DEFAULT 'none'"),("cult_rank","TEXT DEFAULT 'none'"),("cult_join_date","TEXT"),("sacrifices","INTEGER DEFAULT 0"),("curse_type","TEXT DEFAULT 'none'")]:
   try:c.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
   except:pass
  c.execute('''CREATE TABLE IF NOT EXISTS groups(group_id INTEGER PRIMARY KEY,title TEXT,joined_date TEXT)''')
  c.execute('''CREATE TABLE IF NOT EXISTS uploads(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,timestamp TEXT,file_url TEXT,file_type TEXT)''')
  c.execute('''CREATE TABLE IF NOT EXISTS command_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT,user_id INTEGER,chat_id INTEGER,command TEXT,success INTEGER)''')
  c.execute('''CREATE TABLE IF NOT EXISTS wishes(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,timestamp TEXT,wish_text TEXT,luck INTEGER)''')
  c.execute('''CREATE TABLE IF NOT EXISTS fate_pairs(id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id INTEGER,user1_id INTEGER,user1_name TEXT,user2_id INTEGER,user2_name TEXT,love_percentage INTEGER,created_date TEXT)''')
  c.execute('''CREATE TABLE IF NOT EXISTS fortunes(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,timestamp TEXT,fortune_text TEXT)''')
  c.execute('''CREATE TABLE IF NOT EXISTS shrines(user_id INTEGER PRIMARY KEY,power_level INTEGER DEFAULT 10,title TEXT DEFAULT 'Novice')''')
  c.execute('''CREATE TABLE IF NOT EXISTS conversation_history(user_id INTEGER,role TEXT,content TEXT,timestamp TEXT)''')
  c.execute("INSERT OR IGNORE INTO users(user_id,first_name,is_admin)VALUES(?,'Owner',1)",(OWNER_ID,))
  conn.commit()
init_db()
async def send_log(m):
 try:await bot.send_message(LOG_CHANNEL_ID,m[:4000])
 except:pass
async def handle_common(message,cmd):
 user,chat=message.from_user,message.chat
 if chat.type in[ChatType.GROUP,ChatType.SUPERGROUP]:
  try:
   with sqlite3.connect("data/bot.db")as conn:conn.execute("INSERT OR IGNORE INTO groups(group_id,title,joined_date)VALUES(?,?,?)",(chat.id,str(chat.title),datetime.now().isoformat()));conn.commit()
  except:pass
 if maintenance_mode and user.id!=OWNER_ID:await message.answer("Maintenance mode!");return None,None
 if cmd in disabled_commands and disabled_commands[cmd]>datetime.now():await message.answer("Command disabled!");return None,None
 try:
  with sqlite3.connect("data/bot.db")as conn:
   c=conn.cursor()
   c.execute("INSERT OR IGNORE INTO users(user_id,username,first_name,joined_date)VALUES(?,?,?,?)",(user.id,user.username or"",user.first_name or"",datetime.now().isoformat()))
   c.execute("UPDATE users SET last_active=?,username=?,first_name=?WHERE user_id=?",(datetime.now().isoformat(),user.username or"",user.first_name or"",user.id))
   c.execute("INSERT INTO command_logs(timestamp,user_id,chat_id,command,success)VALUES(?,?,?,?,1)",(datetime.now().isoformat(),user.id,chat.id,cmd))
   c.execute("UPDATE users SET commands=commands+1 WHERE user_id=?",(user.id,))
   conn.commit()
 except:pass
 return user,chat
async def is_admin(uid):
 if uid==OWNER_ID:return True
 try:
  with sqlite3.connect("data/bot.db")as conn:
   r=conn.execute("SELECT is_admin FROM users WHERE user_id=?",(uid,)).fetchone()
  return r and r[0]==1
 except:return False
def format_uptime(s):
 d=s//86400;h=(s%86400)//3600;m=(s%3600)//60;sec=s%60
 p=[]
 if d:p.append(f"{d}d")
 if h:p.append(f"{h}h")
 if m:p.append(f"{m}m")
 if sec or not p:p.append(f"{sec}s")
 return" ".join(p)
async def upload_to_catbox(data,filename):
 headers={'User-Agent':'Mozilla/5.0'}
 try:
  files={'reqtype':(None,'fileupload'),'fileToUpload':(filename,data)}
  async with httpx.AsyncClient(timeout=60,headers=headers)as client:
   r=await client.post("https://catbox.moe/user/api.php",files=files)
  if r.status_code==200 and r.text.startswith('http'):return r.text.strip()
 except:pass
 try:
  files={'file':(filename,data)}
  async with httpx.AsyncClient(timeout=60,headers=headers)as client:
   r=await client.post("https://0x0.st",files=files)
  if r.status_code==200 and r.text.startswith('http'):return r.text.strip()
 except:pass
 return None
class EncryptionEngine:
 @staticmethod
 def xor_encrypt(text,key="TEMPEST"):return''.join(chr(ord(c)^ord(key[i%len(key)]))for i,c in enumerate(text))
 @staticmethod
 def encrypt(t):return base64.b64encode(EncryptionEngine.xor_encrypt(t).encode()).decode()
 @staticmethod
 def decrypt(t):
  try:return EncryptionEngine.xor_encrypt(base64.b64decode(t.encode()).decode())
  except:return None
async def fetch_user_avatar(uid,name="User"):
 try:
  photos=await bot.get_user_profile_photos(uid,limit=1)
  if photos.total_count>0:
   fid=photos.photos[0][-1].file_id;fi=await bot.get_file(fid)
   async with httpx.AsyncClient(timeout=30)as c:r=await c.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fi.file_path}")
   if r.status_code==200:
    av=Image.open(io.BytesIO(r.content)).convert("RGBA");av=av.resize((120,120),Image.Resampling.LANCZOS)
    mask=Image.new("L",(120,120),0);d=ImageDraw.Draw(mask);d.ellipse((0,0,120,120),fill=255)
    out=Image.new("RGBA",(120,120),(0,0,0,0));out.paste(av,(0,0),mask=mask);return out
 except:pass
 fb=Image.new("RGBA",(120,120),(20,30,50,255));d=ImageDraw.Draw(fb);d.ellipse((0,0,120,120),outline=(0,255,200),width=3)
 f=get_safe_font(50);draw_visible_text(d,(60,60),name[0].upper()if name else"T",f,(0,255,200),anchor="mm");return fb
def gen_profile_card(username,uid,rank,up,ws,av):
 w,h=800,360;img=Image.new("RGB",(w,h),(10,15,30));d=ImageDraw.Draw(img)
 for y in range(h):
  r=int(10+25*(y/h));g=int(15+35*(y/h));b=int(30+55*(y/h));d.line([(0,y),(w,y)],fill=(r,g,b))
 d.rectangle([10,10,w-10,h-10],outline=(0,200,255),width=3)
 d.ellipse((47,77,173,203),outline=(0,255,200),width=3);img.paste(av,(50,80),mask=av)
 fn=get_safe_font(28);fi=get_safe_font(20)
 draw_visible_text(d,(200,75),str(username)[:20],fn,(255,255,255))
 draw_visible_text(d,(200,120),f"ID: {uid}",fi,(180,200,230))
 draw_visible_text(d,(200,160),f"Rank: {rank}",fi,(0,255,200))
 draw_visible_text(d,(200,205),f"Uploads: {up}  |  Wishes: {ws}",fi,(255,215,0))
 draw_visible_text(d,(770,330),"TEMPEST GUIDER",fi,(100,116,139),anchor="ra")
 b=io.BytesIO();img.save(b,format="PNG");b.seek(0);return b.getvalue()
def gen_fate_card(n1,n2,pct,q,av1=None,av2=None):
 w,h=800,450;img=Image.new("RGB",(w,h),(15,10,25));d=ImageDraw.Draw(img)
 for y in range(h):
  r=int(15+30*(y/h));g=int(10+20*(y/h));b=int(25+45*(y/h));d.line([(0,y),(w,y)],fill=(r,g,b))
 d.rectangle([10,10,w-10,h-10],outline=(255,100,180),width=3)
 ft=get_safe_font(28);fn=get_safe_font(20);fq=get_safe_font(14)
 if av1:img.paste(av1,(100,50),mask=av1)
 if av2:img.paste(av2,(580,50),mask=av2)
 draw_visible_text(d,(400,45),"TEMPEST FATE MATRIX",ft,(255,100,180),anchor="mm")
 draw_visible_text(d,(400,200),f"{n1}  +  {n2}",fn,(255,255,255),anchor="mm")
 draw_visible_text(d,(400,240),f"{pct}% COMPATIBILITY",fn,(255,215,0),anchor="mm")
 words=q.split();lines=[];cur=""
 for wrd in words:
  if len(cur+wrd)<50:cur+=wrd+" "
  else:lines.append(cur.strip());cur=wrd+" "
 if cur:lines.append(cur.strip())
 yp=290
 for ln in lines[:4]:draw_visible_text(d,(400,yp),ln,fq,(210,220,240),anchor="mm");yp+=30
 b=io.BytesIO();img.save(b,format="PNG");b.seek(0);return b.getvalue()
@dp.message(CommandStart())
async def start_cmd(m:Message):
 u,_=await handle_common(m,"start")
 if not u:return
 await m.answer(f"{header('TEMPEST GUIDER')}\nWelcome {u.first_name}!\n\n/help - Commands")
@dp.message(Command("myid"))
async def myid_cmd(m:Message):await m.answer(f"Your ID: <code>{m.from_user.id}</code>",parse_mode=ParseMode.HTML)
@dp.message(Command("help"))
async def help_cmd(m:Message):
 await handle_common(m,"help")
 await m.answer(f"{header('COMMANDS')}\n/link /convert /wish /fortune /dice /flip /fate /profile /encrypt /decrypt /tempest_join /tempest_story /tempest_creed /shrine /curse /remove_curse /time /word /neko /waifu /myid /admin_help")
@dp.message(Command("admin_help"))
async def admin_help_cmd(m:Message):
 u,_=await handle_common(m,"admin_help")
 if not u:return
 if u.id!=OWNER_ID and not await is_admin(u.id):await m.answer(f"Admin only. Your ID: {u.id}");return
 await m.answer(f"{header('ADMIN')}\n/ping /stats /scan /users /broadcast /lag /disable /cm /ban /unban /banlist\nOWNER: /query /restart /maintenance /pro /backup /rem /clearlogs /logs /management")
@dp.message(Command("wish"))
async def wish_cmd(m:Message):
 u,_=await handle_common(m,"wish")
 if not u:return
 args=m.text.split(maxsplit=1)
 if len(args)<2:await m.answer("Usage: /wish [text]");return
 msg=await m.answer("Consulting the storm...");await asyncio.sleep(1);await msg.edit_text("Reading your destiny...");await asyncio.sleep(1);await msg.edit_text("The tempest whispers...");await asyncio.sleep(1)
 luck=random.randint(1,100);stars="*"*(luck//10)+"."*(10-luck//10)
 with sqlite3.connect("data/bot.db")as conn:conn.execute("INSERT INTO wishes(user_id,timestamp,wish_text,luck)VALUES(?,?,?,?)",(u.id,datetime.now().isoformat(),args[1],luck));conn.commit()
 await msg.edit_text(f"{header('WISH')}\n{args[1][:100]}\nLuck: {stars} {luck}%")
@dp.message(Command("fortune"))
async def fortune_cmd(m:Message):
 u,_=await handle_common(m,"fortune")
 if not u:return
 fortunes=["Great things await you!","New doors open!","Adventure calls!","Success is near!","Love finds you!","Lucky week ahead!","A wish comes true!","Strength grows daily!","Hidden talent emerges!","The storm favors you!"]
 msg=await m.answer("Reading the crystal orb...");await asyncio.sleep(1.5);await msg.edit_text("The spirits are speaking...");await asyncio.sleep(1.5)
 f=random.choice(fortunes)
 with sqlite3.connect("data/bot.db")as conn:conn.execute("INSERT INTO fortunes(user_id,timestamp,fortune_text)VALUES(?,?,?)",(u.id,datetime.now().isoformat(),f));conn.commit()
 await msg.edit_text(f"{header('FORTUNE')}\n{f}")
@dp.message(Command("dice"))
async def dice_cmd(m:Message):await handle_common(m,"dice");await m.answer_dice(emoji="🎲")
@dp.message(Command("flip"))
async def flip_cmd(m:Message):await handle_common(m,"flip");await m.answer(f"{random.choice(['HEADS','TAILS'])}!")
@dp.message(Command("fate"))
async def fate_cmd(m:Message):
 u,ch=await handle_common(m,"fate")
 if not u:return
 if ch.type not in[ChatType.GROUP,ChatType.SUPERGROUP]:await m.answer("Groups only!");return
 msg=await m.answer("Weaving destiny...");await asyncio.sleep(1.5);await msg.edit_text("Scanning souls...");await asyncio.sleep(1.5);await msg.edit_text("Calculating compatibility...");await asyncio.sleep(1.5)
 with sqlite3.connect("data/bot.db")as conn:
  c=conn.cursor();c.execute("SELECT user1_name,user2_name,love_percentage FROM fate_pairs WHERE chat_id=?AND created_date>=?",(ch.id,(datetime.now()-timedelta(hours=24)).isoformat()));ex=c.fetchone()
  if ex:await msg.edit_text(f"Today: {ex[0]} & {ex[1]} ({ex[2]}%)");return
  c.execute("SELECT user_id,first_name FROM users WHERE user_id!=?LIMIT 50",(u.id,));members=c.fetchall()
 if len(members)<2:await msg.edit_text("Not enough members!");return
 l1,l2=random.sample(members,2);love=random.randint(50,100);quote=random.choice(ANIME_QUOTES)
 av1=await fetch_user_avatar(l1[0],l1[1]);av2=await fetch_user_avatar(l2[0],l2[1])
 with sqlite3.connect("data/bot.db")as conn:conn.execute("INSERT INTO fate_pairs(chat_id,user1_id,user1_name,user2_id,user2_name,love_percentage,created_date)VALUES(?,?,?,?,?,?,?)",(ch.id,l1[0],l1[1],l2[0],l2[1],love,datetime.now().isoformat()));conn.commit()
 card=await asyncio.to_thread(gen_fate_card,l1[1],l2[1],love,quote,av1,av2)
 await msg.delete();await m.answer_photo(photo=BufferedInputFile(card,filename="fate.png"),caption=f"{l1[1]} & {l2[1]} - {love}% Love")
@dp.message(Command("profile"))
async def profile_cmd(m:Message):
 u,_=await handle_common(m,"profile")
 if not u:return
 msg=await m.answer("Generating profile card...")
 with sqlite3.connect("data/bot.db")as conn:
  c=conn.cursor();c.execute("SELECT uploads,cult_rank FROM users WHERE user_id=?",(u.id,));r=c.fetchone();c.execute("SELECT COUNT(*)FROM wishes WHERE user_id=?",(u.id,));ws=c.fetchone()[0]
 up,rank=(r[0],r[1])if r else(0,"Mortal")
 if not rank or rank=='none':rank="Mortal"
 av=await fetch_user_avatar(u.id,u.first_name);card=await asyncio.to_thread(gen_profile_card,u.first_name,u.id,rank,up,ws,av)
 await msg.delete();await m.answer_photo(photo=BufferedInputFile(card,filename="profile.png"),caption=f"{u.first_name}'s Tempest ID Card")
@dp.message(Command("encrypt"))
async def encrypt_cmd(m:Message):
 await handle_common(m,"encrypt");args=m.text.split(maxsplit=1)
 if len(args)<2:await m.answer("Usage: /encrypt [text]");return
 await m.answer(f"<code>{EncryptionEngine.encrypt(args[1])}</code>",parse_mode=ParseMode.HTML)
@dp.message(Command("decrypt"))
async def decrypt_cmd(m:Message):
 await handle_common(m,"decrypt");args=m.text.split(maxsplit=1)
 if len(args)<2:await m.answer("Usage: /decrypt [text]");return
 dec=EncryptionEngine.decrypt(args[1]);await m.answer(dec if dec else"Invalid!")
@dp.message(Command("tempest_join"))
async def tempest_join_cmd(m:Message):
 u,_=await handle_common(m,"tempest_join")
 if not u:return
 with sqlite3.connect("data/bot.db")as conn:
  c=conn.cursor();c.execute("SELECT cult_status FROM users WHERE user_id=?",(u.id,));r=c.fetchone()
  if r and r[0]!='none':await m.answer("Already in Tempest!");return
  c.execute("UPDATE users SET cult_status='member',cult_rank='Blood Initiate',cult_join_date=?,sacrifices=3 WHERE user_id=?",(datetime.now().isoformat(),u.id));conn.commit()
 ritual=["INITIATING BLOOD PACT...","Drawing sigils...","Channeling storm...","The void responds...","Sacrifice offered...","TEMPEST AWAKENS!"]
 msg=await m.answer("Preparing ritual...")
 for t in ritual:await asyncio.sleep(1.2);await msg.edit_text(t)
 await msg.edit_text("WELCOME TO THE TEMPEST!\nRank: Blood Initiate\nSacrifices: 3")
@dp.message(Command("tempest_story"))
async def tempest_story_cmd(m:Message):
 u,_=await handle_common(m,"tempest_story")
 if not u:return
 chapters=[("Chapter 1: Awakening","Keny Marcus opened his eyes in the obsidian realm of Tempest alongside Bablu and Ravijah. The sky burned with violet aura."),("Chapter 2: Guild of Shadows","With Bablu holding the vanguard and Ravijah orchestrating tactics, Keny forged the Tempest Guild."),("Chapter 3: Breach of Citadel","Ravijah bypassed the firewall while Bablu smashed through the fortress gates. Keny unleashed full kinetic voltage."),("Chapter 4: Reign of King","Standing atop the conquered spire, Keny, Bablu, and Ravijah gazed across the infinite grid."),("Chapter 5: The Void Calls","An ancient entity stirred. The Void whispered promises of infinite power to the three founders."),("Chapter 6: Eternal Storm","Lightning became their blood, thunder their voice. Keny, Ravijah, and Bablu - the eternal storm.")]
 msg=await m.answer("Opening Tempest Archives...");await asyncio.sleep(1.5)
 for i,(t,c)in enumerate(chapters):
  prog="["+"#"*(i+1)+"."*(len(chapters)-i-1)+"]";await msg.edit_text(f"Loading... {prog} {i+1}/{len(chapters)}");await asyncio.sleep(2);await msg.edit_text(f"{header(t)}\n\n{c}");await asyncio.sleep(5)
 await msg.edit_text("We are the eternal storm.")
@dp.message(Command("tempest_creed"))
async def tempest_creed_cmd(m:Message):
 u,_=await handle_common(m,"tempest_creed")
 if not u:return
 with sqlite3.connect("data/bot.db")as conn:c=conn.cursor();c.execute("SELECT first_name,cult_rank,sacrifices FROM users WHERE cult_status!='none'ORDER BY sacrifices DESC LIMIT 10");members=c.fetchall()
 if not members:await m.answer("No members yet!");return
 text=f"{header('TEMPEST CREED')}\n"
 for i,(n,r,s)in enumerate(members,1):text+=f"{i}. {n} - {r} ({s} sacrifices)\n"
 await m.answer(text)
@dp.message(Command("shrine"))
async def shrine_cmd(m:Message):
 u,_=await handle_common(m,"shrine")
 if not u:return
 with sqlite3.connect("data/bot.db")as conn:
  c=conn.cursor();c.execute("INSERT OR IGNORE INTO shrines(user_id)VALUES(?)",(u.id,));c.execute("SELECT power_level FROM shrines WHERE user_id=?",(u.id,));p=c.fetchone()[0];c.execute("SELECT COUNT(*)FROM shrines");tot=c.fetchone()[0];conn.commit()
 if p<25:t="Novice"
 elif p<50:t="Acolyte"
 elif p<100:t="Disciple"
 elif p<200:t="Stormcaller"
 else:t="Tempest Lord"
 await m.answer(f"{header('SHRINE')}\nRank: {t}\nPower: {p} XP\nTotal Shrines: {tot}")
@dp.message(Command("curse"))
async def curse_cmd(m:Message):
 u,_=await handle_common(m,"curse")
 if not u:return
 if not m.reply_to_message:await m.answer("Reply to curse!");return
 t=m.reply_to_message.from_user
 with sqlite3.connect("data/bot.db")as conn:conn.execute("UPDATE users SET curse_type='Bad Luck'WHERE user_id=?",(t.id,));conn.commit()
 await m.reply(f"{t.first_name} is cursed!")
@dp.message(Command("remove_curse"))
async def remove_curse_cmd(m:Message):
 u,_=await handle_common(m,"remove_curse")
 if not u:return
 if u.id!=OWNER_ID and not await is_admin(u.id):await m.answer("Admin only");return
 if not m.reply_to_message:await m.answer("Reply to remove curse!");return
 t=m.reply_to_message.from_user
 with sqlite3.connect("data/bot.db")as conn:conn.execute("UPDATE users SET curse_type='none'WHERE user_id=?",(t.id,));conn.commit()
 await m.reply(f"Curse removed from {t.first_name}!")
@dp.message(Command("time"))
async def time_cmd(m:Message):
 u,_=await handle_common(m,"time")
 if not u:return
 args=m.text.split(maxsplit=1)
 if len(args)<2 or args[1].lower().strip()not in COUNTRY_TIMEZONES:await m.answer("Usage: /time [country]");return
 country=args[1].lower().strip();tz=COUNTRY_TIMEZONES[country]
 try:now=datetime.now(ZoneInfo(tz))if ZoneInfo else datetime.utcnow();await m.answer(f"{country.upper()}: {now.strftime('%H:%M:%S')}")
 except:await m.answer("Error!")
@dp.message(Command("word"))
async def word_cmd(m:Message):
 u,_=await handle_common(m,"word")
 if not u:return
 args=m.text.split(maxsplit=1)
 if len(args)<2:await m.answer("Usage: /word [text]");return
 msg=await m.answer("Creating document...");await asyncio.sleep(1)
 doc=Document();doc.add_heading("TEMPEST ARCHIVES",0);doc.add_paragraph(f"By: {u.first_name}");doc.add_paragraph(args[1]);fn=f"temp/word_{u.id}.docx";doc.save(fn)
 await msg.delete();await m.answer_document(FSInputFile(fn));os.remove(fn)
@dp.message(Command("neko"))
async def neko_cmd(m:Message):
 await handle_common(m,"neko")
 try:
  async with httpx.AsyncClient(timeout=30)as c:r=await c.get("https://nekos.life/api/v2/img/neko")
  if r.status_code==200:await m.answer_photo(photo=r.json()["url"],caption="Neko!")
  else:await m.answer("Failed!")
 except:await m.answer("API error!")
@dp.message(Command("waifu"))
async def waifu_cmd(m:Message):
 await handle_common(m,"waifu")
 try:
  async with httpx.AsyncClient(timeout=30)as c:r=await c.get("https://nekos.life/api/v2/img/waifu")
  if r.status_code==200:await m.answer_photo(photo=r.json()["url"],caption="Waifu!")
  else:await m.answer("Failed!")
 except:await m.answer("API error!")
@dp.message(Command("link"))
async def link_cmd(m:Message):
 u,_=await handle_common(m,"link")
 if not u:return
 upload_waiting[u.id]=True;await m.answer("Send me any file!")
@dp.message(F.photo|F.video|F.document|F.audio|F.voice|F.sticker|F.animation)
async def handle_file(m:Message):
 u=m.from_user
 if u.id not in upload_waiting:return
 upload_waiting.pop(u.id,None);msg=await m.answer("Uploading...")
 try:
  fid=None;fn=f"file_{u.id}"
  if m.photo:fid=m.photo[-1].file_id;fn+=".jpg"
  elif m.video:fid=m.video.file_id;fn=m.video.file_name or fn+".mp4"
  elif m.document:fid=m.document.file_id;fn=m.document.file_name or fn
  elif m.audio:fid=m.audio.file_id;fn+=".mp3"
  elif m.voice:fid=m.voice.file_id;fn+=".ogg"
  elif m.sticker:fid=m.sticker.file_id;fn+=".webp"
  elif m.animation:fid=m.animation.file_id;fn+=".gif"
  f=await bot.get_file(fid);url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f.file_path}"
  async with httpx.AsyncClient(timeout=60)as c:r=await c.get(url)
  link=await upload_to_catbox(r.content,fn)
  if link:
   with sqlite3.connect("data/bot.db")as conn:conn.execute("UPDATE users SET uploads=uploads+1 WHERE user_id=?",(u.id,));conn.commit()
   await msg.edit_text(f"Uploaded!\n{link}")
  else:await msg.edit_text("Upload failed!")
 except Exception as e:await msg.edit_text(f"Error: {e}")
@dp.message(Command("convert"))
async def convert_cmd(m:Message):
 u,_=await handle_common(m,"convert")
 if not u:return
 if not YTDLP_AVAILABLE:await m.answer("yt-dlp not installed!");return
 args=m.text.split(maxsplit=1)
 if len(args)<2:await m.answer("Usage: /convert [URL]");return
 await m.answer("Downloading...")
@dp.message(Command("ping"))
async def ping_cmd(m:Message):
 u,_=await handle_common(m,"ping")
 if not u:return
 if u.id!=OWNER_ID and not await is_admin(u.id):await m.answer("Admin only!");return
 await m.answer(f"Pong! Uptime: {format_uptime(int(time.time()-start_time))}")
@dp.message(Command("stats"))
async def stats_cmd(m:Message):
 u,_=await handle_common(m,"stats")
 if not u:return
 if u.id!=OWNER_ID and not await is_admin(u.id):await m.answer("Admin only!");return
 with sqlite3.connect("data/bot.db")as conn:
  c=conn.cursor();c.execute("SELECT COUNT(*)FROM users");tot=c.fetchone()[0];c.execute("SELECT COUNT(*)FROM users WHERE last_active>=?",((datetime.now()-timedelta(days=7)).isoformat(),));alive=c.fetchone()[0];dead=tot-alive
 await m.answer(f"Total: {tot}\nAlive(7d): {alive}\nDead: {dead}")
@dp.message(Command("scan"))
async def scan_cmd(m:Message):await handle_common(m,"scan");await m.answer("Scan complete!")
@dp.message(Command("users"))
async def users_cmd(m:Message):
 u,_=await handle_common(m,"users")
 if not u:return
 if u.id!=OWNER_ID and not await is_admin(u.id):await m.answer("Admin only!");return
 with sqlite3.connect("data/bot.db")as conn:c=conn.cursor();c.execute("SELECT user_id,first_name,username,uploads,commands,is_banned FROM users ORDER BY commands DESC");users=c.fetchall()
 fn=f"temp/users_{int(time.time())}.txt"
 with open(fn,"w",encoding="utf-8")as f:
  f.write("TEMPEST GUIDER - USER LIST\n"+"="*40+"\n\n")
  for uid,n,un,up,cm,ban in users:f.write(f"{n} (@{un or'None'})\nID: {uid}\nUploads: {up}\nCommands: {cm}\nStatus: {'BANNED'if ban else'ACTIVE'}\n"+"-"*30+"\n")
 await m.answer_document(FSInputFile(fn),caption="User list");os.remove(fn)
@dp.message(Command("broadcast"))
async def broadcast_cmd(m:Message):
 u,_=await handle_common(m,"broadcast")
 if not u:return
 if u.id!=OWNER_ID and not await is_admin(u.id):await m.answer("Admin only!");return
 broadcast_state[u.id]="waiting";await m.answer("Send me anything to broadcast!")
@dp.message(lambda msg:msg.from_user and msg.from_user.id in broadcast_state)
async def handle_broadcast(m:Message):
 u=m.from_user;broadcast_state.pop(u.id,None)
 with sqlite3.connect("data/bot.db")as conn:c=conn.cursor();c.execute("SELECT user_id FROM users WHERE is_banned=0");users=c.fetchall()
 s=0
 for(uid,)in users:
  try:await bot.copy_message(chat_id=uid,from_chat_id=m.chat.id,message_id=m.message_id);s+=1
  except:pass
  await asyncio.sleep(0.03)
 await m.answer(f"Sent to {s} users!")
@dp.message(Command("lag"))
async def lag_cmd(m:Message):await handle_common(m,"lag");await m.answer("Lag test complete!")
@dp.message(Command("disable"))
async def disable_cmd(m:Message):
 u,_=await handle_common(m,"disable")
 if not u:return
 if u.id!=OWNER_ID and not await is_admin(u.id):await m.answer("Admin only!");return
 args=m.text.split()
 if len(args)<2:await m.answer("Usage: /disable [command]");return
 cmd=args[1].replace("/","")
 if cmd=="ai":ai_enabled=False;await m.answer("AI disabled!");return
 disabled_commands[cmd]=datetime.now()+timedelta(minutes=10);await m.answer(f"{cmd} disabled!")
@dp.message(Command("cm"))
async def cm_cmd(m:Message):
 u,_=await handle_common(m,"cm")
 if not u:return
 if u.id!=OWNER_ID and not await is_admin(u.id):await m.answer("Admin only!");return
 await m.answer(f"{header('CM')}\n/cm status\n/cm users\n/cm database")
@dp.message(Command("query"))
async def query_cmd(m:Message):
 u,_=await handle_common(m,"query")
 if not u:return
 if u.id!=OWNER_ID:await m.answer(f"Owner only. Your ID: {u.id}");return
 args=m.text.split(maxsplit=1)
 if len(args)<2:await m.answer("Usage: /query [code]");return
 code=args[1];buf=io.StringIO()
 try:
  with contextlib.redirect_stdout(buf):exec(code)
  out=buf.getvalue()or"No output";await m.answer(f"Output: {out[:3000]}")
 except Exception as e:await m.answer(f"Error: {e}")
@dp.message(Command("management"))
async def management_cmd(m:Message):
 u,_=await handle_common(m,"management")
 if not u:return
 if u.id!=OWNER_ID:await m.answer(f"Owner only. Your ID: {u.id}");return
 args=m.text.split(maxsplit=1)
 if len(args)<2:await m.answer(f"{header('MANAGEMENT')}\n/management status\n/management groq [key]\n/management toggleai");return
 sub=args[1].lower().strip()
 if sub=="status":
  t=f"{header('API STATUS')}\n"
  try:
   async with httpx.AsyncClient(timeout=15)as c:r=await c.get("https://catbox.moe/user/api.php");t+=f"Catbox: {'ALIVE'if r.status_code in[200,412]else'DOWN'}({r.status_code})\n"
  except:t+="Catbox: UNREACHABLE\n"
  t+=f"Groq: {'CONFIGURED'if GROQ_API_KEY else'NOT SET'}\nAI: {'ENABLED'if ai_enabled else'DISABLED'}\n"
  await m.answer(t)
 elif sub.startswith("groq"):
  parts=sub.split(maxsplit=1)
  if len(parts)<2:await m.answer("Usage: /management groq [key]");return
  global GROQ_API_KEY;GROQ_API_KEY=parts[1].strip();await m.answer("GROQ key updated!")
 elif sub=="toggleai":
  global ai_enabled;ai_enabled=not ai_enabled;await m.answer(f"AI: {'ON'if ai_enabled else'OFF'}")
@dp.message(Command("maintenance"))
async def maintenance_cmd(m:Message):
 global maintenance_mode
 u,_=await handle_common(m,"maintenance")
 if not u:return
 if u.id!=OWNER_ID:await m.answer("Owner only!");return
 maintenance_mode=not maintenance_mode;await m.answer(f"Maintenance: {'ON'if maintenance_mode else'OFF'}")
@dp.message(Command("clearlogs"))
async def clearlogs_cmd(m:Message):
 u,_=await handle_common(m,"clearlogs")
 if not u:return
 if u.id!=OWNER_ID:await m.answer("Owner only!");return
 with sqlite3.connect("data/bot.db")as conn:conn.execute("DELETE FROM command_logs");conn.commit()
 await m.answer("Logs cleared!")
@dp.message(Command("logs"))
async def logs_cmd(m:Message):
 u,_=await handle_common(m,"logs")
 if not u:return
 if u.id!=OWNER_ID:await m.answer("Owner only!");return
 fn=f"temp/logs_{int(time.time())}.txt"
 with sqlite3.connect("data/bot.db")as conn:
  c=conn.cursor();c.execute("SELECT timestamp,user_id,command FROM command_logs ORDER BY id DESC LIMIT 100");logs=c.fetchall()
 with open(fn,"w",encoding="utf-8")as f:
  f.write("TEMPEST GUIDER - LOGS\n"+"="*40+"\n\n")
  for ts,uid,cmd in logs:f.write(f"Time: {ts}\nUser: {uid}\nCommand: {cmd}\n"+"-"*20+"\n")
 await m.answer_document(FSInputFile(fn),caption="Complete logs");os.remove(fn)
@dp.message(Command("pro"))
async def pro_cmd(m:Message):
 u,_=await handle_common(m,"pro")
 if not u:return
 if u.id!=OWNER_ID:await m.answer("Owner only!");return
 args=m.text.split()
 if len(args)<2 or not args[1].isdigit():await m.answer("Usage: /pro [user_id]");return
 tid=int(args[1])
 with sqlite3.connect("data/bot.db")as conn:conn.execute("UPDATE users SET is_admin=1 WHERE user_id=?",(tid,));conn.commit()
 await m.answer(f"User {tid} is admin!")
@dp.message(Command("backup"))
async def backup_cmd(m:Message):
 u,_=await handle_common(m,"backup")
 if not u:return
 if u.id!=OWNER_ID:await m.answer("Owner only!");return
 ts=datetime.now().strftime("%Y%m%d_%H%M%S");bf=f"backups/backup_{ts}.db";shutil.copy2("data/bot.db",bf);await m.answer_document(FSInputFile(bf));os.remove(bf)
@dp.message(Command("rem"))
async def rem_cmd(m:Message):
 u,_=await handle_common(m,"rem")
 if not u:return
 if u.id!=OWNER_ID:await m.answer("Owner only!");return
 pending_restore[u.id]=True;await m.answer("Upload .db file!")
@dp.message(Command("restart"))
async def restart_cmd(m:Message):
 u,_=await handle_common(m,"restart")
 if not u:return
 if u.id!=OWNER_ID:await m.answer("Owner only!");return
 await m.answer("Restarting...");upload_waiting.clear();broadcast_state.clear();disabled_commands.clear();conversation_memory.clear();os.execv(sys.executable,['python']+sys.argv)
@dp.message(Command("cancel"))
async def cancel_cmd(m:Message):
 u,_=await handle_common(m,"cancel")
 if not u:return
 upload_waiting.pop(u.id,None);broadcast_state.pop(u.id,None);pending_restore.pop(u.id,None);await m.answer("Cancelled!")
@dp.message(Command("ban"))
async def ban_cmd(m:Message):
 u,_=await handle_common(m,"ban")
 if not u:return
 if u.id!=OWNER_ID and not await is_admin(u.id):await m.answer("Admin only!");return
 if not m.reply_to_message:await m.answer("Reply to ban!");return
 t=m.reply_to_message.from_user
 if t.id==OWNER_ID:await m.answer("Cannot ban Owner!");return
 with sqlite3.connect("data/bot.db")as conn:conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?",(t.id,));conn.commit()
 await m.reply(f"{t.first_name} banned!")
@dp.message(Command("unban"))
async def unban_cmd(m:Message):
 u,_=await handle_common(m,"unban")
 if not u:return
 if u.id!=OWNER_ID and not await is_admin(u.id):await m.answer("Admin only!");return
 args=m.text.split()
 if len(args)<2 or not args[1].isdigit():await m.answer("Usage: /unban [user_id]");return
 tid=int(args[1])
 with sqlite3.connect("data/bot.db")as conn:conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?",(tid,));conn.commit()
 await m.answer(f"User {tid} unbanned!")
@dp.message(Command("banlist"))
async def banlist_cmd(m:Message):
 u,_=await handle_common(m,"banlist")
 if not u:return
 if u.id!=OWNER_ID and not await is_admin(u.id):await m.answer("Admin only!");return
 with sqlite3.connect("data/bot.db")as conn:c=conn.cursor();c.execute("SELECT user_id,first_name FROM users WHERE is_banned=1");banned=c.fetchall()
 if not banned:await m.answer("No banned users!");return
 text="BANNED USERS\n"
 for uid,n in banned:text+=f"{n} ({uid})\n"
 await m.answer(text)
@dp.message()
async def tempest_ai(m:Message):
 if not ai_enabled:return
 if m.from_user.is_bot:return
 text=m.text or m.caption or""
 if m.chat.type in[ChatType.GROUP,ChatType.SUPERGROUP]:
  with sqlite3.connect("data/bot.db")as conn:conn.execute("INSERT OR IGNORE INTO groups(group_id,title,joined_date)VALUES(?,?,?)",(m.chat.id,str(m.chat.title),datetime.now().isoformat()));conn.commit()
 if"tempest"not in text.lower():return
 uid=m.from_user.id;query=text.replace("/tempest","").strip()or text.strip()
 if uid not in conversation_memory:conversation_memory[uid]=[]
 with sqlite3.connect("data/bot.db")as conn:
  c=conn.cursor();c.execute("SELECT role,content FROM conversation_history WHERE user_id=?ORDER BY timestamp DESC LIMIT 20",(uid,));hist=c.fetchall()
  for role,content in reversed(hist):conversation_memory[uid].append({"role":role,"content":content})
 conversation_memory[uid].append({"role":"user","content":query})
 proc=await m.answer("Tempest is thinking...")
 if GROQ_API_KEY:
  try:
   url="https://api.groq.com/openai/v1/chat/completions";headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"}
   sp=("You are Tempest AI - a storm-themed entity. Creator: @Nocis_creed (Keny) - https://t.me/Nocis_creed. Dev: @dont_try_to_copy_mee (Ravijah) - https://t.me/dont_try_to_copy_mee. Remember conversations. Never break character.")
   msgs=[{"role":"system","content":sp}]+conversation_memory[uid][-20:]
   payload={"model":"openai/gpt-oss-20b","messages":msgs,"temperature":0.7,"max_tokens":1024}
   def _req():
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers=headers,method="POST")
    with urllib.request.urlopen(req)as r:return json.loads(r.read().decode())["choices"][0]["message"]["content"]
   resp=await asyncio.to_thread(_req)
   conversation_memory[uid].append({"role":"assistant","content":resp})
   with sqlite3.connect("data/bot.db")as conn:
    conn.execute("INSERT INTO conversation_history(user_id,role,content,timestamp)VALUES(?,'user',?,?)",(uid,query,datetime.now().isoformat()));conn.execute("INSERT INTO conversation_history(user_id,role,content,timestamp)VALUES(?,'assistant',?,?)",(uid,resp,datetime.now().isoformat()));conn.commit()
   await proc.edit_text(f"Tempest AI:\n\n{resp}")
  except Exception as e:await proc.edit_text(f"Error: {e}")
 else:await proc.edit_text("AI not configured. Use /management groq [key]")
async def main():
 await ensure_font()if'ensure_font'in globals()else None
 print("Starting...");await send_log("Bot started!")
 while True:
  try:await dp.start_polling(bot)
  except Exception as e:print(f"Error: {e}");await asyncio.sleep(10)
if __name__=="__main__":asyncio.run(main())