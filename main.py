import json
import os
import hashlib
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
from termcolor import colored

# 🔽 Load environment variables
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# 📌 Basic Setup
SESSION_FILE = "telegram_session"
IMAGE_FOLDER = "images"
JSON_FILE = "image_data.json"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# 📌 Data Storage
image_data = {}
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r") as f:
        image_data = json.load(f)

active_groups = set()
delay_time = 0.0  # Supports decimal values now

# 🤖 Helper Functions
def print_bold(message, color):
    """Print bold colored messages"""
    print(colored(f"\033[1m{message}\033[0m", color))  # \033[1m for bold

def get_image_hash(file_path):
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# 🤖 Initialize Client
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

@client.on(events.NewMessage(pattern="/chalu"))
async def start_handler(event):
    if len(active_groups) >= 2:
        await event.reply("❌ Max 2 groups allowed!")
        print_bold("ERROR: Maximum groups reached", "red")
        return
    
    group_id = event.chat_id
    active_groups.add(group_id)
    await event.reply("🚀 Bot activated!")
    print_bold(f"SUCCESS: Started in group {group_id}", "green")

@client.on(events.NewMessage(pattern="/band"))
async def stop_handler(event):
    group_id = event.chat_id
    if group_id in active_groups:
        active_groups.remove(group_id)
        await event.reply("🛑 Bot stopped!")
        print_bold(f"INFO: Stopped in group {group_id}", "yellow")

@client.on(events.NewMessage(pattern=r"/time\s+(\d+\.?\d*)[sm]"))
async def set_delay_handler(event):
    global delay_time
    try:
        time_value = float(event.pattern_match.group(1))
        if 's' in event.text.lower():
            delay_time = time_value
        elif 'm' in event.text.lower():
            delay_time = time_value * 60
        
        await event.reply(f"⏳ Delay set to {time_value}s")
        print_bold(f"SETTING: Delay = {delay_time:.2f} seconds", "blue")
    except:
        await event.reply("❌ Use: /time 1.5s or /time 2.5m")
        print_bold("ERROR: Invalid delay format", "red")

@client.on(events.NewMessage(incoming=True))
async def message_handler(event):
    if event.chat_id not in active_groups:
        return

    # Auto-reply with delay
    if "Correct! you get +$10000" in event.text:
        await asyncio.sleep(delay_time)
        await event.reply("/nation asia")
        print_bold(f"AUTO-REPLY: After {delay_time:.2f}s delay", "magenta")

    # Image processing
    if event.sender.username == "fam_tree_bot" and event.photo:
        try:
            temp_file = "temp.jpg"
            await event.download_media(temp_file)
            img_hash = get_image_hash(temp_file)
            
            # Your existing image processing logic here
            # ...
            
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

# 🔥 Start Bot
print_bold("BOT STARTED", "green")
with client:
    client.run_until_disconnected()
