from dataclasses import replace

import pytest
import yaml

from netcheat.add import append_command
from netcheat.cli import main
from netcheat.loader import DataError, load_library
from netcheat.markdown import HEADER


@pytest.mark.parametrize(
    "argv",
    [[], ["isid"], ["search", "flow"], ["-t", "macsec"], ["-r", "-p", "srx"], ["flow"], ["flow", "vist-smlt-problem"],
     ["concept", "dvr"], ["tip"]],
)
def test_commands_succeed(argv, capsys):
    assert main(argv) == 0
    assert capsys.readouterr().out


def test_no_match_returns_1_and_suggests(capsys):
    assert main(["adjacensies"]) == 1
    assert "Did you mean" in capsys.readouterr().out


def test_build_md_writes_one_page_per_topic(tmp_path):
    assert main(["build-md", "-o", str(tmp_path)]) == 0
    library = load_library()
    assert len(list(tmp_path.glob("*.md"))) == len(library.topics) + 3


def test_append_command_keeps_file_valid_and_reverts_on_error(tmp_path):
    folder = tmp_path / "fabric-engine"
    folder.mkdir()
    path = folder / "mine.yaml"
    original = "# my notes\ntitle: Mine\ncommands:\n  - cmd: show isis\n    desc: x\n    kind: show\n    mode: User EXEC\n"
    path.write_text(original)
    topic = load_library(tmp_path).topics[0]

    updated = append_command(topic, {"cmd": "show isis spbm", "desc": "y", "kind": "show", "mode": "User EXEC"})
    assert [c.cmd for c in updated.commands] == ["show isis", "show isis spbm"]
    assert path.read_text().startswith("# my notes")
    assert yaml.safe_load(path.read_text())["title"] == "Mine"

    before = path.read_text()
    with pytest.raises(DataError):
        append_command(updated, {"cmd": "bad", "desc": "z", "kind": "nope", "mode": "User EXEC"})
    assert path.read_text() == before


@pytest.mark.parametrize("argv", [["isis", "-s", "9.x"], ["isis", "-n", "0"], ["isis", "-n", "-1"]])
def test_invalid_option_values_are_rejected(argv):
    with pytest.raises(SystemExit) as exit_info:
        main(argv)
    assert exit_info.value.code == 2


def test_limit_shows_n_of_total(capsys):
    assert main(["isis", "-n", "1"]) == 0
    assert "1 of " in capsys.readouterr().out


def test_tip_without_gems_returns_1(monkeypatch):
    library = load_library()
    plain = [replace(topic, commands=tuple(replace(c, rare=False) for c in topic.commands)) for topic in library.topics]
    monkeypatch.setattr("netcheat.cli.load_library", lambda: replace(library, topics=tuple(plain)))
    assert main(["tip"]) == 1


def test_related_hints_respect_the_platform_filter(capsys):
    main(["route", "-p", "srx"])
    assert "l3vsn-route-missing" not in capsys.readouterr().out


def test_build_md_removes_stale_generated_pages(tmp_path):
    (tmp_path / "old-topic.md").write_text(HEADER + "old")
    (tmp_path / "notes.md").write_text("hand written")
    main(["build-md", "-o", str(tmp_path)])
    assert not (tmp_path / "old-topic.md").exists()
    assert (tmp_path / "notes.md").exists()
