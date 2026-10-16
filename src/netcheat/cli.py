"""Command line entry point: `ncs`."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence

from rich.console import Console
from rich.text import Text

from netcheat import CREDIT, __version__
from netcheat.completion import HIDDEN_COMMAND, SCRIPTS, candidates
from netcheat.loader import DataError, load_library
from netcheat.models import KINDS, PLATFORM_ALIASES, PLATFORMS, Concept, Entry, Flow, Library, entry_key
from netcheat.render import (
    command_block,
    concept_block,
    flow_block,
    make_console,
    print_concept_list,
    print_diagnosis,
    print_entry_list,
    print_explanation,
    print_flow_list,
    print_search,
    print_topics,
    print_undo,
)
from netcheat.search import Filters, diagnose, normalize, search_commands, search_concepts, search_flows, suggest
from netcheat.state import State

EXAMPLES = """\
examples:
  ncs                              open the browser (topics, gems, flows, favourites, recent)
  ncs isid                         search everything for "isid" (matches i-sid too)
  ncs show isis adj -d             several words, all must match; -d adds examples and notes
  ncs -t macsec -k config          configuration commands of one topic (see: ncs list)
  ncs radius-replace               open a flow by its id, a concept by its name (ncs nickname)
  ncs radius-replace --set new_radius=10.1.1.5   ... with your own values
  ncs fix clients get no ip        describe a problem, get the matching flow and commands
  ncs what sh isis adj             explain a command or config line (abbreviations work)
  ncs undo < config.txt            the commands that remove pasted configuration
  ncs export radius-replace --md   a flow as a change plan with rollback, for a ticket
  ncs list flows                   list topics, flows, concepts, favourites or recent
"""
LIST_SECTIONS = ("topics", "flows", "concepts", "favourites", "recent")

Handler = Callable[[argparse.Namespace, Library, Console], int]


def main(argv: Sequence[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = _parser()
    if argv[:1] == [HIDDEN_COMMAND]:
        return _complete(parser, argv[1:])
    args = parser.parse_args(_with_default_command(argv))
    console = make_console()
    try:
        library = load_library()
    except DataError as err:
        console.print(Text(f"Data error: {err}", style="removed"))
        return 2
    return HANDLERS[args.command](args, library, console)


def _complete(parser: argparse.ArgumentParser, argv: list[str]) -> int:
    """Called by the shell on <Tab>: `ncs __complete <index> <words...>`, prints one candidate per line."""
    try:
        index, words = int(argv[0]), argv[1:]
        print("\n".join(candidates(parser, load_library, words, index)))
    except (IndexError, ValueError, DataError):
        return 1
    return 0


# --- handlers -------------------------------------------------------------------------------------------------


def cmd_search(args: argparse.Namespace, library: Library, console: Console) -> int:
    phrase = " ".join(args.terms)
    flow = library.flow(phrase)
    if flow:
        return _show_flow(flow, args.set, console)
    if args.set:
        return _fail(console, "--set only applies when opening a flow, e.g. ncs radius-replace --set new_radius=10.1.1.5")
    concept = _exact_concept(library, phrase)
    if concept:
        console.print(concept_block(concept))
        console.print()
        _remember(concept)

    filters = Filters(args.platform, args.topic, args.kind, args.rare)
    results = search_commands(library.commands, args.terms, filters)
    shown = results if args.limit is None else results[: args.limit]

    def on_platform(item: Flow | Concept) -> bool:
        return args.platform in (None, item.platform)

    print_search(
        console,
        shown,
        search_flows(filter(on_platform, library.flows), args.terms)[:5],
        [c for c in search_concepts(filter(on_platform, library.concepts), args.terms)[:5] if c is not concept],
        detail=args.detail or len(shown) <= 2,
        total=len(results),
        suggestions=suggest(library.commands, args.terms) if not (results or concept) else [],
    )
    return 0 if results or concept else 1


def cmd_fix(args: argparse.Namespace, library: Library, console: Console) -> int:
    diagnosis = diagnose(library, " ".join(args.problem), args.platform)
    if not (diagnosis.flows or diagnosis.commands):
        console.print("Nothing fits yet. Describe the symptom differently, or look around with: ncs", style="meta")
        return 1
    print_diagnosis(console, diagnosis)
    return 0


def cmd_what(args: argparse.Namespace, library: Library, console: Console) -> int:
    from netcheat.config import explain, read_lines

    words, detail = _split_detail_flag(args.line)
    try:
        text = " ".join(words) if words else _read_input(None, console, "Paste the lines to explain")
    except OSError as err:
        return _fail(console, str(err))
    lines = read_lines(text)
    explanations = [explain(library, line) for line in lines]
    for explanation in explanations:
        print_explanation(console, explanation, detail=args.detail or detail or len(lines) == 1)
        console.print()
    if len(explanations) == 1 and explanations[0].commands:
        _remember(explanations[0].commands[0])
    return 0 if any(explanation.found for explanation in explanations) else 1


def cmd_undo(args: argparse.Namespace, library: Library, console: Console) -> int:
    from netcheat.config import read_lines, undo

    try:
        result = undo(library, read_lines(_read_input(args.file, console, "Paste the configuration to remove")))
    except OSError as err:
        return _fail(console, str(err))
    if args.plain:
        print("\n".join(result.commands))
    else:
        print_undo(console, result)
    return 0 if result.removals else 1


def cmd_export(args: argparse.Namespace, library: Library, console: Console) -> int:
    from netcheat.export import export_flow

    flow = library.flow(args.flow)
    if flow is None:
        similar = [found.id for found in search_flows(library.flows, [args.flow])[:5]]
        return _fail(console, f"No flow {args.flow!r}." + (f" Did you mean: {', '.join(similar)}" if similar else " List them with: ncs list flows"))
    if args.step is not None and not 1 <= args.step <= len(flow.steps):
        return _fail(console, f"{flow.id} has steps 1 to {len(flow.steps)}")
    if args.md and (args.commands or args.step is not None):
        return _fail(console, "--md gives a whole document; drop it, or drop --commands/--step to get one")
    try:
        filled = flow.with_values(_checked_values(flow, args.set))
    except ValueError as err:
        return _fail(console, str(err))
    _remember(flow)
    if args.commands or args.step is not None:
        print("\n".join(filled.commands(args.step)))
    else:
        print(export_flow(library, filled, "md" if args.md else "text"), end="")
    return 0


def cmd_list(args: argparse.Namespace, library: Library, console: Console) -> int:
    if args.section == "topics":
        print_topics(console, library)
    elif args.section == "flows":
        print_flow_list(console, library.flows)
    elif args.section == "concepts":
        print_concept_list(console, library.concepts)
    else:
        state = State.load()
        keys = state.favourites if args.section == "favourites" else state.recent
        entries = [entry for entry in map(library.find, keys) if entry is not None]
        hint = "Star entries with f in the browser (ncs)." if args.section == "favourites" else "Nothing opened yet."
        print_entry_list(console, args.section.capitalize(), entries, hint)
    return 0


def cmd_browse(args: argparse.Namespace, library: Library, console: Console) -> int:
    from netcheat.browser import run_browser  # imported here: Textual is only needed for this command

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return _fail(console, "The browser needs a terminal. Piped or redirected, use: ncs <words>, ncs list")
    run_browser(library, args.terms)
    return 0


def cmd_tip(args: argparse.Namespace, library: Library, console: Console) -> int:
    gems = search_commands(library.commands, [], Filters(platform=args.platform, rare=True))
    if not gems:
        console.print("No commands marked as rare.", style="meta")
        return 1
    console.print(Text("Command you might have forgotten:", style="label"))
    console.print(command_block(random.choice(gems), detail=True))
    return 0


def cmd_build_md(args: argparse.Namespace, library: Library, console: Console) -> int:
    from netcheat.markdown import build_markdown

    out = args.out.resolve()  # resolved, so the message names the folder it actually wrote to
    written = build_markdown(library, out)
    console.print(Text(f"Wrote {len(written)} Markdown files to {out}", style="new"))
    return 0


def cmd_completion(args: argparse.Namespace, library: Library, console: Console) -> int:
    print(SCRIPTS[args.shell], end="")
    return 0


HANDLERS: dict[str, Handler] = {
    "search": cmd_search,
    "browse": cmd_browse,
    "fix": cmd_fix,
    "what": cmd_what,
    "undo": cmd_undo,
    "export": cmd_export,
    "list": cmd_list,
    "tip": cmd_tip,
    "build-md": cmd_build_md,
    "completion": cmd_completion,
}


# --- helpers --------------------------------------------------------------------------------------------------


def _show_flow(flow: Flow, assignments: Optional[list[tuple[str, str]]], console: Console) -> int:
    try:
        console.print(flow_block(flow.with_values(_checked_values(flow, assignments))))
    except ValueError as err:
        return _fail(console, str(err))
    _remember(flow)
    return 0


def _checked_values(flow: Flow, assignments: Optional[list[tuple[str, str]]]) -> dict[str, str]:
    values = dict(assignments or [])
    unknown = sorted(set(values) - set(flow.values))
    if unknown:
        known = ", ".join(flow.values) or "none"
        raise ValueError(f"{flow.id} has no value {', '.join(unknown)}. Its values: {known}")
    return values


def _exact_concept(library: Library, phrase: str) -> Optional[Concept]:
    wanted = normalize(phrase)
    if not wanted:
        return None
    return next((c for c in library.concepts if wanted in {normalize(name) for name in (c.term, *c.aka)}), None)


def _remember(entry: Entry) -> None:
    State.load().opened(entry_key(entry))


def _split_detail_flag(words: list[str]) -> tuple[list[str], bool]:
    """`ncs what <line>` takes the line as REMAINDER, so an unquoted `|` or `[...]` survives; argparse then
    never sees a trailing `-d`. Pull it out by hand instead of letting it end up inside the line."""
    flags = {"-d", "--detail"}
    return [word for word in words if word not in flags], any(word in flags for word in words)


def _read_input(path: Optional[str], console: Console, prompt: str) -> str:
    """The text of a file, or of stdin ('-' or no file). On a terminal, asks for a paste first."""
    if path and path != "-":
        return Path(path).read_text(encoding="utf-8")
    if sys.stdin.isatty():
        console.print(Text(f"{prompt}, then press Ctrl-D on an empty line:", style="meta"))
    return sys.stdin.read()


def _fail(console: Console, message: str) -> int:
    console.print(Text(message, style="removed"))
    return 2


def _with_default_command(argv: list[str]) -> list[str]:
    """`ncs isid` means `ncs search isid`. No arguments opens the browser (the overview when not on a terminal)."""
    if not argv:
        return ["browse"] if sys.stdin.isatty() and sys.stdout.isatty() else ["list"]
    if argv[0] in HANDLERS or argv[0] in ("-h", "--help", "--version"):
        return argv
    return ["search", *argv]


def _platform(value: str) -> str:
    platform = PLATFORM_ALIASES.get(value, value)
    if platform not in PLATFORMS:
        raise argparse.ArgumentTypeError(f"use one of: {', '.join([*PLATFORMS, *PLATFORM_ALIASES])}")
    return platform


def _positive_int(value: str) -> int:
    if not value.isdigit() or int(value) < 1:
        raise argparse.ArgumentTypeError(f"expected a number of 1 or more, got {value!r}")
    return int(value)


def _assignment(value: str) -> tuple[str, str]:
    name, sep, assigned = value.partition("=")
    if not (sep and name.strip() and assigned.strip()):
        raise argparse.ArgumentTypeError(f"expected name=value, e.g. port=1/7, got {value!r}")
    return name.strip(), assigned.strip()


def _default_docs_dir() -> Optional[Path]:
    """docs/cheatsheet of the checkout this code runs from, or None when it does not run from one
    (a plain `pip install`): then there is nothing to regenerate and `-o` has to say where to write."""
    checkout = Path(__file__).resolve().parents[2]  # src/netcheat/cli.py -> repository root
    return checkout / "docs" / "cheatsheet" if (checkout / "pyproject.toml").exists() else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ncs",
        description="Network cheatsheet: search Extreme Fabric Engine and Juniper SRX commands.",
        epilog=f"{EXAMPLES}\n{CREDIT}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__} · {CREDIT}")
    sub = parser.add_subparsers(dest="command", metavar="{" + ",".join(HANDLERS) + "}")

    values = argparse.ArgumentParser(add_help=False)
    values.add_argument("--set", type=_assignment, action="append", metavar="NAME=VALUE", help="your value for a {name} of a flow; repeatable")

    search = sub.add_parser("search", parents=[values], help="search commands; an exact flow id or concept opens it (default command)")
    search.add_argument("terms", nargs="*", help="words to search for; all must match")
    search.add_argument("-p", "--platform", type=_platform, help="fe | srx")
    search.add_argument("-t", "--topic", help="exactly one topic, e.g. spbm-isis (see: ncs list)")
    search.add_argument("-k", "--kind", choices=KINDS, help="type of command")
    search.add_argument("-r", "--rare", action="store_true", help="only the gems: commands you would not remember exist")
    search.add_argument("-d", "--detail", action="store_true", help="show examples, notes and references")
    search.add_argument("-n", "--limit", type=_positive_int, metavar="N", help="show at most N results")

    browse = sub.add_parser("browse", help="full-screen browser (also: ncs without arguments)")
    browse.add_argument("terms", nargs="*", help="optional words to start the filter with")

    fix = sub.add_parser("fix", help="describe a problem in your own words, get a flow and commands")
    fix.add_argument("problem", nargs="+", help="e.g. clients get no ip address (quotes are optional)")
    fix.add_argument("-p", "--platform", type=_platform, help="fe | srx")

    what = sub.add_parser("what", help="explain a command or config line; several lines from stdin")
    what.add_argument("-d", "--detail", action="store_true", help="full details also for several lines")
    what.add_argument("line", nargs=argparse.REMAINDER, help="the line, e.g. radius server host 10.0.0.5 used-by eapol")

    undo = sub.add_parser("undo", help="the commands that remove pasted configuration")
    undo.add_argument("file", nargs="?", help="a file with config lines; default: stdin (paste, then Ctrl-D)")
    undo.add_argument("--plain", action="store_true", help="only the removal commands, for piping")

    export = sub.add_parser("export", parents=[values], help="a flow as a document for a ticket (rollback included)")
    export.add_argument("flow", help="flow id, e.g. radius-replace (see: ncs list flows)")
    export.add_argument("--md", action="store_true", help="Markdown instead of plain text")
    export.add_argument("--step", type=_positive_int, metavar="N", help="only the commands of step N")
    export.add_argument("--commands", action="store_true", help="only the commands, one per line")

    listing = sub.add_parser("list", help="list topics, flows, concepts, favourites or recent entries")
    listing.add_argument("section", nargs="?", choices=LIST_SECTIONS, default="topics")

    sub.add_parser("tip", help="show a random gem").add_argument("-p", "--platform", type=_platform)
    docs_dir = _default_docs_dir()
    build = sub.add_parser("build-md", help="regenerate the Markdown cheatsheet")
    build.add_argument(
        "-o", "--out", type=Path, default=docs_dir, required=docs_dir is None,
        help="default: docs/cheatsheet of this checkout" if docs_dir else "the folder to write to (required: not run from a checkout)",
    )
    completion = sub.add_parser("completion", help="print the tab-completion script, e.g. eval \"$(ncs completion zsh)\"")
    completion.add_argument("shell", choices=sorted(SCRIPTS))
    return parser
