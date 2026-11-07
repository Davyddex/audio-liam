"""Very small UDP broadcast discovery for receivers on the local network."""
import socket
import time

REQUEST = b"AUDIOLIAM_DISCOVER_V1"
RESPONSE_PREFIX = b"AUDIOLIAM_SERVER_V1 "


def serve_discovery(tcp_port, discovery_port, stop_event=None):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("0.0.0.0", discovery_port))
        listener.settimeout(0.5)
        while stop_event is None or not stop_event.is_set():
            try:
                message, address = listener.recvfrom(256)
            except socket.timeout:
                continue
            if message == REQUEST:
                listener.sendto(RESPONSE_PREFIX + str(tcp_port).encode("ascii"), address)


def find_receivers(discovery_port, timeout=1.2):
    found = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        probe.settimeout(0.15)
        probe.sendto(REQUEST, ("255.255.255.255", discovery_port))
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            probe.settimeout(remaining)
            try:
                message, address = probe.recvfrom(256)
            except socket.timeout:
                break
            if message.startswith(RESPONSE_PREFIX):
                try:
                    port = int(message[len(RESPONSE_PREFIX):].decode("ascii"))
                except ValueError:
                    continue
                found[address[0]] = port
    return found
