"""Sonidos provisorios de cajas y de la mision: SourceAssets/Audio/caja_agarrar.wav, caja_soltar.wav y
mision_completa.wav (28/09). Para cambiarlos, reemplazar los WAV y volver a correr apply_mission.py.

python Scripts/make_ui_sounds.py

Agarrar: roce de carton que sube. Soltar: golpe sordo de carton. Mision cumplida: arpegio corto de campanas.
"""
import wave
from pathlib import Path
import numpy as np

RATE = 44100
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Audio"
rng = np.random.default_rng(11)


def write(name, samples, peak=0.8):
    samples = samples * peak / np.max(np.abs(samples))
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((samples * 32767).astype("<i2").tobytes())


def t_of(length):
    return np.arange(int(length * RATE)) / RATE


def lowpass(x, alpha):
    y = np.zeros_like(x)
    for i in range(1, len(x)):
        y[i] = y[i - 1] + alpha * (x[i] - y[i - 1])
    return y


def pickup():
    t = t_of(0.22)
    rustle = lowpass(rng.uniform(-1, 1, len(t)), 0.25) * np.sin(np.pi * t / t[-1]) ** 2
    lift = 0.35 * np.sin(2 * np.pi * (180 + 260 * t / t[-1]) * t) * np.exp(-t * 9)
    return rustle + lift


def drop():
    t = t_of(0.3)
    thump = np.sin(2 * np.pi * 85 * t) * np.exp(-t * 22) + 0.5 * np.sin(2 * np.pi * 140 * t) * np.exp(-t * 30)
    slap = 0.6 * lowpass(rng.uniform(-1, 1, len(t)), 0.35) * np.exp(-t * 45)
    return thump + slap


def mission():
    out = np.zeros(int(1.6 * RATE))
    for i, f in enumerate((523.25, 659.25, 783.99, 1046.5)):   # do mi sol do
        t = t_of(1.6 - 0.12 * i)
        bell = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t) + 0.2 * np.sin(2 * np.pi * 3.01 * f * t))
        start = int(0.12 * i * RATE)
        out[start:start + len(t)] += bell * np.exp(-t * (2.5 if i == 3 else 5))
    return out


OUT.mkdir(parents=True, exist_ok=True)
write("caja_agarrar.wav", pickup(), 0.55)
write("caja_soltar.wav", drop(), 0.7)
write("mision_completa.wav", mission(), 0.75)
print("UI_SOUNDS_OK")
