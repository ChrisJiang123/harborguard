"""C1 声呐渲染器测试（任务书 C1 验收的 pytest 部分）。

运行：.venv/bin/python -m pytest tests -q
覆盖：契约签名/确定性/全局随机状态/扇形几何/声影朝向/标注有效性/
YOLO 归一化范围/负样本空标签/数据集 yaml 无绝对路径/各类形态与出界。
"""

from __future__ import annotations

import random

import numpy as np
import pytest

from ml.sonar.gen_dataset import main as gen_main
from ml.sonar.render import CLASS_NAMES, render_ping

SIZE = 320  # 测试用小图加速


def _uuv(rng_m: float = 80.0, brg: float = 0.0, L: float = 4.0, W: float = 1.6,
         asp: float = 0.0) -> dict:
    return dict(cls="uuv", range_m=rng_m, bearing_deg=brg, length_m=L,
                width_m=W, aspect_deg=asp)


# ---------------------------------------------------------------- 契约与确定性

def test_signature_and_seed_determinism():
    targets = [_uuv(), dict(cls="fish_school", range_m=60.0, bearing_deg=10.0,
                            length_m=20.0, width_m=20.0, aspect_deg=0.0)]
    img_a, ann_a = render_ping(targets, seed=42, size=SIZE)
    img_b, ann_b = render_ping(targets, seed=42, size=SIZE)
    assert img_a.dtype == np.uint8 and img_a.shape == (SIZE, SIZE)
    assert np.array_equal(img_a, img_b), "同 seed 必须逐像素一致"
    assert ann_a == ann_b
    img_c, _ = render_ping(targets, seed=43, size=SIZE)
    assert not np.array_equal(img_a, img_c), "不同 seed 应产生不同图像"


def test_no_global_rng_pollution():
    np_before = np.random.get_state()
    py_before = random.getstate()
    render_ping([_uuv()], seed=1, size=SIZE)
    render_ping([], seed=2, size=SIZE)
    np_after = np.random.get_state()
    assert np.array_equal(np_before[1], np_after[1]) and np_before[2:] == np_after[2:]
    assert py_before == random.getstate()


def test_bad_inputs_raise():
    with pytest.raises(ValueError):
        render_ping([], fov_deg=200.0)
    with pytest.raises(ValueError):
        render_ping([dict(cls="vessel", range_m=10.0, bearing_deg=0.0,
                          length_m=1.0, width_m=1.0, aspect_deg=0.0)])


# ---------------------------------------------------------------- 扇形几何

def test_sector_geometry_apex_bottom_outside_black():
    img, _ = render_ping([], seed=0, size=SIZE, fov_deg=120.0, noise=0.4)
    # 扇形外为黑：四个角 + 顶边中点（120° 时顶边整体在量程外）
    for y, x in [(0, 0), (0, SIZE - 1), (SIZE - 1, 0), (SIZE - 1, SIZE - 1), (0, SIZE // 2)]:
        assert img[y, x] == 0, f"({y},{x}) 应为扇形外黑像素"
    # 顶点在底部中央：底行仅中心附近属扇形内，中距中心区域应有回波内容
    assert img[SIZE // 2, SIZE // 2 - 20 : SIZE // 2 + 20].max() > 0


# ---------------------------------------------------------------- 声影与方位

def test_uuv_shadow_on_far_side():
    # 宽目标放大影子条带；低噪背景；对比影子区与近侧同形状区
    img, annos = render_ping(
        [_uuv(rng_m=90.0, L=4.0, W=8.0, asp=0.0)],
        max_range_m=120.0, noise=0.05, seed=7, size=SIZE,
    )
    assert annos, "uuv 应产出标注"
    # r_max_px = min(319, 159/sin60°) ≈ 183.6；影子 92–104m → y∈[160,178]，近侧 76–88m → y∈[184,203]
    shadow = img[162:176, 150:170].mean()
    near = img[186:200, 150:170].mean()
    assert shadow < near * 0.6, f"声影区({shadow:.1f})应显著暗于近侧同形状区({near:.1f})"


def test_bearing_sign_maps_to_image_side():
    _, right = render_ping([_uuv(brg=30.0)], seed=3, size=SIZE)
    _, left = render_ping([_uuv(brg=-30.0)], seed=3, size=SIZE)
    cx_r = (right[0]["bbox"][0] + right[0]["bbox"][2]) / 2
    cx_l = (left[0]["bbox"][0] + left[0]["bbox"][2]) / 2
    assert cx_r > SIZE / 2, "正 bearing（右）目标框中心应在图像右半"
    assert cx_l < SIZE / 2, "负 bearing（左）目标框中心应在图像左半"


# ---------------------------------------------------------------- 标注有效性

def test_all_classes_render_with_valid_boxes():
    targets = [
        dict(cls="uuv", range_m=75.0, bearing_deg=0.0, length_m=4.0, width_m=1.8, aspect_deg=0.0),
        dict(cls="fish_school", range_m=60.0, bearing_deg=25.0, length_m=20.0, width_m=20.0, aspect_deg=0.0),
        dict(cls="debris", range_m=16.0, bearing_deg=-10.0, length_m=8.0, width_m=3.0, aspect_deg=90.0),
        dict(cls="marine_mammal", range_m=110.0, bearing_deg=-40.0, length_m=3.0, width_m=1.0, aspect_deg=70.0),
    ]
    img, annos = render_ping(targets, max_range_m=150.0, seed=11, size=640)
    assert [a["cls"] for a in annos] == ["uuv", "fish_school", "debris", "marine_mammal"]
    for a in annos:
        x1, y1, x2, y2 = a["bbox"]
        assert 0 <= x1 < x2 <= 640 and 0 <= y1 < y2 <= 640, f"像素框无效: {a}"


def test_coverage_center_edge_near_partial_out_of_view():
    """中央 / 视场边缘 / 近距离 / 部分出界四类情况，框必须有效。"""
    targets = [
        dict(cls="uuv", range_m=75.0, bearing_deg=0.0, length_m=4.0, width_m=1.8, aspect_deg=0.0),      # 中央
        dict(cls="uuv", range_m=100.0, bearing_deg=55.0, length_m=5.0, width_m=2.0, aspect_deg=30.0),   # 视场边缘（部分出界）
        dict(cls="debris", range_m=16.0, bearing_deg=-10.0, length_m=8.0, width_m=3.0, aspect_deg=90.0),  # 近距离
        dict(cls="uuv", range_m=100.0, bearing_deg=-55.0, length_m=5.0, width_m=2.0, aspect_deg=-30.0),  # 反侧边缘
    ]
    _, annos = render_ping(targets, max_range_m=150.0, seed=9, size=640)
    assert len(annos) >= 3, f"四类情况多数应保留标注: {annos}"
    for a in annos:
        x1, y1, x2, y2 = a["bbox"]
        assert 0 <= x1 < x2 <= 640 and 0 <= y1 < y2 <= 640


def test_tiny_distant_target_dropped_by_area_filter():
    _, annos = render_ping(
        [_uuv(rng_m=149.0, L=0.4, W=0.2)], max_range_m=150.0, seed=5, size=SIZE
    )
    assert annos == [], "面积 < 16 px 的框必须丢弃"


# ---------------------------------------------------------------- 数据集生成

def test_gen_dataset_labels_and_layout(tmp_path):
    n = 40
    out = tmp_path / "ds"
    gen_main(["--n", str(n), "--out", str(out), "--seed", "0",
              "--size", "320", "--yaml", str(tmp_path / "sonar.yaml")])
    imgs = sorted(out.glob("images/*/*.png"))
    lbls = sorted(out.glob("labels/*/*.txt"))
    assert len(imgs) == n and len(lbls) == n, "图像与标签一一对应"
    assert set(p.parent.name for p in imgs) == {"train", "val"}

    empties = 0
    for f in lbls:
        text = f.read_text(encoding="utf-8")
        if not text.strip():
            empties += 1
            continue
        for line in text.splitlines():
            parts = line.split()
            assert len(parts) == 5, f"YOLO 行需 5 列: {line!r}"
            c, x, y, w, h = (float(v) for v in parts)
            assert 0 <= c <= 3, f"类别 ID 越界: {line!r}"
            assert all(0.0 <= v <= 1.0 for v in (x, y, w, h)), f"归一化坐标越界: {line!r}"
            assert w > 0 and h > 0
    assert empties >= 1, "10% 负样本应产生空标签文件（seed=0, n=40 固定结果）"

    # 划分比例 ~85/15（±1 张容差）
    n_val = sum(1 for p_ in imgs if p_.parent.name == "val")
    assert abs(n_val - round(n * 0.15)) <= 1


def test_gen_dataset_rerun_cleans_stale_files(tmp_path):
    """重跑（不同 n/划分）不得留下旧 split 的残留文件。"""
    out = tmp_path / "ds"
    gen_main(["--n", "10", "--out", str(out), "--seed", "0",
              "--size", "320", "--yaml", str(tmp_path / "a.yaml")])
    gen_main(["--n", "6", "--out", str(out), "--seed", "0",
              "--size", "320", "--yaml", str(tmp_path / "b.yaml")])
    imgs = list(out.glob("images/*/*.png"))
    lbls = list(out.glob("labels/*/*.txt"))
    assert len(imgs) == 6 and len(lbls) == 6, f"重跑后应只有 6 张图/标签，得到 {len(imgs)}/{len(lbls)}"


def test_gen_dataset_yaml_relative_and_names(tmp_path):
    out = tmp_path / "ds"
    yaml_path = tmp_path / "sonar.yaml"
    gen_main(["--n", "4", "--out", str(out), "--seed", "1",
              "--size", "320", "--yaml", str(yaml_path)])
    text = yaml_path.read_text(encoding="utf-8")
    assert "/Users/" not in text, "yaml 不得包含 macOS 绝对路径"
    path_line = next(l for l in text.splitlines() if l.startswith("path:"))
    assert not path_line.split(":", 1)[1].strip().startswith("/"), "path 必须是相对路径"
    # 类别顺序：0 uuv，1 fish_school，2 debris，3 marine_mammal
    names_block = text.split("names:", 1)[1]
    order = [line.strip() for line in names_block.splitlines() if line.strip()]
    assert order == ["0: uuv", "1: fish_school", "2: debris", "3: marine_mammal"]


def test_render_seed_matches_contract_docstring_roundtrip():
    """回归：标注 bbox 与图像同源——把 bbox 中心反算回像素，验证框落在非零区域附近。"""
    img, annos = render_ping([_uuv(rng_m=70.0, L=4.0, W=2.0)], seed=21, size=640)
    assert annos
    x1, y1, x2, y2 = annos[0]["bbox"]
    patch = img[y1 : y2 + 1, x1 : x2 + 1]
    assert patch.max() > 0, "标注框内应有回波（框覆盖回波）"
    # 框外上方（更远一侧为声影方向，取框正上方 5px 带内的均值不高于框内）
    assert img[max(0, y1 - 6) : y1, x1:x2].mean() <= patch.mean() + 5
