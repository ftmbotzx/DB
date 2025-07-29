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

@Client.on_message(filters.command("user") & filters.reply)
async def process_usehhjjjr_file(client, message):
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".txt"):
        await message.reply("❗ Please reply to a valid .txt file containing lines in user - spotify_url format.")
        return

    args = message.command
    skip_index = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0

    file_path = await client.download_media(doc)

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    total_users = len(lines)
    if total_users == 0:
        await message.reply("⚠️ The file is empty or has no valid lines.")
        return

    status_msg = await message.reply(f"⏳ Starting to process {total_users} users (Skipping first {skip_index})...")

    all_users_data = []
    batch_data = []
    batch_start_index = skip_index + 1
    skipped_users = []

    for user_index, line in enumerate(lines, start=1):
        if user_index <= skip_index:
            skipped_users.append(user_index)
            continue

        if "-" not in line:
            skipped_users.append(user_index)
            continue

        user_name, url = map(str.strip, line.split("-", 1))
        user_id = extract_user_id(url)

        if not user_id:
            skipped_users.append(user_index)
            continue

        try:
            await status_msg.edit(f"🔍 [{user_index}/{total_users}] Fetching playlists for {user_name} ({user_id})...")

            playlists = sp.user_playlists(user_id)
            if not playlists['items']:
                batch_data.append(f"{user_name} - {url} (No playlists)")
                continue

            while playlists:
                for playlist in playlists['items']:
                    pname = playlist.get("name", "Unnamed Playlist")
                    purl = playlist.get("external_urls", {}).get("spotify", "URL not found")
                    batch_data.append(f"{user_name} - {pname} - {purl}")
                if playlists.get('next'):
                    playlists = sp.next(playlists)
                else:
                    break

        except Exception as e:
            logger.error(f"Error processing {user_name} ({user_id}): {e}")
            batch_data.append(f"{user_name} - ERROR: {str(e)}")
            continue

        if len(batch_data) >= 50 or user_index == total_users:
            batch_end_index = user_index
            timestamp = int(time.time())
            file_name = f"user_playlists_{batch_start_index}_to_{batch_end_index}_{timestamp}.txt"

            with open(file_name, "w", encoding="utf-8") as f:
                for line in batch_data:
                    f.write(f"{line}\n")

            caption_lines = [
                f"📂 User Batch: {batch_start_index} to {batch_end_index}",
                f"✅ Total entries: {len(batch_data)}"
            ]
            if skipped_users:
                skipped_in_batch = [i for i in skipped_users if batch_start_index <= i <= batch_end_index]
                if skipped_in_batch:
                    caption_lines.append(f"⚠️ Skipped users: {', '.join(map(str, skipped_in_batch))}")

            await client.send_document(
                chat_id=message.chat.id,
                document=file_name,
                caption="\n".join(caption_lines)
            )

            os.remove(file_name)
            batch_data = []
            batch_start_index = user_index + 1

    await status_msg.edit("🎉 All users processed. Check chat for playlist batches.")
    os.remove(file_path)
