#!/usr/bin/env python3
"""Render the F11 trace beside its reference. /usr/bin/python3 frontier/island_render.py (Pillow)."""
import argparse
from pathlib import Path
import island_layout as L

COLORS = dict(zip('~w.:,sm=#TpofxB+', [
    '#3477b7', '#5ca6dc', '#dadac5', '#c0ab87', '#86bb72', '#e7d69a', '#a88960', '#b0a698',
    '#99714f', '#35643a', '#da829b', '#786557', '#ecebd2', '#866c94', '#877b80', '#eb453f']))


def render(output):
    from PIL import Image, ImageDraw
    reference = Image.open(Path(__file__).resolve().parents[1] / 'reports/diseno/referencias/frente-esmeralda.webp').convert('RGB')
    tile, margin, label = 8, 16, 24
    w, h = L.W * tile, L.H * tile
    canvas = Image.new('RGB', (w * 2 + margin * 3, h * 2 + margin * 3 + label * 2 + 140), 'white')
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, margin), 'Referencia del usuario (16 px/casilla, reducida al 50%)', fill='black')
    canvas.paste(reference.resize((w, h)), (margin, margin + label))
    for shaded, ox, oy, title in [(False, w + margin * 2, margin, 'Calco: clase por casilla'),
                                  (True, margin, h + label + margin * 2, 'Calco: clase y altura (0-3)')]:
        draw.text((ox, oy), title, fill='black')
        for y, row in enumerate(L.GRID):
            for x, c in enumerate(row):
                rgb = tuple(bytes.fromhex(COLORS[c][1:]))
                if shaded:
                    factor = .62 + int(L.HEIGHT[y][x]) * .17
                    rgb = tuple(min(255, round(v * factor)) for v in rgb)
                xx, yy = ox + x * tile, oy + label + y * tile
                draw.rectangle((xx, yy, xx + tile - 1, yy + tile - 1), fill=rgb)
        # Cell borders in the padded ORAS frame: local x=24,64,104; y=36.
        for x in (24, 64, 104):
            draw.line((ox + x * tile, oy + label, ox + x * tile, oy + label + h), fill='#e85555')
        draw.line((ox, oy + label + 36 * tile, ox + w, oy + label + 36 * tile), fill='#e85555')
        for name, (x, y) in L.DOORS.items():
            draw.text((ox + x * tile + 4, oy + label + y * tile), name, fill='black')
    ox, oy = w + margin * 2, h + label + margin * 2
    draw.text((ox, oy), 'Leyenda; rojo: fronteras de celda ORAS', fill='black')
    for i, (c, description) in enumerate(L.LEGEND.items()):
        yy = oy + 25 + i * 24
        draw.rectangle((ox, yy, ox + 16, yy + 16), fill=COLORS[c])
        draw.text((ox + 25, yy), c + '  ' + description, fill='black')
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('work/f11/calco.png'))
    render(parser.parse_args().output)
