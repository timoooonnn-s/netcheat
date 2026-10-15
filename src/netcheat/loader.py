"""Load the YAML data files into a validated Library.

Layout of the data directory:
    <platform>/<topic>.yaml   one topic per file, e.g. fabric-engine/spbm-isis.yaml
    flows.yaml                troubleshooting flows
    changes.yaml              change workflows: remove, replace and re-add a configuration cleanly
    concepts.yaml             short concept explanations
    synonyms.yaml             words that mean the same thing, for `ncs fix`
"""

from __future__ import annotations

import os
from dataclasses import MISSING, fields
from pathlib import Path
from typing import Any, TypeVar

import yaml

from netcheat.models import PLATFORMS, Command, Concept, Flow, Library, Step, SynonymGroup, Topic, UndoRule

DATA_DIR = Path(os.environ.get("NETCHEAT_DATA", Path(__file__).parent / "data"))
_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)  # the C parser is ~10x faster, if PyYAML has it

T = TypeVar("T")


class DataError(Exception):
    """A data file is malformed. The message names the file and the entry."""


def load_library(root: Path = DATA_DIR) -> Library:
    if not root.is_dir():
        raise DataError(f"data folder not found: {root} (check NETCHEAT_DATA)")
    topics = tuple(
        load_topic(path, platform)
        for platform in PLATFORMS
        for path in sorted((root / platform).glob("*.yaml"))
    )
    _ensure_unique([topic.slug for topic in topics], "topic file name")

    flows = tuple(
        _build_flow(raw, f"{file.name} #{i}", kind)
        for file, kind in ((root / "flows.yaml", "troubleshoot"), (root / "changes.yaml", "change"))
        for i, raw in enumerate(_list(_read(file).get("flows"), f"{file.name}: flows"), 1)
    )
    concepts_file = root / "concepts.yaml"
    concepts = tuple(
        _build(Concept, raw, f"{concepts_file.name} #{i}")
        for i, raw in enumerate(_list(_read(concepts_file).get("concepts"), f"{concepts_file.name}: concepts"), 1)
    )
    synonyms_file = root / "synonyms.yaml"
    synonyms = tuple(
        _build(SynonymGroup, {"words": raw}, f"{synonyms_file.name} #{i}")
        for i, raw in enumerate(_list(_read(synonyms_file).get("groups"), f"{synonyms_file.name}: groups"), 1)
    )
    _ensure_unique([flow.id for flow in flows], "flow id")
    return Library(topics, flows, concepts, synonyms)


def load_topic(path: Path, platform: str) -> Topic:
    doc = _read(path)
    for key in ("title", "commands"):
        if key not in doc:
            raise DataError(f"{path.name}: missing top-level key '{key}'")
    commands = tuple(
        _build_command(raw, f"{path.name} #{i}", platform, path.stem)
        for i, raw in enumerate(_list(doc["commands"], f"{path.name}: commands"), 1)
    )
    return Topic(path.stem, doc["title"], platform, doc.get("description", ""), path, commands)


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        doc = yaml.load(path.read_text(encoding="utf-8"), Loader=_YAML_LOADER)
    except yaml.YAMLError as err:
        raise DataError(f"{path.name}: invalid YAML: {err}") from err
    if doc is not None and not isinstance(doc, dict):
        raise DataError(f"{path.name}: top level must be a mapping")
    return doc or {}


def _build_command(raw: Any, where: str, platform: str, topic: str) -> Command:
    raw = _mapping(raw, where)
    rules = tuple(
        _build(UndoRule, rule, f"{where} undo {i}") for i, rule in enumerate(_list(raw.get("undo"), f"{where}: undo"), 1)
    )
    return _build(Command, {**raw, "undo": rules}, where, platform=platform, topic=topic)


def _build_flow(raw: Any, where: str, kind: str) -> Flow:
    raw = _mapping(raw, where)
    steps = tuple(
        _build(Step, step, f"{where} step {i}") for i, step in enumerate(_list(raw.get("steps"), f"{where}: steps"), 1)
    )
    values = {str(name): _text_item(value) for name, value in _mapping(raw.get("values") or {}, f"{where}: values").items()}
    flow = _build(Flow, {**raw, "steps": steps, "values": values}, where, kind=kind)
    try:
        flow.check_values()
    except ValueError as err:
        raise DataError(f"{where} ({flow.id}): {err}") from err
    return flow


def _build(cls: type[T], raw: Any, where: str, **context: str) -> T:
    """Create a dataclass from a YAML mapping, rejecting unknown or missing fields."""
    raw = _mapping(raw, where)
    allowed = {f.name for f in fields(cls)} - set(context)
    required = {f.name for f in fields(cls) if f.default is MISSING} - set(context)

    unknown, missing = set(raw) - allowed, required - set(raw)
    if unknown:
        raise DataError(f"{where}: unknown field(s): {', '.join(sorted(unknown))}")
    if missing:
        raise DataError(f"{where}: missing field(s): {', '.join(sorted(missing))}")

    values = {key: _clean(value) for key, value in raw.items()}
    label = values.get("cmd") or values.get("title") or values.get("term") or ""
    try:
        return cls(**values, **context)
    except (TypeError, ValueError) as err:
        raise DataError(f"{where} ({label}): {err}") from err


def _list(value: Any, where: str) -> list[Any]:
    """A YAML list; an empty key (None) counts as an empty list."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise DataError(f"{where}: expected a list, got {type(value).__name__}")
    return value


def _mapping(raw: Any, where: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DataError(f"{where}: expected a mapping, got {type(raw).__name__}")
    return raw


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return tuple(_text_item(item) for item in value)
    return value


def _text_item(item: Any) -> Any:
    """Whole numbers (tags: [5520], values: {vlan: 100}) are fine as text; other non-strings stay and fail validation."""
    is_whole_number = isinstance(item, int) and not isinstance(item, bool)
    return str(item) if is_whole_number else _clean(item)


def _ensure_unique(values: list[str], what: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise DataError(f"duplicate {what}: {value}")
        seen.add(value)
