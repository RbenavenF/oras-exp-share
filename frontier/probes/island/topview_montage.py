#!/usr/bin/env python3
"""F11-ISLA-CONSTRUCCION lab only: the user's reference above the island as built (TopView.java render, cropped to the
trace at island_layout.OFFSET), same scale, for the side-by-side check of layout and proportions. Needs Pillow.
    topview_montage.py TOPVIEW.png OUT.png [PX_PER_TILE]"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'frontier'))
import island_layout as L  # noqa: E402

top, out = Image.open(sys.argv[1]).convert('RGB'), Path(sys.argv[2])
px = int(sys.argv[3]) if len(sys.argv) > 3 else 8
ox, oy = L.OFFSET[0] * px, L.OFFSET[1] * px
built = top.crop((ox, oy, ox + L.W * px, oy + L.H * px))
reference = Image.open(ROOT / 'reports/diseno/referencias/frente-esmeralda.webp').convert('RGB').resize(built.size)
label = 28
canvas = Image.new('RGB', (built.width, built.height * 2 + label * 2), 'white')
draw = ImageDraw.Draw(canvas)
draw.text((8, 8), 'Referencia (Frente Batalla de Esmeralda, imagen del usuario)', fill='black')
canvas.paste(reference, (0, label))
draw.text((8, built.height + label + 8), 'Isla construida (zona 209, modelos de las 8 celdas vistos desde arriba; '
          'rojo: puertas; azul: empleado del ferry)', fill='black')
canvas.paste(built, (0, built.height + label * 2))
canvas.save(out)
print(out, canvas.size)
