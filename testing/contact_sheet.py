"""A contact sheet and image metrics for HD | legacy pairs (the PNGs `game_ctl.py pair` writes), standard library only.

    python testing/contact_sheet.py <folder of pairs> <out.png> [--cols 2] [--width 1600]

Each pair PNG (HD on the left, legacy on the right, equal halves) becomes one cell of the sheet; the metrics print one
line per pair, in the order of the cells (reading order: left to right, top to bottom), because the sheet carries no
text. Measured on the playfield only: the bottom HUD band (HUD) is cut, and the legacy half is cut to its 4:3 picture
(D2R draws legacy pillarboxed: 1440 of 1920 px at 1080p), so black bars do not count as dark.

Metrics per pair (the reliable ones only):
  luma   mean Rec.601 luma of HD and of legacy, and HD/legacy (a median sits in the dark majority of a night scene and
         says little). Lighting parity wants about 0.85-1.15.
  black  share of near-black pixels (luma < BLACK) in each: legacy void reads black; HD drawing ground there shows as a
         lower black share.
Not measured: walkable-area overlap and edge masks. The two cameras do not frame the same world area, so those are
judged by eye on the sheet.

Pure Python: decoding a 1920x1080 pair PNG takes seconds; the metrics sample every SAMPLE-th pixel. The pure parts take
`game_ctl.Image` objects, so a check that already holds the shots (check_helpers.pair) need not decode anything.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # the toolkit root, for modkit
import check_helpers  # noqa: E402
from game_ctl import Image  # noqa: E402

HUD = 0.16               # bottom share of the frame that is HUD (orbs, belt, skill bar)
LEGACY_W = 1440 / 1920   # legacy's 4:3 picture inside the 16:9 frame
BLACK = 12               # a pixel below this luma is near-black
SAMPLE = 8               # metrics look at every 8th pixel each way


def crop(img: Image, left: int, top: int, right: int, bottom: int) -> Image:
    rows = [img.rgb[(y * img.width + left) * 3:(y * img.width + right) * 3] for y in range(top, bottom)]
    return Image(right - left, bottom - top, b"".join(rows))


def playfield(pair: Image) -> tuple[Image, Image]:
    """(HD, legacy) playfields of a side-by-side pair: HUD band cut, legacy cut to its 4:3 picture."""
    hd, legacy = check_helpers.split_pair(pair)
    h = int(pair.height * (1 - HUD))
    lw = int(legacy.width * LEGACY_W)
    x0 = (legacy.width - lw) // 2
    return crop(hd, 0, 0, hd.width, h), crop(legacy, x0, 0, x0 + lw, h)


def luma_stats(img: Image, step: int = SAMPLE, black: int = BLACK) -> tuple[float, float]:
    """(mean Rec.601 luma, share of near-black samples) over every `step`-th pixel."""
    total = dark = n = 0
    for y in range(0, img.height, step):
        row = y * img.width * 3
        for x in range(0, img.width, step):
            i = row + x * 3
            v = (299 * img.rgb[i] + 587 * img.rgb[i + 1] + 114 * img.rgb[i + 2]) // 1000
            total += v
            dark += v < black
            n += 1
    return (total / n, dark / n) if n else (0.0, 0.0)


def metrics(pair: Image) -> dict:
    out = {}
    for name, part in zip(("hd", "legacy"), playfield(pair)):
        out[name] = luma_stats(part)
    out["ratio"] = out["hd"][0] / out["legacy"][0] if out["legacy"][0] else float("inf")
    return out


def format_metrics(name: str, m: dict) -> str:
    return (f"{name}\tluma {m['hd'][0]:.0f}/{m['legacy'][0]:.0f} = {m['ratio']:.2f}\t"
            f"black {m['hd'][1]:.0%}/{m['legacy'][1]:.0%}")


def thumbnail(img: Image, width: int) -> Image:
    """Nearest-neighbour thumbnail `width` pixels wide."""
    height = max(1, img.height * width // img.width)
    xs = [x * img.width // width for x in range(width)]
    rows = []
    for y in range(height):
        base = (y * img.height // height) * img.width * 3
        row = bytearray(width * 3)
        for j, x in enumerate(xs):
            row[j * 3:j * 3 + 3] = img.rgb[base + x * 3:base + x * 3 + 3]
        rows.append(bytes(row))
    return Image(width, height, b"".join(rows))


def sheet(pairs: list[tuple[str, Image]], cols: int = 2, width: int = 1600) -> tuple[Image, list[tuple[str, dict]]]:
    """(the sheet image, [(name, metrics)] in cell order) for (name, side-by-side pair) items. Cells are `width // cols`
    wide; empty cells at the end are black."""
    if not pairs:
        raise ValueError("no pairs")
    if cols < 1 or width < cols:
        raise ValueError("cols must be >= 1 and width >= cols")
    cell_w = width // cols
    cells = [thumbnail(p, cell_w) for _, p in pairs]
    cell_h = max(c.height for c in cells)
    rows_n = (len(cells) + cols - 1) // cols
    out_w = cell_w * cols
    rows = []
    for r in range(rows_n):
        for y in range(cell_h):
            line = bytearray(out_w * 3)
            for c in range(cols):
                k = r * cols + c
                if k < len(cells) and y < cells[k].height:
                    line[c * cell_w * 3:(c + 1) * cell_w * 3] = cells[k].rgb[y * cell_w * 3:(y + 1) * cell_w * 3]
            rows.append(bytes(line))
    found = [(name, metrics(p)) for name, p in pairs]
    return Image(out_w, cell_h * rows_n, b"".join(rows)), found


def read_pair(path: str) -> Image:
    from modkit.images import read_png
    w, h, rgba = read_png(path)
    rgb = bytearray(w * h * 3)
    rgb[0::3], rgb[1::3], rgb[2::3] = rgba[0::4], rgba[1::4], rgba[2::4]
    return Image(w, h, bytes(rgb))


def sheet_folder(folder: str, dest: str, cols: int = 2, width: int = 1600) -> list[tuple[str, dict]]:
    """Write the sheet of every pair PNG in `folder` (sorted by name) to `dest` (a PNG); returns the metrics."""
    names = sorted(n for n in os.listdir(folder) if n.lower().endswith(".png"))
    if not names:
        raise ValueError(f"no pairs in {folder}")
    img, found = sheet([(os.path.splitext(n)[0], read_pair(os.path.join(folder, n))) for n in names], cols, width)
    img.save(dest)
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder")
    ap.add_argument("dest", help="the sheet, a PNG")
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--width", type=int, default=1600)
    a = ap.parse_args(argv)
    try:
        for name, m in sheet_folder(a.folder, a.dest, a.cols, a.width):
            print(format_metrics(name, m))
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
