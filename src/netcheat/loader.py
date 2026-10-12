"""Load the YAML data files into a validated Library.

Layout of the data directory:
    <platform>/<topic>.yaml   one topic per file, e.g. fabric-engine/spbm-isis.yaml
    flows.yaml                troubleshooting flows
    concepts.yaml             short concept explanations
"""

from __future__ import annotations

import os
from dataclasses import MISSING, fields
from pathlib import Path
from typing import Any, TypeVar

import yaml

from netcheat.models import PLATFORMS, Command, Concept, Flow, Library, Step, Topic

DATA_DIR = Path(os.environ.get("NETCHEAT_DATA", Path(__file__).parent / "data"))

T = TypeVar("T")


class DataError(Exception):
    """A data file is malformed. The message names the file and the entry."""


def load_library(root: Path = DATA_DIR) -> Library:
    topics = tuple(
        load_topic(path, platform)
        for platform in PLATFORMS
        for path in sorted((root / platform).glob("*.yaml"))
    )
    _ensure_unique([topic.slug for topic in topics], "topic file name")

    flows_file, concepts_file = root / "flows.yaml", root / "concepts.yaml"
    flows = tuple(
        _build_flow(raw, f"{flows_file.name} #{i}") for i, raw in enumerate(_read(flows_file).get("flows", []), 1)
    )
    concepts = tuple(
        _build(Concept, raw, f"{concepts_file.name} #{i}")
        for i, raw in enumerate(_read(concepts_file).get("concepts", []), 1)
    )
    _ensure_unique([flow.id for flow in flows], "flow id")
    return Library(topics, flows, concepts)


def load_topic(path: Path, platform: str) -> Topic:
    doc = _read(path)
    for key in ("title", "commands"):
        if key not in doc:
            raise DataError(f"{path.name}: missing top-level key '{key}'")
    commands = tuple(
        _build(Command, raw, f"{path.name} #{i}", platform=platform, topic=path.stem)
        for i, raw in enumerate(doc["commands"] or [], 1)
    )
    return Topic(path.stem, doc["title"], platform, doc.get("description", ""), path, commands)


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as err:
        raise DataError(f"{path.name}: invalid YAML: {err}") from err
    if doc is not None and not isinstance(doc, dict):
        raise DataError(f"{path.name}: top level must be a mapping")
    return doc or {}


def _build_flow(raw: Any, where: str) -> Flow:
    raw = _mapping(raw, where)
    steps = tuple(_build(Step, step, f"{where} step {i}") for i, step in enumerate(raw.get("steps", []), 1))
    return _build(Flow, {**raw, "steps": steps}, where)


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


def _mapping(raw: Any, where: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DataError(f"{where}: expected a mapping, got {type(raw).__name__}")
    return raw


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return tuple(_clean(item) for item in value)
    return value


def _ensure_unique(values: list[str], what: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise DataError(f"duplicate {what}: {value}")
        seen.add(value)
