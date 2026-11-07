"""Receive microphone audio and expose it as a PipeWire virtual source."""
import argparse
import shutil
import socket
import subprocess
import sys

from audioliam.protocol import recv_frame
from config import BLOCK_SIZE, CHANNELS, PORT, SAMPLE_RATE, SINK_DESCRIPTION, SINK_NAME


class VirtualMicrophone:
    """PipeWire/PulseAudio null sink; its monitor is the selectable mic source."""
    def __init__(self, sink_name, description):
        self.sink_name = sink_name
        self.module_id = None
        self.description = description

    def __enter__(self):
        pactl = shutil.which("pactl")
        if pactl is None:
            raise RuntimeError("pactl not found; install PipeWire's PulseAudio compatibility tools")
        result = subprocess.run(
            [pactl, "load-module", "module-null-sink", f"sink_name={self.sink_name}",
             f"sink_properties=device.description={self.description}"],
            check=True, capture_output=True, text=True,
        )
        self.module_id = result.stdout.strip()
        print(f"Virtual microphone ready: {self.sink_name}.monitor")
        print("Select that monitor source as the microphone in your application.")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.module_id is not None:
            pactl = shutil.which("pactl")
            if pactl:
                subprocess.run([pactl, "unload-module", self.module_id], check=False)


def serve_client(connection, address, sink_name):
    print(f"Sender connected: {address}")
    pacat = shutil.which("pacat")
    if pacat is None:
        raise RuntimeError("pacat not found; install PipeWire's PulseAudio compatibility tools")
    player = subprocess.Popen(
        [pacat, "--playback", f"--device={sink_name}", "--raw", "--format=s16le",
         f"--rate={SAMPLE_RATE}", f"--channels={CHANNELS}"],
        stdin=subprocess.PIPE,
    )
    try:
        with connection:
            while True:
                payload = recv_frame(connection)
                if payload is None:
                    break
                if len(payload) % (2 * CHANNELS):
                    raise ValueError("received audio frame has an invalid channel count")
                player.stdin.write(payload)
                player.stdin.flush()
    finally:
        player.stdin.close()
        if player.wait() not in (0,):
            raise RuntimeError("pacat playback process exited with an error")
    print(f"Sender disconnected: {address}")


def run(host, port, sink_name, description):
    with VirtualMicrophone(sink_name, description):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((host, port))
            listener.listen(1)
            print(f"Listening on {host}:{port}; waiting for a sender...")
            while True:
                connection, address = listener.accept()
                try:
                    serve_client(connection, address, sink_name)
                except (OSError, ValueError, RuntimeError) as exc:
                    print(f"Audio stream ended: {exc}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0", help="interface to listen on (default: all)")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--sink-name", default=SINK_NAME)
    parser.add_argument("--sink-description", default=SINK_DESCRIPTION)
    args = parser.parse_args()
    try:
        run(args.host, args.port, args.sink_name, args.sink_description)
    except KeyboardInterrupt:
        print("\nStopped.")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"AudioLiam receiver error: {exc}\n")


if __name__ == "__main__":
    main()
