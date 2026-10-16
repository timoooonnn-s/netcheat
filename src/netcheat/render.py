"""Terminal output, shared by the plain CLI and the browser.

Icons are plain Unicode symbols (no emoji), so they render in every terminal font.
All data is wrapped in Text objects: command syntax such as [<1-4094>] must never
be parsed as rich markup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, Optional, Sequence

from rich.console import Console, ConsoleOptions, Group, RenderableType, RenderResult
from rich.segment import Segment
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from netcheat import CREDIT
from netcheat.models import FLOW_KINDS, Command, Concept, Entry, Flow, Library, mode_path

if TYPE_CHECKING:  # only for annotations: config imports search, which this module must not load eagerly
    from netcheat.config import Explanation, UndoResult
    from netcheat.search import Diagnosis

KIND_ICONS = {"show": "»", "config": "✎", "action": "►", "clear": "↺"}
RARE, CAUTION, NEW, LINK, CONCEPT, FAVOURITE, RECENT = "◆", "▲", "↑", "↗", "◇", "★", "◷"
FLOW_ICONS = {"troubleshoot": "☰", "change": "⇄"}
ACTION_VERBS = ("clear", "reset", "save", "copy", "ping", "traceroute", "l2 ", "monitor", "tdr-test", "flight-recorder", "request", "isis apply")

THEME = Theme(
    {
        "cmd": "bold cyan",
        "meta": "dim",
        "label": "bold",
        "rare": "magenta",
        "caution": "yellow",
        "new": "green",
        "removed": "red",
        "favourite": "yellow",
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


def step_kind(cmd: str) -> str:
    """Icon kind of a command inside a flow step, guessed from its first word(s)."""
    if cmd.startswith("show "):
        return "show"
    return "action" if cmd.startswith(ACTION_VERBS) else "config"


# --- blocks: one entry each ----------------------------------------------------------------------------------


def command_title(command: Command) -> Text:
    """Kind icon, command and badges (gem, version added/removed, caution)."""
    title = Text.assemble((f"{KIND_ICONS[command.kind]} ", f"kind.{command.kind}"), (command.cmd, "cmd"))
    if command.rare:
        title.append(f"  {RARE}", "rare")
    if command.since:
        title.append(f"  {NEW} {command.since}", "new")
    if command.caution:
        title.append(f"  {CAUTION}", "caution")
    return title


def entry_title(entry: Entry) -> Text:
    """One line naming any entry: a command with its badges, a flow or a concept with its icon."""
    if isinstance(entry, Command):
        return command_title(entry)
    if isinstance(entry, Flow):
        return Text.assemble((f"{FLOW_ICONS[entry.kind]} ", "label"), entry.title, (f"  {entry.id}", "meta"))
    return Text.assemble((f"{CONCEPT} ", "label"), entry.term)


def command_block(command: Command, detail: bool, library: Optional[Library] = None) -> RenderableType:
    """One entry. With a `library`, the detail view also names the concepts that explain this command."""
    meta = Text(f"{command.topic} · {command.mode}", style="meta")
    body: list[RenderableType] = [Text(command.desc), meta]

    if detail:
        steps, also = mode_path(command.mode)
        if steps:
            path = Text.assemble(("Get there: ", "meta"), (" → ".join(steps), "cmd"))
            if also:
                path.append(f"   (also in {', '.join(also)})", "meta")
            body.append(path)
        if command.example:
            body += [Text("Example", style="label"), Indent(Text(command.example))]
        if command.notes:
            body += [Text("Notes", style="label"), Indent(Text(command.notes))]
        if command.caution:
            body.append(Text(f"{CAUTION} {command.caution}", style="caution"))
        background = library.concepts_for(command) if library else ()
        if background:
            body.append(Text.assemble((f"{CONCEPT} Background: ", "meta"), (" · ".join(background), "cmd")))
        if command.ref:
            body.append(Text(f"{LINK} {command.ref}", style="meta"))
    return Group(command_title(command), Indent(Group(*body)))


def flow_block(
    flow: Flow, values_hint: str = "--set name=value", entries: Optional[Mapping[str, Command]] = None
) -> RenderableType:
    """A flow with its values filled in (Flow.with_values). `values_hint` says how to change the values.
    `entries` maps a step command to its cheatsheet entry (config.entries_for), so the flow shows the
    warning that belongs to the command instead of relying on the flow author to repeat it."""
    parts: list[RenderableType] = [
        Text.assemble((f"{FLOW_ICONS[flow.kind]} ", "label"), (flow.title, "cmd"), (f"  {flow.id}", "meta")),
        Indent(Text(flow.summary)),
    ]
    if flow.values:
        values = Text("Values: ", style="meta")
        for index, (name, value) in enumerate(flow.values.items()):
            values.append(f"{' · ' if index else ''}{name}=", "meta").append(value, "label")
        parts.append(Indent(values.append(f"   (change: {values_hint})", "meta")))
    for number, step in enumerate(flow.steps, 1):
        lines: list[RenderableType] = []
        for cmd in step.cmds:
            kind = step_kind(cmd)
            entry = (entries or {}).get(cmd)
            title_line = Text.assemble((f"{KIND_ICONS[kind]} ", f"kind.{kind}"), (cmd, "cmd"))
            if entry is not None and entry.caution:
                title_line.append(f"  {CAUTION}", "caution")
            lines.append(title_line)
            if entry is not None and entry.caution and entry.caution != step.caution:
                lines.append(Indent(Text(f"{CAUTION} {entry.caution}", style="caution"), 2))
        if step.look_for:
            lines.append(Text.assemble(("Look for: ", "meta"), step.look_for))
        if step.caution:
            lines.append(Text(f"{CAUTION} {step.caution}", style="caution"))
        title = Table.grid(padding=(0, 2))
        title.add_column(width=2, justify="right")
        title.add_row(Text(str(number), style="label"), Text(step.title, style="label"))
        parts += [Text(), title, Indent(Group(*lines), 6)]
    return Group(*parts)


def concept_block(concept: Concept) -> RenderableType:
    head = Text.assemble((f"{CONCEPT} ", "label"), (concept.term, "cmd"))
    if concept.aka:
        head.append(f"  ({', '.join(concept.aka)})", "meta")
    body: list[RenderableType] = [Text(concept.text)]
    if concept.see:
        body.append(Text.assemble(("See: ", "meta"), (" · ".join(concept.see), "cmd")))
    return Group(head, Indent(Group(*body)))


# --- whole outputs of one ncs command -------------------------------------------------------------------------


def print_search(
    console: Console,
    library: Library,
    commands: Sequence[Command],
    flows: Sequence[Flow],
    concepts: Sequence[Concept],
    *,
    detail: bool,
    total: int,
    suggestions: Sequence[str] = (),
    in_prose: int = 0,
) -> None:
    if commands:
        for command in commands:
            console.print(command_block(command, detail, library))
            console.print()
        count = f"{len(commands)} of {total}" if total > len(commands) else str(total)
        console.print(Text(f"{count} command(s)", style="meta"))
        console.print(LEGEND)
    else:
        console.print("No matching commands.", style="meta")
        if suggestions:
            console.print(Text.assemble(("Did you mean: ", "meta"), (", ".join(dict.fromkeys(suggestions)), "label")))
    if in_prose:
        plural = "command mentions" if in_prose == 1 else "commands mention"
        console.print(Text(f"{in_prose} more {plural} this in its notes or example: add --notes", style="meta"))
    for kind, name in FLOW_KINDS.items():
        ids = [flow.id for flow in flows if flow.kind == kind]
        if ids:
            _print_related(console, FLOW_ICONS[kind], name, ids, "ncs <id>")
    if concepts:
        _print_related(console, CONCEPT, "Concepts", [concept.term for concept in concepts], "ncs <term>")


def print_diagnosis(
    console: Console, library: Library, diagnosis: Diagnosis, entries: Optional[Mapping[str, Command]] = None
) -> None:
    console.print(Text.assemble(("Understood: ", "meta"), (" · ".join(diagnosis.understood), "label")))
    console.print()
    if diagnosis.flows:
        best, *others = diagnosis.flows
        console.print(flow_block(best.with_values(), entries=entries))
        if others:
            console.print()
            _print_related(console, FLOW_ICONS[best.kind], "Also check", [flow.id for flow in others], "ncs <id>")
    if diagnosis.commands:
        console.print()
        console.print(Text("Helpful commands", style="label"))
        console.print()
        for command in diagnosis.commands:
            console.print(command_block(command, detail=False, library=library))
            console.print()
    if diagnosis.concepts:
        _print_related(console, CONCEPT, "Background", [c.term for c in diagnosis.concepts], "ncs <term>")


def print_undo(console: Console, result: UndoResult) -> None:
    """Removal commands as a plain block (no icons or indent, so it copies cleanly), then what needs a look."""
    if result.commands:
        console.print(Text("Removal commands, in this order:", style="label"))
        for command in result.commands:
            console.print(Text(command, style="cmd"), soft_wrap=True)
    if result.flagged:
        console.print()
        console.print(Text(f"{CAUTION} Check before running (not in the block above):", style="caution"))
        for removal in result.flagged:
            console.print(Text.assemble("  ", (removal.remove or removal.line, "cmd")), soft_wrap=True)
            console.print(Indent(Text(removal.note, style="caution"), 4))
    if result.unhandled:
        console.print()
        console.print(Text("Not handled (no rule, inside a block, or not configuration):", style="label"))
        for line in result.unhandled:
            where = f"   (in {line.context})" if line.context else ""
            console.print(Text.assemble("  ", line.text, (where, "meta")), soft_wrap=True)
    if not (result.removals or result.unhandled):
        console.print("No configuration lines found.", style="meta")
        return
    console.print()
    console.print(Text("Review before pasting, and save only after checking the result.", style="meta"))


def print_explanation(console: Console, library: Library, explanation: Explanation, detail: bool) -> None:
    line = explanation.line
    head = Text.assemble((f"{line.text}", "label"))
    if line.context:
        head.append(f"   (in {line.context})", "meta")
    console.print(head, soft_wrap=True)
    if explanation.negation:
        verb = "removes" if explanation.negation == "no" else "resets to the default"
        console.print(Indent(Text(f"This line {verb} the setting below.", style="meta")))
    if explanation.commands and not explanation.exact:
        console.print(Indent(Text("Closest entry (only the beginning of the line matches):", style="meta")))
    for command in explanation.commands:
        console.print(Indent(command_block(command, detail, library)))
    if not explanation.commands:
        console.print(Indent(Text("No entry matches this command.", style="meta")))
        if explanation.related:
            console.print(Indent(Text("Related:", style="meta")))
            for command in explanation.related:
                console.print(Indent(command_title(command), 4))
    for pipe, filters in explanation.filters:
        console.print(Indent(Text.assemble(("Filter: ", "meta"), (f"| {pipe}", "label"))), soft_wrap=True)
        if not filters:
            console.print(Indent(Text("No output filter matches this part.", style="meta"), 4))
        for command in filters:
            console.print(Indent(command_block(command, detail=False, library=library), 4))
    if explanation.remove:
        console.print(Indent(Text.assemble(("Remove with: ", "meta"), (explanation.remove, "cmd"))))


def print_flow_list(console: Console, flows: Sequence[Flow]) -> None:
    table = _table("", "Flow id", "Title", "Steps")
    for flow in flows:
        table.add_row(Text(FLOW_ICONS[flow.kind], style="label"), Text(flow.id, style="cmd"), flow.title, str(len(flow.steps)))
    console.print(table)
    legend = "   ".join(f"{FLOW_ICONS[kind]} {name.lower()}" for kind, name in FLOW_KINDS.items())
    console.print(Text(f"{legend}   Open one with: ncs <id>", style="meta"))


def print_concept_list(console: Console, concepts: Sequence[Concept]) -> None:
    table = _table("Term", "Platform", "Also known as")
    for concept in concepts:
        table.add_row(Text(concept.term, style="cmd"), concept.platform, ", ".join(concept.aka))
    console.print(table)
    console.print(Text("Open one with: ncs <term>", style="meta"))


def print_entry_list(console: Console, title: str, entries: Sequence[Entry], empty: str) -> None:
    console.print(Text(title, style="label"))
    for entry in entries:
        console.print(Indent(entry_title(entry)), soft_wrap=True)
    if not entries:
        console.print(Indent(Text(empty, style="meta")))


def print_topics(console: Console, library: Library) -> None:
    table = _table("Topic", "Title", "Commands", f"{RARE} Gems")
    for name, topics in library.topics_by_platform():
        table.add_section()
        table.add_row(Text(name, style="label"), "", "", "")
        for topic in topics:
            gems = sum(command.rare for command in topic.commands)
            table.add_row(Text(topic.slug, style="cmd"), topic.title, str(len(topic.commands)), str(gems))
    console.print(table)
    console.print(
        Text(
            f"{len(library.commands)} commands · {len(library.flows_of('troubleshoot'))} troubleshooting flows · "
            f"{len(library.flows_of('change'))} change workflows · {len(library.concepts)} concepts",
            style="meta",
        )
    )
    console.print(Text("Search: ncs <words>   Browse: ncs   Topic: ncs -t <topic>   Help: ncs -h", style="meta"))
    console.print(Text(CREDIT, style="meta"))


def _print_related(console: Console, icon: str, label: str, names: Sequence[str], hint: str) -> None:
    console.print(Text.assemble((f"{icon} {label}: ", "label"), (", ".join(names), "cmd"), (f"   ({hint})", "meta")))


def _table(*columns: str) -> Table:
    table = Table(box=None, header_style="label", pad_edge=False)
    for column in columns:
        table.add_column(column)
    return table
