# Don't Remove Credit 
# Ask Doubt on telegram @theprofessorreport_bot

import os
import asyncio
import time
import requests
import pyrogram
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery 
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, FloodWait
from config import API_ID, API_HASH, ERROR_MESSAGE, LOGIN_SYSTEM, WAITING_TIME, ADMINS, LOG_CHANNEL
from database.db import db
from utils.progress import progress_for_pyrogram

# --- IMPORT YOUR LOGIN FUNCTION ---
from devshiva.generate import main as login_handler

# Bypass detection storage
last_link_gen = {}

class batch_temp(object):
    IS_BATCH = {}

# --- HELPERS ---
def get_readable_file_size(size_in_bytes) -> str:
    if size_in_bytes is None: return "0B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024

def get_readable_time(seconds: int) -> str:
    if seconds is None or seconds <= 0: return "00:00"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def get_shortlink(url, api, link):
    try:
        clean_base = url.replace("https://", "").replace("http://", "").strip("/")
        api_url = f"https://{clean_base}/api?api={api}&url={link}"
        response = requests.get(api_url, timeout=10).json()
        if response.get("status") == "success":
            return response.get("shortenedUrl")
        return link 
    except Exception as e:
        print(f"Shortener Error: {e}")
        return link

# --- FORCE SUBSCRIBE CHECK ---
async def check_fsub(client, message):
    FSUB_CHANNEL = -1003627956964 # Confirm your ID
    try:
        user = await client.get_chat_member(FSUB_CHANNEL, message.from_user.id)
        if user.status == enums.ChatMemberStatus.BANNED:
            await message.reply_text("❌ You are banned from using this bot.")
            return False
    except UserNotParticipant:
        try:
            invite = await client.create_chat_invite_link(FSUB_CHANNEL)
            url = invite.invite_link
        except:
            url = "https://t.me/devXvoid" 

        join_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Channel 📢", url=url)],
            [InlineKeyboardButton("🔄 Checked / Try Again", callback_data="check_fsub_btn")]
        ])
        text = "<b>⚠️ Access Denied!</b>\n\nYou must join our updates channel to use this bot."
        if isinstance(message, CallbackQuery): await message.answer(text, show_alert=True)
        else: await message.reply_text(text, reply_markup=join_btn)
        return False
    except Exception: return True
    return True

# --- DETAILED HELP TEXT ---
DETAILED_HELP = """
<b>🛠 How to use Save Restricted Bot</b>

<b>1️⃣ Basic Usage:</b>
• Send any public/private post link to download.
• Use <b>/login</b> for private channels.
• Use <b>/cancel</b> to stop a batch.

<b>2️⃣ Caption Tags:</b>
• <code>{file_name}</code> - Name
• <code>{file_size}</code> - Size
• <code>{duration}</code> - Runtime
• <code>{file_caption}</code> - Original Text

<b>3️⃣ Thumbnail:</b>
• Reply <code>/set_thumb</code> to any photo to save it.
"""

# --- COMMANDS ---
@Client.on_message(filters.command(["start"]) & filters.private)
async def send_start(client: Client, message: Message):
    if not await check_fsub(client, message): return
    user_id = message.from_user.id
    user_mention = message.from_user.mention

    # NEW USER LOG
    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        if LOG_CHANNEL:
            log_msg = (f"<b>🆕 New User Joined!</b>\n\n"
                       f"<b>👤 Name:</b> {user_mention}\n"
                       f"<b>🆔 ID:</b> <code>{user_id}</code>\n"
                       f"<b>📅 Date:</b> {time.strftime('%Y-%m-%d')}")
            try: await client.send_message(LOG_CHANNEL, log_msg)
            except: pass
    
    if len(message.command) > 1 and message.command[1].startswith("verify"):
        await db.verify_user(user_id)
        return await message.reply_text("<b>Verification Successful! ✅</b>")

    is_verified = await db.get_verify_status(user_id)
    welcome_text = (f"<b>👋 Hi {message.from_user.mention}!</b>\n\nI am a powerful **Save Restricted Bot**.\n\n"
                    f"{'✅ <b>Premium Active!</b>' if is_verified else '🔓 <b>Verify for 6h Access</b>'}")

    buttons = [[InlineKeyboardButton("Help 🛠️", callback_data="help"), InlineKeyboardButton("Settings ⚙️", callback_data="settings_menu")],
               [InlineKeyboardButton("Login 🔑", callback_data="login_process")]]
    if not is_verified: buttons[1].append(InlineKeyboardButton("Verify Bot 🔓", callback_data="gen_link"))
    
    try: await message.reply_photo(photo="logo.png", caption=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))
    except: await message.reply_text(text=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.command("set_thumb") & filters.private)
async def set_thumbnail(client, message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply_text("❌ Please reply to a photo.")
    await db.set_thumb(message.from_user.id, message.reply_to_message.photo.file_id)
    await message.reply_text("✅ **Custom Thumbnail Saved!**")

@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_task(client, message):
    batch_temp.IS_BATCH[message.from_user.id] = True
    await message.reply_text("⏳ **Batch will stop after current file.**")

@Client.on_message(filters.command("set_caption") & filters.private)
async def set_caption_cmd(client, message):
    if len(message.command) < 2: return await message.reply("Usage: /set_caption Your Text")
    await db.set_caption(message.from_user.id, message.text.split(None, 1)[1])
    await message.reply("✅ **Caption Updated!**")

# --- MAIN LOGIC (NO SKIP + WORK LOGS) ---
@Client.on_message(filters.text & filters.private)
async def save(client: Client, message: Message):
    if "https://t.me/" not in message.text: return
    if not await check_fsub(client, message): return
    
    user_id = message.from_user.id
    config = await db.get_verify_config()
    if config.get('is_on') and not await db.get_verify_status(user_id):
        return await message.reply("Verify first!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Verify 🔓", callback_data="gen_link")]]))

    if batch_temp.IS_BATCH.get(user_id) == False:
        return await message.reply_text("❌ A task is already running.")

    datas = message.text.split("/")
    temp = datas[-1].replace("?single","").split("-")
    fromID = int(temp[0].strip())
    toID = int(temp[1].strip()) if len(temp) > 1 else fromID
    
    # --- #work LOG CHANNEL UPDATE ---
    total_files = (toID - fromID) + 1
    if LOG_CHANNEL:
        work_log = (f"<b>#work Started</b>\n\n"
                    f"<b>👤 User:</b> {message.from_user.mention}\n"
                    f"<b>🆔 ID:</b> <code>{user_id}</code>\n"
                    f"<b>📂 Type:</b> {'Batch' if total_files > 1 else 'Single'}\n"
                    f"<b>📁 Total:</b> <code>{total_files}</code>")
        try: await client.send_message(LOG_CHANNEL, work_log)
        except: pass

    batch_temp.IS_BATCH[user_id] = False
    is_private = "/c/" in message.text
    acc = client
    
    if is_private:
        user_data = await db.get_session(user_id)
        if not user_data: 
            batch_temp.IS_BATCH[user_id] = True
            return await message.reply("❌ Login first using /login.")
        acc = Client("saver", session_string=user_data, api_hash=API_HASH, api_id=API_ID)
        await acc.connect()

    for msgid in range(fromID, toID + 1):
        if batch_temp.IS_BATCH.get(user_id) == True: break
        chatid = int("-100" + datas[4]) if is_private else datas[3]
        
        try:
            # STRICT SEQUENTIAL: Bot waits here until file is uploaded
            await handle_private(client, acc, message, chatid, msgid)
            await asyncio.sleep(WAITING_TIME)
        except FloodWait as e: await asyncio.sleep(e.value)
        except Exception as e: print(f"Error on ID {msgid}: {e}")

    if is_private: await acc.disconnect()
    batch_temp.IS_BATCH[user_id] = True
    await message.reply("✅ **Batch Task Completed!**")

async def handle_private(client: Client, acc, message: Message, chatid, msgid: int):
    try:
        msg = await acc.get_messages(chatid, msgid)
        if not msg or msg.empty: return 
        
        user_id = message.from_user.id
        upload_mode = await db.get_upload_mode(user_id)
        target_id = await db.get_target_chat(user_id)
        target_chat = int(target_id) if (upload_mode == "Channel" and target_id) else message.chat.id
        
        custom_caption = await db.get_caption(user_id)
        custom_thumb = await db.get_thumb(user_id)

        if not msg.media:
            if msg.text: await client.send_message(target_chat, msg.text, entities=msg.entities)
            return

        smsg = await client.send_message(message.chat.id, f"⏳ **Processing ID: {msgid}...**")
        media_obj = getattr(msg, msg.media.value)
        f_name = getattr(media_obj, "file_name", "No Name")
        f_size = get_readable_file_size(getattr(media_obj, "file_size", 0))
        duration = get_readable_time(getattr(media_obj, "duration", 0))

        final_cap = (custom_caption.replace("{file_name}", f_name)
                                   .replace("{file_size}", f_size)
                                   .replace("{duration}", duration)
                                   .replace("{file_caption}", msg.caption or "")) if custom_caption else (msg.caption or "")

        file, ph_path = None, None
        try:
            # DOWNLOAD
            file = await acc.download_media(msg, progress=progress_for_pyrogram, 
                                           progress_args=("📥 **Downloading...**", smsg, time.time()))
            
            # THUMBNAIL
            if custom_thumb:
                ph_path = await client.download_media(custom_thumb)
            
            args = {"chat_id": target_chat, "caption": final_cap, "parse_mode": enums.ParseMode.HTML, 
                    "progress": progress_for_pyrogram, "progress_args": ("📤 **Uploading...**", smsg, time.time())}
            
            # UPLOAD
            if msg.document: await client.send_document(document=file, thumb=ph_path, **args)
            elif msg.video: await client.send_video(video=file, thumb=ph_path, **args)
            elif msg.photo: await client.send_photo(photo=file, caption=final_cap)
            elif msg.audio: await client.send_audio(audio=file, thumb=ph_path, **args)
        finally:
            # CLEANUP (To prevent disk full)
            if file and os.path.exists(file): os.remove(file)
            if ph_path and os.path.exists(ph_path): os.remove(ph_path)
            await smsg.delete()
    except Exception as e:
        print(f"Handle Private Error: {e}")

# --- CALLBACKS & ADMIN ---
@Client.on_callback_query()
async def cb_handler(client, query):
    user_id = query.from_user.id
    if query.data == "help":
        await query.message.edit_caption(caption=DETAILED_HELP, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back 🔙", callback_data="back_start")]]))
    elif query.data == "back_start":
        await query.message.delete()
        await send_start(client, query.message)
    elif query.data == "login_process":
        await login_handler(client, query.message)
    elif query.data == "settings_menu":
        mode = await db.get_upload_mode(user_id)
        btn = [[InlineKeyboardButton(f"Mode: {mode}", callback_data=f"set_mode_{'Channel' if mode=='PM' else 'PM'}")],
               [InlineKeyboardButton("Back 🔙", callback_data="back_start")]]
        await query.message.edit_caption(caption=f"<b>⚙️ Settings</b>\n\n<b>Current Mode:</b> {mode}", reply_markup=InlineKeyboardMarkup(btn))
    elif query.data.startswith("set_mode_"):
        await db.set_upload_mode(user_id, query.data.split("_")[2])
        await query.answer("Mode Updated!")
        await cb_handler(client, query)

@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def get_stats(client, message):
    users_count = await db.total_users_count()
    await message.reply_text(f"<b>📊 Stats:</b> <code>{users_count}</code> users")
