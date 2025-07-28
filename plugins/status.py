
from pyrogram import Client, filters
from pyrogram.types import Message
import json
from .spotify_client_manager import SpotifyClientManager
from .ip_manager import IPManager
from .spotify_utils import spotify_helper

# Load clients
with open("clients.json", "r") as f:
    clients_data = json.load(f)
    clients = clients_data["clients"]

@Client.on_message(filters.command("status") & filters.private)
async def get_status(client: Client, message: Message):
    """Get current client and IP status"""
    try:
        status_info = spotify_helper.get_current_status()
        
        status_text = f"""
🔍 **Spotify Client Manager Status**

**Current Client:**
• Index: {status_info['client_index'] + 1}/{status_info['total_clients']}
• ID: {status_info['client_id']}

**Current IP:**
• IP: {status_info['current_ip']}
• Index: {status_info['ip_index'] + 1}/{status_info['total_ips']}

**Requests:**
• Count this minute: {status_info['request_count']}

**Available Clients:** {status_info['total_clients']}
**Available IPs:** {status_info['total_ips']}
        """
        
        await message.reply(status_text)
        
    except Exception as e:
        await message.reply(f"❌ Error getting status: {e}")

@Client.on_message(filters.command("switch") & filters.private)
async def force_switch(client: Client, message: Message):
    """Force switch to next client and IP"""
    try:
        status_msg = await message.reply("🔄 Switching client and IP...")
        
        new_status = await spotify_helper.force_switch()
        
        await status_msg.edit(f"""
✅ **Switched Successfully!**

**New Client:**
• Index: {new_status['client_index'] + 1}/{new_status['total_clients']}
• ID: {new_status['client_id']}

**New IP:**
• IP: {new_status['current_ip']}
• Index: {new_status['ip_index'] + 1}/{new_status['total_ips']}
        """)
        
    except Exception as e:
        await message.reply(f"❌ Error switching: {e}")

@Client.on_message(filters.command("clientinfo") & filters.private)
async def get_client_info(client: Client, message: Message):
    """Get detailed information about all clients"""
    try:
        total_clients = len(clients)
        
        info_text = f"📊 **Client Information**\n\n"
        info_text += f"**Total Clients:** {total_clients}\n\n"
        
        for i, client_data in enumerate(clients[:10], 1):  # Show first 10
            client_id = client_data['client_id']
            info_text += f"**Client {i}:**\n"
            info_text += f"• ID: {client_id[:8]}...\n"
            info_text += f"• Secret: {client_data['client_secret'][:8]}...\n\n"
        
        if total_clients > 10:
            info_text += f"... and {total_clients - 10} more clients\n"
        
        await message.reply(info_text)
        
    except Exception as e:
        await message.reply(f"❌ Error getting client info: {e}")

@Client.on_message(filters.command("ipinfo") & filters.private)
async def get_ip_info(client: Client, message: Message):
    """Get IP and network information"""
    try:
        ip_manager = IPManager()
        all_ips = ip_manager.get_all_available_ips()
        current_public_ip = ip_manager.get_current_public_ip()
        
        info_text = f"""
🌐 **Network Information**

**Public IP:** {current_public_ip or "Unable to detect"}
**Available Local IPs:** {len(all_ips)}

**Local IPs:**
        """
        
        for i, ip in enumerate(all_ips[:10], 1):  # Show first 10
            info_text += f"• {ip}\n"
        
        if len(all_ips) > 10:
            info_text += f"... and {len(all_ips) - 10} more IPs\n"
        
        await message.reply(info_text)
        
    except Exception as e:
        await message.reply(f"❌ Error getting IP info: {e}")
