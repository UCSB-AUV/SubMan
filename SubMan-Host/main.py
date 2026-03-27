import ipaddress
import socket

import psutil
import anyio
from anyio.abc import SocketAttribute, UDPSocket
from objprint import objprint
from dataclasses import dataclass

DISCOVERY_MESSAGE = "DISCOVER_UAV"
PORT_DISCOVERY = 5000
PORT_TELEMETRY = 5002
PORT_VIDEO = 5007

@dataclass(slots=True)
class NetworkInfo:
    name: str
    local_ip: str
    broadcast_ip: str | None
    netmask: str | None
    mac: str | None

class NetworkManager:
    
    _available_interfaces: list[NetworkInfo]
    _selected_interface : NetworkInfo
    _udp_socket : UDPSocket | None


    def __init__(self) -> None:
        self._available_interfaces = []
        self._udp_socket = None

    def _get_broadcast_address(self, ip: str, netmask: str) -> str:
        # Fallback if psutil doesn't provide broadcast (rare).
        try:
            net = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
            return str(net.broadcast_address)
        except Exception:
            return "255.255.255.255"  # safe fallback
        
    def get_available_interfaces(self) -> list[NetworkInfo]:
        if_addrs = psutil.net_if_addrs()
        if_stats = psutil.net_if_stats()

        for if_name, if_info in if_addrs.items():

            # Skip interface if it's not in if_stats or it is down.
            if if_name not in if_stats or not if_stats[if_name].isup:
                continue
            
            ipv4 = None
            mac_addr = None
            for item in if_info:
                if item.family == socket.AF_INET:
                    ipv4 = item
                if item.family == psutil.AF_LINK:
                    mac_addr = item.address

            # Make sure the interface has valid ipv4 address.
            if ipv4 and ipv4.address and ipv4.netmask and not ipv4.address.startswith("169.254"):
                broadcast_ip = (
                    ipv4.broadcast
                    or self._get_broadcast_address(ipv4.address, ipv4.netmask)
                )
                self._available_interfaces.append(NetworkInfo(
                    name=if_name,
                    local_ip=ipv4.address,
                    broadcast_ip=broadcast_ip,
                    netmask=ipv4.netmask,
                    mac=mac_addr
                ))

        return self._available_interfaces

    async def set_interface(self, name: str) -> bool:
        for interface in self._available_interfaces:
            if interface.name == name:
                self._selected_interface = interface
        
        if not self._selected_interface:
            return False
        
        self._udp_socket = await anyio.create_udp_socket(
            family= socket.AF_INET,
            local_host= self._selected_interface.local_ip,
            local_port=0    # ephemeral port, let OS decide
        )

        if not self._udp_socket:
            return False
        
        # Enable broadcast for selected interface
        raw_sock: socket.socket = self._udp_socket.extra(SocketAttribute.raw_socket)
        raw_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        raw_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        return True

    async def send_udp_packet(self, data: bytes, target_ip: str, target_port: int) -> None:
        assert self._udp_socket is not None
        await self._udp_socket.sendto(data, target_ip, target_port)

    async def send_udp_broadcast(self, data: bytes, target_port: int) -> None:
        assert self._selected_interface.broadcast_ip is not None
        await self.send_udp_packet(data, self._selected_interface.broadcast_ip, target_port)

async def main():

    net_mgr = NetworkManager()
    # objprint(net_mgr.get_available_interfaces(), honor_existing=False)
    available_interfaces = net_mgr.get_available_interfaces()
    num_available_interfaces = len(available_interfaces)

    print("List of available interfaces:")
    for i in range(num_available_interfaces):
        print(f"Interface #{i}:")
        print(f"Name: {available_interfaces[i].name}")
        print(f"Local IP: {available_interfaces[i].local_ip}")
        print(f"Broadcast IP: {available_interfaces[i].broadcast_ip}")
        print(f"Net Mask: {available_interfaces[i].netmask}")
        print(f"MAC Address: {available_interfaces[i].mac}")
        print("")

    selected_interface_index = int(input("Enter the index of selected interface: #"))
    selected_interface_name = available_interfaces[selected_interface_index].name
    await net_mgr.set_interface(selected_interface_name)
    
    i=0
    while True:
        i+=1
        await net_mgr.send_udp_broadcast(DISCOVERY_MESSAGE.encode(), PORT_DISCOVERY)
        print(f"Discovery #{i} sent to port {PORT_DISCOVERY}: {DISCOVERY_MESSAGE}")
        await anyio.sleep(1)
        
if __name__ == "__main__":
    anyio.run(main)