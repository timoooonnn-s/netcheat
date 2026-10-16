import pytest

from netcheat.config import ConfigLine, explain, read_lines, rollback, undo
from netcheat.loader import load_library

SHOW_RUN = """\
SW1:1#show running-config module radius
Preparing to Display Configuration...
#
# RADIUS CONFIGURATION
#
radius enable
radius server host 10.0.0.50 key ****** used-by eapol priority 1 acct-enable
radius server host 10.0.0.50 key ****** used-by cli
snmp-server community :: group "readgrp" secname "test"
snmp-server host 10.0.0.81 port 1162 v3 authPriv "nms-v3"
syslog host 1 address 10.0.0.60
syslog host 1 enable
interface gigabitEthernet 1/5
eapol status auto
exit
"""


@pytest.fixture(scope="module")
def library():
    return load_library()


def test_read_lines_skips_prompts_comments_and_pager_and_keeps_block_context():
    lines = read_lines(SHOW_RUN)
    assert lines[0] == ConfigLine("show running-config module radius")
    assert ConfigLine("eapol status auto", "interface gigabitEthernet 1/5") in lines
    assert not any(line.text.startswith(("#", "Preparing", "exit")) for line in lines)


def test_undo_removes_in_reverse_order_once_per_object(library):
    result = undo(library, read_lines(SHOW_RUN))
    assert result.commands == [  # `used-by cli` is a login server: flagged, not in the block
        "no syslog host 1",
        "no snmp-server host 10.0.0.81 port 1162 v3 \"nms-v3\"",
        "no radius server host 10.0.0.50 used-by eapol",
        "no radius enable",
    ]


def test_undo_reports_manual_steps_and_unhandled_lines(library):
    result = undo(library, read_lines(SHOW_RUN))
    assert [r.line for r in result.flagged] == [
        'snmp-server community :: group "readgrp" secname "test"',
        "radius server host 10.0.0.50 key ****** used-by cli",
    ]
    assert "community-by-index" in result.flagged[0].note
    # A pasted show command is not configuration, but it is reported rather than dropped.
    assert [line.text for line in result.unhandled] == [
        "show running-config module radius",
        "interface gigabitEthernet 1/5",
        "eapol status auto",
    ]


def test_risky_removals_are_flagged_not_in_the_block(library):
    result = undo(library, read_lines("ssh\n"))
    assert result.commands == []
    assert result.flagged[0].remove == "no ssh"


@pytest.mark.parametrize(
    "line, removal",
    [
        ("username rwa level rwa", "no username rwa"),
        ("username add netops level rwa enable", "no username netops"),
        ("radius server host 10.0.0.50 key x used-by cli priority 1", "no radius server host 10.0.0.50 used-by cli"),
        ("tacacs server host 10.0.0.70 key x", "no tacacs server 10.0.0.70"),
        ("tacacs server secondary-host 10.0.0.71 key x", "no tacacs server 10.0.0.71"),
    ],
)
def test_removals_that_can_lock_you_out_never_reach_the_paste_block(library, line, removal):
    """Pasting the block must not be able to end your own session. These removals delete the account or
    the server your login depends on, so each one needs a note, which keeps it out of `commands`."""
    result = undo(library, read_lines(line + "\n"))
    assert result.commands == []
    assert [r.remove for r in result.flagged] == [removal]
    assert result.flagged[0].note


def test_read_lines_strips_junos_prompts_and_banners():
    pasted = "{primary:node0}\nadmin@srx1> show interfaces terse\n[edit]\nadmin@srx1# show configuration\n"
    assert read_lines(pasted) == [ConfigLine("show interfaces terse"), ConfigLine("show configuration")]


def test_a_configuration_line_is_never_mistaken_for_a_prompt():
    assert read_lines("snmp-server host 10.0.0.80 v2c readview\n") == [ConfigLine("snmp-server host 10.0.0.80 v2c readview")]


def test_explain_finds_the_entry_behind_a_junos_prompt(library):
    explanation = explain(library, read_lines("admin@srx1> show interfaces terse\n")[0])
    assert explanation.found
    assert explanation.commands[0].cmd == "show interfaces terse [<interface>]"


@pytest.mark.parametrize(
    "line, entry",
    [
        ("sh isis adj", "show isis adjacencies [verbose]"),
        ("no radius server host 10.0.0.5 used-by cli", "no radius server host <ip> used-by {cli | eapol | web | snmp | endpoint-tracking}"),
        ("tacacs server secondary-host 10.0.0.71 key x", "tacacs server host <ip> key <secret> [port <1-65535>] [timeout <10-30>] [single-connection]"),
        ("show running-config module radius", "show running-config [module <module>]"),
    ],
)
def test_explain_finds_the_entry(library, line, entry):
    assert explain(library, ConfigLine(line)).commands[0].cmd == entry


def test_explain_negated_line_and_removal_hint(library):
    negated = explain(library, ConfigLine("no slpp enable"))
    assert negated.negation == "no" and negated.commands[0].cmd == "slpp enable"
    configured = explain(library, ConfigLine("syslog host 2 address 10.0.0.9"))
    assert configured.remove == "no syslog host 2"


def test_explain_unknown_line_offers_related_commands_only_for_two_keywords(library):
    assert explain(library, ConfigLine("something odd 42")).related == []
    assert explain(library, ConfigLine("radius frobnicate")).related


def test_rollback_covers_what_a_change_workflow_adds(library):
    result = rollback(library, library.flow("syslog-ntp-dns-replace").with_values({"new_syslog": "192.0.2.6"}))
    assert result.commands[-1] == "no syslog host 3"
    assert not any("10.0.0.10" in command for command in result.commands)  # the old server is removed by the plan


@pytest.mark.parametrize(
    "line, parts",
    [
        ("show running-config | include radius", ["show running-config", "include radius"]),
        ('show run | inc "radius|snmp" ignore-case', ["show run", 'inc "radius|snmp" ignore-case']),
        ("show run | include radius|snmp | count", ["show run", "include radius|snmp", "count"]),
    ],
)
def test_pipes_split_only_at_standalone_bars(line, parts):
    from netcheat.config import _split_pipes

    assert _split_pipes(line) == parts


def test_explain_piped_line_explains_command_and_each_filter(library):
    explanation = explain(library, ConfigLine('show runn | inc "radius|snmp" ignore-case | count'))
    assert explanation.commands[0].cmd == "show running-config [module <module>]"
    assert [entries[0].cmd for _, entries in explanation.filters] == [
        "<show command> | include <pattern> [field <n>] [ignore-case] [header <n>]",
        "<show command> | count",
    ]
    assert explanation.remove is None and explanation.found


def test_filters_follow_the_platform_of_the_command(library):
    fabric = explain(library, ConfigLine("show vlan basic | count")).filters[0][1]
    junos = explain(library, ConfigLine("show arp no-resolve | count")).filters[0][1]
    assert [c.platform for c in fabric] == ["fabric-engine"]
    assert [c.platform for c in junos] == ["junos-srx"]


def test_a_filter_entry_wins_the_whole_line_but_a_filtered_command_still_splits(library):
    """`show log messages | last 50` is one entry, so the whole line matches it. A plain show command that
    merely ends in a filter must still be split, so the filter gets explained on its own."""
    own = explain(library, ConfigLine("show log messages | last 50"))
    assert own.commands and own.commands[0].cmd == "show log messages | last <n>"
    assert own.filters == []

    filtered = explain(library, ConfigLine("show running-config | include radius"))
    assert filtered.commands[0].cmd == "show running-config [module <module>]"
    assert [pipe for pipe, _ in filtered.filters] == ["include radius"]
    assert all(entries for _, entries in filtered.filters)
