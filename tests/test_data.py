"""Integrity checks for the shipped data files. They run on every change, so hand edits stay valid."""

from collections import Counter
from pathlib import Path

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


def test_gems_stay_a_small_share_of_the_commands(library):
    """`rare` marks a command you would not remember exists. A marker on half the corpus marks nothing,
    so keep it under a fifth: `ncs tip` and `-r` are only useful while the set is small."""
    gems = [c for c in library.commands if c.rare]
    assert gems, "no gems left at all"
    assert len(gems) <= len(library.commands) // 5, f"{len(gems)} of {len(library.commands)} commands marked rare"


def test_every_removal_that_can_lock_you_out_carries_a_note(library):
    """An undo rule whose removal deletes the login account or the server that authenticates admin logins
    must carry a `note`, because a note is what keeps it out of the paste-ready block of `ncs undo`."""
    risky = ("no username", "no tacacs server", "no radius server host <ip> used-by cli")
    missing = [
        rule.match
        for command in library.commands
        for rule in command.undo
        if rule.remove.startswith(risky) and not rule.note
    ]
    assert missing == []


def test_readme_counts_match_the_data(library):
    """The README's intro states the size of the cheatsheet. Keep it true automatically, so the numbers
    the reader uses to judge the tool cannot quietly drift away from the data."""
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    counts = {
        f"{len(library.commands)} commands": "commands",
        f"{len(library.flows_of('troubleshoot'))} troubleshooting flows": "troubleshooting flows",
        f"{len(library.flows_of('change'))} change workflows": "change workflows",
        f"{len(library.concepts)} short concept notes": "concepts",
        f"{sum(c.rare for c in library.commands)} of them are marked": "gems",
    }
    assert [what for phrase, what in counts.items() if phrase not in readme] == []


def test_every_cli_mode_in_the_data_has_a_path(library):
    """A command's detail view says how to reach its CLI mode. A new mode value must get a path, or the
    command silently loses the one line that explains why a correct command is rejected."""
    from netcheat.models import mode_path

    missing = sorted({c.mode for c in library.commands if not mode_path(c.mode)[0] and c.mode not in NO_PATH_NEEDED})
    assert missing == []


NO_PATH_NEEDED = {"User EXEC", "operational", "any"}  # a login lands there already


def test_flow_step_commands_resolve_to_an_entry(library):
    """A step command should be an instance of a real entry, so the flow can carry that entry's caution.
    A step that resolves to nothing is usually a typo or a missing entry; these are the known exceptions."""
    from netcheat.config import entries_for

    known_gaps = {
        # `no` forms with no positive entry to fall back on
        "no boot config flags telnetd",
        "no ip name-server secondary",
        "no snmp-server community-by-index second",
        "reset -cancel",  # the `reset -in` entry mentions it in its notes, but has no entry of its own
        # show variants whose options are not in the documented syntax
        "show interfaces gigabitEthernet statistics verbose 1/5",
        "show ip isis redistribute vrf CORP",
        "show khi performance pthread sort cpu",
        "show spanning-tree bpduguard 1/5",
    }
    steps = {cmd for flow in library.flows for step in flow.with_values().steps for cmd in step.cmds}
    unresolved = sorted(steps - set(entries_for(library, steps)) - known_gaps)
    assert unresolved == []


def test_concept_back_links_reach_the_commands(library):
    """Every `see:` reference resolves to a command, so the reverse index is never empty for it."""
    linked = {ref for concept in library.concepts for ref in concept.see}
    assert linked
    for command in library.commands:
        for term in library.concepts_for(command):
            assert command.cmd in next(c for c in library.concepts if c.term == term).see
    assert sum(1 for c in library.commands if library.concepts_for(c)) == len(linked)
