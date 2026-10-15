"""Command line entry point: `ncs`."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Callable, Sequence

from rich.console import Console
from rich.text import Text

from netcheat import CREDIT, __version__
from netcheat.add import run_add
from netcheat.completion import HIDDEN_COMMAND, SCRIPTS, candidates
from netcheat.loader import DataError, load_library
from netcheat.markdown import build_markdown
from netcheat.models import KINDS, PLATFORM_ALIASES, PLATFORMS, Concept, Flow, Library, is_version
from netcheat.render import (
    command_block,
    concept_block,
    flow_block,
    make_console,
    print_concept_list,
    print_diagnosis,
    print_flow_list,
    print_search,
    print_topics,
)
from netcheat.search import Filters, diagnose, search_commands, search_concepts, search_flows, suggest

EXAMPLES = """\
examples:
  ncs isid                     search everything for "isid" (matches i-sid too)
  ncs show isis adj            several words: all must match
  ncs -t macsec                every command of a topic (see: ncs topics)
  ncs lacp -k config           only configuration commands
  ncs -r -p fe                 rarely used gems on Fabric Engine
  ncs -s 9.3                   commands added in Fabric Engine 9.3 or later
  ncs route -p srx -d          Juniper SRX routing commands with examples and notes
  ncs browse                   browse topics, gems, flows and concepts full-screen
  ncs fix clients get no ip    describe a problem, get a matching flow and commands
  ncs flow no-connectivity     step-by-step troubleshooting flow
  ncs concept nickname         short explanation of a concept
  ncs tip                      a random command you might have forgotten
"""

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


def cmd_search(args: argparse.Namespace, library: Library, console: Console) -> int:
    filters = Filters(args.platform, args.topic, args.kind, args.rare, args.since)
    results = search_commands(library.commands, args.terms, filters)
    shown = results if args.limit is None else results[: args.limit]

    def on_platform(item: Flow | Concept) -> bool:
        return args.platform in (None, item.platform)

    print_search(
        console,
        shown,
        search_flows(filter(on_platform, library.flows), args.terms)[:5],
        search_concepts(filter(on_platform, library.concepts), args.terms)[:5],
        detail=args.detail or len(shown) <= 2,
        total=len(results),
        suggestions=suggest(library.commands, args.terms) if not results else [],
    )
    return 0 if results else 1


def cmd_flow(args: argparse.Namespace, library: Library, console: Console) -> int:
    if not args.terms:
        print_flow_list(console, library.flows)
        return 0
    exact = [flow for flow in library.flows if flow.id == " ".join(args.terms)]
    matches = exact or search_flows(library.flows, args.terms)
    if len(matches) == 1:
        console.print(flow_block(matches[0]))
    elif matches:
        print_flow_list(console, matches)
    else:
        console.print("No matching flow. List all with: ncs flow", style="meta")
    return 0 if matches else 1


def cmd_concept(args: argparse.Namespace, library: Library, console: Console) -> int:
    if not args.terms:
        print_concept_list(console, library.concepts)
        return 0
    matches = search_concepts(library.concepts, args.terms)
    for concept in matches:
        console.print(concept_block(concept))
        console.print()
    if not matches:
        console.print("No matching concept. List all with: ncs concept", style="meta")
    return 0 if matches else 1


def cmd_fix(args: argparse.Namespace, library: Library, console: Console) -> int:
    diagnosis = diagnose(library, " ".join(args.problem), args.platform)
    if not (diagnosis.flows or diagnosis.commands):
        console.print("Nothing fits yet. Describe the symptom differently, or look around with: ncs browse", style="meta")
        return 1
    print_diagnosis(console, diagnosis)
    return 0


def cmd_browse(args: argparse.Namespace, library: Library, console: Console) -> int:
    from netcheat.browser import run_browser  # imported here: Textual is only needed for this command

    run_browser(library, args.terms)
    return 0


def cmd_topics(args: argparse.Namespace, library: Library, console: Console) -> int:
    print_topics(console, library)
    return 0


def cmd_tip(args: argparse.Namespace, library: Library, console: Console) -> int:
    gems = search_commands(library.commands, [], Filters(platform=args.platform, rare=True))
    if not gems:
        console.print("No commands marked as rare.", style="meta")
        return 1
    console.print(Text("Command you might have forgotten:", style="label"))
    console.print(command_block(random.choice(gems), detail=True))
    return 0


def cmd_add(args: argparse.Namespace, library: Library, console: Console) -> int:
    try:
        topic = run_add(console, library)
    except DataError as err:
        console.print(Text(f"Not saved: {err}", style="removed"))
        return 2
    console.print(Text(f"Saved to {topic.path} ({len(topic.commands)} commands). Regenerate docs: ncs build-md", style="new"))
    return 0


def cmd_completion(args: argparse.Namespace, library: Library, console: Console) -> int:
    print(SCRIPTS[args.shell], end="")
    return 0


def cmd_build_md(args: argparse.Namespace, library: Library, console: Console) -> int:
    written = build_markdown(library, args.out)
    console.print(Text(f"Wrote {len(written)} Markdown files to {args.out}", style="new"))
    return 0


HANDLERS: dict[str, Handler] = {
    "search": cmd_search,
    "browse": cmd_browse,
    "flow": cmd_flow,
    "concept": cmd_concept,
    "fix": cmd_fix,
    "topics": cmd_topics,
    "tip": cmd_tip,
    "add": cmd_add,
    "build-md": cmd_build_md,
    "completion": cmd_completion,
}


def _with_default_command(argv: list[str]) -> list[str]:
    """`ncs isid` means `ncs search isid`; no arguments shows the topic overview."""
    if not argv:
        return ["topics"]
    if argv[0] in HANDLERS or argv[0] in ("-h", "--help", "--version"):
        return argv
    return ["search", *argv]


def _platform(value: str) -> str:
    platform = PLATFORM_ALIASES.get(value, value)
    if platform not in PLATFORMS:
        raise argparse.ArgumentTypeError(f"use one of: {', '.join([*PLATFORMS, *PLATFORM_ALIASES])}")
    return platform


def _version(value: str) -> str:
    if not is_version(value):
        raise argparse.ArgumentTypeError(f"expected a version like 9.4 or 9.3.1, got {value!r}")
    return value


def _positive_int(value: str) -> int:
    if not value.isdigit() or int(value) < 1:
        raise argparse.ArgumentTypeError(f"expected a number of 1 or more, got {value!r}")
    return int(value)


def _default_docs_dir() -> Path:
    """docs/cheatsheet of the checkout this code runs from (editable install), else of the current directory."""
    checkout = Path(__file__).resolve().parents[2]  # src/netcheat/cli.py -> repository root
    return checkout / "docs" / "cheatsheet" if (checkout / "pyproject.toml").exists() else Path("docs/cheatsheet")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ncs",
        description="Network cheatsheet: search Extreme Fabric Engine and Juniper SRX commands.",
        epilog=f"{EXAMPLES}\n{CREDIT}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__} · {CREDIT}")
    sub = parser.add_subparsers(dest="command", metavar="{search,browse,fix,flow,concept,topics,tip,add,build-md,completion}")

    search = sub.add_parser("search", help="search commands (default, so the word can be left out)")
    search.add_argument("terms", nargs="*", help="words to search for; all must match")
    search.add_argument("-p", "--platform", type=_platform, help="fe | srx")
    search.add_argument("-t", "--topic", help="limit to a topic, e.g. spbm-isis (see: ncs topics)")
    search.add_argument("-k", "--kind", choices=KINDS, help="type of command")
    search.add_argument("-r", "--rare", action="store_true", help="only rarely used gems")
    search.add_argument("-s", "--since", type=_version, metavar="VERSION", help="only commands added in this version or later")
    search.add_argument("-d", "--detail", action="store_true", help="show examples, notes and references")
    search.add_argument("-n", "--limit", type=_positive_int, metavar="N", help="show at most N results")

    browse = sub.add_parser("browse", help="full-screen browser: topics, gems, flows and concepts with a live filter")
    browse.add_argument("terms", nargs="*", help="optional words to start the filter with")

    fix = sub.add_parser("fix", help="describe a problem in your own words, get a troubleshooting flow and commands")
    fix.add_argument("problem", nargs="+", help='e.g. clients get no ip address (quotes are optional)')
    fix.add_argument("-p", "--platform", type=_platform, help="fe | srx")

    for name, help_text in (("flow", "troubleshooting flows and change workflows"), ("concept", "concept explanations")):
        sub.add_parser(name, help=help_text).add_argument("terms", nargs="*", help="id or words; empty lists all")

    sub.add_parser("topics", help="list topics with command counts")
    sub.add_parser("tip", help="show a random rarely used command").add_argument("-p", "--platform", type=_platform)
    sub.add_parser("add", help="add a command interactively")
    build = sub.add_parser("build-md", help="regenerate the Markdown cheatsheet")
    build.add_argument("-o", "--out", type=Path, default=_default_docs_dir(), help="default: docs/cheatsheet of this checkout")
    completion = sub.add_parser("completion", help="print the tab-completion script, e.g. eval \"$(ncs completion zsh)\"")
    completion.add_argument("shell", choices=sorted(SCRIPTS))
    return parser
