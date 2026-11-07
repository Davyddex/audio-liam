"""Receive one microphone stream and publish it as a PipeWire virtual source."""
import argparse
from collections import deque
import shutil
import socket
import subprocess
import sys
import threading
import time

import numpy as np

from audioliam.discovery import serve_discovery
from audioliam.monitor import make_event, render
from audioliam.protocol import BUSY, HELLO, READY, recv_exact, recv_frame
from config import (
    CHANNELS,
    PORT,
    SAMPLE_RATE,
    SINK_DESCRIPTION,
    SINK_NAME,
    SOURCE_NAME,
)


class VirtualMicrophone:
    """Playback sink feeding a separately named remapped microphone source."""
    def __init__(self, sink_name, description):
        self.sink_name = sink_name
        self.sink_module_id = None
        self.source_module_id = None
        self.description = description

    def __enter__(self):
        pactl = shutil.which("pactl")
        if pactl is None:
            raise RuntimeError("pactl not found; install PipeWire's PulseAudio compatibility tools")
        result = subprocess.run(
            [pactl, "load-module", "module-null-sink", f"sink_name={self.sink_name}",
             f"sink_properties=device.description={self.description} Output"],
            check=True, capture_output=True, text=True,
        )
        self.sink_module_id = result.stdout.strip()
        try:
            source = subprocess.run(
                [pactl, "load-module", "module-remap-source",
                 f"master={self.sink_name}.monitor", f"source_name={SOURCE_NAME}",
                 f"source_properties=device.description={self.description}"],
                check=True, capture_output=True, text=True,
            )
            self.source_module_id = source.stdout.strip()
        except Exception:
            subprocess.run([pactl, "unload-module", self.sink_module_id], check=False)
            self.sink_module_id = None
            raise
        print(f"Virtual microphone input ready: {SOURCE_NAME}")
        print(f"Select '{self.description}' as the microphone input in your application.")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pactl = shutil.which("pactl")
        if pactl:
            for module_id in (self.source_module_id, self.sink_module_id):
                if module_id is not None:
                    subprocess.run([pactl, "unload-module", module_id], check=False)


class ServerStatus:
    def __init__(self):
        self.lock = threading.Lock()
        self.active = False
        self.address = None
        self.missing_frames = 0
        self.rate_kib = 0.0
        self.audio = None
        self.refused = 0
        self.event = "Waiting for a sender"
        self.events = deque([make_event("Server started; waiting for a sender")], maxlen=4)

    def start(self, address):
        with self.lock:
            self.active = True
            self.address = address
            self.missing_frames = 0
            self.rate_kib = 0.0
            self.audio = None
            self.event = f"Connected: {address[0]}"
            self.events.append(make_event(f"Connection started from {address[0]}"))

    def end(self, event):
        with self.lock:
            self.active = False
            self.address = None
            self.event = event
            self.events.append(make_event(event))

    def refuse(self, address):
        with self.lock:
            self.refused += 1
            self.event = f"Rejected extra sender: {address[0]} (already in use)"
            self.events.append(make_event(f"Connection refused from {address[0]} (already connected)"))

    def incoming(self, address):
        with self.lock:
            self.events.append(make_event(f"Incoming connection from {address[0]}"))

    def frame(self, payload, missing, rate_kib):
        with self.lock:
            self.missing_frames += missing
            self.rate_kib = rate_kib
            self.audio = np.frombuffer(payload, dtype=np.int16).copy()

    def snapshot(self):
        with self.lock:
            return (self.active, self.address, self.missing_frames,
                    self.rate_kib, self.audio, self.refused, self.event, list(self.events))


def serve_client(connection, address, sink_name, status, monitor=True):
    pacat = shutil.which("pacat")
    if pacat is None:
        status.end("pacat not found")
        connection.close()
        if not monitor:
            print("Stream stopped: pacat not found")
        return
    try:
        player = subprocess.Popen(
            [pacat, "--playback", f"--device={sink_name}", "--raw", "--format=s16le",
             f"--rate={SAMPLE_RATE}", f"--channels={CHANNELS}", "--latency-msec=30"],
            stdin=subprocess.PIPE,
        )
        started = time.monotonic()
        expected_sequence = 0
        try:
            with connection:
                connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                while True:
                    packet = recv_frame(connection)
                    if packet is None:
                        break
                    sequence, payload = packet
                    if len(payload) % (2 * CHANNELS):
                        raise ValueError("received audio frame has an invalid channel count")
                    gap = (sequence - expected_sequence) & 0xFFFFFFFF
                    missing = gap if gap < 0x80000000 else 0
                    expected_sequence = (sequence + 1) & 0xFFFFFFFF
                    player.stdin.write(payload)
                    player.stdin.flush()
                    elapsed = max(time.monotonic() - started, 0.001)
                    status.frame(payload, missing, len(payload) / elapsed / 1024)
        finally:
            try:
                player.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            player.wait()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        status.end(f"Stream stopped: {exc}")
        if not monitor:
            print(f"Stream stopped: {exc}")
    else:
        status.end(f"Disconnected: {address[0]}")
        if not monitor:
            print(f"Connection closed: {address[0]}")


def run(host, port, discovery_port, sink_name, description, monitor=True):
    discovery_port = discovery_port or port
    status = ServerStatus()
    with VirtualMicrophone(sink_name, description):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((host, port))
            listener.listen(8)
            listener.settimeout(0.15)
            discovery_thread = threading.Thread(
                target=serve_discovery, args=(port, discovery_port), daemon=True,
            )
            discovery_thread.start()
            print(f"AudioLiam ready on TCP {host}:{port}; discovery UDP {discovery_port}")
            last_draw = 0.0
            while True:
                try:
                    connection, address = listener.accept()
                except socket.timeout:
                    connection = None
                if connection is not None:
                    status.incoming(address)
                    with status.lock:
                        already_active = status.active
                        if not already_active:
                            status.active = True  # reserve the single sender slot
                            status.address = address
                    if already_active:
                        status.refuse(address)
                        if not monitor:
                            print(f"Connection refused from {address[0]}: already connected")
                        try:
                            connection.sendall(BUSY)
                        except OSError:
                            pass
                        connection.close()
                    else:
                        connection.settimeout(5)
                        try:
                            hello = recv_exact(connection, len(HELLO))
                            if hello != HELLO:
                                status.end("Rejected client with incompatible protocol")
                                if not monitor:
                                    print(f"Rejected incompatible client from {address[0]}")
                                connection.close()
                            else:
                                status.start(address)
                                if not monitor:
                                    print(f"Connection started from {address[0]}")
                                connection.sendall(READY)
                                connection.settimeout(None)
                                worker = threading.Thread(
                                    target=serve_client,
                                    args=(connection, address, sink_name, status, monitor),
                                    daemon=True,
                                )
                                worker.start()
                        except OSError as exc:
                            status.end(f"Connection failed: {exc}")
                            if not monitor:
                                print(f"Connection failed from {address[0]}: {exc}")
                            connection.close()

                now = time.monotonic()
                if monitor and now - last_draw >= 0.15:
                    active, address, missing, rate, audio, refused, event, events = status.snapshot()
                    render(
                        "AudioLiam Receiver",
                        [
                            f"Listening: {host}:{port}    Discovery UDP: {discovery_port}",
                            f"State: {'CONNECTED' if active else 'waiting'}    Sender: {address[0] if address else '-'}",
                            f"Missing audio frames: {missing}",
                            f"Rate: {rate:,.1f} KiB/s    Rejected extra senders: {refused}",
                            f"Status: {event}",
                        ],
                        audio,
                        SAMPLE_RATE,
                        events,
                    )
                    last_draw = now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0", help="interface to listen on (default: all)")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--discovery-port", type=int, help="UDP discovery port (defaults to --port)")
    parser.add_argument("--sink-name", default=SINK_NAME)
    parser.add_argument("--sink-description", default=SINK_DESCRIPTION)
    parser.add_argument("--no-monitor", action="store_true", help="disable the live terminal dashboard")
    args = parser.parse_args()
    try:
        run(args.host, args.port, args.discovery_port, args.sink_name, args.sink_description,
            monitor=not args.no_monitor)
    except KeyboardInterrupt:
        print("\nStopped.")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"AudioLiam receiver error: {exc}\n")


if __name__ == "__main__":
    main()
