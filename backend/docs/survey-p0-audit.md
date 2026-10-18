# 场景 B 未决观测与投影关联 P0 复验

日期：2026-10-17，America/Los_Angeles。按负责人要求先修业务正确性，不等待LoRA、不重新训练、不补场景数据，不以浏览器流程通过代替复航判定验收。

## 版本核对

- 已保存的真实失败运行：本地组合 `3f237b87866592d43064c76a93083c0f67ac3bd0`，B基线main `8613834e7430eee40d2f020e6277dbdec72ca1f5`、C `6389b705bec35b8fc44018d1c14d770f2a82b364`。B最终8 clear/2 blocked/2 unsurveyed，错误节省12小时。
- Lenovo消息没有给出其审计checkout的精确SHA，故**不能擅自认定双方审计SHA完全相同**。但本地原始坏帧重现了相同的250m、UUV/conf0.595196及0m无检出；原始数据保留在[失败记录](evidence/survey-p0-original-failure.json)。
- 本轮开始时官方main为 `c7840813c6a98c32ada5b91da6e6221dc74b121d`，已含B #10（`6353421`实现）和交接 #12；C仍为上述6389b70。#10已修未决保护/有界重试及C扇形投影，但灾害候选仍按真类debris筛选、用真值ID识别，审计未通过“真值无关”。
- 本轮分支 `codex/harborguard-survey-observation-audit` 从该main创建。只修改B实现、测试和说明；A/C/shared/data及训练文件不改，不自动Merge或Force Push。
- 本轮实现提交：`97a8c751c8ba9a18a6e89ace79f27df99751f28f`。后续证据文档提交不改变该算法源码。

## 本轮 B 修改

1. 新增合成主动观测边界 `backend/app/sim/sonar.py`：所有几何反射体生成不带真类/真值目标ID的匿名米级位置观测。改变真类或真值ID不会改变观测身份；不是只把“debris过滤”换个函数藏起来。
2. 灾害策略只使用该观测位置、浮标几何和模型输出。空结果、非debris、低置信结果、近场或保护条件不足均保持未决；coverage即使为1也不能抹掉。观测消失也不会自动清除之前未决。
3. 保留20仿真秒冷却和最多3次实际检测预算，优先不同且物理可用的浮标。按不带类别的观测位置做40m门限近邻连续关联，跨网格移动也不重置预算；耗尽后仍unsurveyed。未发射的近场/保护阻断不消耗实际发射计数，不捏造成功图像。拥挤/交叉接触的身份精度不在本次合成B验收中，可能保守合并，不宣传真值对象级识别。
4. 给未决记录持久化reason，并通过既有log事件解释近场、禁Ping、漏检、低置信或非碎片及重试次数；不新增公共字段/枚举。日志按原因和实际发射次数去重，避免每tick刷屏。
5. 位置量化的半对角误差范围涉及相邻分区时，两区都保守保持未决/阻塞，避免边界舍入让危险落入另一绿色区。该不确定性只是合成观测假设，不代表实海定位误差模型。
6. 将场景到声呐图的生成放在sim边界，真类只供生成物理图像。输出分类来自检测器；图中其他反射体也参与渲染，避免硬编码“这里只有一个debris”。
7. Pinger关联使用显式观测/预测的距离和方位，经已存在的B内部 `sonar_pixel` 投影匹配；移除缺少预测时从渲染目标range猜关联的路径。新测试以C真实render_ping生成的两个框验证：旧线性公式会选错框，当前公式选中正确距离/方位框。
8. BFS仍只走clear航道、开放相邻clear泊位；节省时间按当前clear分区数×SURVEY_H计算，restricted不再误计入。没有把9h或12h写成修复目标，真实模型测试已改为核对实际分区状态派生值。

0m保持0m：近场不可靠时不发射、不改30m或挪位置。图像生成遇到0距离时方位本身无定义，显式以0°表达该退化输入，距离仍为0；真实C调查仍受30m边界保护。原完整桩识别正例继续保留4个检测和6/4/2断言，不靠把所有区域改黄让测试通过。

## 复验与实测

执行记录及文件哈希见 [机器证据](evidence/survey-p0-20261017.json)。原始JUnit和新版本完整模型调用保留于本地忽略目录`artifacts/survey-audit/`。

最终全量 **211 PASS、2 SKIP，93.88s**；专项35 PASS。跳过的2项缺少另一个COCO冒烟权重，交付声呐权重已真实运行。Ruff、compileall、pip check及diff检查通过。

同一最终算法的独立HTTP/WS运行：冷启动5.898s，同库重启5.785s；294帧，平均4.99733Hz，最大间隔363.56ms，P99间隔267.65ms，状态包最大25,381B；实际模板建议、批准/驳回、断线补偿和同库重启持久化通过。RSS峰值430.85MiB、单核CPU均值39.25%，是短样本，不是20分钟耐久；不是浏览器业务验收或实海安全证明。

| 案例 | 实际结果 / 判定 |
| --- | --- |
| 固定原坏帧250m、seed2029167940 | 同权重仍预测UUV、conf约0.595196；不声称模型已修好。重放这一错误输出，coverage跨0.9、三次耗尽后仍unsurveyed，未进入复航路线：PASS |
| 固定原坏帧0m、seed1926751965 | 同权重仍无检出；当前策略保留near_field、0次实际检测、coverage=1仍unsurveyed：PASS |
| 受控漏检、误分类、低置信 | .1/20.1/30.7/40.1/40.2/1000仿真秒检查，最多3次，覆盖率达标仍未决：PASS |
| 真类/ID读取保护 | 读world目标cls或id就抛异常的对象，在替换为已捕获传感器帧后策略仍可运行；候选对6种真类同位置保持同身份：PASS，范围仅灾害策略 |
| 多目标C投影 | 实际C框：164m/30° UUV与280m/0° debris；旧投影选debris，新关联选UUV，预测点与真实框中心误差≤3px：PASS |
| 近场/保护/重试/失败回滚和同库重启 | 与原有安全及历史测试一起执行，检查次数、原因及RNG/事务恢复；最终统计见机器记录 |
| 真实权重场景B | 完整600仿真秒×3次；无DEBUG真值航迹；均为6 clear/3 blocked/3 unsurveyed，4个危险位置无clear，语义哈希相同 |

新完整B场景：anchorage_north、channel_main_n、channel_turning为blocked；berth_fuel保持unsurveyed；复航只含channel_entrance/channel_main_s，泊位只含berth_container_1。当前状态代入指标公式得9h，这只是仿真假设下的计算值，**不能作为真实可靠复航许可**。

回归中发现匿名瞄准与0距离未定义方位会让旧完整桩正例从4次检测变成6次；保持原断言，修复0距离的方位表达后全量重新执行。没有以放宽测试掩盖这一退化，详见原始/最终JUnit哈希。

新完整场景使用合成观测瞄准和全画面物理朝向，输入图像/种子分配可与旧坏帧不同；新的正向识别不被当作旧误分类已消失的证据。P0保护由原坏帧重放和受控失败验证，旧坏帧与原始置信度继续保留。

## 真值依赖审计：不能宣布全系统“真值无关”通过

| 位置 | 当前用途与边界 |
| --- | --- |
| sim/sonar.py:survey_contacts | **仍是合成理想观测**：从世界几何生成匿名米级候选，所有反射体都有几何提议；不是从真实回波/PNG提取，未建模原始接收端漏检。虽不读真类/真值ID，但几何仍来自仿真源，因此真实感知端到端验收PENDING |
| sim/sonar.py:sonar_scene、sim/acoustics.py | 真类只用于合成形态、声源级、cue等传感器生成，属于允许的场景生成依赖；不把这些标签作为真实YOLO输出或复航证据 |
| perception/classifier.py fallback | 明确stub模式会使用生成标注的类别，这是已有演示兜底，不是独立感知；真实权重场景断言所有Detection.model=yolo26n，不接受悄悄降级 |
| perception/tracker.py:87、engine.py:274 | 模拟AIS仍从世界vessel列表直接做合作匹配；本轮未重构B4。必须记作尚未拆分的真值耦合，不能声称全跟踪/分类链路真值无关 |
| engine.py:_truth_tracks | 仅显式DEBUG_TRUTH_TRACKS=1兜底，本轮禁用；不得把该模式结果算正常定位验收 |
| tools/model_acceptance.py | 在离线评分中按真值位置检查危险区是否clear，属允许的评分用途，不反馈给运行时决策 |
| decision/disaster.py、pinger关联、BFS | 不再按真类筛选候选或按真值ID关联；使用匿名观测和预测几何、检测输出及分区状态。仍依赖上述合成传感器假设 |

另外，覆盖圆仍是演示400m面积积分，真实成像量程300m；0.9覆盖阈值本身不是实际水下安全证明。完全没有进入观测流的障碍不能由本次补丁保证检出。未决保护已修，不代表“当前绿色区域已通过实地安全复航验收”。

## A / C / Lenovo 对接

- A只按后端state显示blocked/unsurveyed，不从coverage或识别非debris推断绿色。原因可在既有log中展示；目前ZoneStatus没有结构化reason字段，不能私加接口，也不要从日志伪造审批/状态。若需要分区详情专用reason字段，应走契约评审。
- C继续提供与render_ping完全一致的公共像素投影helper；本轮用B内部公式与实际C框对照，不改C模块/冻结签名。新helper尚未合入时不假称已对接。LoRA不阻塞本修复。
- Lenovo先复验原250m/0m种子及受控漏检/错分类/低置信；再跑真实B，接受blocked或unsurveyed，断言危险位置不能clear。不把固定9h当验收断言，不需先训练。
- 本轮不动C4在途文件、A源码、权重、shared或场景数据，所有暂存文件在提交前列明。

## 复现与部署

```powershell
.venv/Scripts/python.exe -m pytest backend/tests/test_survey_audit.py backend/tests/test_model_safety.py backend/tests/test_disaster.py backend/tests/test_real_model.py -q
.venv/Scripts/python.exe -m pytest backend/tests tests -q --basetemp=artifacts/p0-pytest
.venv/Scripts/python.exe -m backend.tools.model_acceptance --scenario b --repeat 3 --out artifacts/p0-real-b.json
```

需要与指定C权重匹配的CPU运行依赖。缺少真实权重/runtime的测试明确SKIP，不算真实YOLO通过。新增观测网格参数改变内部配置指纹；保留当前演示库与进程，新版本使用独立HARBORGUARD_DB，例如`backend/runtime/survey-p0.sqlite3`，不要强行加载旧检查点。未修改数据库schema或共享契约。

当前本机5173仍是原演示工作区`1269f3e`，不是这次P0修复的部署。独立HTTP/WS烟测使用8004/8006和新库，完成后仅关闭自己的进程。Lenovo应拉取本轮确切提交、使用新库复验，不能把旧浏览器页面或旧检查点当成新版本结果。
