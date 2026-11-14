"""Renderer registry.

Adding a new medium means adding a renderer and registering its format name.
The pipeline and QA layers do not learn about a specific medium; publishing
is outside this repository.
"""
from __future__ import annotations

from typing import Any

from ..errors import StudioError
from .base import Renderer
from .image_post import ImagePostRenderer

_RENDERERS: dict[str, Renderer] = {
    ImagePostRenderer.format: ImagePostRenderer(),
}


def register(renderer: Renderer) -> None:
    _RENDERERS[renderer.format] = renderer


def get_renderer(format_name: str) -> Renderer:
    try:
        return _RENDERERS[format_name]
    except KeyError as exc:
        known = "、".join(sorted(_RENDERERS))
        raise StudioError(f"未知内容格式“{format_name}”，已注册：{known}") from exc


def list_formats() -> list[str]:
    return sorted(_RENDERERS)


def describe() -> dict[str, Any]:
    return {"formats": list_formats()}
