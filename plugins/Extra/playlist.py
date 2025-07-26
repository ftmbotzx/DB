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

# 🌟 Default search terms if user doesn't provide custom queries
DEFAULT_QUERIES = [
    "bollywood hits", "top hindi songs", "indian classical", "desi hip hop", "punjabi hits",
    "gujarati garba", "indian devotional", "arijit singh", "shreya ghoshal", "indian pop",
    "tamil hits", "telugu hits", "marathi hits", "rajasthani folk", "bengali songs",
    "indian rock", "indian indie", "bhajan", "sufi music india", "indian rap",
    "indian electronic", "fusion music india", "hindi sad songs", "hindi romantic",
    "hindi dance", "regional indian music", "hindi remix", "indian party songs"
]

@Client.on_message(filters.command("playlist"))
async def get_custom_playlists(client: Client, message: Message):
    try:
        args = message.text.split(None, 1)  # Split command and rest of text
        if len(args) > 1:
            # 📌 Parse queries from user input (split by comma or space)
            user_input = args[1].lower()
            queries = [q.strip() for q in user_input.replace(",", " ").split() if q.strip()]
        else:
            # Use default queries if none provided
            queries = DEFAULT_QUERIES

        if not queries:
            return await message.reply("❌ Please provide valid search terms.")

        await message.reply(f"🔍 Searching playlists for: `{', '.join(queries)}`", quote=True)
        logger.info(f"Searching for queries: {queries}")

        playlists_dict = {}

        for query in queries:
            for offset in range(0, 500, 50):
                try:
                    results = sp.search(q=query, type="playlist", limit=50, offset=offset)
                    await asyncio.sleep(0.5)
                    logger.info(f"Queried '{query}' at offset {offset}")
                except Exception as err:
                    logger.warning(f"Error while searching: {query} @ offset {offset}: {err}")
                    continue

                playlists_data = results.get("playlists") if results else None
                if not playlists_data:
                    continue

                items = playlists_data.get("items", [])
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
            return await message.reply("❌ No playlists found. Try again later.")

        file_name = "custom_playlists.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            for idx, (name, url) in enumerate(sorted(playlists_dict.items()), 1):
                f.write(f"{idx}. {name} - {url}\n")

        await message.reply_document(
            file_name,
            caption=f"✅ Found `{total}` unique playlists for your search."
        )

    except Exception as e:
        logger.exception("❌ Final error occurred.")
        await message.reply(f"❌ Final Error: `{e}`")






from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import re
import os
import asyncio

# Regex to extract Spotify playlist URLs
SPOTIFY_PLAYLIST_REGEX = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

async def extract_track_ids(playlist_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(playlist_url, headers=HEADERS) as resp:
                text = await resp.text()

                # Track URI format: "spotify:track:xxxxxxxxxxxxx"
                track_ids = list(set(re.findall(r"spotify:track:([a-zA-Z0-9]+)", text)))
                return track_ids
    except Exception as e:
        print(f"Error scraping {playlist_url}: {e}")
        return []

@Client.on_message(filters.command("extracttracks") & filters.reply)
async def extract_from_txt(client, message: Message):
    if not message.reply_to_message.document:
        return await message.reply("⚠️ Reply to a `.txt` file containing Spotify playlist links.")

    file_path = await message.reply_to_message.download()
    final_track_ids = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        playlist_urls = re.findall(SPOTIFY_PLAYLIST_REGEX, content)
        full_links = [f"https://open.spotify.com/playlist/{pid}" for pid in playlist_urls]

        status = await message.reply(f"🌀 Found {len(full_links)} playlists. Scraping...")

        for idx, url in enumerate(full_links, start=1):
            await status.edit(f"🔍 Scraping {idx}/{len(full_links)}...\n{url}")
            ids = await extract_track_ids(url)
            final_track_ids.extend(ids)
            await asyncio.sleep(1.5)

        # Remove duplicates
        unique_ids = list(set(final_track_ids))

        # Save to .txt
        result_file = "all_tracks.txt"
        with open(result_file, "w") as f:
            f.write("\n".join(unique_ids))

        await message.reply_document(result_file, caption=f"✅ Extracted {len(unique_ids)} tracks.")
        os.remove(result_file)

    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    finally:
        os.remove(file_path)

