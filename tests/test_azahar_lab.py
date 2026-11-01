import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import azahar_lab


def test_stop_from_other_pid_namespace_keeps_session_metadata(tmp_path, monkeypatch):
    state = {'display': ':0', 'xvfb_pid': 123, 'azahar_pid': 456, 'pid_namespace': 'pid:[host]'}
    path = tmp_path / 'session.json'
    path.write_text(json.dumps(state))
    monkeypatch.setattr(azahar_lab, 'LAB', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['azahar_lab.py', 'stop'])
    monkeypatch.setattr(azahar_lab.os, 'readlink', lambda path: 'pid:[sandbox]')
    monkeypatch.setattr(azahar_lab.os, 'kill', lambda *args: pytest.fail('Must not signal an unrelated PID'))
    with pytest.raises(RuntimeError, match='same PID namespace'):
        azahar_lab.main()
    assert json.loads(path.read_text()) == state
    assert not (tmp_path / 'last-session.json').exists()
