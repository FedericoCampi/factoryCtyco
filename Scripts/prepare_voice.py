"""Prepara una voz grabada por el usuario para el juego (29/09).

python Scripts/prepare_voice.py <grabacion> <salida.wav>
Ej.: python Scripts/prepare_voice.py "C:/Users/Usuario/Desktop/3D assets/Voces/vagabundo_y_ella.m4a" SourceAssets/Vagabundo/vagabundo_y_ella.wav

Acepta cualquier formato que lea ffmpeg (m4a, mp3, ogg, opus, wav...). Pasa a 44,1 kHz mono de 16 bits, recorta el
silencio de los extremos (deja 80 ms antes y 250 ms despues), suaviza el principio y el final y normaliza el pico a
0,85. No cambia la voz. Las grabaciones del usuario van en C:/Users/Usuario/Desktop/3D assets/Voces.
"""
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
import numpy as np

source, target = Path(sys.argv[1]), Path(sys.argv[2])
RATE = 44100
with tempfile.TemporaryDirectory() as work:
    raw = Path(work) / "raw.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-ac", "1", "-ar", str(RATE),
                    "-sample_fmt", "s16", str(raw)], check=True)
    with wave.open(str(raw)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
window = RATE // 50
rms = np.array([np.sqrt(np.mean(x[i:i + window] ** 2)) for i in range(0, len(x), window)])
voiced = np.nonzero(rms > max(0.01, rms.max() * 0.08))[0]
if not len(voiced):
    raise SystemExit("La grabacion esta en silencio")
start = max(0, voiced[0] * window - int(0.08 * RATE))
end = min(len(x), (voiced[-1] + 1) * window + int(0.25 * RATE))
y = x[start:end].copy()
fade_in, fade_out = int(0.02 * RATE), int(0.12 * RATE)
y[:fade_in] *= np.linspace(0, 1, fade_in)
y[-fade_out:] *= np.linspace(1, 0, fade_out)
y *= 0.85 / np.max(np.abs(y))
target.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(target), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes((y * 32767).astype(np.int16).tobytes())
print(f"{target.name}: {len(y) / RATE:.2f} s (de {len(x) / RATE:.2f} s grabados)")
