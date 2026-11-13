import argparse
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier'))
import package  # noqa: E402


def lock_with(tmp_path, files):
    for rel, blob in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(blob)
    entries = [dict(path=rel, size=len(blob), sha256=hashlib.sha256(blob).hexdigest()) for rel, blob in files.items()]
    lock = tmp_path / 'lock.json'
    lock.write_text(json.dumps(dict(rom=entries[0], mod_files=entries[1:])))
    return lock


def test_source_lock_accepts_the_locked_inputs_and_refuses_another_dump(tmp_path):
    lock = lock_with(tmp_path, {'game/rom.3ds': b'rom' * 100, 'mod/code.ips': b'PATCHEOF'})
    assert set(package.check_source_lock(lock, tmp_path)) == {'game/rom.3ds', 'mod/code.ips'}
    (tmp_path / 'game/rom.3ds').write_bytes(b'ROM' * 100)          # same size, other dump
    with pytest.raises(ValueError, match='another dump'):
        package.check_source_lock(lock, tmp_path)
    assert set(package.check_source_lock(lock, tmp_path, rom=False)) == {'mod/code.ips'}
    (tmp_path / 'mod/code.ips').unlink()
    with pytest.raises(ValueError, match='Missing input'):
        package.check_source_lock(lock, tmp_path, rom=False)


def test_checked_files_needs_the_exact_set_and_hashes(tmp_path):
    (tmp_path / 'romfs').mkdir()
    (tmp_path / 'code.ips').write_bytes(b'a')
    (tmp_path / 'romfs/x').write_bytes(b'b')
    expected = {'code.ips': hashlib.sha256(b'a').hexdigest(), 'romfs/x': hashlib.sha256(b'b').hexdigest()}
    package.checked_files(tmp_path, expected)
    with pytest.raises(ValueError, match='Hash mismatch'):
        package.checked_files(tmp_path, {**expected, 'romfs/x': expected['code.ips']})
    with pytest.raises(ValueError, match='File set differs'):
        package.checked_files(tmp_path, {'code.ips': expected['code.ips']})
    with pytest.raises(ValueError, match='Unsafe'):
        package.checked_files(tmp_path, {'../code.ips': expected['code.ips']})


def fake_build(root, names):
    for rel in names:
        (root / 'romfs' / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / 'romfs' / rel).write_bytes(rel.encode())
    (root / 'code.ips').write_bytes(b'PATCHnewEOF')


def test_assemble_puts_the_build_over_v05_and_needs_the_whole_build(tmp_path):
    mod, build = tmp_path / 'mod', tmp_path / 'build'
    base = {'code.ips': '', 'romfs/DllBattle.cro': '', 'romfs/sound/bgm': '', 'romfs/a/0/1/2': ''}
    fake_build(build, package.BUILD_FILES)
    sources = package.assemble(base, mod, build)
    assert sources['code.ips'] == build / 'code.ips'
    assert sources['romfs/DllBattle.cro'] == build / 'romfs/DllBattle.cro'
    assert sources['romfs/.crr/static.crr'] == build / 'romfs/.crr/static.crr'
    assert sources['romfs/sound/bgm'] == mod / 'romfs/sound/bgm'
    assert sources['romfs/a/0/1/2'] == mod / 'romfs/a/0/1/2'
    (build / 'romfs/DllField.cro').unlink()
    with pytest.raises(ValueError, match='Unexpected build output'):
        package.assemble(base, mod, build)


def test_readme_covers_base_install_pass_facilities_and_console_status():
    text = package.README
    for needed in ('versión 1.0', 'SIN la actualización', 'Repolished 1.7.6', 'Luma', 'Enable game patching',
                   'Gana la Liga', 'marinero', 'Calagua', 'Pase del Frente', 'Isla del Frente',
                   'Fábrica', 'Torre', 'Palacio', 'Arena', 'Domo', 'Tubo', 'Pirámide',
                   'NO PROBADO EN CONSOLA', 'Mew', 'DllBattle.cro', 'DllField.cro', 'static.crr'):
        assert needed in text, needed


def test_readme_describes_alpha_arena_palace_and_video_limits():
    text = ' '.join(package.README.split())
    arena = text.split('- Arena Batalla', 1)[1].split('- Domo Batalla', 1)[0]
    assert 'juicio solo por Cuerpo' in arena
    assert 'Mente y Técnica aún no están implementadas' in arena
    assert 'Cambio prohibido mientras el Pokémon siga en pie' in arena
    assert 'mente, técnica y cuerpo' not in arena.lower()
    palace = text.split('- Palacio Batalla', 1)[1].split('- Arena Batalla', 1)[0]
    assert 'la presentación y la frase de derrota del entrenador esperan que pulses A' in palace
    assert 'te piden ordenar' not in palace
    assert 'Guardar vídeo' not in text.replace('Ya no aparece «Guardar vídeo»', '')


def test_readme_qualifies_validation_team_changes_and_level_exceptions():
    text = ' '.join(package.README.split())
    assert 'Todo lo del Frente está probado' not in text
    assert 'Tu equipo y tu caja no se tocan' not in text
    for needed in ('con límites pendientes', 'curación, amistad, recuerdos o cintas',
                   'por debajo del nivel 50 no suben hasta él', 'salvo la séptima',
                   'Los combates fuertes usan rango Súper',
                   'los salvajes pueden estar por debajo del nivel 50',
                   'incidencia de reanudación pendiente de reproducir',
                   'No se probaron con ese paquete las rondas completas', 'el juicio de la Arena'):
        assert needed in text, needed


def test_checkpoint_refuses_a_save_that_is_not_the_tested_one(tmp_path, monkeypatch):
    save = tmp_path / 'main'
    save.write_bytes(b'save')
    parser = argparse.ArgumentParser()
    args = argparse.Namespace(save=save, output=tmp_path / 'out', replace=False)
    monkeypatch.setattr(package, 'CHECKPOINT_SAVE_SHA256', '0' * 64)
    with pytest.raises(SystemExit):
        package.checkpoint(args, parser)
    assert not (tmp_path / 'out').exists()


@pytest.mark.skipif(not (ROOT / 'inputs/repolished').exists() or not package.BASE_DIR.exists(),
                    reason='needs the local inputs and dist/held-exp-share-v0.5')
def test_local_inputs_match_the_locks():
    package.check_source_lock(rom=False)
    package.check_code_inputs()
    base, mod = package.check_base()
    assert base['overlay_files']['code.ips'] == package.check_code_inputs()[
        'inputs/repolished/Omega Ruby Repolished (ver. 1.7.6)/code.ips']


def test_v02_readme_explains_the_console_hang_brains_and_video():
    text = ' '.join(package.README.split())
    assert package.VERSION == 'oras-frontier-alpha-v0.2' and '(alfa v0.2)' in text
    new = text.split('NUEVO EN LA v0.2', 1)[1].split('BASE EXACTA', 1)[0]
    for needed in ('TODO combate de tipo Mansión', 'la Mansión Batalla original', 'Luma', '0x579604', '0x579804',
                   'DllBattle.cro', 'Cerebros', 'Símbolos', 'Ya no aparece «Guardar vídeo»'):
        assert needed in new, needed
    for brain in ('Noland', 'Anabel', 'Spenser', 'Greta', 'Tucker', 'Lucy', 'Brandon'):
        assert brain in text, brain
    assert 'sin el jefe' not in text and 'ni jefe' not in text and 'sin jefes' not in text
    assert 'la v0.2 NO está probada aún en consola' in text


def test_v02_build_files_include_the_brains_trainers():
    assert 'a/1/8/3' in package.BUILD_FILES


@pytest.mark.skipif(not (ROOT / 'baseline/oras/clean/exefs/code.bin').exists(), reason='needs the clean code.bin')
def test_console_check_reports_luma_and_our_hook_and_refuses_the_reserve(tmp_path):
    sys.path.insert(0, str(ROOT / 'scripts'))
    import luma
    import patch
    from build_patch import diff_ips
    clean = patch.CLEAN.read_bytes()
    code = bytearray(clean)
    hook = bytes.fromhex('f0412de9')                               # push {r4-r8, lr}
    code[patch.HOOKS - patch.BASE:patch.HOOKS - patch.BASE + 4] = hook
    ips = tmp_path / 'code.ips'
    ips.write_bytes(diff_ips(clean, bytes(code)))
    check = package.console_check(ips)
    assert check['luma_payload_at'] == '0x579604' and check['hooks_at'] == '0x579804'
    assert check['luma_payload_first16'] == luma.PAYLOAD[:16].hex()
    assert check['hooks_first16'].startswith(hook.hex())
    assert set(check['luma_branches']) == {'0x123e80', '0x1325a4'}
    code[patch.CAVE - patch.BASE] = 1
    ips.write_bytes(diff_ips(clean, bytes(code)))
    with pytest.raises(ValueError, match='reserve'):
        package.console_check(ips)
