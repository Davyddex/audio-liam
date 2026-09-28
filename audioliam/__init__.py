import numpy as np
import sounddevice as sd
import opuslib as ol
import socket
import threading
import time
import struct
import subprocess
import atexit

from config import *



def run_pactl(*args):
    """Run pactl and return stdout."""
    result = subprocess.run(
        ["pactl", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def create_virtual_sink():
    """Create a temporary virtual sink and return its module ID."""

    module_id = run_pactl(
        "load-module",
        "module-null-sink",
        f"sink_name={SINK_NAME}",
        f"sink_properties=device.description={SINK_DESCRIPTION}",
    )

    print(f"Created virtual sink: {SINK_NAME}")
    print(f"Module ID: {module_id}")

    return int(module_id)


def remove_virtual_sink(module_id):
    """Remove the temporary virtual sink."""

    try:
        run_pactl("unload-module", str(module_id))
        print("Virtual sink removed.")
    except subprocess.CalledProcessError:
        pass


def get_python_sink_inputs():
    """
    Find sink inputs belonging to this Python process.

    Returns a list of sink-input IDs.
    """

    output = run_pactl("list", "sink-inputs")

    sink_inputs = []

    blocks = output.split("Sink Input #")[1:]

    for block in blocks:
        first_line = block.splitlines()[0]

        try:
            sink_input_id = int(first_line.strip())
        except ValueError:
            continue

        # Look for the Python process
        if 'application.process.binary = "python"' in block:
            sink_inputs.append(sink_input_id)

        # Depending on how Python was launched, this can sometimes
        # be python3 instead.
        elif 'application.process.binary = "python3"' in block:
            sink_inputs.append(sink_input_id)

    return sink_inputs


def route_python_to_sink():
    """Move Python's audio stream to our virtual sink."""

    # Give PipeWire/PulseAudio a moment to register the stream
    time.sleep(0.1)

    sink_inputs = get_python_sink_inputs()

    if not sink_inputs:
        raise RuntimeError(
            "Could not find the Python audio stream."
        )

    for sink_input in sink_inputs:
        run_pactl(
            "move-sink-input",
            str(sink_input),
            SINK_NAME,
        )

        print(
            f"Moved sink-input {sink_input} "
            f"→ {SINK_NAME}"
        )


# ------------------------------------------------------------------
# Audio
# ------------------------------------------------------------------

sample_rate = 48000
frequency = 440
phase = 0


def callback(outdata, frames, time_info, status):
    global phase

    if status:
        print(status)

    t = (np.arange(frames) + phase) / sample_rate

    signal = 0.2 * np.sin(
        2 * np.pi * frequency * t
    )

    outdata[:, 0] = signal

    phase += frames


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

module_id = create_virtual_sink()

# Make sure the sink is removed even if Ctrl+C is used
atexit.register(remove_virtual_sink, module_id)


with sd.OutputStream(
    samplerate=sample_rate,
    channels=1,
    dtype="float32",
    callback=callback,
):
    # PipeWire now has a Python playback stream.
    route_python_to_sink()

    print()
    print("Playing into:", SINK_NAME)
    print()
    print("Virtual microphone:")
    print(f"    {SINK_NAME}.monitor")
    print()
    print("Press Enter to stop...")

    input()

