from pyrogram import Client, filters
import os
import time
import logging 
import aiohttp
import requests
import asyncio
import subprocess
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import LOG_CHANNEL, ADMINS, BOT_TOKEN
from pyrogram.types import Message
from pyrogram.enums import ChatType
from database.db import db 


@Client.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("👋 Hello! Bot is running successfully!")


@Client.on_message(filters.command("restart"))
async def git_pull(client, message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text("🚫 **You are not authorized to use this command!**")
      
    working_directory = "/home/ubuntu/DBMAKKER"

    process = subprocess.Popen(
        "git pull https://github.com/Anshvachhani998/DBMAKKER",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE

    )

    stdout, stderr = process.communicate()
    output = stdout.decode().strip()
    error = stderr.decode().strip()
    cwd = os.getcwd()
    logging.info("Raw Output (stdout): %s", output)
    logging.info("Raw Error (stderr): %s", error)

    if error and "Already up to date." not in output and "FETCH_HEAD" not in error:
        await message.reply_text(f"❌ Error occurred: {os.getcwd()}\n{error}")
        logging.info(f"get dic {cwd}")
        return

    if "Already up to date." in output:
        await message.reply_text("🚀 Repository is already up to date!")
        return
      
    if any(word in output.lower() for word in [
        "updating", "changed", "insert", "delete", "merge", "fast-forward",
        "files", "create mode", "rename", "pulling"
    ]):
        await message.reply_text(f"📦 Git Pull Output:\n```\n{output}\n```")
        await message.reply_text("🔄 Git Pull successful!\n♻ Restarting bot...")

        subprocess.Popen("bash /home/ubuntu/DBMAKKER/start.sh", shell=True)
        os._exit(0)

    await message.reply_text(f"📦 Git Pull Output:\n```\n{output}\n```")


@Client.on_message(filters.command("dbcheck") & filters.user(ADMINS))
async def dbcheck_handler(client: Client, message: Message):
    try:
        # Total media documents
        media_count = await db.db["media"].count_documents({})

        # Total dump documents
        dump_count = await db.db["dump"].count_documents({})

        # Aapke other collections bhi ho toh unka yahan add karo:
        # example: user_count = await db.db["users"].count_documents({})

        text = (
            f"📊 **Database Stats:**\n\n"
            f"📁 Media Files: `{media_count}`\n"
            f"🗃️ Dump Entries: `{dump_count}`\n"
            # f"👤 Users: `{user_count}`\n"  # Add if needed
        )
        await message.reply(text)

    except Exception as e:
        await message.reply(f"❌ Error occurred: `{e}`")


@Client.on_message(filters.command("deleteall"))
async def delete_all_media(client, message):
    result = await db.media_col.delete_many({})
    await message.reply(f"🗑️ Deleted **{result.deleted_count}** entries from media DB.")
import os
import time
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# -------- Logger Setup --------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# -------- Spotify Credentials --------
SPOTIFY_CLIENT_ID = "9bef0c79a4854066b037dc94b0f2b317"
SPOTIFY_CLIENT_SECRET = "11b3d3eb75e449ac8af69c1ebecf8eab"

auth_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)

def extract_user_id(spotify_url: str) -> str:
    import re
    match = re.search(r"open\.spotify\.com/user/([a-zA-Z0-9]+)", spotify_url)
    if match:
        return match.group(1)
    return None

@Client.on_message(filters.command("user") & filters.reply & filters.document)
async def process_user_file(client: Client, message: Message):
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".txt"):
        await message.reply("❗ Please reply to a valid .txt file containing lines in user - spotify_url format.", parse_mode=None)
        return

    file_path = await client.download_media(doc)

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    total_users = len(lines)
    if total_users == 0:
        await message.reply("⚠️ The file is empty or has no valid lines.", parse_mode=None)
        return

    status_msg = await message.reply(f"⏳ Starting to process {total_users} users from the file...", parse_mode=None)

    global_total_tracks = 0
    all_users_track_ids = []

    for user_index, line in enumerate(lines, start=1):
        if "-" not in line:
            await message.reply(f"⚠️ Skipping invalid format line: {line}. Expected format: user - spotify_url", parse_mode=None)
            continue

        user_name, url = map(str.strip, line.split("-", 1))
        user_id = extract_user_id(url)

        if not user_id:
            await message.reply(f"⚠️ Invalid Spotify URL for user {user_name}: {url}", parse_mode=None)
            continue

        try:
            await status_msg.edit(
                f"🔍 [{user_index}/{total_users}] Fetching playlists for user: {user_name} ({user_id})...",
                parse_mode=None
            )

            playlists = sp.user_playlists(user_id)
            if not playlists['items']:
                await status_msg.edit(f"⚠️ No public playlists found for user {user_name}.", parse_mode=None)
                continue

            total_playlists = 0
            total_tracks_user = 0
            total_playlists_count = playlists.get("total") or None
            user_track_ids = []

            while playlists:
                for playlist in playlists['items']:
                    total_playlists += 1
                    pid = playlist['id']
                    pname = playlist['name']
                    tracks = sp.playlist_tracks(pid)
                    playlist_tracks_count = 0

                    while tracks:
                        for item in tracks['items']:
                            track = item['track']
                            if track:
                                user_track_ids.append(track['id'])
                                total_tracks_user += 1
                                playlist_tracks_count += 1
                        if tracks['next']:
                            tracks = sp.next(tracks)
                        else:
                            tracks = None

                    global_total_tracks += playlist_tracks_count

                    await status_msg.edit(
                        f"🔄 Processing User {user_index} / {total_users}\n"
                        f"🎵 Tracks found in current playlist: {playlist_tracks_count}\n"
                        f"📀 Playlists processed for this user: {total_playlists} / {total_playlists_count or '?'}\n"
                        f"🎵 Total tracks for this user: {total_tracks_user}\n\n"
                        f"👥 Total users processed: {user_index} / {total_users}\n"
                        f"🎧 Total tracks collected from ALL users: {global_total_tracks}",
                        parse_mode=None
                    )
                    await asyncio.sleep(1)

                if playlists['next']:
                    playlists = sp.next(playlists)
                else:
                    playlists = None

            unique_user_tracks = list(set(user_track_ids))
            all_users_track_ids.extend(unique_user_tracks)

            await status_msg.edit(
                f"✅ Completed [{user_index}/{total_users}]: {user_name}\n"
                f"📀 Total playlists: {total_playlists}\n"
                f"🎵 Unique tracks: {len(unique_user_tracks)}\n"
                f"🎧 Total tracks collected from ALL users: {global_total_tracks}",
                parse_mode=None
            )

        except Exception as e:
            await message.reply(f"❌ Error fetching tracks for {user_name}: {e}", parse_mode=None)
            logger.error(f"Error fetching tracks for user {user_id}: {e}")

    all_unique_tracks = list(set(all_users_track_ids))
    timestamp = int(time.time())
    file_name = f"all_users_tracks_{timestamp}.txt"

    with open(file_name, "w", encoding="utf-8") as f:
        for tid in all_unique_tracks:
            f.write(f"{tid}\n")

    await client.send_document(
        chat_id=message.chat.id,
        document=file_name,
        caption=f"✅ Total unique track IDs from all users: {len(all_unique_tracks)}"
    )
    os.remove(file_name)
    os.remove(file_path)

    await status_msg.edit("🎉 All users processed. Check your chat for the combined tracks file!", parse_mode=None)
