
import json
import asyncio
import logging
from .spotify_client_manager import SpotifyClientManager
from .ip_manager import IPManager
from .proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

# Load all clients from clients.json
with open("clients.json", "r") as f:
    clients_data = json.load(f)
    clients = clients_data["clients"]

# Initialize managers
client_manager = SpotifyClientManager(clients)
ip_manager = IPManager()
proxy_manager = ProxyManager()

class SpotifyAPIHelper:
    def __init__(self):
        self.client_manager = client_manager
        self.ip_manager = ip_manager
    
    async def get_track_info(self, track_id: str):
        """Get track information"""
        return await self.client_manager.make_request(f"https://api.spotify.com/v1/tracks/{track_id}")
    
    async def get_album_info(self, album_id: str):
        """Get album information"""
        return await self.client_manager.make_request(f"https://api.spotify.com/v1/albums/{album_id}")
    
    async def get_artist_info(self, artist_id: str):
        """Get artist information"""
        return await self.client_manager.make_request(f"https://api.spotify.com/v1/artists/{artist_id}")
    
    async def get_playlist_info(self, playlist_id: str):
        """Get playlist information"""
        return await self.client_manager.make_request(f"https://api.spotify.com/v1/playlists/{playlist_id}")
    
    async def search_tracks(self, query: str, limit: int = 50, offset: int = 0):
        """Search for tracks"""
        params = {
            "q": query,
            "type": "track",
            "limit": limit,
            "offset": offset
        }
        return await self.client_manager.make_request("https://api.spotify.com/v1/search", params)
    
    async def search_albums(self, query: str, limit: int = 50, offset: int = 0):
        """Search for albums"""
        params = {
            "q": query,
            "type": "album",
            "limit": limit,
            "offset": offset
        }
        return await self.client_manager.make_request("https://api.spotify.com/v1/search", params)
    
    async def search_artists(self, query: str, limit: int = 50, offset: int = 0):
        """Search for artists"""
        params = {
            "q": query,
            "type": "artist",
            "limit": limit,
            "offset": offset
        }
        return await self.client_manager.make_request("https://api.spotify.com/v1/search", params)
    
    async def search_playlists(self, query: str, limit: int = 50, offset: int = 0):
        """Search for playlists"""
        params = {
            "q": query,
            "type": "playlist",
            "limit": limit,
            "offset": offset
        }
        return await self.client_manager.make_request("https://api.spotify.com/v1/search", params)
    
    async def get_user_playlists(self, user_id: str, limit: int = 50, offset: int = 0):
        """Get user playlists"""
        params = {"limit": limit, "offset": offset}
        return await self.client_manager.make_request(f"https://api.spotify.com/v1/users/{user_id}/playlists", params)
    
    async def get_playlist_tracks(self, playlist_id: str, limit: int = 50, offset: int = 0):
        """Get playlist tracks"""
        params = {"limit": limit, "offset": offset}
        return await self.client_manager.make_request(f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks", params)
    
    async def get_artist_albums(self, artist_id: str, limit: int = 50, offset: int = 0):
        """Get artist albums"""
        params = {
            "include_groups": "album,single,appears_on,compilation",
            "limit": limit,
            "offset": offset
        }
        return await self.client_manager.make_request(f"https://api.spotify.com/v1/artists/{artist_id}/albums", params)
    
    async def get_album_tracks(self, album_id: str, limit: int = 50, offset: int = 0):
        """Get album tracks"""
        params = {"limit": limit, "offset": offset}
        return await self.client_manager.make_request(f"https://api.spotify.com/v1/albums/{album_id}/tracks", params)
    
    async def get_multiple_tracks(self, track_ids: list):
        """Get multiple tracks at once (up to 50)"""
        if len(track_ids) > 50:
            track_ids = track_ids[:50]
        
        params = {"ids": ",".join(track_ids)}
        return await self.client_manager.make_request("https://api.spotify.com/v1/tracks", params)
    
    async def get_multiple_albums(self, album_ids: list):
        """Get multiple albums at once (up to 20)"""
        if len(album_ids) > 20:
            album_ids = album_ids[:20]
        
        params = {"ids": ",".join(album_ids)}
        return await self.client_manager.make_request("https://api.spotify.com/v1/albums", params)
    
    def get_current_status(self):
        """Get current client and IP status"""
        return self.client_manager.get_current_client_info()
    
    async def force_switch(self):
        """Force switch to next client and IP"""
        await self.client_manager._switch_client()
        await self.client_manager._switch_ip()
        return self.get_current_status()

# Create global helper instance
spotify_helper = SpotifyAPIHelper()
