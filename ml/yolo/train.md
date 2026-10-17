# YOLO26 声呐检测训练说明（C2，可重跑）

数据：`ml/datasets/sonar/`（4000 张**合成**声呐图，85/15 = 3400/600，由
`python -m ml.sonar.gen_dataset --n 4000 --out ml/datasets/sonar --seed 0` 一键重跑）。
数据集配置：`ml/yolo/sonar.yaml`（仓库相对路径）。
类别 ID 固定：`0 uuv，1 fish_school，2 debris，3 marine_mammal`（共享契约）。

训练参数依据任务书 C2：关 mosaic（拼接破坏扇形几何）、关上下翻转（扇形顶点在底部）、
保留左右翻转（等价方位镜像）、`seed=0` 可复现。

## 1. Lenovo（Windows，已验证 GPU 环境）

数据打包上传（MacBook）：

```bash
cd ~/Projects/harborguard && zip -r sonar_dataset.zip ml/datasets/sonar
# 拷到 Lenovo 后解压到仓库根，得到 ml/datasets/sonar/
```

Lenovo（PowerShell，仓库根；环境为已验证的 Python 3.12 + torch 2.14.1+cu130）：

```powershell
# 训练前自检：用 Ultralytics 实际加载器确认 3400/600 张与标签配对
.\.venv-yolo-train\Scripts\python.exe ml\yolo\check_data.py
# 训练（batch 按显存调整；RTX 5060 8GB 从 32 起，OOM 则降 16）
.\.venv-yolo-train\Scripts\python.exe -m ultralytics yolo detect train model=yolo26n.pt data=ml/yolo/sonar.yaml imgsz=640 epochs=50 batch=32 patience=10 seed=0 mosaic=0.0 flipud=0.0 fliplr=0.5
```

## 2. Colab（备选）

```python
!pip install -q ultralytics
!unzip -q sonar_dataset.zip   # 解压到 ml/datasets/sonar（保持相对路径结构）
!yolo detect train model=yolo26n.pt data=ml/yolo/sonar.yaml imgsz=640 epochs=50 batch=32 patience=10 seed=0 mosaic=0.0 flipud=0.0 fliplr=0.5
```

注意：Colab 的 `sonar.yaml` 中 `path: ml/datasets/sonar` 按相对路径解析，
需在包含 `ml/` 的目录层级下运行（与仓库结构一致）。

## 3. 训练完成后（回 MacBook 或在训练机执行）

```bash
# 1) 权重复制到契约路径（nano 权重几 MB；.gitignore 已放行 best.pt）
cp runs/detect/train*/weights/best.pt ml/yolo/weights/best.pt

# 2) 评估：mAP50 / mAP50-95 / 各类召回 / CPU 平均耗时 -> ml/yolo/metrics.json
.venv/bin/python ml/yolo/eval.py            # 或训练机上: python ml/yolo/eval.py --device 0

# 3) 验收线（任务书 C2）：合成验证集 mAP50 >= 0.8；CPU 每张 < 100 ms
# 4) 后端接入后，detection 事件 model 应从 stub 变为 yolo26n
```

`eval.py` 在权重缺失时直接报错退出，**不写 metrics.json**（不做占位数据）。
metrics.json 就绪后 B 的 `GET /api/metrics` 才会返回 yolo 字段。
