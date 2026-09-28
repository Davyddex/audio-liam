import numpy as np
import sounddevice as sd

import socket
import threading
import time
import struct

from config import PORT, ENCODING, STOP, BIT_HEADER_SIZE

server_ip = socket.gethostbyname(socket.gethostname())



server_address = (server_ip, PORT)
print(server_address)
client_connected = []  # Storing the client address of the client connected

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(server_address)

def send_to_list(list_of_user, data):
    """list_of_user = list of client_information
     data = data to send to the list"""

    # send  data to a list of client
    for other_client in list_of_user:
        try:
            # send of the information
            other_client.send(data)
        except:
            pass


def clientf(client, address):

    client_connected.append(client)

    while True:
        Header = client.recv(BIT_HEADER_SIZE).decode(ENCODING)
        if Header:
            print(Header)
            client.close()
            client_connected.remove(client)
            exit()
        time.sleep(1)


def start(Verbose=True):
    server.listen()
    if Verbose:
        print(f"[SERVER] : Server online.")
        print(f"[SERVER] : Connected port : {PORT}")
        print(f"[SERVER] : IP Address  : {server_ip}")
    up = False
    while not up:
        client, address = server.accept()
        thread_client = threading.Thread(target=clientf, args=(client, address))
        thread_client.start()
        time.sleep(1)
        up = thread_client.is_alive()
        if Verbose:
            print(f"[SERVER] : Active Connection : {address}")


start()

