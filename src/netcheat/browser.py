"""The full-screen browser (`ncs`, `ncs browse`), for when you only have a broad idea of what you need.

Left: favourites, recent, gems, topics, flows and concepts. Middle: the matching entries, narrowed live by the
filter. Right: the details of the highlighted entry, rendered with the same blocks as the plain CLI.
Runs in any terminal, also over SSH; copying uses the terminal's clipboard sequence (OSC 52).
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional, Sequence

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, OptionList, Static, Tree
from textual.widgets.option_list import Option

from netcheat import CREDIT
from netcheat.models import FLOW_KINDS, Command, Concept, Entry, Flow, Library, entry_key
from netcheat.render import (
    CONCEPT,
    FAVOURITE,
    FLOW_ICONS,
    RARE,
    RECENT,
    THEME,
    command_block,
    concept_block,
    entry_title,
    flow_block,
)
from netcheat.search import Filters, search_commands, search_concepts, search_flows
from netcheat.state import State

PERSONAL = {"favourites": f"{FAVOURITE} Favourites", "recent": f"{RECENT} Recent"}


@dataclass(frozen=True)
class Scope:
    """What the middle list shows: commands (of one topic, or all; optionally only gems), flows of one kind,
    concepts, or the personal lists (favourites, recent)."""

    kind: str
    topic: Optional[str] = None
    gems: bool = False


class ValuesScreen(ModalScreen[Optional[str]]):
    """Edit the {name} values of a flow as `name=value` pairs."""

    CSS = "ValuesScreen { align: center middle; } #values { width: 90%; border: tall $accent; }"
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        field = Input(self.text, id="values", placeholder="name=value name=value ...")
        field.border_title = "Your values (Enter to apply, Esc to cancel)"
        yield field

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class Browser(App[None]):
    TITLE = "ncs"
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
        Binding("f", "toggle_favourite", "Star"),
        Binding("c", "copy", "Copy"),
        Binding("1", "copy_step(1)", "Copy step", key_display="1-9"),
        *(Binding(str(n), f"copy_step({n})", show=False) for n in range(2, 10)),
        Binding("v", "edit_values", "Values"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, library: Library, terms: Sequence[str] = (), state: Optional[State] = None) -> None:
        super().__init__()
        self.library = library
        self.initial_filter = " ".join(terms)
        self.state = state or State.load()
        self.values: dict[str, str] = {}  # flow values set in this session, shared by all flows that use the name
        self.scope = Scope("commands")
        self.entries: list[Entry] = []  # the current list
        self._listed: dict[str, Entry] = {}  # the same entries by option id (entry_key)

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
        for kind, label in PERSONAL.items():
            tree.root.add_leaf(label, Scope(kind))
        tree.root.add_leaf(f"{RARE} Gems", Scope("commands", gems=True))
        for name, topics in self.library.topics_by_platform():
            platform = tree.root.add(name, expand=True)
            for topic in topics:
                platform.add_leaf(f"{topic.slug} ({len(topic.commands)})", Scope("commands", topic=topic.slug))
        for kind, name in FLOW_KINDS.items():
            tree.root.add_leaf(f"{FLOW_ICONS[kind]} {name}", Scope(kind))
        tree.root.add_leaf(f"{CONCEPT} Concepts", Scope("concepts"))
        return tree

    # --- events ---

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[Scope]) -> None:
        if event.node.data is not None and event.node.data != self.scope:
            self.scope = event.node.data
            self._refresh_items()

    def on_tree_node_selected(self, event: Tree.NodeSelected[Scope]) -> None:
        if event.node.data is not None:
            self.query_one("#items", OptionList).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter":
            self._refresh_items()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter":
            self.query_one("#items", OptionList).focus()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        # Highlight messages are queued, so one may belong to a list that was replaced meanwhile: look the
        # entry up by its key instead of its position, and ignore keys that are no longer listed.
        if (event.option_id or "") in self._listed:
            self._show_detail()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        entry = self._listed.get(event.option_id or "")
        if entry is not None:
            self.state.opened(entry_key(entry))

    # --- actions ---

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def action_leave_filter(self) -> None:
        self.query_one("#items", OptionList).focus()

    def action_toggle_gems(self) -> None:
        if self.scope.kind == "commands":
            self.scope = Scope("commands", self.scope.topic, not self.scope.gems)
            self._refresh_items()

    def action_toggle_favourite(self) -> None:
        entry = self.highlighted
        if entry is None:
            return
        starred = self.state.toggle_favourite(entry_key(entry))
        self.notify(("Starred: " if starred else "Unstarred: ") + entry_title(entry).plain, timeout=2)
        self._refresh_items(keep=entry_key(entry))

    def action_copy(self) -> None:
        """Copy the command, or the id of a flow (for `ncs export <id>`), or the term of a concept."""
        entry = self.highlighted
        if entry is not None:
            text = entry.cmd if isinstance(entry, Command) else entry.id if isinstance(entry, Flow) else entry.term
            self._copy(text, entry)

    def action_copy_step(self, number: int) -> None:
        """Copy all commands of step <number> of the highlighted flow, with the current values filled in."""
        flow = self._highlighted_flow()
        if flow is None:
            return
        if number > len(flow.steps):
            self.notify(f"This flow has {len(flow.steps)} steps.", severity="warning", timeout=2)
            return
        commands = flow.commands(number)
        self._copy("\n".join(commands), flow, f"step {number} ({len(commands)} commands)")

    def action_edit_values(self) -> None:
        flow = self._highlighted_flow()
        if flow is None or not flow.values:
            self.notify("Values exist only for flows with example values.", timeout=2)
            return
        current = " ".join(f"{name}={value}" for name, value in flow.values.items())
        self.push_screen(ValuesScreen(current), self._apply_values)

    def _apply_values(self, text: Optional[str]) -> None:
        if text is None:
            return
        pairs = [part.partition("=") for part in text.split()]
        broken = [name for name, sep, value in pairs if not (sep and name and value)]
        if broken:
            self.notify(f"Not name=value: {', '.join(broken)}", severity="error", timeout=3)
            return
        self.values.update({name: value for name, _, value in pairs})
        self._show_detail()

    # --- helpers ---

    @property
    def highlighted(self) -> Optional[Entry]:
        items = self.query_one("#items", OptionList)
        if items.highlighted is None:
            return None
        return self._listed.get(items.get_option_at_index(items.highlighted).id or "")

    def _highlighted_flow(self) -> Optional[Flow]:
        entry = self.highlighted
        return entry.with_values(self.values) if isinstance(entry, Flow) else None

    def _copy(self, text: str, entry: Entry, what: str = "") -> None:
        """OSC 52 is write-only: the terminal never answers, so a copy into a terminal that ignores the
        sequence (macOS Terminal.app, tmux without clipboard) cannot be detected. Say so instead of
        claiming success, and try a local clipboard tool as well when there is one."""
        self.copy_to_clipboard(text)
        local = _copy_locally(text)
        self.state.opened(entry_key(entry))
        confirmed = "Copied" if local else "Sent to the terminal clipboard:"
        self.notify(f"{confirmed} {what or text}", timeout=2)

    def _show_detail(self) -> None:
        entry = self.highlighted
        if entry is None:
            return
        if isinstance(entry, Command):
            detail = command_block(entry, detail=True)
        elif isinstance(entry, Flow):
            detail = flow_block(entry.with_values(self.values), values_hint="v; copy a step with its number")
        else:
            detail = concept_block(entry)
        self.query_one("#detail", Static).update(detail)
        self.query_one("#detail-pane", VerticalScroll).scroll_home(animate=False)

    def _label(self, entry: Entry) -> Text:
        title = entry_title(entry)
        return Text.assemble((f"{FAVOURITE} ", "favourite"), title) if self.state.is_favourite(entry_key(entry)) else title

    def _refresh_items(self, keep: Optional[str] = None) -> None:
        """Rebuild the middle list; `keep` is the key to highlight again (else the first entry)."""
        self.entries = self._matching_entries(self.query_one("#filter", Input).value.split())
        self._listed = {entry_key(entry): entry for entry in self.entries}
        items = self.query_one("#items", OptionList)
        items.set_options(Option(self._label(entry), id=key) for key, entry in self._listed.items())
        noun = "flows" if self.scope.kind in FLOW_KINDS else "entries" if self.scope.kind in PERSONAL else self.scope.kind
        items.border_title = f"{len(self.entries)} {noun}" + (f" {RARE} gems only" if self.scope.gems else "")
        if self.entries:
            items.highlighted = list(self._listed).index(keep) if keep in self._listed else 0
            self._show_detail()
        else:
            empty = "Star entries with f." if self.scope.kind == "favourites" else "Nothing matches. Change the filter or pick another topic."
            self.query_one("#detail", Static).update(Text(empty, style="dim"))

    def _matching_entries(self, terms: list[str]) -> list[Entry]:
        kind = self.scope.kind
        if kind in PERSONAL:
            keys = self.state.favourites if kind == "favourites" else self.state.recent
            return _filtered([e for e in map(self.library.find, keys) if e is not None], terms)
        if kind in FLOW_KINDS:
            flows = self.library.flows_of(kind)
            return search_flows(flows, terms) if terms else flows
        if kind == "concepts":
            return search_concepts(self.library.concepts, terms) if terms else list(self.library.concepts)
        commands = [c for c in self.library.commands if self.scope.topic in (None, c.topic)]
        return search_commands(commands, terms, Filters(rare=self.scope.gems))


def _copy_locally(text: str) -> bool:
    """Put the text on the clipboard of the machine the terminal runs on, if a clipboard tool is there.
    Over SSH there is none, which is what OSC 52 is for. True only if a tool accepted the text."""
    for tool in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        if shutil.which(tool[0]) is None:
            continue
        try:
            return subprocess.run(tool, input=text.encode(), timeout=2).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False
    return False


def _filtered(entries: list[Entry], terms: list[str]) -> list[Entry]:
    """A mixed list (favourites, recent) narrowed by the filter, keeping its own order."""
    if not terms:
        return entries
    matching = {
        *map(entry_key, search_commands([e for e in entries if isinstance(e, Command)], terms)),
        *map(entry_key, search_flows([e for e in entries if isinstance(e, Flow)], terms)),
        *map(entry_key, search_concepts([e for e in entries if isinstance(e, Concept)], terms)),
    }
    return [entry for entry in entries if entry_key(entry) in matching]


def run_browser(library: Library, terms: Sequence[str] = ()) -> None:
    Browser(library, terms).run()
