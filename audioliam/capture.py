"""Microphone capture helpers."""
import sounddevice as sd


def open_microphone(sample_rate, channels, block_size, device=None):
    return sd.InputStream(
        samplerate=sample_rate,
        channels=channels,
        blocksize=block_size,
        dtype="int16",
        device=device,
    )
