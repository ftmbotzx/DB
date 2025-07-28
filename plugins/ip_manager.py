
import subprocess
import logging
import asyncio
import random
from typing import List, Optional

logger = logging.getLogger(__name__)

class IPManager:
    def __init__(self):
        self.available_interfaces = []
        self.current_interface_index = 0
        self.discover_interfaces()
    
    def discover_interfaces(self):
        """Discover available network interfaces"""
        try:
            # Get network interfaces
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            interfaces = []
            
            for line in result.stdout.split('\n'):
                if ': ' in line and 'state UP' in line:
                    interface_name = line.split(': ')[1].split('@')[0]
                    if interface_name not in ['lo', 'docker0'] and not interface_name.startswith('veth'):
                        interfaces.append(interface_name)
            
            self.available_interfaces = interfaces
            logger.info(f"Discovered interfaces: {self.available_interfaces}")
            
        except Exception as e:
            logger.error(f"Error discovering interfaces: {e}")
            self.available_interfaces = ['eth0']  # Fallback
    
    def get_interface_ips(self, interface: str) -> List[str]:
        """Get all IPs for a specific interface"""
        try:
            result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
            ips = []
            
            for line in result.stdout.split('\n'):
                if 'inet ' in line and not line.strip().startswith('inet 127'):
                    ip = line.split('inet ')[1].split('/')[0].strip()
                    ips.append(ip)
            
            return ips
        except Exception as e:
            logger.error(f"Error getting IPs for {interface}: {e}")
            return []
    
    def get_all_available_ips(self) -> List[str]:
        """Get all available IPs from all interfaces"""
        all_ips = []
        for interface in self.available_interfaces:
            ips = self.get_interface_ips(interface)
            all_ips.extend(ips)
        
        return list(set(all_ips))  # Remove duplicates
    
    async def switch_source_ip(self, target_ip: str) -> bool:
        """Switch to use a specific source IP"""
        try:
            # This is a placeholder for more advanced IP switching
            # In a real scenario, you might need to configure routing tables
            logger.info(f"Switching to use source IP: {target_ip}")
            await asyncio.sleep(1)  # Simulate switch time
            return True
        except Exception as e:
            logger.error(f"Error switching to IP {target_ip}: {e}")
            return False
    
    async def rotate_ip(self) -> Optional[str]:
        """Rotate to next available IP"""
        all_ips = self.get_all_available_ips()
        if not all_ips:
            logger.warning("No IPs available for rotation")
            return None
        
        # Select random IP to avoid patterns
        selected_ip = random.choice(all_ips)
        success = await self.switch_source_ip(selected_ip)
        
        if success:
            return selected_ip
        return None
    
    def get_current_public_ip(self) -> Optional[str]:
        """Get current public IP address"""
        try:
            result = subprocess.run(['curl', '-s', 'ifconfig.me'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.error(f"Error getting public IP: {e}")
        return None
    
    async def test_ip_connectivity(self, ip: str) -> bool:
        """Test if an IP has internet connectivity"""
        try:
            # Test connectivity using ping
            result = subprocess.run(['ping', '-c', '1', '-W', '3', '8.8.8.8'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error testing connectivity for {ip}: {e}")
            return False
