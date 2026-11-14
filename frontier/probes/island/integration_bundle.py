#!/usr/bin/env python3
"""Export reviewable F11 integration sources, without editing common files.

Usage: python frontier/probes/island/integration_bundle.py OUTPUT_DIRECTORY
No workspace, previous build, ROM, save or emulator is required.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

from landscape import HERE, ROOT, integration_helper, integration_source, placements


def export(destination):
    source = ROOT / 'faraway/java/ctrmap/tests/FrontierIsland.java'
    original = source.read_text()
    modified = integration_source(original)
    helper = integration_helper((HERE / 'IslandLandscape.java').read_text())
    chosen = placements(40, 140, 40)
    files = {
        'IslandLandscape.java': helper,
        'FrontierIsland.diff': ''.join(difflib.unified_diff(
            original.splitlines(True), modified.splitlines(True),
            fromfile='a/faraway/java/ctrmap/tests/FrontierIsland.java',
            tofile='b/faraway/java/ctrmap/tests/FrontierIsland.java')),
        'landscape-plan.properties': ''.join(
            f'island.landscape.{i}={line}\n' for i, line in enumerate(chosen)),
    }
    manifest = {
        'builder_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'helper_source_sha256': hashlib.sha256((HERE / 'IslandLandscape.java').read_bytes()).hexdigest(),
        'placements': len(chosen),
        'files': {name: hashlib.sha256(value.encode()).hexdigest() for name, value in files.items()},
    }
    # Refuse to replace existing evidence, including symlinks.
    destination.mkdir(parents=True, exist_ok=False)
    for name, value in files.items():
        (destination / name).write_text(value)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(export(args.destination), indent=2))
