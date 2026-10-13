import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from netcheat.cli import _parser, main
from netcheat.completion import candidates
from netcheat.loader import load_library


@pytest.fixture(scope="module")
def complete():
    parser, library = _parser(), load_library()
    return lambda *words: candidates(parser, lambda: library, list(words), len(words) - 1)


@pytest.mark.parametrize(
    "words, expected",
    [
        (("",), {"browse", "fix", "flow", "search", "topics"}),
        (("flow", "vi"), {"vist-smlt-problem"}),
        (("-t", "ma"), {"macsec"}),
        (("isis", "-p", ""), {"fe", "srx", "fabric-engine", "junos-srx"}),
        (("isis", "-k", ""), {"show", "config", "action", "clear"}),
        (("isis", "-s", ""), {"9.2", "9.3", "9.4"}),
        (("adja",), {"adjacencies"}),
        (("concept", "nick"), {"nickname"}),
        (("completion", ""), {"bash", "zsh"}),
        (("show", "isis", "--li"), {"--limit"}),
    ],
)
def test_candidates(complete, words, expected):
    assert expected <= set(complete(*words))


def test_empty_first_word_offers_only_subcommands(complete):
    assert all(not candidate.startswith("-") and " " not in candidate for candidate in complete(""))
    assert len(complete("")) < 15


def test_hidden_command_prints_candidates(capsys):
    assert main(["__complete", "1", "flow", "vist"]) == 0
    assert capsys.readouterr().out.strip() == "vist-smlt-problem"


def test_hidden_command_ignores_bad_input():
    assert main(["__complete", "x"]) == 1


@pytest.mark.skipif(not shutil.which("bash"), reason="bash not installed")
def test_bash_script_completes(capsys, tmp_path):
    main(["completion", "bash"])
    script = capsys.readouterr().out
    ncs = Path(sys.executable).with_name("ncs")
    test = f'ncs() {{ "{ncs}" "$@"; }}\n{script}COMP_WORDS=(ncs flow vi); COMP_CWORD=2; _ncs_complete; echo "${{COMPREPLY[@]}}"'
    result = subprocess.run(["bash", "-c", test], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "vist-smlt-problem"


def test_options_and_choices_complete_without_loading_data():
    def no_data():
        raise AssertionError("data should not be loaded")

    assert "--limit" in candidates(_parser(), no_data, ["isis", "--li"], 1)
    assert "zsh" in candidates(_parser(), no_data, ["completion", "z"], 1)
    assert "srx" in candidates(_parser(), no_data, ["isis", "-p", "s"], 2)


def test_fix_completes_problem_vocabulary(complete):
    assert "access" in complete("fix", "acc")
    assert "access-diffserv" not in complete("fix", "acc")
