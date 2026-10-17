"""ml.yolo —— YOLO26 声呐目标检测（C2 已验收，Mac 演示机）。

- infer.py: SonarDetector（共享契约 v1 §7；B 在后端 import）✅ 已实现
- check_data.py: 用 Ultralytics 实际加载器验证 sonar.yaml ✅
- train.md: Lenovo/Colab 可重跑训练命令 ✅
- eval.py: mAP/召回/CPU 耗时 -> metrics.json ✅（无权重时不写占位数据）
- weights/best.pt: ✅ Lenovo 训练交付（UATD 初始化，e50/b16/seed0），
  Mac 验收 mAP50=0.9771 / CPU 52.1ms，后端 detection.model=yolo26n（见 ACCEPTANCE-MAC.md）
- metrics.json: ✅ Mac 实测（2026-10-17），后端 /api/metrics 的 yolo 字段
"""
