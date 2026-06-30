import os
import io
import asyncio
import aiohttp
import tempfile
from datetime import datetime, timedelta
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# Free AI Image Generation API (Pollinations.ai - no API key needed)
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"

# User usage tracking (in-memory, resets daily)
user_usage = {}
DAILY_LIMIT = 10

# ==================== HELPER FUNCTIONS ====================
def get_user_usage(user_id):
    """Get user's daily usage count"""
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{today}"
    return user_usage.get(key, 0)

def increment_user_usage(user_id):
    """Increment user's usage count"""
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{today}"
    user_usage[key] = user_usage.get(key, 0) + 1
    return user_usage[key]

def get_remaining_usage(user_id):
    """Get remaining usage for today"""
    return max(0, DAILY_LIMIT - get_user_usage(user_id))

# ==================== KEYBOARD FUNCTIONS ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎨 Generate Image", callback_data="generate")],
        [InlineKeyboardButton("📐 Resize Image", callback_data="resize")],
        [InlineKeyboardButton("🔄 Convert Format", callback_data="convert")],
        [InlineKeyboardButton("📊 Usage", callback_data="usage")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_size_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔲 512x512", callback_data="size_512"), 
         InlineKeyboardButton("🔳 768x768", callback_data="size_768")],
        [InlineKeyboardButton("⬜ 1024x1024", callback_data="size_1024")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_format_keyboard():
    keyboard = [
        [InlineKeyboardButton("🟦 PNG", callback_data="format_png"), 
         InlineKeyboardButton("🟨 JPG", callback_data="format_jpg")],
        [InlineKeyboardButton("🟩 WEBP", callback_data="format_webp")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_generate_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔄 Try Different Size", callback_data="size_menu")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    remaining = get_remaining_usage(str(user.id))
    
    welcome_message = (
        f"✨ Welcome {user.first_name} to **PixelForgeBot**!\n\n"
        f"🎨 I generate images using AI for FREE!\n"
        f"📤 Send any image to convert or resize it\n\n"
        f"📊 **Daily Limit**: {remaining} images remaining today\n\n"
        "⬇️ Use the buttons below to get started!"
    )
    await update.message.reply_text(
        welcome_message, 
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "📖 **PixelForgeBot User Guide**\n\n"
        "**🎨 Generate AI Images**\n"
        "• Click 'Generate Image'\n"
        "• Type your prompt\n"
        "• Choose size\n"
        "• Wait for magic! ✨\n\n"
        "**🔄 Convert Image Format**\n"
        "• Click 'Convert Format'\n"
        "• Send any image\n"
        "• Choose output format\n\n"
        "**📐 Resize Image**\n"
        "• Click 'Resize Image'\n"
        "• Send any image\n"
        "• Choose new size\n\n"
        "**💰 Usage**\n"
        "• {DAILY_LIMIT} images per day\n"
        "• Resets at midnight UTC\n\n"
        "**Commands**\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/usage - Check your usage"
    ).format(DAILY_LIMIT=DAILY_LIMIT)
    
    await update.message.reply_text(
        help_text, 
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /usage command"""
    user_id = str(update.effective_user.id)
    used = get_user_usage(user_id)
    remaining = DAILY_LIMIT - used
    
    status_text = (
        f"📊 **Your Usage**\n\n"
        f"Used today: {used}/{DAILY_LIMIT}\n"
        f"Remaining: {remaining}/{DAILY_LIMIT}\n\n"
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
            
        await query.edit_message_text(
            "🎨 **Describe your image**\n\n"
            "Send me a prompt like:\n"
            "• 'A cat wearing a spacesuit on Mars'\n"
            "• 'Beautiful sunset over mountains'\n"
            "• 'Cyberpunk city at night'\n\n"
            "Choose size first:",
            parse_mode="Markdown",
            reply_markup=get_size_keyboard()
        )
        context.user_data["action"] = "generate"
        
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
        
    elif data == "usage":
        used = get_user_usage(user_id)
        remaining = DAILY_LIMIT - used
        await query.edit_message_text(
            f"📊 **Your Usage**\n\n"
            f"Used today: {used}/{DAILY_LIMIT}\n"
            f"Remaining: {remaining}/{DAILY_LIMIT}\n\n"
            f"🔄 Resets at midnight UTC",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
    elif data == "help":
        await help_command(update, context)
        
    elif data == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        context.user_data["action"] = None
        
    elif data == "size_menu":
        await query.edit_message_text(
            "📐 Choose size:",
            parse_mode="Markdown",
            reply_markup=get_size_keyboard()
        )
        
    elif data.startswith("size_"):
        size_map = {
            "size_512": "512x512",
            "size_768": "768x768",
            "size_1024": "1024x1024"
        }
        context.user_data["size"] = size_map.get(data, "512x512")
        context.user_data["action"] = "generate_ready"
        
        await query.edit_message_text(
            f"✅ Size set to **{context.user_data['size']}**\n\n"
            "Now send me your prompt!\n"
            "Example: 'A beautiful landscape' 🖼️",
            parse_mode="Markdown",
            reply_markup=get_generate_keyboard()
        )
        
    elif data.startswith("format_"):
        format_map = {
            "format_png": "PNG",
            "format_jpg": "JPG",
            "format_webp": "WEBP"
        }
        context.user_data["format"] = format_map.get(data, "PNG")
        context.user_data["action"] = "convert_ready"
        
        await query.edit_message_text(
            f"✅ Format set to **{context.user_data['format']}**\n\n"
            "Now send me an image to convert! 📸",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

# ==================== IMAGE GENERATION ====================
async def generate_image(prompt: str, size: str = "512x512"):
    """Generate image using Pollinations.ai"""
    try:
        # Clean and format prompt
        clean_prompt = prompt.strip().replace(" ", "%20")
        width, height = size.split("x")
        
        # Pollinations.ai URL
        url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width={width}&height={height}&nologo=true&seed={int(datetime.now().timestamp())}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    print(f"API Error: {response.status}")
                    return None
    except asyncio.TimeoutError:
        print("Generation timeout")
        return None
    except Exception as e:
        print(f"Generation error: {e}")
        return None

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
        
        # Convert RGBA to RGB if needed (for JPG)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
            
        # Resize
        img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = io.BytesIO()
        img_resized.save(output, format='PNG')
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
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif target_format.upper() == 'JPG':
            img = img.convert('RGB')
            
        # Save to bytes
        output = io.BytesIO()
        format_type = 'JPEG' if target_format.upper() == 'JPG' else target_format.upper()
        img.save(output, format=format_type)
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
    
    # Check if user wants to generate
    if action in ["generate", "generate_ready"]:
        # Check usage
        if get_user_usage(user_id) >= DAILY_LIMIT:
            await update.message.reply_text(
                "⚠️ **Daily limit reached!**\n\n"
                f"You've used {DAILY_LIMIT} images today.\n"
                "Come back tomorrow for more 🎨",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return
            
        # Check if size is set
        size = context.user_data.get("size", "512x512")
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            f"🎨 **Generating image...**\n\n"
            f"📝 Prompt: *{prompt}*\n"
            f"📐 Size: {size}\n\n"
            "⏳ This may take 10-20 seconds...",
            parse_mode="Markdown"
        )
        
        # Generate image
        image_data = await generate_image(prompt, size)
        
        if image_data:
            # Increment usage
            used = increment_user_usage(user_id)
            remaining = DAILY_LIMIT - used
            
            await processing_msg.delete()
            
            # Send generated image
            await update.message.reply_photo(
                photo=io.BytesIO(image_data),
                caption=f"✨ **Generated!**\n\n"
                       f"📝 *{prompt}*\n"
                       f"📐 Size: {size}\n"
                       f"📊 {used}/{DAILY_LIMIT} used today",
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
            
            # Convert image
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
            # Just received an image
            await update.message.reply_text(
                "🖼️ **Image received!**\n\n"
                "Use the buttons below to:\n"
                "• 🔄 Convert format\n"
                "• 📐 Resize image",
                parse_mode="Markdown",
                reply_markup=get_format_keyboard()
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
def main():
    """Start the bot"""
    print("🚀 Starting PixelForgeBot...")
    print(f"📊 Daily limit: {DAILY_LIMIT} images per user")
    
    # Build application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("usage", usage_command))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    # Start the bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
