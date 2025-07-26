from pyrogram import Client, filters
from pyrogram.types import Message

from plugins.spotify_client import sp  # Spotify client global config
import asyncio

@Client.on_message(filters.command("allplaylists"))
async def get_all_global_playlists(client: Client, message: Message):
    try:
        await message.reply("🌍 Fetching top Spotify playlists globally... Please wait.", quote=True)

        queries = [
            "top hits", "global hits", "trending now", "world music", "pop hits", "party songs",
            "lofi chill", "edm", "rock legends", "workout playlist", "focus music", "romantic songs",
            "hip hop", "classical music", "latin hits", "k-pop", "afro beats", "arabic music",
            "japanese songs", "instrumental", "relaxing songs"
        ]

        playlists_dict = {}

        for query in queries:
            for offset in range(0, 300, 50):  # Max 300 playlists per query
                try:
                    results = sp.search(q=query, type="playlist", limit=50, offset=offset)
                    await asyncio.sleep(0.3)  # avoid rate limit
                except Exception as err:
                    print(f"Spotify error on query '{query}': {err}")
                    continue

                # Safeguard check
                if not results or "playlists" not in results or not results["playlists"]:
                    continue

                items = results["playlists"].get("items", [])
                for item in items:
                    name = item.get("name")
                    playlist_id = item.get("id")
                    if name and playlist_id:
                        url = f"https://open.spotify.com/playlist/{playlist_id}"
                        playlists_dict[name] = url

        # Sort and format
        sorted_playlists = sorted(playlists_dict.items())
        total = len(sorted_playlists)

        if total == 0:
            return await message.reply("❌ No playlists found.")

        file_name = "global_playlists.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            for idx, (name, url) in enumerate(sorted_playlists, 1):
                f.write(f"{idx}. {name} - {url}\n")

        await message.reply_document(
            file_name,
            caption=f"✅ Found `{total}` unique Spotify playlists from around the world."
        )

    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")
