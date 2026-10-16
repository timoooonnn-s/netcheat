"""Ranked keyword search over commands, flows and concepts, and problem matching for `ncs fix`.

Search is forgiving on purpose: case, hyphens and punctuation are ignored ("isid" finds "i-sid",
a pasted "[verbose]" finds "verbose"), and every query word is a prefix ("adj" finds "adjacencies").
All query words must match.

Problem matching (`diagnose`) reads a free-text description instead. Known phrases are expanded with
their synonym group, filler words are dropped, and items are ranked by how much of the problem they cover.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Iterable, NamedTuple, Sequence, TypeVar

from netcheat.models import Command, Concept, Flow, Library, SynonymGroup

T = TypeVar("T")
WeightedFields = Callable[[T], "list[tuple[str, int]]"]

_WORD = re.compile(r"[a-z0-9][a-z0-9_./-]*")
_SEPARATORS = re.compile(r"[_./-]")

STOPWORDS = frozenset(
    "a an and are as at be been but by can cannot cant could do does doesnt dont for from get gets got had has have"
    " how i if in into is it its just me my no not of on only or our since so some still that the their them then"
    " there these they this to too very was we were what when where which while who why will with work works"
    " working would you although again also always anymore keep keeps maybe never randomly seem seems sometimes"
    " suddenly whole up come comes coming end ends one few every minute minutes hour hours day days anything"
    " something everything nothing".split()
)


MAX_FLOWS, MAX_COMMANDS, MAX_CONCEPTS = 4, 6, 3  # what `ncs fix` shows: the best flow plus 3 alternatives


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


class Score(NamedTuple):
    """Compares by coverage first (how many query groups matched), then by weight."""

    matched: int
    weight: int


@dataclass(frozen=True)
class Query:
    """Groups of alternative needles. A group matches if any of its needles matches a word.

    require_all: every group must match (search) or as many as possible (problem matching).
    prefix_min: needles at least this long also match as word prefixes; shorter ones only exactly.
    """

    groups: tuple[tuple[str, ...], ...]
    require_all: bool = True
    prefix_min: int = 1

    @classmethod
    def from_terms(cls, terms: Sequence[str]) -> Query:
        return cls(tuple((needle,) for needle in needles(terms)))

    def score(self, weighted_fields: list[tuple[str, int]]) -> Score:
        """How many groups match, and the sum of the best field weight per group.
        Score(0, 0) if nothing matches, or if a required group matches nowhere."""
        field_words = [(words(text), weight) for text, weight in weighted_fields]
        matched = total = 0
        for group in self.groups:
            best = max((weight for found, weight in field_words if any(self._hit(n, found) for n in group)), default=0)
            if not best and self.require_all:
                return Score(0, 0)
            matched += bool(best)
            total += best
        return Score(matched, total)

    def _hit(self, needle: str, found: frozenset[str]) -> bool:
        return needle in found or (len(needle) >= self.prefix_min and any(word.startswith(needle) for word in found))


@dataclass(frozen=True)
class Filters:
    platform: str | None = None
    topic: str | None = None
    kind: str | None = None
    rare: bool = False

    def accept(self, command: Command) -> bool:
        return (
            (self.platform is None or command.platform == self.platform)
            # The topic must match exactly: `-t system` is the Fabric Engine topic, never also srx-system.
            and (self.topic is None or normalize(self.topic) == normalize(command.topic))
            and (self.kind is None or command.kind == self.kind)
            and (not self.rare or command.rare)
        )


@dataclass(frozen=True)
class Diagnosis:
    understood: tuple[str, ...]
    flows: list[Flow]
    commands: list[Command]
    concepts: list[Concept]


def search_commands(commands: Iterable[Command], terms: Sequence[str], filters: Filters = Filters()) -> list[Command]:
    candidates = [command for command in commands if filters.accept(command)]
    if not terms:
        return candidates
    phrase = normalize(" ".join(terms))
    scored = _scored(
        candidates,
        Query.from_terms(terms),
        _command_fields,
        bonus=lambda command: 10 * (phrase in normalize(command.cmd)),
        tiebreak=_command_tiebreak,
    )
    return [command for _, command in scored]


def search_flows(flows: Iterable[Flow], terms: Sequence[str]) -> list[Flow]:
    return [flow for _, flow in _scored(flows, Query.from_terms(terms), _flow_fields)]


def search_concepts(concepts: Iterable[Concept], terms: Sequence[str]) -> list[Concept]:
    return [concept for _, concept in _scored(concepts, Query.from_terms(terms), _concept_fields)]


def suggest(commands: Iterable[Command], terms: Sequence[str]) -> list[str]:
    """Close spellings of terms that matched nothing, for a 'did you mean' hint."""
    vocabulary = sorted(set().union(*(words(text) for c in commands for text, _ in _command_fields(c))))
    return [match for needle in needles(terms) for match in difflib.get_close_matches(needle, vocabulary, n=2, cutoff=0.75)]


def diagnose(library: Library, problem: str, platform: str | None = None) -> Diagnosis:
    """Flows, commands and concepts that fit a free-text problem description, best first."""
    query, understood = problem_query(problem, library.synonyms)
    if not query.groups:
        return Diagnosis(understood, [], [], [])

    def on_platform(item: Command | Flow | Concept) -> bool:
        return platform in (None, item.platform)

    # A command or concept must cover two aspects of the problem, so one generic word ("user") is not enough.
    min_groups = min(2, len(query.groups))
    flows = _relevant(_scored(filter(on_platform, library.flows), query, _flow_fields), 1)
    commands = _scored(filter(on_platform, library.commands), query, _command_fields, tiebreak=_command_tiebreak)
    concepts = _scored(filter(on_platform, library.concepts), query, _concept_fields)
    return Diagnosis(
        understood,
        flows[:MAX_FLOWS],
        _relevant(commands, min_groups)[:MAX_COMMANDS],
        _relevant(concepts, min_groups)[:MAX_CONCEPTS],
    )


def problem_query(problem: str, synonyms: Sequence[SynonymGroup]) -> tuple[Query, tuple[str, ...]]:
    """Turn a problem description into a Query, plus the recognized key words (for display).

    A synonym group that is mentioned becomes one query group of its single-word entries; multi-word
    phrases ("up down", "no ip") only serve to recognize the group, so their generic words don't match
    everything. Remaining words count on their own, lightly stemmed ("joining" -> "join").
    """
    tokens = _WORD.findall(problem.lower())
    groups: list[tuple[str, ...]] = []
    understood: list[str] = []
    covered: set[str] = set()
    for group in synonyms:
        phrases = [" ".join(_WORD.findall(entry.lower())) for entry in group.words]
        hits = {phrase: _mentioned_by(tokens, phrase) for phrase in phrases}
        hits = {phrase: used for phrase, used in hits.items() if used}
        if hits:
            singles = [phrase for phrase in phrases if " " not in phrase]
            alternatives = tuple(dict.fromkeys(n for n in needles(singles or list(hits)) if n not in STOPWORDS))
            if alternatives:  # a group of only stopwords would never match but still count as an aspect
                groups.append(alternatives)
                understood.append(next(iter(hits)))
            covered.update(token for used in hits.values() for token in used)
    for token in tokens:
        if token not in covered and token not in STOPWORDS and len(normalize(token)) > 1:
            groups.append((_stem(normalize(token)),))
            understood.append(token)
    return Query(tuple(dict.fromkeys(groups)), require_all=False, prefix_min=4), tuple(dict.fromkeys(understood))


def _mentioned_by(tokens: Sequence[str], phrase: str) -> list[str]:
    """The tokens that mention a phrase: the whole phrase as consecutive words, or for a single word
    of 4+ letters also a token starting with it ('flap' in 'flapping'). Empty if not mentioned."""
    parts = phrase.split()
    for start in range(len(tokens) - len(parts) + 1):
        window = tokens[start:start + len(parts)]
        if window == parts or (len(parts) == 1 and len(phrase) >= 4 and window[0].startswith(phrase)):
            return window
    return []


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def _relevant(scored: list[tuple[Score, T]], min_groups: int) -> list[T]:
    """Drop weak matches: keep items covering at least `min_groups` query groups and nearly as many as the best."""
    if not scored:
        return []
    needed = max(min_groups, scored[0][0].matched - 1)
    return [item for score, item in scored if score.matched >= needed]


def _command_fields(command: Command) -> list[tuple[str, int]]:
    return [
        (command.cmd, 5),
        (" ".join(command.tags), 3),
        (command.desc, 2),
        (command.topic, 1),
        (" ".join((command.notes, command.example)), 1),
    ]


def _flow_fields(flow: Flow) -> list[tuple[str, int]]:
    return [(" ".join(flow.symptoms), 4), (flow.id, 3), (flow.title, 3), (" ".join(flow.tags), 2), (flow.summary, 1)]


def _concept_fields(concept: Concept) -> list[tuple[str, int]]:
    return [(concept.term, 3), (" ".join(concept.aka), 3), (concept.text, 1)]


def _command_tiebreak(command: Command) -> tuple:
    return (command.kind != "show", len(command.cmd))


def _scored(
    items: Iterable[T],
    query: Query,
    weighted_fields: WeightedFields,
    bonus: Callable[[T], int] = lambda item: 0,
    tiebreak: Callable[[T], tuple] = lambda item: (),
) -> list[tuple[Score, T]]:
    """(score, item) for matching items, best first; ties by `tiebreak`, then by data file order."""
    if not query.groups:
        return []
    ranked = []
    for position, item in enumerate(items):
        matched, weight = query.score(weighted_fields(item))
        if matched:
            score = Score(matched, weight + bonus(item))
            ranked.append(((-score.matched, -score.weight, tiebreak(item), position), score, item))
    ranked.sort(key=lambda entry: entry[0])
    return [(score, item) for _, score, item in ranked]
