"""CLI: render plans and the plugin-facing render-job entry."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .errors import StudioError
from .pipeline import render_plan, supported_formats
from .render_job import render_job


def _summary(result) -> dict:
    return {
        "ok": result.qa.ok,
        "artifacts": [
            {
                "kind": artifact.kind,
                "path": str(artifact.path),
                "width": artifact.width,
                "height": artifact.height,
            }
            for artifact in result.artifacts
        ],
        "checks": result.qa.checks,
        "errors": result.qa.errors,
        "metadata": result.metadata,
    }


def _project_root(value: str | None) -> Path:
    return (
        Path(value).expanduser().resolve()
        if value
        else Path(__file__).resolve().parent.parent
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dandan-studio")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render = subparsers.add_parser("render", help="按 plan 渲染一个内容产物")
    render.add_argument("--plan", required=True, help="plan JSON 路径")
    render.add_argument("--out", help="输出文件路径；默认 data/renders/<id>.png")
    render.add_argument("--theme", help="覆盖 plan 里的配色主题，例如 sakura-pink")
    render.add_argument("--project-root", help="项目根目录；默认当前仓库")

    render_job_parser = subparsers.add_parser(
        "render-job",
        help="插件入口：渲染 job 到 data/exports/<job_id>，只创作、不发布",
    )
    render_job_parser.add_argument("--job", required=True, help="job JSON 路径")
    render_job_parser.add_argument("--out-root", help="输出根目录；默认 data/exports")
    render_job_parser.add_argument("--overwrite", action="store_true", help="允许覆盖已有输出目录")
    render_job_parser.add_argument("--project-root", help="项目根目录；默认当前仓库")

    subparsers.add_parser("formats", help="列出已注册的内容格式")
    subparsers.add_parser("themes", help="列出可用的配色主题")

    args = parser.parse_args(argv)
    try:
        if args.command == "formats":
            print(json.dumps({"formats": supported_formats()}, ensure_ascii=False, indent=2))
            return 0

        if args.command == "themes":
            root = _project_root(None)
            themes = []
            for path in sorted((root / "themes").glob("*.json")):
                item = json.loads(path.read_text(encoding="utf-8"))
                themes.append(
                    {
                        "id": item.get("id") or path.stem,
                        "name": item.get("name"),
                        "mood": item.get("mood") or [],
                    }
                )
            print(json.dumps({"themes": themes}, ensure_ascii=False, indent=2))
            return 0

        if args.command == "render-job":
            root = _project_root(args.project_root)
            out_root = (
                Path(args.out_root).expanduser().resolve()
                if args.out_root
                else None
            )
            payload = render_job(
                Path(args.job),
                root,
                out_root=out_root,
                overwrite=args.overwrite,
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
            return 0 if payload["ok"] else 1

        plan_path = Path(args.plan).expanduser().resolve()
        root = _project_root(args.project_root)
        output_path = Path(args.out).expanduser().resolve() if args.out else None
        result = render_plan(
            plan_path=plan_path,
            output_path=output_path,
            project_root=root,
            theme=args.theme,
        )
        print(json.dumps(_summary(result), ensure_ascii=False, indent=2, default=str))
        return 0 if result.qa.ok else 1
    except StudioError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
