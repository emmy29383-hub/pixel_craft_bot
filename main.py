"""
🎨 Pixel Craft Bot - AI Image Generator
Generates REAL AI images using Pollinations.ai (FREE - No API Key Needed!)
Features: Image Generation, Conversion, Resize, Usage Tracking
"""

import os
import io
import asyncio
import aiohttp
import tempfile
from datetime import datetime, timedelta
from PIL import Image, ImageEnhance, ImageFilter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    ContextTypes, 
    filters
)

# ==================== CONFIGURATION ====================

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN environment variable not set!")

BOT_NAME = "Pixel Craft Bot"
BOT_USERNAME = "pixel_craft_bot"
BOT_VERSION = "2.0.0"

# Free AI Image Generation API (Pollinations.ai - no API key needed)
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"

# User usage tracking (in-memory, resets daily)
user_usage = {}
DAILY_LIMIT = 15  # Increased from 10 to 15

# Supported image sizes
IMAGE_SIZES = {
    "512": "512x512",
    "768": "768x768",
    "1024": "1024x1024",
    "portrait": "768x1024",
    "landscape": "1024x768",
}

# Art styles for prompt enhancement
ART_STYLES = {
    "realistic": "photorealistic, highly detailed, 8k",
    "anime": "anime style, vibrant colors, beautiful illustration",
    "digital": "digital art, concept art, smooth rendering",
    "cartoon": "cartoon style, colorful, vector art",
    "oil": "oil painting, canvas texture, artistic",
    "watercolor": "watercolor painting, soft colors, artistic",
    "cyberpunk": "cyberpunk, neon lights, futuristic",
    "fantasy": "fantasy art, magical, epic scene",
}

# ==================== HELPER FUNCTIONS ====================

def get_user_usage(user_id: str) -> int:
    """Get user's daily usage count"""
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{today}"
    return user_usage.get(key, 0)

def increment_user_usage(user_id: str) -> int:
    """Increment user's usage count"""
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{today}"
    user_usage[key] = user_usage.get(key, 0) + 1
    return user_usage[key]

def get_remaining_usage(user_id: str) -> int:
    """Get remaining usage for today"""
    return max(0, DAILY_LIMIT - get_user_usage(user_id))

def get_user_status(user_id: str) -> str:
    """Get user's usage status as emoji"""
    used = get_user_usage(user_id)
    remaining = DAILY_LIMIT - used
    
    if remaining <= 0:
        return "🔴"
    elif remaining <= 3:
        return "🟡"
    else:
        return "🟢"

# ==================== KEYBOARD FUNCTIONS ====================

def get_main_keyboard():
    """Create main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎨 Generate Image", callback_data="generate")],
        [InlineKeyboardButton("🔄 Convert Format", callback_data="convert")],
        [InlineKeyboardButton("📐 Resize Image", callback_data="resize")],
        [InlineKeyboardButton("💡 Prompt Ideas", callback_data="ideas")],
        [InlineKeyboardButton("📊 Usage", callback_data="usage")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_size_keyboard():
    """Create size selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("🟦 512x512", callback_data="size_512"), 
         InlineKeyboardButton("🟧 768x768", callback_data="size_768")],
        [InlineKeyboardButton("🟩 1024x1024", callback_data="size_1024")],
        [InlineKeyboardButton("📱 Portrait", callback_data="size_portrait"),
         InlineKeyboardButton("🖥️ Landscape", callback_data="size_landscape")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_format_keyboard():
    """Create format selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("🟦 PNG", callback_data="format_png"), 
         InlineKeyboardButton("🟨 JPG", callback_data="format_jpg")],
        [InlineKeyboardButton("🟩 WEBP", callback_data="format_webp"),
         InlineKeyboardButton("🟪 BMP", callback_data="format_bmp")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_style_keyboard():
    """Create art style selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("📷 Realistic", callback_data="style_realistic"),
         InlineKeyboardButton("🎨 Anime", callback_data="style_anime")],
        [InlineKeyboardButton("💻 Digital", callback_data="style_digital"),
         InlineKeyboardButton("✏️ Cartoon", callback_data="style_cartoon")],
        [InlineKeyboardButton("🖌️ Oil", callback_data="style_oil"),
         InlineKeyboardButton("💧 Watercolor", callback_data="style_watercolor")],
        [InlineKeyboardButton("💜 Cyberpunk", callback_data="style_cyberpunk"),
         InlineKeyboardButton("🧙 Fantasy", callback_data="style_fantasy")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_ideas_keyboard():
    """Create prompt ideas keyboard"""
    keyboard = [
        [InlineKeyboardButton("🌅 Sunset", callback_data="idea_sunset"),
         InlineKeyboardButton("🏔️ Mountain", callback_data="idea_mountain")],
        [InlineKeyboardButton("🌊 Ocean", callback_data="idea_ocean"),
         InlineKeyboardButton("🏙️ City", callback_data="idea_city")],
        [InlineKeyboardButton("🐱 Cat", callback_data="idea_cat"),
         InlineKeyboardButton("🐉 Dragon", callback_data="idea_dragon")],
        [InlineKeyboardButton("🚀 Space", callback_data="idea_space"),
         InlineKeyboardButton("🌸 Garden", callback_data="idea_garden")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_generate_keyboard():
    """Create generate options keyboard"""
    keyboard = [
        [InlineKeyboardButton("🔄 Try Different Size", callback_data="size_menu")],
        [InlineKeyboardButton("🎨 Change Style", callback_data="style_menu")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = str(user.id)
    remaining = get_remaining_usage(user_id)
    status = get_user_status(user_id)
    
    welcome_message = (
        f"🎨 **Welcome to {BOT_NAME}!**\n\n"
        f"👋 Hello @{user.username or user.first_name}!\n\n"
        f"I generate **REAL AI images** from your text descriptions.\n"
        f"⚡ Powered by **Pollinations.ai** (FREE, no API key needed!)\n\n"
        f"📊 **Daily Usage**: {status} {remaining} images remaining today\n\n"
        f"✨ **Features:**\n"
        f"• 🎨 AI Image Generation\n"
        f"• 🔄 Image Format Conversion\n"
        f"• 📐 Image Resize\n"
        f"• 💡 Prompt Ideas\n"
        f"• 📊 Usage Tracking\n\n"
        f"⬇️ Use the buttons below to get started!"
    )
    
    await update.message.reply_text(
        welcome_message, 
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        f"📖 **{BOT_NAME} User Guide**\n\n"
        "**🎨 Generate AI Images**\n"
        "• Click 'Generate Image'\n"
        "• Choose a style or use default\n"
        "• Type your prompt\n"
        "• Wait 10-20 seconds\n\n"
        "**🔄 Convert Image Format**\n"
        "• Click 'Convert Format'\n"
        "• Send any image\n"
        "• Choose output format (PNG, JPG, WEBP, BMP)\n\n"
        "**📐 Resize Image**\n"
        "• Click 'Resize Image'\n"
        "• Send any image\n"
        "• Choose new size\n\n"
        "**💰 Daily Limit**\n"
        f"• {DAILY_LIMIT} images per day\n"
        "• Resets at midnight UTC\n\n"
        "**Commands**\n"
        "/start - Main menu\n"
        "/help - This help\n"
        "/usage - Check usage\n"
        "/about - About the bot"
    )
    
    await update.message.reply_text(
        help_text, 
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command"""
    about_text = (
        f"🤖 **{BOT_NAME}**\n\n"
        f"📦 Version: {BOT_VERSION}\n"
        f"👤 Username: @{BOT_USERNAME}\n\n"
        "🎨 **AI Image Generation**\n"
        "Powered by Pollinations.ai\n"
        "**FREE - No API Key Needed!**\n\n"
        "✨ **Features:**\n"
        "• 8 Art Styles\n"
        "• 5 Image Sizes\n"
        "• Format Conversion (PNG, JPG, WEBP, BMP)\n"
        "• Image Resize\n"
        "• Daily Usage Tracking\n"
        "• Prompt Ideas\n\n"
        "🔒 **Privacy:**\n"
        "No images are permanently stored.\n\n"
        "⭐ Made with ❤️ for Telegram"
    )
    
    await update.message.reply_text(
        about_text, 
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /usage command"""
    user_id = str(update.effective_user.id)
    used = get_user_usage(user_id)
    remaining = DAILY_LIMIT - used
    status = get_user_status(user_id)
    
    # Create usage bar
    bar_length = 10
    filled = int((used / DAILY_LIMIT) * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    status_text = (
        f"📊 **Your Usage**\n\n"
        f"Status: {status}\n"
        f"Used: {used}/{DAILY_LIMIT}\n"
        f"Remaining: {remaining}/{DAILY_LIMIT}\n\n"
        f"Progress: [{bar}] {int((used/DAILY_LIMIT)*100)}%\n\n"
        f"🔄 Resets at midnight UTC"
    )
    
    await update.message.reply_text(
        status_text, 
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# ==================== CALLBACK QUERY HANDLERS ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    
    # --- MAIN MENU ACTIONS ---
    
    if data == "generate":
        remaining = get_remaining_usage(user_id)
        if remaining <= 0:
            await query.edit_message_text(
                "⚠️ **Daily limit reached!**\n\n"
                f"You've used {DAILY_LIMIT} images today.\n"
                "Come back tomorrow for more 🎨",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Show style selection first
        await query.edit_message_text(
            "🎨 **Choose an Art Style**\n\n"
            "Select a style for your image:",
            parse_mode="Markdown",
            reply_markup=get_style_keyboard()
        )
        context.user_data["action"] = "select_style"
        
    elif data == "resize":
        await query.edit_message_text(
            "📐 **Send me an image**\n\n"
            "Then choose the new size:",
            parse_mode="Markdown",
            reply_markup=get_size_keyboard()
        )
        context.user_data["action"] = "resize"
        
    elif data == "convert":
        await query.edit_message_text(
            "🔄 **Send me an image**\n\n"
            "Choose the output format:",
            parse_mode="Markdown",
            reply_markup=get_format_keyboard()
        )
        context.user_data["action"] = "convert"
        
    elif data == "ideas":
        await query.edit_message_text(
            "💡 **Prompt Ideas**\n\n"
            "Click any idea to generate an image instantly:",
            parse_mode="Markdown",
            reply_markup=get_ideas_keyboard()
        )
        context.user_data["action"] = "ideas"
        
    elif data == "usage":
        used = get_user_usage(user_id)
        remaining = DAILY_LIMIT - used
        status = get_user_status(user_id)
        
        bar_length = 10
        filled = int((used / DAILY_LIMIT) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        await query.edit_message_text(
            f"📊 **Your Usage**\n\n"
            f"Status: {status}\n"
            f"Used: {used}/{DAILY_LIMIT}\n"
            f"Remaining: {remaining}/{DAILY_LIMIT}\n\n"
            f"Progress: [{bar}] {int((used/DAILY_LIMIT)*100)}%\n\n"
            f"🔄 Resets at midnight UTC",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    elif data == "help":
        help_text = (
            f"📖 **{BOT_NAME} User Guide**\n\n"
            "**🎨 Generate AI Images**\n"
            "• Click 'Generate Image'\n"
            "• Choose a style\n"
            "• Type your prompt\n"
            "• Wait 10-20 seconds\n\n"
            "**🔄 Convert Format**\n"
            "• Click 'Convert Format'\n"
            "• Send image\n"
            "• Choose output format\n\n"
            "**📐 Resize Image**\n"
            "• Click 'Resize Image'\n"
            "• Send image\n"
            "• Choose new size\n\n"
            f"**💰 Daily Limit**: {DAILY_LIMIT} images/day"
        )
        await query.edit_message_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    elif data == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\n"
            "What would you like to do?",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["action"] = None
        context.user_data["style"] = None
        
    elif data == "size_menu":
        await query.edit_message_text(
            "📐 **Choose Image Size**\n\n"
            "Select the size for your generated image:",
            parse_mode="Markdown",
            reply_markup=get_size_keyboard()
        )
        
    elif data == "style_menu":
        await query.edit_message_text(
            "🎨 **Choose an Art Style**\n\n"
            "Select a style for your image:",
            parse_mode="Markdown",
            reply_markup=get_style_keyboard()
        )
        context.user_data["action"] = "select_style"
    
    # --- STYLE SELECTION ---
    
    elif data.startswith("style_"):
        style = data.replace("style_", "")
        context.user_data["style"] = style
        context.user_data["action"] = "generate"
        
        style_names = {
            "realistic": "📷 Realistic",
            "anime": "🎨 Anime",
            "digital": "💻 Digital Art",
            "cartoon": "✏️ Cartoon",
            "oil": "🖌️ Oil Painting",
            "watercolor": "💧 Watercolor",
            "cyberpunk": "💜 Cyberpunk",
            "fantasy": "🧙 Fantasy"
        }
        
        remaining = get_remaining_usage(user_id)
        
        await query.edit_message_text(
            f"✅ **Style Selected:** {style_names.get(style, style)}\n\n"
            f"📊 {remaining} images remaining today\n\n"
            "📝 **Now send me your prompt!**\n\n"
            "Examples:\n"
            "• 'A beautiful sunset over mountains'\n"
            "• 'A cute cat wearing a wizard hat'\n"
            "• 'A futuristic cyberpunk city at night'\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown",
            reply_markup=get_generate_keyboard()
        )
    
    # --- SIZE SELECTION ---
    
    elif data.startswith("size_"):
        size_key = data.replace("size_", "")
        size_map = {
            "512": "512x512",
            "768": "768x768",
            "1024": "1024x1024",
            "portrait": "768x1024",
            "landscape": "1024x768"
        }
        context.user_data["size"] = size_map.get(size_key, "512x512")
        
        # Check what action we're in
        action = context.user_data.get("action", "")
        
        if action == "resize":
            context.user_data["action"] = "resize_ready"
            await query.edit_message_text(
                f"✅ Size set to **{context.user_data['size']}**\n\n"
                "📸 Now send me the image you want to resize!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            context.user_data["action"] = "generate_ready"
            await query.edit_message_text(
                f"✅ Size set to **{context.user_data['size']}**\n\n"
                "📝 Now send me your prompt!",
                parse_mode="Markdown",
                reply_markup=get_generate_keyboard()
            )
    
    # --- FORMAT SELECTION ---
    
    elif data.startswith("format_"):
        format_map = {
            "format_png": "PNG",
            "format_jpg": "JPG",
            "format_webp": "WEBP",
            "format_bmp": "BMP"
        }
        context.user_data["format"] = format_map.get(data, "PNG")
        context.user_data["action"] = "convert_ready"
        
        await query.edit_message_text(
            f"✅ Format set to **{context.user_data['format']}**\n\n"
            "📸 Now send me an image to convert!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    # --- IDEA GENERATION ---
    
    elif data.startswith("idea_"):
        idea_map = {
            "idea_sunset": "A beautiful sunset over the ocean with golden clouds and palm trees",
            "idea_mountain": "A majestic mountain peak at sunrise with snow and dramatic clouds",
            "idea_ocean": "A peaceful ocean scene with waves and a beautiful sunset",
            "idea_city": "A futuristic cyberpunk city with neon lights and flying cars at night",
            "idea_cat": "A cute cat sitting in a magical garden with glowing flowers and butterflies",
            "idea_dragon": "A majestic dragon flying over a fantasy castle with fire and magic",
            "idea_space": "A beautiful cosmic galaxy with stars, nebula, and colorful planets",
            "idea_garden": "A peaceful Japanese garden with cherry blossoms, koi pond, and pagoda"
        }
        
        prompt = idea_map.get(data, "A beautiful scene")
        context.user_data["prompt"] = prompt
        
        # Check usage
        if get_user_usage(user_id) >= DAILY_LIMIT:
            await query.edit_message_text(
                "⚠️ **Daily limit reached!**\n\n"
                f"You've used {DAILY_LIMIT} images today.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Get size and style
        size = context.user_data.get("size", "512x512")
        style = context.user_data.get("style", "realistic")
        
        # Generate image from idea
        await generate_and_send_image(
            update, 
            context, 
            prompt, 
            size, 
            style,
            query.message
        )

# ==================== IMAGE GENERATION ====================

async def generate_image(prompt: str, size: str = "512x512", style: str = "realistic"):
    """Generate image using Pollinations.ai with style enhancement"""
    try:
        # Add style to prompt
        style_prompt = ART_STYLES.get(style, ART_STYLES["realistic"])
        enhanced_prompt = f"{prompt}, {style_prompt}"
        
        # Clean and format prompt
        clean_prompt = enhanced_prompt.strip().replace(" ", "%20").replace(",", "%2C")
        width, height = size.split("x")
        
        # Pollinations.ai URL with enhanced settings
        url = (
            f"https://image.pollinations.ai/prompt/{clean_prompt}"
            f"?width={width}&height={height}"
            f"&nologo=true"
            f"&seed={int(datetime.now().timestamp())}"
            f"&enhance=true"
        )
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=45) as response:
                if response.status == 200:
                    image_data = await response.read()
                    
                    # Optional: Enhance image quality
                    try:
                        img = Image.open(io.BytesIO(image_data))
                        enhancer = ImageEnhance.Contrast(img)
                        img = enhancer.enhance(1.1)
                        enhancer = ImageEnhance.Color(img)
                        img = enhancer.enhance(1.05)
                        
                        output = io.BytesIO()
                        img.save(output, format='PNG', optimize=True)
                        output.seek(0)
                        return output.read()
                    except:
                        return image_data
                else:
                    print(f"API Error: {response.status}")
                    return None
                    
    except asyncio.TimeoutError:
        print("Generation timeout")
        return None
    except Exception as e:
        print(f"Generation error: {e}")
        return None

async def generate_and_send_image(update, context, prompt, size, style, reply_to=None):
    """Generate image and send to user"""
    user_id = str(update.effective_user.id)
    
    # Send processing message
    style_names = {
        "realistic": "📷 Realistic",
        "anime": "🎨 Anime",
        "digital": "💻 Digital",
        "cartoon": "✏️ Cartoon",
        "oil": "🖌️ Oil",
        "watercolor": "💧 Watercolor",
        "cyberpunk": "💜 Cyberpunk",
        "fantasy": "🧙 Fantasy"
    }
    
    processing_text = (
        f"🎨 **Generating your image...**\n\n"
        f"📝 Prompt: *{prompt[:60]}{'...' if len(prompt) > 60 else ''}*\n"
        f"🎨 Style: {style_names.get(style, style)}\n"
        f"📐 Size: {size}\n\n"
        f"⏳ This may take 10-20 seconds..."
    )
    
    if reply_to:
        processing_msg = await reply_to.edit_text(
            processing_text,
            parse_mode="Markdown"
        )
    else:
        processing_msg = await update.message.reply_text(
            processing_text,
            parse_mode="Markdown"
        )
    
    # Generate image
    image_data = await generate_image(prompt, size, style)
    
    if image_data:
        # Increment usage
        used = increment_user_usage(user_id)
        remaining = DAILY_LIMIT - used
        
        await processing_msg.delete()
        
        # Send generated image
        caption = (
            f"✨ **Image Generated!**\n\n"
            f"📝 *{prompt[:100]}{'...' if len(prompt) > 100 else ''}*\n"
            f"🎨 Style: {style_names.get(style, style)}\n"
            f"📐 Size: {size}\n"
            f"📊 {used}/{DAILY_LIMIT} used today\n"
            f"{'🔴' if remaining <= 0 else '🟢'} {remaining} remaining"
        )
        
        await update.message.reply_photo(
            photo=io.BytesIO(image_data),
            caption=caption,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await processing_msg.edit_text(
            "❌ **Failed to generate image**\n\n"
            "Please try:\n"
            "• A different prompt\n"
            "• Shorter description\n"
            "• Wait a few seconds and retry",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== IMAGE PROCESSING ====================

async def resize_image(image_data: bytes, target_size: str):
    """Resize image to target size"""
    try:
        # Parse size
        if "x" in target_size:
            width, height = map(int, target_size.split("x"))
        else:
            size = int(target_size)
            width, height = size, size
            
        # Open image
        img = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            img = img.convert('RGB')
            
        # Resize with high quality
        img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = io.BytesIO()
        img_resized.save(output, format='PNG', optimize=True)
        output.seek(0)
        
        return output.read()
    except Exception as e:
        print(f"Resize error: {e}")
        return None

async def convert_image(image_data: bytes, target_format: str):
    """Convert image to different format"""
    try:
        # Open image
        img = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB for JPG
        if target_format.upper() == 'JPG' and img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif target_format.upper() == 'JPG':
            img = img.convert('RGB')
        
        # Save to bytes
        output = io.BytesIO()
        format_type = 'JPEG' if target_format.upper() == 'JPG' else target_format.upper()
        img.save(output, format=format_type, optimize=True)
        output.seek(0)
        
        return output.read()
    except Exception as e:
        print(f"Conversion error: {e}")
        return None

# ==================== MESSAGE HANDLERS ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = str(update.effective_user.id)
    action = context.user_data.get("action", "")
    prompt = update.message.text.strip()
    
    # Check for cancel
    if prompt.lower() == "/cancel":
        context.user_data["action"] = None
        await update.message.reply_text(
            "✅ **Cancelled**\n\n"
            "Operation cancelled. Use /start for main menu.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Handle generation
    if action in ["generate", "generate_ready"]:
        # Check usage
        if get_user_usage(user_id) >= DAILY_LIMIT:
            await update.message.reply_text(
                "⚠️ **Daily limit reached!**\n\n"
                f"You've used {DAILY_LIMIT} images today.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Get size and style
        size = context.user_data.get("size", "512x512")
        style = context.user_data.get("style", "realistic")
        
        await generate_and_send_image(update, context, prompt, size, style)
        
    elif action == "convert_ready":
        await update.message.reply_text(
            "📸 **Please send an image file**\n\n"
            "I need an actual image to convert.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    elif action == "resize_ready":
        await update.message.reply_text(
            "📸 **Please send an image file**\n\n"
            "I need an actual image to resize.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    else:
        # Default response
        await update.message.reply_text(
            "👋 **Use the buttons below!**\n\n"
            "Click 'Generate Image' to create AI art 🎨\n"
            "Or send me an image to convert/resize 📸",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image messages"""
    user_id = str(update.effective_user.id)
    action = context.user_data.get("action", "")
    
    try:
        # Get the image file
        photo = await update.message.photo[-1].get_file()
        image_data = await photo.download_as_bytearray()
        
        if action == "convert" or action == "convert_ready":
            # Get target format
            target_format = context.user_data.get("format", "PNG")
            
            await update.message.reply_text(
                f"🔄 **Converting to {target_format}...**",
                parse_mode="Markdown"
            )
            
            converted = await convert_image(image_data, target_format)
            
            if converted:
                await update.message.reply_document(
                    document=io.BytesIO(converted),
                    filename=f"converted.{target_format.lower()}",
                    caption=f"✅ **Converted to {target_format}**",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ **Conversion failed**\n\n"
                    "Please try a different image or format.",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
                
        elif action == "resize" or action == "resize_ready":
            # Get target size
            target_size = context.user_data.get("size", "512x512")
            
            await update.message.reply_text(
                f"📐 **Resizing to {target_size}...**",
                parse_mode="Markdown"
            )
            
            resized = await resize_image(image_data, target_size)
            
            if resized:
                await update.message.reply_document(
                    document=io.BytesIO(resized),
                    filename=f"resized_{target_size.replace('x', 'X')}.png",
                    caption=f"✅ **Resized to {target_size}**",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ **Resize failed**\n\n"
                    "Please try a different image or size.",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
        else:
            # Just received an image - show options
            await update.message.reply_text(
                "🖼️ **Image received!**\n\n"
                "Use the buttons below to:\n"
                "• 🔄 Convert format\n"
                "• 📐 Resize image",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Convert Format", callback_data="convert")],
                    [InlineKeyboardButton("📐 Resize Image", callback_data="resize")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
                ])
            )
            
    except Exception as e:
        print(f"Image handling error: {e}")
        await update.message.reply_text(
            "❌ **Error processing image**\n\n"
            "Please try again with a different image.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== MAIN FUNCTION ====================

async def post_init(application):
    """Actions after bot starts"""
    print("=" * 50)
    print(f"🎨 {BOT_NAME} Started!")
    print(f"🤖 Username: @{BOT_USERNAME}")
    print(f"📊 Daily Limit: {DAILY_LIMIT} images per user")
    print("=" * 50)

def main():
    """Start the bot"""
    print(f"🚀 Starting {BOT_NAME}...")
    
    # Build application
    application = ApplicationBuilder() \
        .token(BOT_TOKEN) \
        .post_init(post_init) \
        .build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("usage", usage_command))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    # Start the bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
