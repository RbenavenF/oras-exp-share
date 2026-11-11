"""Dome's own hall: retail zone 365 (League's large final hall), script/native donor 517.

Measured with faraway.Probe zones/entities/floor and WorldTextures; reports/frontier.md §37.
The flat floor covers the Maison Singles choreography (x=19–23, y=12–25), so the
Dome script and its cameras need no changes. Only the two receptionists and a
spectator remain; no retail League event, trigger or exit survives.
"""
import struct
from formats import zo_files
from pawn import Script

ZONE, DONOR = 456, 365
TEXT, NATIVE_DONOR = 619, 517
ZO_LIMIT = 17248
# Keep uid 1/2: Maison Singles/Doubles reception scripts address these actors.
NPCS = ((297, 5, 10, 17, 1), (62, 2, 23, 24, 1), (62, 3, 17, 24, 1))


def plan_lines(budget):
    return [f'text.{ZONE}={TEXT}', f'zone.{ZONE}.clearNpcs=1',
            f'zone.{ZONE}.clearTriggers=1', f'zone.{ZONE}.loadBudget={budget}',
            *(f'zone.{ZONE}.npc.{i}={m},{m},{event},0,{x},{y},0,{face}'
              for i, (m, event, x, y, face) in enumerate(NPCS)),
            *(f'regdonor.{m}=214' for m in sorted({n[0] for n in NPCS}))]


def check_room(raw, script, exit_zone, exit_warp):
    """Validate the complete ZO, including the unmodified Dome script and its only exit."""
    if len(raw) > ZO_LIMIT:
        raise ValueError(f'Dome room ZO {len(raw)} exceeds {ZO_LIMIT}')
    files = zo_files(raw)
    entities = files[1]
    if tuple(entities[4:9]) != (0, len(NPCS), 1, 0, 0):
        raise ValueError('Dome room has unexpected props/NPCs/warps/triggers')
    if struct.unpack_from('<HH', entities, 12 + len(NPCS) * 0x30) != (exit_zone, exit_warp):
        raise ValueError('Dome room exit does not lead to its plaza door')
    if struct.unpack_from('<H', files[0], 6)[0] != TEXT:
        raise ValueError('Dome room does not have the Maison helper texts')
    if files[2] != script or Script.parse(files[2]).build() != script:
        raise ValueError('Dome room did not preserve its script')
    return len(raw)
