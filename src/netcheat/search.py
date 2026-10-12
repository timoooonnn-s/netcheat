"""Ranked keyword search over commands, flows and concepts.

Matching is forgiving on purpose: case, hyphens and punctuation are ignored ("isid" finds "i-sid",
a pasted "[verbose]" finds "verbose"), and every query word is a prefix ("adj" finds "adjacencies").
All query words must match.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Iterable, Sequence, TypeVar

from netcheat.models import Command, Concept, Flow, version_key

T = TypeVar("T")

_WORD = re.compile(r"[a-z0-9][a-z0-9_./-]*")
_SEPARATORS = re.compile(r"[_./-]")


def normalize(text: str) -> str:
    return _SEPARATORS.sub("", text.lower())


@lru_cache(maxsize=None)
def words(text: str) -> frozenset[str]:
    """All searchable words of a text: every run of consecutive parts of a compound,
    so 'ip-unicast-fib' yields ip, unicast, fib, ipunicast, unicastfib and ipunicastfib.
    Cached, because the same data texts are tokenized on every search."""
    result: set[str] = set()
    for word in _WORD.findall(text.lower()):
        parts = [part for part in _SEPARATORS.split(word) if part]
        result.update("".join(parts[start:end]) for start in range(len(parts)) for end in range(start + 1, len(parts) + 1))
    return frozenset(result)


def needles(terms: Sequence[str]) -> list[str]:
    """Query terms as normalized words, so punctuation in a term ('[verbose]', '<isid>') is ignored."""
    return [normalize(word) for term in terms for word in _WORD.findall(term.lower())]


@dataclass(frozen=True)
class Filters:
    platform: str | None = None
    topic: str | None = None
    kind: str | None = None
    rare: bool = False
    since: str | None = None

    def accept(self, command: Command) -> bool:
        return (
            (self.platform is None or command.platform == self.platform)
            and (self.topic is None or normalize(self.topic) in normalize(command.topic))
            and (self.kind is None or command.kind == self.kind)
            and (not self.rare or command.rare)
            and (self.since is None or (bool(command.since) and version_key(command.since) >= version_key(self.since)))
        )


def search_commands(commands: Iterable[Command], terms: Sequence[str], filters: Filters = Filters()) -> list[Command]:
    candidates = [command for command in commands if filters.accept(command)]
    if not terms:
        return candidates
    phrase = normalize(" ".join(terms))
    return _ranked(
        candidates,
        terms,
        _command_fields,
        bonus=lambda command: 10 * (phrase in normalize(command.cmd)),
        tiebreak=lambda command: (command.kind != "show", len(command.cmd)),
    )


def search_flows(flows: Iterable[Flow], terms: Sequence[str]) -> list[Flow]:
    return _ranked(flows, terms, lambda flow: [(flow.id, 3), (flow.title, 3), (" ".join(flow.tags), 2), (flow.summary, 1)])


def search_concepts(concepts: Iterable[Concept], terms: Sequence[str]) -> list[Concept]:
    return _ranked(concepts, terms, lambda concept: [(concept.term, 3), (" ".join(concept.aka), 3), (concept.text, 1)])


def suggest(commands: Iterable[Command], terms: Sequence[str]) -> list[str]:
    """Close spellings of terms that matched nothing, for a 'did you mean' hint."""
    vocabulary = sorted(set().union(*(words(text) for c in commands for text, _ in _command_fields(c))))
    return [match for needle in needles(terms) for match in difflib.get_close_matches(needle, vocabulary, n=2, cutoff=0.75)]


def _command_fields(command: Command) -> list[tuple[str, int]]:
    return [
        (command.cmd, 5),
        (" ".join(command.tags), 3),
        (command.desc, 2),
        (command.topic, 1),
        (" ".join((command.notes, command.example, command.cisco)), 1),
    ]


def _score(weighted_fields: list[tuple[str, int]], query: Sequence[str]) -> int:
    """Sum of the best field weight per query word; 0 if any word matches nowhere."""
    field_words = [(words(text), weight) for text, weight in weighted_fields]
    total = 0
    for needle in query:
        best = max((weight for found, weight in field_words if any(w.startswith(needle) for w in found)), default=0)
        if not best:
            return 0
        total += best
    return total


def _ranked(
    items: Iterable[T],
    terms: Sequence[str],
    weighted_fields: Callable[[T], list[tuple[str, int]]],
    bonus: Callable[[T], int] = lambda item: 0,
    tiebreak: Callable[[T], tuple] = lambda item: (),
) -> list[T]:
    """Matching items, best score first; ties are ordered by `tiebreak`, then by data file order."""
    query = needles(terms)
    if not query:
        return []
    scored = []
    for position, item in enumerate(items):
        score = _score(weighted_fields(item), query)
        if score:
            scored.append(((-(score + bonus(item)), tiebreak(item), position), item))
    return [item for _, item in sorted(scored, key=lambda entry: entry[0])]
