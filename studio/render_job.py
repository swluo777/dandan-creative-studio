"""Plugin-facing render entry point.

This is the "button pressed upstream -> image comes back" path. It only
renders and writes a self-contained result directory; publishing, account
login and cookies belong to the upstream plugin.

Default output:

    data/exports/<job_id>/
      image.png
      plan.json
      result.json
      caption.txt

`data/exports` is gitignored. The caller gets absolute paths back, so the
upstream plugin does not need to know the studio's directory layout.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import StudioError
from .job_spec import load_job
from .pipeline import load_plan, render_plan


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def render_job(
    job_path: Path,
    project_root: Path,
    out_root: Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    project_root = project_root.expanduser().resolve()
    spec = load_job(job_path, project_root)
    plan = load_plan(spec.plan_path, project_root=project_root)

    base = (
        Path(out_root).expanduser().resolve()
        if out_root
        else project_root / "data" / "exports"
    )
    out_dir = base / spec.job_id
    if out_dir.exists():
        if not overwrite:
            raise StudioError(
                f"输出目录已存在，拒绝覆盖：{out_dir}。换 job_id，或明确传 overwrite=true。"
            )
        for name in ("image.png", "plan.json", "result.json", "caption.txt"):
            old = out_dir / name
            if old.exists():
                old.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    image_path = out_dir / "image.png"
    result = render_plan(
        plan_path=spec.plan_path,
        output_path=image_path,
        project_root=project_root,
    )
    image_artifact = next(
        (artifact for artifact in result.artifacts if artifact.kind == "image"),
        None,
    )
    if image_artifact is None:
        raise StudioError("render_job 需要一个 image artifact；当前该 format 还不能走插件渲染")

    caption = str(plan.get("caption") or "").strip()
    plan_path = out_dir / "plan.json"
    result_path = out_dir / "result.json"
    caption_path = out_dir / "caption.txt"
    _write_json(plan_path, plan)
    _write_json(
        result_path,
        {
            "schema_version": 1,
            "job_id": spec.job_id,
            "source": spec.source,
            "ok": result.qa.ok,
            "image": str(image_path),
            "plan_file": str(plan_path),
            "qa": {
                "ok": result.qa.ok,
                "checks": result.qa.checks,
                "errors": result.qa.errors,
            },
            "artifacts": [
                {
                    "kind": artifact.kind,
                    "path": str(artifact.path),
                    "width": artifact.width,
                    "height": artifact.height,
                }
                for artifact in result.artifacts
            ],
            "metadata": result.metadata,
            "caption": caption,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    if caption:
        caption_path.write_text(caption + "\n", encoding="utf-8")

    return {
        "ok": result.qa.ok,
        "job_id": spec.job_id,
        "source": spec.source,
        "output_dir": str(out_dir),
        "image": str(image_path),
        "result": str(result_path),
        "plan": str(plan_path),
        "caption_file": str(caption_path) if caption else None,
        "caption": caption,
        "qa": {
            "ok": result.qa.ok,
            "checks": result.qa.checks,
            "errors": result.qa.errors,
        },
    }
