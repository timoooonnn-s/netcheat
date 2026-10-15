import io
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from netcheat.add import append_command
from netcheat.cli import _default_docs_dir, main
from netcheat.loader import DataError, load_library
from netcheat.markdown import HEADER


@pytest.mark.parametrize(
    "argv",
    [[], ["isid"], ["search", "flow"], ["-t", "macsec"], ["-r", "-p", "srx"], ["vist-smlt-problem"], ["nickname"],
     ["list"], ["list", "flows"], ["list", "concepts"], ["list", "favourites"], ["list", "recent"], ["tip"]],
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
    assert len(list(tmp_path.glob("*.md"))) == len(library.topics) + 4  # + flows, changes, concepts, README
    changes = (tmp_path / "changes.md").read_text()
    assert "radius-replace" in changes and "vist-smlt-problem" not in changes


def test_change_workflow_marks_config_commands_and_cautions(capsys):
    assert main(["radius-replace"]) == 0
    out = capsys.readouterr().out
    assert "⇄ Replace or remove RADIUS" in out
    assert "✎ no radius server host 10.0.0.50 used-by eapol" in out
    assert "» show radius-server" in out
    assert "▲" in out


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


def test_short_missing_data_path_gives_a_data_error():
    env = {**os.environ, "NETCHEAT_DATA": "/nope"}  # used to crash while building the parser
    result = subprocess.run([sys.executable, "-m", "netcheat", "list"], env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert "data folder not found" in result.stdout


def test_build_md_default_is_this_checkout():
    assert _default_docs_dir() == Path(__file__).resolve().parents[1] / "docs" / "cheatsheet"


def test_exact_concept_opens_it_above_the_commands(capsys):
    assert main(["nickname"]) == 0
    out = capsys.readouterr().out
    assert out.index("◇ Nickname") < out.index("command(s)")


def test_set_fills_in_flow_values(capsys):
    assert main(["radius-replace", "--set", "new_radius=192.0.2.10"]) == 0
    out = capsys.readouterr().out
    assert "radius server host 192.0.2.10 key <secret> used-by eapol" in out
    assert "new_radius=192.0.2.10" in out


@pytest.mark.parametrize(
    "argv, message",
    [
        (["radius-replace", "--set", "colour=red"], "has no value colour"),
        (["isid", "--set", "port=1/7"], "only applies when opening a flow"),
        (["export", "nope"], "No flow 'nope'"),
        (["export", "radius-replace", "--step", "99"], "has steps 1 to"),
    ],
)
def test_wrong_input_is_explained(argv, message, capsys):
    assert main(argv) == 2
    assert message in capsys.readouterr().out


def test_set_needs_name_and_value():
    with pytest.raises(SystemExit):
        main(["radius-replace", "--set", "port"])


def test_export_text_has_values_steps_and_rollback(capsys):
    assert main(["export", "radius-replace", "--set", "new_radius=192.0.2.10"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Replace or remove RADIUS servers")
    assert "     no radius server host 10.0.0.50 used-by eapol" in out
    rollback = out.split("Rollback")[1]
    assert "no radius server host 192.0.2.10 used-by eapol" in rollback
    assert "10.0.0.50" not in rollback  # the old servers are restored from the original config, not by rollback


def test_export_markdown_and_commands_only(capsys):
    assert main(["export", "snmp-replace", "--md"]) == 0
    assert capsys.readouterr().out.startswith("# Replace or remove SNMP")
    assert main(["export", "radius-replace", "--step", "5", "--set", "old_radius=192.0.2.9"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "no radius server host 192.0.2.9 used-by eapol"


def test_what_explains_a_line(capsys):
    assert main(["what", "radius", "server", "host", "10.0.0.5", "key", "x", "used-by", "eapol"]) == 0
    out = capsys.readouterr().out
    assert "radius server host <ip> key <secret> used-by eapol" in out
    assert "Remove with: no radius server host 10.0.0.5 used-by eapol" in out


def test_what_reads_several_lines_from_stdin(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("sh isis adj\nno slpp enable\nsomething odd\n"))
    assert main(["what"]) == 0
    out = capsys.readouterr().out
    assert "show isis adjacencies [verbose]" in out
    assert "This line removes the setting below" in out
    assert "No entry matches this command" in out


def test_undo_from_a_file(tmp_path, capsys):
    config = tmp_path / "radius.txt"
    config.write_text("# RADIUS\nradius enable\nradius server host 10.0.0.5 key **** used-by eapol\nspbm 1 nick-name 1.11.11\n")
    assert main(["undo", str(config)]) == 0
    out = capsys.readouterr().out
    assert out.index("no radius server host 10.0.0.5 used-by eapol") < out.index("no radius enable")
    assert "spbm 1 nick-name 1.11.11" in out.split("No rule for these lines")[1]


def test_undo_plain_prints_only_safe_commands(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("syslog host 1 address 10.0.0.6\nssh\n"))
    assert main(["undo", "--plain"]) == 0
    assert capsys.readouterr().out == "no syslog host 1\n"  # `no ssh` needs a check first, so it is not in the block


def test_undo_of_unknown_lines_returns_1(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("spbm 1 nick-name 1.11.11\n"))
    assert main(["undo"]) == 1


def test_release_hides_newer_commands(capsys, monkeypatch):
    assert main(["clilog", "-R", "9.3"]) == 1  # clilog enable came with 9.4
    monkeypatch.setenv("NCS_RELEASE", "9.4")
    assert main(["clilog"]) == 0


def test_opened_flows_and_concepts_become_recent(capsys):
    main(["radius-replace"])
    main(["nickname"])
    capsys.readouterr()
    main(["list", "recent"])
    out = capsys.readouterr().out
    assert out.index("Nickname") < out.index("radius-replace")
