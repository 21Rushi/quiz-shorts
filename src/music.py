"""Background music + sound effects for the quiz Short.

Everything is synthesised with numpy, so it is 100% original audio:
no copyright claims, no downloads needed. If you drop your own
royalty-free tracks (e.g. from the YouTube Audio Library) into
assets/music/, make_video.py uses one of those instead and only
layers the ticks + reveal chime from this file on top.
"""
import random
import wave

import numpy as np

SR = 44100


def _note(freq_name: str) -> float:
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3,
             "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    name, octave = freq_name[:-1], int(freq_name[-1])
    semis = names[name] + (octave - 4) * 12
    return 440.0 * 2 ** (semis / 12)


def _env(n, attack=0.01, release=0.3):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    r = np.exp(-t / max(release, 1e-4))
    return a * r


def _sine(freq, n, phase=0.0):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t + phase)


def _pad(freqs, n):
    out = np.zeros(n)
    for f in freqs:
        for detune in (-0.15, 0.15):
            out += _sine(f * (1 + detune / 100), n) * 0.5
            out += _sine(f * 2 * (1 + detune / 100), n) * 0.12
    swell = np.minimum(1, np.arange(n) / (0.4 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.3 * SR))
    return out * swell / len(freqs)


def _pluck(freq, n, decay=0.25):
    tone = _sine(freq, n) + 0.35 * _sine(freq * 2, n) + 0.12 * _sine(freq * 3, n)
    return tone * _env(n, 0.003, decay)


def _kick(n):
    t = np.arange(n) / SR
    f = 110 * np.exp(-t * 18) + 45
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * np.exp(-t * 9)


def _hat(n, rng):
    noise = rng.uniform(-1, 1, n)
    noise = np.diff(noise, prepend=0)  # crude high-pass
    return noise * np.exp(-np.arange(n) / SR * 60)


PROGRESSIONS = [
    # (chord roots + tones) – warm, upbeat-ish loops
    [["A3", "C4", "E4"], ["F3", "A3", "C4"], ["C4", "E4", "G4"], ["G3", "B3", "D4"]],
    [["C4", "E4", "G4"], ["G3", "B3", "D4"], ["A3", "C4", "E4"], ["F3", "A3", "C4"]],
    [["D4", "F4", "A4"], ["A#3", "D4", "F4"], ["F3", "A3", "C4"], ["C4", "E4", "G4"]],
    [["E3", "G3", "B3"], ["C4", "E4", "G4"], ["G3", "B3", "D4"], ["D4", "F#4", "A4"]],
]


def background_track(duration: float, seed: int, bpm: int = 96) -> np.ndarray:
    """Return a mono float32 track in [-1, 1]."""
    rng = np.random.default_rng(seed)
    pyrng = random.Random(seed)
    prog = PROGRESSIONS[seed % len(PROGRESSIONS)]
    bpm = bpm + pyrng.randint(-6, 10)
    beat = 60.0 / bpm
    n_total = int(duration * SR)
    bar = beat * 4
    n_bars = int(np.ceil(duration / bar)) + 1
    out = np.zeros(int((n_bars + 1) * bar * SR) + SR * 2)
    arp_patterns = [[0, 1, 2, 1], [0, 2, 1, 2], [2, 1, 0, 1], [0, 1, 2, 0]]
    pattern = arp_patterns[seed % len(arp_patterns)]

    for b in range(n_bars):
        chord = prog[b % len(prog)]
        freqs = [_note(x) for x in chord]
        start = int(b * bar * SR)
        nbar = int(bar * SR)
        if start >= n_total:
            break
        # pad
        out[start:start + nbar] += _pad(freqs, nbar) * 0.22
        # bass on beats 1 and 3
        for k in (0, 2):
            s = start + int(k * beat * SR)
            n = int(beat * 1.6 * SR)
            out[s:s + n] += _pluck(freqs[0] / 2, n, 0.35) * 0.32
        # 8th-note arpeggio
        for k in range(8):
            s = start + int(k * beat / 2 * SR)
            n = int(beat * SR)
            f = freqs[pattern[k % 4]] * 2
            out[s:s + n] += _pluck(f, n, 0.18) * 0.10
        # drums
        for k in range(4):
            s = start + int(k * beat * SR)
            n = int(0.35 * SR)
            if k in (0, 2):
                out[s:s + n] += _kick(n) * 0.45
            hs = s + int(beat / 2 * SR)
            hn = int(0.08 * SR)
            out[hs:hs + hn] += _hat(hn, rng) * 0.05
    out = out[:n_total]
    # simple soft-clip + normalise
    out = np.tanh(out * 1.2)
    out /= max(1e-6, np.max(np.abs(out)))
    return (out * 0.8).astype(np.float32)


def tick(n_sec=0.06, freq=1800):
    n = int(n_sec * SR)
    return (_sine(freq, n) * _env(n, 0.001, 0.015)).astype(np.float32)


def reveal_chime():
    n = int(1.6 * SR)
    out = np.zeros(n)
    for i, f in enumerate([_note("C5"), _note("E5"), _note("G5"), _note("C6")]):
        s = int(i * 0.07 * SR)
        out[s:] += _pluck(f, n - s, 0.5)[: n - s] * 0.5
    return (out / np.max(np.abs(out)) * 0.9).astype(np.float32)


def whoosh():
    n = int(0.45 * SR)
    rng = np.random.default_rng(7)
    noise = rng.uniform(-1, 1, n)
    k = np.ones(40) / 40
    noise = np.convolve(noise, k, mode="same")
    t = np.arange(n) / n
    return (noise * np.sin(np.pi * t) * 2.5).astype(np.float32)


def mix_sfx(track: np.ndarray, reveal_at: float, countdown_from: float) -> np.ndarray:
    """Duck the music a little at reveal and layer ticks + chime."""
    out = track.copy()
    # whoosh at start when options slide in
    w = whoosh() * 0.25
    out[: len(w)] += w
    # ticks every second during the last stretch of the countdown
    sec = countdown_from
    while sec < reveal_at - 0.01:
        s = int(sec * SR)
        tk = tick(freq=1800 if (reveal_at - sec) > 3 else 2400) * 0.55
        out[s:s + len(tk)] += tk[: max(0, len(out) - s)]
        sec += 1
    # chime
    s = int(reveal_at * SR)
    ch = reveal_chime() * 0.7
    out[s:s + len(ch)] += ch[: max(0, len(out) - s)]
    out = np.clip(out, -1, 1)
    return out


def write_wav(path: str, mono: np.ndarray):
    pcm = (np.clip(mono, -1, 1) * 32767).astype(np.int16)
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())
