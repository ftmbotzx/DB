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

# Spotify Client Manager
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

SPOTIFY_PLAYLIST_REGEX = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"

@Client.on_message(filters.command("creators") & filters.reply)
async def get_creators_from_playlists(client: Client, message: Message):
    # Check if replied message has document
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Please reply to a `.txt` file containing Spotify playlist links.")

    # Download the replied .txt file
    file_path = await message.reply_to_message.download()
    creators_dict = {}

    try:
        # Read content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract playlist IDs
        playlist_ids = re.findall(SPOTIFY_PLAYLIST_REGEX, content)
        total = len(playlist_ids)
        logger.info(f"Found {total} playlists to process.")
        status_msg = await message.reply(f"🌀 Found {total} playlists. Extracting creators...")

        for idx, pid in enumerate(playlist_ids, start=1):
            try:
                playlist_info = await client_manager.make_request(f"https://api.spotify.com/v1/playlists/{pid}")
                if not playlist_info:
                    logger.warning(f"Failed to fetch playlist {pid}")
                    continue
                    
                owner = playlist_info.get("owner", {})
                owner_name = owner.get("display_name", "Unknown")
                owner_id = owner.get("id", None)
                if owner_id:
                    owner_url = f"https://open.spotify.com/user/{owner_id}"
                else:
                    owner_url = "N/A"

                # Add to dict unique creators by owner name (or owner id)
                creators_dict[owner_name] = owner_url
                logger.info(f"Got creator: {owner_name} ({owner_url}) from playlist {pid}")
            except Exception as e:
                logger.warning(f"Error fetching playlist {pid}: {e}")

            if idx % 10 == 0 or idx == total:
                await status_msg.edit(f"🔍 Extracted creators from {idx}/{total} playlists...")
                
                # Log current client status every 50 playlists
                if idx % 50 == 0:
                    status_info = client_manager.get_current_client_info()
                    logger.info(f"Progress: {idx}/{total}, Client: {status_info['client_index']+1}/{status_info['total_clients']}, IP: {status_info['current_ip']}")

        if not creators_dict:
            return await message.reply("❌ No creators found.")

        timestamp = int(time.time())
        result_file = f"creators_list_{timestamp}.txt"
        with open(result_file, "w", encoding="utf-8") as f:
            for idx, (name, url) in enumerate(sorted(creators_dict.items()), 1):
                f.write(f"{idx}. {name} - {url}\n")
              
        await message.reply_document(result_file, caption=f"✅ Found {len(creators_dict)} unique playlist creators.")
        os.remove(result_file)

    except Exception as e:
        logger.exception("An error occurred while extracting creators.")
        await message.reply(f"❌ Error: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
