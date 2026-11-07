"""A gentle frame-based gate for reducing background noise between speech."""
import numpy as np


class NoiseGate:
    """Fade quieter frames down by up to 12 dB; leave louder speech untouched."""

    def __init__(self, close_db=-55.0, open_db=-43.0, floor_gain=0.25):
        self.close_db = close_db
        self.open_db = open_db
        self.floor_gain = floor_gain
        self.gain = floor_gain

    def process(self, audio):
        samples = np.asarray(audio, dtype=np.float32)
        rms = float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0
        level_db = 20.0 * np.log10(max(rms / 32768.0, 1e-8))
        if level_db <= self.close_db:
            target = self.floor_gain
        elif level_db >= self.open_db:
            target = 1.0
        else:
            fraction = (level_db - self.close_db) / (self.open_db - self.close_db)
            target = self.floor_gain + fraction * (1.0 - self.floor_gain)

        # Ramp gain across each 10 ms frame to avoid abrupt changes/clicks.
        ramp = np.linspace(self.gain, target, samples.shape[0], endpoint=True, dtype=np.float32)
        self.gain = target
        return np.clip(samples * ramp[:, None], -32768, 32767).astype(np.int16)
