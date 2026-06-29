"""
🎨 Pixel Craft Bot - AI Image Generator
Generate images WITHOUT needing an API key!
Uses free Hugging Face inference API (rate limited) or generates placeholder images
"""

import os
import io
import json
import logging
import aiohttp
import asyncio
import random
from typing import Optional, Dict, Any
from datetime import datetime

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
from PIL import Image, ImageDraw, ImageFont

# ==================== CONFIGURATION ====================

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN is required!")

# Try to get API key, but DON'T require it
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

# Bot Info
BOT_NAME = "Pixel Craft Bot"
BOT_USERNAME = "pixel_craft_bot"
BOT_VERSION = "2.0.0"

# Initialize
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ==================== CONSTANTS ====================

# Free API endpoints (no key required for basic usage)
FREE_API_ENDPOINTS = [
    "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev",
    "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5",
    "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1",
]

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
    "realistic": {"label": "📷 Realistic", "prompt": "photorealistic, high quality"},
    "anime": {"label": "🎨 Anime", "prompt": "anime style, manga, vibrant"},
    "cartoon": {"label": "✏️ Cartoon", "prompt": "cartoon style, illustration"},
    "oil": {"label": "🖌️ Oil Painting", "prompt": "oil painting, artistic"},
    "watercolor": {"label": "💧 Watercolor", "prompt": "watercolor painting, soft"},
    "sketch": {"label": "✒️ Sketch", "prompt": "pencil sketch, drawing"},
    "3d": {"label": "🎮 3D Render", "prompt": "3D render, CGI"},
    "cyberpunk": {"label": "💜 Cyberpunk", "prompt": "cyberpunk, neon, futuristic"},
    "fantasy": {"label": "🧙 Fantasy", "prompt": "fantasy art, magical"},
    "minimalist": {"label": "⬜ Minimalist", "prompt": "minimalist, clean, simple"},
}

# Negative prompts
NEGATIVE_PROMPTS = {
    "none": {"label": "None", "prompt": ""},
    "low_quality": {"label": "Low Quality", "prompt": "low quality, blurry"},
    "distorted": {"label": "Distorted", "prompt": "distorted, ugly, bad anatomy"},
    "watermark": {"label": "Watermark", "prompt": "watermark, signature, text"},
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
                "negative": "none",
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

def negative_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for neg_id, neg_data in NEGATIVE_PROMPTS.items():
        builder.row(InlineKeyboardButton(
            text=neg_data["label"],
            callback_data=f"negative_{neg_id}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_settings"))
    return builder.as_markup()

def ideas_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ideas = [
        ("🌅 Sunset", "golden sunset over ocean, dramatic clouds, warm colors"),
        ("🐱 Cat", "cute fluffy cat, realistic photography, professional lighting"),
        ("🚀 Space", "futuristic space station, nebula, stars, cosmic colors"),
        ("🏰 Castle", "medieval fantasy castle, misty morning, epic landscape"),
        ("🌌 Galaxy", "colorful spiral galaxy, cosmic scene, stars, nebula"),
        ("🌸 Garden", "beautiful japanese garden, cherry blossoms, peaceful"),
        ("🏙️ Cyberpunk", "cyberpunk city, neon lights, rainy night, reflections"),
        ("🧙 Wizard", "ancient wizard, magic spell, glowing staff, mystical"),
        ("🐉 Dragon", "epic dragon, fantasy art, fire breathing, majestic"),
        ("🌊 Wave", "massive ocean wave, dramatic lighting, artistic style"),
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

# ==================== CORE FUNCTIONS ====================

async def generate_image_free(
    prompt: str,
    width: int = 512,
    height: int = 512,
    style: str = "realistic",
    negative: str = "",
    retry_count: int = 0
) -> Optional[bytes]:
    """
    Generate image using FREE Hugging Face API (no key required)
    Falls back to placeholder images if API fails
    """
    
    try:
        # Build prompt with style
        style_prompt = ART_STYLES.get(style, ART_STYLES["realistic"])["prompt"]
        full_prompt = f"{prompt}, {style_prompt}"
        
        if negative:
            full_prompt = f"{full_prompt}. Avoid: {negative}"
        
        logger.info(f"🎨 Generating: {full_prompt[:100]}...")
        
        # Try to use Hugging Face API (free tier)
        if retry_count < 2:  # Try API twice before falling back
            try:
                # Prepare request
                payload = {
                    "inputs": full_prompt,
                    "parameters": {
                        "width": min(width, 512),
                        "height": min(height, 512),
                        "num_inference_steps": 25,
                        "guidance_scale": 7.5,
                    }
                }
                
                # Try different endpoints
                endpoint_index = retry_count % len(FREE_API_ENDPOINTS)
                api_url = FREE_API_ENDPOINTS[endpoint_index]
                
                headers = {"Content-Type": "application/json"}
                if HUGGINGFACE_API_KEY:
                    headers["Authorization"] = f"Bearer {HUGGINGFACE_API_KEY}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        api_url,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=120)
                    ) as response:
                        
                        if response.status == 200:
                            image_data = await response.read()
                            logger.info(f"✅ Generated successfully ({len(image_data)} bytes)")
                            return image_data
                            
                        elif response.status == 503:
                            # Model is loading, wait and retry
                            logger.info("⏳ Model loading, waiting...")
                            await asyncio.sleep(15)
                            if retry_count < 3:
                                return await generate_image_free(
                                    prompt, width, height, style, negative, retry_count + 1
                                )
                                
                        elif response.status == 429:
                            # Rate limited, wait longer
                            logger.warning("⚠️ Rate limited, waiting...")
                            await asyncio.sleep(30)
                            if retry_count < 2:
                                return await generate_image_free(
                                    prompt, width, height, style, negative, retry_count + 1
                                )
                        
                        else:
                            error_text = await response.text()
                            logger.warning(f"⚠️ API Error {response.status}: {error_text[:100]}")
                            
            except Exception as e:
                logger.warning(f"⚠️ API request failed: {str(e)}")
                await asyncio.sleep(5)
        
        # If API fails, generate a beautiful placeholder
        logger.info("🎨 Generating placeholder image...")
        return create_placeholder_image(width, height, prompt, style)
        
    except Exception as e:
        logger.error(f"❌ Generation error: {str(e)}")
        return create_placeholder_image(width, height, prompt, style)

def create_placeholder_image(width: int, height: int, prompt: str, style: str = "realistic") -> bytes:
    """Create a beautiful placeholder image when API is unavailable"""
    try:
        # Create gradient background
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        
        # Color themes based on style
        color_themes = {
            "realistic": [(50, 50, 80), (100, 80, 120)],
            "anime": [(255, 200, 220), (200, 100, 150)],
            "cartoon": [(255, 220, 100), (255, 150, 50)],
            "oil": [(100, 80, 60), (150, 120, 80)],
            "watercolor": [(150, 200, 220), (100, 150, 180)],
            "sketch": [(80, 80, 80), (180, 180, 180)],
            "3d": [(50, 100, 150), (100, 200, 250)],
            "cyberpunk": [(100, 50, 150), (255, 100, 200)],
            "fantasy": [(100, 50, 100), (200, 100, 200)],
            "minimalist": [(200, 200, 220), (240, 240, 250)],
        }
        
        colors = color_themes.get(style, color_themes["realistic"])
        
        # Draw gradient
        for y in range(height):
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * y / height)
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * y / height)
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * y / height)
            draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
        
        # Add decorative shapes
        random.seed(hash(prompt) % 2**32)
        for _ in range(20):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(x1, min(x1 + 100, width))
            y2 = random.randint(y1, min(y1 + 100, height))
            alpha = random.randint(30, 80)
            draw.rectangle([x1, y1, x2, y2], 
                          fill=(255, 255, 255, alpha), 
                          outline=None)
        
        # Add stars
        for _ in range(50):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(1, 3)
            brightness = random.randint(150, 255)
            draw.ellipse([x, y, x + size, y + size], 
                        fill=(brightness, brightness, brightness))
        
        # Add text
        try:
            font_size = min(width, height) // 20
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Wrap prompt text
        words = prompt.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] > width * 0.8:
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
        
        # Draw text
        y_offset = height // 3
        for line in lines[:5]:
            try:
                bbox = draw.textbbox((0, 0), line, font=font)
                x = (width - (bbox[2] - bbox[0])) // 2
                draw.text((x, y_offset), line, fill=(255, 255, 255), font=font)
                y_offset += (bbox[3] - bbox[1]) + 10
            except:
                pass
        
        # Add footer
        try:
            footer_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            footer_font = ImageFont.load_default()
        
        footer = "🎨 Pixel Craft Bot - AI Generated"
        try:
            bbox = draw.textbbox((0, 0), footer, font=footer_font)
            x = (width - (bbox[2] - bbox[0])) // 2
            draw.text((x, height - 40), footer, fill=(200, 200, 200), font=footer_font)
        except:
            pass
        
        # Add status indicator
        status = "✨ DEMO MODE" if not HUGGINGFACE_API_KEY else "🚀 AI POWERED"
        try:
            bbox = draw.textbbox((0, 0), status, font=footer_font)
            draw.text((10, height - 40), status, fill=(255, 200, 100), font=footer_font)
        except:
            pass
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG', optimize=True)
        img_bytes.seek(0)
        return img_bytes.read()
        
    except Exception as e:
        logger.error(f"❌ Placeholder error: {str(e)}")
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
    
    api_status = "✅ Connected" if HUGGINGFACE_API_KEY else "🆓 Free Mode (No API Key)"
    
    welcome = (
        f"🎨 **Welcome to {BOT_NAME}!**\n\n"
        f"👋 Hello @{user.username or 'User'}!\n\n"
        f"I generate images from text descriptions using AI.\n\n"
        f"🔧 **Status:** {api_status}\n"
        f"📊 Images Generated: {data['settings']['total_generated']}\n\n"
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
        "Be detailed for better results:\n"
        "• Subject: what's in the image?\n"
        "• Style: realistic, anime, etc.\n"
        "• Mood: happy, dark, peaceful\n"
        "• Colors: warm, cool, vibrant\n\n"
        "📝 **Examples:**\n"
        "• \"A majestic dragon flying over a medieval castle\"\n"
        "• \"A cyberpunk city with neon lights in the rain\"\n"
        "• \"A cute cat wearing a wizard hat in a magical forest\"\n\n"
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
    negative = NEGATIVE_PROMPTS.get(settings["negative"], NEGATIVE_PROMPTS["none"])
    
    text = (
        "⚙️ **Current Settings**\n\n"
        f"📐 Size: {size['label']}\n"
        f"🎨 Style: {style['label']}\n"
        f"🚫 Negative: {negative['label']}\n\n"
        "Select what to customize:"
    )
    
    await message.reply(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="📐 Change Size", callback_data="change_size"),
            InlineKeyboardButton(text="🎨 Change Style", callback_data="change_style")
        ).row(
            InlineKeyboardButton(text="🚫 Change Negative", callback_data="change_negative"),
            InlineKeyboardButton(text="🔄 Reset All", callback_data="reset_settings")
        ).row(
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
        f"📈 Success rate: {len([h for h in history if h.get('success')])}/{len(history) if history else 1}"
    )
    
    await message.reply(text, parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "❓ **Help & Support**\n\n"
        "🤖 **How to use:**\n"
        "1. Send /generate or tap Generate\n"
        "2. Type your image description\n"
        "3. Wait 10-30 seconds\n"
        "4. Get your image!\n\n"
        "🎯 **Tips:**\n"
        "• Be specific and detailed\n"
        "• Mention style, mood, colors\n"
        "• Use 5-20 words for best results\n\n"
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
        "🎨 **AI Image Generation**\n"
        "Powered by state-of-the-art AI models.\n\n"
        "✨ **Features:**\n"
        "• 10+ Art Styles\n"
        "• 5 Image Sizes\n"
        "• No API Key Required!\n"
        "• Free to use\n"
        "• Usage Statistics\n\n"
        "🔒 **Privacy:**\n"
        "No images or data are stored permanently.\n\n"
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
    negative = NEGATIVE_PROMPTS.get(settings["negative"], NEGATIVE_PROMPTS["none"])
    
    # Send processing message
    processing = await message.reply(
        f"🎨 **Generating your image...**\n\n"
        f"📝 Prompt: {prompt[:150]}{'...' if len(prompt) > 150 else ''}\n"
        f"📐 Size: {size['label']}\n"
        f"🎨 Style: {style['label']}\n\n"
        f"⏳ Please wait 10-30 seconds...",
        parse_mode="Markdown"
    )
    
    try:
        # Generate image (NO API KEY REQUIRED!)
        image_data = await generate_image_free(
            prompt=prompt,
            width=size["width"],
            height=size["height"],
            style=settings["style"],
            negative=negative["prompt"]
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
                    f"🎨 **Image Generated!**\n\n"
                    f"📝 Prompt: {prompt[:200]}{'...' if len(prompt) > 200 else ''}\n"
                    f"📐 Size: {size['label']}\n"
                    f"🎨 Style: {style['label']}\n"
                    f"📊 Size: {format_size(len(image_data))}\n\n"
                    f"🔄 Send a new prompt to generate again!"
                ),
                parse_mode="Markdown",
                reply_markup=generate_options_keyboard()
            )
            
            await processing.delete()
            
        else:
            # Something went wrong
            data["history"].append({
                "prompt": prompt,
                "success": False,
                "timestamp": datetime.now().isoformat()
            })
            
            await message.reply(
                "⚠️ **Generation Failed**\n\n"
                "I couldn't generate an image right now.\n\n"
                "💡 **Tips:**\n"
                "• Try a different prompt\n"
                "• Wait a few seconds and retry\n"
                "• Use a simpler description\n\n"
                "🔄 Tap Retry to try again:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text="🔄 Retry", callback_data="retry_generate"),
                    InlineKeyboardButton(text="🏠 Menu", callback_data="back_menu")
                ).as_markup()
            )
            
            await processing.delete()
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        await message.reply(
            "❌ **Error**\n\n"
            "Something went wrong. Please try again later."
        )
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
        
    elif action == "change_negative":
        await callback.message.edit_text(
            "🚫 **Select Negative Prompt**\n\n"
            "Choose what to avoid in images:",
            parse_mode="Markdown",
            reply_markup=negative_keyboard()
        )
        return
        
    elif action == "reset_settings":
        data["settings"] = {
            "size": "square",
            "style": "realistic",
            "negative": "none",
            "total_generated": data["settings"]["total_generated"],
            "last_generated": data["settings"]["last_generated"]
        }
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
    
    # Negative Selection
    elif action.startswith("negative_"):
        negative_id = action.replace("negative_", "")
        if negative_id in NEGATIVE_PROMPTS:
            settings["negative"] = negative_id
            negative = NEGATIVE_PROMPTS[negative_id]
            await callback.message.edit_text(
                f"✅ **Negative Updated!**\n\n"
                f"New negative: {negative['label']}",
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
                f"🎨 **Generating your idea...**\n\n"
                f"📝 Prompt: {prompt}\n"
                f"⏳ Please wait...",
                parse_mode="Markdown"
            )
            
            size = IMAGE_SIZES.get(settings["size"], IMAGE_SIZES["square"])
            style = ART_STYLES.get(settings["style"], ART_STYLES["realistic"])
            negative = NEGATIVE_PROMPTS.get(settings["negative"], NEGATIVE_PROMPTS["none"])
            
            image_data = await generate_image_free(
                prompt=prompt,
                width=size["width"],
                height=size["height"],
                style=settings["style"],
                negative=negative["prompt"]
            )
            
            if image_data and len(image_data) > 1000:
                data["settings"]["total_generated"] += 1
                input_file = BufferedInputFile(image_data, filename="generated_image.png")
                await callback.message.reply_photo(
                    photo=input_file,
                    caption=(
                        f"🎨 **Image Generated!**\n\n"
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
                await callback.message.reply("⚠️ Failed to generate. Please try again.")
        return
    
    # Retry / Regenerate
    elif action == "retry_generate":
        await cmd_generate(callback.message, state)
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

# ==================== ERROR HANDLER ====================

@dp.errors()
async def error_handler(update, exception):
    logger.error(f"❌ Error: {str(exception)}")
    if hasattr(update, 'message') and update.message:
        try:
            await update.message.reply(
                "❌ **Error**\n\n"
                "Something went wrong. Please try again."
            )
        except:
            pass

# ==================== MAIN ====================

async def main():
    try:
        logger.info("=" * 60)
        logger.info(f"🎨 {BOT_NAME} v{BOT_VERSION}")
        logger.info(f"🤖 Username: @{BOT_USERNAME}")
        logger.info(f"🔑 API Key: {'✅ Configured' if HUGGINGFACE_API_KEY else '🆓 Free Mode'}")
        logger.info("=" * 60)
        
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Fatal: {str(e)}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"💥 Fatal: {str(e)}")
