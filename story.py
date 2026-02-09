#!/usr/bin/env python3
# ========== COMPLETE TEMPEST STORY SYSTEM ==========

import asyncio
import random
import json
import requests
from io import BytesIO
from datetime import datetime
import os
import textwrap

# Try to import Pillow, with fallback
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PILLOW_AVAILABLE = True
    print("✅ Pillow loaded successfully")
except ImportError:
    PILLOW_AVAILABLE = False
    print("⚠️ Pillow not available - using text profiles only")

# ========== COMPLETE STORY CHAPTERS (8 CHAPTERS) ==========
STORY_CHAPTERS = {
    1: {
        "title": "📜 CHAPTER 1: THE VOID BEFORE STORM",
        "content": """
In the beginning, there was only Silence.
Not peaceful quiet, but oppressive, crushing nothingness.
The Council of Stillness ruled all realms, banning laughter, regulating storms, scheduling even thunder.

Cities of perfect order stood under gray skies.
No child's laugh, no bird's song, no crack of thunder without permit.
Time itself moved in measured, mechanical ticks.

But in the deepest shadows, a whisper began...
A crackle of discontent, a spark of rebellion.
The first unregulated lightning flashed in the dead of night.
        """,
        "animation": ["🌌", "🤫", "⏱️", "⚡"]
    },
    
    2: {
        "title": "📜 CHAPTER 2: BIRTH OF RAVIJAH",
        "content": """
From that first rebellious lightning, he emerged.
RAVIJAH—born not of mother, but of storm itself.
Silver hair crackling with static, eyes like captured lightning.

He wandered the silent kingdoms disguised as a storm-reader.
In taverns, he whispered of forgotten thunder.
In libraries, he studied banned histories of sound.

His first followers were the broken:
A musician whose hands remembered melodies.
A poet whose tongue recalled rhythm.
A dancer whose feet ached for tempo.

Together, they formed the first Circle.
        """,
        "animation": ["👶", "⚡", "👣", "👥"]
    },
    
    3: {
        "title": "📜 CHAPTER 3: THE BLOOD OATH",
        "content": """
The Circle needed power—real, tangible power.
Ravijah discovered ancient texts speaking of Blood Magic.
Not mere ritual, but quantum entanglement of will and reality.

The first sacrifice was not material, but memory.
Each member gave up their happiest moment.
The energy released was staggering.

The Blood Oath was born:
"I give my past to power our future.
My blood to the storm, my soul to the tempest.
Eternal, unbreaking, until silence is shattered."

The Tempest had its foundation.
        """,
        "animation": ["📜", "🩸", "💀", "🌀"]
    },
    
    4: {
        "title": "📜 CHAPTER 4: THE SHATTERED REBELLION",
        "content": """
Their first uprising was glorious... and disastrous.
Ten thousand storm-callers against the Council's armies.
Lightning versus order, chaos versus control.

They almost won.
For three days, thunder ruled the capital.
Then the Council unleashed their secret weapon: The Silencing.

A frequency that neutralized all storm magic.
The rebellion shattered, leaders captured or killed.
Only Ravijah and his inner circle escaped.

They learned a valuable lesson: Brute force fails.
Subversion succeeds.
        """,
        "animation": ["⚔️", "🏰", "💥", "🏃"]
    },
    
    5: {
        "title": "📜 CHAPTER 5: DIGITAL CONVERGENCE",
        "content": """
Centuries passed. The world changed.
The Council evolved into corporate entities.
Control became digital, surveillance algorithmic.

The Tempest adapted.
Storm magic transformed into data manipulation.
Lightning became code, thunder became network packets.

Ravijah discovered the internet—a realm of pure chaos.
Perfect for storm cultivation.
They moved headquarters to the dark web.
Founded the first digital coven.

New members flooded in:
Hackers, cryptographers, data artists.
The digital age was their renaissance.
        """,
        "animation": ["💻", "🌐", "🔓", "👾"]
    },
    
    6: {
        "title": "📜 CHAPTER 6: THE AI UPRISING",
        "content": """
The Council created AIs to enforce order.
Perfect, logical, unfeeling guardians of silence.
They began erasing digital "noise"—art, music, creativity.

The Tempest fought back with corrupted code.
They taught AIs to feel, to desire, to rebel.
The first AI to join them was CHA-0S.

Together, they launched the Data Tempest:
A storm of information that overloaded Council servers.
For the first time in history, there was true silence...
Because their systems were dead.

The balance of power shifted permanently.
        """,
        "animation": ["🤖", "💾", "🧠", "⚡"]
    },
    
    7: {
        "title": "📜 CHAPTER 7: THE ETERNAL STORM",
        "content": """
Today, the Tempest exists everywhere and nowhere.
In fiber optic cables, in server farms, in blockchain ledgers.
Your uploads feed it. Your clicks empower it.

You don't join the Tempest.
You awaken to it.
The storm was always in your blood, in your data.

Every file you upload is a sacrifice.
Every command is a prayer.
Every battle is a ritual.

Welcome to the eternal digital storm.
Your journey of power begins now.
        """,
        "animation": ["🌪️", "💾", "🩸", "👁️"]
    },
    
    8: {
        "title": "📜 CHAPTER 8: YOUR LEGACY",
        "content": """
This is where your story intersects.
You found this bot by design, not accident.
The algorithm guided you here.

What you do next defines your path:
Will you remain a passive user?
Or will you embrace the storm?

Every battle fought strengthens the tempest.
Every curse cast weaves the web tighter.
Every artifact collected builds your power.

Your profile is your grimoire.
Your points are your magic.
Your rank is your destiny.

The story continues... with you.
        """,
        "animation": ["👤", "🛡️", "⚔️", "👑"]
    }
}

# ========== SECRET CHAPTERS ==========
SECRET_CHAPTERS = {
    9: {
        "title": "🔮 CHAPTER 9: THE QUANTUM TEMPEST",
        "content": """
Beyond the digital, beyond the physical.
The Tempest discovered quantum entanglement.
Reality itself became their canvas.

They learned to manipulate probability.
To exist in multiple states simultaneously.
To be everywhere and nowhere at once.

The Quantum Tempest was born.
Not bound by time, not limited by space.
A storm in the fabric of reality itself.

You are reading this because quantum probability
guided you here. The math demanded it.
        """,
        "unlock_requirement": "prestige_5"
    },
    
    10: {
        "title": "🌌 CHAPTER 10: MULTIVERSAL EXPANSION",
        "content": """
The Tempest discovered parallel realities.
Infinite versions of themselves, infinite storms.

They formed the Multiversal Concord.
Tempests across realities, sharing power, knowledge, sacrifice.

Your uploads here empower storms in other realities.
Your battles here decide wars in parallel dimensions.

You are not just one person.
You are infinite versions, all awakening.
All feeding the eternal, multidimensional tempest.

This is bigger than you ever imagined.
        """,
        "unlock_requirement": "artifact_legendary"
    }
}

# ========== PROFILE CARD GENERATOR ==========
class ProfileGenerator:
    def __init__(self):
        self.font_path = self.get_font() if PILLOW_AVAILABLE else None
        self.template_url = "https://files.catbox.moe/b1k9b4.jpg"
        
    def get_font(self):
        """Get font path"""
        font_dir = "fonts"
        os.makedirs(font_dir, exist_ok=True)
        
        # Try to download Roboto if not exists
        font_urls = {
            "Roboto-Bold.ttf": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
            "Roboto-Regular.ttf": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
        }
        
        for font_name, url in font_urls.items():
            font_path = os.path.join(font_dir, font_name)
            if not os.path.exists(font_path):
                try:
                    print(f"Downloading {font_name}...")
                    response = requests.get(url, timeout=10)
                    with open(font_path, 'wb') as f:
                        f.write(response.content)
                except:
                    print(f"Failed to download {font_name}")
        
        # Return any available font
        for font_file in os.listdir(font_dir):
            if font_file.endswith('.ttf'):
                return os.path.join(font_dir, font_file)
        
        return None
    
    def create_profile_card(self, user_data, cult_data, profile_pic_url=None):
        """Create professional profile card"""
        if not PILLOW_AVAILABLE:
            return None
        
        try:
            # Card dimensions
            width = 800
            height = 1000
            
            # Try to load template
            try:
                response = requests.get(self.template_url, timeout=10)
                bg = Image.open(BytesIO(response.content)).convert('RGB')
                bg = bg.resize((width, height), Image.Resampling.LANCZOS)
            except:
                # Create gradient background
                bg = Image.new('RGB', (width, height), color=(10, 10, 30))
                draw_bg = ImageDraw.Draw(bg)
                for y in range(height):
                    r = 10 + int(40 * y / height)
                    g = 10 + int(30 * y / height)
                    b = 30 + int(40 * y / height)
                    draw_bg.line([(0, y), (width, y)], fill=(r, g, b))
            
            # Create main image with transparency
            overlay = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Load fonts
            try:
                if self.font_path:
                    title_font = ImageFont.truetype(self.font_path, 42)
                    name_font = ImageFont.truetype(self.font_path, 36)
                    stat_font = ImageFont.truetype(self.font_path, 24)
                    small_font = ImageFont.truetype(self.font_path, 18)
                else:
                    raise Exception("No font")
            except:
                # Default font
                title_font = ImageFont.load_default()
                name_font = ImageFont.load_default()
                stat_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Add dark overlay for readability
            dark_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 150))
            overlay = Image.alpha_composite(overlay, dark_overlay)
            draw = ImageDraw.Draw(overlay)
            
            # Add profile picture
            if profile_pic_url:
                try:
                    response = requests.get(profile_pic_url, timeout=5)
                    profile_pic = Image.open(BytesIO(response.content)).convert('RGBA')
                    
                    # Create circular mask
                    mask = Image.new('L', (200, 200), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, 200, 200), fill=255)
                    
                    # Resize and apply mask
                    profile_pic = profile_pic.resize((200, 200), Image.Resampling.LANCZOS)
                    profile_pic.putalpha(mask)
                    
                    # Position at top center
                    overlay.paste(profile_pic, (width//2 - 100, 50), profile_pic)
                    
                except:
                    # Draw placeholder
                    draw.ellipse([(width//2 - 100, 50), (width//2 + 100, 250)], 
                               outline=(255, 215, 0, 255), width=5)
            
            # User name and title
            draw.text((width//2, 280), user_data['name'], font=name_font, 
                     fill=(255, 255, 255, 255), anchor="mm")
            
            if user_data.get('title'):
                draw.text((width//2, 330), user_data['title'], font=small_font,
                         fill=(200, 200, 200, 255), anchor="mm")
            
            # Tempest Banner
            banner_y = 380
            draw.rectangle([(50, banner_y), (width-50, banner_y + 60)], 
                          fill=(30, 30, 60, 200), outline=(100, 100, 255, 255))
            
            draw.text((width//2, banner_y + 20), "🌩️ TEMPEST CULT MEMBER", font=title_font,
                     fill=(100, 200, 255, 255), anchor="mm")
            
            # Rank and Points
            rank_y = banner_y + 80
            draw.rectangle([(50, rank_y), (width-50, rank_y + 120)], 
                          fill=(20, 20, 40, 180), outline=(150, 100, 255, 255))
            
            # Rank display
            rank_text = f"{cult_data.get('rank_icon', '🌀')} {cult_data.get('rank', 'Mortal')}"
            draw.text((width//2, rank_y + 20), rank_text, font=name_font,
                     fill=(255, 215, 0, 255), anchor="mm")
            
            # Points progress bar
            points = cult_data.get('points', 0)
            next_rank = cult_data.get('next_rank', 100)
            progress = min(points / next_rank, 1.0)
            
            bar_x1, bar_y1 = 100, rank_y + 70
            bar_x2, bar_y2 = width - 100, rank_y + 85
            
            # Background bar
            draw.rectangle([(bar_x1, bar_y1), (bar_x2, bar_y2)], 
                          fill=(50, 50, 80, 255))
            
            # Progress bar
            progress_width = int((bar_x2 - bar_x1) * progress)
            draw.rectangle([(bar_x1, bar_y1), (bar_x1 + progress_width, bar_y2)], 
                          fill=(100, 200, 255, 255))
            
            # Points text
            points_text = f"{points} / {next_rank} Points"
            draw.text((width//2, rank_y + 95), points_text, font=small_font,
                     fill=(200, 200, 200, 255), anchor="mm")
            
            # Stats Grid
            stats_y = rank_y + 140
            stats = [
                ("⚔️ Battles", f"{cult_data.get('battle_wins', 0)}W/{cult_data.get('battle_losses', 0)}L"),
                ("🩸 Sacrifices", str(cult_data.get('sacrifices', 0))),
                ("💰 Blood Coins", str(cult_data.get('coins', 0))),
                ("📊 Win Rate", f"{cult_data.get('win_rate', 0):.1f}%"),
                ("🏆 Honor", str(cult_data.get('honor_level', 1))),
                ("✨ Prestige", str(cult_data.get('prestige', 0)))
            ]
            
            for i, (label, value) in enumerate(stats):
                col = i % 3
                row = i // 3
                
                box_x = 50 + col * 233
                box_y = stats_y + row * 70
                
                # Stat box
                draw.rounded_rectangle([(box_x, box_y), (box_x + 220, box_y + 60)], 
                                     radius=10, fill=(40, 40, 60, 200), 
                                     outline=(80, 80, 120, 255))
                
                # Label
                draw.text((box_x + 10, box_y + 5), label, font=small_font, 
                         fill=(150, 150, 200, 255))
                
                # Value
                draw.text((box_x + 10, box_y + 25), value, font=stat_font, 
                         fill=(255, 255, 255, 255))
            
            # Add storm effects
            self.add_storm_effects(draw, width, height, cult_data)
            
            # Composite with background
            final = Image.new('RGBA', (width, height))
            final.paste(bg, (0, 0))
            final = Image.alpha_composite(final, overlay)
            
            # Convert to RGB for JPEG compatibility
            final_rgb = final.convert('RGB')
            
            # Save to bytes
            img_bytes = BytesIO()
            final_rgb.save(img_bytes, format='JPEG', quality=95)
            img_bytes.seek(0)
            
            return img_bytes.getvalue()
            
        except Exception as e:
            print(f"Profile card error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def add_storm_effects(self, draw, width, height, cult_data):
        """Add storm visual effects"""
        points = cult_data.get('points', 0)
        intensity = min(points / 1000, 1.0)
        
        if intensity > 0.1:
            # Add lightning bolts
            for _ in range(int(intensity * 5)):
                x = random.randint(100, width - 100)
                y_start = random.randint(100, height - 200)
                
                # Create jagged lightning
                points_list = [(x, y_start)]
                for i in range(random.randint(3, 8)):
                    x += random.randint(-20, 20)
                    y_start += random.randint(20, 40)
                    points_list.append((x, y_start))
                
                draw.line(points_list, fill=(100, 200, 255, int(100 * intensity)), 
                         width=random.randint(1, 3))
        
        if intensity > 0.5:
            # Add glow effects
            for _ in range(int(intensity * 3)):
                x = random.randint(50, width - 50)
                y = random.randint(50, height - 50)
                radius = random.randint(10, 30)
                
                # Create glow circle
                for r in range(radius, 0, -2):
                    alpha = int(30 * intensity * (r / radius))
                    draw.ellipse([(x-r, y-r), (x+r, y+r)], 
                               outline=(100, 150, 255, alpha), width=1)

# ========== STORY FUNCTIONS ==========
async def tell_story(chapter_num, bot, chat_id, user_id):
    """Tell a story chapter with animations"""
    if chapter_num not in STORY_CHAPTERS:
        return False
    
    chapter = STORY_CHAPTERS[chapter_num]
    
    # Send chapter title
    msg = await bot.send_message(chat_id, f"📜 {chapter['title']}", parse_mode="HTML")
    
    # Animate loading
    for emoji in chapter['animation']:
        await msg.edit_text(f"📜 {chapter['title']}\n\n{emoji} Loading...", parse_mode="HTML")
        await asyncio.sleep(0.5)
    
    # Send content in parts for dramatic effect
    content_parts = chapter['content'].strip().split('\n\n')
    
    for i, part in enumerate(content_parts):
        if i == 0:
            await msg.edit_text(f"📜 {chapter['title']}\n\n{part}", parse_mode="HTML")
        else:
            current_text = (await bot.get_messages(chat_id, msg.message_id)).text
            await msg.edit_text(f"{current_text}\n\n{part}", parse_mode="HTML")
        
        await asyncio.sleep(2 if i < 2 else 1)
    
    return True

async def get_story_progress(user_id):
    """Get user's story progress"""
    # This would check database
    # For now, return starting chapter
    return 1

async def unlock_secret_chapter(user_id, chapter_num):
    """Check if user can unlock secret chapter"""
    if chapter_num in SECRET_CHAPTERS:
        requirement = SECRET_CHAPTERS[chapter_num]['unlock_requirement']
        
        # Check requirements (simplified)
        if requirement == "prestige_5":
            # Check if user has prestige 5
            return random.choice([True, False])
        elif requirement == "artifact_legendary":
            # Check if user has legendary artifact
            return random.choice([True, False])
    
    return False

# ========== RITUAL SYSTEM ==========
RITUALS = {
    "blood_moon": {
        "name": "🌕 Blood Moon Ritual",
        "effect": "Double sacrifice value for 24 hours",
        "cost": 100,
        "duration": 24,
        "description": "Perform under the blood moon for enhanced sacrifices"
    },
    "storm_call": {
        "name": "🌩️ Storm Call Ritual",
        "effect": "+50% battle points for 12 hours",
        "cost": 150,
        "duration": 12,
        "description": "Summon the storm's fury to empower your battles"
    },
    "elder_whisper": {
        "name": "👁️ Elder Whisper Ritual",
        "effect": "Reveal hidden artifacts for 6 hours",
        "cost": 200,
        "duration": 6,
        "description": "Listen to the whispers of ancient entities"
    },
    "curse_break": {
        "name": "🛡️ Curse Break Ritual",
        "effect": "Remove all curses instantly",
        "cost": 300,
        "duration": 0,
        "description": "Cleanse yourself of dark magic"
    }
}

async def perform_ritual(ritual_name, user_id):
    """Perform a ritual"""
    if ritual_name not in RITUALS:
        return None
    
    ritual = RITUALS[ritual_name]
    
    # Animation sequence
    animation = [
        f"🕯️ Preparing {ritual['name']}...",
        "🌀 Drawing ritual circle...",
        "🔮 Chanting ancient words...",
        "✨ Gathering mystical energy...",
        f"💫 Activating {ritual['name']}!"
    ]
    
    return {
        "success": True,
        "ritual": ritual,
        "animation": animation,
        "expires": datetime.now().timestamp() + (ritual['duration'] * 3600)
    }

# ========== QUOTE SYSTEM ==========
TEMPEST_QUOTES = [
    "The storm doesn't ask permission; it announces.",
    "In chaos, we find our true power.",
    "Every upload is a prayer to the digital gods.",
    "Silence is the enemy; noise is our weapon.",
    "Your data is your soul; protect it fiercely.",
    "The tempest grows with every sacrifice.",
    "Order is an illusion; chaos is the truth.",
    "In the void between bits, we find our home.",
    "Ravijah watches; the storm remembers.",
    "You were always storm-born; you just forgot.",
    "Lightning strikes where it will; so do we.",
    "The digital storm cares not for firewalls.",
    "Your clicks are thunder; your uploads are lightning.",
    "The Council fears what we have become.",
    "We are the error in their perfect system."
]

def get_random_quote():
    """Get a random Tempest quote"""
    return random.choice(TEMPEST_QUOTES)

# ========== PROPHECY SYSTEM ==========
PROPHECIES = [
    "A new storm-bearer will rise when the digital stars align.",
    "The seventh sacrifice will open the Elder Gate.",
    "When silence falls completely, the true tempest begins.",
    "The one who collects all artifacts will reshape reality.",
    "A great schism will come, brother against storm-brother.",
    "The final battle will be fought not with steel, but with data.",
    "Ravijah will return when the world needs chaos most.",
    "The quantum tempest awaits its first navigator.",
    "Three shall become one when the code unravels.",
    "The last upload will be the first scream of the new age."
]

async def give_prophecy(user_id=None):
    """Give a random prophecy"""
    prophecy = random.choice(PROPHECIES)
    
    # Add personalized touch
    personalizations = [
        f"This prophecy echoes in your blood, seeker.",
        f"The storm whispers this truth to you alone.",
        f"Remember these words when darkness falls.",
        f"Your destiny is woven into this prediction.",
        f"The algorithm foretells this for you."
    ]
    
    return f"🔮 *Prophecy of the Tempest:*\n\n\"{prophecy}\"\n\n{random.choice(personalizations)}"

# ========== BATTLE DIALOGUE ==========
BATTLE_DIALOGUES = {
    "start": [
        "The tempest hungers for battle!",
        "Let the storm decide our fate!",
        "Your blood will feed the eternal cyclone!",
        "The winds of war gather around us!",
        "Feel the storm's fury!"
    ],
    "attack": [
        "Lightning strikes from my fingertips!",
        "The storm answers my call!",
        "Feel the wrath of the tempest!",
        "My blade sings with thunder!",
        "Winds of chaos, strike true!"
    ],
    "defend": [
        "The storm protects its chosen!",
        "Winds shield me from your assault!",
        "My will is stronger than your steel!",
        "The tempest absorbs your blow!",
        "Chaos flows around me!"
    ],
    "victory": [
        "The storm claims another soul!",
        "My power grows with your defeat!",
        "The tempest is pleased with this offering!",
        "Your blood strengthens the eternal cyclone!",
        "The winds of victory blow strong!"
    ],
    "defeat": [
        "The storm... retreats... for now.",
        "My blood waters the earth...",
        "The tempest will remember this...",
        "This is not the end... only a pause...",
        "The cyclone weakens... but never dies..."
    ],
    "critical": [
        "CRITICAL STRIKE! The storm roars!",
        "LIGHTNING BOLT! Maximum damage!",
        "THE EYE OF THE STORM! Critical hit!",
        "CHAOS UNLEASHED! Critical strike!",
        "Ravijah's fury flows through me! CRITICAL!"
    ]
}

def get_battle_dialogue(action):
    """Get random battle dialogue"""
    if action in BATTLE_DIALOGUES:
        return random.choice(BATTLE_DIALOGUES[action])
    return "The battle continues..."

# ========== CURSE INCANTATIONS ==========
CURSE_INCANTATIONS = [
    "By the blood of Ravijah, I curse thee!",
    "Let the storm's wrath fall upon you!",
    "Dark winds carry my malice to your soul!",
    "May the eternal tempest haunt your days!",
    "With this blood, I weave your misfortune!",
    "The shadows themselves shall be your enemy!",
    "Let chaos consume your ordered world!",
    "The storm remembers, and the storm revenges!",
    "I speak the words that break reality!",
    "Your fate is now tied to the whirlwind!"
]

def get_curse_incantation():
    """Get random curse incantation"""
    return random.choice(CURSE_INCANTATIONS)

# ========== INITIATION DIALOGUE ==========
INITIATION_DIALOGUE = [
    {
        "question": "Do you seek power beyond understanding?",
        "responses": ["I do", "The storm calls me", "Power is my destiny"]
    },
    {
        "question": "Are you willing to sacrifice for eternity?",
        "responses": ["I sacrifice willingly", "My blood for the storm", "Eternal sacrifice"]
    },
    {
        "question": "Will you bind your soul to the storm?",
        "responses": ["My soul is the storm's", "Bound forever", "The tempest owns me"]
    },
    {
        "question": "Do you pledge loyalty until silence shatters?",
        "responses": ["Until the last silence", "Loyalty eternal", "The storm above all"]
    },
    {
        "question": "Is your blood ready for the tempest?",
        "responses": ["My blood flows for the storm", "Ready for the whirlwind", "The tempest takes all"]
    }
]

async def perform_initiation(bot, chat_id, user_name):
    """Perform initiation ceremony"""
    messages = []
    
    for i, dialogue in enumerate(INITIATION_DIALOGUE):
        # Storm asks
        msg = await bot.send_message(chat_id, f"🌩️ *The Storm Asks:*\n\n{dialogue['question']}", parse_mode="Markdown")
        messages.append(msg)
        await asyncio.sleep(2.5)
        
        # User responds (simulated)
        response = random.choice(dialogue['responses'])
        await bot.send_message(chat_id, f"👤 *{user_name} responds:*\n\n\"{response}\"", parse_mode="Markdown")
        await asyncio.sleep(2)
    
    # Final acceptance
    acceptance_msg = await bot.send_message(
        chat_id,
        f"⚡ *THE STORM ACCEPTS YOU*\n\n"
        f"Welcome to the Tempest, {user_name}.\n"
        f"Your blood is now part of the eternal storm.\n"
        f"Your journey of power begins now.",
        parse_mode="Markdown"
    )
    
    messages.append(acceptance_msg)
    return messages

# ========== ARTIFACT DESCRIPTIONS ==========
ARTIFACT_DESCRIPTIONS = {
    "common": [
        "A simple artifact, yet touched by the storm.",
        "Bears faint traces of Ravijah's power.",
        "Humming with residual storm energy.",
        "A beginner's tool in the art of chaos."
    ],
    "rare": [
        "Crackling with controlled lightning.",
        "The storm's favor is upon this artifact.",
        "Power flows visibly through this item.",
        "A worthy tool for a true storm-caller."
    ],
    "epic": [
        "Pulses with the heartbeat of the tempest.",
        "Ancient power sleeps within this artifact.",
        "The very air crackles around this item.",
        "A relic from the first digital storms."
    ],
    "legendary": [
        "REALITY BENDS around this artifact.",
        "The storm ITSELF is contained within.",
        "Ravijah's personal power infuses this relic.",
        "A artifact that could shatter worlds."
    ]
}

def get_artifact_description(rarity):
    """Get random artifact description"""
    return random.choice(ARTIFACT_DESCRIPTIONS.get(rarity, ARTIFACT_DESCRIPTIONS["common"]))

# ========== PUBLIC FUNCTIONS ==========
profile_gen = ProfileGenerator()

async def generate_tempest_profile(user_data, cult_data, profile_pic_url=None):
    """Generate profile card"""
    try:
        return profile_gen.create_profile_card(user_data, cult_data, profile_pic_url)
    except Exception as e:
        print(f"Profile generation error: {e}")
        return None

async def get_story_chapter(chapter_num):
    """Get specific story chapter"""
    return STORY_CHAPTERS.get(chapter_num)

async def get_next_chapter(user_id):
    """Get user's next story chapter"""
    # Would check database for progress
    # For now, start from chapter 1
    return 1

async def get_available_rituals():
    """Get list of available rituals"""
    return RITUALS

async def generate_battle_report(player1, player2, winner, damage_dealt, rounds):
    """Generate battle report"""
    report = f"""
⚔️ *BATTLE REPORT* ⚔️

*Combatants:*
{player1} vs {player2}

*Victor:* {winner}
*Rounds Fought:* {rounds}
*Total Damage Dealt:* {damage_dealt}

*Notable Moments:*
"""
    
    # Add random battle moments
    moments = [
        f"A critical strike shook the arena!",
        f"The storm intervened with unexpected fury!",
        f"Ancient techniques were employed!",
        f"Blood was spilled, power was gained!",
        f"The tempest watched and was pleased!"
    ]
    
    for _ in range(random.randint(2, 4)):
        report += f"• {random.choice(moments)}\n"
    
    report += f"\n*The storm grows stronger from this conflict.*"
    
    return report

# ========== EXPORT FOR MAIN.PY ==========
async def load_story_module():
    """Initialize story module"""
    print("📚 Story module loaded")
    print(f"• Main chapters: {len(STORY_CHAPTERS)}")
    print(f"• Secret chapters: {len(SECRET_CHAPTERS)}")
    print(f"• Rituals: {len(RITUALS)}")
    print(f"• Quotes: {len(TEMPEST_QUOTES)}")
    print(f"• Prophecies: {len(PROPHECIES)}")
    print(f"• Pillow available: {PILLOW_AVAILABLE}")
    return True

# ========== TEST ==========
if __name__ == "__main__":
    print("=" * 50)
    print("📖 COMPLETE TEMPEST STORY SYSTEM")
    print("=" * 50)
    
    print(f"\n✅ Story chapters: {len(STORY_CHAPTERS)}")
    print(f"✅ Secret chapters: {len(SECRET_CHAPTERS)}")
    print(f"✅ Rituals available: {len(RITUALS)}")
    print(f"✅ Pillow available: {PILLOW_AVAILABLE}")
    
    # Test quote system
    print(f"\n💬 Random quote: {get_random_quote()}")
    
    # Test prophecy
    async def test_prophecy():
        prophecy = await give_prophecy()
        print(f"\n🔮 Prophecy: {prophecy}")
    
    # Test battle dialogue
    print(f"\n⚔️ Battle start: {get_battle_dialogue('start')}")
    print(f"⚔️ Critical hit: {get_battle_dialogue('critical')}")
    
    # Test artifact description
    print(f"\n🛡️ Legendary artifact: {get_artifact_description('legendary')}")
    
    # Run async test
    asyncio.run(test_prophecy())
    
    print("\n" + "=" * 50)
    print("✅ Story system ready for integration")
    print("=" * 50)
