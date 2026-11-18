"""Trilha original e simples (120 bpm) gerada por síntese, sem samples de terceiros."""
import numpy as np, wave, sys

SR = 44100
BPM = 120
BEAT = 60 / BPM


def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    e = np.minimum(t / a, 1.0) * np.exp(-t / d)
    return e


def kick(n):
    t = np.arange(n) / SR
    f = 120 * np.exp(-t * 18) + 45
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env(n, 0.002, 0.18)


def hat(n, rng):
    return rng.uniform(-1, 1, n) * env(n, 0.001, 0.03) * 0.35


def clap(n, rng):
    x = rng.uniform(-1, 1, n) * env(n, 0.002, 0.08)
    return np.convolve(x, np.ones(8) / 8, mode="same") * 0.6


def tone(freq, n, d=0.25, kind="saw"):
    t = np.arange(n) / SR
    if kind == "saw":
        w = sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 7))
    else:
        w = np.sin(2 * np.pi * freq * t)
    return w * env(n, 0.01, d)


def build(seconds, out):
    rng = np.random.default_rng(7)
    total = int(seconds * SR) + SR
    mix = np.zeros(total)
    step = BEAT / 2  # colcheia
    # progressão: Am - F - C - G (2 compassos cada acorde = 8 colcheias por compasso)
    roots = [220.0, 174.61, 261.63, 196.0]
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]
    i = 0
    t = 0.0
    while t < seconds:
        s = int(t * SR)
        bar_pos = i % 8
        chord_idx = (i // 16) % 4
        n = int(0.5 * SR)
        def add(sig, gain):
            e = min(total, s + len(sig))
            mix[s:e] += sig[: e - s] * gain
        if bar_pos in (0, 4):
            add(kick(n), 0.9)
        if bar_pos in (2, 6):
            add(clap(int(0.2 * SR), rng), 0.5)
        add(hat(int(0.06 * SR), rng), 0.5 if bar_pos % 2 else 0.25)
        # baixo em colcheias
        add(tone(roots[chord_idx] / 2, int(step * SR), 0.12, "saw"), 0.18)
        # stabs no contratempo
        if bar_pos in (1, 3, 5, 7):
            stab = sum(tone(f, int(0.25 * SR), 0.09, "saw") for f in chords[chord_idx])
            add(stab, 0.05)
        t += step
        i += 1
    mix = mix[: int(seconds * SR)]
    # fade out final
    fo = int(0.8 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.8
    data = (mix * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


if __name__ == "__main__":
    build(float(sys.argv[1]), sys.argv[2])
