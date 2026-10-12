"""Interactive `ncs add`: append a new command entry to one of the topic files."""

from __future__ import annotations

from pathlib import Path
from textwrap import indent
from typing import Any

import yaml
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.text import Text

from netcheat.loader import DataError, load_topic
from netcheat.models import KINDS, Library, Topic

DEFAULT_MODE = {"fabric-engine": "User EXEC", "junos-srx": "operational"}


def run_add(console: Console, library: Library) -> Topic:
    """Ask for the fields of a new command, append it and return the reloaded topic."""
    for number, topic in enumerate(library.topics, 1):
        console.print(Text.assemble(f"{number:>3}  ", (topic.slug, "cmd"), (f"  {topic.title}", "meta")))
    choice = IntPrompt.ask("Topic number", choices=[str(n) for n in range(1, len(library.topics) + 1)], show_choices=False)
    topic = library.topics[choice - 1]

    entry: dict[str, Any] = {
        "cmd": Prompt.ask("Command"),
        "desc": Prompt.ask("What it does"),
        "kind": Prompt.ask("Kind", choices=list(KINDS), default="show"),
        "mode": Prompt.ask("CLI mode", default=DEFAULT_MODE[topic.platform]),
        "tags": [tag.strip() for tag in Prompt.ask("Tags, comma separated", default="").split(",") if tag.strip()],
        "example": Prompt.ask("Example (optional)", default=""),
        "notes": Prompt.ask("Notes (optional)", default=""),
        "since": Prompt.ask("Added in version, e.g. 9.4 (optional)", default=""),
        "rare": Confirm.ask("Rarely used gem worth remembering?", default=False),
    }
    return append_command(topic, {key: value for key, value in entry.items() if value})


def append_command(topic: Topic, entry: dict[str, Any]) -> Topic:
    """Append the entry to the topic's `commands:` list (always the last key of a topic file).

    Plain text is appended instead of re-dumping the file, so comments and layout survive.
    The file is restored if the result does not load cleanly.
    """
    path: Path = topic.path
    original = path.read_text(encoding="utf-8")
    block = yaml.safe_dump([entry], sort_keys=False, allow_unicode=True, width=100)
    path.write_text(original.rstrip("\n") + "\n\n" + indent(block, "  "), encoding="utf-8")
    try:
        return load_topic(path, topic.platform)
    except DataError:
        path.write_text(original, encoding="utf-8")
        raise
