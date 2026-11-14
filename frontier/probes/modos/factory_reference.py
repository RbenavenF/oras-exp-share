#!/usr/bin/env python3
"""Cotejo de rangos Libre desde objetos Git fijados; no modifica el checkout.

python frontier/probes/modos/factory_reference.py /tmp/frontier-cerebros-pokeemerald
Solo emite IDs, equivalencias de especie y hashes; ningún movimiento del volcado.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'frontier'))
import data as fd
import factory_open as fo

REF = '731ad5bfd6e6f265508d0efcca0ba42f9dcf5881'
FILES = ('src/battle_factory.c', 'include/constants/battle_frontier_mons.h',
         'src/data/battle_frontier/battle_frontier_mons.h', 'include/constants/pokedex.h')


def reference(sources):
    """Extract real set IDs/species and the eight Open ranges, without C evaluation."""
    factory, constants, mons, dex = (sources[p] for p in FILES)
    ids = {name: int(i) for name, i in re.findall(r'#define\s+(FRONTIER_MONS?_\w+)\s+(\d+)\b', constants)}
    ids['NUM_FRONTIER_MONS'] = int(re.search(r'#define\s+NUM_FRONTIER_MONS\s+(\d+)', constants)[1])
    national = {name: i for i, name in enumerate(re.findall(r'\bNATIONAL_DEX_(\w+)\s*,',
                         dex.split('// Old Unown')[0]))}
    if len(national) != 387 or national.get('LATIOS') != 381:
        raise ValueError('unexpected National Dex enum')
    rows = {}
    for name, species in re.findall(r'\[(FRONTIER_MON_\w+)\]\s*=\s*\{\s*\.species\s*=\s*SPECIES_(\w+)', mons):
        rows[ids[name]] = national[species]
    if set(rows) != set(range(882)):
        raise ValueError('expected exactly 882 Emerald sets')
    body = factory.split('static const u16 sInitialRentalMonRanges[][2] =', 1)[1].split('};', 1)[0]
    pairs = re.findall(r'\{\s*(FRONTIER_MON_\w+)\s*,\s*(FRONTIER_MONS?_\w+|NUM_FRONTIER_MONS)\s*(- 1)?\s*\}', body)
    ranges = [(ids[a], ids[b] - bool(minus)) for a, b, minus in pairs][8:]
    if ranges != [(372, 467), (468, 563), (564, 659), (660, 755), *[(372, 881)] * 4]:
        raise ValueError(f'Open ranges changed: {ranges}')
    return rows, ranges


def verify(repo):
    sources = {path: subprocess.check_output(['git', '-C', str(repo), 'show', f'{REF}:{path}']) for path in FILES}
    rows, ranges = reference({p: b.decode() for p, b in sources.items()})
    sets = fd.check_tiers(fd.load())
    fo.check_mapping(sets)
    strong = {sets[r][i]['species'] for r, i in fo.STRONG_POOLS[0]}
    for a, b in ranges[:4]:
        if {rows[i] for i in range(a, b + 1)} - strong != set(fo.SOURCE_STRONG_EXCLUSIONS):
            raise ValueError('strong species exclusions changed')
    if {rows[i] for i in range(756, 800)} != set(fo.LEGENDARY_SETS):
        raise ValueError('compatible legendary species differ from Emerald')
    candidates = {species: tuple(i for i, s in enumerate(sets['S']) if s['species'] == species)
                  for species in set(rows.values())}
    eligible = set(fo.OPEN_POOLS[-1])
    mapping = {i: {'species': rows[i], 'oras': tuple(j for j in candidates[rows[i]] if ('S', j) in eligible)}
               for i in range(372, 882)}
    excluded = {row['species'] for row in mapping.values() if not row['oras']}
    if excluded != set(fo.SOURCE_STRONG_EXCLUSIONS):
        raise ValueError('unmapped source species changed')
    # Verify tail by actual species; no arithmetic relation between the games' IDs.
    tail = {i: {'species': rows[i], 'oras': candidates[rows[i]]} for i in range(850, 882)}
    if any(tuple(row['oras']) != {**fo.TAIL_STRONG_SETS, **fo.LEGENDARY_SETS}[row['species']]
           for row in tail.values()):
        raise ValueError('tail equivalence changed')
    return {'commit': REF, 'source_sha256': {p: hashlib.sha256(b).hexdigest() for p, b in sources.items()},
            'archives': fd.ARCHIVES, 'open_ranges': ranges,
            'strong_source_species': len({rows[i] for i in range(372, 756)}),
            'strong_oras_species': len(strong), 'excluded_emerald_strong_species': fo.SOURCE_STRONG_EXCLUSIONS, 'compatible_legendaries': fo.LEGENDARY_SETS,
            'tail_850_881': tail, 'mapping_372_881': mapping,
            'unmapped_source_ids': [i for i, row in mapping.items() if not row['oras']], 'excluded_oras_species': fo.EXCLUDED_LEGENDARIES,
            'pool_counts': [len(p) for p in fo.OPEN_POOLS],
            'unique_final_species': len({sets[r][i]['species'] for r, i in fo.OPEN_POOLS[-1]})}


if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1])), indent=2))
