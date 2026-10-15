import pytest

from netcheat.loader import DataError, load_library


def write_topic(root, body, name="test.yaml"):
    folder = root / "fabric-engine"
    folder.mkdir(exist_ok=True)
    (folder / name).write_text(body, encoding="utf-8")


VALID_ENTRY = """\
title: Test
commands:
  - cmd: show isis
    desc: Global IS-IS settings.
    kind: show
    mode: User EXEC
"""


def test_valid_topic_loads_with_context(tmp_path):
    write_topic(tmp_path, VALID_ENTRY)
    command = load_library(tmp_path).commands[0]
    assert (command.topic, command.platform) == ("test", "fabric-engine")


@pytest.mark.parametrize(
    "extra, message",
    [
        ("    colour: red\n", "unknown field"),
        ("    since: 9.4\n", "quoted version"),
        ("    tags: isis\n", "must be a list"),
    ],
)
def test_invalid_fields_are_reported(tmp_path, extra, message):
    write_topic(tmp_path, VALID_ENTRY + extra)
    with pytest.raises(DataError, match=message):
        load_library(tmp_path)


def test_missing_required_field_is_reported(tmp_path):
    write_topic(tmp_path, VALID_ENTRY.replace("    kind: show\n", ""))
    with pytest.raises(DataError, match="missing field.*kind"):
        load_library(tmp_path)


def test_invalid_kind_names_the_command(tmp_path):
    write_topic(tmp_path, VALID_ENTRY.replace("kind: show", "kind: shwo"))
    with pytest.raises(DataError, match=r"test.yaml #1 \(show isis\)"):
        load_library(tmp_path)


def test_broken_yaml_names_the_file(tmp_path):
    write_topic(tmp_path, VALID_ENTRY + "    cisco: dir flash:\n")
    with pytest.raises(DataError, match="test.yaml: invalid YAML"):
        load_library(tmp_path)


def test_yaml_special_words_in_lists_are_rejected(tmp_path):
    write_topic(tmp_path, VALID_ENTRY + "    tags: [static, null]\n")
    with pytest.raises(DataError, match="must be text"):
        load_library(tmp_path)


@pytest.mark.parametrize("flows", ["flows:\n", "flows:\n  - id: x\n    title: X\n    platform: fabric-engine\n    summary: s\n    steps:\n"])
def test_empty_lists_are_allowed(tmp_path, flows):
    write_topic(tmp_path, VALID_ENTRY)
    (tmp_path / "flows.yaml").write_text(flows)
    load_library(tmp_path)


def test_non_list_value_is_reported(tmp_path):
    write_topic(tmp_path, VALID_ENTRY)
    (tmp_path / "concepts.yaml").write_text("concepts: oops\n")
    with pytest.raises(DataError, match="concepts.yaml: concepts: expected a list"):
        load_library(tmp_path)


def test_missing_data_folder_is_reported(tmp_path):
    with pytest.raises(DataError, match="data folder not found"):
        load_library(tmp_path / "nope")


FLOW = "flows:\n  - id: x\n    title: X\n    platform: fabric-engine\n    summary: s\n    steps:\n      - title: t\n        cmds: [show isis]\n"


def test_flow_kind_comes_from_the_file(tmp_path):
    write_topic(tmp_path, VALID_ENTRY)
    (tmp_path / "flows.yaml").write_text(FLOW)
    (tmp_path / "changes.yaml").write_text(FLOW.replace("id: x", "id: y"))
    assert [(flow.id, flow.kind) for flow in load_library(tmp_path).flows] == [("x", "troubleshoot"), ("y", "change")]


def test_flow_kind_in_yaml_is_rejected(tmp_path):
    write_topic(tmp_path, VALID_ENTRY)
    (tmp_path / "changes.yaml").write_text(FLOW + "    kind: change\n")
    with pytest.raises(DataError, match="unknown field.*kind"):
        load_library(tmp_path)


def test_flow_ids_are_unique_across_both_files(tmp_path):
    write_topic(tmp_path, VALID_ENTRY)
    (tmp_path / "flows.yaml").write_text(FLOW)
    (tmp_path / "changes.yaml").write_text(FLOW)
    with pytest.raises(DataError, match="duplicate flow id: x"):
        load_library(tmp_path)
