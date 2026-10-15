import pytest


@pytest.fixture(autouse=True)
def private_state(tmp_path, monkeypatch):
    """Favourites and recents of a test run go to a temporary file, never to the user's own state."""
    monkeypatch.setenv("NETCHEAT_STATE", str(tmp_path / "state.json"))
    monkeypatch.delenv("NCS_RELEASE", raising=False)
