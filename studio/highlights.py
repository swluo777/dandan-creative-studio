"""Highlight policy: at most three exact substrings, one role each.

The rule is deliberately narrow so the layout stays calm:
- hook: the opening sentence / announcement
- identity: the name or identity anchor
- topic: the one topic this post promises

Supporting details stay white. A highlight must be an exact substring of the
body, max 10 characters, and highlights may not overlap or touch.
"""
from __future__ import annotations

from .errors import HighlightError

MAX_HIGHLIGHTS = 3
MAX_HIGHLIGHT_CHARS = 10


def validate_highlights(text: str, highlights: list[str]) -> list[tuple[int, int]]:
    if not isinstance(highlights, list):
        raise HighlightError("highlights 必须是字符串数组")
    if len(highlights) > MAX_HIGHLIGHTS:
        raise HighlightError(f"高亮最多 {MAX_HIGHLIGHTS} 段，当前 {len(highlights)} 段")
    if not text.strip():
        if highlights:
            raise HighlightError("正文为空时不能设置高亮")
        return []

    spans: list[tuple[int, int, str]] = []
    for item in highlights:
        if not isinstance(item, str) or not item:
            raise HighlightError("高亮片段必须是非空字符串")
        if len(item) > MAX_HIGHLIGHT_CHARS:
            raise HighlightError(
                f"高亮片段“{item}”超过 {MAX_HIGHLIGHT_CHARS} 字，容易把版式打散"
            )
        start = text.find(item)
        if start < 0:
            raise HighlightError(f"高亮片段“{item}”不是正文的精确子串")
        if text.find(item, start + 1) >= 0:
            raise HighlightError(f"高亮片段“{item}”在正文中出现多次，无法确定位置")
        spans.append((start, start + len(item), item))

    spans.sort()
    for index, (start, end, item) in enumerate(spans):
        for other_start, other_end, other in spans[index + 1 :]:
            if start < other_end and other_start < end:
                raise HighlightError(f"高亮片段“{item}”与“{other}”重叠")
            if end == other_start or other_end == start:
                raise HighlightError(f"高亮片段“{item}”与“{other}”相邻，不能堆叠")

    return [(start, end) for start, end, _ in spans]


def color_map(text: str, highlights: list[str], text_color: str, highlight_color: str) -> list[str]:
    spans = validate_highlights(text, highlights)
    colors = [text_color] * len(text)
    for start, end in spans:
        for index in range(start, end):
            colors[index] = highlight_color
    return colors
