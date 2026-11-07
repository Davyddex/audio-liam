"""Very small UDP broadcast discovery for receivers on the local network."""
import ipaddress
import os
import re
import socket
import subprocess
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
        for target in _broadcast_targets():
            try:
                probe.sendto(REQUEST, (target, discovery_port))
            except OSError:
                continue
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


def _broadcast_targets():
    """Return limited and interface-directed broadcasts for active IPv4 nets."""
    targets = {"255.255.255.255"}
    networks = []
    if os.name == "nt":
        command = [
            "powershell", "-NoProfile", "-Command",
            "Get-NetIPAddress -AddressFamily IPv4 | "
            "Where-Object {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'} | "
            "ForEach-Object { '{0}/{1}' -f $_.IPAddress, $_.PrefixLength }",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
            entries = result.stdout.splitlines()
        except (OSError, subprocess.SubprocessError):
            entries = []
    else:
        try:
            result = subprocess.run(
                ["ip", "-o", "-4", "addr", "show", "up"],
                capture_output=True, text=True, timeout=3, check=False,
            )
            entries = re.findall(r"\binet\s+(\d+\.\d+\.\d+\.\d+/\d+)", result.stdout)
        except (OSError, subprocess.SubprocessError):
            entries = []

    if not entries:
        try:
            entries = [f"{item[4][0]}/24" for item in socket.getaddrinfo(
                socket.gethostname(), None, socket.AF_INET, socket.SOCK_DGRAM
            )]
        except OSError:
            entries = []

    for entry in entries:
        try:
            interface = ipaddress.IPv4Interface(entry.strip())
            address = interface.ip
            if address.is_loopback or address.is_link_local or interface.network.prefixlen >= 31:
                continue
            networks.append(interface.network)
        except ValueError:
            continue
    for network in networks:
        targets.add(str(network.broadcast_address))
    return sorted(targets)
