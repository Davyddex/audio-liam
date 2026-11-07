"""Capture the local microphone and send audio to an AudioLiam receiver."""
import argparse
import socket
import sys

import numpy as np

from audioliam.capture import open_microphone
from audioliam.protocol import encode_frame
from config import BLOCK_SIZE, CHANNELS, PORT, SAMPLE_RATE


def run(host, port, device=None):
    print(f"Connecting to receiver {host}:{port}...", flush=True)
    with socket.create_connection((host, port), timeout=5) as connection:
        connection.settimeout(None)
        print("Connected. Opening microphone...", flush=True)
        try:
            with open_microphone(SAMPLE_RATE, CHANNELS, BLOCK_SIZE, device) as stream:
                print("Microphone ready; sending audio. Press Ctrl+C to stop.", flush=True)
                while True:
                    audio, overflowed = stream.read(BLOCK_SIZE)
                    if overflowed:
                        print("Warning: microphone input overflow", file=sys.stderr)
                    connection.sendall(encode_frame(np.asarray(audio, dtype=np.int16).tobytes()))
        except (BrokenPipeError, ConnectionResetError):
            print("Receiver disconnected.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="IP address or hostname of the receiver")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--device", help="sounddevice input device name or index")
    args = parser.parse_args()
    try:
        run(args.host, args.port, args.device)
    except KeyboardInterrupt:
        print("\nStopped.")
    except (OSError, RuntimeError) as exc:
        parser.exit(1, f"AudioLiam sender error: {exc}\n")


if __name__ == "__main__":
    main()
