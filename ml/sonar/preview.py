"""C1 synthetic dataset preview: sample n images (default16), draw boxes/classes and assemble a grid.
Example: python -m ml.sonar.preview.
"""


from __future__ import annotations

import argparse
import math
from pathlib import Path

import cv2
import numpy as np

from ml.sonar.render import CLASS_NAMES

# BGR palette; English class names avoid unavailable CJK OpenCV fonts.
_COLORS = ((0, 255, 0), (255, 255, 0), (0, 0, 255), (0, 255, 255))


def _load_labels(lbl_path: Path) -> list[tuple[int, float, float, float, float]]:
    out = []
    if not lbl_path.exists():
        return out
    for line in lbl_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 5:
            c, x, y, w, h = (float(v) for v in parts)
            out.append((int(c), x, y, w, h))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Preview sampled synthetic sonar images (C1)")
    p.add_argument("--dataset", default="ml/datasets/sonar")
    p.add_argument("--out", default="ml/sonar/samples.png")
    p.add_argument("--n", type=int, default=16)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--cols", type=int, default=4)
    args = p.parse_args(argv)

    ds = Path(args.dataset)
    images = sorted((ds / "images/train").glob("*.png")) + sorted((ds / "images/val").glob("*.png"))
    if not images:
        raise SystemExit(f"No images: {ds}/images/{{train,val}}/*.png; run gen_dataset first")
    pick_rng = np.random.default_rng([args.seed, 7])
    chosen = pick_rng.choice(len(images), size=min(args.n, len(images)), replace=False)

    cell = cv2.imread(str(images[0]), cv2.IMREAD_GRAYSCALE)
    if cell is None:
        raise SystemExit(f"Cannot read: {images[0]}")
    h, w = cell.shape

    n = len(chosen)
    cols = max(1, args.cols)
    rows = math.ceil(n / cols)
    grid = np.zeros((rows * h, cols * w), dtype=np.uint8)
    for k, idx in enumerate(chosen):
        img_path = images[int(idx)]
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        lbl = _load_labels(ds / "labels" / img_path.parent.name / (img_path.stem + ".txt"))
        for c, cx, cy, bw, bh in lbl:
            x1 = int((cx - bw / 2) * w)
            y1 = int((cy - bh / 2) * h)
            x2 = int((cx + bw / 2) * w)
            y2 = int((cy + bh / 2) * h)
            color = _COLORS[c % len(_COLORS)]
            cv2.rectangle(bgr, (x1, y1), (x2, y2), color, 2)
            name = CLASS_NAMES[c] if 0 <= c < len(CLASS_NAMES) else str(c)
            ty = max(14, y1 - 5)
            cv2.putText(bgr, name, (x1 + 2, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(bgr, name, (x1 + 2, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        color, 1, cv2.LINE_AA)
        if not lbl:  # Negative sample: background only.
            cv2.putText(bgr, "background", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (200, 200, 200), 1, cv2.LINE_AA)
        r, cidx = divmod(k, cols)
        grid[r * h : (r + 1) * h, cidx * w : (cidx + 1) * w] = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), grid)
    print(f"Wrote {out} ({n}-image grid sampled from {len(images)} images)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
