"""Shared AudioLiam settings."""
import os

PORT = int(os.getenv("AUDIOLIAM_PORT", "54536"))
DISCOVERY_PORT = int(os.getenv("AUDIOLIAM_DISCOVERY_PORT", str(PORT + 1)))
SAMPLE_RATE = int(os.getenv("AUDIOLIAM_SAMPLE_RATE", "48000"))
CHANNELS = 1
BLOCK_SIZE = int(os.getenv("AUDIOLIAM_BLOCK_SIZE", "480"))  # 10 ms at 48 kHz
SINK_NAME = os.getenv("AUDIOLIAM_SINK_NAME", "audioliam_virtual_mic")
SINK_DESCRIPTION = os.getenv("AUDIOLIAM_SINK_DESCRIPTION", "AudioLiam Virtual Microphone")
SOURCE_NAME = os.getenv("AUDIOLIAM_SOURCE_NAME", "audioliam_microphone")
