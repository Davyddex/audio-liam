# AudioLiam

Stream a microphone from one computer to another and expose the received audio as a selectable virtual microphone on a Linux receiver running PipeWire (through its PulseAudio compatibility layer).

## Install

On both computers, install Python 3.9+ and the Python dependencies:

```sh
python -m pip install numpy sounddevice
```

The receiver also needs PipeWire with `pipewire-pulse` and the `pactl` and `pacat` commands available. On Debian/Ubuntu, both are provided by `pulseaudio-utils`.

## Start the receiver (Linux)

```sh
python server.py
```

The receiver creates a temporary playback sink plus a separate remapped PipeWire source named `audioliam_microphone`. Select **AudioLiam Virtual Microphone** as the microphone input in your application. Both virtual devices are removed when the receiver exits.

## Start the sender

On the computer with the physical microphone:

```sh
python client.py RECEIVER_IP
```

Use `--device` to select an input device and `--port` to change the default TCP port (`54536`). Press Ctrl+C to stop either process.

The stream uses mono 48 kHz signed 16-bit PCM in 20 ms frames. Ensure the receiver port is reachable through the network firewall. This initial implementation sends unencrypted audio and should only be used on a trusted network.
