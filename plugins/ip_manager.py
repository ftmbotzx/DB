
import subprocess
import logging
import asyncio
import random
import socket
import requests
import netifaces
from typing import List, Optional

logger = logging.getLogger(__name__)

class IPManager:
    def __init__(self):
        self.available_interfaces = []
        self.available_ips = []
        self.current_interface_index = 0
        self.current_ip_index = 0
        self.discover_interfaces()
    
    def discover_interfaces(self):
        """Discover available network interfaces using netifaces"""
        try:
            # Get all network interfaces
            interfaces = netifaces.interfaces()
            valid_interfaces = []
            all_ips = []
            
            for interface in interfaces:
                # Skip loopback and virtual interfaces
                if interface in ['lo', 'docker0'] or interface.startswith('veth'):
                    continue
                    
                try:
                    # Get IPv4 addresses for this interface
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        for addr_info in addrs[netifaces.AF_INET]:
                            ip = addr_info.get('addr')
                            if ip and not ip.startswith('127.'):
                                valid_interfaces.append(interface)
                                all_ips.append(ip)
                                break
                except Exception as e:
                    logger.debug(f"Error getting addresses for {interface}: {e}")
                    continue
            
            self.available_interfaces = list(set(valid_interfaces))
            self.available_ips = list(set(all_ips))
            
            # If no interfaces found, try alternative method
            if not self.available_ips:
                self.discover_ips_alternative()
            
            logger.info(f"Discovered {len(self.available_interfaces)} interfaces: {self.available_interfaces}")
            logger.info(f"Discovered {len(self.available_ips)} IPs: {self.available_ips}")
            
        except ImportError:
            logger.warning("netifaces not available, using alternative method")
            self.discover_ips_alternative()
        except Exception as e:
            logger.error(f"Error discovering interfaces: {e}")
            self.discover_ips_alternative()
    
    def discover_ips_alternative(self):
        """Alternative method to discover IPs without netifaces"""
        try:
            # Method 1: Use socket to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                if local_ip and not local_ip.startswith('127.'):
                    self.available_ips.append(local_ip)
            
            # Method 2: Get hostname IP
            hostname_ip = socket.gethostbyname(socket.gethostname())
            if hostname_ip and not hostname_ip.startswith('127.') and hostname_ip not in self.available_ips:
                self.available_ips.append(hostname_ip)
            
            # Fallback to default
            if not self.available_ips:
                self.available_ips = ['0.0.0.0']
                logger.warning("No local IPs found, using default 0.0.0.0")
            
            self.available_interfaces = ['default'] * len(self.available_ips)
            
        except Exception as e:
            logger.error(f"Error in alternative IP discovery: {e}")
            self.available_ips = ['0.0.0.0']
            self.available_interfaces = ['default']
    
    def get_interface_ips(self, interface: str) -> List[str]:
        """Get all IPs for a specific interface"""
        try:
            if interface == 'default':
                return self.available_ips
                
            addrs = netifaces.ifaddresses(interface)
            ips = []
            
            if netifaces.AF_INET in addrs:
                for addr_info in addrs[netifaces.AF_INET]:
                    ip = addr_info.get('addr')
                    if ip and not ip.startswith('127.'):
                        ips.append(ip)
            
            return ips
        except Exception as e:
            logger.error(f"Error getting IPs for {interface}: {e}")
            return []
    
    def get_all_available_ips(self) -> List[str]:
        """Get all available IPs from all interfaces"""
        return self.available_ips.copy()
    
    async def switch_source_ip(self, target_ip: str) -> bool:
        """Switch to use a specific source IP"""
        try:
            if target_ip in self.available_ips:
                self.current_ip_index = self.available_ips.index(target_ip)
                logger.info(f"Switched to use source IP: {target_ip}")
                await asyncio.sleep(1)  # Simulate switch time
                return True
            else:
                logger.warning(f"IP {target_ip} not available")
                return False
        except Exception as e:
            logger.error(f"Error switching to IP {target_ip}: {e}")
            return False
    
    async def rotate_ip(self) -> Optional[str]:
        """Rotate to next available IP"""
        if not self.available_ips:
            logger.warning("No IPs available for rotation")
            return None
        
        if len(self.available_ips) <= 1:
            logger.warning("Only one IP available, cannot rotate")
            return self.available_ips[0] if self.available_ips else None
        
        # Move to next IP
        self.current_ip_index = (self.current_ip_index + 1) % len(self.available_ips)
        selected_ip = self.available_ips[self.current_ip_index]
        
        success = await self.switch_source_ip(selected_ip)
        
        if success:
            return selected_ip
        return None
    
    def get_current_ip(self) -> str:
        """Get current IP being used"""
        if self.available_ips and self.current_ip_index < len(self.available_ips):
            return self.available_ips[self.current_ip_index]
        return "0.0.0.0"
    
    def get_current_public_ip(self) -> Optional[str]:
        """Get current public IP address"""
        try:
            # Try multiple services in case one is down
            services = [
                'https://api.ipify.org',
                'https://ifconfig.me/ip',
                'https://icanhazip.com'
            ]
            
            for service in services:
                try:
                    response = requests.get(service, timeout=10)
                    if response.status_code == 200:
                        return response.text.strip()
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error getting public IP: {e}")
        return None
    
    async def test_ip_connectivity(self, ip: str) -> bool:
        """Test if an IP has internet connectivity"""
        try:
            # Create a socket and try to connect
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                # Try to connect to Google DNS
                result = s.connect_ex(('8.8.8.8', 53))
                return result == 0
        except Exception as e:
            logger.error(f"Error testing connectivity for {ip}: {e}")
            return False
    
    def get_status(self) -> dict:
        """Get current IP manager status"""
        return {
            "current_ip": self.get_current_ip(),
            "current_ip_index": self.current_ip_index,
            "available_ips": self.available_ips,
            "total_ips": len(self.available_ips),
            "available_interfaces": self.available_interfaces,
            "total_interfaces": len(self.available_interfaces)
        }
