"""Sonidos provisorios de las cintas de despacho: SourceAssets/DispatchBox/cinta_encender.wav y cinta_apagar.wav.

python Scripts/make_belt_sounds.py

Encender: clic del hongo y un motor que arranca subiendo de tono. Apagar: clic y el motor que se frena.
"""
import wave
from pathlib import Path
import numpy as np

RATE = 44100
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/DispatchBox"
rng = np.random.default_rng(3)


def write(name, samples):
    samples = samples * 0.8 / np.max(np.abs(samples))
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((samples * 32767).astype("<i2").tobytes())


def click(length):
    t = np.arange(int(length * RATE)) / RATE
    body = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 400) + 0.6 * rng.uniform(-1, 1, len(t)) * np.exp(-t * 250)
    return body


def motor(length, f0, f1, fade_in, fade_out):
    t = np.arange(int(length * RATE)) / RATE
    freq = f0 + (f1 - f0) * (1 - np.exp(-t / (length / 3)))
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    tone = np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.3 * np.sin(3 * phase) + 0.15 * rng.uniform(-1, 1, len(t))
    env = np.minimum(1, t / fade_in) * np.clip((length - t) / fade_out, 0, 1)
    return tone * env


def combine(first, second, offset):
    out = np.zeros(max(len(first), int(offset * RATE) + len(second)))
    out[:len(first)] += first
    out[int(offset * RATE):int(offset * RATE) + len(second)] += 0.35 * second
    return out


OUT.mkdir(parents=True, exist_ok=True)
write("cinta_encender.wav", combine(click(0.08), motor(1.1, 35, 95, 0.35, 0.4), 0.05))
write("cinta_apagar.wav", combine(click(0.08), motor(1.0, 95, 25, 0.02, 0.7), 0.05))
print("BELT_SOUNDS_OK")
