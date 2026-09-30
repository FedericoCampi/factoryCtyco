"""Voz del vagabundo: "¿Y ella?" (29/09).

La base es la voz sintetica de Windows "Microsoft Pablo" (es-ES), generada con SSML (lenta, grave y suave) en
SourceAssets/Vagabundo/vagabundo_y_ella_tts.wav. Aca se baja un poco mas el tono (remuestreo x0,9), se le da una voz
cascada (saturacion suave y un soplo de ruido), un eco corto de patio, se recorta el silencio y se normaliza.
Salida: SourceAssets/Vagabundo/vagabundo_y_ella_sintetica.wav (44,1 kHz, mono, 16 bits). Era la voz provisoria; desde
el 29/09 el juego usa la grabacion del usuario (prepare_voice.py -> vagabundo_y_ella.wav).

python Scripts/make_vagabundo_voice.py
"""
import wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1] / "SourceAssets/Vagabundo"
with wave.open(str(HERE / "vagabundo_y_ella_tts.wav")) as w:
    rate, width, channels = w.getframerate(), w.getsampwidth(), w.getnchannels()
    raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16 if width == 2 else np.int32)
x = raw.reshape(-1, channels).mean(axis=1).astype(np.float64) / (2 ** (8 * width - 1))
# recorte del silencio de los extremos
loud = np.nonzero(np.abs(x) > 0.02)[0]
x = x[max(0, loud[0] - int(0.05 * rate)): loud[-1] + int(0.15 * rate)]
# mas grave y lento: remuestreo a 44,1 kHz leyendo un 10 % mas despacio
OUT_RATE = 44100
t = np.arange(0, len(x) - 1, rate / OUT_RATE * 0.9)
y = np.interp(t, np.arange(len(x)), x)
# voz cascada: saturacion suave + un poco de ruido modulado por la envolvente
rng = np.random.default_rng(7)
env = np.convolve(np.abs(y), np.ones(400) / 400, mode="same")
y = np.tanh(y * 2.2) / np.tanh(2.2) + rng.normal(0, 1, len(y)) * env * 0.18
# eco corto de patio
for delay, gain in ((0.045, 0.22), (0.11, 0.12), (0.19, 0.06)):
    d = int(delay * OUT_RATE)
    y = np.concatenate([y, np.zeros(d)])
    y[d:] += gain * y[:-d]
fade = int(0.03 * OUT_RATE)
y[:fade] *= np.linspace(0, 1, fade)
y[-fade * 4:] *= np.linspace(1, 0, fade * 4)
y = y / np.max(np.abs(y)) * 0.85
with wave.open(str(HERE / "vagabundo_y_ella_sintetica.wav"), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(OUT_RATE)
    w.writeframes((y * 32767).astype(np.int16).tobytes())
print(f"vagabundo_y_ella_sintetica.wav: {len(y) / OUT_RATE:.2f} s (fuente {rate} Hz)")
