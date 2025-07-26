from pyrogram import Client, filters
from pyrogram.types import Message
from spotify_client import sp
import asyncio

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
                except Exception as err:
                    print(f"⚠️ Error while searching: {query} @ offset {offset}: {err}")
                    continue

                # Safely extract playlists
                if not results or not results.get("playlists"):
                    continue

                playlists = results.get("playlists", {})
                items = playlists.get("items", [])

                if not items:
                    continue

                for item in items:
                    name = item.get("name")
                    playlist_id = item.get("id")
                    if name and playlist_id:
                        url = f"https://open.spotify.com/playlist/{playlist_id}"
                        playlists_dict[name] = url

        total = len(playlists_dict)
        if total == 0:
            return await message.reply("❌ No playlists found. Try again later.")

        file_name = "global_playlists.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            for idx, (name, url) in enumerate(sorted(playlists_dict.items()), 1):
                f.write(f"{idx}. {name} - {url}\n")

        await message.reply_document(
            file_name,
            caption=f"✅ Found `{total}` unique Spotify playlists from across the world."
        )

    except Exception as e:
        await message.reply(f"❌ Final Error: `{e}`")
