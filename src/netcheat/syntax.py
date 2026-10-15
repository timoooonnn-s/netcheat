"""Command syntax patterns, and matching real command or config lines against them.

The notation is the one the data files use for `cmd`:

    radius server host <ip> key <secret> used-by {cli | eapol} [priority <1-10>] [timeout <1-180>]

    word        a keyword, matched case-insensitively
    <name>      one value (a quoted "value with spaces" counts as one)
    [ ... ]     optional; a run of optional parts may appear in any order, like on the switch
    { a | b }   one of the alternatives ([ a | b ] is an optional choice)
    ...         any number of values (used by `undo` rules)
    a / b       two related commands in one entry; each is a pattern of its own
    (note)      an annotation such as "(interface)", ignored

Placeholders in a match pattern are captured by name, so an undo template like
`no radius server host <ip>` can be filled from the line that matched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator, NamedTuple, Optional, Union

_SYMBOL = re.compile(r'"<[^<>]*>"|<[^<>]*>|\([^()]*\)|\.\.\.|[\[\]{}|]|[^\s\[\]{}|<>]+')
_TOKEN = re.compile(r'"[^"]*"|\S+')
_SLOT = re.compile(r"<([^<>]+)>")


class SyntaxParseError(ValueError):
    """The notation of a pattern is broken, e.g. an unclosed bracket."""


@dataclass(frozen=True)
class Word:
    text: str


@dataclass(frozen=True)
class Slot:
    name: str


@dataclass(frozen=True)
class Rest:
    """`...`: any number of tokens."""


@dataclass(frozen=True)
class Choice:
    alternatives: tuple[Seq, ...]
    optional: bool = False


@dataclass(frozen=True)
class AnyOrder:
    """Optional parts that may appear in any order, each at most once."""

    options: tuple[Seq, ...]


Node = Union[Word, Slot, Rest, Choice, AnyOrder]
Seq = "tuple[Node, ...]"


@dataclass(frozen=True)
class Match:
    """A successful match. The pattern with the most keywords wins; full keywords beat abbreviated ones."""

    values: dict[str, str]
    words: int
    abbreviated: int
    rests: int

    @property
    def rank(self) -> tuple[int, int, int]:
        return (self.words, -self.abbreviated, -self.rests)


def tokens(line: str) -> list[str]:
    """Split a line into tokens; a "quoted value" stays one token."""
    return _TOKEN.findall(line)


def slots(text: str) -> list[str]:
    """The placeholder names in a pattern or template, e.g. ['ip', 'app']."""
    return _SLOT.findall(text)


def fill(template: str, values: dict[str, str]) -> str:
    """Replace each <name> of a template with its value."""
    return _SLOT.sub(lambda m: values[m.group(1)], template)


@lru_cache(maxsize=None)
def compile_patterns(text: str) -> tuple[Seq, ...]:
    """The patterns of a syntax text, one per ` / ` alternative. Raises SyntaxParseError."""
    return tuple(_Parser(part).parse() for part in re.split(r"\s+/\s+", text.strip()))


def try_compile(text: str) -> tuple[Seq, ...]:
    """Like compile_patterns, but an unparsable text gives no patterns instead of an error."""
    try:
        return compile_patterns(text)
    except SyntaxParseError:
        return ()


def match(patterns: tuple[Seq, ...], line: str, *, partial: bool = False, abbreviations: bool = False) -> Optional[Match]:
    """The best match of a whole line against any of the patterns, or None.

    partial: also accept a line with extra tokens after a complete pattern.
    abbreviations: a keyword may be shortened to 2+ letters, as on the switch CLI ("sh isis adj").
    """
    words = tokens(line)
    best: Optional[Match] = None
    for pattern in patterns:
        for state in _match_seq(pattern, words, _State(0), abbreviations):
            if state.pos == len(words) or partial:
                found = Match(dict(state.values), state.words, state.abbreviated, state.rests)
                if best is None or found.rank > best.rank:
                    best = found
    return best


class _Parser:
    def __init__(self, text: str) -> None:
        self.symbols = [s for s in _SYMBOL.findall(text) if not s.startswith("(")]
        self.pos = 0
        self.text = text

    def parse(self) -> Seq:
        seq = self._seq(closing=())
        if self.pos != len(self.symbols):
            raise SyntaxParseError(f"unexpected {self.symbols[self.pos]!r} in {self.text!r}")
        if not seq:
            raise SyntaxParseError(f"empty pattern in {self.text!r}")
        return seq

    def _seq(self, closing: tuple[str, ...]) -> Seq:
        nodes: list[Node] = []
        while self.pos < len(self.symbols) and self.symbols[self.pos] not in closing:
            symbol = self.symbols[self.pos]
            self.pos += 1
            if symbol in ("[", "{"):
                nodes.append(self._choice(symbol))
            elif symbol in ("]", "}", "|"):
                raise SyntaxParseError(f"unexpected {symbol!r} in {self.text!r}")
            elif symbol == "...":
                nodes.append(Rest())
            elif "<" in symbol:
                nodes.append(Slot(symbol.strip('"<>').strip()))
            else:
                nodes.append(Word(symbol.lower()))
        return _group_optionals(nodes)

    def _choice(self, opening: str) -> Choice:
        closing = "]" if opening == "[" else "}"
        alternatives = [self._seq(closing=("|", closing))]
        while self.pos < len(self.symbols) and self.symbols[self.pos] == "|":
            self.pos += 1
            alternatives.append(self._seq(closing=("|", closing)))
        if self.pos == len(self.symbols):
            raise SyntaxParseError(f"missing {closing!r} in {self.text!r}")
        self.pos += 1
        return Choice(tuple(alternatives), optional=opening == "[")


def _group_optionals(nodes: list[Node]) -> Seq:
    """Turn every run of two or more optional parts into one AnyOrder node."""
    grouped: list[Node] = []
    run: list[Choice] = []
    for node in [*nodes, None]:
        if isinstance(node, Choice) and node.optional:
            run.append(node)
            continue
        if len(run) > 1:
            grouped.append(AnyOrder(tuple((option,) for option in run)))
        else:
            grouped.extend(run)
        run = []
        if node is not None:
            grouped.append(node)
    return tuple(grouped)


class _State(NamedTuple):
    """Where a match attempt stands: the next token, the captured values and how the keywords matched."""

    pos: int
    values: tuple[tuple[str, str], ...] = ()
    words: int = 0
    abbreviated: int = 0
    rests: int = 0


def _match_seq(seq: Seq, words: list[str], state: _State, abbreviations: bool) -> Iterator[_State]:
    if not seq:
        yield state
        return
    for after_head in _match_node(seq[0], words, state, abbreviations):
        yield from _match_seq(seq[1:], words, after_head, abbreviations)


def _match_node(node: Node, words: list[str], state: _State, abbreviations: bool) -> Iterator[_State]:
    pos = state.pos
    if isinstance(node, Word):
        token = words[pos].lower() if pos < len(words) else ""
        if token == node.text:
            yield state._replace(pos=pos + 1, words=state.words + 1)
        elif abbreviations and len(token) >= 2 and node.text.startswith(token):
            yield state._replace(pos=pos + 1, words=state.words + 1, abbreviated=state.abbreviated + 1)
    elif isinstance(node, Slot):
        if pos < len(words):
            yield state._replace(pos=pos + 1, values=(*state.values, (node.name, words[pos])))
    elif isinstance(node, Rest):
        for end in range(len(words), pos - 1, -1):
            yield state._replace(pos=end, rests=state.rests + 1)
    elif isinstance(node, Choice):
        if node.optional:
            yield state
        for alternative in node.alternatives:
            yield from _match_seq(alternative, words, state, abbreviations)
    else:
        yield from _match_any_order(node.options, words, state, abbreviations)


def _match_any_order(options: tuple[Seq, ...], words: list[str], state: _State, abbreviations: bool) -> Iterator[_State]:
    yield state
    for index, option in enumerate(options):
        remaining = options[:index] + options[index + 1:]
        for after in _match_seq(option, words, state, abbreviations):
            if after.pos > state.pos:  # an option that consumes nothing would loop forever
                yield from _match_any_order(remaining, words, after, abbreviations)
