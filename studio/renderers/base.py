"""Renderer protocol and shared result/context types."""
from __future__ import annotations

from typing import Any, Protocol

from ..models import RenderContext, RenderResult


class Renderer(Protocol):
    format: str

    def render(self, plan: dict[str, Any], context: RenderContext) -> RenderResult:
        ...
