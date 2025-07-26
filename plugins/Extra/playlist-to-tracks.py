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

import json

async def extract_track_ids_playwright(playlist_url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(playlist_url, wait_until="networkidle")

            # Scroll to bottom multiple times to load all tracks
            previous_height = None
            for _ in range(30):
                current_height = await page.evaluate("document.body.scrollHeight")
                if current_height == previous_height:
                    break
                previous_height = current_height
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

            # Query all track link elements from DOM
            # Spotify playlist tracks are often inside <a> tags with href like "/track/{id}"
            anchors = await page.query_selector_all('a[href^="/track/"]')

            track_ids = set()
            for a in anchors:
                href = await a.get_attribute("href")
                if href:
                    # href format: /track/{track_id}
                    parts = href.split('/')
                    if len(parts) >= 3 and parts[1] == "track":
                        track_ids.add(parts[2])

            await browser.close()
            logger.info(f"Playwright scraped {len(track_ids)} tracks from: {playlist_url}")
            return list(track_ids)

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
