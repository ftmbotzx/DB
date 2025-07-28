import logging
from pyrogram import Client, filters
from pyrogram.types import Message
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import os
import asyncio
import time

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# Spotify credentials
SPOTIFY_CLIENT_ID = "c6e8b0da7751415e848a97f309bc057d"
SPOTIFY_CLIENT_SECRET = "97d40c2c7b7948589df58d838b8e9e68"

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

SPOTIFY_PLAYLIST_REGEX = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"


# === Helper: send batch of creators ===
async def send_creator_batch(client, chat_id, creators_dict, batch_counter):
    if not creators_dict:
        return

    file_path = f"creators_batch_{batch_counter}.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        for idx, (name, url) in enumerate(sorted(creators_dict.items()), 1):
            f.write(f"{idx}. {name} - {url}\n")

    await client.send_document(
        chat_id=chat_id,
        document=file_path,
        caption=f"📦 Batch #{batch_counter}: {len(creators_dict)} creators"
    )
    os.remove(file_path)


@Client.on_message(filters.command("creators") & filters.reply)
async def get_creators_from_playlists(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Please reply to a `.txt` file containing Spotify playlist links.")

    file_path = await message.reply_to_message.download()
    all_creators_dict = {}
    current_batch_dict = {}

    last_batch_time = time.time()
    batch_counter = 1

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        playlist_ids = re.findall(SPOTIFY_PLAYLIST_REGEX, content)
        total = len(playlist_ids)
        logger.info(f"Found {total} playlists to process.")
        status_msg = await message.reply(f"🌀 Found {total} playlists. Extracting creators...")

        for idx, pid in enumerate(playlist_ids, start=1):
            try:
                playlist_info = sp.playlist(pid)
                owner = playlist_info.get("owner", {})
                owner_name = owner.get("display_name", "Unknown")
                owner_id = owner.get("id", None)
                owner_url = f"https://open.spotify.com/user/{owner_id}" if owner_id else "N/A"

                if owner_name not in all_creators_dict:
                    all_creators_dict[owner_name] = owner_url
                    current_batch_dict[owner_name] = owner_url

                logger.info(f"Got creator: {owner_name} ({owner_url}) from playlist {pid}")
            except Exception as e:
                logger.warning(f"Error fetching playlist {pid}: {e}")

            # Batch send after 5 minutes
            now = time.time()
            if now - last_batch_time > 300:
                await send_creator_batch(client, message.chat.id, current_batch_dict, batch_counter)
                current_batch_dict.clear()
                batch_counter += 1
                last_batch_time = now

            if idx % 10 == 0 or idx == total:
                await status_msg.edit(f"🔍 Extracted creators from {idx}/{total} playlists...")

            await asyncio.sleep(0.5)

        # Final batch (remaining)
        if current_batch_dict:
            await send_creator_batch(client, message.chat.id, current_batch_dict, batch_counter)

        # Final full file with all unique creators
        final_file = f"creators_full_{int(time.time())}.txt"
        with open(final_file, "w", encoding="utf-8") as f:
            for idx, (name, url) in enumerate(sorted(all_creators_dict.items()), 1):
                f.write(f"{idx}. {name} - {url}\n")

        await message.reply_document(final_file, caption=f"✅ Total unique creators: {len(all_creators_dict)}")
        os.remove(final_file)

    except Exception as e:
        logger.exception("An error occurred while extracting creators.")
        await message.reply(f"❌ Error: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
