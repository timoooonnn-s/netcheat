import asyncio
import io

from rich.console import Console

from textual.widgets import Input, OptionList, Static, Tree
from textual.widgets.option_list import Option

from netcheat.browser import Browser, Scope
from netcheat.loader import load_library
from netcheat.models import entry_key
from netcheat.state import State


def drive(steps, terms=()):
    """Run the browser headless, apply `steps(app, pilot)` and return the app afterwards."""

    async def run():
        app = Browser(load_library(), terms)
        async with app.run_test(size=(140, 40)) as pilot:
            await steps(app, pilot)
        return app

    return asyncio.run(run())


def test_starts_with_all_commands():
    async def steps(app, pilot):
        assert app.query_one("#items", OptionList).option_count == len(app.library.commands)

    drive(steps)


def test_filter_narrows_and_copy_puts_the_command_on_the_clipboard():
    async def steps(app, pilot):
        await pilot.press("slash", *"isis adj", "enter", "c")
        await pilot.pause()
        assert app.entries[0].cmd == "show isis adjacencies [verbose]"
        assert app.clipboard == "show isis adjacencies [verbose]"

    drive(steps)


def test_initial_terms_prefill_the_filter():
    async def steps(app, pilot):
        assert app.entries[0].cmd.startswith("show isis adjacencies")

    drive(steps, terms=["isis", "adj"])


def test_gems_toggle_and_scopes():
    async def steps(app, pilot):
        await pilot.press("g")
        await pilot.pause()
        assert app.entries and all(entry.rare for entry in app.entries)

        tree = app.query_one("#nav", Tree)
        flows_node = next(node for node in tree.root.children if node.data == Scope("troubleshoot"))
        tree.move_cursor(flows_node)
        await pilot.pause()
        assert [entry.id for entry in app.entries] == [flow.id for flow in app.library.flows_of("troubleshoot")]

        changes_node = next(node for node in tree.root.children if node.data == Scope("change"))
        tree.move_cursor(changes_node)
        await pilot.pause()
        assert app.entries and all(entry.kind == "change" for entry in app.entries)

    drive(steps)


def test_highlight_from_a_replaced_list_is_ignored():
    async def steps(app, pilot):
        items = app.query_one("#items", OptionList)
        stale = OptionList.OptionHighlighted(items, Option("old", id="command:gone"), 250)
        await pilot.press("slash", *"macsec mka keychain")
        await pilot.pause()
        app.on_option_list_option_highlighted(stale)  # used to index the new, shorter list and crash
        shown = Console(width=100, record=True, file=io.StringIO())
        shown.print(app.query_one("#detail", Static).content)
        assert "keychain" in shown.export_text()

    drive(steps)


def test_list_shows_the_same_badges_as_the_cli():
    async def steps(app, pilot):
        await pilot.press("slash", *"clilog")
        await pilot.pause()
        label = app.query_one("#items", OptionList).get_option_at_index(0).prompt
        assert "↑ 9.4" in label.plain

    drive(steps)


def select(app, scope):
    tree = app.query_one("#nav", Tree)
    tree.move_cursor(next(node for node in tree.root.children if node.data == scope))


def test_star_shows_in_favourites_and_is_saved():
    async def steps(app, pilot):
        await pilot.press("slash", *"isis adj", "enter", "f")
        await pilot.pause()
        starred = app.entries[0]
        assert State.load().favourites == [entry_key(starred)]
        select(app, Scope("favourites"))
        await pilot.pause()
        assert app.entries == [starred]  # the filter still applies: "isis adj" matches it
        assert app.query_one("#items", OptionList).get_option_at_index(0).prompt.plain.startswith("★")

    drive(steps)


def test_copied_and_selected_entries_become_recent():
    async def steps(app, pilot):
        await pilot.press("slash", *"isis adj", "enter", "c")
        await pilot.pause()
        assert State.load().recent[0] == entry_key(app.entries[0])

    drive(steps)


def test_number_copies_a_flow_step_with_values():
    async def steps(app, pilot):
        select(app, Scope("change"))
        await pilot.pause()
        app.query_one("#items", OptionList).focus()
        await pilot.press("v")
        await pilot.pause()
        app.screen.query_one(Input).value = "old_radius=192.0.2.9"
        await pilot.press("enter", "5")
        await pilot.pause()
        assert app.clipboard.splitlines()[0] == "no radius server host 192.0.2.9 used-by eapol"

    drive(steps)
