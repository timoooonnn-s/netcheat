"""Personal state: favourite and recently opened entries, kept per user outside the repository.

Stored as JSON in $XDG_DATA_HOME/netcheat/state.json (default ~/.local/share/netcheat/state.json), or in the
file named by NETCHEAT_STATE. Entries are referenced by `entry_key`, so renaming a topic file keeps them.
The state is a convenience: an unreadable or unwritable file never stops the tool.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

MAX_RECENT = 30


def state_file() -> Path:
    if "NETCHEAT_STATE" in os.environ:
        return Path(os.environ["NETCHEAT_STATE"])
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return data_home / "netcheat" / "state.json"


@dataclass
class State:
    favourites: list[str] = field(default_factory=list)
    recent: list[str] = field(default_factory=list)  # newest first

    @classmethod
    def load(cls) -> State:
        try:
            raw = json.loads(state_file().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        return cls(_keys(raw, "favourites"), _keys(raw, "recent"))

    def save(self) -> None:
        path = state_file()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"favourites": self.favourites, "recent": self.recent}, indent=1), encoding="utf-8")
            temporary.replace(path)  # atomic: a crash never leaves a half-written file
        except OSError:
            pass

    def is_favourite(self, key: str) -> bool:
        return key in self.favourites

    def toggle_favourite(self, key: str) -> bool:
        """Star or unstar an entry; returns True if it is a favourite now."""
        if key in self.favourites:
            self.favourites.remove(key)
        else:
            self.favourites.append(key)
        self.save()
        return key in self.favourites

    def opened(self, key: str) -> None:
        """Remember an entry as recently opened."""
        self.recent = [key, *(k for k in self.recent if k != key)][:MAX_RECENT]
        self.save()


def _keys(raw: object, name: str) -> list[str]:
    """A list of entry keys from the loaded JSON; anything else (hand-edited, damaged) counts as empty."""
    value = raw.get(name) if isinstance(raw, dict) else None
    return [key for key in value if isinstance(key, str)] if isinstance(value, list) else []
