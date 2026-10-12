"""Domain objects of the cheatsheet: commands, troubleshooting flows and concepts."""

from __future__ import annotations

import re
from dataclasses import dataclass
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


def _check_version(name: str, value: str) -> None:
    if value and not (isinstance(value, str) and _VERSION.match(value)):
        raise ValueError(f"{name} must be a quoted version string like \"9.4\", got {value!r}")


def _check_platform(value: str) -> None:
    if value not in PLATFORMS:
        raise ValueError(f"unknown platform {value!r}, expected one of {', '.join(PLATFORMS)}")


def _check_list(name: str, value: tuple[str, ...]) -> None:
    if not isinstance(value, tuple):
        raise ValueError(f"{name} must be a list, e.g. [{value}]")


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

    @property
    def commands(self) -> list[Command]:
        return [command for topic in self.topics for command in topic.commands]

    def topic(self, slug: str) -> Topic:
        return next(topic for topic in self.topics if topic.slug == slug)
