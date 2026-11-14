"""Job parsing for the plugin-facing render path.

A creation job is deliberately small: an id, a plan (inline or path), and
optional source/idempotency metadata. Publishing fields, if present, are
ignored: publishing belongs to the upstream plugin, not this studio.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import StudioError


def safe_job_id(value: str) -> str:
    text = str(value).strip()
    invalid = set('\\/:*?"<>|')
    if (
        not text
        or text in {".", ".."}
        or any(char in invalid for char in text)
        or any(ord(char) < 32 for char in text)
    ):
        raise StudioError(f"job_id 不能用作文件名：{value}")
    return text


def _resolve_plan_path(raw: dict[str, Any], job_path: Path, project_root: Path) -> Path:
    if "plan" in raw:
        plan = raw["plan"]
        if not isinstance(plan, dict):
            raise StudioError("job.plan 必须是 JSON 对象")
        job_id = safe_job_id(str(raw.get("job_id") or job_path.stem))
        target = project_root / "data" / "jobs" / f"{job_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    plan_path = raw.get("plan_path")
    if not plan_path:
        raise StudioError("job 需要 plan 对象或 plan_path")
    candidate = Path(str(plan_path)).expanduser()
    if not candidate.is_absolute():
        beside_job = (job_path.parent / candidate).resolve()
        candidate = beside_job if beside_job.exists() else (project_root / candidate).resolve()
    return candidate


@dataclass
class JobSpec:
    job_id: str
    source: str
    idempotency_key: str
    plan_path: Path
    raw: dict[str, Any] = field(default_factory=dict)


def load_job(job_path: Path, project_root: Path) -> JobSpec:
    job_path = job_path.expanduser().resolve()
    if not job_path.exists():
        raise StudioError(f"job 不存在：{job_path}")
    raw = json.loads(job_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise StudioError("job 必须是 JSON 对象")

    job_id = safe_job_id(str(raw.get("job_id") or job_path.stem))
    plan_path = _resolve_plan_path({**raw, "job_id": job_id}, job_path, project_root)
    return JobSpec(
        job_id=job_id,
        source=str(raw.get("source") or "upstream"),
        idempotency_key=str(raw.get("idempotency_key") or job_id),
        plan_path=plan_path,
        raw=raw,
    )
