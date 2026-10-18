# ml/ — HarborGuard Model Modules (Owner C)

```
ml/
  __init__.py
  sonar/    __init__.py  render.py  gen_dataset.py  preview.py     # C1 implemented
  yolo/     __init__.py  sonar.yaml  train.md  infer.py  eval.py   # C2 accepted on Mac demo machine
            weights/best.pt  metrics.json  ACCEPTANCE-MAC.md
  lora/     __init__.py  gen_contexts.py  capture_real.py           # C4 scripts implemented
            distill.py  train_lora.ipynb  Modelfile  eval.py
            metrics.json  datasets/ (gitignored; reproducible scripts)
  datasets/ (gitignored; regenerate 4000 synthetic images with gen_dataset --n 4000 --seed 0)
```

- Exact frozen signatures of ml/sonar/render.py::render_ping and ml/yolo/infer.py::SonarDetector are in ../docs/shared-contract-v1.md §7 (B/C Python interfaces).
- YOLO class IDs: 0 uuv, 1 fish_school, 2 debris, 3 marine_mammal.
- Use fixed random seeds and reproducible dataset/training scripts.
- Keep training environments separate from runtime; see ../README.md.
