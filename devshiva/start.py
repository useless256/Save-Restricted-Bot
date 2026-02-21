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
from devshiva.strings import HELP_TXT
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

# --- FORCE SUBSCRIBE CHECK ---
async def check_fsub(client, message):
    FSUB_CHANNEL = -1003627956964 # Your Actual Channel ID
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

# --- START COMMAND & VERIFICATION ---
@Client.on_message(filters.command(["start"]) & filters.private)
async def send_start(client: Client, message: Message):
    if not await check_fsub(client, message): return
    
    user_id = message.from_user.id
    user_mention = message.from_user.mention

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        if LOG_CHANNEL:
            log_text = (f"<b>🆕 New User Started Bot</b>\n\n<b>👤 Name:</b> {user_mention}\n"
                        f"<b>🆔 User ID:</b> <code>{user_id}</code>\n"
                        f"<b>📅 Date:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}")
            try: await client.send_message(LOG_CHANNEL, log_text)
            except: pass

    if len(message.command) > 1 and message.command[1].startswith("verify"):
        sent_time = last_link_gen.get(user_id, 0)
        if time.time() - sent_time < 30:
            btn = [[InlineKeyboardButton("Try Again 🔐", callback_data="gen_link")]]
            return await message.reply_text("<b>⚠️ Bypass Detected!</b>", reply_markup=InlineKeyboardMarkup(btn))
        await db.verify_user(user_id)
        return await message.reply_text("<b>Verification Successful! ✅</b>")

    is_verified = await db.get_verify_status(user_id)
    welcome_text = (
        f"<b>👋 Hi {message.from_user.mention}!</b>\n\n"
        "I am a powerful **Save Restricted Content Bot**.\n\n"
        f"{'✅ <b>Premium Active!</b>' if is_verified else '🔓 <b>Verify for 6h Access</b>'}"
    )

    buttons = [[InlineKeyboardButton("Help 🛠️", callback_data="help"), InlineKeyboardButton("Login 🔑", callback_data="login_process")],
               [InlineKeyboardButton("Settings ⚙️", callback_data="settings_menu")]]
    if not is_verified: buttons[1].append(InlineKeyboardButton("Verify Bot 🔓", callback_data="gen_link"))
    
    try: await message.reply_photo(photo="logo.png", caption=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))
    except: await message.reply_text(text=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

# --- CANCEL COMMAND ---
@Client.on_message(filters.command("cancel") & filters.private)
async def cancel_batch(client, message):
    user_id = message.from_user.id
    if batch_temp.IS_BATCH.get(user_id) == False: 
        batch_temp.IS_BATCH[user_id] = True 
        return await message.reply_text("⏳ **Batch cancellation requested...**")
    await message.reply_text("❌ No active task to cancel.")

# --- ADMIN COMMANDS ---
@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def get_stats(client, message):
    users_count = await db.total_users_count()
    await message.reply_text(f"<b>📊 Stats:</b> <code>{users_count}</code>")

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast_handler(client, message):
    if not message.reply_to_message: return await message.reply_text("Reply to a message.")
    b_msg = await message.reply_text("<b>🚀 Started...</b>")
    users = await db.get_all_users()
    success, failed = 0, 0
    async for user in users:
        try:
            await message.reply_to_message.copy(user['id'])
            success += 1
        except: failed += 1
    await b_msg.edit(f"<b>✅ Done!</b>\nSent: {success}\nFailed: {failed}")

# --- CALLBACKS ---
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if query.data != "check_fsub_btn":
        if not await check_fsub(client, query): return

    if query.data == "check_fsub_btn":
        if await check_fsub(client, query):
            await query.message.delete()
            await send_start(client, query.message)
    elif query.data == "login_process":
        await query.message.delete()
        try: await login_handler(client, query.message)
        except: pass
    elif query.data == "gen_link":
        config = await db.get_verify_config()
        if not config.get('is_on'): return await query.answer("Disabled.", show_alert=True)
        s_url, s_api = config.get('url'), config.get('api')
        token_link = f"https://t.me/{client.me.username}?start=verify_{user_id}"
        short_link = get_shortlink(s_url, s_api, token_link)
        last_link_gen[user_id] = time.time()
        btn = [[InlineKeyboardButton("Open Verification Link 🔓", url=short_link)]]
        await query.message.edit_caption(caption="<b>🔐 Verification Required</b>", reply_markup=InlineKeyboardMarkup(btn))
    elif query.data == "settings_menu":
        mode = await db.get_upload_mode(user_id)
        chat = await db.get_target_chat(user_id)
        settings_text = (f"<b>⚙️ Bot Configuration</b>\n\n<b>Mode:</b> {mode}\n<b>Target:</b> <code>{chat or 'PM'}</code>\n\n"
                         "• /set_caption, /set_thumb, /set_chat")
        await query.message.edit_caption(caption=settings_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back 🔙", callback_data="back_start")]]))
    elif query.data == "help":
        await query.message.edit_caption(caption=HELP_TXT, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back 🔙", callback_data="back_start")]]))
    elif query.data == "back_start":
        await query.message.delete()
        await send_start(client, query.message)

# --- SETTINGS: THUMB, CAPTION, CHAT ---
@Client.on_message(filters.command("set_thumb") & filters.private)
async def set_thumbnail(client, message):
    if not await check_fsub(client, message): return
    reply = message.reply_to_message
    if not reply or not reply.photo:
        return await message.reply_text("❌ Reply to a <b>Photo</b> to set custom thumbnail.")
    await db.set_thumb(message.from_user.id, reply.photo.file_id)
    await message.reply_text("✅ **Custom Thumbnail Saved!**")

@Client.on_message(filters.command("set_caption") & filters.private)
async def set_caption_cmd(client, message):
    if len(message.command) < 2: return await message.reply("Usage: /set_caption Text")
    await db.set_caption(message.from_user.id, message.text.split(None, 1)[1])
    await message.reply("✅ **Caption Saved!**")

@Client.on_message(filters.command("set_chat") & filters.private)
async def set_chat_cmd(client, message):
    if len(message.command) < 2: return await message.reply("Usage: /set_chat -100xxxxxx")
    await perform_set_chat(client, message, message.command[1])

@Client.on_message(filters.forwarded & filters.private)
async def forward_handler(client, message):
    if message.forward_from_chat:
        await perform_set_chat(client, message, message.forward_from_chat.id)

async def perform_set_chat(client, message, chat_id):
    try:
        target_chat = int(chat_id)
        bot_stat = await client.get_chat_member(target_chat, "me")
        if bot_stat.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return await message.reply("❌ Make me Admin in that channel first!")
        await db.set_target_chat(message.from_user.id, target_chat)
        await db.set_upload_mode(message.from_user.id, "Channel")
        await message.reply(f"✅ **Target Saved:** <code>{target_chat}</code>")
    except Exception as e: await message.reply(f"❌ **Error:** `{e}`")

# --- MAIN LOGIC ---
@Client.on_message(filters.text & filters.private)
async def save(client: Client, message: Message):
    if "https://t.me/" not in message.text: return
    if not await check_fsub(client, message): return
    
    user_id = message.from_user.id
    config = await db.get_verify_config()
    if config.get('is_on') and not await db.get_verify_status(user_id):
        return await message.reply("Verify first!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Verify 🔓", callback_data="gen_link")]]))

    if batch_temp.IS_BATCH.get(user_id) == False:
        return await message.reply_text("❌ Task running. Use /cancel to stop.")

    datas = message.text.split("/")
    temp = datas[-1].replace("?single","").split("-")
    fromID = int(temp[0].strip())
    toID = int(temp[1].strip()) if len(temp) > 1 else fromID
    
    total_files = (toID - fromID) + 1
    if LOG_CHANNEL:
        log_work = (f"<b>#work</b>\n<b>User:</b> {message.from_user.first_name}\n<b>Files:</b> {total_files}")
        try: await client.send_message(LOG_CHANNEL, log_work)
        except: pass

    is_private = "/c/" in message.text
    acc = None
    if is_private:
        user_data = await db.get_session(user_id)
        if not user_data: return await message.reply("❌ Login first.")
        acc = Client("saver", session_string=user_data, api_hash=API_HASH, api_id=API_ID)
        await acc.connect()
    else: acc = client

    batch_temp.IS_BATCH[user_id] = False
    for msgid in range(fromID, toID + 1):
        if batch_temp.IS_BATCH.get(user_id) == True:
            await message.reply_text("🛑 **Stopped!**")
            break
        chatid = int("-100" + datas[4]) if is_private else datas[3]
        try: await handle_private(client, acc, message, chatid, msgid)
        except: pass
        await asyncio.sleep(WAITING_TIME)

    if is_private and acc: await acc.disconnect()
    batch_temp.IS_BATCH[user_id] = True
    await message.reply("✅ **Completed!**")

# --- MEDIA HANDLER ---
async def handle_private(client: Client, acc, message: Message, chatid, msgid: int):
    try: msg = await acc.get_messages(chatid, msgid)
    except: return
    if not msg or msg.empty: return 
    
    user_id = message.from_user.id
    upload_mode = await db.get_upload_mode(user_id)
    target_id = await db.get_target_chat(user_id)
    try: target_chat = int(target_id) if (upload_mode == "Channel" and target_id) else message.chat.id
    except: target_chat = message.chat.id
    
    custom_caption = await db.get_caption(user_id)
    custom_thumb = await db.get_thumb(user_id)

    if not msg.media:
        if msg.text: await client.send_message(target_chat, msg.text, entities=msg.entities)
        return

    smsg = await client.send_message(message.chat.id, f"⏳ **Processing...** ({msgid})")
    media_obj = getattr(msg, msg.media.value)
    f_name = getattr(media_obj, "file_name", "No Name")
    f_size = get_readable_file_size(getattr(media_obj, "file_size", 0))
    final_cap = custom_caption.replace("{file_name}", f_name).replace("{file_size}", f_size).replace("{file_caption}", msg.caption or "") if custom_caption else (msg.caption or "")

    file = None
    ph_path = None
    try:
        file = await acc.download_media(msg, progress=progress_for_pyrogram, progress_args=("📥 **Downloading...**", smsg, time.time()))
        if custom_thumb: ph_path = await client.download_media(custom_thumb)
        
        common_args = {"chat_id": target_chat, "caption": final_cap, "parse_mode": enums.ParseMode.HTML, "thumb": ph_path, "progress": progress_for_pyrogram, "progress_args": ("📤 **Uploading...**", smsg, time.time())}
        
        if msg.document: await client.send_document(document=file, **common_args)
        elif msg.video: await client.send_video(video=file, **common_args)
        elif msg.photo: await client.send_photo(photo=file, caption=final_cap)
        elif msg.audio: await client.send_audio(audio=file, **common_args)
    except Exception as e: await smsg.edit(f"❌ Error: {e}")
    finally:
        if file and os.path.exists(file): os.remove(file)
        if ph_path and os.path.exists(ph_path): os.remove(ph_path)
        await smsg.delete()

# Don't Remove Credit 
# Ask Doubt on telegram @theprofessorreport_bot
