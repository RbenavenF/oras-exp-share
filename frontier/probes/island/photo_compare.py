#!/usr/bin/env python3
"""Compare the reference and F11 model overview with unstitched Azahar photo frames.

Uses Pillow (system python). OUT.png WEST_SCREEN.png EAST_SCREEN.png.
Screenshots retain the whole framebuffer; no missing terrain is reconstructed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'frontier'))
import island_layout as layout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('west', type=Path)
    parser.add_argument('east', type=Path)
    parser.add_argument('--west-box', help='explicit screenshot crop: left,top,right,bottom')
    parser.add_argument('--east-box', help='explicit screenshot crop: left,top,right,bottom')
    args = parser.parse_args()
    output, west, east = args.output, args.west, args.east
    width, height = 1200, 675
    reference = Image.open(ROOT / 'reports/diseno/referencias/frente-esmeralda.webp').convert('RGB')
    before = Image.open(ROOT / 'work/f11/finish/before.png').convert('RGB')
    x, y = (n * 8 for n in layout.OFFSET)
    before = before.crop((x, y, x + layout.W * 8, y + layout.H * 8))
    canvas = Image.new('RGB', (width, (height + 32) * 2 + 482), 'white')
    draw = ImageDraw.Draw(canvas)
    for index, (label, panel) in enumerate([
        ('Referencia del usuario', reference),
        ('Antes: F11, modelos con color medio de textura (NO Azahar)', before),
    ]):
        top = index * (height + 32)
        draw.text((8, top + 8), label, fill='black')
        canvas.paste(panel.resize((width, height)), (0, top + 32))
    top = 2 * (height + 32)
    evidence = []
    for index, (label, file) in enumerate([
        ('Despues: Azahar cenital oeste (34,24)', west),
        ('Despues: Azahar cenital este (129,21)', east),
    ]):
        panel = Image.open(file).convert('RGB')
        raw_box = args.west_box if index == 0 else args.east_box
        box = tuple(map(int, raw_box.split(','))) if raw_box else None
        if box is not None:
            if len(box) != 4 or not (0 <= box[0] < box[2] <= panel.width and 0 <= box[1] < box[3] <= panel.height):
                raise ValueError('Crop must fit screenshot')
            panel = panel.crop(box)
            label += ' (recorte)'
        draw.text((index * 600 + 8, top + 8), label, fill='black')
        scale = min(600 / panel.width, 450 / panel.height)
        panel = panel.resize((round(panel.width * scale), round(panel.height * scale)))
        canvas.paste(panel, (index * 600 + (600 - panel.width) // 2, top + 32))
        evidence.append(dict(file=str(file), sha256=hashlib.sha256(file.read_bytes()).hexdigest(), crop=box))
    canvas.save(output)
    output.with_suffix('.json').write_text(json.dumps(evidence, indent=2) + '\n')


if __name__ == '__main__':
    main()
