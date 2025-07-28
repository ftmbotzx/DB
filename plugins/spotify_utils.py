
import json
import asyncio
import logging
from .spotify_client_manager import SpotifyClientManager

logger = logging.getLogger(__name__)

# Load all clients from clients.json
with open("clients.json", "r") as f:
    clients_data = json.load(f)
    clients = clients_data["clients"]

# Initialize the client manager with all available clients
client_manager = SpotifyClientManager(clients)

async def get_artist_albums(artist_id, limit=50, offset=0):
    """Get artist albums using client manager"""
    endpoint = f"artists/{artist_id}/albums"
    params = {"limit": limit, "offset": offset, "include_groups": "album,single"}
    return await client_manager.make_request(f"https://api.spotify.com/v1/{endpoint}", params)

async def get_album_tracks(album_id, limit=50, offset=0):
    """Get album tracks using client manager"""
    endpoint = f"albums/{album_id}/tracks"
    params = {"limit": limit, "offset": offset}
    return await client_manager.make_request(f"https://api.spotify.com/v1/{endpoint}", params)

async def get_playlist_tracks(playlist_id, limit=50, offset=0):
    """Get playlist tracks using client manager"""
    endpoint = f"playlists/{playlist_id}/tracks"
    params = {"limit": limit, "offset": offset}
    return await client_manager.make_request(f"https://api.spotify.com/v1/{endpoint}", params)

async def get_user_playlists(user_id, limit=50, offset=0):
    """Get user playlists using client manager"""
    endpoint = f"users/{user_id}/playlists"
    params = {"limit": limit, "offset": offset}
    return await client_manager.make_request(f"https://api.spotify.com/v1/{endpoint}", params)

async def get_artist_info(artist_id):
    """Get artist information using client manager"""
    endpoint = f"artists/{artist_id}"
    return await client_manager.make_request(f"https://api.spotify.com/v1/{endpoint}")
