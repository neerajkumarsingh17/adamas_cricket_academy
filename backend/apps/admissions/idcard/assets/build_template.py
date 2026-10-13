"""Build `id_card_front.jpg` — the print background pdf.py draws each
card's details onto — from the designer's mock-up. Re-run after the
artwork changes:

    .venv/bin/python apps/admissions/idcard/assets/build_template.py

The mock-up is a finished sample card (drop shadow, a sample name and
sample values baked in). This crops it to the card edge and paints out
the sample text so pdf.py can set the real student's in its place; the
photo placeholder is left in, as the fallback for a student with no
photo on file. Pillow only — every painted-out patch sits on the soft,
near-flat part of the background, so blending inwards from the patch's
own edges is enough to make it disappear.

All coordinates here and in pdf.py are pixels in the 3200x4800 source.
"""

from pathlib import Path

from PIL import Image, ImageChops

ASSETS = Path(__file__).resolve().parent
SOURCE = ASSETS.parents[3] / "docs_files" / "CRICKET ACADEMY_ID_CARD.png"
OUTPUT = ASSETS / "id_card_front.jpg"

# The card itself inside the mock-up (the rest is shadow and margin).
# pdf.py's ART_BOX must match.
CARD_BOX = (137, 90, 3059, 4634)

# Sample text to paint out: (left, top, right, bottom).
ERASE = [
    (1250, 2750, 1960, 2950),  # name
    (960, 3110, 2200, 3300),  # "ID:" + value
    (960, 3390, 2450, 3590),  # "Programme:" + value
    (960, 3690, 2350, 3848),  # "Valid until:" + value (stops short of the wave)
]

# 600 dpi at the printed 85.6 mm card height.
OUTPUT_HEIGHT = 2022
EDGE = 6  # px of surrounding background sampled along each side of a patch


def _ramp(size: tuple[int, int], horizontal: bool) -> Image.Image:
    line = Image.linear_gradient("L")  # 256x256, black at the top
    if horizontal:
        line = line.rotate(90, expand=True)  # black at the left
    return line.resize(size)


def _fill(image: Image.Image, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    size = (right - left, bottom - top)

    def edge(crop_box):
        strip = image.crop(crop_box)
        along_x = strip.width > strip.height
        strip = strip.resize(
            (strip.width, 1) if along_x else (1, strip.height), Image.Resampling.BOX
        )
        return strip.resize(size, Image.Resampling.BICUBIC)

    above = edge((left, top - EDGE, right, top))
    below = edge((left, bottom, right, bottom + EDGE))
    before = edge((left - EDGE, top, left, bottom))
    after = edge((right, top, right + EDGE, bottom))

    vertical = Image.composite(below, above, _ramp(size, horizontal=False))
    horizontal = Image.composite(after, before, _ramp(size, horizontal=True))
    image.paste(ImageChops.blend(vertical, horizontal, 0.5), (left, top))


def main() -> None:
    image = Image.open(SOURCE).convert("RGB")
    for box in ERASE:
        _fill(image, box)
    card = image.crop(CARD_BOX)
    width = round(OUTPUT_HEIGHT * card.width / card.height)
    card.resize((width, OUTPUT_HEIGHT), Image.Resampling.LANCZOS).save(
        OUTPUT, quality=92, optimize=True
    )
    print(f"{OUTPUT.name}: {width}x{OUTPUT_HEIGHT}, {OUTPUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
