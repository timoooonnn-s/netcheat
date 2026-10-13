import pytest

from netcheat.cli import main
from netcheat.loader import load_library
from netcheat.models import SynonymGroup
from netcheat.search import diagnose, problem_query


@pytest.fixture(scope="module")
def library():
    return load_library()


@pytest.mark.parametrize(
    "problem, flow",
    [
        ("clients get no ip address", "client-no-connectivity"),
        ("laptop cant reach anything", "client-no-connectivity"),
        ("users on floor 3 have no internet", "client-no-connectivity"),
        ("phone works but the pc behind it does not", "nac-auth-failure"),
        ("dot1x login fails for a laptop", "nac-auth-failure"),
        ("printer ends up in guest vlan", "nac-auth-failure"),
        ("isis neighbor stuck in init", "isis-adjacency-down"),
        ("uplink to core shows adjacency init", "isis-adjacency-down"),
        ("two buildings same vlan cannot ping each other", "l2vsn-not-working"),
        ("route missing in vrf on remote site", "l3vsn-route-missing"),
        ("subnet from branch not in routing table", "l3vsn-route-missing"),
        ("vist is down", "vist-smlt-problem"),
        ("lacp bundle only comes up on one core switch", "vist-smlt-problem"),
        ("access point does not come up on autosense port", "autosense-onboarding"),
        ("new switch not joining the fabric", "autosense-onboarding"),
        ("whole network slow, maybe broadcast storm", "loop-broadcast-storm"),
        ("port keeps flapping", "port-errors-flapping"),
        ("sfp shows low light and errors", "port-errors-flapping"),
        ("encrypted link between cores has no traffic after key change", "macsec-link-down"),
        ("cli lagging and ssh slow on switch", "switch-slow-high-cpu"),
        ("juniper firewall not forwarding traffic", "srx-routed-traffic-dropped"),
    ],
)
def test_problem_descriptions_find_the_right_flow(library, problem, flow):
    assert diagnose(library, problem).flows[0].id == flow


def test_synonym_phrases_are_recognized_and_filler_is_dropped(library):
    query, understood = problem_query("The AP keeps flapping", library.synonyms)
    assert understood == ("ap", "flap")
    assert len(query.groups) == 2


def test_multi_word_phrases_do_not_add_generic_words(library):
    query, understood = problem_query("pc gets no ip", library.synonyms)
    assert "no ip" in understood
    assert not any("ip" in group or "no" in group for group in query.groups)


def test_helpful_commands_need_two_aspects_of_the_problem(library):
    assert "show users" not in [c.cmd for c in diagnose(library, "users on floor 3 have no internet").commands]


def test_platform_filter_applies(library):
    diagnosis = diagnose(library, "ospf neighbor down", platform="junos-srx")
    assert all(item.platform == "junos-srx" for item in [*diagnosis.flows, *diagnosis.commands])


def test_fix_command_prints_the_flow(capsys):
    assert main(["fix", "clients", "get", "no", "ip"]) == 0
    assert "Client has no network connectivity" in capsys.readouterr().out


def test_fix_without_match_returns_1(capsys):
    assert main(["fix", "blubber"]) == 1


def test_vague_problems_show_a_limited_number_of_flows(library):
    assert 1 <= len(diagnose(library, "port problem").flows) <= 4


def test_group_of_only_stopwords_adds_no_query_group():
    query, _ = problem_query("still no access", [SynonymGroup(("no", "no access"))])
    assert query.groups == ()
