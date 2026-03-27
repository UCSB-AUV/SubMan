import socket

BROADCAST_PORT = 5000
MESSAGE = b"Hello from pure socket broadcast!"

# === CHANGE THESE ===
LOCAL_IP = "192.168.1.230"          # ←←← YOUR ACTUAL NIC IP
BROADCAST_ADDR = "192.168.1.255"   # ←←← subnet broadcast (NOT 255.255.255.255)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind explicitly to your interface (this fixes most Windows issues)
sock.bind((LOCAL_IP, 0))

print(f"Sending broadcast from {LOCAL_IP} to {BROADCAST_ADDR}:{BROADCAST_PORT}")
sock.sendto(MESSAGE, (BROADCAST_ADDR, BROADCAST_PORT))
print("sendto() completed — check Wireshark + NIC LED now")