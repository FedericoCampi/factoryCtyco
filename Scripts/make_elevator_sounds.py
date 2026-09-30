"""Sonidos provisorios del ascensor (sintetizados, sin dependencias): SourceAssets/Ascensor2/*.wav.

python Scripts/make_elevator_sounds.py

- ascensor_motor.wav: zumbido de 3 s que se repite sin corte (ciclos enteros).
- ascensor_golpe.wav: golpe grave corto del arranque y la frenada.
- ascensor_puerta.wav: deslizamiento de la puerta, ~0,9 s, con tope al final.
Reemplazables por los del usuario con el mismo nombre.
"""
import math
import random
import struct
import wave
from pathlib import Path

RATE = 44100
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Ascensor2"
random.seed(7)


def write(name, samples):
    peak = max(1e-6, max(abs(s) for s in samples))
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(s / peak * 0.8 * 32767)) for s in samples))


def lowpass(samples, alpha):
    out, y = [], 0.0
    for s in samples:
        y += alpha * (s - y)
        out.append(y)
    return out


def motor():
    n = RATE * 3
    samples = []
    for i in range(n):
        t = i / RATE
        # 60 Hz y armonicos (ciclos enteros en 3 s), con un batido lento de 1 Hz
        s = (math.sin(2 * math.pi * 60 * t) + 0.5 * math.sin(2 * math.pi * 120 * t)
             + 0.25 * math.sin(2 * math.pi * 180 * t) + 0.12 * math.sin(2 * math.pi * 300 * t))
        samples.append(s * (0.85 + 0.15 * math.sin(2 * math.pi * 1 * t)))
    noise = lowpass([random.uniform(-1, 1) for _ in range(n)], 0.05)
    return [a + 0.6 * b for a, b in zip(samples, noise)]


def clunk():
    n = int(RATE * 0.45)
    thump = [math.sin(2 * math.pi * (70 - 30 * i / n) * i / RATE) * math.exp(-i / RATE * 12) for i in range(n)]
    click = lowpass([random.uniform(-1, 1) * math.exp(-i / RATE * 60) for i in range(n)], 0.3)
    return [a + 0.7 * b for a, b in zip(thump, click)]


def door():
    n = int(RATE * 0.9)
    slide = lowpass([random.uniform(-1, 1) for _ in range(n)], 0.08)
    env = [math.sin(math.pi * min(1.0, i / (n * 0.8))) ** 0.6 if i < n * 0.8 else 0.0 for i in range(n)]
    stop_at = int(n * 0.8)
    stop = [math.sin(2 * math.pi * 110 * (i - stop_at) / RATE) * math.exp(-(i - stop_at) / RATE * 25) if i >= stop_at else 0.0
            for i in range(n)]
    return [0.6 * s * e + st for s, e, st in zip(slide, env, stop)]


OUT.mkdir(parents=True, exist_ok=True)
write("ascensor_motor.wav", motor())
write("ascensor_golpe.wav", clunk())
write("ascensor_puerta.wav", door())
print("SOUNDS_OK", sorted(p.name for p in OUT.glob("*.wav")))
