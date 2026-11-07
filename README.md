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
bash start_server.sh
```

The receiver creates a temporary playback sink plus a separate remapped PipeWire source named `audioliam_microphone`. Select **AudioLiam Virtual Microphone** as the microphone input in your application. Both virtual devices are removed when the receiver exits.

## Start the sender

On Linux, run:

```sh
bash start_client.sh
```

On Windows, double-click `start_client.bat`, or run it from a terminal. With no address supplied, the client searches the local network and connects automatically when it finds one receiver. It asks you to choose if it finds several. If discovery does not work on your Wi-Fi, enter the receiver's IP when prompted. A manual address also works: `bash start_client.sh 192.168.1.93` on Linux, or `start_client.bat 192.168.1.93` on Windows.

Use `--device` to select a microphone and `--port` to change the default TCP port (`54536`). Press Ctrl+C to stop. The Windows launcher pauses after the client exits so messages such as “receiver already has a sender” stay visible.

The server accepts one sender at a time. Additional clients are immediately told that the receiver is busy and exit; the server stays running for the active sender. The terminal dashboards keep a short event history and show detected missing audio frames, input level, rate, and a vertically stacked spectrum with fading block characters. Since the audio uses TCP, this reports missing application audio frames rather than raw network packet retransmissions.

Local discovery uses UDP port `54536`, the same port number used for audio over TCP. Both sockets use the same numeric port; allow both TCP and UDP `54536` through the receiver firewall (for UFW: `sudo ufw allow 54536/tcp` and `sudo ufw allow 54536/udp`). The client sends limited and interface-directed IPv4 broadcasts. Discovery is local-network only and does not cross VPNs; when connecting remotely, pass the receiver's VPN address directly, for example `python client.py 10.8.0.1`.

The stream uses mono 48 kHz signed 16-bit PCM in 10 ms frames, with a 30 ms requested playback latency. A gentle noise gate reduces quiet background noise between speech; use `--no-noise-gate` on the sender to disable it. The gate does not remove steady noise while speaking. Update both sender and receiver together because the stream protocol includes a connection handshake and sequenced frames. Audio is sent without additional encryption, so use it only on trusted networks or inside a VPN.
