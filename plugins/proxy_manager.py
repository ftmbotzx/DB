
import random
import asyncio
import aiohttp
import logging
import requests
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
        self.session_delays = [1, 2, 3, 4, 5]
        
        # Free proxy lists (you can add paid proxy services here)
        self.proxy_sources = [
            'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all',
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt'
        ]
        
        self.proxies = []
        self.current_proxy_index = 0
        self.verified_proxies = []
        
        # Load proxies on initialization
        asyncio.create_task(self.load_proxies())
    
    async def load_proxies(self):
        """Load proxies from various sources"""
        try:
            all_proxies = []
            
            for source in self.proxy_sources:
                try:
                    response = requests.get(source, timeout=10)
                    if response.status_code == 200:
                        proxy_list = response.text.strip().split('\n')
                        for proxy in proxy_list:
                            proxy = proxy.strip()
                            if proxy and ':' in proxy:
                                all_proxies.append(f"http://{proxy}")
                except Exception as e:
                    logger.warning(f"Failed to load proxies from {source}: {e}")
            
            # Remove duplicates and limit to 200 proxies
            self.proxies = list(set(all_proxies))[:200]
            logger.info(f"Loaded {len(self.proxies)} proxies")
            
            # Verify proxies in background
            asyncio.create_task(self.verify_proxies())
            
        except Exception as e:
            logger.error(f"Error loading proxies: {e}")
    
    async def verify_proxies(self):
        """Verify which proxies are working"""
        working_proxies = []
        
        for proxy in self.proxies[:50]:  # Test first 50 proxies
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    async with session.get(
                        'http://httpbin.org/ip', 
                        proxy=proxy,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            working_proxies.append(proxy)
                            if len(working_proxies) >= 20:  # Keep 20 verified proxies
                                break
            except:
                continue
        
        self.verified_proxies = working_proxies
        logger.info(f"Verified {len(self.verified_proxies)} working proxies")
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(self.user_agents)
    
    def rotate_user_agent(self) -> str:
        """Rotate to next user agent"""
        self.current_ua_index = (self.current_ua_index + 1) % len(self.user_agents)
        return self.user_agents[self.current_ua_index]
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy from the list"""
        if not self.verified_proxies:
            if self.proxies:
                return random.choice(self.proxies)
            return None
        
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.verified_proxies)
        return self.verified_proxies[self.current_proxy_index]
    
    def get_random_proxy(self) -> Optional[str]:
        """Get a random proxy"""
        if self.verified_proxies:
            return random.choice(self.verified_proxies)
        elif self.proxies:
            return random.choice(self.proxies)
        return None
    
    async def get_session_with_rotation(self, use_proxy: bool = False) -> aiohttp.ClientSession:
        """Create a session with rotated headers and optional proxy"""
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
        proxy = None
        
        if use_proxy:
            proxy = self.get_random_proxy()
            if proxy:
                logger.debug(f"Using proxy: {proxy}")
        
        return aiohttp.ClientSession(
            headers=headers,
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def make_request_with_proxy(self, url: str, **kwargs):
        """Make a request using a proxy"""
        proxy = self.get_random_proxy()
        
        try:
            async with self.get_session_with_rotation(use_proxy=True) as session:
                async with session.get(url, proxy=proxy, **kwargs) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Proxy request failed: {e}")
            # Fallback to direct request
            async with self.get_session_with_rotation(use_proxy=False) as session:
                async with session.get(url, **kwargs) as response:
                    return await response.json()
    
    async def add_random_delay(self, min_delay: float = 0.5, max_delay: float = 2.0):
        """Add random delay to avoid detection"""
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    def get_status(self) -> Dict:
        """Get proxy manager status"""
        return {
            "current_user_agent": self.user_agents[self.current_ua_index],
            "total_user_agents": len(self.user_agents),
            "current_ua_index": self.current_ua_index,
            "total_proxies": len(self.proxies),
            "verified_proxies": len(self.verified_proxies),
            "current_proxy_index": self.current_proxy_index
        }
