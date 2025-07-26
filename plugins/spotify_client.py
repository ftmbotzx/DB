import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

SPOTIFY_CLIENT_ID = "c6e8b0da7751415e848a97f309bc057d"
SPOTIFY_CLIENT_SECRET = "97d40c2c7b7948589df58d838b8e9e68"

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))
