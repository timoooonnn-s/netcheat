"""Tab completion for bash and zsh.

Enable it with `eval "$(ncs completion zsh)"` (or bash) in the shell profile. On every <Tab> the shell
calls `ncs __complete <index> <words...>`, and `candidates` answers from the argparse definition
(options, choices) and the data (topics, flow ids, concept names, search words). The data is only
loaded when a candidate needs it, so completing options and choices skips reading the YAML files.
"""

from __future__ import annotations

import argparse
import re
from typing import Callable, Iterable

from netcheat.models import PLATFORM_ALIASES, PLATFORMS, Library

HIDDEN_COMMAND = "__complete"

SCRIPTS = {
    "bash": """\
_ncs_complete() {
    local IFS=$'\\n'
    COMPREPLY=($(ncs __complete "$((COMP_CWORD - 1))" "${COMP_WORDS[@]:1}" 2>/dev/null))
}
complete -F _ncs_complete ncs
""",
    "zsh": """\
_ncs_complete() {
    local -a candidates
    candidates=(${(f)"$(ncs __complete "$((CURRENT - 2))" "${(@)words[2,-1]}" 2>/dev/null)"})
    compadd -- "${candidates[@]}"
}
(( $+functions[compdef] )) || { autoload -Uz compinit && compinit }
compdef _ncs_complete ncs
""",
}

_TOKEN = re.compile(r"[a-z0-9][a-z0-9_.-]*[a-z0-9]")


Loader = Callable[[], Library]


def candidates(parser: argparse.ArgumentParser, load: Loader, args: list[str], index: int) -> list[str]:
    """Completions for the word at `index` of the arguments after `ncs`; `load` returns the data on demand."""
    current = args[index] if index < len(args) else ""
    before = args[:index]
    subparsers = _subparsers(parser)

    if before and before[0] in subparsers:
        command, before = before[0], before[1:]
    else:
        command = "search"
    sub = subparsers[command]

    if before and (values := _option_values(sub, before[-1], load)) is not None:
        options = values
    elif current.startswith("-"):
        options = [option for action in sub._actions for option in action.option_strings]
    else:
        options = _positionals(command, load, current) or [
            str(choice) for action in sub._actions if not action.option_strings for choice in action.choices or ()
        ]
        if command == "search" and not before:
            options = [*subparsers, *options]
    return sorted({option for option in options if option.startswith(current)})


def _subparsers(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return {name: sub for name, sub in action.choices.items() if name != HIDDEN_COMMAND}


def _option_values(sub: argparse.ArgumentParser, option: str, load: Loader) -> list[str] | None:
    """Values for the option `option` if it takes one; None if it is no option or a flag."""
    action = next((a for a in sub._actions if option in a.option_strings), None)
    if action is None or action.nargs == 0:
        return None
    if action.choices:
        return [str(choice) for choice in action.choices]
    return VALUE_COMPLETERS.get(action.dest, lambda load: [])(load)


def _positionals(command: str, load: Loader, current: str) -> list[str]:
    if command == "export":
        return [flow.id for flow in load().flows]
    if not current:  # search, what and fix have hundreds of words: only complete once the first letter is typed
        return []
    if command == "search":  # an exact flow id or concept name opens it, so those are offered too
        library = load()
        names = (" ".join((concept.term, *concept.aka)) for concept in library.concepts)
        return [flow.id for flow in library.flows] + _tokens(" ".join((c.cmd, *c.tags)) for c in library.commands) + _tokens(names)
    if command == "what":
        return _tokens(c.cmd for c in load().commands)
    if command == "fix":  # free text: offer the vocabulary that `ncs fix` understands
        return _tokens(" ".join(group.words) for group in load().synonyms)
    return []


def _tokens(texts: Iterable[str]) -> list[str]:
    return [token for text in texts for token in _TOKEN.findall(text.lower())]


VALUE_COMPLETERS: dict[str, Callable[[Loader], list[str]]] = {
    "platform": lambda load: [*PLATFORM_ALIASES, *PLATFORMS],
    "topic": lambda load: [topic.slug for topic in load().topics],
}
