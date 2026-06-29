"""
🎨 Pixel Craft Bot - AI Image Generator
Creates images using Python's PIL library - NO API KEY NEEDED!
Generates beautiful images with your text prompts
"""

import os
import io
import logging
import random
import textwrap
from datetime import datetime
from typing import Dict, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

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
BOT_VERSION = "2.0.0"

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ==================== CONSTANTS ====================

# Color themes for different moods
COLOR_THEMES = {
    "sunset": [(255, 100, 50), (255, 200, 100), (200, 50, 80)],
    "ocean": [(0, 50, 100), (50, 150, 200), (100, 200, 255)],
    "forest": [(20, 80, 20), (50, 150, 50), (100, 200, 100)],
    "cyberpunk": [(100, 0, 150), (255, 0, 200), (0, 200, 255)],
    "warm": [(255, 200, 100), (255, 150, 50), (200, 100, 50)],
    "cool": [(100, 150, 255), (50, 100, 200), (0, 50, 150)],
    "pastel": [(255, 200, 220), (200, 220, 255), (220, 255, 200)],
    "neon": [(255, 0, 100), (0, 255, 200), (200, 0, 255)],
    "nature": [(50, 150, 50), (100, 200, 100), (150, 100, 50)],
    "space": [(10, 10, 50), (50, 0, 100), (100, 0, 200)],
}

# Image sizes
IMAGE_SIZES = {
    "square": {"width": 512, "height": 512, "label": "🟦 Square (512x512)"},
    "portrait": {"width": 384, "height": 512, "label": "📱 Portrait (384x512)"},
    "landscape": {"width": 512, "height": 384, "label": "🖥️ Landscape (512x384)"},
    "wide": {"width": 768, "height": 512, "label": "🖼️ Wide (768x512)"},
    "hd": {"width": 1024, "height": 768, "label": "📷 HD (1024x768)"},
}

# Art styles
ART_STYLES = {
    "realistic": {"label": "📷 Realistic", "style": "realistic"},
    "anime": {"label": "🎨 Anime", "style": "anime"},
    "cartoon": {"label": "✏️ Cartoon", "style": "cartoon"},
    "oil": {"label": "🖌️ Oil Painting", "style": "oil"},
    "watercolor": {"label": "💧 Watercolor", "style": "watercolor"},
    "sketch": {"label": "✒️ Sketch", "style": "sketch"},
    "3d": {"label": "🎮 3D Render", "style": "3d"},
    "cyberpunk": {"label": "💜 Cyberpunk", "style": "cyberpunk"},
    "fantasy": {"label": "🧙 Fantasy", "style": "fantasy"},
    "minimalist": {"label": "⬜ Minimalist", "style": "minimalist"},
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
        ("🌅 Sunset", "golden sunset over ocean with dramatic clouds"),
        ("🐱 Cat", "cute fluffy cat in a garden with flowers"),
        ("🚀 Space", "futuristic rocket launching into space"),
        ("🏰 Castle", "medieval castle on a mountain at sunrise"),
        ("🌌 Galaxy", "colorful spiral galaxy with stars and nebula"),
        ("🌸 Garden", "beautiful japanese garden with cherry blossoms"),
        ("🏙️ Cyberpunk", "cyberpunk city with neon lights at night"),
        ("🧙 Wizard", "ancient wizard casting a magic spell"),
        ("🐉 Dragon", "majestic dragon flying over mountains"),
        ("🌊 Wave", "massive ocean wave with dramatic lighting"),
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

# ==================== IMAGE GENERATION ENGINE ====================

def generate_image_from_prompt(
    prompt: str,
    width: int = 512,
    height: int = 512,
    style: str = "realistic"
) -> bytes:
    """
    Generate a beautiful image using Python's PIL library
    NO API KEY NEEDED! Creates images based on the prompt text
    """
    try:
        # Create base image
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        
        # Select color theme based on prompt content
        theme = select_color_theme(prompt)
        colors = COLOR_THEMES.get(theme, COLOR_THEMES["warm"])
        
        # Create gradient background
        for y in range(height):
            # Interpolate between colors
            ratio = y / height
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
            draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
        
        # Add decorative elements based on prompt
        add_decorative_elements(img, draw, width, height, prompt)
        
        # Add text from prompt
        add_text_to_image(img, draw, width, height, prompt)
        
        # Apply style effects
        img = apply_style_effects(img, style)
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG', optimize=True)
        img_bytes.seek(0)
        return img_bytes.read()
        
    except Exception as e:
        logger.error(f"❌ Generation error: {str(e)}")
        return create_fallback_image(width, height, prompt)

def select_color_theme(prompt: str) -> str:
    """Select color theme based on prompt content"""
    prompt_lower = prompt.lower()
    
    themes = {
        "sunset": ["sunset", "golden", "orange", "red", "warm", "evening"],
        "ocean": ["ocean", "sea", "water", "wave", "blue", "beach"],
        "forest": ["forest", "tree", "green", "nature", "wood", "leaf"],
        "cyberpunk": ["cyberpunk", "neon", "future", "city", "futuristic"],
        "space": ["space", "star", "galaxy", "cosmic", "universe"],
        "warm": ["warm", "cozy", "fire", "sun", "gold"],
        "cool": ["cool", "ice", "snow", "winter", "cold"],
        "pastel": ["pastel", "soft", "gentle", "delicate", "cute"],
        "neon": ["neon", "vibrant", "bright", "glow"],
    }
    
    for theme, keywords in themes.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                return theme
    
    return "warm"  # Default theme

def add_decorative_elements(img: Image.Image, draw: ImageDraw.Draw, width: int, height: int, prompt: str):
    """Add decorative elements based on prompt content"""
    prompt_lower = prompt.lower()
    random.seed(hash(prompt) % 2**32)
    
    # Add stars or sparkles
    if any(word in prompt_lower for word in ["star", "space", "night", "galaxy", "magic", "sparkle"]):
        for _ in range(30):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(2, 5)
            brightness = random.randint(150, 255)
            draw.ellipse([x, y, x + size, y + size], 
                        fill=(brightness, brightness, brightness))
    
    # Add flowers for garden/nature prompts
    if any(word in prompt_lower for word in ["flower", "garden", "nature", "spring", "bloom"]):
        for _ in range(8):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(10, 20)
            colors = [(255, 100, 150), (255, 200, 100), (200, 100, 255), (255, 100, 100)]
            color = random.choice(colors)
            # Draw flower (circle with petals)
            draw.ellipse([x - size, y - size, x + size, y + size], 
                        fill=color, outline=(255, 255, 255))
    
    # Add water waves for ocean prompts
    if any(word in prompt_lower for word in ["ocean", "wave", "water", "sea"]):
        for i in range(3):
            y = height // 3 + i * 80
            points = []
            for x in range(0, width, 5):
                y_offset = int(15 * ((x / width) * 3.14 * 2) + i * 20)
                points.append((x, y + y_offset))
            draw.line(points, fill=(255, 255, 255, 100), width=3)
    
    # Add clouds for sky prompts
    if any(word in prompt_lower for word in ["sky", "cloud", "sunset", "sunrise"]):
        for _ in range(5):
            x = random.randint(0, width)
            y = random.randint(0, height // 2)
            size = random.randint(30, 80)
            draw.ellipse([x, y, x + size, y + size//2], 
                        fill=(255, 255, 255, 100))
            draw.ellipse([x - size//3, y + 10, x + size//2, y + size//2 + 10], 
                        fill=(255, 255, 255, 80))

def add_text_to_image(img: Image.Image, draw: ImageDraw.Draw, width: int, height: int, prompt: str):
    """Add styled text to the image"""
    try:
        # Try to use a nicer font
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "arial.ttf"
        ]
        
        font = None
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, 32)
                break
            except:
                continue
        
        if font is None:
            font = ImageFont.load_default()
        
        # Wrap text
        words = prompt.split()
        lines = []
        current_line = []
        max_width = int(width * 0.85)
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] > max_width:
                    if len(current_line) > 1:
                        current_line.pop()
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(test_line)
                        current_line = []
            except:
                lines.append(test_line)
                current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Limit to 6 lines
        lines = lines[:6]
        
        # Calculate total height
        total_height = 0
        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                total_height += bbox[3] - bbox[1] + 10
            except:
                total_height += 50
        
        # Draw text with shadow effect
        y_offset = (height - total_height) // 2
        for line in lines:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                x = (width - (bbox[2] - bbox[0])) // 2
                
                # Shadow
                draw.text((x + 2, y_offset + 2), line, fill=(0, 0, 0, 150), font=font)
                # Main text
                draw.text((x, y_offset), line, fill=(255, 255, 255), font=font)
                
                y_offset += (bbox[3] - bbox[1]) + 10
            except:
                pass
        
        # Add small footer
        try:
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            footer = "🎨 Pixel Craft Bot"
            bbox = draw.textbbox((0, 0), footer, font=small_font)
            x = (width - (bbox[2] - bbox[0])) // 2
            draw.text((x, height - 30), footer, fill=(255, 255, 255, 150), font=small_font)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Text error: {str(e)}")

def apply_style_effects(img: Image.Image, style: str) -> Image.Image:
    """Apply artistic style effects to the image"""
    try:
        if style == "oil":
            img = img.filter(ImageFilter.SMOOTH_MORE)
            img = img.filter(ImageFilter.EDGE_ENHANCE)
        elif style == "sketch":
            img = img.filter(ImageFilter.CONTOUR)
            img = ImageEnhance.Contrast(img).enhance(2.0)
        elif style == "watercolor":
            img = img.filter(ImageFilter.SMOOTH)
            img = ImageEnhance.Color(img).enhance(0.8)
        elif style == "cartoon":
            img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
            img = ImageEnhance.Color(img).enhance(1.2)
        elif style == "cyberpunk":
            img = ImageEnhance.Color(img).enhance(1.5)
            img = ImageEnhance.Contrast(img).enhance(1.3)
        elif style == "minimalist":
            img = ImageEnhance.Color(img).enhance(0.5)
            img = ImageEnhance.Contrast(img).enhance(0.8)
        elif style == "3d":
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = ImageEnhance.Sharpness(img).enhance(1.5)
        elif style == "fantasy":
            img = ImageEnhance.Color(img).enhance(1.3)
            img = img.filter(ImageFilter.SMOOTH)
        elif style == "realistic":
            img = ImageEnhance.Sharpness(img).enhance(1.1)
        elif style == "anime":
            img = ImageEnhance.Color(img).enhance(1.4)
            img = ImageEnhance.Contrast(img).enhance(1.1)
    except Exception as e:
        logger.error(f"Style error: {str(e)}")
    
    return img

def create_fallback_image(width: int, height: int, prompt: str) -> bytes:
    """Create a simple fallback image if main generation fails"""
    try:
        img = Image.new('RGB', (width, height), color=(50, 50, 100))
        draw = ImageDraw.Draw(img)
        
        # Simple gradient
        for y in range(height):
            r = int(50 + (100 * y / height))
            g = int(50 + (50 * y / height))
            b = int(100 + (100 * y / height))
            draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
        
        # Add text
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Wrap text
        words = prompt.split()
        lines = []
        current_line = []
        for word in words[:20]:
            current_line.append(word)
            if len(' '.join(current_line)) > 30:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(' '.join(current_line))
                    current_line = []
        if current_line:
            lines.append(' '.join(current_line))
        
        y_offset = height // 3
        for line in lines[:4]:
            bbox = draw.textbbox((0, 0), line, font=font)
            x = (width - (bbox[2] - bbox[0])) // 2
            draw.text((x, y_offset), line, fill=(255, 255, 255), font=font)
            y_offset += bbox[3] - bbox[1] + 10
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes.read()
        
    except Exception as e:
        logger.error(f"Fallback error: {str(e)}")
        return b""

def format_size(bytes_count: int) -> str:
    """Format bytes to human readable"""
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
        f"I create unique images from your text descriptions.\n"
        f"**NO API KEY NEEDED** - Everything runs locally!\n\n"
        f"📊 You've generated {data['settings']['total_generated']} images\n\n"
        f"✨ **Features:**\n"
        f"• 🎨 10+ Art Styles\n"
        f"• 📐 5 Image Sizes\n"
        f"• 💡 Ready-to-use Ideas\n"
        f"• ⚙️ Customizable Settings\n\n"
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
        "🎨 **Describe your image!**\n\n"
        "Be creative! I'll generate a unique image based on your words.\n\n"
        "📝 **Examples:**\n"
        "• \"A beautiful sunset over the ocean with golden clouds\"\n"
        "• \"A cute cat sitting in a magical forest with butterflies\"\n"
        "• \"A futuristic cyberpunk city with neon lights and flying cars\"\n\n"
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
        "3. Watch your image come to life!\n\n"
        "🎯 **Tips:**\n"
        "• Be creative with your descriptions\n"
        "• Mention colors, mood, and elements\n"
        "• Use 3-15 words for best results\n\n"
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
        "🎨 **Image Generation**\n"
        "Creates unique images from your text prompts.\n"
        "**NO API KEYS NEEDED!**\n\n"
        "✨ **Features:**\n"
        "• 10+ Art Styles\n"
        "• 5 Image Sizes\n"
        "• 100% Free\n"
        "• No API Required\n"
        "• Usage Statistics\n\n"
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
    
    # Get settings
    data = get_user_data(user_id)
    settings = data["settings"]
    
    size = IMAGE_SIZES.get(settings["size"], IMAGE_SIZES["square"])
    style = ART_STYLES.get(settings["style"], ART_STYLES["realistic"])
    
    # Send processing message
    processing = await message.reply(
        f"🎨 **Creating your image...**\n\n"
        f"📝 Prompt: {prompt[:150]}{'...' if len(prompt) > 150 else ''}\n"
        f"📐 Size: {size['label']}\n"
        f"🎨 Style: {style['label']}\n\n"
        f"⏳ Please wait...",
        parse_mode="Markdown"
    )
    
    try:
        # Generate image (NO API REQUIRED!)
        image_data = generate_image_from_prompt(
            prompt=prompt,
            width=size["width"],
            height=size["height"],
            style=settings["style"]
        )
        
        if image_data and len(image_data) > 1000:
            # Update stats
            data["settings"]["total_generated"] += 1
            data["settings"]["last_generated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            data["history"].append({
                "prompt": prompt,
                "success": True,
                "timestamp": datetime.now().isoformat()
            })
            
            # Send image
            input_file = BufferedInputFile(image_data, filename="generated_image.png")
            
            await message.reply_photo(
                photo=input_file,
                caption=(
                    f"🎨 **Image Created!**\n\n"
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
                "I couldn't create an image right now.\n\n"
                "💡 **Tips:**\n"
                "• Try a different prompt\n"
                "• Use simpler words\n"
                "• Try again in a moment",
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
    
    # Navigation
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
    
    # Main Actions
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
    
    # Settings Changes
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
        data["settings"]["size"] = "square"
        data["settings"]["style"] = "realistic"
        await callback.message.edit_text(
            "✅ **Settings Reset!**\n\n"
            "All settings have been reset to default.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🔙 Back", callback_data="back_settings")
            ).as_markup()
        )
        return
    
    # Size Selection
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
    
    # Style Selection
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
    
    # Ideas
    elif action.startswith("idea_"):
        prompt = action.replace("idea_", "")
        if prompt:
            await callback.message.edit_text(
                f"🎨 **Creating your image...**\n\n"
                f"📝 Prompt: {prompt}\n"
                f"⏳ Please wait...",
                parse_mode="Markdown"
            )
            
            size = IMAGE_SIZES.get(settings["size"], IMAGE_SIZES["square"])
            style = ART_STYLES.get(settings["style"], ART_STYLES["realistic"])
            
            image_data = generate_image_from_prompt(
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
                        f"🎨 **Image Created!**\n\n"
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
    
    # Regenerate
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
        logger.info(f"📦 Mode: NO API KEY NEEDED")
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
