import asyncio
import base64
import logging
import os
import random
import re
import string
import time

from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import *
from helper_func import *
from database.database import add_user, del_user, full_userbase, present_user

# Define BroadcastStats class
class BroadcastStats:
    """Track broadcast statistics."""
    def __init__(self):
        self.total = 0
        self.successful = 0
        self.blocked = 0
        self.deleted = 0
        self.unsuccessful = 0

# Function to generate a progress bar with stars
def generate_progress_bar(current, total, length=20):
    """Generate a progress bar with stars."""
    completed = int(length * current / total)
    remaining = length - completed
    bar = f"[{'★' * completed}{'☆' * remaining}]"
    return bar

def clean_caption(text, add_text=True):
    """Clean caption with text addition and language conversion"""
    try:
        if not text:
            return ""
        cleaned = text.replace("-UtsavTV", "")
        cleaned = cleaned.replace("Tamil", "Kannada")
        if add_text and ".mkv" in cleaned:
            base, ext = cleaned.rsplit('.mkv', 1)
            cleaned = f"{base} @SB_KAN.mkv{ext}"
        return cleaned.strip()
    except:
        return text

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    if not await present_user(id):
        try:
            await add_user(id)
        except:
            pass
    text = message.text
    if len(text)>7:
        try:
            base64_string = text.split(" ", 1)[1]
        except:
            return
        string = await decode(base64_string)
        argument = string.split("-")
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
            except:
                return
            if start <= end:
                ids = range(start,end+1)
            else:
                ids = []
                i = start
                while True:
                    ids.append(i)
                    i -= 1
                    if i < end:
                        break
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except:
                return
        temp_msg = await message.reply("Please wait...")
        try:
            messages = await get_messages(client, ids)
        except:
            await message.reply_text("Something went wrong..!")
            return
        await temp_msg.delete()

        track_msgs = []

        for msg in messages:
            if bool(CUSTOM_CAPTION) and (bool(msg.document) or bool(msg.video)):
                filename = msg.document.file_name if msg.document else (msg.video.file_name if msg.video else "")
                cleaned_caption = clean_caption(msg.caption.html if msg.caption else "", add_text=False)
                caption = CUSTOM_CAPTION.format(
                    previouscaption=cleaned_caption,
                    filename=clean_caption(filename, add_text=False)
                )
            else:
                caption = clean_caption(msg.caption.html if msg.caption else "", add_text=False)

            if DISABLE_CHANNEL_BUTTON:
                reply_markup = msg.reply_markup
            else:
                reply_markup = None

            if AUTO_DELETE_TIME and AUTO_DELETE_TIME > 0:
                try:
                    copied_msg_for_deletion = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    if copied_msg_for_deletion:
                        track_msgs.append(copied_msg_for_deletion)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    copied_msg_for_deletion = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    if copied_msg_for_deletion:
                        track_msgs.append(copied_msg_for_deletion)
            else:
                try:
                    await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    await asyncio.sleep(0.5)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                except:
                    pass

        if track_msgs:
            delete_data = await client.send_message(
                chat_id=message.from_user.id,
                text=AUTO_DELETE_MSG.format(time=AUTO_DELETE_TIME)
            )
            asyncio.create_task(delete_file(track_msgs, client, delete_data))
        return
    else:
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("😊 About Me", callback_data = "about"),
                    InlineKeyboardButton("🔒 Close", callback_data = "close")
                ]
            ]
        )
        if START_PIC:
            await message.reply_photo(
                photo=START_PIC,
                caption=START_MSG.format(
                    first=message.from_user.first_name,
                    last=message.from_user.last_name,
                    username=None if not message.from_user.username else '@' + message.from_user.username,
                    mention=message.from_user.mention,
                    id=message.from_user.id
                ),
                reply_markup=reply_markup,
                quote=True
            )
        else:
            await message.reply_text(
                text=START_MSG.format(
                    first=message.from_user.first_name,
                    last=message.from_user.last_name,
                    username=None if not message.from_user.username else '@' + message.from_user.username,
                    mention=message.from_user.mention,
                    id=message.from_user.id
                ),
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                quote=True
            )
        return

    
#=====================================================================================##

WAIT_MSG = """"<b>Processing ...</b>"""

REPLY_ERROR = """<code>Use this command as a replay to any telegram message with out any spaces.</code>"""

#=====================================================================================##

    
    
@Bot.on_message(filters.command('start') & filters.private)
async def not_joined(client: Client, message: Message):
    try:
        # Get channel info first
        try:
            chat = await client.get_chat(int(FORCE_SUB_CHANNEL))
        except Exception as e:
            print(f"Failed to get channel info: {e}")
            return await message.reply("❌ Force subscription channel is not properly configured.")

        # Get the channel link
        if JOIN_REQUEST_ENABLE:
            try:
                invite = await client.create_chat_invite_link(
                    chat_id=int(FORCE_SUB_CHANNEL),
                    creates_join_request=True
                )
                ButtonUrl = invite.invite_link
            except Exception as e:
                print(f"Failed to create join request link: {e}")
                ButtonUrl = None
        else:
            if chat.username:
                ButtonUrl = f"https://t.me/{chat.username}"
            else:
                try:
                    ButtonUrl = chat.invite_link
                    if not ButtonUrl:
                        ButtonUrl = await client.export_chat_invite_link(int(FORCE_SUB_CHANNEL))
                except Exception as e:
                    print(f"Failed to get/create invite link: {e}")
                    return await message.reply("❌ Bot needs to be admin in the force subscription channel with invite link permissions.")

        if not ButtonUrl:
            return await message.reply("❌ Could not get channel link. Please check bot permissions.")

        buttons = [
            [
                InlineKeyboardButton(
                    "📢 Join Channel",
                    url=ButtonUrl
                )
            ]
        ]

        if len(message.command) > 1:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text='🔄 Try Again',
                        url=f"https://t.me/{client.username}?start={message.command[1]}"
                    )
                ]
            )

        await message.reply(
            text=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Error in not_joined: {e}")
        await message.reply("❌ An error occurred. Please make sure the bot is properly configured.")

@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def broadcast_handler(client: Bot, message: Message):
    """Handle broadcast command with optional pinning"""
    if not message.reply_to_message:
        msg = await message.reply("Please reply to a message to broadcast it.")
        await asyncio.sleep(8)
        await msg.delete()
        return

    # Check if pin option is specified
    should_pin = False
    if len(message.command) > 1:
        pin_arg = message.command[1].lower()
        should_pin = pin_arg in ['pin', 'true', '1', 'yes']

    stats = BroadcastStats()
    status_msg = await message.reply("<i>Broadcasting message... This will take some time</i>")
    start_time = time.time()  # Record start time
    
    try:
        user_ids = await full_userbase()
        broadcast_msg = message.reply_to_message
        total_users = len(user_ids)
        update_interval = max(1, total_users // 100)  # Update every 1% of total users

        for user_id in user_ids:
            stats.total += 1
            try:
                sent_msg = await broadcast_msg.copy(user_id)
                if should_pin:
                    await client.pin_chat_message(
                        chat_id=user_id,
                        message_id=sent_msg.id,
                        disable_notification=True,
                        both_sides=True
                    )
                stats.successful += 1
                
            except FloodWait as e:
                await asyncio.sleep(e.x)
                try:
                    sent_msg = await broadcast_msg.copy(user_id)
                    if should_pin:
                        await client.pin_chat_message(
                            chat_id=user_id,
                            message_id=sent_msg.id,
                            disable_notification=True,
                            both_sides=True
                        )
                    stats.successful += 1
                except Exception:
                    stats.unsuccessful += 1
                    
            except UserIsBlocked:
                await del_user(user_id)
                stats.blocked += 1
                
            except InputUserDeactivated:
                await del_user(user_id)
                stats.deleted += 1
                
            except Exception as e:
                print(f"Failed to send message to {user_id}: {e}")
                stats.unsuccessful += 1

            # Update status message periodically
            if stats.total % update_interval == 0:
                elapsed_time = time.time() - start_time
                progress = stats.total / total_users
                estimated_total_time = elapsed_time / progress if progress > 0 else 0
                remaining_time = estimated_total_time - elapsed_time

                progress_bar = generate_progress_bar(stats.total, total_users, length=20)
                await status_msg.edit(
                    f"📡 <i>Broadcast in Progress...</i>\n\n"
                    f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
                    f"✅ <b>Delivered:</b> <code>{stats.successful}</code>\n"
                    f"⛔ <b>Blocked:</b> <code>{stats.blocked}</code>\n"
                    f"💀 <b>Deleted:</b> <code>{stats.deleted}</code>\n"
                    f"⚠️ <b>Failed:</b> <code>{stats.unsuccessful}</code>\n\n"
                    f"Progress: {progress_bar} {stats.total}/{total_users}\n"
                    f"⏳ <b>Time Remaining:</b> <code>{int(remaining_time)}s</code>\n\n"
                    f"⏳ Please wait while we complete the broadcast..."
                )

        # Final status update
        elapsed_time = time.time() - start_time
        success_rate = (stats.successful / total_users) * 100 if total_users > 0 else 0
        final_status = f"""🎉 <b>Broadcast Completed!</b>

📊 <b>Summary:</b>
👥 <b>Total Users:</b> <code>{total_users}</code>
✅ <b>Delivered:</b> <code>{stats.successful}</code>
⛔ <b>Blocked:</b> <code>{stats.blocked}</code>
💀 <b>Deleted:</b> <code>{stats.deleted}</code>
⚠️ <b>Failed:</b> <code>{stats.unsuccessful}</code>
📈 <b>Success Rate:</b> <code>{success_rate:.2f}%</code>
⏱️ <b>Time Taken:</b> <code>{int(elapsed_time)}s</code>

Progress: [{'★' * 20}] 100% Complete ✅

📌 <b>Message Pinning:</b> <i>{'Enabled ✅' if should_pin else 'Not Enabled 🚫'}</i>
🚀 Thank you for using the broadcast feature!"""

        await status_msg.edit(final_status)

    except Exception as e:
        await status_msg.edit(f"<b>❌ Broadcast Failed</b>\n\n<code>{str(e)}</code>")

# Function to handle file deletion
async def delete_files(messages, client, k):
    await asyncio.sleep(FILE_AUTO_DELETE)  # Wait for the duration specified in config.py
    
    for msg in messages:
        try:
            await client.delete_messages(chat_id=msg.chat.id, message_ids=[msg.id])
        except Exception as e:
            print(f"The attempt to delete the media {msg.id} was unsuccessful: {e}")

    # Safeguard against k.command being None or having insufficient parts
    command_part = k.command[1] if k.command and len(k.command) > 1 else None

    if command_part:
        button_url = f"https://t.me/{client.username}?start={command_part}"
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ!", url=button_url)]
            ]
        )
    else:
        keyboard = None

    # Edit message with the button
    await k.edit_text("<b><i>Your Video / File Is Successfully Deleted ✅</i></b>", reply_markup=keyboard)

@Bot.on_callback_query(filters.regex('^checksub_'))
async def check_sub_callback(client: Bot, callback_query: CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        command_arg = callback_query.data.split('_')[1]
        
        # Check if user has subscribed
        if await is_subscribed(None, client, callback_query):
            # User has subscribed, send success message
            await callback_query.answer("✅ Thank you for subscribing!", show_alert=True)
            
            # Delete the force subscribe message
            await callback_query.message.delete()
            
            # Start command processing
            if command_arg:
                try:
                    base64_string = command_arg
                    string = await decode(base64_string)
                    argument = string.split("-")
                    if len(argument) == 3:
                        start = int(int(argument[1]) / abs(client.db_channel.id))
                        end = int(int(argument[2]) / abs(client.db_channel.id))
                        ids = range(start, end + 1)
                    elif len(argument) == 2:
                        ids = [int(int(argument[1]) / abs(client.db_channel.id))]
                    
                    # Get messages
                    temp_msg = await client.send_message(chat_id=user_id, text="Please wait...")
                    messages = await get_messages(client, ids)
                    await temp_msg.delete()
                    
                    # Send messages
                    for msg in messages:
                        try:
                            await msg.copy(chat_id=user_id, protect_content=PROTECT_CONTENT)
                            await asyncio.sleep(0.5)
                        except FloodWait as e:
                            await asyncio.sleep(e.value)
                            await msg.copy(chat_id=user_id, protect_content=PROTECT_CONTENT)
                        except Exception:
                            pass
                except Exception as e:
                    await client.send_message(chat_id=user_id, text=f"Error: {str(e)}")
            else:
                # Send start message for direct /start command
                reply_markup = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("😊 About Me", callback_data="about"),
                            InlineKeyboardButton("🔒 Close", callback_data="close")
                        ]
                    ]
                )
                await client.send_message(
                    chat_id=user_id,
                    text=START_MSG.format(
                        first=callback_query.from_user.first_name,
                        last=callback_query.from_user.last_name,
                        username=None if not callback_query.from_user.username else '@' + callback_query.from_user.username,
                        mention=callback_query.from_user.mention,
                        id=callback_query.from_user.id
                    ),
                    reply_markup=reply_markup
                )
        else:
            # User hasn't subscribed yet
            await callback_query.answer("❌ Please join the channel first!", show_alert=True)
    except Exception as e:
        logger.error(f"Error in check_sub_callback: {e}")
        await callback_query.answer("❌ An error occurred. Please try again.", show_alert=True)
