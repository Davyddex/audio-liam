"""Capture the local microphone and send audio to an AudioLiam receiver."""
import argparse
import socket
import sys
import time

import numpy as np

from audioliam.capture import open_microphone
from audioliam.discovery import find_receivers
from audioliam.monitor import make_event, render
from audioliam.noisegate import NoiseGate
from audioliam.protocol import BUSY, HELLO, READY, encode_frame, recv_exact
from config import BLOCK_SIZE, CHANNELS, PORT, SAMPLE_RATE


def choose_receiver(port, discovery_port):
    while True:
        print("Searching for AudioLiam receivers on the local network...", flush=True)
        receivers = find_receivers(discovery_port)
        if len(receivers) == 1:
            address, discovered_port = next(iter(receivers.items()))
            print(f"Found receiver at {address}:{discovered_port}")
            return address, discovered_port
        if len(receivers) > 1:
            choices = list(receivers.items())
            print("Found receivers:")
            for index, (address, discovered_port) in enumerate(choices, 1):
                print(f"  {index}. {address}:{discovered_port}")
            answer = input("Select receiver number, enter an IP, or press Enter to retry: ").strip()
            if answer.isdigit() and 1 <= int(answer) <= len(choices):
                address, discovered_port = choices[int(answer) - 1]
                return address, discovered_port
            if answer:
                return answer, port
            continue
        answer = input(
            "No receiver found. Check UDP discovery on the receiver's firewall; "
            "enter its IP address or press Enter to retry: "
        ).strip()
        if answer:
            return answer, port


def run(host, port, device=None, noise_gate=True, discovery_port=None):
    discovery_port = discovery_port or port
    if not host:
        host, port = choose_receiver(port, discovery_port)
    print(f"Connecting to receiver {host}:{port}...", flush=True)
    with socket.create_connection((host, port), timeout=5) as connection:
        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        connection.sendall(HELLO)
        response = recv_exact(connection, len(READY))
        if response == BUSY:
            events = [make_event(f"Connecting to {host}:{port}"),
                      make_event("Connection refused: receiver already has a sender")]
            render("AudioLiam Sender", ["No microphone stream started."], events=events)
            print("This receiver already has a sender. Disconnect that sender before retrying.")
            return
        if response != READY:
            raise RuntimeError("receiver sent an invalid response; update both client and server")

        connection.settimeout(None)
        print("Connected. Opening microphone...", flush=True)
        events = [make_event(f"Connection started to {host}:{port}")]
        gate = NoiseGate() if noise_gate else None
        sequence = 0
        input_overflows = 0
        total_bytes = 0
        started = time.monotonic()
        last_draw = 0.0
        last_audio = None
        try:
            with open_microphone(SAMPLE_RATE, CHANNELS, BLOCK_SIZE, device) as stream:
                events.append(make_event("Microphone capture started"))
                while True:
                    audio, overflowed = stream.read(BLOCK_SIZE)
                    if overflowed:
                        input_overflows += 1
                    if gate is not None:
                        audio = gate.process(audio)
                    payload = np.asarray(audio, dtype=np.int16).tobytes()
                    connection.sendall(encode_frame(payload, sequence))
                    sequence = (sequence + 1) & 0xFFFFFFFF
                    total_bytes += len(payload)
                    last_audio = audio

                    now = time.monotonic()
                    if now - last_draw >= 0.15:
                        elapsed = max(now - started, 0.001)
                        render(
                            "AudioLiam Sender",
                            [
                                f"Receiver: {host}:{port}",
                                f"Input overflows: {input_overflows}",
                                f"Rate: {total_bytes / elapsed / 1024:,.1f} KiB/s    Gate: {'on' if gate else 'off'}",
                            ],
                            last_audio,
                            SAMPLE_RATE,
                            events,
                        )
                        last_draw = now
        finally:
            events.append(make_event("Connection closed"))
            render(
                "AudioLiam Sender",
                [f"Receiver: {host}:{port}", "Connection closed."],
                last_audio,
                SAMPLE_RATE,
                events,
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", nargs="?", help="receiver IP; omit to search the local network")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--discovery-port", type=int, help="UDP discovery port (defaults to --port)")
    parser.add_argument("--device", help="sounddevice input device name or index")
    parser.add_argument("--no-noise-gate", action="store_true", help="disable the gentle background noise gate")
    args = parser.parse_args()
    try:
        run(args.host, args.port, args.device, noise_gate=not args.no_noise_gate,
            discovery_port=args.discovery_port)
    except KeyboardInterrupt:
        print("\nStopped.")
    except (OSError, RuntimeError) as exc:
        parser.exit(1, f"AudioLiam sender error: {exc}\n")


if __name__ == "__main__":
    main()
