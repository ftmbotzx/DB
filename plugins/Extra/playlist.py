from pyrogram import Client, filters
from pyrogram.types import Message
import asyncio
import spotipy
import logging
from spotipy.oauth2 import SpotifyClientCredentials

# 🔧 Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🟢 Spotify credentials
client_secret = "97d40c2c7b7948589df58d838b8e9e68"
client_id = "c6e8b0da7751415e848a97f309bc057d"
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

@Client.on_message(filters.command("allplaylists"))
async def get_all_global_playlists(client: Client, message: Message):
    try:
        await message.reply("🌍 Searching top Spotify playlists... Please wait.", quote=True)

        queries = [
            "top hits", "global hits", "trending now", "world music", "pop hits", "party songs",
            "lofi chill", "edm", "rock legends", "workout playlist", "focus music", "romantic songs",
            "hip hop", "classical music", "latin hits", "k-pop", "afro beats", "arabic music",
            "japanese songs", "instrumental", "relaxing songs"
        ]

        playlists_dict = {}

        for query in queries:
            for offset in range(0, 300, 50):
                try:
                    results = sp.search(q=query, type="playlist", limit=50, offset=offset)
                    await asyncio.sleep(0.3)
                    logger.info(f"🔍 Queried '{query}' at offset {offset}")
                except Exception as err:
                    logger.warning(f"⚠️ Error while searching: {query} @ offset {offset}: {err}")
                    continue

                playlists_data = results.get("playlists") if results else None
                if not playlists_data:
                    logger.warning(f"⚠️ No 'playlists' key found in results for query: {query}")
                    continue

                items = playlists_data.get("items", [])
                if not items:
                    logger.info(f"ℹ️ No playlists found in this batch for query: {query}")
                    continue

                for item in items:
                    if not item:
                        continue
                    name = item.get("name")
                    playlist_id = item.get("id")
                    if name and playlist_id:
                        url = f"https://open.spotify.com/playlist/{playlist_id}"
                        playlists_dict[name] = url

        total = len(playlists_dict)
        if total == 0:
            logger.info("❌ No playlists were collected.")
            return await message.reply("❌ No playlists found. Try again later.")

        file_name = "global_playlists.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            for idx, (name, url) in enumerate(sorted(playlists_dict.items()), 1):
                f.write(f"{idx}. {name} - {url}\n")

        logger.info(f"✅ Total {total} unique playlists saved.")
        await message.reply_document(
            file_name,
            caption=f"✅ Found `{total}` unique Spotify playlists from across the world."
        )

    except Exception as e:
        logger.exception("❌ Final error occurred.")
        await message.reply(f"❌ Final Error: `{e}`")
