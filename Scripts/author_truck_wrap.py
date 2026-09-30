"""Ploteo del camion inspirado en League of Legends (28/09), diseno propio (sin logos oficiales).

Textura T_PloteoCamion (2048x720, la proporcion del lateral de la caja: 2,95 x 1,04 m): fondo azul noche
con degradado a azul hextech, rayos de luz diagonales, marco dorado doble con esquinas en punta, un emblema
hexagonal propio (hexagono dorado con una runa de cristal celeste) a la izquierda y el texto
"LEAGUE OF LEGENDS" en serif dorado con un filete y la bajada "LA GRIETA DEL INVOCADOR".
Salida: SourceAssets/Ploteo/T_PloteoCamion.png.

python Scripts/author_truck_wrap.py
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent.parent / "SourceAssets/Ploteo"
W, H = 2048, 720
GOLD, GOLD_LIGHT, GOLD_DARK = (200, 170, 110), (240, 230, 210), (120, 90, 50)
NAVY, BLUE, CYAN = (1, 10, 19), (9, 40, 70), (10, 200, 185)
FONTS = Path("C:/Windows/Fonts")


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


img = Image.new("RGB", (W, H))
px = img.load()
# Fondo: degradado diagonal azul noche -> azul hextech, mas claro detras del emblema.
for y in range(H):
    for x in range(W):
        t = min(1.0, max(0.0, (x / W) * 0.7 + (1 - y / H) * 0.3))
        c = lerp(BLUE, NAVY, t)
        glow = math.exp(-(((x - 330) / 420) ** 2 + ((y - 360) / 300) ** 2))
        px[x, y] = lerp(c, (20, 90, 120), glow * 0.55)

# Rayos de luz diagonales que salen del emblema.
rays = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(rays)
for i, ang in enumerate(range(-40, 45, 12)):
    a = math.radians(ang)
    w = 0.035 + 0.02 * (i % 2)
    d.polygon([(330, 360), (330 + 2600 * math.cos(a - w), 360 + 2600 * math.sin(a - w)),
               (330 + 2600 * math.cos(a + w), 360 + 2600 * math.sin(a + w))], fill=26)
rays = rays.filter(ImageFilter.GaussianBlur(18))
img = Image.composite(Image.new("RGB", (W, H), (60, 150, 190)), img, rays)

# Hexagonos de fondo, finos (patron hextech).
over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(over)
R = 46
for row in range(-1, H // int(R * 1.5) + 2):
    for col in range(-1, W // int(R * 1.732) + 2):
        cx = col * R * 1.732 + (row % 2) * R * 0.866
        cy = row * R * 1.5
        fade = max(0.0, 1 - abs(cx - 1400) / 900)   # solo en el centro-derecha, detras del texto
        if fade <= 0:
            continue
        pts = [(cx + R * math.cos(math.radians(60 * k + 30)), cy + R * math.sin(math.radians(60 * k + 30))) for k in range(6)]
        d.polygon(pts, outline=(120, 190, 220, int(28 * fade)))
img.paste(over, (0, 0), over)

d = ImageDraw.Draw(img)


def frame(inset, width, color, cut):
    """Marco con las esquinas cortadas en diagonal."""
    x0, y0, x1, y1 = inset, inset, W - inset, H - inset
    pts = [(x0 + cut, y0), (x1 - cut, y0), (x1, y0 + cut), (x1, y1 - cut), (x1 - cut, y1), (x0 + cut, y1), (x0, y1 - cut), (x0, y0 + cut)]
    d.line(pts + [pts[0]], fill=color, width=width, joint="curve")


frame(14, 10, GOLD_DARK, 46)
frame(18, 5, GOLD, 42)
frame(40, 2, GOLD, 30)
# Adornos en las esquinas: rombos dorados.
for cx, cy in ((64, 64), (W - 64, 64), (64, H - 64), (W - 64, H - 64)):
    d.polygon([(cx, cy - 14), (cx + 14, cy), (cx, cy + 14), (cx - 14, cy)], fill=GOLD, outline=GOLD_LIGHT)

# Emblema propio: hexagono dorado en capas con una runa de cristal.
EX, EY = 330, 360


def hexagon(r, rot=0):
    return [(EX + r * math.cos(math.radians(60 * k + rot)), EY + r * math.sin(math.radians(60 * k + rot))) for k in range(6)]


glow = Image.new("L", (W, H), 0)
ImageDraw.Draw(glow).polygon(hexagon(250, 30), fill=150)
glow = glow.filter(ImageFilter.GaussianBlur(40))
img = Image.composite(Image.new("RGB", (W, H), (70, 200, 230)), img, glow.point(lambda v: v // 2))
d = ImageDraw.Draw(img)
d.polygon(hexagon(215, 30), fill=GOLD_DARK)
d.polygon(hexagon(200, 30), fill=GOLD)
d.polygon(hexagon(182, 30), fill=(14, 34, 52))
d.polygon(hexagon(170, 30), outline=GOLD, width=4)
# Puntas del emblema (arriba y abajo), como una corona.
for s in (-1, 1):
    d.polygon([(EX - 40, EY + s * 200), (EX, EY + s * 262), (EX + 40, EY + s * 200)], fill=GOLD, outline=GOLD_LIGHT)
# Runa: un cristal en rombo con facetas y dos alas.
crystal = [(EX, EY - 118), (EX + 62, EY), (EX, EY + 118), (EX - 62, EY)]
d.polygon(crystal, fill=(20, 150, 170))
d.polygon([(EX, EY - 118), (EX + 62, EY), (EX, EY)], fill=(60, 220, 215))
d.polygon([(EX, EY - 118), (EX - 62, EY), (EX, EY)], fill=(30, 185, 195))
d.polygon([(EX, EY + 118), (EX - 62, EY), (EX, EY)], fill=(8, 95, 120))
d.line(crystal + [crystal[0]], fill=GOLD_LIGHT, width=4)
for s in (-1, 1):
    d.polygon([(EX + s * 78, EY - 70), (EX + s * 140, EY), (EX + s * 78, EY + 70), (EX + s * 100, EY)], fill=GOLD, outline=GOLD_LIGHT)
d.ellipse((EX - 12, EY - 12, EX + 12, EY + 12), fill=(235, 255, 250))

# Texto: serif dorado con sombra y un brillo claro arriba.
big = ImageFont.truetype(str(FONTS / "georgiab.ttf"), 132)
small = ImageFont.truetype(str(FONTS / "georgiab.ttf"), 74)
tag = ImageFont.truetype(str(FONTS / "georgia.ttf"), 44)
TX = 1310


def gold_text(xy, text, font, spacing):
    """Texto centrado en xy, letra por letra con espaciado extra, relleno en degradado dorado."""
    widths = [d.textlength(ch, font=font) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = xy[0] - total / 2
    top, bottom = font.getbbox("L")[1], font.getbbox("L")[3]
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    for ch, w in zip(text, widths):
        d.text((x + 5, xy[1] + 6), ch, font=font, fill=(0, 6, 12))
        md.text((x, xy[1]), ch, font=font, fill=255)
        x += w + spacing
    grad = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        t = min(1, max(0, (y - xy[1] - top) / max(1, bottom - top)))
        gd.line([(0, y), (W, y)], fill=lerp(GOLD_LIGHT, GOLD_DARK, t ** 1.4) if t < 1 else GOLD_DARK)
    img.paste(grad, (0, 0), mask)


gold_text((TX, 140), "LEAGUE", big, 14)
d = ImageDraw.Draw(img)
# "OF" entre dos filetes dorados.
d.line([(TX - 520, 346), (TX - 90, 346)], fill=GOLD, width=4)
d.line([(TX + 90, 346), (TX + 520, 346)], fill=GOLD, width=4)
for x in (TX - 520, TX + 520):
    d.polygon([(x, 336), (x + 10, 346), (x, 356), (x - 10, 346)], fill=GOLD_LIGHT)
gold_text((TX, 300), "OF", small, 10)
d = ImageDraw.Draw(img)
gold_text((TX, 386), "LEGENDS", big, 14)
d = ImageDraw.Draw(img)
w = d.textlength("LA GRIETA DEL INVOCADOR", font=tag) + 22 * 6
d.text((TX - w / 2, 580), "  ".join("LA GRIETA DEL INVOCADOR".split(" ")), font=tag, fill=(120, 205, 215))

OUT.mkdir(parents=True, exist_ok=True)
img.save(OUT / "T_PloteoCamion.png")
print("PLOTEO_OK", OUT / "T_PloteoCamion.png")
