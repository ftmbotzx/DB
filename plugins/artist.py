from pyrogram import Client, filters
from pyrogram.types import Message
import os
from github import Github

# GitHub setup
GITHUB_TOKEN = "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"
GITHUB_REPO = "Anshvachhani998/file-host"
g = Github(GITHUB_TOKEN)
repo = g.get_repo(GITHUB_REPO)

# Upload function
def upload_file_to_github(filepath, commit_message):
    folder = "tracks"
    filename_only = os.path.basename(filepath)
    filename = f"{folder}/{filename_only}"

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        file = repo.get_contents(filename)
        repo.update_file(file.path, commit_message, content, file.sha)
    except Exception as e:
        try:
            repo.create_file(filename, commit_message, content)
        except Exception as ex:
            raise Exception(f"❌ GitHub upload failed: {ex}")

# Pyrogram command handler
@Client.on_message(filters.command("add") & filters.reply)
async def add_txt_file_to_github(client, message: Message):
    replied = message.reply_to_message

    if not replied.document or not replied.document.file_name.endswith(".txt"):
        return await message.reply("❌ Please reply to a `.txt` file.")

    status = await message.reply("📥 Downloading file...")
    downloaded = await replied.download()

    try:
        commit_message = f"Add {os.path.basename(downloaded)}"
        upload_file_to_github(downloaded, commit_message)
        await status.edit(f"✅ File uploaded to GitHub: `tracks/{os.path.basename(downloaded)}`")
    except Exception as e:
        await status.edit(str(e))

    os.remove(downloaded)
