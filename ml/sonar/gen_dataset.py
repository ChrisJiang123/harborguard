"""ml.sonar.gen_dataset —— 合成声呐数据集生成器（C1）。

用法（任务书 C1，本轮试验用 --n 100）::

    python -m ml.sonar.gen_dataset --n 4000 --out ml/datasets/sonar --seed 0

- 每张图 1–4 个目标，另有 10% 仅背景的负样本（标签文件为空）。
- 类别比例 uuv 30% / fish_school 30% / debris 20% / marine_mammal 20%
  （全局配额制，小样本下比例偏差也远小于 3 个百分点）。
- max_range_m 50–300 随机；noise 0.1–0.6；目标距离为量程的 10%–95%；
  bearing 全视场均匀（自然覆盖中央、视场边缘与部分出界）。
- 85/15 分 train/val，输出 YOLO 目录（images/、labels/）与 ml/yolo/sonar.yaml。
- 数据集目录不入 Git（.gitignore: ml/datasets/）；所有路径相对仓库根，无绝对路径。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import cv2
import numpy as np

from ml.sonar.render import CLASS_NAMES, render_ping

REPO_ROOT = Path(__file__).resolve().parents[2]
CLASS_WEIGHTS = (0.30, 0.30, 0.20, 0.20)  # 与 CLASS_NAMES 顺序一一对应
NEG_PROB = 0.10  # 仅背景负样本比例


def _target_params(
    rng: np.random.Generator, cls: str, max_range_m: float, fov_deg: float
) -> dict:
    """按任务书 C1 的尺寸范围采样一个目标。"""
    if cls == "uuv":
        length = float(rng.uniform(2.0, 6.0))
        width = length * float(rng.uniform(0.35, 0.55))
    elif cls == "debris":
        length = float(rng.uniform(6.0, 12.0))
        width = length * float(rng.uniform(0.30, 0.45))
    elif cls == "marine_mammal":
        length = float(rng.uniform(2.0, 5.0))
        width = length * float(rng.uniform(0.25, 0.40))
    else:  # fish_school：直径仅占位，实际散布半径由渲染器采样（5–30 m）
        length = width = 2.0 * float(rng.uniform(5.0, 30.0))
    return {
        "cls": cls,
        "range_m": float(rng.uniform(0.10, 0.95)) * max_range_m,
        "bearing_deg": float(rng.uniform(-fov_deg / 2.0, fov_deg / 2.0)),
        "length_m": length,
        "width_m": width,
        "aspect_deg": float(rng.uniform(-180.0, 180.0)),
    }


def _write_yaml(yaml_path: Path, dataset_dir: Path) -> None:
    """写 ultralytics 数据集 yaml；path 用相对仓库根的路径，绝不写绝对路径。"""
    rel = os.path.relpath(dataset_dir.resolve(), REPO_ROOT).replace(os.sep, "/")
    names = "\n".join(f"  {i}: {n}" for i, n in enumerate(CLASS_NAMES))
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        "# 由 ml/sonar/gen_dataset.py 自动生成（重跑会覆盖）\n"
        f"# path 为相对仓库根路径：训练时从仓库根运行，或将 ultralytics datasets_dir 指到仓库根\n"
        f"path: {rel}\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n"
        f"{names}\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="生成合成声呐 YOLO 数据集（C1）")
    p.add_argument("--n", type=int, default=4000, help="图像总数（任务书 4000；试验可用 100）")
    p.add_argument("--out", default="ml/datasets/sonar", help="输出目录（不入 Git）")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--size", type=int, default=640)
    p.add_argument("--fov", type=float, default=120.0)
    p.add_argument("--yaml", default="ml/yolo/sonar.yaml", help="数据集 yaml 输出路径")
    args = p.parse_args(argv)
    if args.n < 1:
        p.error("--n 需 >= 1")

    out = Path(args.out)
    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    # 清理旧运行残留：重跑若划分/数量不同，旧 split 里的遗留文件会污染数据集
    removed = 0
    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        for f in (out / sub).iterdir():
            if f.is_file() and f.suffix in (".png", ".txt"):
                f.unlink()
                removed += 1
    if removed:
        print(f"清理旧输出 {removed} 个文件")

    # 1) 先定每张图的目标数（10% 负样本 + 1–4 目标），再按比例全局分配类别
    counts_rng = np.random.default_rng([args.seed, 1])
    n_targets = [
        0 if counts_rng.random() < NEG_PROB else int(counts_rng.integers(1, 5))
        for _ in range(args.n)
    ]
    total = sum(n_targets)
    quotas = [int(round(total * w)) for w in CLASS_WEIGHTS]
    quotas[0] = total - sum(quotas[1:])  # 余数归 uuv，保证总数一致
    class_seq = np.concatenate([np.full(q, i, dtype=np.int8) for i, q in enumerate(quotas)])
    np.random.default_rng([args.seed, 2]).shuffle(class_seq)
    class_iter = iter(class_seq.tolist())

    # 2) 85/15 划分（对索引做固定种子重排，与图像内容无关）
    n_val = max(1, int(round(args.n * 0.15)))
    val_ids = set(np.random.default_rng([args.seed, 3]).permutation(args.n)[:n_val].tolist())

    stats = dict.fromkeys(CLASS_NAMES, 0)
    generated = dict.fromkeys(CLASS_NAMES, 0)   # 生成的目标数（含被面积下限丢弃的）
    areas = {name: [] for name in CLASS_NAMES}  # 有标注目标的 bbox 面积 px²
    negatives = 0
    empty_labels = 0
    for i in range(args.n):
        img_rng = np.random.default_rng([args.seed, 1000 + i])
        max_range_m = float(img_rng.uniform(50.0, 300.0))
        noise = float(img_rng.uniform(0.1, 0.6))
        targets = [
            _target_params(img_rng, CLASS_NAMES[next(class_iter)], max_range_m, args.fov)
            for _ in range(n_targets[i])
        ]
        # 渲染器内部随机（斑点/斑块/鱼群散布）也走固定种子，保证整库可重跑
        img, annos = render_ping(
            targets,
            max_range_m=max_range_m,
            fov_deg=args.fov,
            noise=noise,
            seed=args.seed * 1_000_003 + i,
            size=args.size,
        )

        split = "val" if i in val_ids else "train"
        cv2.imwrite(str(out / "images" / split / f"{i:06d}.png"), img)

        lines = []
        for t in targets:
            generated[t["cls"]] += 1
        for a in annos:  # YOLO 归一化 cx cy w h，全部裁剪到 [0, 1]
            x1, y1, x2, y2 = a["bbox"]
            areas[a["cls"]].append((x2 - x1) * (y2 - y1))
            cx = min(max((x1 + x2) / 2 / args.size, 0.0), 1.0)
            cy = min(max((y1 + y2) / 2 / args.size, 0.0), 1.0)
            w = min(max((x2 - x1) / args.size, 0.0), 1.0)
            h = min(max((y2 - y1) / args.size, 0.0), 1.0)
            lines.append(f"{CLASS_NAMES.index(a['cls'])} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            stats[a["cls"]] += 1
        (out / "labels" / split / f"{i:06d}.txt").write_text(
            "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
        )
        negatives += int(not targets)
        empty_labels += int(not lines)

    _write_yaml(Path(args.yaml), out)

    # 3) 数量表（验收：比例与设定相差 < 3 个百分点）
    print(f"数据集: {out}  共 {args.n} 张 (train {args.n - n_val} / val {n_val})，size={args.size}")
    print(f"负样本(仅背景): {negatives} 张 ({negatives / args.n:.1%}，设定 {NEG_PROB:.0%})；空标签文件: {empty_labels}")
    print(f"{'类别':<14}{'数量':>6}{'占比':>9}{'设定':>7}{'偏差':>9}")
    for name, w in zip(CLASS_NAMES, CLASS_WEIGHTS):
        share = stats[name] / total if total else 0.0
        print(f"{name:<14}{stats[name]:>6d}{share:>9.1%}{w:>7.0%}{(share - w) * 100:>+8.1f}pp")
    n_annotated = sum(stats.values())
    print(f"生成目标 {total}，有标注 {n_annotated}（其余为 <16px² 被契约下限丢弃）")

    # 4) 目标像素尺寸统计与小目标保留情况（小目标参考线：面积 <64px²，约 8×8 px）
    print("目标像素尺寸（bbox 面积 px²）:")
    print(f"{'类别':<14}{'生成':>6}{'有标注':>8}{'丢弃':>6}{'中位':>8}{'p10':>8}{'p90':>8}{'<64px²':>8}")
    all_areas: list[float] = []
    dropped_total = 0
    for name in CLASS_NAMES:
        g, k = generated[name], stats[name]
        dropped_total += g - k
        a = np.array(areas[name]) if areas[name] else np.array([0.0])
        all_areas.extend(areas[name])
        print(f"{name:<14}{g:>6d}{k:>8d}{g - k:>6d}"
              f"{np.median(a):>8.0f}{np.percentile(a, 10):>8.0f}{np.percentile(a, 90):>8.0f}"
              f"{float((a < 64).mean()) if len(areas[name]) else 0.0:>7.0%}")
    if all_areas:
        aa = np.array(all_areas)
        n_small = int((aa < 64).sum())
        print(
            f"小目标保留策略: 面积 <64px² 记为小目标，共 {n_small} 个"
            f"（{n_small / len(aa):.0%}），全部保留在图中；"
            f"面积 <16px² 被契约下限丢弃 {dropped_total} 个（占生成目标 "
            f"{dropped_total / max(total, 1):.0%}），远距离小目标不做额外删除"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
