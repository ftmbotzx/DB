import os
import time
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
# Removed spotipy imports - using client manager instead

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
        await message.reply("❗ Please reply to a valid .txt file containing lines in user - spotify_url format.")
        return

    file_path = await client.download_media(doc)

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    total_users = len(lines)
    if total_users == 0:
        await message.reply("⚠️ The file is empty or has no valid lines.")
        return

    status_msg = await message.reply(f"⏳ Starting to process {total_users} users from the file...")

    global_total_tracks = 0
    all_users_track_ids = []  # <-- New list to collect all users' tracks

    for user_index, line in enumerate(lines, start=1):
        if "-" not in line:
            await message.reply(f"⚠️ Skipping invalid format line: {line}. Expected format: user - spotify_url")
            continue

        user_name, url = map(str.strip, line.split("-", 1))
        user_id = extract_user_id(url)

        if not user_id:
            await message.reply(f"⚠️ Invalid Spotify URL for user {user_name}: {url}")
            continue

        try:
            await status_msg.edit(
                f"🔍 [{user_index}/{total_users}] Fetching playlists for user: **{user_name}** ({user_id})..."
            )

            playlists_response = await client_manager.make_request(f"https://api.spotify.com/v1/users/{user_id}/playlists", {"limit": 50})
            if not playlists_response:
                await status_msg.edit(f"⚠️ Failed to fetch playlists for user **{user_name}**.")
                continue
            
            playlists = playlists_response
            if not playlists['items']:
                await status_msg.edit(f"⚠️ No public playlists found for user **{user_name}**.")
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
                    # Get playlist tracks using client manager
                    offset = 0
                    playlist_tracks_count = 0
                    
                    while True:
                        tracks_response = await client_manager.make_request(
                            f"https://api.spotify.com/v1/playlists/{pid}/tracks",
                            {"limit": 50, "offset": offset}
                        )
                        
                        if not tracks_response or not tracks_response.get('items'):
                            break
                            
                        for item in tracks_response['items']:
                            track = item.get('track')
                            if track and track.get('id'):
                                user_track_ids.append(track['id'])
                                total_tracks_user += 1
                                playlist_tracks_count += 1
                        
                        if len(tracks_response['items']) < 50 or not tracks_response.get('next'):
                            break
                            
                        offset += 50

                    global_total_tracks += playlist_tracks_count

                    await status_msg.edit(
                        f"🔄 Processing User {user_index} / {total_users}\n"
                        f"🎵 Tracks found in current playlist: {playlist_tracks_count}\n"
                        f"📀 Playlists processed for this user: {total_playlists} / {total_playlists_count or '?'}\n"
                        f"🎵 Total tracks for this user: {total_tracks_user}\n\n"
                        f"👥 Total users processed: {user_index} / {total_users}\n"
                        f"🎧 Total tracks collected from ALL users: {global_total_tracks}"
                    )
                    await asyncio.sleep(1)

                # Check for next page of playlists
                if playlists.get('next'):
                    # Extract offset from next URL or increment manually
                    offset = playlists.get('offset', 0) + playlists.get('limit', 50)
                    playlists_response = await client_manager.make_request(
                        f"https://api.spotify.com/v1/users/{user_id}/playlists",
                        {"limit": 50, "offset": offset}
                    )
                    playlists = playlists_response if playlists_response else None
                else:
                    playlists = None

            unique_user_tracks = list(set(user_track_ids))
            all_users_track_ids.extend(unique_user_tracks)  # add user's unique tracks to global list

            await status_msg.edit(
                f"✅ Completed [{user_index}/{total_users}]: **{user_name}**\n"
                f"📀 Total playlists: {total_playlists}\n"
                f"🎵 Unique tracks: {len(unique_user_tracks)}\n"
                f"🎧 Total tracks collected from ALL users: {global_total_tracks}"
            )

        except Exception as e:
            await message.reply(f"❌ Error fetching tracks for **{user_name}**: {e}")
            logger.error(f"Error fetching tracks for user {user_id}: {e}")

    # After processing all users, write all unique tracks to one file
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

    await status_msg.edit("🎉 All users processed. Check your chat for the combined tracks file!")
