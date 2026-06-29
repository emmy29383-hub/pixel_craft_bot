"""
🎨 Pixel Craft Bot - Professional Image Generator
Creates ACTUAL images with scenes, objects, and landscapes
NO API KEY NEEDED! Uses Python's PIL to draw everything
"""

import os
import io
import logging
import random
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# ==================== CONFIGURATION ====================

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN is required!")

BOT_NAME = "Pixel Craft Bot"
BOT_USERNAME = "pixel_craft_bot"
BOT_VERSION = "3.0.0"

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ==================== CONSTANTS ====================

IMAGE_SIZES = {
    "square": {"width": 512, "height": 512, "label": "🟦 Square (512x512)"},
    "portrait": {"width": 384, "height": 512, "label": "📱 Portrait (384x512)"},
    "landscape": {"width": 512, "height": 384, "label": "🖥️ Landscape (512x384)"},
    "wide": {"width": 768, "height": 512, "label": "🖼️ Wide (768x512)"},
    "hd": {"width": 1024, "height": 768, "label": "📷 HD (1024x768)"},
}

ART_STYLES = {
    "realistic": {"label": "📷 Realistic", "style": "realistic"},
    "anime": {"label": "🎨 Anime", "style": "anime"},
    "cartoon": {"label": "✏️ Cartoon", "style": "cartoon"},
    "oil": {"label": "🖌️ Oil Painting", "style": "oil"},
    "watercolor": {"label": "💧 Watercolor", "style": "watercolor"},
    "sketch": {"label": "✒️ Sketch", "style": "sketch"},
    "cyberpunk": {"label": "💜 Cyberpunk", "style": "cyberpunk"},
    "fantasy": {"label": "🧙 Fantasy", "style": "fantasy"},
}

# ==================== USER DATA ====================

class GeneratorStates(StatesGroup):
    WAITING_PROMPT = State()

user_data: Dict[int, Dict] = {}

def get_user_data(user_id: int) -> Dict:
    if user_id not in user_data:
        user_data[user_id] = {
            "settings": {
                "size": "square",
                "style": "realistic",
                "total_generated": 0,
                "last_generated": None
            },
            "history": []
        }
    return user_data[user_id]

# ==================== KEYBOARDS ====================

def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎨 Generate", callback_data="generate"),
        InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")
    )
    builder.row(
        InlineKeyboardButton(text="💡 Ideas", callback_data="ideas"),
        InlineKeyboardButton(text="📊 Stats", callback_data="stats")
    )
    builder.row(
        InlineKeyboardButton(text="❓ Help", callback_data="help")
    )
    return builder.as_markup()

def size_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for size_id, size_data in IMAGE_SIZES.items():
        builder.row(InlineKeyboardButton(
            text=size_data["label"],
            callback_data=f"size_{size_id}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_settings"))
    return builder.as_markup()

def style_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    styles = list(ART_STYLES.items())
    for i in range(0, len(styles), 2):
        row = []
        for j in range(2):
            if i + j < len(styles):
                style_id, style_data = styles[i + j]
                row.append(InlineKeyboardButton(
                    text=style_data["label"],
                    callback_data=f"style_{style_id}"
                ))
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_settings"))
    return builder.as_markup()

def ideas_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ideas = [
        ("🌅 Sunset Beach", "sunset over ocean with palm trees"),
        ("🐱 Cute Cat", "cute cat sitting in a garden"),
        ("🚀 Space Launch", "rocket launching into space"),
        ("🏰 Fantasy Castle", "magical castle on a mountain"),
        ("🌌 Galaxy", "beautiful spiral galaxy with stars"),
        ("🌸 Cherry Blossom", "cherry blossom trees in spring"),
        ("🏙️ Cyber City", "cyberpunk city with neon lights"),
        ("🧙 Wizard Tower", "wizard tower with magic aura"),
        ("🐉 Dragon", "dragon flying over mountains"),
        ("🌊 Ocean Wave", "huge wave with dramatic lighting"),
        ("🌲 Forest", "mysterious forest with light rays"),
        ("🏔️ Mountain", "snowy mountain with clouds"),
    ]
    for idea_text, idea_prompt in ideas[:8]:
        builder.row(InlineKeyboardButton(
            text=idea_text,
            callback_data=f"idea_{idea_prompt}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_menu"))
    return builder.as_markup()

def generate_options_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Re-generate", callback_data="regenerate"),
        InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")
    )
    builder.row(
        InlineKeyboardButton(text="💡 More Ideas", callback_data="ideas"),
        InlineKeyboardButton(text="🏠 Menu", callback_data="back_menu")
    )
    return builder.as_markup()

# ==================== DRAWING FUNCTIONS ====================

def draw_sky(draw: ImageDraw.Draw, width: int, height: int, colors: List[Tuple[int, int, int]]):
    """Draw a gradient sky"""
    for y in range(height // 2):
        ratio = y / (height // 2)
        r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
        g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
        b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
        draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))

def draw_ground(draw: ImageDraw.Draw, width: int, height: int, colors: List[Tuple[int, int, int]]):
    """Draw ground/landscape"""
    ground_y = height // 2 + random.randint(-20, 20)
    for y in range(ground_y, height):
        ratio = (y - ground_y) / (height - ground_y)
        r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
        g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
        b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
        draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
    return ground_y

def draw_sun(draw: ImageDraw.Draw, width: int, height: int):
    """Draw a sun"""
    sun_x = random.randint(width // 4, width * 3 // 4)
    sun_y = random.randint(height // 6, height // 3)
    sun_radius = random.randint(30, 60)
    
    # Glow
    for i in range(5, 0, -1):
        r = sun_radius + i * 15
        alpha = int(50 / i)
        draw.ellipse([sun_x - r, sun_y - r, sun_x + r, sun_y + r], 
                    fill=(255, 200, 50, alpha))
    
    # Main sun
    draw.ellipse([sun_x - sun_radius, sun_y - sun_radius, 
                  sun_x + sun_radius, sun_y + sun_radius], 
                fill=(255, 220, 80))
    draw.ellipse([sun_x - sun_radius//2, sun_y - sun_radius//2, 
                  sun_x + sun_radius//2, sun_y + sun_radius//2], 
                fill=(255, 240, 150))
    return sun_x, sun_y

def draw_mountain(draw: ImageDraw.Draw, width: int, height: int, ground_y: int, 
                  x: int, size: float, color: Tuple[int, int, int]):
    """Draw a mountain"""
    points = [
        (x - int(80 * size), ground_y),
        (x, int(ground_y - 120 * size)),
        (x + int(80 * size), ground_y)
    ]
    draw.polygon(points, fill=color)
    
    # Snow cap
    if size > 1.2:
        snow_points = [
            (x - int(20 * size), int(ground_y - 90 * size)),
            (x, int(ground_y - 120 * size)),
            (x + int(20 * size), int(ground_y - 90 * size))
        ]
        draw.polygon(snow_points, fill=(255, 255, 255, 200))

def draw_tree(draw: ImageDraw.Draw, x: int, y: int, height: int, 
              color: Tuple[int, int, int], style: str = "realistic"):
    """Draw a tree"""
    # Trunk
    trunk_height = height // 3
    draw.rectangle([x - 3, y - trunk_height, x + 3, y], fill=(80, 50, 20))
    
    # Canopy
    if style == "anime":
        # Round anime-style tree
        for i in range(3):
            radius = height // 3 - i * 10
            draw.ellipse([x - radius, y - trunk_height - i * 20 - radius, 
                          x + radius, y - trunk_height - i * 20 + radius], 
                        fill=(color[0] - i * 20, color[1] - i * 10, color[2] - i * 10))
    else:
        # Natural tree
        points = [
            (x, y - height),
            (x - height//2, y - trunk_height),
            (x + height//2, y - trunk_height),
            (x, y - trunk_height + 10)
        ]
        draw.polygon(points, fill=color)

def draw_cloud(draw: ImageDraw.Draw, x: int, y: int, size: int):
    """Draw a cloud"""
    draw.ellipse([x, y, x + size, y + size//2], fill=(255, 255, 255, 180))
    draw.ellipse([x - size//3, y + 5, x + size//3, y + size//2 + 5], 
                fill=(255, 255, 255, 150))
    draw.ellipse([x + size//3, y + 5, x + size, y + size//2 + 5], 
                fill=(255, 255, 255, 150))

def draw_stars(draw: ImageDraw.Draw, width: int, height: int, count: int = 50):
    """Draw stars in the sky"""
    for _ in range(count):
        x = random.randint(0, width)
        y = random.randint(0, height // 2)
        size = random.randint(1, 3)
        brightness = random.randint(150, 255)
        draw.ellipse([x, y, x + size, y + size], 
                    fill=(brightness, brightness, brightness, 200))

def draw_moon(draw: ImageDraw.Draw, width: int, height: int):
    """Draw a moon"""
    moon_x = random.randint(width // 4, width * 3 // 4)
    moon_y = random.randint(height // 8, height // 3)
    moon_r = random.randint(25, 50)
    
    # Glow
    for i in range(3, 0, -1):
        r = moon_r + i * 20
        draw.ellipse([moon_x - r, moon_y - r, moon_x + r, moon_y + r], 
                    fill=(255, 255, 200, 20))
    
    draw.ellipse([moon_x - moon_r, moon_y - moon_r, 
                  moon_x + moon_r, moon_y + moon_r], 
                fill=(240, 240, 220))
    draw.ellipse([moon_x - moon_r//2, moon_y - moon_r//2, 
                  moon_x + moon_r//2, moon_y + moon_r//2], 
                fill=(255, 255, 240))

def draw_water(draw: ImageDraw.Draw, width: int, height: int, ground_y: int):
    """Draw water/ocean"""
    for y in range(ground_y, height):
        ratio = (y - ground_y) / (height - ground_y)
        r = int(20 + (50 * ratio))
        g = int(80 + (100 * ratio))
        b = int(150 + (80 * ratio))
        draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
    
    # Waves
    for i in range(3):
        y = ground_y + 20 + i * 30
        points = []
        for x in range(0, width, 3):
            y_offset = int(10 * math.sin(x / 30 + i * 2))
            points.append((x, y + y_offset))
        draw.line(points, fill=(255, 255, 255, 100), width=2)

def draw_flowers(draw: ImageDraw.Draw, width: int, height: int, ground_y: int, count: int = 15):
    """Draw flowers on the ground"""
    colors = [(255, 100, 150), (255, 200, 100), (200, 100, 255), 
              (255, 100, 100), (255, 150, 200)]
    for _ in range(count):
        x = random.randint(20, width - 20)
        y = random.randint(ground_y + 20, height - 20)
        size = random.randint(5, 10)
        color = random.choice(colors)
        draw.ellipse([x - size, y - size, x + size, y + size], fill=color)
        draw.ellipse([x - size//2, y - size - size//2, x + size//2, y - size + size//2], 
                    fill=color)

def draw_birds(draw: ImageDraw.Draw, width: int, height: int, count: int = 3):
    """Draw birds in the sky"""
    for _ in range(count):
        x = random.randint(50, width - 50)
        y = random.randint(30, height // 3)
        size = random.randint(8, 15)
        # V shape
        points = [(x, y), (x - size, y - size//2), (x - size//2, y - size//4), 
                  (x, y), (x + size//2, y - size//4), (x + size, y - size//2)]
        draw.line(points, fill=(30, 30, 30), width=2)

def draw_castle(draw: ImageDraw.Draw, x: int, y: int, size: int):
    """Draw a castle"""
    # Base
    draw.rectangle([x - size, y - size//2, x + size, y], fill=(120, 110, 100))
    # Towers
    for i in [-size//2, size//2]:
        draw.rectangle([x + i - 15, y - size, x + i + 15, y - size//2], 
                      fill=(130, 120, 110))
        # Tower top
        draw.polygon([(x + i - 20, y - size), (x + i, y - size - 30), 
                      (x + i + 20, y - size)], fill=(150, 140, 130))
        # Windows
        draw.rectangle([x + i - 5, y - size + 20, x + i + 5, y - size + 40], 
                      fill=(255, 200, 100))
    # Gate
    draw.rectangle([x - 20, y - 30, x + 20, y], fill=(50, 40, 30))
    draw.arc([x - 20, y - 30, x + 20, y], 180, 0, fill=(50, 40, 30))

def draw_dragon(draw: ImageDraw.Draw, width: int, height: int):
    """Draw a simple dragon"""
    cx = width // 2
    cy = height // 2 - 50
    
    # Body
    points = [(cx - 80, cy + 40), (cx, cy - 60), (cx + 80, cy + 40), 
              (cx + 40, cy + 60), (cx - 40, cy + 60)]
    draw.polygon(points, fill=(50, 150, 50))
    
    # Wings
    wing_points = [(cx - 60, cy - 20), (cx - 120, cy - 100), 
                   (cx - 80, cy - 60), (cx - 40, cy - 40)]
    draw.polygon(wing_points, fill=(80, 200, 80, 150))
    wing_points2 = [(cx + 60, cy - 20), (cx + 120, cy - 100), 
                    (cx + 80, cy - 60), (cx + 40, cy - 40)]
    draw.polygon(wing_points2, fill=(80, 200, 80, 150))
    
    # Head
    draw.ellipse([cx - 30, cy - 80, cx + 30, cy - 30], fill=(50, 150, 50))
    # Eyes
    draw.ellipse([cx - 20, cy - 70, cx - 10, cy - 60], fill=(255, 200, 50))
    draw.ellipse([cx + 10, cy - 70, cx + 20, cy - 60], fill=(255, 200, 50))
    # Fire
    fire_points = [(cx - 10, cy - 30), (cx - 30, cy + 20), 
                   (cx, cy + 10), (cx + 30, cy + 20), (cx + 10, cy - 30)]
    draw.polygon(fire_points, fill=(255, 100, 0, 150))
    draw.polygon([(cx - 5, cy - 20), (cx - 15, cy), 
                  (cx, cy - 5), (cx + 15, cy), (cx + 5, cy - 20)], 
                fill=(255, 200, 0, 150))

def draw_rocket(draw: ImageDraw.Draw, width: int, height: int):
    """Draw a rocket launching"""
    cx = width // 2
    cy = height // 2
    
    # Body
    draw.rectangle([cx - 20, cy - 60, cx + 20, cy + 20], fill=(200, 200, 220))
    # Nose cone
    draw.polygon([(cx - 20, cy - 60), (cx, cy - 100), (cx + 20, cy - 60)], 
                fill=(255, 100, 100))
    # Fins
    draw.polygon([(cx - 40, cy + 10), (cx - 20, cy), (cx - 20, cy + 20)], 
                fill=(200, 200, 220))
    draw.polygon([(cx + 40, cy + 10), (cx + 20, cy), (cx + 20, cy + 20)], 
                fill=(200, 200, 220))
    # Window
    draw.ellipse([cx - 12, cy - 30, cx + 12, cy - 10], fill=(100, 200, 255))
    # Flames
    flame_points = [(cx - 15, cy + 20), (cx, cy + 60), (cx + 15, cy + 20)]
    draw.polygon(flame_points, fill=(255, 150, 0, 200))
    draw.polygon([(cx - 8, cy + 25), (cx, cy + 50), (cx + 8, cy + 25)], 
                fill=(255, 255, 100, 200))

def draw_tower(draw: ImageDraw.Draw, width: int, height: int):
    """Draw a wizard tower"""
    cx = width // 2
    cy = height // 2
    
    # Tower body
    draw.rectangle([cx - 40, cy - 60, cx + 40, cy + 40], fill=(100, 80, 60))
    # Tower top
    draw.polygon([(cx - 50, cy - 60), (cx, cy - 120), (cx + 50, cy - 60)], 
                fill=(120, 100, 80))
    # Windows
    draw.ellipse([cx - 15, cy - 30, cx + 15, cy], fill=(255, 200, 50))
    # Magic aura
    for i in range(3, 0, -1):
        r = 60 + i * 20
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], 
                    fill=(150, 50, 200, 20))
    # Star on top
    star_points = [
        (cx, cy - 140), (cx + 10, cy - 125), (cx + 25, cy - 125),
        (cx + 15, cy - 115), (cx + 20, cy - 100), (cx, cy - 110),
        (cx - 20, cy - 100), (cx - 15, cy - 115), (cx - 25, cy - 125),
        (cx - 10, cy - 125)
    ]
    draw.polygon(star_points, fill=(255, 200, 50))

def draw_wave(draw: ImageDraw.Draw, width: int, height: int):
    """Draw a giant wave"""
    # Water background
    for y in range(height):
        r = int(10 + (30 * y / height))
        g = int(50 + (80 * y / height))
        b = int(100 + (100 * y / height))
        draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
    
    # Wave
    points = []
    for x in range(width):
        y = height//2 + int(100 * math.sin(x / 20 + 1.5))
        points.append((x, y))
    
    # Fill wave
    wave_points = points + [(width, height), (0, height)]
    draw.polygon(wave_points, fill=(30, 100, 200, 180))
    
    # Wave curve
    draw.line(points, fill=(255, 255, 255, 150), width=3)
    
    # Wave curl
    curl_x = width // 2 + 80
    curl_y = height//2 + 100
    draw.arc([curl_x - 50, curl_y - 50, curl_x + 50, curl_y + 50], 
             0, 180, fill=(255, 255, 255, 150), width=3)
    
    # Spray
    for _ in range(20):
        x = curl_x + random.randint(-30, 30)
        y = curl_y - random.randint(10, 40)
        size = random.randint(2, 5)
        draw.ellipse([x, y, x + size, y + size], fill=(255, 255, 255, 150))

def draw_forest(draw: ImageDraw.Draw, width: int, height: int):
    """Draw a magical forest"""
    # Ground
    ground_y = height * 2 // 3
    for y in range(ground_y, height):
        r = int(30 + (20 * (y - ground_y) / (height - ground_y)))
        g = int(80 + (40 * (y - ground_y) / (height - ground_y)))
        b = int(30 + (20 * (y - ground_y) / (height - ground_y)))
        draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
    
    # Trees
    for i in range(8):
        x = random.randint(30, width - 30)
        tree_height = random.randint(60, 120)
        draw_tree(draw, x, ground_y, tree_height, 
                  (random.randint(40, 80), random.randint(120, 180), 
                   random.randint(30, 60)))
    
    # Light rays
    for x in range(0, width, 20):
        y_start = random.randint(0, 50)
        draw.line([(x, y_start), (x + random.randint(-10, 10), ground_y)], 
                 fill=(255, 255, 200, 30), width=3)
    
    # Magic particles
    for _ in range(30):
        x = random.randint(0, width)
        y = random.randint(0, ground_y)
        size = random.randint(2, 4)
        draw.ellipse([x, y, x + size, y + size], 
                    fill=(255, 255, 200, 150))

# ==================== MAIN GENERATION ENGINE ====================

def generate_image(prompt: str, width: int, height: int, style: str) -> bytes:
    """
    Main image generation function - NO API REQUIRED!
    Draws actual scenes based on prompt
    """
    try:
        # Create image
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        
        prompt_lower = prompt.lower()
        
        # ============ SCENE SELECTION ============
        
        if any(word in prompt_lower for word in ["sunset", "sunrise", "evening", "golden", "beach"]):
            # Sunset scene
            draw_sky(draw, width, height, [(200, 80, 50), (255, 150, 80)])
            ground_y = draw_ground(draw, width, height, [(100, 80, 60), (60, 40, 30)])
            draw_sun(draw, width, height)
            
            if any(word in prompt_lower for word in ["ocean", "sea", "water", "wave"]):
                draw_water(draw, width, height, ground_y)
            else:
                for _ in range(2):
                    draw_cloud(draw, random.randint(0, width), random.randint(20, 100), 
                              random.randint(60, 120))
            
            if "palm" in prompt_lower or "tree" in prompt_lower:
                draw_tree(draw, random.randint(50, 150), ground_y, 80, (50, 150, 50))
                draw_tree(draw, random.randint(width - 150, width - 50), ground_y, 90, (50, 150, 50))
            
            draw_birds(draw, width, height)
            draw_flowers(draw, width, height, ground_y, 10)
            
        elif any(word in prompt_lower for word in ["cat", "kitten", "animal"]):
            # Cat scene
            draw_sky(draw, width, height, [(100, 150, 255), (150, 200, 255)])
            ground_y = draw_ground(draw, width, height, [(100, 180, 100), (50, 120, 50)])
            
            for _ in range(2):
                draw_cloud(draw, random.randint(0, width), random.randint(20, 80), 
                          random.randint(50, 100))
            
            draw_flowers(draw, width, height, ground_y, 12)
            
            # Draw cat
            cx = width // 2
            cy = ground_y - 40
            # Body
            draw.ellipse([cx - 35, cy - 20, cx + 35, cy + 30], fill=(200, 150, 100))
            # Head
            draw.ellipse([cx - 25, cy - 50, cx + 25, cy - 10], fill=(200, 150, 100))
            # Ears
            draw.polygon([(cx - 25, cy - 50), (cx - 15, cy - 80), (cx - 5, cy - 50)], 
                        fill=(200, 150, 100))
            draw.polygon([(cx + 5, cy - 50), (cx + 15, cy - 80), (cx + 25, cy - 50)], 
                        fill=(200, 150, 100))
            # Eyes
            draw.ellipse([cx - 15, cy - 45, cx - 8, cy - 38], fill=(100, 200, 100))
            draw.ellipse([cx + 8, cy - 45, cx + 15, cy - 38], fill=(100, 200, 100))
            draw.ellipse([cx - 12, cy - 42, cx - 11, cy - 41], fill=(0, 0, 0))
            draw.ellipse([cx + 11, cy - 42, cx + 12, cy - 41], fill=(0, 0, 0))
            # Nose
            draw.polygon([(cx, cy - 35), (cx - 3, cy - 30), (cx + 3, cy - 30)], 
                        fill=(255, 100, 100))
            # Tail
            draw.line([(cx + 35, cy + 10), (cx + 60, cy - 20)], fill=(200, 150, 100), width=5)
            
        elif any(word in prompt_lower for word in ["space", "rocket", "launch", "galaxy"]):
            # Space scene
            draw_sky(draw, width, height, [(10, 10, 40), (20, 10, 60)])
            draw_stars(draw, width, height, 80)
            draw_galaxy(draw, width, height)
            draw_rocket(draw, width, height)
            
        elif any(word in prompt_lower for word in ["castle", "fantasy", "magic", "wizard"]):
            # Fantasy scene
            draw_sky(draw, width, height, [(100, 50, 150), (200, 100, 200)])
            ground_y = draw_ground(draw, width, height, [(100, 80, 60), (50, 40, 30)])
            draw_tower(draw, width, height)
            draw_flowers(draw, width, height, ground_y, 8)
            draw_stars(draw, width, height, 30)
            
        elif any(word in prompt_lower for word in ["dragon", "fire", "fly"]):
            # Dragon scene
            draw_sky(draw, width, height, [(200, 100, 50), (255, 150, 100)])
            draw_ground(draw, width, height, [(100, 80, 60), (60, 40, 30)])
            for _ in range(2):
                draw_mountain(draw, width, height, height * 3 // 4, 
                            random.randint(100, width - 100), 
                            random.uniform(0.8, 1.5),
                            (80, 70, 60))
            draw_dragon(draw, width, height)
            
        elif any(word in prompt_lower for word in ["city", "cyberpunk", "neon", "future"]):
            # Cyberpunk city
            draw_sky(draw, width, height, [(10, 10, 30), (50, 0, 100)])
            draw_ground(draw, width, height, [(30, 30, 50), (10, 10, 30)])
            
            # Buildings
            for i in range(5):
                x = 50 + i * 100 + random.randint(-20, 20)
                bw = random.randint(30, 60)
                bh = random.randint(80, 180)
                draw.rectangle([x, height - bh - 50, x + bw, height - 50], 
                             fill=(80 + random.randint(0, 40), 
                                   80 + random.randint(0, 40), 
                                   100 + random.randint(0, 40)))
                # Windows
                for wx in range(x + 5, x + bw - 5, 15):
                    for wy in range(height - bh - 40, height - 60, 15):
                        if random.random() > 0.3:
                            color = random.choice([(255, 200, 50), (255, 100, 255), 
                                                  (100, 255, 255), (255, 255, 255)])
                            draw.rectangle([wx, wy, wx + 8, wy + 8], fill=color)
            
            # Neon signs
            for i in range(3):
                x = random.randint(50, width - 50)
                y = random.randint(100, height - 80)
                draw.rectangle([x, y, x + random.randint(40, 80), y + 15], 
                             fill=random.choice([(255, 0, 200), (0, 200, 255), (255, 200, 0)]))
            
            draw_stars(draw, width, height, 20)
            
        else:
            # Default - Beautiful landscape
            draw_sky(draw, width, height, [(135, 206, 235), (200, 230, 255)])
            ground_y = draw_ground(draw, width, height, [(100, 180, 100), (50, 120, 50)])
            
            # Mountains
            for _ in range(3):
                draw_mountain(draw, width, height, ground_y, 
                            random.randint(100, width - 100), 
                            random.uniform(0.8, 1.5),
                            (80 + random.randint(0, 40), 70 + random.randint(0, 30), 60))
            
            for _ in range(3):
                draw_cloud(draw, random.randint(0, width), random.randint(20, 80), 
                          random.randint(60, 120))
            
            for _ in range(5):
                draw_tree(draw, random.randint(30, width - 30), ground_y, 
                         random.randint(50, 100), 
                         (random.randint(40, 80), random.randint(120, 180), 
                          random.randint(30, 60)))
            
            draw_flowers(draw, width, height, ground_y, 15)
            draw_birds(draw, width, height, 5)
        
        # ============ APPLY STYLE EFFECTS ============
        
        if style == "oil":
            img = img.filter(ImageFilter.SMOOTH_MORE)
            img = img.filter(ImageFilter.EDGE_ENHANCE)
            img = ImageEnhance.Color(img).enhance(1.2)
            
        elif style == "watercolor":
            img = img.filter(ImageFilter.SMOOTH)
            img = ImageEnhance.Color(img).enhance(0.7)
            img = ImageEnhance.Brightness(img).enhance(1.1)
            
        elif style == "sketch":
            img = img.filter(ImageFilter.CONTOUR)
            img = ImageEnhance.Contrast(img).enhance(2.0)
            
        elif style == "anime":
            img = ImageEnhance.Color(img).enhance(1.4)
            img = ImageEnhance.Contrast(img).enhance(1.1)
            img = img.filter(ImageFilter.SMOOTH)
            
        elif style == "cartoon":
            img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
            img = ImageEnhance.Color(img).enhance(1.3)
            
        elif style == "cyberpunk":
            img = ImageEnhance.Color(img).enhance(1.6)
            img = ImageEnhance.Contrast(img).enhance(1.3)
            
        elif style == "fantasy":
            img = ImageEnhance.Color(img).enhance(1.3)
            img = img.filter(ImageFilter.SMOOTH)
            img = ImageEnhance.Brightness(img).enhance(1.1)
            
        # ============ CONVERT TO BYTES ============
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG', optimize=True)
        img_bytes.seek(0)
        return img_bytes.read()
        
    except Exception as e:
        logger.error(f"❌ Generation error: {str(e)}")
        return create_fallback_image(width, height, prompt)

def draw_galaxy(draw: ImageDraw.Draw, width: int, height: int):
    """Draw a spiral galaxy"""
    cx = width // 2
    cy = height // 2
    
    # Spiral arms
    for r in range(20, 200, 5):
        for angle in range(0, 360, 10):
            rad = math.radians(angle)
            spiral_r = r + 20 * math.sin(rad * 3)
            x = int(cx + spiral_r * math.cos(rad))
            y = int(cy + spiral_r * math.sin(rad) * 0.4)
            if 0 < x < width and 0 < y < height:
                brightness = int(100 + 100 * (1 - r / 250))
                draw.ellipse([x, y, x + 3, y + 3], 
                           fill=(brightness, brightness, 255, brightness // 2))

def create_fallback_image(width: int, height: int, prompt: str) -> bytes:
    """Create a simple fallback image"""
    try:
        img = Image.new('RGB', (width, height), color=(30, 30, 60))
        draw = ImageDraw.Draw(img)
        
        # Gradient
        for y in range(height):
            r = int(30 + (50 * y / height))
            g = int(30 + (40 * y / height))
            b = int(60 + (80 * y / height))
            draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
        
        # Add text
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        words = prompt.split()
        lines = []
        current = []
        for word in words[:10]:
            current.append(word)
            if len(' '.join(current)) > 25:
                if len(current) > 1:
                    current.pop()
                    lines.append(' '.join(current))
                    current = [word]
                else:
                    lines.append(' '.join(current))
                    current = []
        if current:
            lines.append(' '.join(current))
        
        y = height // 3
        for line in lines[:3]:
            bbox = draw.textbbox((0, 0), line, font=font)
            x = (width - (bbox[2] - bbox[0])) // 2
            draw.text((x, y), line, fill=(255, 255, 255), font=font)
            y += bbox[3] - bbox[1] + 10
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes.read()
        
    except:
        return b""

def format_size(bytes_count: int) -> str:
    for unit in ['B', 'KB', 'MB']:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} GB"

# ==================== COMMAND HANDLERS ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    data = get_user_data(user.id)
    
    welcome = (
        f"🎨 **Welcome to {BOT_NAME}!**\n\n"
        f"👋 Hello @{user.username or 'User'}!\n\n"
        f"I create **actual images** with scenes, objects, and landscapes\n"
        f"from your text descriptions.\n\n"
        f"✨ **NO API KEY NEEDED!**\n\n"
        f"📊 You've generated {data['settings']['total_generated']} images\n\n"
        f"🚀 Tap **Generate** below to start!"
    )
    
    await message.reply(
        welcome,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@dp.message(Command("generate"))
async def cmd_generate(message: Message, state: FSMContext):
    await state.set_state(GeneratorStates.WAITING_PROMPT)
    await message.reply(
        "🎨 **Describe what you want to see!**\n\n"
        "I'll draw a scene with:\n"
        "• 🌅 Sunsets & Beaches\n"
        "• 🐱 Animals & Nature\n"
        "• 🚀 Space & Rocket Launches\n"
        "• 🏰 Fantasy Castles & Dragons\n"
        "• 🌃 Cyberpunk Cities\n"
        "• 🏔️ Mountains & Forests\n\n"
        "📝 **Try:** \"A beautiful sunset over the ocean with palm trees\"\n\n"
        "Send /cancel to cancel.",
        parse_mode="Markdown"
    )

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    settings = data["settings"]
    
    size = IMAGE_SIZES.get(settings["size"], IMAGE_SIZES["square"])
    style = ART_STYLES.get(settings["style"], ART_STYLES["realistic"])
    
    text = (
        "⚙️ **Current Settings**\n\n"
        f"📐 Size: {size['label']}\n"
        f"🎨 Style: {style['label']}\n\n"
        "Select what to customize:"
    )
    
    await message.reply(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="📐 Change Size", callback_data="change_size"),
            InlineKeyboardButton(text="🎨 Change Style", callback_data="change_style")
        ).row(
            InlineKeyboardButton(text="🔄 Reset All", callback_data="reset_settings"),
            InlineKeyboardButton(text="🔙 Back", callback_data="back_menu")
        ).as_markup()
    )

@dp.message(Command("ideas"))
async def cmd_ideas(message: Message):
    await message.reply(
        "💡 **Get Inspired!**\n\n"
        "Click any idea below:",
        parse_mode="Markdown",
        reply_markup=ideas_keyboard()
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    settings = data["settings"]
    history = data["history"]
    
    text = (
        "📊 **Your Statistics**\n\n"
        f"🖼️ Total images: {settings['total_generated']}\n"
        f"📐 Size: {IMAGE_SIZES.get(settings['size'], IMAGE_SIZES['square'])['label']}\n"
        f"🎨 Style: {ART_STYLES.get(settings['style'], ART_STYLES['realistic'])['label']}\n"
        f"📅 Last generated: {settings['last_generated'] or 'Never'}\n\n"
        f"📈 Generations: {len(history)}"
    )
    
    await message.reply(text, parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "❓ **Help & Support**\n\n"
        "🤖 **How to use:**\n"
        "1. Send /generate or tap Generate\n"
        "2. Type your image description\n"
        "3. Watch your scene come to life!\n\n"
        "🎯 **What I can draw:**\n"
        "• Sunsets, Beaches, Oceans\n"
        "• Cats, Animals, Nature\n"
        "• Space, Rockets, Galaxies\n"
        "• Castles, Dragons, Fantasy\n"
        "• Cyberpunk, Futuristic Cities\n"
        "• Mountains, Forests, Flowers\n\n"
        "📌 **Commands:**\n"
        "/start - Main menu\n"
        "/generate - Generate image\n"
        "/settings - Change preferences\n"
        "/ideas - Get inspiration\n"
        "/stats - View statistics\n"
        "/help - This help\n"
        "/about - About the bot\n"
        "/cancel - Cancel operation"
    )
    await message.reply(help_text, parse_mode="Markdown")

@dp.message(Command("about"))
async def cmd_about(message: Message):
    about = (
        f"🤖 **{BOT_NAME}**\n\n"
        f"📦 Version: {BOT_VERSION}\n"
        f"👤 Username: @{BOT_USERNAME}\n\n"
        "🎨 **Professional Image Generator**\n"
        "Creates actual scenes, objects, and landscapes\n"
        "**NO API KEYS NEEDED!**\n\n"
        "✨ **What I draw:**\n"
        "• Landscapes & Nature\n"
        "• Animals & Creatures\n"
        "• Space & Sci-Fi\n"
        "• Fantasy & Magic\n"
        "• Cyberpunk & Futuristic\n"
        "• And much more!\n\n"
        "🔒 **Privacy:**\n"
        "No data is stored permanently.\n\n"
        "⭐ Made with ❤️ for Telegram"
    )
    await message.reply(about, parse_mode="Markdown")

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.reply(
        "✅ **Cancelled**\n\n"
        "Operation cancelled successfully.",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@dp.message(GeneratorStates.WAITING_PROMPT)
async def handle_prompt(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/"):
        return
    
    user_id = message.from_user.id
    prompt = message.text
    
    if not prompt:
        await message.reply("❌ Please send a text description.")
        return
    
    settings = get_user_data(user_id)["settings"]
    size = IMAGE_SIZES.get(settings["size"], IMAGE_SIZES["square"])
    style = ART_STYLES.get(settings["style"], ART_STYLES["realistic"])
    
    processing = await message.reply(
        f"🎨 **Creating your scene...**\n\n"
        f"📝 Prompt: {prompt[:150]}{'...' if len(prompt) > 150 else ''}\n"
        f"📐 Size: {size['label']}\n"
        f"🎨 Style: {style['label']}\n\n"
        f"⏳ Please wait...",
        parse_mode="Markdown"
    )
    
    try:
        image_data = generate_image(
            prompt=prompt,
            width=size["width"],
            height=size["height"],
            style=settings["style"]
        )
        
        if image_data and len(image_data) > 1000:
            data = get_user_data(user_id)
            data["settings"]["total_generated"] += 1
            data["settings"]["last_generated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            data["history"].append({
                "prompt": prompt,
                "success": True,
                "timestamp": datetime.now().isoformat()
            })
            
            input_file = BufferedInputFile(image_data, filename="generated_image.png")
            
            await message.reply_photo(
                photo=input_file,
                caption=(
                    f"🎨 **Scene Created!**\n\n"
                    f"📝 Prompt: {prompt[:200]}{'...' if len(prompt) > 200 else ''}\n"
                    f"📐 Size: {size['label']}\n"
                    f"🎨 Style: {style['label']}\n"
                    f"📊 Size: {format_size(len(image_data))}\n\n"
                    f"🔄 Send a new prompt to create another!"
                ),
                parse_mode="Markdown",
                reply_markup=generate_options_keyboard()
            )
            
            await processing.delete()
            
        else:
            await message.reply(
                "⚠️ **Generation Failed**\n\n"
                "Please try again with a different prompt.",
                parse_mode="Markdown"
            )
            await processing.delete()
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        await message.reply("❌ Something went wrong. Please try again.")
        await processing.delete()
    
    await state.clear()

# ==================== CALLBACK HANDLERS ====================

@dp.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    user_id = callback.from_user.id
    data = get_user_data(user_id)
    settings = data["settings"]
    action = callback.data
    
    if action == "back_menu":
        await callback.message.edit_text(
            "🎨 **Main Menu**\n\n"
            "What would you like to do?",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
        return
        
    elif action == "back_settings":
        await cmd_settings(callback.message)
        return
    
    elif action == "generate":
        await cmd_generate(callback.message, state)
        return
        
    elif action == "settings":
        await cmd_settings(callback.message)
        return
        
    elif action == "ideas":
        await callback.message.edit_text(
            "💡 **Get Inspired!**\n\n"
            "Click any idea below:",
            parse_mode="Markdown",
            reply_markup=ideas_keyboard()
        )
        return
        
    elif action == "stats":
        await cmd_stats(callback.message)
        return
        
    elif action == "help":
        await cmd_help(callback.message)
        return
    
    elif action == "change_size":
        await callback.message.edit_text(
            "📐 **Select Image Size**\n\n"
            "Choose your preferred size:",
            parse_mode="Markdown",
            reply_markup=size_keyboard()
        )
        return
        
    elif action == "change_style":
        await callback.message.edit_text(
            "🎨 **Select Art Style**\n\n"
            "Choose your preferred style:",
            parse_mode="Markdown",
            reply_markup=style_keyboard()
        )
        return
        
    elif action == "reset_settings":
        settings["size"] = "square"
        settings["style"] = "realistic"
        await callback.message.edit_text(
            "✅ **Settings Reset!**\n\n"
            "All settings have been reset to default.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🔙 Back", callback_data="back_settings")
            ).as_markup()
        )
        return
    
    elif action.startswith("size_"):
        size_id = action.replace("size_", "")
        if size_id in IMAGE_SIZES:
            settings["size"] = size_id
            size = IMAGE_SIZES[size_id]
            await callback.message.edit_text(
                f"✅ **Size Updated!**\n\n"
                f"New size: {size['label']}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text="🔙 Back", callback_data="back_settings")
                ).as_markup()
            )
        return
    
    elif action.startswith("style_"):
        style_id = action.replace("style_", "")
        if style_id in ART_STYLES:
            settings["style"] = style_id
            style = ART_STYLES[style_id]
            await callback.message.edit_text(
                f"✅ **Style Updated!**\n\n"
                f"New style: {style['label']}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text="🔙 Back", callback_data="back_settings")
                ).as_markup()
            )
        return
    
    elif action.startswith("idea_"):
        prompt = action.replace("idea_", "")
        if prompt:
            await callback.message.edit_text(
                f"🎨 **Creating your scene...**\n\n"
                f"📝 Prompt: {prompt}\n"
                f"⏳ Please wait...",
                parse_mode="Markdown"
            )
            
            size = IMAGE_SIZES.get(settings["size"], IMAGE_SIZES["square"])
            style = ART_STYLES.get(settings["style"], ART_STYLES["realistic"])
            
            image_data = generate_image(
                prompt=prompt,
                width=size["width"],
                height=size["height"],
                style=settings["style"]
            )
            
            if image_data and len(image_data) > 1000:
                data["settings"]["total_generated"] += 1
                input_file = BufferedInputFile(image_data, filename="generated_image.png")
                await callback.message.reply_photo(
                    photo=input_file,
                    caption=(
                        f"🎨 **Scene Created!**\n\n"
                        f"📝 Prompt: {prompt}\n"
                        f"📐 Size: {size['label']}\n"
                        f"🎨 Style: {style['label']}"
                    ),
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardBuilder().row(
                        InlineKeyboardButton(text="💡 More Ideas", callback_data="ideas"),
                        InlineKeyboardButton(text="🎨 Generate", callback_data="generate")
                    ).row(
                        InlineKeyboardButton(text="🏠 Menu", callback_data="back_menu")
                    ).as_markup()
                )
            else:
                await callback.message.reply("⚠️ Failed to create image. Please try again.")
        return
    
    elif action == "regenerate":
        if data["history"]:
            last = data["history"][-1]
            if last.get("success") and last.get("prompt"):
                await cmd_generate(callback.message, state)
        return

@dp.message()
async def handle_other(message: Message):
    await message.reply(
        "❓ I don't understand that.\n\n"
        "Use /start to see the menu or /help for assistance.",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="🏠 Menu", callback_data="back_menu")
        ).as_markup()
    )

# ==================== MAIN ====================

async def main():
    try:
        logger.info("=" * 60)
        logger.info(f"🎨 {BOT_NAME} v{BOT_VERSION}")
        logger.info(f"🤖 Username: @{BOT_USERNAME}")
        logger.info(f"📦 Mode: PROFESSIONAL - NO API KEY NEEDED")
        logger.info("=" * 60)
        
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Fatal: {str(e)}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"💥 Fatal: {str(e)}")
