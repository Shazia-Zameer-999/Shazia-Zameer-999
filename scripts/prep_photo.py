#!/usr/bin/env python3
"""
prep_photo.py — turn a normal photo into a clean grayscale source
image that converts well to ASCII art.

Pipeline:
  1. Remove the background with rembg (isolate the subject).
  2. Boost local contrast with OpenCV CLAHE.
  3. Composite onto pure white (so background -> blank ASCII glyph).

Usage:
    python scripts/prep_photo.py source-photo.jpg
Output:
    source-prepped.png (grayscale, same folder as input unless -o given)
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def remove_background(img: Image.Image) -> Image.Image:
    """Returns an RGBA image with background removed via rembg.

    Falls back to the original image (no bg removal) if rembg isn't
    installed, or if it's installed but its ONNX runtime backend is
    missing/broken — either way this should never crash the pipeline.
    """
    try:
        from rembg import remove
    except ImportError:
        print("rembg not installed — skipping background removal "
              '(run: pip install "rembg[cpu]")', file=sys.stderr)
        return img.convert("RGBA")

    try:
        return remove(img)
    except Exception as e:
        print(f"rembg failed to run ({e!s}) — skipping background removal. "
              'Fix with: pip install "rembg[cpu]"', file=sys.stderr)
        return img.convert("RGBA")


def boost_contrast(gray: np.ndarray) -> np.ndarray:
    """CLAHE local-contrast boost. Flat lighting -> real highlights/shadows."""
    import cv2
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    return clahe.apply(gray)


def composite_on_white(rgba: Image.Image) -> Image.Image:
    """Flatten transparent background to pure white."""
    bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, rgba).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="source photo (jpg/png)")
    ap.add_argument("-o", "--output", default=None,
                     help="output path (default: source-prepped.png next to input)")
    ap.add_argument("--width", type=int, default=800,
                     help="resize width before processing (default 800)")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output) if args.output else in_path.with_name("source-prepped.png")

    img = Image.open(in_path).convert("RGB")

    # Resize so downstream processing is fast and predictable.
    w = args.width
    h = int(img.height * (w / img.width))
    img = img.resize((w, h), Image.LANCZOS)

    no_bg = remove_background(img)          # RGBA, subject isolated
    flat = composite_on_white(no_bg)         # RGB, white background
    gray = np.array(flat.convert("L"))       # grayscale

    try:
        gray = boost_contrast(gray)
    except ImportError:
        print("opencv-python not installed — skipping CLAHE contrast boost "
              "(run: pip install opencv-python)", file=sys.stderr)

    Image.fromarray(gray).save(out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
