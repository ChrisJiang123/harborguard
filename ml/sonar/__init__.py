"""ml.sonar —— 声呐图渲染与合成数据集（C1 已实现）。

- render.py: render_ping（共享契约 v1 §7，签名未改；B 直接 import）
- gen_dataset.py: 批量生成 YOLO 训练集（python -m ml.sonar.gen_dataset）
- preview.py: 抽样可视化 samples.png（python -m ml.sonar.preview）
- 测试: tests/test_sonar_render.py（.venv/bin/python -m pytest tests -q）
"""
