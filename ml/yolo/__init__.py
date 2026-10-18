"""C2 YOLO26 sonar detector, historically accepted on the Mac demo host. infer.py provides frozen
SonarDetector; check_data uses the real Ultralytics loader; train.md has Lenovo/Colab commands; eval
writes measured metrics only. Lenovo best.pt used UATD initialization,e50/b16/seed0. Recorded Mac
synthetic mAP50=0.9771, CPU49.7ms; B emits yolo26n. See ACCEPTANCE-MAC.md; metrics.json is
the2026-10-17 measurement.
"""
