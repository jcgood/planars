"""Side-by-side pixel comparison of two chart PNGs, for planarsviz porting.

Writes reference | candidate | difference into one image and prints the
fraction of pixels that differ by more than a small tolerance (to ignore
anti-aliasing noise). Used by the chart-porting loop in
docs/PLAN_planarsviz_library.md, section 7 step 4.

Usage:
    python scripts/planarsviz_compare.py REF.png NEW.png OUT.png [--tolerance 32]

If the two images differ in size, the report says so and the side-by-side
pads the smaller one with white rather than rescaling it (rescaling would
hide exactly the kind of layout difference this check is meant to catch).
"""

import argparse
import sys

import numpy as np
from PIL import Image


def load_rgb(path):
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        white = Image.new("RGBA", im.size, (255, 255, 255, 255))
        white.alpha_composite(im)
        im = white
    return np.asarray(im.convert("RGB"), dtype=np.int16)


def pad(arr, h, w):
    out = np.full((h, w, 3), 255, dtype=np.int16)
    out[: arr.shape[0], : arr.shape[1]] = arr
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ref")
    parser.add_argument("new")
    parser.add_argument("out")
    parser.add_argument("--tolerance", type=int, default=32)
    args = parser.parse_args()

    a, b = load_rgb(args.ref), load_rgb(args.new)
    same_size = a.shape == b.shape
    h, w = max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1])
    a, b = pad(a, h, w), pad(b, h, w)
    diff = np.abs(a - b).max(axis=2)
    changed = diff > args.tolerance
    frac = changed.mean()

    diff_img = np.full((h, w, 3), 255, dtype=np.uint8)
    diff_img[changed] = (220, 0, 0)
    gap = np.full((h, 12, 3), 128, dtype=np.uint8)
    side = np.concatenate([a.astype(np.uint8), gap, b.astype(np.uint8), gap, diff_img], axis=1)
    Image.fromarray(side).save(args.out)

    print(f"size_match={same_size} ref={load_rgb(args.ref).shape[1::-1]} "
          f"new={load_rgb(args.new).shape[1::-1]} differing_pixels={frac:.4%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
