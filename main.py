"""
Pixel Craft Bot - AI Image Generator for Telegram
Generate images from text prompts using AI
"""

import os
import io
import json
import logging
import aiohttp
import asyncio
from typing import Optional
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    BufferedInputFile,
    InputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from PIL import Image

# ==================== CONFIGURATION ====================

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

# AI API Configuration
# Using Hugging Face API (Free tier)
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"

# Bot information
BOT_NAME = "Pixel Craft Bot"
BOT_USERNAME = "pixel_craft_bot"
BOT_VERSION = "1.0.0"

# Initialize bot
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# User state for image generation
class ImageGenStates(StatesGroup):
    waiting_for_prompt = State()
    waiting_for_size = State()

# User data storage
user_data = {}

# ==================== CONSTANTS ====================

# Image sizes
IMAGE_SIZES = {
    "square": {"width": 512, "height": 512, "label": "🟦 Square (512x512)"},
    "portrait": {"width": 384, "height": 512, "label": "🟧 Portrait (384x512)"},
    "landscape": {"width": 512, "height": 384, "label": "🟩 Landscape (512x384)"},
    "wide": {"width": 768, "height": 512, "label": "🟨 Wide (768x512)"},
}

# Styles
IMAGE_STYLES = {
    "realistic": {"prompt": "realistic photo, photography", "label": "📷 Realistic"},
    "anime": {"prompt": "anime style, manga", "label": "🎨 Anime"},
    "cartoon": {"prompt": "cartoon style, illustration", "label": "✏️ Cartoon"},
    "oil_painting": {"prompt": "oil painting, artistic", "label": "🖌️ Oil Painting"},
    "watercolor": {"prompt": "watercolor painting, soft", "label": "🎨 Watercolor"},
    "sketch": {"prompt": "pencil sketch, drawing", "label": "✏️ Sketch"},
    "3d": {"prompt": "3D render, cgi", "label": "🎮 3D Render"},
    "cyberpunk": {"prompt": "cyberpunk style, neon", "label": "💜 Cyberpunk"},
}

# Negative prompts
NEGATIVE_PROMPTS = {
    "none": {"label": "None", "prompt": ""},
    "low_quality": {"label": "Low Quality", "prompt": "low quality, blurry, pixelated"},
    "distorted": {"label": "Distorted", "prompt": "distorted, ugly, bad anatomy"},
    "watermark": {"label": "No Watermark", "prompt": "watermark, signature, text"},
}

# ==================== HELPERS ====================

def get_main_menu() -> InlineKeyboardMarkup:
    """Create main menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎨 Generate Image", callback_data="generate")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Settings", callback_data="settings"),
        InlineKeyboardButton(text="ℹ️ Help", callback_data="help")
    )
    builder.row(
        InlineKeyboardButton(text="💡 Ideas", callback_data="ideas")
    )
    return builder.as_markup()


def get_size_keyboard() -> InlineKeyboardMarkup:
    """Create size selection keyboard"""
    builder = InlineKeyboardBuilder()
    for size_id, size_data in IMAGE_SIZES.items():
        builder.row(InlineKeyboardButton(
            text=size_data["label"],
            callback_data=f"size_{size_id}"
        ))
    builder.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")
    )
    return builder.as_markup()


def get_style_keyboard() -> InlineKeyboardMarkup:
    """Create style selection keyboard"""
    builder = InlineKeyboardBuilder()
    styles = list(IMAGE_STYLES.items())
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
    builder.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")
    )
    return builder.as_markup()


def get_negative_keyboard() -> InlineKeyboardMarkup:
    """Create negative prompt selection keyboard"""
    builder = InlineKeyboardBuilder()
    for neg_id, neg_data in NEGATIVE_PROMPTS.items():
        builder.row(InlineKeyboardButton(
            text=neg_data["label"],
            callback_data=f"negative_{neg_id}"
        ))
    builder.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")
    )
    return builder.as_markup()


def get_ideas_keyboard() -> InlineKeyboardMarkup:
    """Create ideas keyboard"""
    builder = InlineKeyboardBuilder()
    ideas = [
        ("🌅 Sunset", "sunset over ocean, golden hour, beautiful landscape"),
        ("🐱 Cat", "cute cat, fluffy, realistic photography"),
        ("🚀 Space", "futuristic space station, nebula, stars"),
        ("🏰 Castle", "medieval castle, fantasy, misty morning"),
        ("🌌 Galaxy", "colorful galaxy, cosmic, stars"),
        ("🌸 Garden", "beautiful garden, flowers, butterflies"),
        ("🏙️ City", "cyberpunk city, neon lights, rainy night"),
        ("🧙 Wizard", "old wizard, magic, glowing staff"),
        ("🐉 Dragon", "epic dragon, fantasy art, fire breathing"),
        ("🌊 Wave", "massive wave, ocean, dramatic lighting"),
    ]
    for idea_text, idea_prompt in ideas:
        builder.row(InlineKeyboardButton(
            text=idea_text,
            callback_data=f"idea_{idea_prompt[:50]}"
        ))
    builder.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")
    )
    return builder.as_markup()


def get_settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Create settings keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Get user settings
    settings = user_data.get(user_id, {}).get("settings", {})
    current_size = settings.get("size", "square")
    current_style = settings.get("style", "realistic")
    current_negative = settings.get("negative", "none")
    
    builder.row(InlineKeyboardButton(
        text=f"📐 Size: {IMAGE_SIZES[current_size]['label'][:20]}",
        callback_data="change_size"
    ))
    builder.row(InlineKeyboardButton(
        text=f"🎨 Style: {IMAGE_STYLES[current_style]['label']}",
        callback_data="change_style"
    ))
    builder.row(InlineKeyboardButton(
        text=f"🚫 Negative: {NEGATIVE_PROMPTS[current_negative]['label']}",
        callback_data="change_negative"
    ))
    builder.row(
        InlineKeyboardButton(text="🔄 Reset Settings", callback_data="reset_settings"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")
    )
    return builder.as_markup()


async def generate_image(
    prompt: str,
    width: int = 512,
    height: int = 512,
    style: str = "realistic",
    negative: str = ""
) -> Optional[bytes]:
    """
    Generate image using Hugging Face API
    Returns image bytes or None if failed
    """
    try:
        # Combine prompt with style
        style_data = IMAGE_STYLES.get(style, {})
        style_prompt = style_data.get("prompt", "")
        
        full_prompt = f"{prompt}, {style_prompt}"
        
        # Add negative prompt
        if negative:
            full_prompt = f"{full_prompt} [negative: {negative}]"
        
        # Prepare request payload
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "width": width,
                "height": height,
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
            }
        }
        
        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}" if HUGGINGFACE_API_KEY else "",
            "Content-Type": "application/json",
        }
        
        # Use free API (no key needed for rate-limited demo)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    return await response.read()
                elif response.status == 503:
                    # Model loading, wait and retry
                    await asyncio.sleep(5)
                    return await generate_image(prompt, width, height, style, negative)
                else:
                    error_text = await response.text()
                    logger.error(f"API Error: {response.status} - {error_text}")
                    
                    # Try fallback API
                    return await generate_image_fallback(prompt, width, height)
                    
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        return await generate_image_fallback(prompt, width, height)


async def generate_image_fallback(prompt: str, width: int, height: int) -> Optional[bytes]:
    """
    Fallback image generation using a simpler API
    """
    try:
        # Use Stable Diffusion API (free, no key needed)
        fallback_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "width": min(width, 512),
                "height": min(height, 512),
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                fallback_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Fallback API failed: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Fallback error: {str(e)}")
        return None


def create_placeholder_image(width: int, height: int, prompt: str) -> bytes:
    """
    Create a placeholder image when API fails
    """
    try:
        # Create a simple gradient image with text
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new('RGB', (width, height), color=(50, 50, 80))
        draw = ImageDraw.Draw(img)
        
        # Draw gradient
        for i in range(height):
            color = int(50 + (100 * i / height))
            draw.rectangle([(0, i), (width, i+1)], fill=(color, color, color+50))
        
        # Add text
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        text = f"🎨 {prompt[:30]}{'...' if len(prompt) > 30 else ''}"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        
        # Add footer
        footer = "Pixel Craft Bot - Demo Mode"
        footer_bbox = draw.textbbox((0, 0), footer, font=font)
        footer_width = footer_bbox[2] - footer_bbox[0]
        draw.text(((width - footer_width) // 2, height - 40), footer, fill=(200, 200, 200), font=font)
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes.read()
        
    except Exception as e:
        logger.error(f"Placeholder error: {str(e)}")
        return b""


# ==================== COMMAND HANDLERS ====================

@dp.message(Command("start"))
async def start_command(message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    # Initialize user data
    if user_id not in user_data:
        user_data[user_id] = {
            "settings": {
                "size": "square",
                "style": "realistic",
                "negative": "none",
            }
        }
    
    welcome_text = (
        f"🎨 Welcome to {BOT_NAME}!\n\n"
        f"👋 Hello @{username}!\n\n"
        "I can generate amazing images from your text descriptions using AI.\n\n"
        "📷 **Supported Features:**\n"
        "• Text-to-Image Generation\n"
        "• Multiple Art Styles\n"
        "• Various Image Sizes\n"
        "• Custom Negative Prompts\n\n"
        "💡 **Quick Start:**\n"
        "1. Click 'Generate Image' below\n"
        "2. Type your description\n"
        "3. Wait for the magic!\n\n"
        "🔧 **Commands:**\n"
        "/start - Show this menu\n"
        "/generate - Generate an image\n"
        "/settings - Change settings\n"
        "/ideas - Get inspiration\n"
        "/help - Show help\n"
        "/about - About this bot"
    )
    
    await message.reply(
        welcome_text,
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )


@dp.message(Command("generate"))
async def generate_command(message: Message, state: FSMContext):
    """Handle /generate command"""
    await state.set_state(ImageGenStates.waiting_for_prompt)
    await message.reply(
        "🎨 **Describe what you want to generate!**\n\n"
        "Examples:\n"
        "• \"A beautiful sunset over the ocean\"\n"
        "• \"A cute cat wearing a wizard hat\"\n"
        "• \"A futuristic city with neon lights\"\n\n"
        "Send /cancel to cancel.",
        parse_mode="Markdown"
    )


@dp.message(Command("settings"))
async def settings_command(message: Message):
    """Handle /settings command"""
    user_id = message.from_user.id
    await message.reply(
        "⚙️ **Settings**\n\n"
        "Customize your image generation preferences:",
        reply_markup=get_settings_keyboard(user_id),
        parse_mode="Markdown"
    )


@dp.message(Command("ideas"))
async def ideas_command(message: Message):
    """Handle /ideas command"""
    await message.reply(
        "💡 **Need inspiration?**\n\n"
        "Click any idea below to generate an image:",
        reply_markup=get_ideas_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(Command("help"))
async def help_command(message: Message):
    """Handle /help command"""
    help_text = (
        "❓ **Help & Support**\n\n"
        "📖 **How to use:**\n"
        "1. Click 'Generate Image' or send /generate\n"
        "2. Type a detailed description\n"
        "3. Wait for your image to generate\n\n"
        "🎨 **Tips for better results:**\n"
        "• Be specific and detailed\n"
        "• Include style, colors, mood\n"
        "• Mention lighting and composition\n"
        "• Use 5-20 words for best results\n\n"
        "⚙️ **Customization:**\n"
        "• Change image size (Square, Portrait, etc.)\n"
        "• Select art style (Realistic, Anime, etc.)\n"
        "• Add negative prompts to avoid issues\n\n"
        "🔄 **Commands:**\n"
        "/start - Main menu\n"
        "/generate - Generate an image\n"
        "/settings - Change settings\n"
        "/ideas - Get inspiration\n"
        "/help - This help\n"
        "/about - About this bot\n"
        "/cancel - Cancel current operation"
    )
    await message.reply(help_text, parse_mode="Markdown")


@dp.message(Command("about"))
async def about_command(message: Message):
    """Handle /about command"""
    about_text = (
        f"🤖 **{BOT_NAME}**\n\n"
        f"Version: {BOT_VERSION}\n\n"
        "🎨 **AI Image Generator**\n"
        "Powered by cutting-edge AI technology\n\n"
        "✨ **Features:**\n"
        "• Text-to-Image Generation\n"
        "• Multiple Art Styles\n"
        "• Various Image Sizes\n"
        "• Custom Negative Prompts\n\n"
        "🔒 **Privacy:**\n"
        "No images or data are stored permanently.\n"
        "All data is deleted after processing.\n\n"
        "👨‍💻 **Username:** @pixel_craft_bot\n"
        "📚 **Open Source**"
    )
    await message.reply(about_text, parse_mode="Markdown")


@dp.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    """Cancel current operation"""
    await state.clear()
    await message.reply(
        "✅ Operation cancelled.\n"
        "Use /start to return to the menu."
    )


@dp.message(ImageGenStates.waiting_for_prompt)
async def process_prompt(message: Message, state: FSMContext):
    """Process user's prompt and generate image"""
    if message.text and message.text.startswith("/"):
        await state.clear()
        return
    
    user_id = message.from_user.id
    prompt = message.text
    
    if not prompt:
        await message.reply("❌ Please send a text description.")
        return
    
    # Get user settings
    settings = user_data.get(user_id, {}).get("settings", {})
    size_id = settings.get("size", "square")
    style_id = settings.get("style", "realistic")
    negative_id = settings.get("negative", "none")
    
    size_data = IMAGE_SIZES.get(size_id, IMAGE_SIZES["square"])
    negative_data = NEGATIVE_PROMPTS.get(negative_id, NEGATIVE_PROMPTS["none"])
    
    width = size_data["width"]
    height = size_data["height"]
    negative_prompt = negative_data["prompt"]
    
    # Send processing message
    processing_msg = await message.reply(
        f"🎨 **Generating your image...**\n\n"
        f"📝 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n"
        f"📐 Size: {size_data['label']}\n"
        f"🎨 Style: {IMAGE_STYLES[style_id]['label']}\n\n"
        f"⏳ Please wait 10-30 seconds...",
        parse_mode="Markdown"
    )
    
    try:
        # Generate image
        image_data = await generate_image(
            prompt=prompt,
            width=width,
            height=height,
            style=style_id,
            negative=negative_prompt
        )
        
        if image_data:
            # Send generated image
            input_file = BufferedInputFile(image_data, filename="generated_image.png")
            
            await message.reply_photo(
                photo=input_file,
                caption=(
                    f"🎨 **Image Generated!**\n\n"
                    f"📝 Prompt: {prompt[:200]}{'...' if len(prompt) > 200 else ''}\n"
                    f"📐 Size: {size_data['label']}\n"
                    f"🎨 Style: {IMAGE_STYLES[style_id]['label']}\n\n"
                    f"🔄 Send a new prompt to generate again!\n"
                    f"⚙️ Use /settings to change preferences."
                ),
                parse_mode="Markdown"
            )
            
            # Delete processing message
            await processing_msg.delete()
            
        else:
            # If generation failed, create placeholder
            placeholder_data = create_placeholder_image(width, height, prompt)
            input_file = BufferedInputFile(placeholder_data, filename="placeholder.png")
            
            await message.reply_photo(
                photo=input_file,
                caption=(
                    "⚠️ **Demo Mode**\n\n"
                    "This is a placeholder image.\n\n"
                    "To get real AI-generated images:\n"
                    "1. Add a Hugging Face API key\n"
                    "2. Or use the free version with rate limits\n\n"
                    "Try again with a different prompt!"
                ),
                parse_mode="Markdown"
            )
            
            await processing_msg.delete()
            
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        await message.reply(
            "❌ **Generation Failed**\n\n"
            "Something went wrong. Please try again.\n\n"
            "Tips:\n"
            "• Try a shorter prompt\n"
            "• Use simpler language\n"
            "• Try again in a few seconds"
        )
        await processing_msg.delete()
    
    await state.clear()


@dp.message()
async def handle_other_messages(message: Message):
    """Handle other messages"""
    await message.reply(
        "❓ I don't understand that.\n\n"
        "Use /start to see the menu or /help for assistance."
    )


# ==================== CALLBACK HANDLERS ====================

@dp.callback_query()
async def handle_callback(callback_query: CallbackQuery, state: FSMContext):
    """Handle inline button callbacks"""
    await callback_query.answer()
    
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    # Initialize user data if needed
    if user_id not in user_data:
        user_data[user_id] = {
            "settings": {
                "size": "square",
                "style": "realistic",
                "negative": "none",
            }
        }
    
    # --- Main Menu ---
    if data == "generate":
        await callback_query.message.edit_text(
            "🎨 **Describe what you want to generate!**\n\n"
            "Examples:\n"
            "• \"A beautiful sunset over the ocean\"\n"
            "• \"A cute cat wearing a wizard hat\"\n"
            "• \"A futuristic city with neon lights\"\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown"
        )
        await state.set_state(ImageGenStates.waiting_for_prompt)
        
    elif data == "settings":
        await callback_query.message.edit_text(
            "⚙️ **Settings**\n\n"
            "Customize your image generation preferences:",
            reply_markup=get_settings_keyboard(user_id),
            parse_mode="Markdown"
        )
        
    elif data == "help":
        help_text = (
            "❓ **Help & Support**\n\n"
            "📖 **How to use:**\n"
            "1. Click 'Generate Image' or send /generate\n"
            "2. Type a detailed description\n"
            "3. Wait for your image to generate\n\n"
            "🎨 **Tips for better results:**\n"
            "• Be specific and detailed\n"
            "• Include style, colors, mood\n"
            "• Mention lighting and composition\n"
            "• Use 5-20 words for best results\n\n"
            "⚙️ **Customization:**\n"
            "• Change image size (Square, Portrait, etc.)\n"
            "• Select art style (Realistic, Anime, etc.)\n"
            "• Add negative prompts to avoid issues"
        )
        await callback_query.message.edit_text(
            help_text,
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🔙 Back", callback_data="back_to_menu")
            ).as_markup(),
            parse_mode="Markdown"
        )
        
    elif data == "ideas":
        await callback_query.message.edit_text(
            "💡 **Need inspiration?**\n\n"
            "Click any idea below to generate an image:",
            reply_markup=get_ideas_keyboard(),
            parse_mode="Markdown"
        )
    
    # --- Settings ---
    elif data == "change_size":
        await callback_query.message.edit_text(
            "📐 **Select Image Size**\n\n"
            "Choose the size for your generated images:",
            reply_markup=get_size_keyboard(),
            parse_mode="Markdown"
        )
        
    elif data == "change_style":
        await callback_query.message.edit_text(
            "🎨 **Select Art Style**\n\n"
            "Choose the style for your generated images:",
            reply_markup=get_style_keyboard(),
            parse_mode="Markdown"
        )
        
    elif data == "change_negative":
        await callback_query.message.edit_text(
            "🚫 **Select Negative Prompt**\n\n"
            "Choose what to avoid in your images:",
            reply_markup=get_negative_keyboard(),
            parse_mode="Markdown"
        )
        
    elif data == "reset_settings":
        user_data[user_id]["settings"] = {
            "size": "square",
            "style": "realistic",
            "negative": "none",
        }
        await callback_query.message.edit_text(
            "✅ **Settings Reset!**\n\n"
            "All settings have been reset to default.",
            reply_markup=get_settings_keyboard(user_id),
            parse_mode="Markdown"
        )
    
    # --- Size Selection ---
    elif data.startswith("size_"):
        size_id = data.replace("size_", "")
        if size_id in IMAGE_SIZES:
            user_data[user_id]["settings"]["size"] = size_id
            await callback_query.message.edit_text(
                f"✅ **Size Updated!**\n\n"
                f"New size: {IMAGE_SIZES[size_id]['label']}\n\n"
                "Your future images will be generated in this size.",
                reply_markup=get_settings_keyboard(user_id),
                parse_mode="Markdown"
            )
    
    # --- Style Selection ---
    elif data.startswith("style_"):
        style_id = data.replace("style_", "")
        if style_id in IMAGE_STYLES:
            user_data[user_id]["settings"]["style"] = style_id
            await callback_query.message.edit_text(
                f"✅ **Style Updated!**\n\n"
                f"New style: {IMAGE_STYLES[style_id]['label']}\n\n"
                "Your future images will use this style.",
                reply_markup=get_settings_keyboard(user_id),
                parse_mode="Markdown"
            )
    
    # --- Negative Prompt Selection ---
    elif data.startswith("negative_"):
        negative_id = data.replace("negative_", "")
        if negative_id in NEGATIVE_PROMPTS:
            user_data[user_id]["settings"]["negative"] = negative_id
            await callback_query.message.edit_text(
                f"✅ **Negative Prompt Updated!**\n\n"
                f"New negative prompt: {NEGATIVE_PROMPTS[negative_id]['label']}\n\n"
                "Your future images will avoid these elements.",
                reply_markup=get_settings_keyboard(user_id),
                parse_mode="Markdown"
            )
    
    # --- Ideas ---
    elif data.startswith("idea_"):
        # Get the prompt from the callback data
        prompt = data.replace("idea_", "")[:100]
        
        # Get user settings
        settings = user_data.get(user_id, {}).get("settings", {})
        size_id = settings.get("size", "square")
        style_id = settings.get("style", "realistic")
        negative_id = settings.get("negative", "none")
        
        size_data = IMAGE_SIZES.get(size_id, IMAGE_SIZES["square"])
        negative_data = NEGATIVE_PROMPTS.get(negative_id, NEGATIVE_PROMPTS["none"])
        
        width = size_data["width"]
        height = size_data["height"]
        negative_prompt = negative_data["prompt"]
        
        # Send processing message
        await callback_query.message.edit_text(
            f"🎨 **Generating image from idea...**\n\n"
            f"📝 Prompt: {prompt}\n"
            f"⏳ Please wait...",
            parse_mode="Markdown"
        )
        
        # Generate image
        image_data = await generate_image(
            prompt=prompt,
            width=width,
            height=height,
            style=style_id,
            negative=negative_prompt
        )
        
        if image_data:
            input_file = BufferedInputFile(image_data, filename="generated_image.png")
            await callback_query.message.reply_photo(
                photo=input_file,
                caption=(
                    f"🎨 **Image Generated!**\n\n"
                    f"📝 Prompt: {prompt}\n"
                    f"📐 Size: {size_data['label']}\n"
                    f"🎨 Style: {IMAGE_STYLES[style_id]['label']}\n\n"
                    f"💡 Try another idea or create your own!"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text="💡 More Ideas", callback_data="ideas"),
                    InlineKeyboardButton(text="🎨 Generate", callback_data="generate")
                ).as_markup()
            )
        else:
            placeholder_data = create_placeholder_image(width, height, prompt)
            input_file = BufferedInputFile(placeholder_data, filename="placeholder.png")
            await callback_query.message.reply_photo(
                photo=input_file,
                caption=(
                    "⚠️ **Demo Mode**\n\n"
                    "This is a placeholder image.\n"
                    "For real AI images, add an API key.",
                ),
                parse_mode="Markdown"
            )
    
    # --- Navigation ---
    elif data == "back_to_menu":
        await callback_query.message.edit_text(
            "🎨 **Main Menu**\n\n"
            "What would you like to do?",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )


# ==================== MAIN ====================

async def main():
    """Main entry point"""
    try:
        logger.info("=" * 50)
        logger.info(f"🎨 {BOT_NAME} is starting...")
        logger.info(f"🤖 Username: @{BOT_USERNAME}")
        logger.info(f"📦 Version: {BOT_VERSION}")
        logger.info("=" * 50)
        
        # Check API key
        if HUGGINGFACE_API_KEY:
            logger.info("✅ Hugging Face API key found!")
        else:
            logger.warning("⚠️ No Hugging Face API key found. Using demo mode.")
        
        # Delete webhook
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Start polling
        logger.info("📡 Starting polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Critical error: {str(e)}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}")
