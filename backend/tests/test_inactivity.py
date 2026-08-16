from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INACTIVITY = ROOT / 'frontend' / 'src' / 'features' / 'auth' / 'inactivity.ts'
GUARD = ROOT / 'frontend' / 'src' / 'features' / 'auth' / 'InactivityGuard.tsx'


def test_inactivity_timeout_is_ten_minutes():
    source = INACTIVITY.read_text(encoding='utf-8')
    assert 'INACTIVITY_TIMEOUT_MS = 10 * 60 * 1000' in source
    assert 'WARNING_BEFORE_MS = 60 * 1000' in source
    assert 'mousedown' in source
    assert 'keydown' in source
    assert 'touchstart' in source
    assert 'pointerdown' in source


def test_inactivity_guard_signs_out_to_login():
    source = GUARD.read_text(encoding='utf-8')
    assert "navigate('/login'" in source
    assert 'signOut' in source
    assert 'INACTIVITY_WARNING_MESSAGE' in source
    assert 'fetch' not in source
    assert 'setInterval' in source


def test_activity_resets_timer():
    source = GUARD.read_text(encoding='utf-8')
    assert 'lastActivity.current = Date.now()' in source
    assert 'location.pathname' in source
