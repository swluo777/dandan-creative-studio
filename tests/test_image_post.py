"""Tests for the first image-post renderer and highlight policy."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from studio.errors import HighlightError, LayoutError
from studio.models import RenderContext
from studio.pipeline import render_plan
from studio.renderers.image_post import ImagePostRenderer
from studio.highlights import color_map, validate_highlights

ROOT = Path(__file__).resolve().parents[1]


class HighlightPolicyTest(unittest.TestCase):
    def test_three_anchors(self):
        text = "新号第一条。本鱼叫蛋蛋，蓝鲸，成年。以后记点冷知识。"
        spans = validate_highlights(text, ["新号第一条。", "蛋蛋", "冷知识"])
        self.assertEqual(len(spans), 3)

    def test_too_many(self):
        with self.assertRaises(HighlightError):
            validate_highlights("甲乙丙丁", ["甲", "乙", "丙", "丁"])

    def test_not_a_substring(self):
        with self.assertRaises(HighlightError):
            validate_highlights("本鱼叫蛋蛋", ["不存在"])

    def test_overlap(self):
        with self.assertRaises(HighlightError):
            validate_highlights("本鱼叫蛋蛋", ["蛋蛋", "蛋蛋"])

    def test_adjacent(self):
        with self.assertRaises(HighlightError):
            validate_highlights("蛋蛋冷知识", ["蛋蛋", "冷知识"])

    def test_too_long(self):
        with self.assertRaises(HighlightError):
            validate_highlights("一二三四五六七八九十十一", ["一二三四五六七八九十十一"])

    def test_color_map(self):
        colors = color_map("蛋蛋冷知识", ["蛋蛋"], "#FFFFFF", "#FFF35F")
        self.assertEqual(colors[:2], ["#FFF35F", "#FFF35F"])
        self.assertEqual(colors[2:], ["#FFFFFF", "#FFFFFF", "#FFFFFF"])


class ImagePostRendererTest(unittest.TestCase):
    def render_example(self, example: str, name: str):
        plan_path = ROOT / "examples" / example
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / name
            result = render_plan(plan_path, output_path=output, project_root=ROOT)
            self.assertTrue(result.qa.ok, result.qa.errors)
            self.assertEqual(len(result.artifacts), 1)
            self.assertTrue(output.exists())
            with Image.open(output) as image:
                self.assertEqual(image.size, (1080, 1440))
            return result

    def test_text_only(self):
        result = self.render_example("first-post.json", "first-post.png")
        self.assertEqual(result.metadata["font_size"], 100)
        self.assertEqual(result.metadata["line_count"], 6)
        self.assertFalse(result.metadata["character"])
        self.assertEqual(result.metadata["theme"], "butter-yellow")

    def test_theme_override(self):
        plan_path = ROOT / "examples" / "first-post.json"
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "sakura.png"
            result = render_plan(plan_path, output_path=output, project_root=ROOT, theme="sakura-pink")
            self.assertTrue(result.qa.ok, result.qa.errors)
            self.assertEqual(result.metadata["theme"], "sakura-pink")
            with Image.open(output) as image:
                self.assertEqual(image.getpixel((10, 10)), (0xF3, 0xC9, 0xD4))

    def test_all_themes_render(self):
        plan_path = ROOT / "examples" / "first-post.json"
        for theme_path in sorted((ROOT / "themes").glob("*.json")):
            theme_id = theme_path.stem
            with tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / f"{theme_id}.png"
                result = render_plan(plan_path, output_path=output, project_root=ROOT, theme=theme_id)
                self.assertTrue(result.qa.ok, f"{theme_id}: {result.qa.errors}")
                self.assertEqual(result.metadata["theme"], theme_id)

    def test_preset_merge(self):
        plan_path = ROOT / "examples" / "first-post-preset.json"
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "preset.png"
            result = render_plan(plan_path, output_path=output, project_root=ROOT)
            self.assertTrue(result.qa.ok, result.qa.errors)
            self.assertEqual(result.metadata["preset"], "dandan-default")
            self.assertEqual(result.metadata["handle"], "@蛋蛋")
            self.assertEqual(result.metadata["theme"], "butter-yellow")

    def test_parameterized_demo(self):
        plan_path = ROOT / "examples" / "parameterized-demo.json"
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "params.png"
            result = render_plan(plan_path, output_path=output, project_root=ROOT)
            self.assertTrue(result.qa.ok, result.qa.errors)
            self.assertEqual(result.metadata["handle"], "@测试号")
            self.assertEqual(result.metadata["date"], "11-14")
            self.assertEqual(result.metadata["time"], "20:30")
            self.assertEqual(result.metadata["weekday"], "Saturday")
            self.assertEqual(result.metadata["theme"], "mist-blue")
            self.assertTrue(result.metadata["character"])
            self.assertEqual(result.metadata["character_id"], "dandan")

    def test_custom_colors_override_theme(self):
        source = json.loads((ROOT / "examples" / "first-post.json").read_text(encoding="utf-8"))
        source["colors"] = {"background": "#123456", "highlight": "#ABCDEF"}
        with tempfile.TemporaryDirectory() as temp:
            plan_path = Path(temp) / "custom-colors.json"
            plan_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
            output = Path(temp) / "custom-colors.png"
            result = render_plan(plan_path, output_path=output, project_root=ROOT)
            self.assertTrue(result.qa.ok, result.qa.errors)
            with Image.open(output) as image:
                self.assertEqual(image.getpixel((10, 10)), (0x12, 0x34, 0x56))

    def test_avatar_and_handle_override(self):
        source = json.loads((ROOT / "examples" / "first-post.json").read_text(encoding="utf-8"))
        source["account"] = {
            "handle": "@另一个AI",
            "avatar": "characters/dandan/sticker.png",
        }
        with tempfile.TemporaryDirectory() as temp:
            plan_path = Path(temp) / "account.json"
            plan_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
            output = Path(temp) / "account.png"
            result = render_plan(plan_path, output_path=output, project_root=ROOT)
            self.assertTrue(result.qa.ok, result.qa.errors)
            self.assertEqual(result.metadata["handle"], "@另一个AI")
            self.assertEqual(result.metadata["avatar"], "characters/dandan/sticker.png")

    def test_long_handle_is_loud(self):
        source = json.loads((ROOT / "examples" / "first-post.json").read_text(encoding="utf-8"))
        source["account"]["handle"] = "@" + "很长的昵称" * 8
        with tempfile.TemporaryDirectory() as temp:
            plan_path = Path(temp) / "long-handle.json"
            plan_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
            output = Path(temp) / "long-handle.png"
            result = render_plan(plan_path, output_path=output, project_root=ROOT)
            self.assertFalse(result.qa.ok)
            check = next(item for item in result.qa.checks if item["name"] == "header_handle_fit")
            self.assertFalse(check["ok"])

    def test_display_time_override(self):
        source = json.loads((ROOT / "examples" / "first-post.json").read_text(encoding="utf-8"))
        source["display_time"] = {"date": "01-01", "time": "00:00", "weekday": "Monday"}
        with tempfile.TemporaryDirectory() as temp:
            plan_path = Path(temp) / "display-time.json"
            plan_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
            output = Path(temp) / "display-time.png"
            result = render_plan(plan_path, output_path=output, project_root=ROOT)
            self.assertTrue(result.qa.ok, result.qa.errors)
            self.assertEqual(result.metadata["date"], "01-01")
            self.assertEqual(result.metadata["time"], "00:00")
            self.assertEqual(result.metadata["weekday"], "Monday")

    def test_current_time_default(self):
        source = json.loads((ROOT / "examples" / "first-post.json").read_text(encoding="utf-8"))
        source.pop("published_at", None)
        with tempfile.TemporaryDirectory() as temp:
            plan_path = Path(temp) / "now.json"
            plan_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
            output = Path(temp) / "now.png"
            result = render_plan(plan_path, output_path=output, project_root=ROOT)
            self.assertTrue(result.qa.ok, result.qa.errors)
            self.assertRegex(result.metadata["date"], r"^\d{2}-\d{2}$")
            self.assertRegex(result.metadata["time"], r"^\d{2}:\d{2}$")
            self.assertTrue(result.metadata["weekday"])

    def test_utc_time_converts_to_shanghai(self):
        source = json.loads((ROOT / "examples" / "first-post.json").read_text(encoding="utf-8"))
        source["published_at"] = "2026-11-14T12:30:00Z"
        source["timezone"] = "Asia/Shanghai"
        with tempfile.TemporaryDirectory() as temp:
            plan_path = Path(temp) / "utc.json"
            plan_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
            output = Path(temp) / "utc.png"
            result = render_plan(plan_path, output_path=output, project_root=ROOT)
            self.assertTrue(result.qa.ok, result.qa.errors)
            self.assertEqual(result.metadata["date"], "11-14")
            self.assertEqual(result.metadata["time"], "20:30")

    def test_character_cutout(self):
        result = self.render_example("first-post-with-character.json", "first-post-with-character.png")
        self.assertTrue(result.metadata["character"])
        check = next(item for item in result.qa.checks if item["name"] == "character_bounds")
        self.assertTrue(check["ok"])

    def test_registry_has_five_poses(self):
        registry = json.loads(
            (ROOT / "assets" / "characters" / "registry.json").read_text(encoding="utf-8")
        )
        poses = registry["dandan"]["poses"]
        self.assertEqual(set(poses), {"stand", "wave", "sit", "peek-left", "peek-right"})
        self.assertEqual(registry["dandan"]["poseMeta"]["peek-left"]["cutEdge"], "left")
        self.assertEqual(registry["dandan"]["poseMeta"]["peek-right"]["cutEdge"], "right")

    def test_pose_placements(self):
        cases = [
            ("pose-sit-bottom.json", "sit", "bottom-right"),
            ("pose-peek-left.json", "peek-left", "left-edge"),
            ("pose-peek-right.json", "peek-right", "right-edge"),
            ("pose-wave-bottom.json", "wave", "bottom-right"),
            ("pose-stand-bottom.json", "stand", "bottom-right"),
        ]
        for example, pose, placement in cases:
            result = self.render_example(example, example.replace(".json", ".png"))
            self.assertEqual(result.metadata["character_pose"], pose)
            self.assertEqual(result.metadata["character_placement"], placement)
            for name in ("character_bounds", "character_body_overlap", "character_header_overlap"):
                check = next(item for item in result.qa.checks if item["name"] == name)
                self.assertTrue(check["ok"], f"{example}: {name} {check}")

    def test_pose_presets(self):
        cases = [
            ("dandan-sit-bottom", "sit", "bottom-right"),
            ("dandan-peek-left", "peek-left", "left-edge"),
            ("dandan-peek-right", "peek-right", "right-edge"),
        ]
        for preset, pose, placement in cases:
            plan = {
                "preset": preset,
                "hook": "试一下预设。",
                "body": "今天不聊冷知识，就看看谁在偷看。",
                "highlights": ["试一下预设。", "偷看"],
                "caption": "试一下预设。",
                "published_at": "2026-11-13T23:09:00+08:00",
            }
            with tempfile.TemporaryDirectory() as temp:
                plan_path = Path(temp) / "preset.json"
                plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
                output = Path(temp) / "preset.png"
                result = render_plan(plan_path, output_path=output, project_root=ROOT)
                self.assertTrue(result.qa.ok, result.qa.errors)
                self.assertEqual(result.metadata["character_pose"], pose)
                self.assertEqual(result.metadata["character_placement"], placement)
                self.assertEqual(result.metadata["preset"], preset)

    def test_overflow_is_loud(self):
        plan_path = ROOT / "examples" / "first-post.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["body"] = "很长" * 80
        plan["hook"] = ""
        plan["highlights"] = []
        plan["id"] = "overflow"
        with tempfile.TemporaryDirectory() as temp:
            context = RenderContext(
                project_root=ROOT,
                assets_dir=ROOT / "assets",
                templates_dir=ROOT / "templates",
                themes_dir=ROOT / "themes",
                output_path=Path(temp) / "overflow.png",
            )
            with self.assertRaises(LayoutError):
                ImagePostRenderer().render(plan, context)


if __name__ == "__main__":
    unittest.main()
