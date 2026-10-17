# C2 Mac 演示机验收记录（2026-10-17）

权重来源：Lenovo 训练交付 ZIP `~/Downloads/sonar4_uatd_init_yolo26n_sonar4_uatdinit_e50_b16_s0_20261017_024524_496351.zip`
（文件名信息：yolo26n · 50 epoch · batch 16 · seed 0）。本记录只覆盖 Mac 侧验收；
训练环境结论见 ZIP 内 REPORT.md（Windows · RTX 5060 Laptop · torch 2.14.1+cu130）。

## 1. 交付核验

| 项 | 结果 |
| --- | --- |
| ZIP SHA256 | `4fb70ca0292b21cbe8353272e037c7a7d79d2b3058b94afff20b2613d2759393` |
| best.pt SHA256（自述 best.pt.sha256 vs 实测） | `2cad3146fa4b98516efa0057367c3c5d53220dc2a3246058f5608094a6568839` 一致 |
| MANIFEST.sha256.json | 全部条目逐一复算，一致 |
| classes.json / portable_data.yaml / checkpoint 内部 model.names | 三处一致：`0 uuv / 1 fish_school / 2 debris / 3 marine_mammal`，与共享契约类别顺序逐字相同 |
| 安装 | `cp` 至 `ml/yolo/weights/best.pt`（安装前目录仅有 .gitkeep，无旧权重需备份）；安装后复算 SHA256 一致 |
| 训练信息（REPORT.md） | UATD 十类初始化（逐项张量核验兼容复制），50 epoch、best=epoch40、patience=10 早停；train 3400/val 600 |

## 2. Mac 评估（现有 .venv 环境，全部 CPU）

命令：`.venv/bin/python -m ml.yolo.eval`（或 `python ml/yolo/eval.py`，已支持两种调用）（600 张合成 val 全量验证 + SonarDetector
CPU 路径预热 1 张后连续计时 20 张，强制 `device="cpu"`）。

| 指标 | 实测 | 验收线 |
| --- | --- | --- |
| mAP50 | **0.9771** | ≥ 0.8 ✅ |
| mAP50–95 | 0.7485 | — |
| 召回 uuv / fish_school / debris / marine_mammal | 0.9774 / 0.9439 / 0.9962 / 0.9314 | — |
| CPU 平均耗时 | **49.7 ms/张**（首测 52.1，复测 49.7，负载抖动，均 < 100 ms）| < 100 ms ✅ |

与 Lenovo 端报告 mAP50=0.97763 吻合（同一权重、两台机器分别验证）。
`ml/yolo/metrics.json` 已生成（schema 与任务书一致），本次实测取代任何占位数值。

## 3. 后端集成

- 重启本机后端（旧进程启动时无权重，detection 均为 `model="stub"`）
- 场景 A（speed 10）：detection 事件 `model="yolo26n"`；首个真实识别
  `det-5 uuv conf=0.72`（此前 unknown/conf=0 为主动 ping 前的被动检测，与契约一致）
- `GET /api/metrics`：`yolo` 字段即第 2 节实测值，`lora=null`（C4 LoRA 尚未部署，符合预期）
- 验证完成后场景已 reset，后端留在空闲状态

## 4. 结论与边界

- C2 验收两项硬指标（mAP50、CPU 耗时）在 Mac 演示机上**通过**
- 指标全部来自合成数据；真实声呐（如 UATD 测试集）泛化能力不在本次验收范围
- UATD 初始化相对随机初始化的增益未做对照实验，不宣称迁移收益
