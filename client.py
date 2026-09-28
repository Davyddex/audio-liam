import numpy as np
import sounddevice as sd

import socket
import threading
import time
import struct

from config import PORT, ENCODING, STOP, BIT_HEADER_SIZE


server_ip = input("Address:")

server_address = (server_ip, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.connect(server_address)
except:
    print("No connection establish")
    exit()

#client.send(b"Hello")

# stop = STOP.encode(ENCODING)
# client.send(stop)
