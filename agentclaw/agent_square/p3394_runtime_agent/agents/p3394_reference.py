"""Local P3394 draft reference helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


P3394_REFERENCE_FILENAME = "P3394-v0.9.0-combined(2).md"

P3394_INTERNAL_ROLES = [
    (
        "P3394 Planner",
        "turn the user request into a manifest/session/capability-aware plan before execution",
    ),
    (
        "P3394 Researcher",
        "inspect local documents, Markdown/PDF files, project structure, and web sources when evidence is needed",
    ),
    (
        "P3394 Executor",
        "run tools, commands, file edits, and project operations through AgentClaw runtime tools",
    ),
    (
        "P3394 Reviewer",
        "check command results, changed files, risks, missing evidence, and conformance gaps before final output",
    ),
]


def find_p3394_reference_path(start: Path | None = None) -> Path | None:
    """Find the local P3394 draft by walking upward from this module."""
    anchor = (start or Path(__file__)).resolve()
    candidates = [anchor.parent, *anchor.parents]
    for parent in candidates:
        candidate = parent / P3394_REFERENCE_FILENAME
        if candidate.exists():
            return candidate
    return None


@lru_cache(maxsize=1)
def load_p3394_reference_text() -> tuple[Path | None, str]:
    path = find_p3394_reference_path()
    if not path:
        return None, ""
    try:
        return path, path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return path, ""


def _clean_line(line: str) -> str:
    return " ".join(line.replace("**", "").replace("`", "").split())


def _line_containing(text: str, *needles: str) -> str:
    lowered_needles = [needle.lower() for needle in needles]
    for raw_line in text.splitlines():
        line = _clean_line(raw_line)
        lowered = line.lower()
        if line and all(needle in lowered for needle in lowered_needles):
            return line
    return ""


def _fallback_core_points() -> list[str]:
    return [
        "Agent manifest: the public contract for identity, channels, relationships, capabilities, security policy, sessions, and conformance.",
        "Channel adapter: the runtime boundary that listens, authenticates, resolves principals/relationships, validates semantic blocks, normalizes to UMF, and delivers to handle_message.",
        "Universal Message Format: the transport-agnostic envelope carrying message type, sender/recipient, body, metadata, and session identity.",
        "Session model: owner-capable agents manage lifecycle, context variables, participants, budgets, memory pointers, and child sessions.",
        "Security: relationship-based authorization and the non-escalation invariant prevent tools or sub-agents from exceeding caller privileges.",
        "Conformance: Level 1 establishes handle_message plus adapter/manifest, Level 2 adds relationships/security/session support, Level 3 adds elevation, extensions, delegation provenance, and audit.",
    ]


def _extract_core_points(text: str) -> list[str]:
    if not text:
        return _fallback_core_points()

    extracted = [
        _line_containing(text, "Agent Manifest", "public contract"),
        _line_containing(text, "Channel and Channel Adapter", "adapter contract"),
        _line_containing(text, "Universal Message Format", "envelope"),
        _line_containing(text, "Session", "Session Context"),
        _line_containing(text, "non-escalation invariant"),
        _line_containing(text, "Conformance Levels"),
    ]
    fallbacks = _fallback_core_points()
    return [point or fallbacks[index] for index, point in enumerate(extracted)]


def build_p3394_reference_prompt() -> str:
    """Build a compact startup prompt from the local P3394 draft."""
    path, text = load_p3394_reference_text()
    title = _line_containing(text, "IEEE P3394") or "IEEE P3394 Draft Specification"
    source = str(path) if path else f"{P3394_REFERENCE_FILENAME} not found"
    core_points = _extract_core_points(text)
    role_points = [f"{name}: {description}." for name, description in P3394_INTERNAL_ROLES]

    return "\n".join(
        [
            "P3394 local architecture reference:",
            f"- source: {source}",
            f"- document: {title}",
            "- core architecture:",
            *[f"  - {point}" for point in core_points],
            "- internal role operating model:",
            *[f"  - {point}" for point in role_points],
            "- project architecture mode: when the user asks to analyze or transform a project by P3394, map the project to manifest, channel adapter, UMF message flow, session/context compartments, relationship/capability authorization, tools/resources, audit/conformance evidence, then propose or execute the smallest verified change.",
        ]
    )
