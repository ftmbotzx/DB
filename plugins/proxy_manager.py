
import random
import asyncio
import aiohttp
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
        ]
        self.current_ua_index = 0
        self.session_delays = [1, 2, 3, 4, 5]  # Random delays between requests
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(self.user_agents)
    
    def rotate_user_agent(self) -> str:
        """Rotate to next user agent"""
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        return self.user_agents[self.current_ua_index]
    
    async def get_session_with_rotation(self, local_addr: tuple = None) -> aiohttp.ClientSession:
        """Create a session with rotated headers and optional local address binding"""
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        connector = None
        if local_addr:
            try:
                connector = aiohttp.TCPConnector(local_addr=local_addr)
            except Exception as e:
                logger.warning(f"Could not bind to {local_addr}, using default: {e}")
        
        return aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def add_random_delay(self, min_delay: float = 0.5, max_delay: float = 2.0):
        """Add random delay to avoid detection"""
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    def get_status(self) -> Dict:
        """Get proxy manager status"""
        return {
            "current_user_agent": self.user_agents[self.current_ua_index],
            "total_user_agents": len(self.user_agents),
            "current_ua_index": self.current_ua_index
        }
