"""
🎨 Pixel Craft Bot - Professional AI Image Generator
Generates REAL images from text prompts using AI
Telegram Bot for @pixel_craft_bot
"""

import os
import io
import logging
import json
import base64
import random
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Telegram Bot Libraries
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
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# HTTP Client for API calls
import httpx

# Image Processing
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# Utilities
from dotenv import load_dotenv

# ==================== CONFIGURATION ====================

load_dotenv()

# Logging setup
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN is required!")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required!")

# AI API Configuration - Multiple options for redundancy
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

BOT_NAME = "Pixel Craft Bot"
BOT_USERNAME = "pixel_craft_bot"
BOT_VERSION = "3.0.0"

# Initialize bot
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ==================== CONSTANTS ====================

# Image Sizes
IMAGE_SIZES = {
    "square": {"width": 1024, "height": 1024, "label": "🟦 Square (1024x1024)"},
    "portrait": {"width": 1024, "height": 1536, "label": "📱 Portrait (1024x1536)"},
    "landscape": {"width": 1536, "height": 1024, "label": "🖥️ Landscape (1536x1024)"},
    "hd": {"width": 1792, "height": 1024, "label": "📷 HD (1792x1024)"},
}

# Art Styles
ART_STYLES = {
    "realistic": {"label": "📷 Realistic", "prompt": "photorealistic, highly detailed, 8k"},
    "3d": {"label": "🎮 3D Render", "prompt": "3D render, octane render, realistic textures"},
    "anime": {"label": "🎨 Anime", "prompt": "anime style, vibrant colors, cel shaded"},
    "digital": {"label": "💻 Digital Art", "prompt": "digital art, concept art, smooth rendering"},
    "cartoon": {"label": "✏️ Cartoon", "prompt": "cartoon style, colorful, flat design"},
    "oil": {"label": "🖌️ Oil Painting", "prompt": "oil painting, canvas texture, artistic"},
    "watercolor": {"label": "💧 Watercolor", "prompt": "watercolor painting, soft colors"},
    "pixel": {"label": "📟 Pixel Art", "prompt": "pixel art, retro, 8-bit style"},
    "cyberpunk": {"label": "💜 Cyberpunk", "prompt": "cyberpunk, neon lights, futuristic"},
    "cinematic": {"label": "🎬 Cinematic", "prompt": "cinematic, movie scene, dramatic lighting"},
}

# Color Themes for prompt enhancement
COLOR_THEMES = {
    "neon": "neon colors, glowing, vibrant",
    "dark": "dark, moody, shadowy",
    "pastel": "pastel colors, soft, gentle",
    "vintage": "vintage, retro, warm tones",
    "cyberpunk": "cyberpunk colors, neon pink, cyan",
    "minimal": "minimal, clean, simple",
    "luxury": "luxury, gold, premium, elegant",
    "cinematic": "cinematic colors, film grade",
    "warm": "warm colors, golden, sunset",
    "cool": "cool colors, blue, cyan, fresh",
    "monochrome": "monochrome, black and white",
    "vibrant": "vibrant, colorful, bold"
}

# Scene Keywords for detection
SCENE_KEYWORDS = {
    "portrait": ["portrait", "face", "person", "people", "model", "woman", "man"],
    "landscape": ["landscape", "scenery", "mountain", "ocean", "beach", "forest"],
    "character": ["character", "figure", "avatar", "warrior", "mage", "knight"],
    "product": ["product", "item", "device", "phone", "laptop", "camera"],
    "architecture": ["building", "architecture", "castle", "tower", "city"],
    "fantasy": ["fantasy", "magic", "dragon", "wizard", "elf", "creature"],
    "abstract": ["abstract", "pattern", "texture", "geometric", "modern"],
    "technology": ["tech", "cyber", "robot", "digital", "future", "ai"],
    "nature": ["nature", "flower", "tree", "garden", "animal", "bird"],
}

# Scene enhancements
SCENE_ENHANCEMENTS = {
    "portrait": "professional portrait, studio lighting, sharp focus",
    "landscape": "breathtaking landscape, panoramic view, golden hour",
    "character": "character design, detailed illustration, dynamic pose",
    "product": "product photography, studio lighting, perfect composition",
    "architecture": "architectural photography, stunning building, geometric",
    "fantasy": "fantasy art, magical atmosphere, epic scene, vivid colors",
    "abstract": "abstract art, creative composition, artistic expression",
    "technology": "futuristic technology, sleek design, digital art",
    "nature": "beautiful nature, vibrant colors, peaceful scene",
}

# ==================== STATES ====================

class GeneratorStates(StatesGroup):
    WAITING_PROMPT = State()

# ==================== USER DATA ====================

user_data: Dict[int, Dict] = {}

def get_user_data(user_id: int) -> Dict:
    if user_id not in user_data:
        user_data[user_id] = {
            "settings": {
                "size": "square",
                "style": "realistic",
                "theme": "vibrant",
                "quality": "standard",
                "total_generated": 0,
                "last_generated": None
            },
            "history": [],
            "last_prompt": None,
            "last_image": None,
            "last_result": None
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
        InlineKeyboardButton(text="❓ Help", callback_data="help"),
        InlineKeyboardButton(text="🔄 Regenerate", callback_data="regenerate")
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

def theme_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    themes = list(COLOR_THEMES.items())
    for i in range(0, len(themes), 2):
        row = []
        for j in range(2):
            if i + j < len(themes):
                theme_id, theme_data = themes[i + j]
                row.append(InlineKeyboardButton(
                    text=f"🎨 {theme_id.capitalize()}",
                    callback_data=f"theme_{theme_id}"
                ))
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_settings"))
    return builder.as_markup()

def ideas_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ideas = [
        ("🌅 Cinematic Sunset", "epic cinematic sunset over ocean with golden clouds, dramatic lighting"),
        ("🐱 Cute Anime Cat", "cute anime style cat in a magical forest with glowing flowers"),
        ("🚀 Futuristic City", "futuristic cyberpunk city with neon lights and flying cars, night scene"),
        ("🏰 Fantasy Castle", "magnificent fantasy castle on a mountain peak, magical clouds, epic scene"),
        ("🌌 Cosmic Galaxy", "beautiful cosmic galaxy with vibrant nebula, stars, and planets"),
        ("🌸 Japanese Garden", "peaceful japanese garden with cherry blossoms, koi pond, pagoda"),
        ("🧙 Dark Wizard", "dark wizard casting powerful magic, dramatic lighting, fantasy art"),
        ("🐉 Epic Dragon", "epic dragon flying over mountains, fire breathing, fantasy scene"),
        ("🌊 Ocean Wave", "massive ocean wave, dramatic lighting, watercolor art style"),
        ("🏔️ Mountain Peak", "snowy mountain peak at sunrise, golden hour, majestic landscape"),
        ("🤖 AI Robot", "futuristic AI robot, sleek design, cyberpunk style, glowing neon"),
        ("🌺 Tropical Paradise", "tropical paradise with palm trees, crystal clear water, sunset")
    ]
    for label, prompt in ideas[:8]:
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"idea_{prompt}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_menu"))
    return builder.as_markup()

# ==================== AI IMAGE GENERATION ====================

class AIImageGenerator:
    """Real AI Image Generation using multiple APIs"""
    
    def __init__(self):
        self.replicate_token = REPLICATE_API_TOKEN
        self.openai_key = OPENAI_API_KEY
        self.huggingface_key = HUGGINGFACE_API_KEY
        
        # Available models (try in order)
        self.models = []
        
        if self.replicate_token:
            self.models.append(self._generate_replicate)
        
        if self.huggingface_key:
            self.models.append(self._generate_huggingface)
        
        if self.openai_key:
            self.models.append(self._generate_openai)
    
    async def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        style: str = "realistic",
        num_images: int = 1,
        theme: str = "vibrant"
    ) -> Optional[bytes]:
        """
        Generate image using available APIs
        Returns: image bytes or None
        """
        if not self.models:
            logger.warning("⚠️ No AI API keys configured! Use placeholder mode.")
            return self._create_placeholder(prompt, width, height)
        
        # Enhance prompt
        enhanced_prompt = self._enhance_prompt(prompt, style, theme)
        logger.info(f"🎨 Generating: {enhanced_prompt[:100]}...")
        
        # Try each model
        for generate_func in self.models:
            try:
                result = await generate_func(enhanced_prompt, width, height, num_images)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Model failed: {str(e)}")
                continue
        
        # If all fail, return placeholder
        return self._create_placeholder(prompt, width, height)
    
    async def _generate_replicate(self, prompt: str, width: int, height: int, num_images: int) -> Optional[bytes]:
        """Generate using Replicate API"""
        try:
            import replicate
            
            client = replicate.Client(api_token=self.replicate_token)
            
            # Use SDXL model
            output = client.run(
                "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                input={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_outputs": num_images,
                    "guidance_scale": 7.5,
                    "num_inference_steps": 50,
                    "negative_prompt": "low quality, blurry, distorted, ugly, bad anatomy"
                }
            )
            
            # Download image
            if isinstance(output, list) and output:
                image_url = output[0]
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url, timeout=60)
                    response.raise_for_status()
                    return response.content
            return None
            
        except Exception as e:
            logger.error(f"Replicate error: {str(e)}")
            raise
    
    async def _generate_huggingface(self, prompt: str, width: int, height: int, num_images: int) -> Optional[bytes]:
        """Generate using Hugging Face API"""
        try:
            # Use Stable Diffusion on Hugging Face
            api_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
            headers = {"Authorization": f"Bearer {self.huggingface_key}"}
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "width": min(width, 512),
                    "height": min(height, 512),
                    "num_inference_steps": 30,
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                
                if response.status_code == 200:
                    return response.content
                elif response.status_code == 503:
                    # Model loading, wait and retry
                    await asyncio.sleep(10)
                    return await self._generate_huggingface(prompt, width, height, num_images)
                else:
                    logger.error(f"HuggingFace error: {response.status_code}")
                    raise Exception(f"API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"HuggingFace error: {str(e)}")
            raise
    
    async def _generate_openai(self, prompt: str, width: int, height: int, num_images: int) -> Optional[bytes]:
        """Generate using OpenAI DALL-E"""
        try:
            import openai
            
            openai.api_key = self.openai_key
            
            response = await openai.Image.acreate(
                prompt=prompt,
                n=num_images,
                size=f"{width}x{height}",
                quality="standard"
            )
            
            if response.data and response.data[0].url:
                async with httpx.AsyncClient() as client:
                    image_response = await client.get(response.data[0].url, timeout=60)
                    image_response.raise_for_status()
                    return image_response.content
            
            return None
            
        except Exception as e:
            logger.error(f"OpenAI error: {str(e)}")
            raise
    
    def _enhance_prompt(self, prompt: str, style: str, theme: str) -> str:
        """Enhance prompt with style and theme"""
        # Detect scene
        scene = self._detect_scene(prompt)
        scene_enhancement = SCENE_ENHANCEMENTS.get(scene, "")
        
        # Get style prompt
        style_prompt = ART_STYLES.get(style, ART_STYLES["realistic"])["prompt"]
        
        # Get theme prompt
        theme_prompt = COLOR_THEMES.get(theme, COLOR_THEMES["vibrant"])
        
        # Build enhanced prompt
        enhanced = f"{prompt}, {style_prompt}, {theme_prompt}, {scene_enhancement}, high quality, detailed, beautiful"
        
        return enhanced
    
    def _detect_scene(self, prompt: str) -> str:
        """Detect scene from prompt"""
        prompt_lower = prompt.lower()
        scores = {}
        
        for scene, keywords in SCENE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > 0:
                scores[scene] = score
        
        if not scores:
            return "landscape"
        
        return max(scores, key=scores.get)
    
    def _create_placeholder(self, prompt: str, width: int, height: int) -> bytes:
        """Create placeholder when no API is available"""
        try:
            img = Image.new('RGB', (width, height), color=(30, 30, 50))
            draw = ImageDraw.Draw(img)
            
            # Gradient
            for y in range(height):
                r = int(30 + (80 * y / height))
                g = int(30 + (60 * y / height))
                b = int(50 + (120 * y / height))
                draw.rectangle([(0, y), (width, y + 1)], fill=(r, g, b))
            
            # Stars
            random.seed(hash(prompt) % 2**32)
            for _ in range(50):
                x = random.randint(0, width)
                y = random.randint(0, height)
                size = random.randint(1, 3)
                brightness = random.randint(150, 255)
                draw.ellipse([x, y, x + size, y + size],
                           fill=(brightness, brightness, brightness))
            
            # Text
            try:
                font_size = min(width, height) // 20
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # Wrap prompt text
            words = prompt.split()
            lines = []
            current = []
            max_width = width - 40
            
            for word in words[:20]:
                test_line = ' '.join(current + [word])
                try:
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    if bbox[2] - bbox[0] > max_width:
                        if current:
                            lines.append(' '.join(current))
                            current = [word]
                        else:
                            lines.append(test_line)
                            current = []
                    else:
                        current.append(word)
                except:
                    lines.append(test_line)
                    current = []
            
            if current:
                lines.append(' '.join(current))
            
            # Draw text
            y_offset = height // 3
            for line in lines[:5]:
                try:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    x = (width - (bbox[2] - bbox[0])) // 2
                    draw.text((x + 2, y_offset + 2), line, fill=(0, 0, 0, 150), font=font)
                    draw.text((x, y_offset), line, fill=(255, 255, 255), font=font)
                    y_offset += (bbox[3] - bbox[1]) + 15
                except:
                    pass
            
            # Status
            try:
                status_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
                status = "⚠️ DEMO MODE - API Token Required"
                bbox = draw.textbbox((0, 0), status, font=status_font)
                x = (width - (bbox[2] - bbox[0])) // 2
                draw.text((x, height - 40), status, fill=(255, 200, 100), font=status_font)
            except:
                pass
            
            # Convert to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', optimize=True)
            img_bytes.seek(0)
            return img_bytes.getvalue()
            
        except Exception as e:
            logger.error(f"Placeholder error: {str(e)}")
            return b""

# Initialize AI Generator
ai_generator = AIImageGenerator()

# ==================== COMMAND HANDLERS ====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    data = get_user_data(user.id)
    
    # Check if API is configured
    has_api = bool(REPLICATE_API_TOKEN or OPENAI_API_KEY or HUGGINGFACE_API_KEY)
    status = "🚀 AI Ready" if has_api else "⚠️ Demo Mode (API Key Required)"
    
    welcome = (
        f"🎨 **Welcome to {BOT_NAME}!**\n\n"
        f"👋 Hello @{user.username or 'User'}!\n\n"
        f"I generate **real AI images** from your text descriptions.\n\n"
        f"📊 **Status:** {status}\n"
        f"🖼️ **Images Generated:** {data['settings']['total_generated']}\n\n"
        f"✨ **Features:**\n"
        f"• 🎨 10 Art Styles\n"
        f"• 📐 4 Image Sizes\n"
        f"• 🌈 12 Color Themes\n"
        f"• 🔍 Smart Scene Detection\n"
        f"• 💡 12+ Prompt Ideas\n"
        f"• 🔄 Regenerate Images\n\n"
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
        "Be creative! I'll generate a unique image based on your words.\n\n"
        "📝 **Examples:**\n"
        "• \"A beautiful sunset over the ocean with golden clouds\"\n"
        "• \"A cute cat sitting in a magical forest with glowing flowers\"\n"
        "• \"A futuristic cyberpunk city with neon lights and flying cars\"\n"
        "• \"A majestic dragon flying over a fantasy castle at dawn\"\n\n"
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
    theme = settings.get("theme", "vibrant")
    
    text = (
        "⚙️ **Settings**\n\n"
        f"📐 Size: {size['label']}\n"
        f"🎨 Style: {style['label']}\n"
        f"🌈 Theme: {theme.capitalize()}\n\n"
        "Select what to customize:"
    )
    
    await message.reply(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="📐 Change Size", callback_data="change_size"),
            InlineKeyboardButton(text="🎨 Change Style", callback_data="change_style")
        ).row(
            InlineKeyboardButton(text="🌈 Change Theme", callback_data="change_theme"),
            InlineKeyboardButton(text="🔄 Reset All", callback_data="reset_settings")
        ).row(
            InlineKeyboardButton(text="🔙 Back", callback_data="back_menu")
        ).as_markup()
    )

@dp.message(Command("ideas"))
async def cmd_ideas(message: Message):
    await message.reply(
        "💡 **Get Inspired!**\n\n"
        "Click any idea below to generate an image instantly:",
        parse_mode="Markdown",
        reply_markup=ideas_keyboard()
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    settings = data["settings"]
    history = data["history"]
    
    # Calculate style usage
    style_counts = {}
    for h in history:
        style = h.get("style", "unknown")
        style_counts[style] = style_counts.get(style, 0) + 1
    
    most_used_style = max(style_counts.items(), key=lambda x: x[1])[0] if style_counts else "None"
    
    text = (
        "📊 **Your Statistics**\n\n"
        f"🖼️ Total images: {settings['total_generated']}\n"
        f"📐 Default Size: {IMAGE_SIZES.get(settings['size'], IMAGE_SIZES['square'])['label']}\n"
        f"🎨 Default Style: {ART_STYLES.get(settings['style'], ART_STYLES['realistic'])['label']}\n"
        f"🌈 Default Theme: {settings.get('theme', 'vibrant').capitalize()}\n"
        f"📅 Last generated: {settings['last_generated'] or 'Never'}\n\n"
        f"🏆 Most used style: {most_used_style.capitalize()}\n"
        f"📈 Total generations: {len(history)}"
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
        "4. Get your AI-generated image!\n\n"
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
    # Check if API is configured
    has_api = bool(REPLICATE_API_TOKEN or OPENAI_API_KEY or HUGGINGFACE_API_KEY)
    
    about = (
        f"🤖 **{BOT_NAME}**\n\n"
        f"📦 Version: {BOT_VERSION}\n"
        f"👤 Username: @{BOT_USERNAME}\n\n"
        "🎨 **Professional AI Image Generator**\n"
        f"Status: {'🚀 AI Ready' if has_api else '⚠️ Demo Mode'}\n\n"
        "✨ **Features:**\n"
        "• 10 Art Styles\n"
        "• 4 Image Sizes\n"
        "• 12 Color Themes\n"
        "• Smart Scene Detection\n"
        "• Prompt Enhancement\n"
        "• Usage Statistics\n"
        "• Regenerate Images\n\n"
        "🔒 **Privacy:**\n"
        "No images are permanently stored.\n\n"
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
    
    prompt = message.text
    if not prompt:
        await message.reply("❌ Please send a text description.")
        return
    
    await generate_and_send(message, prompt, state)

# ==================== GENERATION FUNCTION ====================

async def generate_and_send(message: Message, prompt: str, state: FSMContext = None):
    """Generate and send image"""
    user_id = message.from_user.id
    data = get_user_data(user_id)
    settings = data["settings"]
    
    size = IMAGE_SIZES.get(settings["size"], IMAGE_SIZES["square"])
    style = ART_STYLES.get(settings["style"], ART_STYLES["realistic"])
    theme = settings.get("theme", "vibrant")
    
    # Send processing message
    processing = await message.reply(
        f"🎨 **Generating your image...**\n\n"
        f"📝 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n"
        f"📐 Size: {size['label']}\n"
        f"🎨 Style: {style['label']}\n"
        f"🌈 Theme: {theme.capitalize()}\n\n"
        f"⏳ Please wait 10-30 seconds...",
        parse_mode="Markdown"
    )
    
    try:
        # Generate image
        image_bytes = await ai_generator.generate(
            prompt=prompt,
            width=size["width"],
            height=size["height"],
            style=settings["style"],
            theme=theme
        )
        
        if image_bytes and len(image_bytes) > 1000:
            # Update stats
            data["settings"]["total_generated"] += 1
            data["settings"]["last_generated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            data["history"].append({
                "prompt": prompt,
                "style": settings["style"],
                "size": settings["size"],
                "theme": theme,
                "success": True,
                "timestamp": datetime.now().isoformat()
            })
            data["last_prompt"] = prompt
            data["last_image"] = image_bytes
            
            # Send image
            input_file = BufferedInputFile(image_bytes, filename="generated_image.png")
            
            # Detect if it's real AI or placeholder
            has_api = bool(REPLICATE_API_TOKEN or OPENAI_API_KEY or HUGGINGFACE_API_KEY)
            status_text = "🚀 AI Generated" if has_api else "⚠️ Demo Mode"
            
            await message.reply_photo(
                photo=input_file,
                caption=(
                    f"🎨 **Image Created!**\n\n"
                    f"📝 Prompt: {prompt[:200]}{'...' if len(prompt) > 200 else ''}\n"
                    f"📐 Size: {size['label']}\n"
                    f"🎨 Style: {style['label']}\n"
                    f"🌈 Theme: {theme.capitalize()}\n"
                    f"📊 Status: {status_text}\n"
                    f"📁 Size: {len(image_bytes) // 1024} KB\n\n"
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
        await message.reply(
            f"❌ **Something went wrong**\n\n"
            f"Error: {str(e)[:100]}\n\n"
            "Please try again later.",
            parse_mode="Markdown"
        )
        await processing.delete()
    
    if state:
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
    
    if action == "back_settings":
        await cmd_settings(callback.message)
        return
    
    # Main Actions
    if action == "generate":
        await cmd_generate(callback.message, state)
        return
    
    if action == "settings":
        await cmd_settings(callback.message)
        return
    
    if action == "ideas":
        await callback.message.edit_text(
            "💡 **Get Inspired!**\n\n"
            "Click any idea below to generate an image:",
            parse_mode="Markdown",
            reply_markup=ideas_keyboard()
        )
        return
    
    if action == "stats":
        await cmd_stats(callback.message)
        return
    
    if action == "help":
        await cmd_help(callback.message)
        return
    
    # Settings
    if action == "change_size":
        await callback.message.edit_text(
            "📐 **Select Image Size**\n\n"
            "Choose your preferred size:",
            parse_mode="Markdown",
            reply_markup=size_keyboard()
        )
        return
    
    if action == "change_style":
        await callback.message.edit_text(
            "🎨 **Select Art Style**\n\n"
            "Choose your preferred style:",
            parse_mode="Markdown",
            reply_markup=style_keyboard()
        )
        return
    
    if action == "change_theme":
        await callback.message.edit_text(
            "🌈 **Select Color Theme**\n\n"
            "Choose your preferred theme:",
            parse_mode="Markdown",
            reply_markup=theme_keyboard()
        )
        return
    
    if action == "reset_settings":
        settings["size"] = "square"
        settings["style"] = "realistic"
        settings["theme"] = "vibrant"
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
    if action.startswith("size_"):
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
    if action.startswith("style_"):
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
    
    # Theme Selection
    if action.startswith("theme_"):
        theme_id = action.replace("theme_", "")
        if theme_id in COLOR_THEMES:
            settings["theme"] = theme_id
            await callback.message.edit_text(
                f"✅ **Theme Updated!**\n\n"
                f"New theme: {theme_id.capitalize()}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text="🔙 Back", callback_data="back_settings")
                ).as_markup()
            )
        return
    
    # Ideas
    if action.startswith("idea_"):
        prompt = action.replace("idea_", "")
        if prompt:
            await generate_and_send(callback.message, prompt, state)
        return
    
    # Regenerate
    if action == "regenerate":
        if data.get("last_prompt"):
            await generate_and_send(callback.message, data["last_prompt"], state)
        else:
            await callback.message.reply(
                "❌ No previous image to regenerate.\n"
                "Generate a new image with /generate",
                parse_mode="Markdown"
            )
        return

# ==================== MESSAGE HANDLER ====================

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
                "Something went wrong. Please try again.",
                parse_mode="Markdown"
            )
        except:
            pass

# ==================== MAIN ====================

async def main():
    """Main entry point"""
    try:
        logger.info("=" * 60)
        logger.info(f"🎨 {BOT_NAME} v{BOT_VERSION}")
        logger.info(f"🤖 Username: @{BOT_USERNAME}")
        logger.info(f"🔑 API Keys: {'✅' if (REPLICATE_API_TOKEN or OPENAI_API_KEY or HUGGINGFACE_API_KEY) else '⚠️ None'}")
        logger.info(f"🎨 Styles: {len(ART_STYLES)}")
        logger.info(f"📐 Sizes: {len(IMAGE_SIZES)}")
        logger.info("=" * 60)
        
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal: {str(e)}")
