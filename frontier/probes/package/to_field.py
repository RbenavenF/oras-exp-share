#!/usr/bin/env python3
"""Lab only: press A (or KEY) every 2.5 s until the field's touch screen (bright DexNav header, pixel 500,480 =
255,237,234) is shown with no dialogue, then stop. Usage: to_field.py [--max N] [--key a]"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'frontier'))
from lab_factory import Png  # noqa: E402


def field():
    subprocess.run(['python', 'scripts/azahar_lab.py', 'screenshot'], cwd=ROOT, check=True, capture_output=True)
    img = Png(str(ROOT / 'work/azahar-lab/screen.png'))
    r = img.row(480)
    return tuple(r[500 * img.bpp:500 * img.bpp + 3]) == (255, 237, 234)


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--max', type=int, default=30)
p.add_argument('--key', default='a')
a = p.parse_args()
for i in range(a.max):
    if field():
        time.sleep(1.5)
        if field():
            print(f'field after {i} presses')
            sys.exit(0)
    subprocess.run(['python', 'scripts/azahar_lab.py', 'input', 'keydown', a.key, 'sleep', '0.08', 'keyup', a.key],
                   cwd=ROOT, check=True)
    time.sleep(2.5)
sys.exit('field not reached')
