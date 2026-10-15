"""`ncs browse`: a full-screen browser for when you only have a broad idea of what you need.

Left: topics, gems, troubleshooting flows, change workflows and concepts. Middle: the matching entries, narrowed live by the filter.
Right: the details of the highlighted entry, rendered with the same blocks as the plain CLI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence, Union

from rich.console import RenderableType
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, Input, OptionList, Static, Tree
from textual.widgets.option_list import Option

from netcheat import CREDIT
from netcheat.models import FLOW_KINDS, Command, Concept, Flow, Library
from netcheat.render import CONCEPT, FLOW_ICONS, RARE, THEME, command_block, command_title, concept_block, flow_block
from netcheat.search import Filters, search_commands, search_concepts, search_flows

Entry = Union[Command, Flow, Concept]


@dataclass(frozen=True)
class Scope:
    """What the middle list shows: commands (of one topic, or all; optionally only gems), flows of one kind or concepts."""

    kind: str
    topic: str | None = None
    gems: bool = False


@dataclass(frozen=True)
class View:
    """How one entry appears in the browser. `key` identifies it in the option list."""

    key: str
    label: Text
    copy_text: str
    detail: Callable[[], RenderableType]


def view(entry: Entry) -> View:
    if isinstance(entry, Command):
        key = f"command:{entry.topic}:{entry.mode}:{entry.cmd}"
        return View(key, command_title(entry), entry.cmd, lambda: command_block(entry, detail=True))
    if isinstance(entry, Flow):
        return View(f"flow:{entry.id}", Text.assemble((f"{FLOW_ICONS[entry.kind]} ", "label"), entry.title), entry.id, lambda: flow_block(entry))
    return View(f"concept:{entry.term}", Text.assemble((f"{CONCEPT} ", "label"), entry.term), entry.term, lambda: concept_block(entry))


class Browser(App[None]):
    TITLE = "ncs browse"
    SUB_TITLE = CREDIT
    CSS = """
    #nav, #items, #detail-pane { border: none; border-top: solid $panel; border-title-color: $text-muted; }
    #nav { width: 32; }
    #items { width: 1fr; }
    #detail-pane { width: 1fr; padding: 0 1; }
    """
    BINDINGS = [
        Binding("slash", "focus_filter", "Filter"),
        Binding("escape", "leave_filter", "Leave filter", show=False),
        Binding("g", "toggle_gems", "Gems only"),
        Binding("c", "copy", "Copy command"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, library: Library, terms: Sequence[str] = ()) -> None:
        super().__init__()
        self.library = library
        self.initial_filter = " ".join(terms)
        self.scope = Scope("commands")
        self.entries: list[Entry] = []
        self.views: dict[str, View] = {}  # the current list, by option id

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(self.initial_filter, placeholder="Filter: type words, e.g. isis adj   (/ to focus, Esc to leave)", id="filter")
        with Horizontal():
            yield self._navigation()
            yield OptionList(id="items")
            with VerticalScroll(id="detail-pane"):
                yield Static(id="detail")
        yield Footer()

    def on_mount(self) -> None:
        self.console.push_theme(THEME)  # the named styles (cmd, meta, ...) of the shared render blocks
        self.query_one("#nav", Tree).border_title = "Browse"
        self.query_one("#detail-pane", VerticalScroll).border_title = "Details"
        self._refresh_items()
        self.query_one("#nav", Tree).focus()

    def _navigation(self) -> Tree[Scope]:
        tree: Tree[Scope] = Tree("ncs", id="nav")
        tree.show_root = False
        tree.root.add_leaf("All commands", Scope("commands"))
        tree.root.add_leaf(f"{RARE} Gems", Scope("commands", gems=True))
        for name, topics in self.library.topics_by_platform():
            platform = tree.root.add(name, expand=True)
            for topic in topics:
                platform.add_leaf(f"{topic.slug} ({len(topic.commands)})", Scope("commands", topic=topic.slug))
        for kind, name in FLOW_KINDS.items():
            tree.root.add_leaf(f"{FLOW_ICONS[kind]} {name}", Scope(kind))
        tree.root.add_leaf(f"{CONCEPT} Concepts", Scope("concepts"))
        return tree

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[Scope]) -> None:
        if event.node.data is not None and event.node.data != self.scope:
            self.scope = event.node.data
            self._refresh_items()

    def on_tree_node_selected(self, event: Tree.NodeSelected[Scope]) -> None:
        if event.node.data is not None:
            self.query_one("#items", OptionList).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh_items()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#items", OptionList).focus()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        # Highlight messages are queued, so one may belong to a list that was replaced meanwhile: look the
        # entry up by its key instead of its position, and ignore keys that are no longer listed.
        shown = self.views.get(event.option_id or "")
        if shown is not None:
            self.query_one("#detail", Static).update(shown.detail())
            self.query_one("#detail-pane", VerticalScroll).scroll_home(animate=False)

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def action_leave_filter(self) -> None:
        self.query_one("#items", OptionList).focus()

    def action_toggle_gems(self) -> None:
        if self.scope.kind == "commands":
            self.scope = Scope("commands", self.scope.topic, not self.scope.gems)
            self._refresh_items()

    def action_copy(self) -> None:
        items = self.query_one("#items", OptionList)
        if items.highlighted is None:
            return
        text = self.views[items.get_option_at_index(items.highlighted).id or ""].copy_text
        self.copy_to_clipboard(text)
        self.notify(f"Copied: {text}", timeout=2)

    def _refresh_items(self) -> None:
        self.entries = self._matching_entries(self.query_one("#filter", Input).value.split())
        self.views = {shown.key: shown for shown in map(view, self.entries)}
        items = self.query_one("#items", OptionList)
        items.set_options(Option(shown.label, id=key) for key, shown in self.views.items())
        noun = "flows" if self.scope.kind in FLOW_KINDS else self.scope.kind
        items.border_title = f"{len(self.entries)} {noun}" + (f" {RARE} gems only" if self.scope.gems else "")
        if self.entries:
            items.highlighted = 0
        else:
            self.query_one("#detail", Static).update(Text("Nothing matches. Change the filter or pick another topic.", style="dim"))

    def _matching_entries(self, terms: list[str]) -> list[Entry]:
        if self.scope.kind in FLOW_KINDS:
            flows = self.library.flows_of(self.scope.kind)
            return search_flows(flows, terms) if terms else flows
        if self.scope.kind == "concepts":
            return search_concepts(self.library.concepts, terms) if terms else list(self.library.concepts)
        commands = [c for c in self.library.commands if self.scope.topic in (None, c.topic)]
        return search_commands(commands, terms, Filters(rare=self.scope.gems))


def run_browser(library: Library, terms: Sequence[str] = ()) -> None:
    Browser(library, terms).run()
