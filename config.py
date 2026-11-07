"""Shared AudioLiam settings."""
import os

PORT = int(os.getenv("AUDIOLIAM_PORT", "54536"))
SAMPLE_RATE = int(os.getenv("AUDIOLIAM_SAMPLE_RATE", "48000"))
CHANNELS = 1
BLOCK_SIZE = int(os.getenv("AUDIOLIAM_BLOCK_SIZE", "960"))  # 20 ms at 48 kHz
SINK_NAME = os.getenv("AUDIOLIAM_SINK_NAME", "audioliam_virtual_mic")
SINK_DESCRIPTION = os.getenv("AUDIOLIAM_SINK_DESCRIPTION", "AudioLiam Virtual Microphone")
