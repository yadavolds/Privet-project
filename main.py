import json
import os
import hashlib
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
from termcolor import colored

# Load environment variables
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Basic Setup
SESSION_FILE = "telegram_session"
IMAGE_FOLDER = "images"
JSON_FILE = "image_data.json"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Data Storage
image_data = {}
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r") as f:
        image_data = json.load(f)

active_groups = set()
delay_time = 0.0  # Supports decimal values

def print_bold(message, color):
    """Print bold colored messages"""
    print(colored(f"\033[1m{message}\033[0m", color))

def get_image_hash(file_path):
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# Initialize Client
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

@client.on(events.NewMessage(pattern="/chalu"))
async def start_handler(event):
    if len(active_groups) >= 2:
        await event.reply("❌ Maximum 2 groups allowed! Use /band in another group first.")
        return
    
    group_id = event.chat_id
    active_groups.add(group_id)
    await event.reply("🚀 Bot activated! I'll now auto-reply to game messages.")
    print_bold(f"Bot started in group: {group_id}", "green")

@client.on(events.NewMessage(pattern="/band"))
async def stop_handler(event):
    group_id = event.chat_id
    if group_id in active_groups:
        active_groups.remove(group_id)
        await event.reply("🛑 Bot deactivated!")
        print_bold(f"Bot stopped in group: {group_id}", "yellow")

@client.on(events.NewMessage(pattern=r"/time\s+(\d+\.?\d*)[sm]"))
async def set_delay_handler(event):
    global delay_time
    try:
        time_value = float(event.pattern_match.group(1))
        if 's' in event.text.lower():
            delay_time = time_value
            reply_msg = f"⏳ Auto-reply delay set to {time_value} seconds"
        elif 'm' in event.text.lower():
            delay_time = time_value * 60
            reply_msg = f"⏳ Auto-reply delay set to {time_value} minutes"
        
        await event.reply(reply_msg)
        print_bold(f"Delay set to: {delay_time:.2f} seconds", "blue")  # Only shows when delay is set
    except:
        await event.reply("❌ Invalid format! Use: /time 1.5s or /time 2.5m")

@client.on(events.NewMessage(incoming=True))
async def message_handler(event):
    if event.chat_id not in active_groups:
        return

    # Game completion detection and auto-reply
    if "Correct! you get +$10000" in event.text:
        await asyncio.sleep(delay_time)
        await event.reply("/nation asia")
        print_bold("New game started with /nation asia", "magenta")

    # Image processing from fam_tree_bot
    if event.sender and event.sender.username == "fam_tree_bot" and event.photo:
        temp_file = "temp.jpg"
        await event.download_media(temp_file)
        
        try:
            img_hash = get_image_hash(temp_file)
            found = False
            
            # Check if image exists in database
            for img_id, data in image_data.items():
                if data["hash"] == img_hash:
                    if data.get("country"):
                        await event.reply(data["country"])
                        print_bold(f"Image matched! Sent answer: {data['country']}", "green")
                    else:
                        await event.reply("⚠️ I know this image but don't have an answer yet!")
                        print_bold("Image matched but no answer available", "yellow")
                    found = True
                    break
            
            if not found:
                # Store new image
                new_id = f"img_{len(image_data)+1}"
                new_path = os.path.join(IMAGE_FOLDER, f"{new_id}.jpg")
                os.rename(temp_file, new_path)
                
                image_data[new_id] = {"hash": img_hash, "country": ""}
                with open(JSON_FILE, "w") as f:
                    json.dump(image_data, f)
                
                await event.reply(f"📸 New image stored! (ID: {new_id})")
                print_bold(f"New image stored with ID: {new_id}", "cyan")
                
        except Exception as e:
            print_bold(f"Error processing image: {str(e)}", "red")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

# Start Bot
print_bold("Bot is running...", "green")
with client:
    client.run_until_disconnected()
