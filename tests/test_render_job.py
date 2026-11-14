"""Tests for the plugin-facing render-only entry point."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from studio.errors import StudioError
from studio.render_job import render_job

ROOT = Path(__file__).resolve().parents[1]


class RenderJobTest(unittest.TestCase):
    def test_outputs_self_contained_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            job = temp_path / "job.json"
            job.write_text(
                json.dumps(
                    {
                        "job_id": "render-sit",
                        "source": "plugin-test",
                        "plan_path": str(ROOT / "examples" / "pose-sit-bottom.json"),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            payload = render_job(job, ROOT, out_root=temp_path / "exports")
            self.assertTrue(payload["ok"])
            output_dir = Path(payload["output_dir"])
            self.assertTrue((output_dir / "image.png").exists())
            self.assertTrue((output_dir / "result.json").exists())
            self.assertTrue((output_dir / "plan.json").exists())
            self.assertTrue((output_dir / "caption.txt").exists())

            result = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["job_id"], "render-sit")
            self.assertTrue(result["qa"]["ok"])

    def test_refuses_to_overwrite_without_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            job = temp_path / "job.json"
            job.write_text(
                json.dumps(
                    {
                        "job_id": "render-twice",
                        "plan_path": str(ROOT / "examples" / "pose-sit-bottom.json"),
                    }
                ),
                encoding="utf-8",
            )
            render_job(job, ROOT, out_root=temp_path / "exports")
            with self.assertRaises(StudioError):
                render_job(job, ROOT, out_root=temp_path / "exports")
            payload = render_job(
                job,
                ROOT,
                out_root=temp_path / "exports",
                overwrite=True,
            )
            self.assertTrue(Path(payload["image"]).exists())


if __name__ == "__main__":
    unittest.main()
