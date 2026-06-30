"""
🎨 Pixel Craft Bot - AI Image Generator
Generates REAL AI images using Pollinations.ai (FREE - No API Key Needed!)
Features: Image Generation, Conversion, Resize, Usage Tracking
"""

import os
import io
import asyncio
import aiohttp
from datetime import datetime
from PIL import Image, ImageEnhance
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
DAILY_LIMIT = 15

# User usage tracking
user_usage = {}

# Art Styles
ART_STYLES = {
    "realistic": "photorealistic, highly detailed, 8k",
    "anime": "anime style, vibrant colors, beautiful illustration",
    "digital": "digital art, concept art, smooth rendering",
    "cartoon": "cartoon style, colorful, vector art",
    "oil": "oil painting, canvas texture, artistic",
    "watercolor": "watercolor painting, soft colors, artistic",
    "cyberpunk": "cyberpunk, neon lights, futuristic",
    "fantasy": "fantasy art, magical, epic scene"
}

# ==================== HELPER FUNCTIONS ====================

def get_user_usage(user_id: str) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return user_usage.get(f"{user_id}_{today}", 0)

def increment_user_usage(user_id: str) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{today}"
    user_usage[key] = user_usage.get(key, 0) + 1
    return user_usage[key]

def get_remaining_usage(user_id: str) -> int:
    return max(0, DAILY_LIMIT - get_user_usage(user_id))

# ==================== KEYBOARDS ====================

def get_main_keyboard():
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
    keyboard = [
        [InlineKeyboardButton("🟦 PNG", callback_data="format_png"),
         InlineKeyboardButton("🟨 JPG", callback_data="format_jpg")],
        [InlineKeyboardButton("🟩 WEBP", callback_data="format_webp"),
         InlineKeyboardButton("🟪 BMP", callback_data="format_bmp")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_style_keyboard():
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
    keyboard = [
        [InlineKeyboardButton("🔄 Try Different Size", callback_data="size_menu")],
        [InlineKeyboardButton("🎨 Change Style", callback_data="style_menu")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    remaining = get_remaining_usage(user_id)
    
    welcome = (
        f"🎨 **Welcome to {BOT_NAME}!**\n\n"
        f"👋 Hello @{user.username or user.first_name}!\n\n"
        f"I generate **REAL AI images** from your text descriptions.\n"
        f"⚡ Powered by **Pollinations.ai** (FREE!)\n\n"
        f"📊 **Daily Limit**: {remaining} images remaining today\n\n"
        f"✨ **Features:**\n"
        f"• 🎨 AI Image Generation\n"
        f"• 🔄 Image Conversion\n"
        f"• 📐 Image Resize\n"
        f"• 💡 Prompt Ideas\n\n"
        f"⬇️ Use the buttons below!"
    )
    
    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        f"**💰 Daily Limit**: {DAILY_LIMIT} images/day\n\n"
        "**Commands:**\n"
        "/start - Main menu\n"
        "/help - This help\n"
        "/usage - Check usage"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    used = get_user_usage(user_id)
    remaining = DAILY_LIMIT - used
    
    bar = "█" * int((used/DAILY_LIMIT)*10) + "░" * (10 - int((used/DAILY_LIMIT)*10))
    
    status_text = (
        f"📊 **Your Usage**\n\n"
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

# ==================== CALLBACK HANDLERS ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    
    if data == "generate":
        remaining = get_remaining_usage(user_id)
        if remaining <= 0:
            await query.edit_message_text(
                "⚠️ **Daily limit reached!**\n\n"
                f"You've used {DAILY_LIMIT} images today.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        await query.edit_message_text(
            "🎨 **Choose an Art Style**",
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
            "Click any idea to generate:",
            parse_mode="Markdown",
            reply_markup=get_ideas_keyboard()
        )
        context.user_data["action"] = "ideas"
        
    elif data == "usage":
        used = get_user_usage(user_id)
        remaining = DAILY_LIMIT - used
        bar = "█" * int((used/DAILY_LIMIT)*10) + "░" * (10 - int((used/DAILY_LIMIT)*10))
        
        await query.edit_message_text(
            f"📊 **Your Usage**\n\n"
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
            "• Type your prompt\n\n"
            "**🔄 Convert Format**\n"
            "• Click 'Convert Format'\n"
            "• Send image\n"
            "• Choose output format\n\n"
            f"**💰 Daily Limit**: {DAILY_LIMIT} images/day"
        )
        await query.edit_message_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    elif data == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["action"] = None
        
    elif data == "size_menu":
        await query.edit_message_text(
            "📐 **Choose Image Size**",
            parse_mode="Markdown",
            reply_markup=get_size_keyboard()
        )
        
    elif data == "style_menu":
        await query.edit_message_text(
            "🎨 **Choose an Art Style**",
            parse_mode="Markdown",
            reply_markup=get_style_keyboard()
        )
        context.user_data["action"] = "select_style"
        
    # ===== STYLE SELECTION =====
    elif data.startswith("style_"):
        style = data.replace("style_", "")
        context.user_data["style"] = style
        context.user_data["action"] = "generate"
        
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
        
        remaining = get_remaining_usage(user_id)
        
        await query.edit_message_text(
            f"✅ **Style:** {style_names.get(style, style)}\n\n"
            f"📊 {remaining} images remaining\n\n"
            "📝 **Send me your prompt!**\n\n"
            "Examples:\n"
            "• 'A beautiful sunset over mountains'\n"
            "• 'A cute cat wearing a wizard hat'\n\n"
            "Send /cancel to cancel.",
            parse_mode="Markdown",
            reply_markup=get_generate_keyboard()
        )
    
    # ===== SIZE SELECTION =====
    elif data.startswith("size_"):
        size_map = {
            "512": "512x512",
            "768": "768x768",
            "1024": "1024x1024",
            "portrait": "768x1024",
            "landscape": "1024x768"
        }
        size_key = data.replace("size_", "")
        context.user_data["size"] = size_map.get(size_key, "512x512")
        
        action = context.user_data.get("action", "")
        
        if action == "resize":
            context.user_data["action"] = "resize_ready"
            await query.edit_message_text(
                f"✅ Size: **{context.user_data['size']}**\n\n"
                "📸 Now send me the image to resize!",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            context.user_data["action"] = "generate_ready"
            await query.edit_message_text(
                f"✅ Size: **{context.user_data['size']}**\n\n"
                "📝 Now send me your prompt!",
                parse_mode="Markdown",
                reply_markup=get_generate_keyboard()
            )
    
    # ===== FORMAT SELECTION =====
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
            f"✅ Format: **{context.user_data['format']}**\n\n"
            "📸 Now send me an image to convert!",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    
    # ===== IDEAS =====
    elif data.startswith("idea_"):
        idea_map = {
            "idea_sunset": "A beautiful sunset over the ocean with golden clouds",
            "idea_mountain": "A majestic mountain peak at sunrise with snow",
            "idea_ocean": "A peaceful ocean scene with waves and sunset",
            "idea_city": "A futuristic cyberpunk city with neon lights at night",
            "idea_cat": "A cute cat sitting in a magical garden with glowing flowers",
            "idea_dragon": "A majestic dragon flying over a fantasy castle",
            "idea_space": "A beautiful cosmic galaxy with stars and planets",
            "idea_garden": "A peaceful Japanese garden with cherry blossoms"
        }
        
        prompt = idea_map.get(data, "A beautiful scene")
        context.user_data["prompt"] = prompt
        
        if get_user_usage(user_id) >= DAILY_LIMIT:
            await query.edit_message_text(
                "⚠️ **Daily limit reached!**",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        size = context.user_data.get("size", "512x512")
        style = context.user_data.get("style", "realistic")
        
        await generate_and_send(update, context, prompt, size, style, query.message)

# ==================== IMAGE GENERATION ====================

async def generate_image(prompt: str, size: str = "512x512", style: str = "realistic"):
    try:
        style_prompt = ART_STYLES.get(style, ART_STYLES["realistic"])
        enhanced_prompt = f"{prompt}, {style_prompt}"
        
        clean_prompt = enhanced_prompt.strip().replace(" ", "%20").replace(",", "%2C")
        width, height = size.split("x")
        
        url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width={width}&height={height}&nologo=true&seed={int(datetime.now().timestamp())}&enhance=true"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=45) as response:
                if response.status == 200:
                    image_data = await response.read()
                    try:
                        img = Image.open(io.BytesIO(image_data))
                        enhancer = ImageEnhance.Contrast(img)
                        img = enhancer.enhance(1.1)
                        output = io.BytesIO()
                        img.save(output, format='PNG', optimize=True)
                        output.seek(0)
                        return output.read()
                    except:
                        return image_data
                return None
    except:
        return None

async def generate_and_send(update, context, prompt, size, style, reply_to=None):
    user_id = str(update.effective_user.id)
    
    style_names = {
        "realistic": "📷 Realistic", "anime": "🎨 Anime", "digital": "💻 Digital",
        "cartoon": "✏️ Cartoon", "oil": "🖌️ Oil", "watercolor": "💧 Watercolor",
        "cyberpunk": "💜 Cyberpunk", "fantasy": "🧙 Fantasy"
    }
    
    processing_text = (
        f"🎨 **Generating...**\n\n"
        f"📝 {prompt[:60]}{'...' if len(prompt) > 60 else ''}\n"
        f"🎨 {style_names.get(style, style)}\n"
        f"📐 {size}\n\n"
        f"⏳ Please wait..."
    )
    
    if reply_to:
        processing_msg = await reply_to.edit_text(processing_text, parse_mode="Markdown")
    else:
        processing_msg = await update.message.reply_text(processing_text, parse_mode="Markdown")
    
    image_data = await generate_image(prompt, size, style)
    
    if image_data:
        used = increment_user_usage(user_id)
        remaining = DAILY_LIMIT - used
        
        await processing_msg.delete()
        
        await update.message.reply_photo(
            photo=io.BytesIO(image_data),
            caption=(
                f"✨ **Generated!**\n\n"
                f"📝 {prompt[:100]}{'...' if len(prompt) > 100 else ''}\n"
                f"🎨 {style_names.get(style, style)}\n"
                f"📊 {used}/{DAILY_LIMIT} used"
            ),
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await processing_msg.edit_text(
            "❌ **Failed to generate**\n\n"
            "Please try again.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== IMAGE PROCESSING ====================

async def resize_image(image_data: bytes, target_size: str):
    try:
        if "x" in target_size:
            width, height = map(int, target_size.split("x"))
        else:
            width = height = int(target_size)
            
        img = Image.open(io.BytesIO(image_data))
        if img.mode == 'RGBA':
            img = img.convert('RGB')
            
        img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        img_resized.save(output, format='PNG', optimize=True)
        output.seek(0)
        return output.read()
    except:
        return None

async def convert_image(image_data: bytes, target_format: str):
    try:
        img = Image.open(io.BytesIO(image_data))
        
        if target_format.upper() == 'JPG' and img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif target_format.upper() == 'JPG':
            img = img.convert('RGB')
        
        output = io.BytesIO()
        format_type = 'JPEG' if target_format.upper() == 'JPG' else target_format.upper()
        img.save(output, format=format_type, optimize=True)
        output.seek(0)
        return output.read()
    except:
        return None

# ==================== MESSAGE HANDLERS ====================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    action = context.user_data.get("action", "")
    prompt = update.message.text.strip()
    
    if prompt.lower() == "/cancel":
        context.user_data["action"] = None
        await update.message.reply_text(
            "✅ Cancelled",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    if action in ["generate", "generate_ready"]:
        if get_user_usage(user_id) >= DAILY_LIMIT:
            await update.message.reply_text(
                "⚠️ **Daily limit reached!**",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
        
        size = context.user_data.get("size", "512x512")
        style = context.user_data.get("style", "realistic")
        await generate_and_send(update, context, prompt, size, style)
        
    else:
        await update.message.reply_text(
            "👋 **Use the buttons below!**",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.get("action", "")
    
    try:
        photo = await update.message.photo[-1].get_file()
        image_data = await photo.download_as_bytearray()
        
        if action == "convert" or action == "convert_ready":
            target_format = context.user_data.get("format", "PNG")
            
            await update.message.reply_text(f"🔄 Converting to {target_format}...", parse_mode="Markdown")
            
            converted = await convert_image(image_data, target_format)
            
            if converted:
                await update.message.reply_document(
                    document=io.BytesIO(converted),
                    filename=f"converted.{target_format.lower()}",
                    caption=f"✅ Converted to {target_format}",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ Conversion failed",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
                
        elif action == "resize" or action == "resize_ready":
            target_size = context.user_data.get("size", "512x512")
            
            await update.message.reply_text(f"📐 Resizing to {target_size}...", parse_mode="Markdown")
            
            resized = await resize_image(image_data, target_size)
            
            if resized:
                await update.message.reply_document(
                    document=io.BytesIO(resized),
                    filename=f"resized_{target_size.replace('x', 'X')}.png",
                    caption=f"✅ Resized to {target_size}",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ Resize failed",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
        else:
            await update.message.reply_text(
                "🖼️ Image received!\n\nUse the buttons below:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Convert", callback_data="convert")],
                    [InlineKeyboardButton("📐 Resize", callback_data="resize")],
                    [InlineKeyboardButton("🏠 Menu", callback_data="back")]
                ])
            )
            
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text(
            "❌ Error processing image",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== MAIN ====================

async def post_init(application):
    print("=" * 50)
    print(f"🎨 {BOT_NAME} Started!")
    print(f"🤖 @{BOT_USERNAME}")
    print(f"📊 Daily Limit: {DAILY_LIMIT} images")
    print("=" * 50)

def main():
    print(f"🚀 Starting {BOT_NAME}...")
    
    application = ApplicationBuilder() \
        .token(BOT_TOKEN) \
        .post_init(post_init) \
        .build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("usage", usage_command))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    print("✅ Bot is running!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
