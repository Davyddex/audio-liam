"""Cross-platform terminal status display with a slow-fading spectrum."""
from datetime import datetime
import time

import numpy as np


class SpectrumHold:
    """Fast attack and slow release for frequency-band display levels."""
    def __init__(self, band_count=24, release_seconds=1.2):
        self.band_count = band_count
        self.release_seconds = release_seconds
        self.levels = np.zeros(band_count, dtype=np.float32)
        self.history = np.zeros(2048, dtype=np.float32)
        self.last_update = time.monotonic()

    def update(self, audio, sample_rate):
        incoming = np.asarray(audio, dtype=np.float32).reshape(-1)
        if incoming.size == 0:
            return
        if incoming.size >= self.history.size:
            self.history[:] = incoming[-self.history.size:]
        else:
            self.history[:-incoming.size] = self.history[incoming.size:]
            self.history[-incoming.size:] = incoming
        samples = self.history
        window = np.hanning(samples.size).astype(np.float32)
        spectrum = np.abs(np.fft.rfft(samples * window))
        frequencies = np.fft.rfftfreq(samples.size, 1.0 / sample_rate)
        edges = np.geomspace(90.0, min(9000.0, sample_rate / 2), self.band_count + 1)
        target = np.zeros(self.band_count, dtype=np.float32)
        window_gain = max(float(np.sum(window)), 1.0)
        for index, (low, high) in enumerate(zip(edges[:-1], edges[1:])):
            band = spectrum[(frequencies >= low) & (frequencies < high)]
            magnitude = float(np.max(band)) if band.size else 0.0
            dbfs = 20.0 * np.log10(max(2.0 * magnitude / window_gain / 32768.0, 1e-7))
            target[index] = max(0.0, min(1.0, (dbfs + 78.0) / 63.0))

        now = time.monotonic()
        elapsed = max(0.02, min(now - self.last_update, 0.5))
        self.last_update = now
        # Attack quickly, then let each band decay over about 1.2 seconds.
        attacking = target >= self.levels
        self.levels[attacking] += (target[attacking] - self.levels[attacking]) * 0.8
        self.levels[~attacking] = np.maximum(
            target[~attacking],
            self.levels[~attacking] * np.exp(-elapsed / self.release_seconds),
        )

    def lines(self, height=12):
        partial = " ▁▂▃▄▅▆▇"
        output = []
        units = self.levels * height
        for row in range(height, 0, -1):
            cells = []
            for value in units:
                if value >= row:
                    cells.append("█")
                elif value > row - 1:
                    fraction = int((value - (row - 1)) * 8)
                    cells.append(partial[max(1, min(7, fraction))])
                else:
                    cells.append("┄" if row in (3, 6, 9, 12) else " ")
            output.append(f"{row:02d} ┤" + " ".join(cells))
        output.append("00 └" + "┴ " * self.band_count)
        return output


_spectra = {}
_meters = {}


def make_event(message):
    return datetime.now().strftime("%H:%M:%S"), time.monotonic(), message


def _format_event(event):
    if isinstance(event, tuple) and len(event) == 3:
        timestamp, created, message = event
        age = max(0.0, time.monotonic() - created)
        return f"> {timestamp}  {age:5.1f}s ago  {message}"
    return f"> {datetime.now().strftime('%H:%M:%S')}  {event}"


def audio_stats(audio):
    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    if samples.size == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(samples * samples)))
    return 20.0 * np.log10(max(rms / 32768.0, 1e-6))


class LevelSmoother:
    """Quick meter attack and a short, gentle release."""
    def __init__(self, release_seconds=0.28, attack_seconds=0.045):
        self.release_seconds = release_seconds
        self.attack_seconds = attack_seconds
        self.level = -120.0
        self.last_update = time.monotonic()

    def update(self, target):
        now = time.monotonic()
        elapsed = max(0.02, min(now - self.last_update, 0.5))
        self.last_update = now
        duration = self.attack_seconds if target > self.level else self.release_seconds
        amount = 1.0 - np.exp(-elapsed / duration)
        self.level += float(amount) * (target - self.level)
        return self.level


def render(title, lines, audio=None, sample_rate=48000, events=None):
    spectrum = _spectra.setdefault(title, SpectrumHold())
    level = _meters.setdefault(title, LevelSmoother())
    if audio is not None:
        spectrum.update(audio, sample_rate)
        level.update(audio_stats(audio))
    level_db = level.level
    meter_width = 24
    filled = max(0, min(meter_width, int((level_db + 60.0) / 60.0 * meter_width)))
    meter_bar = "█" * filled + " " * (meter_width - filled)
    body = [
        title,
        "=" * len(title),
        *lines,
        f"Input level: [{meter_bar}] {level_db:6.1f} dBFS",
        "Spectrum: 24 logarithmic buckets, 90 Hz → 9 kHz",
        *spectrum.lines(),
    ]
    if events:
        body.append("Recent events:")
        body.extend(_format_event(event) for event in events[-4:])
    body.append("Ctrl+C to stop")
    print("\033[2J\033[H" + "\n".join(body), end="\033[J", flush=True)
