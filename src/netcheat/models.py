"""Domain objects of the cheatsheet: commands, flows (troubleshooting and change workflows) and concepts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from functools import cached_property
from pathlib import Path
from typing import Mapping, Optional, Union

from netcheat.syntax import SyntaxParseError, compile_patterns, slots

PLATFORMS = {
    "fabric-engine": "Extreme Fabric Engine",
    "junos-srx": "Juniper SRX",
}
PLATFORM_ALIASES = {"fe": "fabric-engine", "voss": "fabric-engine", "srx": "junos-srx", "junos": "junos-srx"}
KINDS = ("show", "config", "action", "clear")

# How to reach each CLI mode from a fresh login: the commands to type before the entry's own command.
# "Wrong mode" is the usual reason a correct command is rejected, and the mode name alone does not say
# how to get there. The sub-mode commands are the ones this cheatsheet's own examples use.
MODE_PATHS: Mapping[str, tuple[str, ...]] = {
    "User EXEC": (),
    "Privileged EXEC": ("enable",),
    "Global Config": ("enable", "configure terminal"),
    "Interface Config": ("enable", "configure terminal", "interface gigabitEthernet <ports>"),
    "VLAN Interface Config": ("enable", "configure terminal", "interface vlan <vid>"),
    "MLT Interface Config": ("enable", "configure terminal", "interface mlt <mlt-id>"),
    "IS-IS Router Config": ("enable", "configure terminal", "router isis"),
    "VRF Router Config": ("enable", "configure terminal", "router vrf <vrf>"),
    "ELAN I-SID Config": ("enable", "configure terminal", "i-sid <isid> elan"),
    "MKA Keychain Config": ("enable", "configure terminal", "macsec mka keychain <name>"),
    "operational": (),  # Junos: where a login lands
    "configuration": ("configure",),
    "any": (),
}


def mode_path(mode: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(commands to get into the mode, the other modes the command also works in).

    A `mode` of "A / B" means either mode will do, so the path of the first one is shown and the rest are
    named. An unknown mode gives no path rather than a guessed one.
    """
    names = tuple(part.strip() for part in mode.split(" / "))
    for index, name in enumerate(names):
        if MODE_PATHS.get(name):
            return MODE_PATHS[name], names[:index] + names[index + 1:]
    return (), ()
FLOW_KINDS = {
    "troubleshoot": "Troubleshooting flows",
    "change": "Change workflows",
}

_VERSION = re.compile(r"^\d+(\.\d+)*$")
_VALUE = re.compile(r"\{([a-z][a-z0-9_]*)\}")


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
class UndoRule:
    """How to remove a configuration line: `match` is a pattern for the line as `show running-config` prints it,
    `remove` the command that removes it, filled from the placeholders of `match`. A rule without `remove` is a
    manual step: the `note` says what to do instead."""

    match: str
    remove: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        try:
            compile_patterns(self.match)
        except SyntaxParseError as err:
            raise ValueError(f"undo match: {err}") from err
        unknown = set(slots(self.remove)) - set(slots(self.match))
        if unknown:
            raise ValueError(f"undo remove uses <{'>, <'.join(sorted(unknown))}>, which match does not capture")
        if not (self.remove or self.note):
            raise ValueError("an undo rule needs `remove`, or a `note` that explains the manual step")


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
    since: str = ""
    rare: bool = False
    ref: str = ""
    undo: tuple[UndoRule, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)}, got {self.kind!r}")
        _check_platform(self.platform)
        _check_list("tags", self.tags)
        _check_version("since", self.since)


@dataclass(frozen=True)
class Step:
    title: str
    cmds: tuple[str, ...] = ()
    look_for: str = ""
    caution: str = ""

    def __post_init__(self) -> None:
        _check_list("cmds", self.cmds)


@dataclass(frozen=True)
class Flow:
    """A troubleshooting flow or a change workflow. Example values in the text are written as {name}, with
    their defaults in `values`, so they can be replaced with your own (`with_values`)."""

    id: str
    title: str
    platform: str
    summary: str
    steps: tuple[Step, ...]
    tags: tuple[str, ...] = ()
    symptoms: tuple[str, ...] = ()
    values: Mapping[str, str] = field(default_factory=dict, hash=False)
    kind: str = "troubleshoot"

    def __post_init__(self) -> None:
        if self.kind not in FLOW_KINDS:
            raise ValueError(f"flow kind must be one of {', '.join(FLOW_KINDS)}, got {self.kind!r}")
        _check_platform(self.platform)
        _check_list("tags", self.tags)
        _check_list("symptoms", self.symptoms)

    def check_values(self) -> None:
        """Every {name} needs a default in `values`, and every default must be used. Checked once, when loading."""
        used, defined = set(self.placeholders), set(self.values)
        if used - defined:
            raise ValueError(f"no default in `values` for {', '.join(sorted(used - defined))}")
        if defined - used:
            raise ValueError(f"`values` defines {', '.join(sorted(defined - used))}, which the flow does not use")

    def commands(self, step: Optional[int] = None) -> list[str]:
        """The commands of all steps, or of one step (1-based), in order."""
        steps = self.steps if step is None else (self.steps[step - 1],)
        return [cmd for one in steps for cmd in one.cmds]

    @property
    def placeholders(self) -> list[str]:
        """The {name} placeholders of the flow, in order of first use."""
        found = (name for text in self._texts() for name in _VALUE.findall(text))
        return list(dict.fromkeys(found))

    def with_values(self, overrides: Optional[Mapping[str, str]] = None) -> Flow:
        """The flow with every {name} replaced: by `overrides` where given, else by its default.
        Overrides for names this flow does not use are ignored."""
        values = {**self.values, **{name: value for name, value in (overrides or {}).items() if name in self.values}}

        def filled(text: str) -> str:
            return _VALUE.sub(lambda m: values[m.group(1)], text)

        steps = tuple(
            replace(step, title=filled(step.title), cmds=tuple(map(filled, step.cmds)),
                    look_for=filled(step.look_for), caution=filled(step.caution))
            for step in self.steps
        )
        return replace(self, title=filled(self.title), summary=filled(self.summary), steps=steps, values=values)

    def _texts(self) -> list[str]:
        texts = [self.title, self.summary]
        for step in self.steps:
            texts += [step.title, *step.cmds, step.look_for, step.caution]
        return texts


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
class SynonymGroup:
    """Words and phrases that mean the same thing in a problem description, e.g. ap / access point / wap."""

    words: tuple[str, ...]

    def __post_init__(self) -> None:
        _check_list("words", self.words)


@dataclass(frozen=True)
class Topic:
    slug: str
    title: str
    platform: str
    description: str
    path: Path
    commands: tuple[Command, ...]


Entry = Union[Command, Flow, Concept]


def entry_key(entry: Entry) -> str:
    """A stable id of a command, flow or concept, used for favourites and recents."""
    if isinstance(entry, Command):
        return f"command:{entry.platform}:{entry.mode}:{entry.cmd}"
    if isinstance(entry, Flow):
        return f"flow:{entry.id}"
    return f"concept:{entry.term}"


@dataclass(frozen=True)
class Library:
    topics: tuple[Topic, ...]
    flows: tuple[Flow, ...]
    concepts: tuple[Concept, ...]
    synonyms: tuple[SynonymGroup, ...] = ()

    @cached_property
    def commands(self) -> tuple[Command, ...]:
        return tuple(command for topic in self.topics for command in topic.commands)

    @cached_property
    def _by_key(self) -> dict[str, Entry]:
        return {entry_key(entry): entry for entry in (*self.commands, *self.flows, *self.concepts)}

    def find(self, key: str) -> Optional[Entry]:
        return self._by_key.get(key)

    @cached_property
    def _concepts_by_command(self) -> dict[str, tuple[str, ...]]:
        index: dict[str, list[str]] = {}
        for concept in self.concepts:
            for cmd in concept.see:
                index.setdefault(cmd, []).append(concept.term)
        return {cmd: tuple(terms) for cmd, terms in index.items()}

    def concepts_for(self, command: Command) -> tuple[str, ...]:
        """The concepts that name this command under `see`. The data only links concept -> command, so
        without this a command never says which background note explains it."""
        return self._concepts_by_command.get(command.cmd, ())

    def flow(self, flow_id: str) -> Optional[Flow]:
        return next((flow for flow in self.flows if flow.id == flow_id), None)

    def flows_of(self, kind: str) -> list[Flow]:
        return [flow for flow in self.flows if flow.kind == kind]

    def topics_by_platform(self) -> list[tuple[str, list[Topic]]]:
        """(platform display name, topics) in PLATFORMS order, skipping platforms without topics."""
        grouped = [(name, [topic for topic in self.topics if topic.platform == key]) for key, name in PLATFORMS.items()]
        return [(name, topics) for name, topics in grouped if topics]
