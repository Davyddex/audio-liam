"""Small cross-platform ANSI terminal audio meter."""
import numpy as np


def audio_stats(audio, sample_rate, band_count=20):
    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    if samples.size == 0:
        return -120.0, ""
    rms = float(np.sqrt(np.mean(samples * samples)))
    level_db = 20.0 * np.log10(max(rms / 32768.0, 1e-6))

    window = np.hanning(samples.size).astype(np.float32)
    spectrum = np.abs(np.fft.rfft(samples * window))
    frequencies = np.fft.rfftfreq(samples.size, 1.0 / sample_rate)
    edges = np.geomspace(90.0, min(9000.0, sample_rate / 2), band_count + 1)
    bars = []
    for low, high in zip(edges[:-1], edges[1:]):
        band = spectrum[(frequencies >= low) & (frequencies < high)]
        magnitude = float(np.max(band)) if band.size else 0.0
        db = 20.0 * np.log10(max(magnitude / (samples.size * 32768.0), 1e-7))
        height = max(0, min(5, int((db + 75.0) / 12.0)))
        bars.append("#" * height + " " * (5 - height))
    return level_db, " ".join(bars)


def render(title, lines, audio=None, sample_rate=48000):
    level = -120.0
    spectrum = "(waiting for audio)"
    if audio is not None:
        level, spectrum = audio_stats(audio, sample_rate)
    meter_width = 24
    filled = max(0, min(meter_width, int((level + 60.0) / 60.0 * meter_width)))
    meter = "#" * filled + "-" * (meter_width - filled)
    body = [
        title,
        "=" * len(title),
        *lines,
        f"Input level: [{meter}] {level:6.1f} dBFS",
        "Spectrum:    " + spectrum,
        "Ctrl+C to stop",
    ]
    print("\033[2J\033[H" + "\n".join(body), end="\033[J", flush=True)
