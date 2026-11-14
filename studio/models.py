"""Creative-plan models shared by every renderer.

The studio is intentionally format-agnostic: image posts, code animation,
generative video and real-world compositing all consume the same plan envelope
and return the same artifact/QA envelope.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Artifact:
    kind: str
    path: Path
    width: int | None = None
    height: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QAReport:
    ok: bool
    checks: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class RenderResult:
    artifacts: list[Artifact]
    qa: QAReport
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderContext:
    project_root: Path
    assets_dir: Path
    templates_dir: Path
    themes_dir: Path | None = None
    output_path: Path | None = None
    output_dir: Path | None = None
    now: Any | None = None
