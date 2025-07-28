
from pyrogram import Client, filters
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from spotify_client_manager import SpotifyClientManager
import re

# Load all clients from clients.json
with open("clients.json", "r") as f:
    clients_data = json.load(f)
    clients = clients_data["clients"]

# Initialize the client manager with all available clients
client_manager = SpotifyClientManager(clients)

def extract_playlist_id(playlist_url: str) -> str:
    """Extract playlist ID from Spotify URL"""
    match = re.search(r"playlist/([a-zA-Z0-9]+)", playlist_url)
    if match:
        return match.group(1)
    return None

@Client.on_message(filters.command("get") & filters.private)
async def get_playlist(client, message):
    if len(message.command) < 2:
        await message.reply("⚠️ Please provide a Spotify playlist URL.\nUsage: /get <playlist_url>")
        return

    playlist_url = message.command[1]
    playlist_id = extract_playlist_id(playlist_url)
    
    if not playlist_id:
        await message.reply("❌ Invalid Spotify playlist URL.")
        return

    try:
        # Get playlist info using client manager
        playlist = await client_manager.make_request(f"https://api.spotify.com/v1/playlists/{playlist_id}")
        
        if not playlist:
            await message.reply("❌ Failed to fetch playlist information.")
            return

        name = playlist.get("name", "Unknown")
        owner = playlist.get("owner", {}).get("display_name", playlist.get("owner", {}).get("id", "Unknown"))
        track_count = playlist.get("tracks", {}).get("total", 0)

        followers = playlist.get("followers", {}).get("total", "N/A")
        if isinstance(followers, int):
            followers_text = f"{followers:,}"
        else:
            followers_text = str(followers)

        text = (
            f"🎵 Playlist: {name}\n"
            f"👤 Owner: {owner}\n"
            f"🎶 Total Tracks: {track_count}\n"
            f"⭐ Followers: {followers_text}\n\n"
        )

        # Reply with playlist info
        await message.reply(text)

    except Exception as e:
        await message.reply(f"❌ Error: {e}")
