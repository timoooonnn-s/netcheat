"""Domain objects of the cheatsheet: commands, troubleshooting flows and concepts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

PLATFORMS = {
    "fabric-engine": "Extreme Fabric Engine",
    "junos-srx": "Juniper SRX",
}
PLATFORM_ALIASES = {"fe": "fabric-engine", "voss": "fabric-engine", "srx": "junos-srx", "junos": "junos-srx"}
KINDS = ("show", "config", "action", "clear")

_VERSION = re.compile(r"^\d+(\.\d+)*$")


def version_key(version: str) -> tuple[int, ...]:
    """Turn '9.4.1' into (9, 4, 1) so versions compare numerically."""
    return tuple(int(part) for part in version.split("."))


def is_version(value: object) -> bool:
    return isinstance(value, str) and bool(_VERSION.match(value))


def _check_version(name: str, value: str) -> None:
    if value and not is_version(value):
        raise ValueError(f"{name} must be a quoted version string like \"9.4\", got {value!r}")


def _check_platform(value: str) -> None:
    if value not in PLATFORMS:
        raise ValueError(f"unknown platform {value!r}, expected one of {', '.join(PLATFORMS)}")


def _check_list(name: str, value: tuple[str, ...]) -> None:
    if not isinstance(value, tuple):
        raise ValueError(f"{name} must be a list, e.g. [{value}]")
    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"every {name} entry must be text; quote words YAML treats specially (null, yes, no, on, off)")


@dataclass(frozen=True)
class Command:
    cmd: str
    desc: str
    kind: str
    mode: str
    platform: str
    topic: str
    tags: tuple[str, ...] = ()
    example: str = ""
    notes: str = ""
    caution: str = ""
    cisco: str = ""
    since: str = ""
    removed: str = ""
    rare: bool = False
    ref: str = ""

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)}, got {self.kind!r}")
        _check_platform(self.platform)
        _check_list("tags", self.tags)
        _check_version("since", self.since)
        _check_version("removed", self.removed)


@dataclass(frozen=True)
class Step:
    title: str
    cmds: tuple[str, ...] = ()
    look_for: str = ""

    def __post_init__(self) -> None:
        _check_list("cmds", self.cmds)


@dataclass(frozen=True)
class Flow:
    id: str
    title: str
    platform: str
    summary: str
    steps: tuple[Step, ...]
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_platform(self.platform)
        _check_list("tags", self.tags)


@dataclass(frozen=True)
class Concept:
    term: str
    text: str
    platform: str
    aka: tuple[str, ...] = ()
    see: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_platform(self.platform)
        _check_list("aka", self.aka)
        _check_list("see", self.see)


@dataclass(frozen=True)
class Topic:
    slug: str
    title: str
    platform: str
    description: str
    path: Path
    commands: tuple[Command, ...]


@dataclass(frozen=True)
class Library:
    topics: tuple[Topic, ...]
    flows: tuple[Flow, ...]
    concepts: tuple[Concept, ...]

    @cached_property
    def commands(self) -> tuple[Command, ...]:
        return tuple(command for topic in self.topics for command in topic.commands)

    def topics_by_platform(self) -> list[tuple[str, list[Topic]]]:
        """(platform display name, topics) in PLATFORMS order, skipping platforms without topics."""
        grouped = [(name, [topic for topic in self.topics if topic.platform == key]) for key, name in PLATFORMS.items()]
        return [(name, topics) for name, topics in grouped if topics]
