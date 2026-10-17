"""ml.yolo —— YOLO26 声呐目标检测（C2 准备就绪，训练未开始）。

- infer.py: SonarDetector（共享契约 v1 §7；B 在后端 import）✅ 已实现
- check_data.py: 用 Ultralytics 实际加载器验证 sonar.yaml ✅
- train.md: Lenovo/Colab 可重跑训练命令 ✅
- eval.py: mAP/召回/CPU 耗时 -> metrics.json ✅（无权重时不写占位数据）
- weights/best.pt: ⏳ 待训练产出（*.pt 默认忽略，best.pt 已放行入库）
"""
