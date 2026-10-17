# ml/ —— HarborGuard 模型模块（负责人 C）

```
ml/
  __init__.py
  sonar/    __init__.py  render.py  gen_dataset.py  preview.py     # C1 已实现
  yolo/     __init__.py  sonar.yaml  train.md  infer.py  eval.py   # C2 待实现
            weights/best.pt  metrics.json
  lora/     gen_contexts.py  distill.py  train_lora.ipynb           # C4 待实现
            Modelfile  eval.py  metrics.json
  datasets/ (gitignored —— 4000 张合成数据集，由 gen_dataset --n 4000 --seed 0 重跑生成)
```

- `ml/sonar/render.py::render_ping` 与 `ml/yolo/infer.py::SonarDetector` 的签名
  见 `../docs/shared-contract-v1.md` §7（B 与 C 的 Python 接口），一字不改。
- YOLO 类别 ID：`0 uuv，1 fish_school，2 debris，3 marine_mammal`。
- 随机数一律用固定 seed；数据集与训练命令写成可重跑脚本。
- 训练环境与运行环境分开：见 `../README.md`「三套环境」。
