import pytest

from netcheat.loader import load_library
from netcheat.search import (
    Filters,
    normalize,
    prose_only_matches,
    search_commands,
    search_concepts,
    search_flows,
    suggest,
    words,
)


@pytest.fixture(scope="module")
def library():
    return load_library()


def first(library, *terms, **filters):
    return search_commands(library.commands, terms, Filters(**filters))[0].cmd


def test_normalize_ignores_case_and_separators():
    assert normalize("I-SID") == normalize("isid") == "isid"


def test_words_include_compounds_and_parts():
    assert {"ipunicastfib", "unicastfib", "ip", "unicast", "fib"} <= words("show isis spbm ip-unicast-fib")


def test_hyphenless_term_finds_hyphenated_command(library):
    assert first(library, "isid").startswith("show i-sid")


def test_prefix_terms_rank_the_matching_command_first(library):
    assert first(library, "isis", "adj") == "show isis adjacencies [verbose]"


def test_all_terms_must_match(library):
    assert search_commands(library.commands, ["isis", "poe"]) == []


def test_filters_restrict_results(library):
    results = search_commands(library.commands, [], Filters(platform="junos-srx", kind="show"))
    assert results and all(c.platform == "junos-srx" and c.kind == "show" for c in results)


def test_topic_filter_matches_one_topic_exactly(library):
    """`-t system` is the Fabric Engine topic, never also srx-system: a mixed list invites
    pasting Junos syntax into a VOSS switch."""
    results = search_commands(library.commands, [], Filters(topic="system"))
    assert results and {c.topic for c in results} == {"system"}
    assert search_commands(library.commands, [], Filters(topic="s")) == []


def test_suggest_offers_close_spellings(library):
    assert "adjacencies" in suggest(library.commands, ["adjacensies"])


def test_flows_and_concepts_are_searchable(library):
    assert search_flows(library.flows, ["vist"])[0].id == "vist-smlt-problem"
    assert search_flows(library.flows, ["no-connectivity"])[0].id == "client-no-connectivity"
    assert search_concepts(library.concepts, ["nickname"])[0].term == "Nickname"


def test_pasted_command_with_brackets_finds_itself(library):
    assert first(library, "show", "isis", "adjacencies", "[verbose]") == "show isis adjacencies [verbose]"


def test_punctuation_only_query_matches_nothing(library):
    assert search_commands(library.commands, ["[]"]) == []


def test_flow_search_uses_symptoms(library):
    assert search_flows(library.flows, ["radius", "reject"])[0].id == "nac-auth-failure"


def test_a_word_only_in_the_notes_is_not_a_result(library):
    """`ncs radius` used to return `show i-sid`, because its notes mention RADIUS in passing. Only what a
    command is about counts: its syntax, tags and description."""
    results = search_commands(library.commands, ["radius"])
    assert results
    for command in results:
        haystack = " ".join((command.cmd, " ".join(command.tags), command.desc)).lower()
        assert "radius" in haystack, f"{command.cmd} matched on prose only"
    assert not any(c.cmd == "show i-sid [<isid>]" for c in results)


def test_the_topic_name_is_not_a_relevance_signal(library):
    """Searching a word that appears in a topic slug must not return that whole topic: `-t` is the filter."""
    results = search_commands(library.commands, ["radius"])
    assert not any(c.cmd.startswith("show nodealias") for c in results)
    assert all(c.topic == "nac-eap-radius" for c in library.commands if c.cmd.startswith("show nodealias"))


def test_prose_search_is_available_on_request(library):
    """The capability is not lost, just off by default, and the search says how many it is holding back."""
    plain = search_commands(library.commands, ["radius"])
    with_prose = search_commands(library.commands, ["radius"], in_prose=True)
    assert len(with_prose) > len(plain)
    assert set(plain) < set(with_prose)
    assert prose_only_matches(library.commands, ["radius"])


def test_short_query_words_must_match_a_whole_word(library):
    """A two-letter word is not an abbreviation of everything: `ip` must not pull in every ipfix keyword."""
    assert all("ipfix" not in c.cmd for c in search_commands(library.commands, ["ip"]) if "ipfix" not in c.desc.lower())
    assert search_commands(library.commands, ["adj"]), "three letters still match as a prefix"


def test_the_command_the_query_names_ranks_first(library):
    assert search_commands(library.commands, ["radius"])[0].cmd == "show radius"
    assert search_commands(library.commands, ["isis", "adjacencies"])[0].cmd == "show isis adjacencies [verbose]"
