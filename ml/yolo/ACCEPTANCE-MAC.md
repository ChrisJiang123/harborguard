# C2 Mac Demo Machine Acceptance (2026-10-17)

Weights came from Lenovo training ZIP `~/Downloads/sonar4_uatd_init_yolo26n_sonar4_uatdinit_e50_b16_s0_20261017_024524_496351.zip` (yolo26n, 50 epochs, batch 16, seed 0). This record covers Mac acceptance only; training environment evidence is REPORT.md inside the ZIP (Windows, RTX 5060 Laptop, torch 2.14.1+cu130).

## Delivery checks

| Item | Result |
| --- | --- |
| ZIP SHA256 | 4fb70ca0292b21cbe8353272e037c7a7d79d2b3058b94afff20b2613d2759393 |
| best.pt declared/measured SHA256 | 2cad3146fa4b98516efa0057367c3c5d53220dc2a3246058f5608094a6568839, matched |
| MANIFEST.sha256.json | Every entry recalculated and matched |
| classes.json / portable_data.yaml / checkpoint model.names | All three: 0 uuv / 1 fish_school / 2 debris / 3 marine_mammal, exactly the frozen class order |
| Installation | Copied to ml/yolo/weights/best.pt; directory previously contained only .gitkeep, so no old weights needed backup; installed SHA matched |
| REPORT.md training | Ten-class UATD initialization with compatible tensor copies individually verified; 50 epochs, best epoch 40, patience 10 early stopping; train 3400/val 600 |

## Mac evaluation (existing .venv, CPU only)

Command: `.venv/bin/python -m ml.yolo.eval` or `python ml/yolo/eval.py`. Full 600-image synthetic validation; one SonarDetector warmup image, then 20 timed images, forced device=cpu.

| Metric | Measured | Acceptance |
| --- | --- | --- |
| mAP50 | 0.9771 | >=0.8 PASS |
| mAP50–95 | 0.7485 | — |
| Recall uuv/fish_school/debris/marine_mammal | 0.9774 / 0.9439 / 0.9962 / 0.9314 | — |
| Mean CPU latency | 49.7 ms/image; first 52.1, repeat 49.7, load variation; both <100 ms | <100 ms PASS |

Consistent with Lenovo mAP50=0.97763 for the same weights, independently tested on two machines. ml/yolo/metrics.json was generated using actual measurements, replacing any placeholders and matching the taskbook schema.

## Backend integration

- Restarted local B; its earlier weightless process had produced model=stub.
- A at speed 10 produced detection model=yolo26n; first actual classification det-5 uuv conf=0.72. Earlier unknown/conf=0 entries were pre-active-ping passive detections, consistent with contract.
- GET /api/metrics returned the measured yolo values above and lora=null, as C4 had not yet been deployed.
- Reset the scenario after validation, leaving B idle.

## Conclusions and limits

C2 mAP50 and CPU latency gates passed on the Mac demo machine. All evaluation images were synthetic; real-sonar/UATD test-set generalization was not evaluated. No controlled random-initialization comparison was run, so no UATD transfer-learning gain is claimed.
