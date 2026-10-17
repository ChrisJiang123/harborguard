"""HarborGuard ML 模块（负责人 C）。

子模块：
- ml.sonar：声呐图渲染器 render_ping（C1）与合成数据集。
- ml.yolo：YOLO26 训练产物、SonarDetector 推理接口（C2）。
- ml.lora：蒸馏数据、LoRA 训练、GGUF 导出与评估（C4）。

与 B 的接口签名见 docs/shared-contract-v1.md §7，一字不改。
"""
