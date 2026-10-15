import json

from netcheat.state import MAX_RECENT, State, state_file


def test_favourites_toggle_and_survive_a_reload():
    state = State.load()
    assert state.toggle_favourite("flow:x") is True
    assert State.load().favourites == ["flow:x"]
    assert state.toggle_favourite("flow:x") is False
    assert State.load().favourites == []


def test_recent_is_newest_first_without_duplicates_and_capped():
    state = State.load()
    for number in range(MAX_RECENT + 5):
        state.opened(f"flow:{number}")
    state.opened("flow:3")
    recent = State.load().recent
    assert recent[0] == "flow:3" and recent.count("flow:3") == 1
    assert len(recent) == MAX_RECENT


def test_a_broken_state_file_is_ignored():
    state_file().write_text("{not json")
    assert State.load() == State()
    state_file().write_text(json.dumps({"favourites": "oops", "recent": ["flow:x", 3]}))
    assert State.load() == State([], ["flow:x"])


def test_state_file_follows_xdg(monkeypatch, tmp_path):
    monkeypatch.delenv("NETCHEAT_STATE")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert state_file() == tmp_path / "netcheat" / "state.json"
