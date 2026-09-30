"""Musica de fondo del juego, sintetizada: SourceAssets/Audio/musica_fabrica.wav (estereo, loop sin corte).

python Scripts/make_music.py

La menor, 96 BPM, 32 compases (80 s): pad calido, bajo pulsante, arpegio que entra en el compas 5 y
percusion suave desde el 9; los ultimos 8 compases la sacan para que el loop respire. Las colas que
pasan del final se suman al principio, asi el loop no tiene corte. Reemplazable por un tema propio con
el mismo nombre (y volver a correr Scripts/apply_music_and_boxes.py).
"""
import wave
from pathlib import Path
import numpy as np

RATE = 44100
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
BARS = 32
N = int(round(BARS * BAR * RATE))
TAIL = int(3 * RATE)
OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Audio"
rng = np.random.default_rng(11)

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def hz(name, octave):
    return 440.0 * 2 ** ((NOTE[name] + 12 * (octave + 1) - 69) / 12)


# acordes por compas (raiz, tercera, quinta)
CHORDS = {"Am": ("A", "C", "E"), "F": ("F", "A", "C"), "C": ("C", "E", "G"), "G": ("G", "B", "D"),
          "Em": ("E", "G", "B"), "Dm": ("D", "F", "A")}
PROGRESSION = (["Am", "F", "C", "G"] * 2 + ["Am", "F", "G", "Em"] + ["Dm", "F", "G", "G"]) * 2

left = np.zeros(N + TAIL)
right = np.zeros(N + TAIL)


def add(signal, start, pan=0.0, gain=1.0):
    i0 = int(start * RATE)
    i1 = min(len(left), i0 + len(signal))
    s = signal[: i1 - i0] * gain
    left[i0:i1] += s * np.sqrt(0.5 * (1 - pan))
    right[i0:i1] += s * np.sqrt(0.5 * (1 + pan))


def lowpass(signal, cutoff):
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(len(signal), 1 / RATE)
    spectrum *= 1 / np.sqrt(1 + (freqs / cutoff) ** 4)
    return np.fft.irfft(spectrum, len(signal))


def saw(freq, t):
    return 2 * ((freq * t) % 1.0) - 1


# pad: dos sierras desafinadas por nota, filtradas, con ataque y salida suaves (se solapan entre compases)
for bar, chord in enumerate(PROGRESSION):
    length = BAR + 1.2
    t = np.arange(int(length * RATE)) / RATE
    env = np.minimum(1, t / 0.8) * np.clip((length - t) / 1.2, 0, 1)
    for i, name in enumerate(CHORDS[chord]):
        octave = 3 if i == 0 else 4
        f = hz(name, octave)
        for detune, pan in ((0.997, -0.5), (1.003, 0.5)):
            voice = lowpass(saw(f * detune, t + i * 0.01), 900) * env
            add(voice, bar * BAR, pan, 0.10)

# bajo: corcheas sobre la raiz, con acento en el tiempo 1
for bar, chord in enumerate(PROGRESSION):
    f = hz(CHORDS[chord][0], 2)
    for eighth in range(8):
        t = np.arange(int(0.3 * RATE)) / RATE
        tone = np.sin(2 * np.pi * f * t) + 0.3 * np.sign(np.sin(2 * np.pi * f * t))
        env = np.exp(-t * 9) * (1.0 if eighth == 0 else 0.7)
        add(lowpass(tone * env, 500), bar * BAR + eighth * BEAT / 2, 0.0, 0.28)

# arpegio: semicorcheas por las notas del acorde, del compas 5 al 28, alternando lados
for bar, chord in enumerate(PROGRESSION):
    if not 4 <= bar < 28:
        continue
    notes = [hz(n, 5) for n in CHORDS[chord]] + [hz(CHORDS[chord][0], 6)]
    pattern = [0, 1, 2, 3, 2, 1, 2, 3, 0, 2, 1, 3, 2, 1, 0, 2] if bar % 2 else [0, 1, 2, 1, 3, 2, 1, 2] * 2
    for step, k in enumerate(pattern):
        if bar >= 24 and step % 2:   # se afina hacia el final
            continue
        t = np.arange(int(0.35 * RATE)) / RATE
        f = notes[k]
        tone = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 11)
        add(tone, bar * BAR + step * BEAT / 4, 0.45 if step % 2 else -0.45, 0.06)

# percusion suave del compas 9 al 28: bombo en 1 y 3, platillo cerrado a contratiempo
for bar in range(8, 28):
    for beat in range(4):
        start = bar * BAR + beat * BEAT
        if beat in (0, 2):
            t = np.arange(int(0.35 * RATE)) / RATE
            sweep = 2 * np.pi * np.cumsum(45 + 55 * np.exp(-t * 30)) / RATE
            add(np.sin(sweep) * np.exp(-t * 10), start, 0.0, 0.35)
        t = np.arange(int(0.06 * RATE)) / RATE
        noise = rng.uniform(-1, 1, len(t))
        hat = (noise - lowpass(noise, 6000)) * np.exp(-t * 70)
        add(hat, start + BEAT / 2, 0.25, 0.10)

# loop sin corte: las colas vuelven al principio
for channel in (left, right):
    channel[:TAIL] += channel[N:N + TAIL]
mix = np.stack([left[:N], right[:N]], axis=1)
mix = np.tanh(mix * 1.4) / np.tanh(1.4)
mix *= 0.85 / np.max(np.abs(mix))
OUT.mkdir(parents=True, exist_ok=True)
with wave.open(str(OUT / "musica_fabrica.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("MUSIC_OK", round(N / RATE, 2), "s")
