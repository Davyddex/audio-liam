"""Audio playback helpers."""
import sounddevice as sd


def open_playback(sample_rate, channels, block_size, device=None):
    return sd.OutputStream(
        samplerate=sample_rate,
        channels=channels,
        blocksize=block_size,
        dtype="int16",
        device=device,
    )
