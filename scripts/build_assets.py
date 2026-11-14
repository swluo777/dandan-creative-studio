"""Build deterministic avatar and sticker assets used by the black-card template.

Run from the repository root:
    python scripts/build_assets.py

Pose cutouts live under assets/characters/dandan/poses/ and are curated
assets: they were produced with MediaKit background removal and manual edge
cleanup, then reviewed. This script deliberately does not regenerate them,
so a low-quality flood-fill pass cannot overwrite the approved poses.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "characters" / "dandan" / "source.png"
AVATAR_SOURCE = ROOT / "assets" / "characters" / "dandan" / "avatar-source.png"
AVATAR = ROOT / "assets" / "characters" / "dandan" / "avatar.png"
STICKER = ROOT / "assets" / "characters" / "dandan" / "sticker.png"


def build_avatar() -> None:
    source = Image.open(AVATAR_SOURCE).convert("RGBA")
    # The reference post uses this smug, hand-on-cheek avatar artwork.
    # The crop keeps the headband, lightbulb and the two side doodles.
    crop = source.crop((60, 30, 1500, 1470))
    crop = crop.resize((320, 320), Image.Resampling.LANCZOS)
    mask = Image.new("L", (320, 320), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 319, 319], fill=255)
    crop.putalpha(mask)
    crop.save(AVATAR)
    print(f"avatar: {AVATAR} {crop.size}")


def build_sticker() -> None:
    source = Image.open(SOURCE).convert("RGBA")
    crop = source.crop((235, 210, 845, 960))
    crop = crop.resize((600, 680), Image.Resampling.LANCZOS)
    crop.save(STICKER)
    print(f"sticker: {STICKER} {crop.size}")


if __name__ == "__main__":
    if not SOURCE.exists():
        raise SystemExit(f"source missing: {SOURCE}")
    build_avatar()
    build_sticker()
