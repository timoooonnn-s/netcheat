"""`ncs export`: a flow as a plain-text or Markdown document, e.g. for a change ticket."""

from __future__ import annotations

from netcheat.config import rollback
from netcheat.markdown import ROLLBACK_NOTE, flow_markdown
from netcheat.models import PLATFORMS, Flow, Library


def export_flow(library: Library, flow: Flow, fmt: str = "text") -> str:
    """The flow as a document. `flow` should already have its values filled in (Flow.with_values)."""
    return (flow_markdown(flow, library) if fmt == "md" else flow_text(flow, library)) + "\n"


def flow_text(flow: Flow, library: Library) -> str:
    """Plain text that survives any ticket system: no markup, commands indented on their own lines.

    Carries the same facts as `flow_markdown`, so a ticket does not depend on which format was exported.
    """
    lines = [flow.title, "=" * len(flow.title), "", f"{PLATFORMS[flow.platform]} · id: {flow.id}", "", flow.summary, ""]
    if flow.values:
        lines += ["Values: " + ", ".join(f"{name}={value}" for name, value in flow.values.items()), ""]
    if flow.symptoms:
        lines += ["Typical symptoms: " + "; ".join(flow.symptoms) + ".", ""]
    for number, step in enumerate(flow.steps, 1):
        lines.append(f"{number}. {step.title}")
        lines += [f"     {cmd}" for cmd in step.cmds]
        if step.look_for:
            lines.append(f"   Check: {step.look_for}")
        if step.caution:
            lines.append(f"   Caution: {step.caution}")
        lines.append("")
    if flow.kind == "change":
        back = rollback(library, flow)
        lines += ["Rollback", "--------", ROLLBACK_NOTE, "", *(f"     {cmd}" for cmd in back.commands), ""]
        lines += [f"   Not in the block above, check first: {r.remove or r.line}: {r.note}" for r in back.flagged]
    return "\n".join(lines).rstrip()
