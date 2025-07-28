import json
import asyncio
import aiohttp
import base64
import logging
import subprocess
import random
import time
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class SpotifyClientManager:
    def __init__(self, clients: List[Dict]):
        self.clients = clients
        self.current_client_index = 0
        self.current_ip_index = 0
        self.available_ips = []
        self.tokens = {}
        self.token_expires = {}
        self.rate_limit_reset = {}
        self.lock = asyncio.Lock()
        self.request_count = 0
        self.last_reset_time = time.time()
        self.max_requests_per_minute = 80

        # Initialize available IPs
        asyncio.create_task(self._discover_available_ips())

    async def _discover_available_ips(self):
        """Discover available network interfaces and IPs"""
        try:
            import socket
            import netifaces

            interfaces = []

            # Method 1: Use netifaces if available
            try:
                for interface in netifaces.interfaces():
                    if interface in ['lo', 'docker0'] or interface.startswith('veth'):
                        continue

                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        for addr_info in addrs[netifaces.AF_INET]:
                            ip = addr_info.get('addr')
                            if ip and not ip.startswith('127.'):
                                interfaces.append(ip)
            except ImportError:
                logger.warning("netifaces not available, using socket method")

                # Method 2: Use socket
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                    if local_ip and not local_ip.startswith('127.'):
                        interfaces.append(local_ip)

                # Try hostname method too
                hostname_ip = socket.gethostbyname(socket.gethostname())
                if hostname_ip and not hostname_ip.startswith('127.') and hostname_ip not in interfaces:
                    interfaces.append(hostname_ip)

            if interfaces:
                self.available_ips = list(set(interfaces))  # Remove duplicates
                logger.info(f"Discovered {len(self.available_ips)} available IPs: {self.available_ips}")
            else:
                self.available_ips = ['0.0.0.0']  # Fallback
                logger.warning("No additional IPs found, using default")

        except Exception as e:
            logger.error(f"Error discovering IPs: {e}")
            self.available_ips = ['0.0.0.0']

    async def _switch_ip(self):
        """Switch to next available IP address"""
        if len(self.available_ips) <= 1:
            logger.warning("Only one IP available, cannot switch")
            return False

        self.current_ip_index = (self.current_ip_index + 1) % len(self.available_ips)
        current_ip = self.available_ips[self.current_ip_index]
        logger.info(f"Switched to IP: {current_ip}")

        # Add delay after IP switch
        await asyncio.sleep(2)
        return True

    async def _switch_client(self):
        """Switch to next available client"""
        self.current_client_index = (self.current_client_index + 1) % len(self.clients)
        current_client = self.clients[self.current_client_index]
        logger.info(f"Switched to client: {current_client['client_id'][:8]}...")

        # Clear token for new client
        client_key = f"{current_client['client_id']}:{current_client['client_secret']}"
        if client_key in self.tokens:
            del self.tokens[client_key]

        return current_client

    async def _get_access_token(self, client_id: str, client_secret: str) -> Optional[str]:
        """Get access token for client credentials"""
        client_key = f"{client_id}:{client_secret}"

        # Check if we have a valid token
        if (client_key in self.tokens and 
            client_key in self.token_expires and 
            time.time() < self.token_expires[client_key]):
            return self.tokens[client_key]

        # Get new token
        auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}

        try:
            # Try using proxy first, then fallback to local IP
            proxy = self.proxy_manager.get_random_proxy() if hasattr(self, 'proxy_manager') else None

            connector = None
            if not proxy and self.available_ips and self.current_ip_index < len(self.available_ips):
                current_ip = self.available_ips[self.current_ip_index]
                if current_ip != '0.0.0.0':
                    connector = aiohttp.TCPConnector(local_addr=(current_ip, 0))

            session_kwargs = {'connector': connector}

            async with aiohttp.ClientSession(**session_kwargs) as session:
                async with session.post(
                    "https://accounts.spotify.com/api/token", 
                    headers=headers, 
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        token = result.get("access_token")
                        expires_in = result.get("expires_in", 3600)

                        self.tokens[client_key] = token
                        self.token_expires[client_key] = time.time() + expires_in - 60  # 1 min buffer

                        return token
                    elif resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited getting token, sleeping {retry_after}s")
                        await asyncio.sleep(retry_after)
                        return None
                    else:
                        logger.error(f"Token request failed: {resp.status}")
                        return None

        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None

    async def _handle_rate_limit(self, retry_after: int = None):
        """Handle rate limit by switching IP and client"""
        if retry_after is None:
            retry_after = random.randint(5, 15)

        logger.warning(f"Rate limit hit! Switching IP and client, waiting {retry_after}s")

        # Switch IP first
        await self._switch_ip()

        # Switch client
        await self._switch_client()

        # Wait the specified time
        await asyncio.sleep(retry_after)

        # Reset request counter
        self.request_count = 0
        self.last_reset_time = time.time()

    async def _check_request_limit(self):
        """Check if we're approaching request limits"""
        current_time = time.time()

        # Reset counter every minute
        if current_time - self.last_reset_time >= 60:
            self.request_count = 0
            self.last_reset_time = current_time

        # If approaching limit, preemptively switch
        if self.request_count >= self.max_requests_per_minute:
            logger.info("Approaching request limit, switching proactively")
            await self._switch_ip()
            await self._switch_client()
            self.request_count = 0
            self.last_reset_time = current_time
            await asyncio.sleep(2)

    async def make_request(self, url: str, params: Dict = None, max_retries: int = 5) -> Optional[Dict]:
        """Make authenticated request to Spotify API with automatic switching"""
        async with self.lock:
            await self._check_request_limit()

            for attempt in range(max_retries):
                current_client = self.clients[self.current_client_index]

                # Get access token
                token = await self._get_access_token(
                    current_client['client_id'], 
                    current_client['client_secret']
                )

                if not token:
                    logger.warning(f"Failed to get token for attempt {attempt + 1}")
                    await self._switch_client()
                    continue

                headers = {"Authorization": f"Bearer {token}"}

                try:
                    # Try using proxy first, then fallback to local IP
                    proxy = self.proxy_manager.get_random_proxy() if hasattr(self, 'proxy_manager') else None

                    connector = None
                    if not proxy and self.available_ips and self.current_ip_index < len(self.available_ips):
                        current_ip = self.available_ips[self.current_ip_index]
                        if current_ip != '0.0.0.0':
                            connector = aiohttp.TCPConnector(local_addr=(current_ip, 0))

                    session_kwargs = {'connector': connector}

                    async with aiohttp.ClientSession(**session_kwargs) as session:
                        request_kwargs = {
                            "headers": headers,
                            "params": params,
                            "timeout": aiohttp.ClientTimeout(total=30)
                        }
                        if proxy:
                            request_kwargs["proxy"] = proxy

                        async with session.get(url, **request_kwargs) as resp:
                            self.request_count += 1

                            if resp.status == 200:
                                return await resp.json()
                            elif resp.status == 429:
                                retry_after = int(resp.headers.get("Retry-After", 10))
                                await self._handle_rate_limit(retry_after)
                                continue
                            elif resp.status in [401, 403]:
                                logger.warning(f"Auth error {resp.status}, switching client")
                                await self._switch_client()
                                continue
                            else:
                                text = await resp.text()
                                logger.error(f"API error {resp.status}: {text}")
                                if attempt < max_retries - 1:
                                    await asyncio.sleep(2 ** attempt)
                                continue

                except asyncio.TimeoutError:
                    logger.warning(f"Request timeout on attempt {attempt + 1}")
                    await self._switch_ip()
                    continue
                except Exception as e:
                    logger.error(f"Request error: {e}")
                    await self._switch_ip()
                    await asyncio.sleep(2)
                    continue

            logger.error(f"All {max_retries} attempts failed for {url}")
            return None

    def get_current_client_info(self) -> Dict:
        """Get current client information"""
        current_client = self.clients[self.current_client_index]
        current_ip = self.available_ips[self.current_ip_index] if self.available_ips else "unknown"

        return {
            "client_id": current_client['client_id'][:8] + "...",
            "client_index": self.current_client_index,
            "total_clients": len(self.clients),
            "current_ip": current_ip,
            "ip_index": self.current_ip_index,
            "total_ips": len(self.available_ips),
            "request_count": self.request_count
        }