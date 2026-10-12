import pytest

from netcheat.loader import load_library
from netcheat.search import Filters, normalize, search_commands, search_concepts, search_flows, suggest, words


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


def test_since_filter_only_returns_newer_commands(library):
    results = search_commands(library.commands, [], Filters(since="9.4"))
    assert results and all(c.since.startswith("9.4") for c in results)


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
