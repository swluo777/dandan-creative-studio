"""Generic pipeline entry point. Medium-specific logic lives in renderers."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .errors import StudioError
from .models import RenderContext, RenderResult
from .renderers.registry import get_renderer, list_formats


def _safe_component(value: Any, label: str) -> str:
    text = str(value)
    if not text or text in {".", ".."} or "/" in text or "\\" in text:
        raise StudioError(f"{label} 必须是简单名称：{value}")
    return text


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Preset is a base; plan values win; nested dicts merge."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_plan(plan_path: Path, project_root: Path | None = None) -> dict[str, Any]:
    if not plan_path.exists():
        raise StudioError(f"plan 不存在：{plan_path}")
    raw = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise StudioError("plan 必须是 JSON 对象")

    root = (project_root or Path(__file__).resolve().parent.parent).resolve()
    preset_id = raw.get("preset")
    if preset_id:
        preset_id = _safe_component(preset_id, "preset")
        preset_path = root / "presets" / f"{preset_id}.json"
        if not preset_path.exists():
            raise StudioError(f"preset 不存在：{preset_path}")
        preset = json.loads(preset_path.read_text(encoding="utf-8"))
        if not isinstance(preset, dict):
            raise StudioError(f"preset 必须是 JSON 对象：{preset_path}")
        plan = _deep_merge(preset, {key: value for key, value in raw.items() if key != "preset"})
        plan["preset"] = preset_id
    else:
        plan = raw

    if not plan.get("format"):
        plan["format"] = "image_post"
    if not plan.get("template"):
        raise StudioError("plan 缺少 template")
    plan["template"] = _safe_component(plan["template"], "template")
    if not plan.get("id"):
        plan["id"] = plan_path.stem
    return plan


def render_plan(
    plan_path: Path,
    output_path: Path | None = None,
    project_root: Path | None = None,
    now: Any | None = None,
    theme: str | None = None,
) -> RenderResult:
    project_root = (project_root or Path(__file__).resolve().parent.parent).resolve()
    plan = load_plan(plan_path, project_root=project_root)
    if theme:
        plan["theme"] = theme
    renderer = get_renderer(plan["format"])
    context = RenderContext(
        project_root=project_root,
        assets_dir=project_root / "assets",
        templates_dir=project_root / "templates",
        themes_dir=project_root / "themes",
        output_path=output_path,
        output_dir=project_root / "data" / "renders",
        now=now,
    )
    return renderer.render(plan, context)


def supported_formats() -> list[str]:
    return list_formats()
