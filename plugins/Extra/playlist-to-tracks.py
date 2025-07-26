import logging
from pyrogram import Client, filters
from pyrogram.types import Message
import re
import os
import asyncio
from playwright.async_api import async_playwright

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

SPOTIFY_PLAYLIST_REGEX = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"

async def extract_track_ids_playwright(playlist_url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True
                # headless=False  # Debug mode: browser window dikhega
            )
            page = await browser.new_page()
            await page.goto(playlist_url, wait_until="networkidle")

            previous_height = None
            for i in range(30):  # Scroll 30 times max
                current_height = await page.evaluate("document.body.scrollHeight")
                if previous_height == current_height:
                    logger.info(f"Scroll stopped at iteration {i}")
                    break
                previous_height = current_height
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)  # Wait 3 seconds for content load

            content = await page.content()
            await browser.close()

            # Updated regex to find track IDs inside JSON in page source
            track_ids = list(set(re.findall(r'"uri":"spotify:track:([a-zA-Z0-9]+)"', content)))
            logger.info(f"Playwright scraped {len(track_ids)} tracks from: {playlist_url}")
            return track_ids

    except Exception as e:
        logger.error(f"Playwright error scraping {playlist_url}: {e}")
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

        playlist_ids = re.findall(SPOTIFY_PLAYLIST_REGEX, content)
        full_links = [f"https://open.spotify.com/playlist/{pid}" for pid in playlist_ids]

        total = len(full_links)
        logger.info(f"Found {total} playlists to process.")
        status = await message.reply(f"🌀 Found {total} playlists. Starting scraping...")

        for idx, url in enumerate(full_links, start=1):
            ids = await extract_track_ids_playwright(url)
            final_track_ids.extend(ids)

            if idx % 5 == 0 or idx == total:
                await status.edit(f"🔍 Scraped {idx}/{total} playlists...\nLatest: {url}")
                logger.info(f"Updated progress message at {idx}/{total}")

            await asyncio.sleep(1)  # small delay

        unique_ids = list(set(final_track_ids))
        result_file = "all_tracks.txt"
        with open(result_file, "w") as f:
            f.write("\n".join(unique_ids))

        logger.info(f"✅ Total Unique Tracks Extracted: {len(unique_ids)}")
        await message.reply_document(result_file, caption=f"✅ Extracted {len(unique_ids)} unique tracks.")
        os.remove(result_file)

    except Exception as e:
        logger.exception("An error occurred during processing.")
        await message.reply(f"❌ Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
