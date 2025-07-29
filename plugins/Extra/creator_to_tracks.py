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
async def process_user_file(client, message):
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".txt"):
        await message.reply("❗ Please reply to a valid .txt file containing lines in `User - SpotifyURL` format.")
        return

    args = message.command
    skip_index = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0

    file_path = await client.download_media(doc)
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    total_users = len(lines)
    if total_users == 0:
        await message.reply("⚠️ File is empty.")
        return

    status_msg = await message.reply(f"⏳ Starting to process {total_users} users...")

    batch_data = []
    skipped_users = []
    batch_start_index = None
    batch_number = 1
    current_batch_user_count = 0

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

        if batch_start_index is None:
            batch_start_index = user_index

        try:
            await status_msg.edit(f"📥 [{user_index}/{total_users}] Fetching playlists for: {user_name}")
            playlists = sp.user_playlists(user_id)

            has_playlist = False
            while playlists:
                for playlist in playlists['items']:
                    pname = playlist.get("name", "Unnamed")
                    purl = playlist.get("external_urls", {}).get("spotify", "N/A")
                    batch_data.append(f"{user_name} - {pname} - {purl}")
                    has_playlist = True
                if playlists.get("next"):
                    playlists = sp.next(playlists)
                else:
                    break

            if not has_playlist:
                batch_data.append(f"{user_name} - No public playlists found.")

        except Exception as e:
            batch_data.append(f"{user_name} - ERROR: {e}")
            skipped_users.append(user_index)
            continue

        current_batch_user_count += 1

        # 🧾 Send file every 50 users or last user
        if current_batch_user_count == 50 or user_index == total_users:
            batch_end_index = user_index
            file_name = f"user_batch_{batch_start_index}_to_{batch_end_index}.txt"

            with open(file_name, "w", encoding="utf-8") as f:
                for line in batch_data:
                    f.write(line + "\n")

            caption_lines = [
                f"📁 User Batch: {batch_start_index} to {batch_end_index}",
                f"🧾 Total entries: {len(batch_data)}"
            ]
            skipped_in_this_batch = [str(i) for i in skipped_users if batch_start_index <= i <= batch_end_index]
            if skipped_in_this_batch:
                caption_lines.append(f"⚠️ Skipped users: {', '.join(skipped_in_this_batch)}")

            await client.send_document(
                chat_id=message.chat.id,
                document=file_name,
                caption="\n".join(caption_lines)
            )

            os.remove(file_name)

            # Reset batch data
            batch_data = []
            current_batch_user_count = 0
            batch_start_index = None

    await status_msg.edit("✅ All users processed. Check chat for batches.")
    os.remove(file_path)
    
