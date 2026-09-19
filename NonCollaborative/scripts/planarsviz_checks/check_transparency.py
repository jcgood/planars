"""Report how much of a PNG's background is fully transparent.

Plan section 4.3 step 4: the tree-count "house style" charts must have a
transparent background (an earlier version rendered solid black, caught only
by checking alpha). Render with `pdftocairo -png -transp`, then run this on
the PNG.

Usage:
    python scripts/planarsviz_checks/check_transparency.py file.png [file2.png ...]
"""

import sys

from PIL import Image

for path in sys.argv[1:]:
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    alpha = image.getchannel("A")
    flatten = getattr(alpha, "get_flattened_data", None) or alpha.getdata  # getdata goes in Pillow 14
    pixels = list(flatten())
    transparent = sum(1 for a in pixels if a == 0) / len(pixels)
    corners = [alpha.getpixel((0, 0)), alpha.getpixel((width - 1, 0)),
               alpha.getpixel((0, height - 1)), alpha.getpixel((width - 1, height - 1))]
    print(f"{path}: {transparent:.1%} of pixels fully transparent; corner alpha {corners}")
