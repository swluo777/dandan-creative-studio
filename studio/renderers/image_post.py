"""Image-post renderer: Pillow layout for 1080x1440 text cards.

The renderer is deliberately deterministic. The LLM writes a plan (copy +
highlight roles), the template owns every visual token, and this module turns
the plan into pixels. No generative model is allowed to draw the card itself.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from ..errors import TemplateError
from ..highlights import color_map, validate_highlights
from ..models import Artifact, QAReport, RenderContext, RenderResult
from ..text_layout import draw_colored_lines, fit_text, hex_to_rgb, load_font
from .base import Renderer


class ImagePostRenderer(Renderer):
    format = "image_post"

    def render(self, plan: dict[str, Any], context: RenderContext) -> RenderResult:
        template = self._load_template(context.templates_dir, plan.get("template"))
        if template.get("format") != self.format:
            raise TemplateError(
                f"模板 {template.get('id')} 的格式是 {template.get('format')}，不是 {self.format}"
            )
        theme = self._load_theme(
            context.themes_dir,
            str(plan.get("theme") or template.get("theme") or ""),
        )
        if theme:
            self._apply_theme(template, theme)
        color_override = plan.get("colors")
        if color_override:
            if not isinstance(color_override, dict):
                raise TemplateError("plan.colors 必须是对象")
            self._apply_colors(template, color_override)

        character = self._character_config(template, plan, context)
        account = plan.get("account") or {}
        default_handle = "@" + str(character.get("name") or "蛋蛋")
        handle = str(account.get("handle") or default_handle)
        avatar_rel = str(
            account.get("avatar")
            or character.get("avatar")
            or "characters/dandan/avatar.png"
        )

        canvas = template["canvas"]
        width, height = int(canvas["width"]), int(canvas["height"])
        palette = template["palette"]
        typography = template.get("typography") or {}
        card = template["card"]

        timezone_name = str(plan.get("timezone") or "Asia/Shanghai")
        published_at = self._published_at(
            plan.get("published_at"),
            context.now,
            timezone_name,
        )
        display_time = plan.get("display_time") or {}
        if not isinstance(display_time, dict):
            raise TemplateError("plan.display_time 必须是对象")
        date_label = str(display_time.get("date") or published_at.strftime("%m-%d"))
        time_label = str(display_time.get("time") or published_at.strftime("%H:%M"))
        weekday_label = str(display_time.get("weekday") or published_at.strftime("%A"))

        body_text = self._body_text(plan)
        highlight_spans = validate_highlights(body_text, plan.get("highlights") or [])
        colors = color_map(
            body_text,
            plan.get("highlights") or [],
            template["body"]["textColor"],
            template["body"]["highlightColor"],
        )

        body_cfg = dict(template["body"])
        if character["enabled"]:
            body_cfg.update(character.get("bodyBox") or {})

        font_rel = str(typography.get("font") or "fonts/NotoSansSC-VF.ttf")
        font_path = context.assets_dir / font_rel
        if not font_path.exists():
            raise TemplateError(f"字体缺失：{font_path}")

        font, lines, font_size, line_height = fit_text(
            body_text,
            colors,
            font_path,
            str(typography.get("bodyVariation") or "Black"),
            int(body_cfg["width"]),
            int(body_cfg["height"]),
            int(body_cfg["sizeMin"]),
            int(body_cfg["sizeMax"]),
            float(body_cfg["lineHeight"]),
            int(body_cfg["maxLines"]),
        )

        image = Image.new("RGB", (width, height), hex_to_rgb(canvas["background"]))
        draw = ImageDraw.Draw(image)

        draw.rounded_rectangle(
            [
                int(card["x"]),
                int(card["y"]),
                int(card["x"]) + int(card["width"]),
                int(card["y"]) + int(card["height"]),
            ],
            radius=int(card["radius"]),
            fill=hex_to_rgb(palette["card"]),
        )

        self._draw_header(
            image,
            draw,
            template,
            context,
            font_path,
            typography,
            handle,
            avatar_rel,
            date_label,
            palette,
        )

        body_top = int(body_cfg["y"])
        text_bottom = draw_colored_lines(
            draw,
            lines,
            int(body_cfg["x"]),
            body_top,
            font,
            line_height,
        )

        character_box = None
        if character["enabled"]:
            character_box = self._draw_character(image, template, context, character, palette)

        self._draw_footer(
            draw,
            template,
            font_path,
            typography,
            time_label,
            weekday_label,
            palette,
        )

        output_path = context.output_path or (
            (context.output_dir or context.project_root / "data" / "renders")
            / f"{plan.get('id') or 'image-post'}.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, "PNG")

        header = template["header"]
        footer = template["footer"]
        handle_check_font = load_font(
            font_path,
            int(header["handle"]["size"]),
            str(typography.get("uiBoldVariation") or "Bold"),
        )
        date_check_font = load_font(
            font_path,
            int(header["date"]["size"]),
            str(typography.get("uiVariation") or "Regular"),
        )
        footer_time_font = load_font(
            font_path,
            int(footer["timeSize"]),
            str(typography.get("uiVariation") or "Regular"),
        )
        footer_weekday_font = load_font(
            font_path,
            int(footer["weekdaySize"]),
            str(typography.get("uiVariation") or "Regular"),
        )
        card_right = int(card["x"]) + int(card["width"])
        card_bottom = int(card["y"]) + int(card["height"])
        handle_width = handle_check_font.getlength(handle)
        date_width = date_check_font.getlength(date_label)
        footer_width = max(
            footer_time_font.getlength(time_label),
            footer_weekday_font.getlength(weekday_label),
        )

        checks = [
            self._check("canvas", image.size == (width, height), f"{image.size[0]}x{image.size[1]}"),
            self._check(
                "body_fit",
                text_bottom <= body_top + int(body_cfg["height"]),
                f"正文底部 {text_bottom} / 版心底 {body_top + int(body_cfg['height'])}",
            ),
            self._check(
                "line_count",
                len(lines) <= int(body_cfg["maxLines"]),
                f"{len(lines)} / {int(body_cfg['maxLines'])} 行",
            ),
            self._check(
                "header_handle_fit",
                int(header["handle"]["x"]) + handle_width <= card_right - 24,
                f"{handle_width:.0f}px / {card_right - 24 - int(header['handle']['x'])}px",
            ),
            self._check(
                "header_date_fit",
                int(header["date"]["x"]) + date_width <= card_right - 24,
                f"{date_width:.0f}px",
            ),
            self._check(
                "footer_fit",
                int(footer["x"]) + footer_width <= card_right - 24
                and int(footer["y"]) + int(footer["lineGap"]) + int(footer["weekdaySize"]) <= card_bottom - 20,
                f"{footer_width:.0f}px",
            ),
            self._check(
                "highlights",
                len(highlight_spans) <= 3,
                f"{len(highlight_spans)} 段",
            ),
            self._check(
                "character_bounds",
                character_box is None or self._inside_card(character_box, card),
                "无角色层" if character_box is None else str(character_box),
            ),
            self._check(
                "character_body_overlap",
                character_box is None
                or not self._overlaps(
                    character_box,
                    (
                        int(body_cfg["x"]),
                        int(body_cfg["y"]),
                        int(body_cfg["x"]) + int(body_cfg["width"]),
                        int(body_cfg["y"]) + int(body_cfg["height"]),
                    ),
                ),
                "无角色层" if character_box is None else f"角色 {character_box}",
            ),
            self._check(
                "character_header_overlap",
                character_box is None
                or not self._overlaps(
                    character_box,
                    (
                        int(card["x"]),
                        int(card["y"]),
                        card_right,
                        int(header["date"]["y"]) + int(header["date"]["size"]) + 12,
                    ),
                ),
                "无角色层" if character_box is None else f"角色 {character_box}",
            ),
        ]
        errors = [check["detail"] for check in checks if not check["ok"]]
        qa = QAReport(ok=not errors, checks=checks, errors=errors)

        return RenderResult(
            artifacts=[
                Artifact(
                    kind="image",
                    path=output_path,
                    width=width,
                    height=height,
                    metadata={"format": self.format, "template": template.get("id"), "theme": template.get("theme")},
                )
            ],
            qa=qa,
            metadata={
                "font_size": font_size,
                "line_height": line_height,
                "line_count": len(lines),
                "body_text": body_text,
                "highlights": plan.get("highlights") or [],
                "character": character["enabled"],
                "character_id": character.get("id"),
                "character_pose": character.get("pose"),
                "character_placement": character.get("placement"),
                "handle": handle,
                "avatar": avatar_rel,
                "date": date_label,
                "time": time_label,
                "weekday": weekday_label,
                "timezone": timezone_name,
                "preset": plan.get("preset"),
                "theme": template.get("theme"),
                "color_override": sorted((plan.get("colors") or {}).keys()),
                "published_at": published_at.isoformat(),
            },
        )

    def _load_template(self, templates_dir: Path, template_id: str | None) -> dict[str, Any]:
        if not template_id:
            raise TemplateError("plan 缺少 template")
        template_id = str(template_id)
        if "/" in template_id or "\\" in template_id or template_id in {".", ".."}:
            raise TemplateError(f"template 必须是简单名称：{template_id}")
        path = templates_dir / template_id / "template.json"
        if not path.exists():
            raise TemplateError(f"模板不存在：{path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_theme(self, themes_dir: Path | None, theme_id: str) -> dict[str, Any] | None:
        if not theme_id:
            return None
        theme_id = str(theme_id)
        if "/" in theme_id or "\\" in theme_id or theme_id in {".", ".."}:
            raise TemplateError(f"theme 必须是简单名称：{theme_id}")
        if themes_dir is None:
            raise TemplateError("context 缺少 themes_dir，无法应用配色主题")
        path = themes_dir / f"{theme_id}.json"
        if not path.exists():
            raise TemplateError(f"配色主题不存在：{path}")
        theme = json.loads(path.read_text(encoding="utf-8"))
        colors = theme.get("colors") or {}
        for key in ("background", "card", "text", "highlight", "muted", "accent"):
            if not colors.get(key):
                raise TemplateError(f"配色主题 {theme_id} 缺少 colors.{key}")
        return theme

    def _apply_theme(self, template: dict[str, Any], theme: dict[str, Any]) -> None:
        self._apply_colors(template, theme["colors"])
        template["theme"] = theme["id"]

    def _apply_colors(self, template: dict[str, Any], colors: dict[str, Any]) -> None:
        allowed = {"background", "card", "text", "highlight", "muted", "accent"}
        unknown = set(colors) - allowed
        if unknown:
            raise TemplateError(f"不支持的颜色字段：{', '.join(sorted(unknown))}")
        for key, value in colors.items():
            try:
                hex_to_rgb(str(value))
            except ValueError as exc:
                raise TemplateError(f"colors.{key} 不是合法色值：{value}") from exc

        if "background" in colors:
            template["canvas"]["background"] = colors["background"]
        palette = template["palette"]
        if "card" in colors:
            palette["card"] = colors["card"]
        if "text" in colors:
            palette["text"] = colors["text"]
            template["body"]["textColor"] = colors["text"]
        if "highlight" in colors:
            palette["highlight"] = colors["highlight"]
            template["body"]["highlightColor"] = colors["highlight"]
        if "muted" in colors:
            palette["muted"] = colors["muted"]
        if "accent" in colors:
            palette["avatarRing"] = colors["accent"]
            palette["stickerBorder"] = colors["accent"]

    def _published_at(self, value: str | None, now: Any | None, timezone_name: str) -> datetime:
        try:
            timezone = ZoneInfo(timezone_name)
        except Exception as exc:
            # Windows Python sometimes ships without the IANA tz database.
            if timezone_name in {"Asia/Shanghai", "Asia/Chongqing", "Asia/Harbin", "PRC"}:
                timezone = dt_timezone(timedelta(hours=8))
            else:
                raise TemplateError(f"timezone 不是合法时区：{timezone_name}") from exc
        if value:
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError as exc:
                raise TemplateError(f"published_at 不是合法时间：{value}") from exc
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone)
            return parsed.astimezone(timezone)
        if now is not None:
            if isinstance(now, datetime):
                return now.astimezone(timezone) if now.tzinfo else now.replace(tzinfo=timezone)
            return now
        return datetime.now(timezone)

    def _body_text(self, plan: dict[str, Any]) -> str:
        body = str(plan.get("body") or "").strip()
        hook = str(plan.get("hook") or "").strip()
        if not body:
            raise TemplateError("plan 缺少 body")
        if not hook:
            return body
        if body.startswith(hook):
            return body
        return f"{hook}{body}"

    def _character_config(
        self,
        template: dict[str, Any],
        plan: dict[str, Any],
        context: RenderContext,
    ) -> dict[str, Any]:
        template_character = template.get("character") or {}
        planned = plan.get("character") or {}
        if not isinstance(planned, dict):
            raise TemplateError("plan.character 必须是对象")

        placement = str(
            planned.get("placement")
            or template_character.get("placement")
            or "bottom-right"
        )
        placements = template_character.get("placements") or {}
        if placements and placement not in placements:
            raise TemplateError(
                f"未知角色位置 {placement}；可选：{', '.join(sorted(placements))}"
            )

        config = {
            key: value
            for key, value in template_character.items()
            if key not in {"placements", "bodyBoxes"}
        }
        config.update(placements.get(placement) or {})
        config.update(planned)
        config["placement"] = placement
        config["enabled"] = bool(config.get("enabled", False))

        character_id = str(config.get("id") or "dandan")
        config["id"] = character_id

        registry = self._load_character_registry(context.assets_dir)
        entry = registry.get(character_id)
        if registry and entry is None and config["enabled"]:
            raise TemplateError(f"角色注册表里没有 {character_id}")

        pose = str(config.get("pose") or "stand")
        config["pose"] = pose
        if entry:
            config.setdefault("name", entry.get("name"))
            config.setdefault("avatar", entry.get("avatar"))
            poses = entry.get("poses") or {}
            pose_path = poses.get(pose)
            if config["enabled"] and pose not in poses:
                raise TemplateError(f"角色 {character_id} 没有动作 {pose}")
            pose_meta = (entry.get("poseMeta") or {}).get(pose) or {}
            if "cutEdge" not in planned:
                config["cutEdge"] = pose_meta.get("cutEdge", config.get("cutEdge", "none"))
            for size_key in ("width", "height"):
                if size_key in pose_meta and size_key not in planned:
                    config[size_key] = pose_meta[size_key]
            if not config.get("image"):
                if str(config.get("mode") or "cutout") == "sticker":
                    config["image"] = entry.get("sticker") or pose_path or entry.get("avatar")
                else:
                    config["image"] = pose_path or entry.get("avatar")

        if not config.get("image"):
            config["image"] = "characters/dandan/poses/stand.png"

        body_boxes = template_character.get("bodyBoxes") or {}
        body_box = dict(body_boxes.get(placement) or {})
        keys = {
            "bodyX": "x",
            "bodyY": "y",
            "bodyWidth": "width",
            "bodyHeight": "height",
            "bodyMaxLines": "maxLines",
            "bodySizeMin": "sizeMin",
            "bodySizeMax": "sizeMax",
        }
        for source, target in keys.items():
            if source in planned:
                body_box[target] = planned[source]
        config["bodyBox"] = body_box
        return config

    def _load_character_registry(self, assets_dir: Path) -> dict[str, Any]:
        path = assets_dir / "characters" / "registry.json"
        if not path.exists():
            return {}
        registry = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(registry, dict):
            raise TemplateError(f"角色注册表必须是 JSON 对象：{path}")
        return registry

    def _draw_header(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        template: dict[str, Any],
        context: RenderContext,
        font_path: Path,
        typography: dict[str, Any],
        handle: str,
        avatar_rel: str,
        date_label: str,
        palette: dict[str, Any],
    ) -> None:
        header = template["header"]
        avatar_cfg = header["avatar"]
        size = int(avatar_cfg["size"])
        x, y = int(avatar_cfg["x"]), int(avatar_cfg["y"])

        avatar_path = context.assets_dir / avatar_rel
        if not avatar_path.exists():
            raise TemplateError(f"头像素材缺失：{avatar_path}")
        avatar = self._circular_image(avatar_path, size)
        ring_width = int(avatar_cfg.get("ringWidth", 0))
        if ring_width > 0:
            draw.ellipse(
                [x - ring_width, y - ring_width, x + size + ring_width, y + size + ring_width],
                outline=hex_to_rgb(palette["avatarRing"]),
                width=ring_width,
            )
        image.paste(avatar, (x, y), avatar)

        handle_cfg = header["handle"]
        handle_font = load_font(
            font_path,
            int(handle_cfg["size"]),
            str(typography.get("uiBoldVariation") or "Bold"),
        )
        draw.text(
            (int(handle_cfg["x"]), int(handle_cfg["y"])),
            handle,
            font=handle_font,
            fill=hex_to_rgb(palette["text"]),
            anchor="lt",
        )

        date_cfg = header["date"]
        date_font = load_font(
            font_path,
            int(date_cfg["size"]),
            str(typography.get("uiVariation") or "Regular"),
        )
        draw.text(
            (int(date_cfg["x"]), int(date_cfg["y"])),
            date_label,
            font=date_font,
            fill=hex_to_rgb(palette["muted"]),
            anchor="lt",
        )

    def _draw_footer(
        self,
        draw: ImageDraw.ImageDraw,
        template: dict[str, Any],
        font_path: Path,
        typography: dict[str, Any],
        time_label: str,
        weekday_label: str,
        palette: dict[str, Any],
    ) -> None:
        footer = template["footer"]
        time_font = load_font(
            font_path,
            int(footer["timeSize"]),
            str(typography.get("uiVariation") or "Regular"),
        )
        weekday_font = load_font(
            font_path,
            int(footer["weekdaySize"]),
            str(typography.get("uiVariation") or "Regular"),
        )
        x, y = int(footer["x"]), int(footer["y"])
        draw.text((x, y), time_label, font=time_font, fill=hex_to_rgb(palette["text"]), anchor="lt")
        draw.text(
            (x, y + int(footer["lineGap"])),
            weekday_label,
            font=weekday_font,
            fill=hex_to_rgb(palette["muted"]),
            anchor="lt",
        )

    def _draw_character(
        self,
        image: Image.Image,
        template: dict[str, Any],
        context: RenderContext,
        config: dict[str, Any],
        palette: dict[str, Any],
    ) -> tuple[int, int, int, int]:
        asset_path = context.assets_dir / str(config.get("image") or "characters/dandan/poses/stand.png")
        if not asset_path.exists():
            raise TemplateError(f"角色素材缺失：{asset_path}")

        box_w, box_h = int(config["width"]), int(config["height"])
        radius = int(config.get("radius", 24))
        border = int(config.get("borderWidth", 0))
        x, y = int(config["x"]), int(config["y"])
        mode = str(config.get("mode") or "cutout")

        source = Image.open(asset_path).convert("RGBA")

        if mode == "cutout":
            # Transparent pose: preserve the silhouette, never wrap it in a card.
            source = ImageOps.contain(source, (box_w, box_h), method=Image.Resampling.LANCZOS)
            actual_w, actual_h = source.size
            draw_x, draw_y = self._anchor_position(
                str(config.get("anchor") or "bottom-right"),
                x,
                y,
                box_w,
                box_h,
                actual_w,
                actual_h,
            )
            styled, pad = self._style_cutout(source, config, palette)
            if config.get("clipToCard", True):
                self._paste_clipped(image, styled, (draw_x - pad, draw_y - pad), template["card"])
            else:
                image.paste(styled, (draw_x - pad, draw_y - pad), styled)
            return (draw_x, draw_y, draw_x + actual_w, draw_y + actual_h)

        # Sticker mode: keep the artwork's own background, round it and frame it.
        source = ImageOps.fit(source, (box_w, box_h), method=Image.Resampling.LANCZOS)
        mask = Image.new("L", (box_w, box_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, box_w - 1, box_h - 1],
            radius=radius,
            fill=255,
        )
        source.putalpha(mask)

        total_w, total_h = box_w + border * 2, box_h + border * 2
        framed = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        if border > 0:
            border_layer = Image.new("RGBA", (total_w, total_h), (*hex_to_rgb(palette["stickerBorder"]), 255))
            border_mask = Image.new("L", (total_w, total_h), 0)
            ImageDraw.Draw(border_mask).rounded_rectangle(
                [0, 0, total_w - 1, total_h - 1],
                radius=radius + border,
                fill=255,
            )
            framed.paste(border_layer, (0, 0), border_mask)
        framed.paste(source, (border, border), source)

        if config.get("shadow", True):
            shadow = Image.new("RGBA", (total_w + 40, total_h + 40), (0, 0, 0, 0))
            shadow_mask = Image.new("L", shadow.size, 0)
            ImageDraw.Draw(shadow_mask).rounded_rectangle(
                [20, 20, 20 + total_w, 20 + total_h],
                radius=radius + border,
                fill=110,
            )
            shadow.putalpha(shadow_mask)
            shadow = shadow.filter(ImageFilter.GaussianBlur(18))
            image.paste(shadow, (x - 20, y - 12), shadow)

        image.paste(framed, (x, y), framed)
        return (x, y, x + total_w, y + total_h)

    def _anchor_position(
        self,
        anchor: str,
        x: int,
        y: int,
        box_w: int,
        box_h: int,
        actual_w: int,
        actual_h: int,
    ) -> tuple[int, int]:
        if anchor == "top-left":
            return x, y
        if anchor == "top-right":
            return x - actual_w, y
        if anchor == "bottom-left":
            return x, y - actual_h
        if anchor == "center":
            return x + (box_w - actual_w) // 2, y + (box_h - actual_h) // 2
        if anchor == "bottom-right":
            return x - actual_w, y - actual_h
        raise TemplateError(f"未知角色锚点：{anchor}")

    def _style_cutout(
        self,
        source: Image.Image,
        config: dict[str, Any],
        palette: dict[str, Any],
    ) -> tuple[Image.Image, int]:
        outline_width = max(0, int(config.get("outlineWidth", 0)))
        glow_radius = max(0, int(config.get("glowRadius", 0)))
        pad = max(12, outline_width * 3 + 6, glow_radius * 2 + 6)
        width, height = source.size
        styled = Image.new("RGBA", (width + pad * 2, height + pad * 2), (0, 0, 0, 0))

        outline_color = self._resolve_character_color(
            config.get("outlineColor"), palette, "highlight"
        )
        glow_color = self._resolve_character_color(
            config.get("glowColor"), palette, "highlight"
        )

        if glow_radius:
            glow_alpha = source.getchannel("A").filter(
                ImageFilter.GaussianBlur(glow_radius)
            ).point(lambda value: int(value * float(config.get("glowOpacity", 0.22))))
            glow_layer = Image.new("RGBA", source.size, (*glow_color, 255))
            glow_layer.putalpha(glow_alpha)
            styled.alpha_composite(glow_layer, (pad, pad))

        if outline_width:
            outline_alpha = source.getchannel("A").filter(
                ImageFilter.MaxFilter(outline_width * 2 + 1)
            ).filter(ImageFilter.GaussianBlur(1.0))
            outline_layer = Image.new("RGBA", source.size, (*outline_color, 255))
            outline_layer.putalpha(outline_alpha)
            styled.alpha_composite(outline_layer, (pad, pad))

        styled.alpha_composite(source, (pad, pad))

        # The source is trimmed to its alpha bbox, so the silhouette can touch
        # all four canvas edges. Do not let the outline run along those crop
        # edges: that reads as a rectangular sticker on a black card.
        transparent = (0, 0, 0, 0)
        edge = 2
        styled.paste(transparent, (0, 0, styled.width, pad + edge))
        styled.paste(transparent, (0, pad + height - edge, styled.width, styled.height))
        styled.paste(transparent, (0, 0, pad + edge, styled.height))
        styled.paste(transparent, (pad + width - edge, 0, styled.width, styled.height))

        cut_edge = str(config.get("cutEdge") or "none")
        if cut_edge == "left":
            styled.paste(transparent, (0, 0, pad + 8, styled.height))
        elif cut_edge == "right":
            styled.paste(transparent, (pad + width - 8, 0, styled.width, styled.height))
        elif cut_edge not in {"none", ""}:
            raise TemplateError(f"未知 cutEdge：{cut_edge}")
        return styled, pad

    def _resolve_character_color(
        self,
        value: Any,
        palette: dict[str, Any],
        fallback_key: str,
    ) -> tuple[int, int, int]:
        if value in (None, "", "auto"):
            return hex_to_rgb(palette[fallback_key])
        try:
            return hex_to_rgb(str(value))
        except ValueError as exc:
            raise TemplateError(f"角色描边/光晕颜色不合法：{value}") from exc

    def _paste_clipped(
        self,
        image: Image.Image,
        layer: Image.Image,
        position: tuple[int, int],
        card: dict[str, Any],
    ) -> None:
        clip = Image.new("L", layer.size, 0)
        left = int(card["x"]) - position[0]
        top = int(card["y"]) - position[1]
        right = left + int(card["width"])
        bottom = top + int(card["height"])
        ImageDraw.Draw(clip).rounded_rectangle(
            [left, top, right, bottom],
            radius=int(card["radius"]),
            fill=255,
        )
        mask = ImageChops.multiply(layer.getchannel("A"), clip)
        image.paste(layer, position, mask)

    def _circular_image(self, path: Path, size: int) -> Image.Image:
        source = Image.open(path).convert("RGBA")
        side = min(source.size)
        left = (source.width - side) // 2
        top = (source.height - side) // 2
        source = source.crop((left, top, left + side, top + side))
        source = source.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
        mask = Image.new("L", (size * 2, size * 2), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size * 2 - 1, size * 2 - 1], fill=255)
        source.putalpha(mask)
        return source.resize((size, size), Image.Resampling.LANCZOS)

    def _inside_card(self, box: tuple[int, int, int, int], card: dict[str, Any]) -> bool:
        left, top = int(card["x"]), int(card["y"])
        right = left + int(card["width"])
        bottom = top + int(card["height"])
        return box[0] >= left and box[1] >= top and box[2] <= right and box[3] <= bottom

    def _overlaps(
        self,
        first: tuple[int, int, int, int],
        second: tuple[int, int, int, int],
    ) -> bool:
        return not (
            first[2] <= second[0]
            or second[2] <= first[0]
            or first[3] <= second[1]
            or second[3] <= first[1]
        )

    def _check(self, name: str, ok: bool, detail: str) -> dict[str, Any]:
        return {"name": name, "ok": bool(ok), "detail": detail}
