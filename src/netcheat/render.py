"""Terminal output.

Icons are plain Unicode symbols (no emoji), so they render in every terminal font.
All data is wrapped in Text objects: command syntax such as [<1-4094>] must never
be parsed as rich markup.
"""

from __future__ import annotations

from typing import Sequence

from rich.console import Console, ConsoleOptions, Group, RenderableType, RenderResult
from rich.segment import Segment
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from netcheat.models import PLATFORMS, Command, Concept, Flow, Library

KIND_ICONS = {"show": "»", "config": "✎", "action": "►", "clear": "↺"}
RARE, CAUTION, CISCO, NEW, REMOVED, LINK, FLOW, CONCEPT = "◆", "▲", "≈", "↑", "✕", "↗", "☰", "◇"

THEME = Theme(
    {
        "cmd": "bold cyan",
        "meta": "dim",
        "label": "bold",
        "rare": "magenta",
        "caution": "yellow",
        "new": "green",
        "removed": "red",
        "kind.show": "green",
        "kind.config": "yellow",
        "kind.action": "blue",
        "kind.clear": "red",
    }
)

LEGEND = Text.assemble(
    *(part for kind, icon in KIND_ICONS.items() for part in ((icon, f"kind.{kind}"), (f" {kind}  ", "meta"))),
    (RARE, "rare"), (" gem  ", "meta"),
    (CAUTION, "caution"), (" caution  ", "meta"),
    (NEW, "new"), (" added in", "meta"),
)


class Indent:
    """Indent a renderable, wrapping lines inside the indent and without padding them to full width
    (rich's Padding does, which leaves trailing spaces in copied or piped output)."""

    def __init__(self, renderable: RenderableType, width: int = 2) -> None:
        self.renderable, self.width = renderable, width

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        inner = options.update_width(max(options.max_width - self.width, 20))
        for line in console.render_lines(self.renderable, inner, pad=False):
            yield Segment(" " * self.width)
            yield from line
            yield Segment.line()


def make_console() -> Console:
    return Console(theme=THEME, highlight=False)


def print_search(
    console: Console,
    commands: Sequence[Command],
    flows: Sequence[Flow],
    concepts: Sequence[Concept],
    *,
    detail: bool,
    total: int,
    suggestions: Sequence[str] = (),
) -> None:
    if commands:
        for command in commands:
            console.print(command_block(command, detail))
            console.print()
        count = f"{len(commands)} of {total}" if total > len(commands) else str(total)
        console.print(Text(f"{count} command(s)", style="meta"))
        console.print(LEGEND)
    else:
        console.print("No matching commands.", style="meta")
        if suggestions:
            console.print(Text.assemble(("Did you mean: ", "meta"), (", ".join(dict.fromkeys(suggestions)), "label")))
    if flows:
        _print_related(console, FLOW, "Flows", [flow.id for flow in flows], "ncs flow <id>")
    if concepts:
        _print_related(console, CONCEPT, "Concepts", [concept.term for concept in concepts], "ncs concept <term>")


def command_block(command: Command, detail: bool) -> RenderableType:
    head = Text.assemble((f"{KIND_ICONS[command.kind]} ", f"kind.{command.kind}"), (command.cmd, "cmd"))
    if command.rare:
        head.append(f"  {RARE}", "rare")
    if command.since:
        head.append(f"  {NEW} {command.since}", "new")
    if command.removed:
        head.append(f"  {REMOVED} removed in {command.removed}", "removed")
    if command.caution:
        head.append(f"  {CAUTION}", "caution")

    meta = Text(f"{command.topic} · {command.mode}", style="meta")
    if command.cisco:
        meta.append(f" · {CISCO} Cisco: {command.cisco}")
    body: list[RenderableType] = [Text(command.desc), meta]

    if detail:
        if command.example:
            body += [Text("Example", style="label"), Indent(Text(command.example))]
        if command.notes:
            body += [Text("Notes", style="label"), Indent(Text(command.notes))]
        if command.caution:
            body.append(Text(f"{CAUTION} {command.caution}", style="caution"))
        if command.ref:
            body.append(Text(f"{LINK} {command.ref}", style="meta"))
    return Group(head, Indent(Group(*body)))


def print_flow(console: Console, flow: Flow) -> None:
    console.print(Text.assemble((f"{FLOW} ", "label"), (flow.title, "cmd"), (f"  [{flow.platform}]", "meta")))
    console.print(Indent(Text(flow.summary)))
    for number, step in enumerate(flow.steps, 1):
        console.print()
        console.print(Text.assemble((f"{number:>2}  ", "label"), (step.title, "label")))
        lines: list[RenderableType] = [Text.assemble((f"{KIND_ICONS['show']} ", "kind.show"), (cmd, "cmd")) for cmd in step.cmds]
        if step.look_for:
            lines.append(Text.assemble(("Look for: ", "meta"), step.look_for))
        console.print(Indent(Group(*lines), 6))


def print_concept(console: Console, concept: Concept) -> None:
    head = Text.assemble((f"{CONCEPT} ", "label"), (concept.term, "cmd"))
    if concept.aka:
        head.append(f"  ({', '.join(concept.aka)})", "meta")
    body: list[RenderableType] = [Text(concept.text)]
    if concept.see:
        body.append(Text.assemble(("See: ", "meta"), (" · ".join(concept.see), "cmd")))
    console.print(head)
    console.print(Indent(Group(*body)))
    console.print()


def print_flow_list(console: Console, flows: Sequence[Flow]) -> None:
    table = _table("Flow id", "Title", "Steps")
    for flow in flows:
        table.add_row(Text(flow.id, style="cmd"), flow.title, str(len(flow.steps)))
    console.print(table)
    console.print(Text("Open one with: ncs flow <id>", style="meta"))


def print_concept_list(console: Console, concepts: Sequence[Concept]) -> None:
    table = _table("Term", "Platform", "Also known as")
    for concept in concepts:
        table.add_row(Text(concept.term, style="cmd"), concept.platform, ", ".join(concept.aka))
    console.print(table)
    console.print(Text("Open one with: ncs concept <term>", style="meta"))


def print_topics(console: Console, library: Library) -> None:
    table = _table("Topic", "Title", "Commands", f"{RARE} Gems")
    for platform, name in PLATFORMS.items():
        topics = [topic for topic in library.topics if topic.platform == platform]
        if not topics:
            continue
        table.add_section()
        table.add_row(Text(name, style="label"), "", "", "")
        for topic in topics:
            gems = sum(command.rare for command in topic.commands)
            table.add_row(Text(topic.slug, style="cmd"), topic.title, str(len(topic.commands)), str(gems))
    console.print(table)
    console.print(
        Text(f"{len(library.commands)} commands · {len(library.flows)} flows · {len(library.concepts)} concepts", style="meta")
    )
    console.print(Text("Search: ncs <words>   Topic: ncs -t <topic>   Help: ncs -h", style="meta"))


def _print_related(console: Console, icon: str, label: str, names: Sequence[str], hint: str) -> None:
    console.print(Text.assemble((f"{icon} {label}: ", "label"), (", ".join(names), "cmd"), (f"   ({hint})", "meta")))


def _table(*columns: str) -> Table:
    table = Table(box=None, header_style="label", pad_edge=False)
    for column in columns:
        table.add_column(column)
    return table
