"""Laboratory only: the island build without its Plaza step, kept as work/frontier/plaza-exp/base-game.

frontier/lab_plaza.sh paints plaza variants on copies of it (reports/frontier.md §21).
Usage: python frontier/lab_plaza_base.py
"""
import shutil
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import overlay, island_build
real = subprocess.run
def run(cmd, *a, **k):
    if 'Plaza' in cmd:
        return None
    return real(cmd, *a, **k)
island_build.subprocess.run = run
romfs = ROOT / 'work/faraway/dev/overlay/romfs'
archives, _ = overlay.build(romfs)
work = ROOT / 'work/frontier/plaza-exp/island'
try:
    island_build.build(archives, lambda rel: overlay.source(romfs, rel), work)
except ValueError as e:
    print('expected (no plaza):', str(e)[:60])
base = ROOT / 'work/frontier/plaza-exp/base-game'
if base.exists():
    shutil.rmtree(base)
shutil.copytree(work / 'game', base)
print('base at', base)
