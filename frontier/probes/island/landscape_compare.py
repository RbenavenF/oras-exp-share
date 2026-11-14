#!/usr/bin/env python3
"""Compare reference, production F11 and landscape trial renders at the same tile scale.

TopView uses texture averages; these are model renders, not Azahar screenshots.
    /usr/bin/python3 landscape_compare.py BEFORE.png AFTER.png OUT.png [PX_PER_TILE]
"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'frontier'))
import island_layout as layout


def main():
    before, after, out = map(Path, sys.argv[1:4])
    px = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    x, y = (n * px for n in layout.OFFSET)
    w, h = layout.W * px, layout.H * px
    box = (x, y, x + w, y + h)
    panels = [Image.open(ROOT / 'reports/diseno/referencias/frente-esmeralda.webp').convert('RGB').resize((w, h)),
              Image.open(before).convert('RGB').crop(box), Image.open(after).convert('RGB').crop(box)]
    canvas = Image.new('RGB', (w, (h + 28) * 3), 'white')
    draw = ImageDraw.Draw(canvas)
    for i, (label, panel) in enumerate(zip(['Referencia del usuario', 'F11 anterior: modelos, color medio de textura',
                                           'Acabado ORAS: modelos, color medio de textura'], panels)):
        draw.text((8, i * (h + 28) + 8), label, fill='black')
        canvas.paste(panel, (0, i * (h + 28) + 28))
    canvas.save(out)


if __name__ == '__main__':
    main()
