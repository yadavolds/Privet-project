import json
import os
import hashlib
import datetime
import asyncio
import requests
import base64
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from termcolor import colored

# 🔽 Load environment variables from .env file
load_dotenv()

# 📌 Expiration Date (Format: YYYY-MM-DD)
EXPIRATION_DATE = "2025-04-01"

# 📌 Check if the program is expired
current_date = datetime.datetime.now().date()
expiry_date = datetime.datetime.strptime(EXPIRATION_DATE, "%Y-%m-%d").date()

if current_date >= expiry_date:
    print(colored("[❌] Program has expired! Please contact the owner.", "red"))
    exit()

# 📌 Load credentials from .env file
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# 📌 Telegram Bot Token and Admin ID
BOT_TOKEN = "7857443299:AAHew-ha66tdyqp5J9iKUcSTSldpexr6MgI"  # Replace with your bot token
ADMIN_ID = 5770659918  # Replace with your admin ID

# 📌 Telegram Session File
SESSION_FILE = "telegram_session"

# 📌 Admin Group & Payment Channel
ADMIN_GROUP_ID = -1002668825274  # Replace with actual admin group ID
YADAV_PAYMENTS_CHANNEL = "YADAV_PAYMENTS"
TAX_MESSAGE_ID = 4  # Fixed tax message ID

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

# 📌 Earnings Tracking
total_earnings = 0
tax_payment_history = []  # To store tax payment history

# 📌 Active Groups (Max 2)
active_groups = set()

# 📌 Delay Settings
delay_time = 0  # Default delay time in seconds

# 📌 GitHub Raw URL for JSON Data
GITHUB_RAW_URL = "https://raw.githubusercontent.com/yadavolds/Database-pvt/main/databse.json"

# 📌 JSON file to store earnings and tax history
USER_DATA_FILE = "user_data.json"

# 📌 Flags for controlling debug messages
show_verified_users = True
show_tax_already_paid = True

def encode_field(value):
    """Encode a specific field using base64."""
    if isinstance(value, (int, float, str)):
        value = str(value).encode()
        encoded_value = base64.b64encode(value).decode()
        return encoded_value
    return value

def decode_field(encoded_value):
    """Decode a specific field using base64."""
    if not encoded_value:
        return None
    
    try:
        # Add padding if necessary
        padding = len(encoded_value) % 4
        if padding:
            encoded_value += "=" * (4 - padding)
        
        # Decode the value
        decoded_value = base64.b64decode(encoded_value.encode()).decode()
        return decoded_value
    except Exception as e:
        print(f"Error decoding field: {e}")
        return None

def save_user_data(data, filename=USER_DATA_FILE):
    """Save user data with selective encoding."""
    encoded_data = {
        "earnings": encode_field(data["earnings"]),
        "last_tax_payment": encode_field(data["last_tax_payment"])
    }
    with open(filename, "w") as f:
        json.dump(encoded_data, f, indent=4)

def load_user_data(filename=USER_DATA_FILE):
    """Load user data and decode specific fields."""
    try:
        with open(filename, "r") as f:
            encoded_data = json.load(f)
        decoded_data = {
            "earnings": decode_field(encoded_data.get("earnings")),
            "last_tax_payment": decode_field(encoded_data.get("last_tax_payment"))
        }
        return decoded_data
    except FileNotFoundError:
        return {"earnings": 0, "last_tax_payment": None}
    except Exception as e:
        print(f"Error loading user data: {e}")
        return {"earnings": 0, "last_tax_payment": None}

def get_image_hash(file_path):
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# 🤖 Initialize Telegram Client
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

# 🤖 Initialize Bot Client
from telethon import TelegramClient as BotClient
bot_client = BotClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def send_tax_payment_notification(amount):
    """ Send tax payment notification to admin """
    try:
        message = f"💸 **Tax Paid!**\nAmount: ${amount}\nTotal Earnings: ${total_earnings}\n\n📅 Payment History:\n"
        for payment in tax_payment_history:
            message += f"- ${payment['amount']} on {payment['date']}\n"

        await bot_client.send_message(ADMIN_ID, message)
        print(colored(f"[📤] Tax payment notification sent to admin.", "green"))
    except Exception as e:
        print(colored(f"[❌] Error sending tax payment notification: {e}", "red"))

async def fetch_tax_amount(user_id):
    """ Fetch tax amount from GitHub raw JSON file """
    global show_verified_users

    try:
        response = requests.get(GITHUB_RAW_URL)
        if response.status_code == 200:
            # Parse JSON data
            data = response.json()
            verified_users = data.get("verified_users", [])
            tax_amount_str = data.get("tax_amount", "1+5")  # Default tax amount if not found

            if show_verified_users:
                print(colored(f"[🔍] Verified Users: {verified_users}", "yellow"))  # Debugging log
                show_verified_users = False  # Ensure this is printed only once

            print(colored(f"[🔍] Tax Amount Fetched: {tax_amount_str}", "yellow"))  # Debugging log

            if user_id in verified_users:
                return tax_amount_str
            else:
                print(colored(f"[❌] User {user_id} not verified.", "red"))  # Debugging log
                return None  # User not verified
        else:
            print(colored(f"[❌] Failed to fetch JSON data. Status code: {response.status_code}", "red"))
            return None
    except Exception as e:
        print(colored(f"[❌] Error fetching JSON data: {e}", "red"))
        return None

async def pay_tax(user_id):
    """ Function to pay tax """
    global total_earnings, tax_payment_history, show_tax_already_paid

    # Fetch tax amount
    tax_amount_str = await fetch_tax_amount(user_id)
    if tax_amount_str is None:
        print(colored(f"[❌] User {user_id} not verified.", "red"))
        return

    # Check if 24 hours have passed since last tax payment
    user_data = load_user_data()
    last_tax_payment = user_data.get("last_tax_payment")
    if last_tax_payment:
        last_payment_time = datetime.datetime.strptime(last_tax_payment, "%Y-%m-%d %H:%M:%S")
        current_time = datetime.datetime.now()
        if (current_time - last_payment_time).total_seconds() < 24 * 3600:
            if show_tax_already_paid:
                print(colored(f"[⏳] Tax already paid in the last 24 hours.", "yellow"))
                show_tax_already_paid = False  # Ensure this is printed only once
            return

    # Send tax payment message in the format `/pay <amount> tax`
    tax_payment_message = f"/pay {tax_amount_str} tax"
    print(colored(f"[🔍] Sending tax payment message: {tax_payment_message}", "yellow"))  # Debugging log
    await client.send_message(ADMIN_GROUP_ID, tax_payment_message, reply_to=TAX_MESSAGE_ID)
    print(colored(f"[✅] Tax payment message sent: {tax_payment_message}", "blue"))

    # Update tax payment history
    tax_payment_history.append({"amount": tax_amount_str, "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    # Save updated user data
    save_user_data({"earnings": total_earnings, "last_tax_payment": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    # Send tax payment notification to admin
    await send_tax_payment_notification(tax_amount_str)
    print(colored(f"[✅] Tax of ${tax_amount_str} paid successfully.", "blue"))
    show_tax_already_paid = True  # Reset the flag after paying tax

@client.on(events.NewMessage(pattern="/chalu"))
async def start_handler(event):
    """ Start the bot in the group where /chalu is sent """
    global active_groups

    if len(active_groups) >= 2:
        await event.reply("❌ Maximum 2 groups mein hi khel sakte hain. Pehle kisi group ko `/band` karein.")
        return

    group_id = event.chat_id
    if group_id in active_groups:
        await event.reply("✅ Bot already is group mein active hai.")
    else:
        active_groups.add(group_id)
        await event.reply("🚀 Bot ne khelna shuru kar diya hai is group mein!")
        print(colored(f"[🚀] Bot started in group: {group_id}", "blue"))

@client.on(events.NewMessage(pattern="/band"))
async def stop_handler(event):
    """ Stop the bot in the group where /band is sent """
    global active_groups

    group_id = event.chat_id
    if group_id in active_groups:
        active_groups.remove(group_id)
        await event.reply("🛑 Bot ne khelna band kar diya hai is group mein.")
        print(colored(f"[🛑] Bot stopped in group: {group_id}", "red"))
    else:
        await event.reply("❌ Bot is group mein active nahi hai.")

@client.on(events.NewMessage(pattern="/time"))
async def set_delay_handler(event):
    """ Set delay time using /time command """
    global delay_time

    message = event.message.message.strip()
    try:
        time_value = message.split()[1]  # Extract time value (e.g., "4s", "1m")
        if time_value.endswith("s"):
            delay_time = int(time_value[:-1])
        elif time_value.endswith("m"):
            delay_time = int(time_value[:-1]) * 60
        else:
            raise ValueError("Invalid time format.")

        await event.reply(f"⏳ Delay set to {time_value}.")
        print(colored(f"[⏳] Delay set to {time_value}", "yellow"))
    except Exception as e:
        await event.reply("❌ Invalid format. Use `/time <value><s/m>`. Example: `/time 4s` or `/time 1m`.")
        print(colored(f"[❌] Error setting delay: {e}", "red"))

@client.on(events.NewMessage(incoming=True))
async def message_handler(event):
    """ Handle messages in active groups """
    global total_earnings, tax_payment_history

    if event.chat_id not in active_groups:
        return  # Ignore messages from non-active groups

    message_text = event.message.message.strip()

    # 🎯 Auto-reply when game is completed
    if "Correct! you get +$10000" in message_text:
        total_earnings += 10000
        print(colored(f"[💰] Earnings Updated: ${total_earnings}", "green"))

        # Pay tax if earnings reach the threshold
        user_id = event.sender_id
        await pay_tax(user_id)

        await asyncio.sleep(delay_time)  # Apply delay before replying
        await event.reply("/nation asia")
        print(colored(f"[🚀] Detected game completion message. Sent '/nation asia'.", "blue"))

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
                    print(colored(f"[✔] Image Matched - ID: {existing_id} | Answer: {answer}", "green"))
                else:
                    await event.reply("⚠ **Answer missing in database!**")
                    print(colored(f"[❌] Image Matched but answer not set - ID: {existing_id}", "red"))
            else:
                # ❌ Image Not Found, So Store It
                new_id = f"img_{len(image_data) + 1}"
                new_file_path = os.path.join(IMAGE_FOLDER, f"{new_id}.jpg")
                os.rename(temp_file, new_file_path)

                image_data[new_id] = {"hash": img_hash, "country": ""}
                with open(JSON_FILE, "w", encoding="utf-8") as f:
                    json.dump(image_data, f, indent=4)

                await event.reply(f"📂 **New Image Stored!** (ID: `{new_id}`)")
                print(colored(f"[⚠] New Image Added to Database - ID: {new_id}", "yellow"))

        except Exception as e:
            print(colored(f"[❌] Error processing image: {e}", "red"))
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

async def join_admin_group():
    """ Automatically join the admin group on user login """
    try:
        await client(JoinChannelRequest(ADMIN_GROUP_ID))
        print(colored("[✅] Admin Group Joined Successfully!", "blue"))
    except Exception as e:
        print(colored(f"[❌] Error joining admin group: {e}", "red"))

# 🔥 Start the Telegram Client
with client:
    print(colored("[🚀] Bot is running...", "blue"))
    client.loop.run_until_complete(join_admin_group())
    client.loop.run_forever()
