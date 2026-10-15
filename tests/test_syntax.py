import pytest

from netcheat.syntax import SyntaxParseError, compile_patterns, fill, match, slots, tokens, try_compile


def matches(syntax, line, **options):
    return match(compile_patterns(syntax), line, **options)


@pytest.mark.parametrize(
    "syntax, line",
    [
        ("show isis adjacencies [verbose]", "show isis adjacencies"),
        ("show isis adjacencies [verbose]", "SHOW ISIS ADJACENCIES VERBOSE"),
        ("tacacs authentication {cli | web | all}", "tacacs authentication web"),
        ("radius server host <ip> key <secret> [priority <1-10>] [timeout <1-180>]", "radius server host 1.1.1.1 key k timeout 5 priority 1"),
        ("show fa agent / show fa interface", "show fa interface"),
        ('mlt <id> enable name "<name>"', 'mlt 1 enable name "to core"'),
        ("macsec mka enable (interface)", "macsec mka enable"),
        ("snmp-server user <user> ...", 'snmp-server user "nms" group "g" sha 0x12 aes 0x34'),
    ],
)
def test_lines_match_their_syntax(syntax, line):
    assert matches(syntax, line)


@pytest.mark.parametrize(
    "syntax, line",
    [
        ("show isis adjacencies [verbose]", "show isis adjacencies verbose extra"),
        ("tacacs authentication {cli | web}", "tacacs authentication"),
        ("radius server host <ip> [priority <1-10>] [timeout <1-180>]", "radius server host 1.1.1.1 priority 1 priority 2"),
    ],
)
def test_lines_that_do_not_match(syntax, line):
    assert matches(syntax, line) is None


def test_values_are_captured_by_name_and_filled_into_a_template():
    found = matches("radius server host <ip> ... used-by <app> ...", "radius server host 10.0.0.5 key **** used-by eapol priority 1")
    assert found.values == {"ip": "10.0.0.5", "app": "eapol"}
    assert fill("no radius server host <ip> used-by <app>", found.values) == "no radius server host 10.0.0.5 used-by eapol"


def test_more_keywords_and_full_words_rank_higher():
    generic = matches("snmp-server user <user> ...", "snmp-server user engine-id 8000 nms")
    specific = matches("snmp-server user engine-id ...", "snmp-server user engine-id 8000 nms")
    assert specific.rank > generic.rank
    full = matches("show isis", "show isis", abbreviations=True)
    short = matches("show isis", "sh isis", abbreviations=True)
    assert full.rank > short.rank


def test_abbreviations_and_partial_lines_only_when_asked():
    assert matches("show isis adjacencies", "sh isis adj") is None
    assert matches("show isis adjacencies", "sh isis adj", abbreviations=True)
    assert matches("show isis", "show isis adjacencies") is None
    assert matches("show isis", "show isis adjacencies", partial=True)


def test_quoted_values_stay_one_token():
    assert tokens('snmp-server location "Building A, Room 1"') == ["snmp-server", "location", '"Building A, Room 1"']
    assert slots("no snmp-server host <ip> v2c <name>") == ["ip", "name"]


@pytest.mark.parametrize("broken", ["show [verbose", "show {a | b", "show ]", ""])
def test_broken_notation_is_reported(broken):
    with pytest.raises(SyntaxParseError):
        compile_patterns(broken)
    assert try_compile(broken) == ()
