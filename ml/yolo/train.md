# Reproducible YOLO26 Sonar Training (C2)

Data: ml/datasets/sonar/, 4000 **synthetic** sonar images, 85/15 split = 3400/600. Regenerate with `python -m ml.sonar.gen_dataset --n 4000 --out ml/datasets/sonar --seed 0`. Configuration: ml/yolo/sonar.yaml, repository-relative paths. Frozen class IDs: 0 uuv, 1 fish_school, 2 debris, 3 marine_mammal.

Taskbook C2 settings disable mosaic (which breaks fan geometry), disable vertical flips (fan apex stays at bottom), retain horizontal flips (bearing mirror), and use seed=0.

## Lenovo: verified Windows GPU environment

Package on MacBook:

```bash
cd ~/Projects/harborguard && zip -r sonar_dataset.zip ml/datasets/sonar
# Extract at the Lenovo repository root to obtain ml/datasets/sonar/.
```

PowerShell at repository root; verified Python 3.12 + torch 2.14.1+cu130:

```powershell
# Verify actual Ultralytics image/label pairing for 3400/600 images before training.
.\.venv-yolo-train\Scripts\python.exe ml\yolo\check_data.py
# Adjust batch for VRAM. RTX 5060 8 GB: try 32; reduce to 16 on OOM.
.\.venv-yolo-train\Scripts\python.exe -m ultralytics yolo detect train model=yolo26n.pt data=ml/yolo/sonar.yaml imgsz=640 epochs=50 batch=32 patience=10 seed=0 mosaic=0.0 flipud=0.0 fliplr=0.5
```

## Colab fallback

```python
!pip install -q ultralytics
!unzip -q sonar_dataset.zip  # Retain ml/datasets/sonar relative structure.
!yolo detect train model=yolo26n.pt data=ml/yolo/sonar.yaml imgsz=640 epochs=50 batch=32 patience=10 seed=0 mosaic=0.0 flipud=0.0 fliplr=0.5
```

Colab resolves sonar.yaml path ml/datasets/sonar relative to the working directory. Run from the directory containing ml/, matching repository layout.

## After training

```bash
# Copy the nano weights (a few MB) to the frozen path; .gitignore allows best.pt.
cp runs/detect/train*/weights/best.pt ml/yolo/weights/best.pt
# Evaluate mAP50/mAP50-95/class recall/CPU mean latency into metrics.json.
.venv/bin/python ml/yolo/eval.py
# Training machine alternative: python ml/yolo/eval.py --device 0
# C2 gates: synthetic-val mAP50 >=0.8, CPU latency <100 ms/image.
# Integrated B detections should change model from stub to yolo26n.
```

If weights are missing, eval.py exits with an error and does not write metrics.json; it never fabricates placeholder metrics. B GET /api/metrics returns yolo only once metrics.json exists. These are reproducibility instructions, not authorization to retrain during the final demo freeze.
