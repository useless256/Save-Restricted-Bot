# Don't Remove Credit 
# Ask Doubt on telegram @theprofessorreport_bot

import os
import asyncio
import time
import requests
import pyrogram
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery 
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
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

# --- UPDATED: STRICT FORCE SUBSCRIBE CHECK ---
async def check_fsub(client, message):
    FSUB_CHANNEL = -1003627956964 
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
        if isinstance(message, CallbackQuery):
            await message.answer(text, show_alert=True)
        else:
            await message.reply_text(text, reply_markup=join_btn)
        return False
    except Exception:
        return True
    return True

# --- DETAILED HELP TEXT ---
DETAILED_HELP = """
<b>🛠 How to use Save Restricted Bot</b>

<b>1️⃣ Basic Usage:</b>
• Send any post link to download.
• For private posts, <b>/login</b> first.
• Use <b>/cancel</b> to stop current task.

<b>2️⃣ Caption Tags (Feelings):</b>
Use these placeholders in <code>/set_caption</code>:
• <code>{file_name}</code> - Video/File name.
• <code>{file_size}</code> - Total size of file.
• <code>{file_caption}</code> - Original caption.

<b>3️⃣ Formatting Styles:</b>
• <code>&lt;b&gt;Text&lt;/b&gt;</code> - <b>Bold</b>
• <code>&lt;i&gt;Text&lt;/i&gt;</code> - <i>Italic</i>
• <code>&lt;u&gt;Text&lt;/u&gt;</code> - <u>Underline</u>
• <code>&lt;blockquote&gt;Text&lt;/blockquote&gt;</code> - Quote Box

<b>4️⃣ Thumbnail:</b>
• Reply <code>/set_thumb</code> to any image.
"""

# --- START COMMAND ---
@Client.on_message(filters.command(["start"]) & filters.private)
async def send_start(client: Client, message: Message):
    if not await check_fsub(client, message): return
    
    user_id = message.from_user.id
    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        if LOG_CHANNEL:
            log_text = f"<b>🆕 New User:</b> {message.from_user.mention}\n<b>🆔 ID:</b> <code>{user_id}</code>"
            try: await client.send_message(LOG_CHANNEL, log_text)
            except: pass

    if len(message.command) > 1 and message.command[1].startswith("verify"):
        await db.verify_user(user_id)
        return await message.reply_text("<b>Verification Successful! ✅</b>")

    is_verified = await db.get_verify_status(user_id)
    welcome_text = f"<b>👋 Hi {message.from_user.mention}!</b>\n\nI am a Save Restricted Bot.\n\n{'✅ Premium: Active' if is_verified else '🔓 Status: Free'}"

    buttons = [[InlineKeyboardButton("Help 🛠️", callback_data="help"), InlineKeyboardButton("Settings ⚙️", callback_data="settings_menu")],
               [InlineKeyboardButton("Login 🔑", callback_data="login_process")]]
    
    if not is_verified:
        buttons[1].append(InlineKeyboardButton("Verify 🔓", callback_data="gen_link"))
    
    try: await message.reply_photo(photo="logo.png", caption=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))
    except: await message.reply_text(text=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

# --- ADMIN PANEL ---
@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def get_stats(client, message):
    users_count = await db.total_users_count()
    await message.reply_text(f"<b>📊 Total Users:</b> <code>{users_count}</code>")

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast_handler(client, message):
    if not message.reply_to_message: return await message.reply_text("Reply to a message.")
    b_msg = await message.reply_text("<b>🚀 Processing...</b>")
    users = await db.get_all_users()
    success, failed = 0, 0
    async for user in users:
        try:
            await message.reply_to_message.copy(user['id'])
            success += 1
        except: failed += 1
    await b_msg.edit(f"<b>✅ Broadcast Done!</b>\n\nSuccess: {success}\nFailed: {failed}")

# --- SETTINGS & CALLBACKS ---
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if query.data != "check_fsub_btn":
        if not await check_fsub(client, query): return

    if query.data == "check_fsub_btn":
        if await check_fsub(client, query):
            await query.message.delete()
            await send_start(client, query.message)
            
    elif query.data == "help":
        await query.message.edit_caption(caption=DETAILED_HELP, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back 🔙", callback_data="back_start")]]))

    elif query.data == "settings_menu":
        mode = await db.get_upload_mode(user_id)
        chat = await db.get_target_chat(user_id)
        btn_text = "📁 Mode: PM" if mode == "PM" else "📢 Mode: CHANNEL"
        next_m = "Channel" if mode == "PM" else "PM"
        text = f"<b>⚙️ Settings</b>\n\n<b>Current Mode:</b> {mode}\n<b>Target:</b> {chat or 'Private'}"
        await query.message.edit_caption(caption=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, callback_data=f"set_mode_{next_m}")],[InlineKeyboardButton("Back 🔙", callback_data="back_start")]]))

    elif query.data.startswith("set_mode_"):
        await db.set_upload_mode(user_id, query.data.split("_")[2])
        await query.answer("Mode Updated!")
        # Refresh settings
        mode = await db.get_upload_mode(user_id)
        chat = await db.get_target_chat(user_id)
        btn_text = "📁 Mode: PM" if mode == "PM" else "📢 Mode: CHANNEL"
        next_m = "Channel" if mode == "PM" else "PM"
        await query.message.edit_caption(caption=f"<b>⚙️ Settings</b>\n\n<b>Current Mode:</b> {mode}\n<b>Target:</b> {chat or 'Private'}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, callback_data=f"set_mode_{next_m}")],[InlineKeyboardButton("Back 🔙", callback_data="back_start")]]))

    elif query.data == "back_start":
        await query.message.delete()
        await send_start(client, query.message)

# --- USER COMMANDS ---
@Client.on_message(filters.command("set_thumb") & filters.private)
async def set_thumbnail(client, message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply_text("❌ Reply to a photo with /set_thumb")
    await db.set_thumb(message.from_user.id, message.reply_to_message.photo.file_id)
    await message.reply_text("✅ **Thumbnail Saved!**")

@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_task(client, message):
    user_id = message.from_user.id
    if batch_temp.IS_BATCH.get(user_id) == False:
        batch_temp.IS_BATCH[user_id] = True
        await message.reply_text("🛑 **Stopping...**")
    else:
        await message.reply_text("❌ Nothing to cancel.")

@Client.on_message(filters.command("set_caption") & filters.private)
async def set_caption_cmd(client, message):
    if len(message.command) < 2: return await message.reply("<b>Usage:</b> <code>/set_caption Your Text</code>")
    await db.set_caption(message.from_user.id, message.text.split(None, 1)[1])
    await message.reply("✅ **Caption Updated!**")

# --- CORE PROCESSING ---
@Client.on_message(filters.text & filters.private)
async def save(client: Client, message: Message):
    if "https://t.me/" not in message.text: return
    if not await check_fsub(client, message): return
    
    user_id = message.from_user.id
    # Verification check
    v_cfg = await db.get_verify_config()
    if v_cfg.get('is_on') and not await db.get_verify_status(user_id):
        return await message.reply("Verify first!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Verify 🔓", callback_data="gen_link")]]))

    if batch_temp.IS_BATCH.get(user_id) == False:
        return await message.reply_text("❌ Task already running.")

    # Link Parsing
    links = message.text.split("/")
    id_range = links[-1].replace("?single","").split("-")
    f_id = int(id_range[0].strip())
    t_id = int(id_range[1].strip()) if len(id_range) > 1 else f_id
    
    # Logging
    if LOG_CHANNEL:
        await client.send_message(LOG_CHANNEL, f"<b>#work</b>\nUser: {message.from_user.first_name}\nFiles: {t_id-f_id+1}")

    # Session Handling
    is_p = "/c/" in message.text
    acc = client
    if is_p:
        sess = await db.get_session(user_id)
        if not sess: return await message.reply("❌ Login first.")
        acc = Client("saver", session_string=sess, api_hash=API_HASH, api_id=API_ID)
        await acc.connect()

    batch_temp.IS_BATCH[user_id] = False
    for msgid in range(f_id, t_id + 1):
        if batch_temp.IS_BATCH.get(user_id) == True: break
        c_id = int("-100" + links[4]) if is_p else links[3]
        try: await handle_private(client, acc, message, c_id, msgid)
        except: pass
        await asyncio.sleep(WAITING_TIME)

    if is_p: await acc.disconnect()
    batch_temp.IS_BATCH[user_id] = True
    await message.reply("✅ **Completed!**")

async def handle_private(client, acc, message, chatid, msgid):
    msg = await acc.get_messages(chatid, msgid)
    if not msg or msg.empty: return 
    
    user_id = message.from_user.id
    mode = await db.get_upload_mode(user_id)
    t_chat = int(await db.get_target_chat(user_id)) if (mode == "Channel") else message.chat.id
    
    cap_format = await db.get_caption(user_id)
    thumb_id = await db.get_thumb(user_id)

    if not msg.media:
        if msg.text: await client.send_message(t_chat, msg.text, entities=msg.entities)
        return

    smsg = await client.send_message(message.chat.id, "⏳ **Processing...**")
    media = getattr(msg, msg.media.value)
    f_name = getattr(media, "file_name", "No Name")
    f_size = get_readable_file_size(getattr(media, "file_size", 0))
    
    # Feeling/Tag logic
    caption = cap_format.replace("{file_name}", f_name).replace("{file_size}", f_size).replace("{file_caption}", msg.caption or "") if cap_format else (msg.caption or "")

    file_path = None
    thumb_path = None
    try:
        file_path = await acc.download_media(msg, progress=progress_for_pyrogram, progress_args=("📥 **Downloading...**", smsg, time.time()))
        thumb_path = await client.download_media(thumb_id) if thumb_id else None
        
        args = {"chat_id": t_chat, "caption": caption, "parse_mode": enums.ParseMode.HTML, "progress": progress_for_pyrogram, "progress_args": ("📤 **Uploading...**", smsg, time.time())}
        
        if msg.document: await client.send_document(document=file_path, thumb=thumb_path, **args)
        elif msg.video: await client.send_video(video=file_path, thumb=thumb_path, **args)
        elif msg.photo: await client.send_photo(photo=file_path, caption=caption)
        elif msg.audio: await client.send_audio(audio=file_path, thumb=thumb_path, **args)
    finally:
        if file_path and os.path.exists(file_path): os.remove(file_path)
        if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
        await smsg.delete()

# End of Code
