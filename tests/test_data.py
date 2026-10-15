"""Integrity checks for the shipped data files. They run on every change, so hand edits stay valid."""

from collections import Counter

import pytest

from netcheat.loader import load_library
from netcheat.models import version_key


@pytest.fixture(scope="module")
def library():
    return load_library()


def test_library_loads_all_platforms(library):
    platforms = {topic.platform for topic in library.topics}
    assert platforms == {"fabric-engine", "junos-srx"}
    assert all(topic.commands for topic in library.topics)


def test_no_duplicate_commands_within_a_platform(library):
    keys = Counter((c.platform, c.cmd, c.mode) for c in library.commands)
    assert [key for key, count in keys.items() if count > 1] == []


def test_concept_references_point_to_existing_commands(library):
    known = {c.cmd for c in library.commands}
    missing = [(concept.term, ref) for concept in library.concepts for ref in concept.see if ref not in known]
    assert missing == []


def test_every_flow_step_has_commands(library):
    assert all(step.cmds for flow in library.flows for step in flow.steps)


def test_fabric_engine_commands_cite_the_official_reference(library):
    fabric = [c for c in library.commands if c.platform == "fabric-engine"]
    assert [c.cmd for c in fabric if not c.ref.startswith("https://documentation.extremenetworks.com/")] == []


def test_versions_are_not_newer_than_the_latest_known_release(library):
    latest = version_key("9.4.2")
    assert [c.cmd for c in library.commands if c.since and version_key(c.since) > latest] == []


def test_both_flow_kinds_are_shipped(library):
    assert library.flows_of("troubleshoot") and library.flows_of("change")


def test_every_undo_rule_wins_for_its_own_line(library):
    """A sample line built from each rule's pattern must be removed by that rule, not by a competing one."""
    from netcheat.config import _best_undo
    from netcheat.syntax import fill, slots

    for command in library.commands:
        for rule in command.undo:
            values = {name: f"v{index}" for index, name in enumerate(slots(rule.match))}
            line = " ".join(fill(rule.match, values).replace("...", "").split())
            found = _best_undo(library.commands, line)
            assert found is not None and found[1] == rule, f"{line!r} is taken by {found and found[1].match!r}"


def test_change_workflows_have_example_values(library):
    assert all(flow.values for flow in library.flows_of("change"))
