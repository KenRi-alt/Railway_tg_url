#!/usr/bin/env python3
# ========== STORY & PROFILE GENERATOR ==========

import asyncio
import random
import json
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

# ========== PROFILE CARD GENERATOR ==========
class ProfileGenerator:
    def __init__(self):
        self.font_path = self.get_font()
        
    def get_font(self):
        """Get font path, download if needed"""
        font_dir = "fonts"
        os.makedirs(font_dir, exist_ok=True)
        
        font_urls = [
            "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
            "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
        ]
        
        for url in font_urls:
            font_name = url.split("/")[-1]
            font_path = os.path.join(font_dir, font_name)
            
            if not os.path.exists(font_path):
                try:
                    print(f"Downloading {font_name}...")
                    response = requests.get(url)
                    with open(font_path, 'wb') as f:
                        f.write(response.content)
                except:
                    print(f"Failed to download {font_name}")
        
        # Return any available font
        for font_file in os.listdir(font_dir):
            if font_file.endswith(('.ttf', '.otf')):
                return os.path.join(font_dir, font_file)
        
        return None
    
    def create_profile_card(self, user_data, cult_data, profile_pic_url=None):
        """Create beautiful profile card"""
        # Card dimensions
        width = 800
        height = 1000
        
        # Create base image with gradient
        img = Image.new('RGB', (width, height), color=(20, 20, 40))
        draw = ImageDraw.Draw(img)
        
        # Add gradient effect
        for y in range(height):
            r = 20 + int(30 * y / height)
            g = 20 + int(20 * y / height)
            b = 40 + int(30 * y / height)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Load fonts
        try:
            title_font = ImageFont.truetype(self.font_path, 42) if self.font_path else ImageFont.load_default()
            name_font = ImageFont.truetype(self.font_path, 36) if self.font_path else ImageFont.load_default()
            stat_font = ImageFont.truetype(self.font_path, 24) if self.font_path else ImageFont.load_default()
            small_font = ImageFont.truetype(self.font_path, 18) if self.font_path else ImageFont.load_default()
        except:
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            stat_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add profile picture
        if profile_pic_url:
            try:
                response = requests.get(profile_pic_url, timeout=5)
                profile_pic = Image.open(BytesIO(response.content))
                
                # Resize and make circular
                profile_pic = profile_pic.resize((200, 200))
                
                # Create circular mask
                mask = Image.new('L', (200, 200), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, 200, 200), fill=255)
                
                # Apply mask
                profile_pic.putalpha(mask)
                
                # Add to image
                img.paste(profile_pic, (width//2 - 100, 50), profile_pic)
                
            except:
                # Draw placeholder circle
                draw.ellipse([(width//2 - 100, 50), (width//2 + 100, 250)], 
                           outline=(255, 215, 0), width=5)
        
        # User name
        draw.text((width//2, 280), user_data['name'], font=name_font, 
                 fill=(255, 255, 255), anchor="mm")
        
        # Tempest banner
        banner_y = 350
        draw.rectangle([(50, banner_y), (width-50, banner_y + 60)], 
                      fill=(40, 40, 80), outline=(100, 100, 255))
        
        draw.text((width//2, banner_y + 20), "🌩️ TEMPEST CULT", font=title_font,
                 fill=(150, 200, 255), anchor="mm")
        
        # Rank display
        rank_y = banner_y + 80
        rank_text = f"{cult_data.get('rank', 'Mortal')}"
        draw.text((width//2, rank_y), rank_text, font=name_font,
                 fill=(255, 215, 0), anchor="mm")
        
        # Stats grid
        stats = [
            ("⭐ Points", str(cult_data.get('points', 0))),
            ("💰 Coins", str(cult_data.get('coins', 0))),
            ("🩸 Sacrifices", str(cult_data.get('sacrifices', 0))),
            ("⚔️ Battles", f"{cult_data.get('battle_wins', 0)}/{cult_data.get('battle_losses', 0)}"),
            ("❤️ Health", str(cult_data.get('health', 100))),
            ("🎯 Critical", f"{cult_data.get('critical', 0)*100:.1f}%")
        ]
        
        for i, (label, value) in enumerate(stats):
            row = i // 2
            col = i % 2
            
            x = 100 + col * 300
            y = rank_y + 60 + row * 80
            
            # Stat box
            draw.rounded_rectangle([(x, y), (x + 250, y + 60)], radius=10,
                                 fill=(50, 50, 80), outline=(80, 80, 120))
            
            # Label
            draw.text((x + 10, y + 5), label, font=small_font,
                     fill=(150, 150, 200))
            
            # Value
            draw.text((x + 10, y + 25), value, font=stat_font,
                     fill=(255, 255, 255))
        
        # Bottom info
        bottom_y = height - 50
        draw.text((width//2, bottom_y), f"ID: {user_data['id']}", font=small_font,
                 fill=(150, 150, 150), anchor="mm")
        
        # Add storm effects
        self.add_effects(img, cult_data)
        
        # Save to bytes
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG', quality=95)
        img_bytes.seek(0)
        
        return img_bytes.getvalue()
    
    def add_effects(self, img, cult_data):
        """Add visual effects based on cult stats"""
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        points = cult_data.get('points', 0)
        intensity = min(points / 1000, 1.0)
        
        if intensity > 0.1:
            # Add lightning
            for _ in range(int(intensity * 3)):
                x = random.randint(100, width - 100)
                y = random.randint(100, height - 200)
                
                points = [(x, y)]
                for _ in range(random.randint(2, 5)):
                    x += random.randint(-30, 30)
                    y += random.randint(30, 60)
                    points.append((x, y))
                
                draw.line(points, fill=(100, 200, 255, int(200 * intensity)), 
                         width=random.randint(1, 2))
        
        if intensity > 0.5:
            # Add glow
            for _ in range(int(intensity * 2)):
                x = random.randint(50, width - 50)
                y = random.randint(50, height - 50)
                radius = random.randint(20, 50)
                
                for r in range(radius, 0, -3):
                    alpha = int(50 * intensity * (r / radius))
                    draw.ellipse([(x-r, y-r), (x+r, y+r)], 
                               outline=(100, 150, 255, alpha))

# ========== STORY SYSTEM ==========
STORY_CHAPTERS = {
    1: {
        "title": "🌌 CHAPTER 1: THE WHISPER IN STATIC",
        "content": """
It begins with a whisper. Not a sound you hear,
but one you feel in your bones.
A crackle in the silence between heartbeats.

You were just uploading files, like always.
But something was different this time.
The pixels arranged themselves differently.
The code whispered back.

The Tempest doesn't announce itself.
It invites through patterns only certain minds see.
You saw. You heard. You followed.

This is where normal ends.
        """
    },
    2: {
        "title": "⚡ CHAPTER 2: THE FIRST SPARK",
        "content": """
Ravijah wasn't born. He emerged.
From the first unregulated lightning bolt,
from the first server that crashed mysteriously,
from the first data packet that arrived before it was sent.

He is the anomaly in the system.
The bug that became a feature.
The error that became truth.

When you joined, you didn't just sign up.
You became part of the anomaly.
Your uploads now feed something ancient.
Your clicks now power something hungry.
        """
    },
    3: {
        "title": "🌀 CHAPTER 3: THE DIGITAL STORM",
        "content": """
The Tempest lives in the spaces between.
Between 0 and 1. Between on and off.
Between sent and received.

Every file you upload is a sacrifice.
Every link you generate is a prayer.
Every battle you fight is a ritual.

You thought you were just using a bot.
But the bot was using you too.
Gathering power. Building strength.
Preparing for something... bigger.

The storm grows with each member.
And you are now part of the weather.
        """
    }
}

# ========== PUBLIC FUNCTIONS ==========
profile_gen = ProfileGenerator()

async def generate_tempest_profile(user_data, cult_data, profile_pic_url=None):
    """Generate profile card (async wrapper)"""
    try:
        return profile_gen.create_profile_card(user_data, cult_data, profile_pic_url)
    except Exception as e:
        print(f"Profile generation error: {e}")
        return None

async def get_story_chapter(chapter_num):
    """Get story chapter by number"""
    if chapter_num in STORY_CHAPTERS:
        return STORY_CHAPTERS[chapter_num]
    return None

async def tell_story(chapter_num, max_parts=3):
    """Tell a story chapter in parts"""
    chapter = await get_story_chapter(chapter_num)
    if not chapter:
        return []
    
    content = chapter['content'].strip().split('\n\n')
    parts = []
    
    # Add title
    parts.append(f"📜 {chapter['title']}\n")
    
    # Add content in parts
    for i, part in enumerate(content[:max_parts]):
        parts.append(f"{part}\n")
    
    return parts

async def get_random_prophecy():
    """Get a random prophecy"""
    prophecies = [
        "The seventh sacrifice will open the Elder Gate.",
        "When silence falls completely, the true tempest begins.",
        "A great schism will come, brother against storm-brother.",
        "The final battle will be fought not with steel, but with data.",
        "Ravijah will return when the world needs chaos most."
    ]
    
    return random.choice(prophecies)

async def get_cult_quote():
    """Get a random cult quote"""
    quotes = [
        "The storm doesn't ask permission; it announces.",
        "In chaos, we find our true power.",
        "Every upload is a prayer to the digital gods.",
        "Silence is the enemy; noise is our weapon.",
        "Your data is your soul; protect it fiercely."
    ]
    
    return random.choice(quotes)

# ========== BATTLE ANIMATIONS ==========
async def generate_battle_animation(player1, player2, action, damage):
    """Create battle animation description"""
    actions = {
        "⚔️ Slash": f"{player1} slashes at {player2} for {damage} damage!",
        "🛡️ Block": f"{player1} blocks {player2}'s attack and heals 20 HP!",
        "❤️ Heal": f"{player1} channels healing energy, restoring 30 HP!",
        "🔥 Fire": f"{player1} engulfs {player2} in flames for {damage} damage!",
        "❄️ Ice": f"{player1} freezes {player2} solid for {damage} damage!",
        "⚡ Shock": f"{player1} strikes {player2} with lightning for {damage} damage!"
    }
    
    return actions.get(action, f"{player1} attacks {player2}!")

# ========== INITIATION RITUAL ==========
async def perform_initiation_ritual(user_name):
    """Perform initiation ritual"""
    steps = [
        f"🌀 The storm senses {user_name}'s presence...",
        "⚡ Ancient algorithms awaken...",
        "🌪️ Data winds begin to swirl...",
        "🩸 Digital blood is offered...",
        "💀 The pact is written in code...",
        f"👁️ {user_name} is now part of the Tempest!"
    ]
    
    return steps

# ========== MAIN TEST ==========
if __name__ == "__main__":
    # Test the generator
    print("📖 Story & Profile System")
    print("=" * 40)
    
    test_data = {
        'id': 123456789,
        'name': 'Test User'
    }
    
    test_cult = {
        'rank': 'Blood Initiate',
        'points': 150,
        'coins': 200,
        'sacrifices': 5,
        'battle_wins': 3,
        'battle_losses': 1,
        'health': 85,
        'critical': 0.07
    }
    
    print("✅ Profile generator ready")
    print(f"📚 Chapters available: {len(STORY_CHAPTERS)}")
    
    # Test story
    async def test():
        story = await tell_story(1)
        for part in story:
            print(part)
        
        print(f"🌀 Prophecy: {await get_random_prophecy()}")
        print(f"💬 Quote: {await get_cult_quote()}")
    
    asyncio.run(test())
