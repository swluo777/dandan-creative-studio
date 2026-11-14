"""Text measurement, wrapping and colored-run drawing for the card renderer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import ImageDraw, ImageFont

from .errors import LayoutError

NO_LINE_START = "，。！？、；：）》”』】…"
NO_LINE_END = "（《“‘『【"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip()
    if value.startswith("#"):
        value = value[1:]
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"不支持的色值：{value}")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def load_font(path: Path, size: int, variation: str | None = "Black") -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(path), size=size)
    if variation:
        try:
            font.set_variation_by_name(variation)
        except (OSError, ValueError):
            pass
    return font


@dataclass
class Run:
    text: str
    color: tuple[int, int, int]


def _group_runs(chars: list[str], colors: list[str]) -> list[list[Run]]:
    lines: list[list[Run]] = []
    current: list[Run] = []
    for char, color in zip(chars, colors):
        if char == "\n":
            if current:
                lines.append(current)
                current = []
            continue
        if current and current[-1].color == hex_to_rgb(color):
            current[-1].text += char
        else:
            current.append(Run(char, hex_to_rgb(color)))
    if current:
        lines.append(current)
    return lines


def _build_units(
    text: str,
    colors: list[str],
    atomic_spans: list[tuple[int, int]] | None,
) -> list[tuple[str, str]]:
    """Keep highlighted phrases atomic so a yellow word never splits across lines."""
    starts = {start: end for start, end in (atomic_spans or [])}
    units: list[tuple[str, str]] = []
    index = 0
    while index < len(text):
        end = starts.get(index)
        if end is not None:
            units.append((text[index:end], colors[index]))
            index = end
        else:
            units.append((text[index], colors[index]))
            index += 1
    return units


def wrap_colored_text(
    text: str,
    colors: list[str],
    font: ImageFont.FreeTypeFont,
    max_width: int,
    atomic_spans: list[tuple[int, int]] | None = None,
) -> list[list[Run]]:
    """Wrap by character, keeping color runs and avoiding leading punctuation."""
    if len(text) != len(colors):
        raise LayoutError("文字与颜色数量不一致")

    lines: list[list[Run]] = []
    line: list[Run] = []
    line_width = 0.0

    def append_unit(unit_text: str, color: str) -> None:
        nonlocal line_width
        if line and line[-1].color == hex_to_rgb(color):
            line[-1].text += unit_text
        else:
            line.append(Run(unit_text, hex_to_rgb(color)))
        line_width += font.getlength(unit_text)

    def flush() -> None:
        nonlocal line, line_width
        if line:
            lines.append(line)
            line = []
            line_width = 0.0

    def add_unit(unit_text: str, color: str) -> None:
        nonlocal line_width
        if unit_text == "\n":
            flush()
            return

        unit_width = font.getlength(unit_text)
        if not line:
            if unit_width <= max_width or len(unit_text) == 1:
                append_unit(unit_text, color)
                return
            for char in unit_text:
                add_unit(char, color)
            return

        if line_width + unit_width <= max_width:
            append_unit(unit_text, color)
            return

        # Punctuation should not start a line; let it overhang slightly instead.
        if unit_text[0] in NO_LINE_START:
            append_unit(unit_text, color)
            flush()
            return

        # Opening punctuation should not end a line; pull it down with the next unit.
        if line[-1].text and line[-1].text[-1] in NO_LINE_END and len(line[-1].text) == 1:
            carry = line.pop()
            line_width -= font.getlength(carry.text)
            flush()
            append_unit(carry.text, "#%02X%02X%02X" % carry.color)
            add_unit(unit_text, color)
            return

        flush()
        add_unit(unit_text, color)

    for unit_text, color in _build_units(text, colors, atomic_spans):
        add_unit(unit_text, color)

    flush()
    return lines


def fit_text(
    text: str,
    colors: list[str],
    font_path: Path,
    variation: str,
    max_width: int,
    max_height: int,
    min_size: int,
    max_size: int,
    line_height: float,
    max_lines: int,
    atomic_spans: list[tuple[int, int]] | None = None,
) -> tuple[ImageFont.FreeTypeFont, list[list[Run]], int, int]:
    last: tuple[int, int, int] | None = None
    for size in range(max_size, min_size - 1, -1):
        font = load_font(font_path, size, variation)
        lines = wrap_colored_text(text, colors, font, max_width, atomic_spans)
        height = int(round(size * line_height)) * len(lines)
        last = (size, len(lines), height)
        if len(lines) <= max_lines and height <= max_height:
            return font, lines, size, int(round(size * line_height))

    size, line_count, height = last or (max_size, 0, 0)
    raise LayoutError(
        "正文放不进当前版心："
        f"字号 {size}px 时仍有 {line_count} 行、总高 {height}px，"
        f"上限为 {max_lines} 行 / {max_height}px。请缩短正文或改模板。"
    )


def draw_colored_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[list[Run]],
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    line_height: int,
) -> int:
    ascent, _descent = font.getmetrics()
    top = y
    for line in lines:
        baseline = top + ascent
        cursor = x
        for run in line:
            draw.text((cursor, baseline), run.text, font=font, fill=run.color, anchor="ls")
            cursor += font.getlength(run.text)
        top += line_height
    return top
