import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import os
import asyncio
import time

# -------- Logger Setup --------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# -------- Spotify Client Manager --------
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from spotify_client_manager import SpotifyClientManager

# Load all clients from clients.json
with open("clients.json", "r") as f:
    clients_data = json.load(f)
    clients = clients_data["clients"]

# Initialize the client manager with all available clients
client_manager = SpotifyClientManager(clients)

# -------- Regex to extract playlist IDs --------
SPOTIFY_PLAYLIST_REGEX = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"

# -------- Extract tracks from one playlist --------
async def extract_track_ids_spotify(playlist_id):
    try:
        track_ids = []
        offset = 0
        limit = 50
        
        while True:
            endpoint = f"playlists/{playlist_id}/tracks"
            params = {"limit": limit, "offset": offset}
            response = await client_manager.make_request(f"https://api.spotify.com/v1/{endpoint}", params)
            
            if not response or "items" not in response:
                break
                
            tracks = response["items"]
            
            for item in tracks:
                track = item.get("track")
                if track and track.get("id"):
                    track_ids.append(track["id"])
            
            # Check if there are more tracks to fetch
            if len(tracks) < limit or not response.get("next"):
                break
                
            offset += limit
            
            # Log client info every 500 tracks
            if len(track_ids) % 500 == 0:
                info = client_manager.get_current_client_info()
                logger.info(f"Progress: {len(track_ids)} tracks, using client {info['client_index']+1}/{info['total_clients']}, IP {info['current_ip']}")

        logger.info(f"✅ Extracted {len(track_ids)} tracks from playlist {playlist_id}")
        return track_ids
    except Exception as e:
        logger.error(f"❌ Error scraping playlist {playlist_id}: {e}")
        return []

# -------- Command Handler --------
@Client.on_message(filters.command("extracttracks") & filters.reply)
async def extract_from_txt(client: Client, message: Message):
    if not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a `.txt` file containing Spotify playlist links.")

    # Parse start index from command args, default 0
    try:
        start_index = int(message.command[1]) if len(message.command) > 1 else 0
    except:
        return await message.reply("⚠️ Invalid start index. Usage: /extracttracks 0")

    file_path = await message.reply_to_message.download()
    final_track_ids = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        playlist_ids = re.findall(SPOTIFY_PLAYLIST_REGEX, content)
        total = len(playlist_ids)

        if start_index >= total:
            return await message.reply(f"⚠️ Start index {start_index} is out of range (total {total} playlists).")

        logger.info(f"📂 Found {total} playlist links.")
        logger.info(f"🎯 Starting extraction from playlist index {start_index + 1}/{total}")

        status = await message.reply(
            f"🌀 Found {total} playlists.\n➡️ Starting from index {start_index + 1}..."
        )

        batch_counter = 1
        batch_start = start_index + 1  # human-readable playlist number (1-based)
        batch_tracks = []

        for idx in range(start_index, total):
            pid = playlist_ids[idx]
            logger.info(f"Processing playlist {idx + 1}/{total}")

            ids = await extract_track_ids_spotify(pid)
            batch_tracks.extend(ids)
            final_track_ids.extend(ids)

            # Every 500 playlists or at the end, send batch file
            if (idx + 1 - start_index) % 500 == 0 or (idx + 1) == total:
                batch_end = idx + 1
                unique_tracks = list(set(batch_tracks))
                timestamp = int(time.time())
                filename = f"tracks_batch_{batch_start}_to_{batch_end}_{timestamp}.txt"

                with open(filename, "w") as f:
                    f.write("\n".join(unique_tracks))

                await message.reply_document(filename, caption=f"📦 Batch {batch_counter} sent: playlists {batch_start} to {batch_end}")

                logger.info(f"Batch {batch_counter} sent: playlists {batch_start} to {batch_end}")

                os.remove(filename)
                batch_counter += 1
                batch_start = batch_end + 1
                batch_tracks.clear()

            # Edit progress message every 5 playlists
            if (idx + 1) % 5 == 0 or (idx + 1) == total:
                try:
                    await status.edit(f"🔍 Extracted {idx + 1}/{total} playlists.")
                except MessageNotModified:
                    pass

            await asyncio.sleep(0.5)

        await status.edit(f"✅ Extraction complete! Total playlists processed: {total - start_index}. Total unique tracks: {len(set(final_track_ids))}")

    except Exception as e:
        logger.exception("An error occurred during extraction.")
        await message.reply(f"❌ Error: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
