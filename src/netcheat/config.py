"""Read pasted configuration and commands: `ncs undo` (removal commands) and `ncs what` (explain a line).

Both work on lines as you copy them from a switch: prompts ("SW1:1(config)#"), comment and section lines
("# RADIUS CONFIGURATION"), `config terminal`/`exit`/`end`, pager output and blank lines are skipped. Lines
inside an `interface ...` or `router ...` block keep that block as their context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Optional, Sequence

from netcheat.models import Command, Flow, Library, UndoRule
from netcheat.search import search_commands
from netcheat.syntax import Match, compile_patterns, fill, match, tokens, try_compile

_PROMPT = re.compile(r"^\S+?:\d+(\([^)]*\))?[#>]\s*")
_SKIP = re.compile(r"^(#|!|--more--|preparing to display|config(ure)? terminal$|end$|enable$|exit$)", re.IGNORECASE)
_BLOCK = re.compile(r"^(interface|router|route-map|i-sid|mgmt|logical-intf)\s", re.IGNORECASE)
_KEYWORD = re.compile(r"^[a-z][a-z0-9-]*$", re.IGNORECASE)
_NEGATION = re.compile(r"^(no|default)\s+(.*)$", re.IGNORECASE)
_REMOVING = re.compile(r"^(show|no|default)\s", re.IGNORECASE)
_FILTER_ENTRY = re.compile(r"^<[^<>]+> \| (.+)$")  # "<show command> | include <pattern>": a filter for any command
MAX_RELATED = 3


@dataclass(frozen=True)
class ConfigLine:
    text: str
    context: str = ""  # e.g. "interface gigabitEthernet 1/5" for lines inside that block


def read_lines(text: str) -> list[ConfigLine]:
    """The meaningful lines of pasted config or commands. A block line ("interface gigabitEthernet 1/5")
    is kept as a line of its own and becomes the context of the lines after it, up to `exit`."""
    lines: list[ConfigLine] = []
    context = ""
    for raw in text.splitlines():
        line = _PROMPT.sub("", raw.strip()).strip()
        if line.lower() == "exit":
            context = ""
        if not line or _SKIP.match(line):
            continue
        lines.append(ConfigLine(line, context))
        if _BLOCK.match(line):
            context = line
    return lines


# --- ncs undo -------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Removal:
    line: str
    command: Command
    remove: str  # empty for a manual step
    note: str


@dataclass(frozen=True)
class UndoResult:
    removals: list[Removal]  # in the order to run them
    unhandled: list[ConfigLine]

    @property
    def commands(self) -> list[str]:
        """The removals that are safe to paste as a block, in order."""
        return [removal.remove for removal in self.removals if removal.remove and not removal.note]

    @property
    def flagged(self) -> list[Removal]:
        """Removals to check before running (they carry a note), and manual steps (no command)."""
        return [removal for removal in self.removals if removal.note or not removal.remove]


def undo(library: Library, lines: Sequence[ConfigLine]) -> UndoResult:
    """The commands that remove the given configuration lines.

    Removals run in reverse order of the configuration, because `show running-config` lists what a line
    depends on before the line itself. Duplicates (several lines of one syslog host, ...) are removed once.
    Only global configuration is handled; lines inside an interface or router block are reported as unhandled.
    """
    removals: list[Removal] = []
    unhandled: list[ConfigLine] = []
    seen: set[str] = set()
    for line in reversed(lines):
        if line.text.lower().startswith("show "):
            continue  # a pasted show command, not configuration
        found = None if line.context else _best_undo(library.commands, line.text)
        if found is None:
            unhandled.append(line)
            continue
        command, rule, matched = found
        remove = fill(rule.remove, matched.values) if rule.remove else ""
        if remove and remove in seen:
            continue
        seen.add(remove)
        removals.append(Removal(line.text, command, remove, rule.note))
    return UndoResult(removals, list(reversed(unhandled)))


def rollback(library: Library, flow: Flow) -> UndoResult:
    """The removals for what a change workflow adds, as far as undo rules know them."""
    added = [cmd for cmd in flow.commands() if not _REMOVING.match(cmd)]
    return undo(library, [ConfigLine(cmd) for cmd in added])


def removal_for(library: Library, line: str) -> Optional[str]:
    """The removal command for a single configuration line, if a rule knows it."""
    found = _best_undo(library.commands, line)
    return fill(found[1].remove, found[2].values) if found and found[1].remove else None


def _best_undo(commands: Iterable[Command], line: str) -> Optional[tuple[Command, UndoRule, Match]]:
    best: Optional[tuple[Command, UndoRule, Match]] = None
    for command in commands:
        for rule in command.undo:
            found = match(compile_patterns(rule.match), line)
            if found and (best is None or found.rank > best[2].rank):
                best = (command, rule, found)
    return best


# --- ncs what -------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Explanation:
    line: ConfigLine
    commands: list[Command]  # the entries this line is an instance of, best first
    exact: bool  # False: only the beginning of the line matched (extra values, or a different variant)
    negation: str  # "no" or "default" if the line removes or resets something
    remove: Optional[str]  # how to remove the line, if it is configuration with an undo rule
    related: list[Command]  # search results when nothing matched
    filters: list[tuple[str, list[Command]]]  # each "| ..." part of the line, with the output filters it matches

    @property
    def found(self) -> bool:
        """True if anything of the line is explained: the command or one of its filters."""
        return bool(self.commands) or any(entries for _, entries in self.filters)


def explain(library: Library, line: ConfigLine) -> Explanation:
    """Which cheatsheet entries describe a command or configuration line. Output filters after the command
    ("show running-config | include radius") are explained one by one."""
    text, *pipes = _split_pipes(line.text)
    commands, exact = _entries_for(library.commands, text)
    negation = ""
    negated = _NEGATION.match(text)
    if not commands and negated:  # e.g. "no slpp enable" when only "slpp enable" is in the cheatsheet
        negation = negated.group(1).lower()
        commands, exact = _entries_for(library.commands, negated.group(2))
    remove = None if negated or line.context or pipes else removal_for(library, text)
    related = [] if commands else _related(library.commands, text)
    platforms = {command.platform for command in commands}
    filters = [(pipe, _filters_for(library.commands, pipe, platforms)) for pipe in pipes]
    return Explanation(line, commands, exact, negation, remove, related, filters)


def _split_pipes(text: str) -> list[str]:
    """The command and its output filters, split at every standalone `|`. A `|` inside a pattern
    ("radius|snmp", with or without quotes) is part of the pattern."""
    parts: list[list[str]] = [[]]
    for token in tokens(text):
        if token == "|":
            parts.append([])
        else:
            parts[-1].append(token)
    return [" ".join(part) for part in parts]


def _filters_for(commands: Sequence[Command], pipe: str, platforms: set[str]) -> list[Command]:
    """The output-filter entries ("<show command> | include <pattern> ...") that match one `| ...` part,
    from the platform of the command before the pipe when it is known."""
    ranked = []
    for command in commands:
        found = match(_filter_patterns(command), pipe, abbreviations=True)
        if found:
            ranked.append((found.rank, command))
    if any(command.platform in platforms for _, command in ranked):
        ranked = [(rank, command) for rank, command in ranked if command.platform in platforms]
    best = max((rank for rank, _ in ranked), default=None)
    return [command for rank, command in ranked if rank == best]


@lru_cache(maxsize=None)
def _filter_patterns(command: Command) -> tuple:
    """For an output-filter entry, the syntax after the pipe ("include <pattern> [field <n>] ..."); else nothing."""
    is_filter = _FILTER_ENTRY.match(command.cmd)
    return try_compile(is_filter.group(1)) if is_filter else ()


def _entries_for(commands: Sequence[Command], text: str) -> tuple[list[Command], bool]:
    """Entries whose syntax matches the whole text; else those matching its beginning (`partial`)."""
    for partial in (False, True):
        ranked = []
        for position, command in enumerate(commands):
            found = match(_patterns(command), text, partial=partial, abbreviations=True)
            if found and found.words >= 1 + partial:
                ranked.append((found.rank, -position, command))
        if ranked:
            ranked.sort(reverse=True)
            best = ranked[0][0]
            return [command for rank, _, command in ranked if rank == best], not partial
    return [], False


def _related(commands: Sequence[Command], text: str) -> list[Command]:
    """Search results for the keywords of a line (values such as IPs left out), dropping trailing keywords
    until something matches. A single keyword is only searched if commands start with it ("radius"), since
    one generic word ("something") finds anything."""
    keywords = [word for word in text.split() if _KEYWORD.match(word)]
    starts = {command.cmd.split()[0].lower() for command in commands}
    minimum = 1 if keywords and keywords[0].lower() in starts else 2
    while len(keywords) >= minimum:
        found = search_commands(commands, keywords)
        if found:
            return found[:MAX_RELATED]
        keywords.pop()
    return []


@lru_cache(maxsize=None)
def _patterns(command: Command) -> tuple:
    """The syntax of the entry itself, plus its undo patterns (written for `show running-config` lines)."""
    return try_compile(command.cmd) + tuple(p for rule in command.undo for p in compile_patterns(rule.match))
