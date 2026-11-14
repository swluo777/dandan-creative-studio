"""Render the same post in every color theme and build a contact sheet.

Usage:
    python scripts/render_themes.py

Outputs:
    examples/themes/first-post-<theme>.png
    examples/themes/theme-sheet.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from studio.pipeline import render_plan
from studio.text_layout import hex_to_rgb, load_font

PLAN = ROOT / "examples" / "first-post.json"
THEMES = ROOT / "themes"
OUT = ROOT / "examples" / "themes"
ORDER = [
    "butter-yellow",
    "sakura-pink",
    "mist-blue",
    "mint-green",
    "apricot-orange",
    "lavender-gray",
]
FONT = ROOT / "assets" / "fonts" / "NotoSansSC-VF.ttf"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cards: list[tuple[str, str, list[str], Image.Image, dict]] = []
    for theme_id in ORDER:
        theme = json.loads((THEMES / f"{theme_id}.json").read_text(encoding="utf-8"))
        output = OUT / f"first-post-{theme_id}.png"
        result = render_plan(
            PLAN,
            output_path=output,
            project_root=ROOT,
            theme=theme_id,
        )
        if not result.qa.ok:
            raise SystemExit(f"{theme_id} 渲染失败：{result.qa.errors}")
        with Image.open(output) as image:
            image.load()
            cards.append((theme_id, theme["name"], theme["mood"], image.copy(), theme["colors"]))
        print(f"{theme_id}: {output}")

    # 2 x 3 contact sheet. Each card is 360 x 480.
    card_w, card_h = 360, 480
    gap_x, gap_y = 22, 56
    margin_x, top = 40, 126
    sheet_w = margin_x * 2 + card_w * 3 + gap_x * 2
    sheet_h = top + card_h * 2 + gap_y * 2 + 36
    sheet = Image.new("RGB", (sheet_w, sheet_h), hex_to_rgb("#141414"))
    draw = ImageDraw.Draw(sheet)

    title_font = load_font(FONT, 38, "Black")
    sub_font = load_font(FONT, 20, "Regular")
    name_font = load_font(FONT, 20, "Bold")
    meta_font = load_font(FONT, 14, "Regular")
    draw.text((margin_x, 28), "黑卡大字 · 6 个配色", font=title_font, fill=(255, 255, 255), anchor="lt")
    draw.text(
        (margin_x, 80),
        "同一段文案，只换主题；角色层对所有主题通用",
        font=sub_font,
        fill=(160, 160, 160),
        anchor="lt",
    )

    for index, (theme_id, name, mood, image, colors) in enumerate(cards):
        col, row = index % 3, index // 3
        x = margin_x + col * (card_w + gap_x)
        y = top + row * (card_h + gap_y)
        image = image.resize((card_w, card_h), Image.Resampling.LANCZOS)
        sheet.paste(image, (x, y))

        label_y = y + card_h + 10
        swatch = 14
        draw.rounded_rectangle(
            [x, label_y + 4, x + swatch, label_y + 4 + swatch],
            radius=4,
            fill=hex_to_rgb(colors["background"]),
        )
        draw.rounded_rectangle(
            [x + swatch + 6, label_y + 4, x + swatch * 2 + 6, label_y + 4 + swatch],
            radius=4,
            fill=hex_to_rgb(colors["highlight"]),
        )
        draw.text((x + swatch * 2 + 16, label_y), f"{index + 1:02d}  {name}", font=name_font, fill=(255, 255, 255), anchor="lt")
        draw.text(
            (x + swatch * 2 + 16, label_y + 26),
            " / ".join(mood),
            font=meta_font,
            fill=(160, 160, 160),
            anchor="lt",
        )
        draw.text(
            (x, label_y + 50),
            theme_id,
            font=meta_font,
            fill=(100, 100, 100),
            anchor="lt",
        )

    output = OUT / "theme-sheet.png"
    sheet.save(output, "PNG")
    print(f"sheet: {output} {sheet.size}")


if __name__ == "__main__":
    main()
