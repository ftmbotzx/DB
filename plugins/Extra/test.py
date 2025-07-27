from pyrogram import Client, filters
from spotify_scraper import SpotifyClient

# Initialize SpotifyClient (with default rate limiting)
spotify_client = SpotifyClient()

@Client.on_message(filters.command("get") & filters.private)
async def get_playlist(client, message):
    if len(message.command) < 2:
        await message.reply("⚠️ Please provide a Spotify playlist URL.\nUsage: /get <playlist_url>")
        return

    playlist_url = message.command[1]

    try:
        # Get playlist info using spotify_scraper
        playlist = spotify_client.get_playlist_info(playlist_url)

        name = playlist.get("name", "Unknown")
        owner = playlist.get("owner", {}).get("display_name", playlist.get("owner", {}).get("id", "Unknown"))
        track_count = playlist.get("track_count", 0)

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
            "Tracks:\n"
        )

        for track in playlist["tracks"]:
            track_name = track.get("name", "Unknown")
            artist_name = (
                track.get("artists", [{}])[0].get("name", "Unknown")
                if track.get("artists")
                else "Unknown"
            )
            text += f"  - {track_name} by {artist_name}\n"

        # Reply with playlist info
        await message.reply(text)

    except Exception as e:
        await message.reply(f"❌ Error: {e}")
