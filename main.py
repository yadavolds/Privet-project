import json
import os
import hashlib
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
from termcolor import colored
from pyfiglet import figlet_format

# 🔽 Load environment variables from .env file
load_dotenv()

# 📌 Telegram credentials
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# 📌 Telegram Session File
SESSION_FILE = "telegram_session"

# 🎯 Image Data Storage
IMAGE_FOLDER = "images"
JSON_FILE = "image_data.json"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# 📌 Load existing image data
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        image_data = json.load(f)
else:
    image_data = {}

# 📌 Active Groups (Max 2)
active_groups = set()

# 📌 Delay Settings
delay_time = 0.0  # Changed to float for decimal support

def print_bold(message, color):
    """Print bold colored messages"""
    print(colored(figlet_format(message, font="small"), color))

def get_image_hash(file_path):
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# 🤖 Initialize Telegram Client
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

@client.on(events.NewMessage(pattern="/chalu"))
async def start_handler(event):
    """ Start the bot in the group where /chalu is sent """
    global active_groups

    if len(active_groups) >= 2:
        await event.reply("❌ Maximum 2 groups mein hi khel sakte hain. Pehle kisi group ko `/band` karein.")
        print_bold("MAX GROUPS REACHED!", "red")
        return

    group_id = event.chat_id
    if group_id in active_groups:
        await event.reply("✅ Bot already is group mein active hai.")
        print_bold("BOT ALREADY ACTIVE", "yellow")
    else:
        active_groups.add(group_id)
        await event.reply("🚀 Bot ne khelna shuru kar diya hai is group mein!")
        print_bold(f"BOT STARTED IN GROUP: {group_id}", "green")

@client.on(events.NewMessage(pattern="/band"))
async def stop_handler(event):
    """ Stop the bot in the group where /band is sent """
    global active_groups

    group_id = event.chat_id
    if group_id in active_groups:
        active_groups.remove(group_id)
        await event.reply("🛑 Bot ne khelna band kar diya hai is group mein.")
        print_bold(f"BOT STOPPED IN GROUP: {group_id}", "red")
    else:
        await event.reply("❌ Bot is group mein active nahi hai.")
        print_bold("BOT NOT ACTIVE IN THIS GROUP", "yellow")

@client.on(events.NewMessage(pattern=r"/time\s+(\d+\.?\d*)[sm]"))  # Updated regex pattern
async def set_delay_handler(event):
    """ Set delay time using /time command with decimal support """
    global delay_time

    message = event.message.message.strip()
    try:
        # Extract the numeric value (including decimals)
        time_value = event.pattern_match.group(1)
        
        if 's' in message.lower():
            delay_time = float(time_value)
        elif 'm' in message.lower():
            delay_time = float(time_value) * 60
        else:
            raise ValueError("Invalid time format.")

        await event.reply(f"⏳ Delay set to {time_value}s." if 's' in message.lower() else f"⏳ Delay set to {time_value}m.")
        print_bold(f"DELAY SET TO: {delay_time:.2f} seconds", "blue")
    except Exception as e:
        await event.reply("❌ Invalid format. Use `/time <value><s/m>`. Examples:\n`/time 2.5s`\n`/time 1.5s`\n`/time 0.7s`")
        print_bold(f"DELAY SET ERROR: {e}", "red")

@client.on(events.NewMessage(incoming=True))
async def message_handler(event):
    """ Handle messages in active groups """
    if event.chat_id not in active_groups:
        return  # Ignore messages from non-active groups

    message_text = event.message.message.strip()

    # 🎯 Auto-reply when game is completed
    if "Correct! you get +$10000" in message_text:
        await asyncio.sleep(delay_time)  # Apply delay before replying
        await event.reply("/nation asia")
        print_bold(f"AUTO-REPLY: /nation asia (after {delay_time:.2f}s)", "magenta")

    # 📌 Image Processing (Only from @fam_tree_bot)
    if event.sender.username == "fam_tree_bot" and event.photo:
        temp_file = "temp.jpg"
        await event.download_media(file=temp_file)

        try:
            img_hash = get_image_hash(temp_file)
            existing_id, answer = None, None

            # 🔎 Check if image exists in database
            for file_id, data in image_data.items():
                if data["hash"] == img_hash:
                    existing_id = file_id
                    answer = data.get("country", "")
                    break

            if existing_id:
                # ✅ Image Found in Database
                if answer:
                    await event.reply(answer)
                    print_bold(f"IMAGE MATCHED - ID: {existing_id} | ANSWER: {answer}", "green")
                else:
                    await event.reply("⚠ **Answer missing in database!**")
                    print_bold(f"IMAGE MATCHED BUT NO ANSWER - ID: {existing_id}", "yellow")
            else:
                # ❌ Image Not Found, So Store It
                new_id = f"img_{len(image_data) + 1}"
                new_file_path = os.path.join(IMAGE_FOLDER, f"{new_id}.jpg")
                os.rename(temp_file, new_file_path)

                image_data[new_id] = {"hash": img_hash, "country": ""}
                with open(JSON_FILE, "w", encoding="utf-8") as f:
                    json.dump(image_data, f, indent=4)

                await event.reply(f"📂 **New Image Stored!** (ID: `{new_id}`)")
                print_bold(f"NEW IMAGE STORED - ID: {new_id}", "cyan")

        except Exception as e:
            print_bold(f"IMAGE PROCESSING ERROR: {e}", "red")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

# 🔥 Start the Telegram Client
print_bold("BOT STARTING...", "blue")
with client:
    print_bold("BOT IS RUNNING!", "green")
    client.loop.run_forever()
