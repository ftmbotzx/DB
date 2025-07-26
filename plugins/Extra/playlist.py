from pyrogram import Client, filters
from pyrogram.types import Message

from plugins.spotify_client import sp

@Client.on_message(filters.command("playlist"))
async def get_all_global_playlists(client: Client, message: Message):
    try:
        await message.reply("🌍 Searching for top Spotify playlists globally... Please wait.", quote=True)

        queries = [
            "top hits", "global hits", "trending now", "world music", "pop hits", "party songs",
            "lofi chill", "edm", "rock legends", "workout playlist", "focus music", "romantic songs",
            "hip hop", "classical music", "latin hits", "k-pop", "afro beats", "arabic music",
            "japanese songs", "instrumental", "relaxing songs"
        ]

        playlists_dict = {}

        for query in queries:
            for offset in range(0, 300, 50):  # Fetch 300 playlists per query
                results = sp.search(q=query, type="playlist", limit=50, offset=offset)
                for item in results["playlists"]["items"]:
                    name = item["name"]
                    url = f"https://open.spotify.com/playlist/{item['id']}"
                    playlists_dict[name] = url

        # Sort and build result
        sorted_playlists = sorted(playlists_dict.items())
        total = len(sorted_playlists)

        # Write to file
        with open("global_playlists.txt", "w", encoding="utf-8") as f:
            for idx, (name, url) in enumerate(sorted_playlists, 1):
                f.write(f"{idx}. {name} - {url}\n")

        await message.reply_document(
            "global_playlists.txt",
            caption=f"✅ Found `{total}` unique Spotify playlists worldwide."
        )

    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")
