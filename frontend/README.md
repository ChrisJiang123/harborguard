# HarborGuard 前端

港口水下安防数字孪生看板。按任务书 A0–A6 逐阶段实现。

界面语言为英文，包括 2D/3D 控件、提示、审批、演示建议、日志与错误信息。已有录制文件的已知中文标签与标准后端消息由前端显示层翻译，原始记录和事件身份不变；未收录的外部自由文本保留数据源原文。

## 当前进度

已实现 A0–A1 的界面骨架、共享契约类型、Zustand 状态管理、本地假数据和 WebSocket 自动重连，A2 的 2D 地图，A3 的操作面板与场景 A 交互流程，以及 A4 的可运行水上/水下一体 3D 数字孪生视图。

已接入 A5 的灾害复航演示、JSONL 回放播放器、声呐图弹窗和合成数据指标卡，并加入本地 OSM 岸线简图作为离线降级。已在本机浏览器验证 2D/3D、回放切换和刷新恢复；真实断网环境、目标投影设备及 B/C 全服务现场验收仍待完成。当前也不是完整 PMTiles 离线底图方案。

The 3D renderer is **Three.js / React Three Fiber, not Cesium**. The default seabed now uses NOAA H12617 **multibeam** BAG survey products (1 m / 2 m original grids, acquired 2013), with ~8 m harbor rendering and a ~2 m local inspection patch. See [multibeam provenance and regeneration](public/data/MULTIBEAM-SOURCE.md). It is not an ordinary land DEM or a synthetic/merged regional DEM masquerading as multibeam. **A6 remains incomplete**: historical survey/coverage/uncertainty acceptance, MLLW–NAVD88 alignment, live tide, current full-service rehearsal, target projector/network and field sign-off remain separate. Recording was cancelled by the user and is not performed.

## 开发运行

先在仓库根目录启动 B 后端（Python 3.11+）：

```powershell
py -3.11 -m venv .venv
./dev.ps1 setup
./dev.ps1 backend
```

若环境已准备好，直接执行 `./dev.ps1 backend`。健康检查为 http://localhost:8000/api/health，接口文档为 http://localhost:8000/docs。

另开终端，在 frontend 目录运行：

```powershell
npm.cmd install
npm.cmd run dev
```

- 本地演示：http://localhost:5173/?mock=1
- 实时连接：http://localhost:5173/
- 安防模拟回放：http://localhost:5173/?replay=demo_a.jsonl
- 灾害模拟回放：http://localhost:5173/?replay=demo_b.jsonl
- 三分钟合成回放：http://localhost:5173/?replay=demo_full.jsonl
- B 的真实录制文件放在 public/replay_a.jsonl 后，用 ?replay=replay_a.jsonl 打开。

生产预览使用 `npm.cmd run build` 后执行 `npm.cmd run preview -- --host 127.0.0.1 --port 5173`；后端当前 CORS 允许该端口，若改用其他端口需同步调整后端允许来源。

在 VS Code 已运行开发服务时，无需重复启动。修改文件后浏览器自动更新。

## 第一阶段如何查看

打开本地演示后，默认按正常速度运行：

- 10 秒：一级警报。
- 35 秒：二级警报与模拟识别事件。
- 60 秒：三级警报与模拟方案。
- 66 秒：模板建议。
- 90 秒：模拟目标到达示例资产。

顶栏可选择 4×、10× 加速，或暂停、重启场景。点击左侧目标可以选中，再次点击取消。
MOCK 标签说明数据为本地模拟，不代表真实港口信息。

无参数页面连接 ws://localhost:8000/ws。后端未启动时显示断线并按 1、2、5、5 秒重试。
后端发来符合契约的数据后显示 LIVE。此状态与 network 字段代表的外网状态不同。

## 第二阶段如何查看

中央地图使用洛杉矶港 OpenStreetMap 底图，默认中心 33.735、-118.255，缩放 14。

- 有 10 个示例分区、资产的三级警戒圈、10 个浮标覆盖圈和两个模拟目标。
- 实线表示历史航迹，虚线表示预测航迹；颜色按后端给出的 level 显示。
- 目标附近的椭圆表示 err 的一倍标准差范围，按米制坐标绘制。
- 点击目标出现白色光圈，并与左侧列表共用选中状态；点击地图空白取消选中。
- 浮标离线时变灰并带叉号，pinging 为 true 时扩散动画持续约 1.5 秒。
- 第 66 秒以后，悬停右侧方案行可以预览对应分区的红色虚线边界；键盘 Tab 聚焦也能预览。
- “港口全景”恢复初始视野；右上角 ↻ 重读业务图层，本地模式下会重启演示。

实时模式启动时只读取一次 /api/zones、/api/assets、/api/buoys，失败时尝试 public/data/，最后使用明确标注的示例图层。
本地演示只读 public/data/ 或示例图层，不访问后端。几何图层和 mock 共用相同文件与分区 ID。

示例分区不是 OSM 或官方安防边界；OSM 提供地理底图，业务数据由 B 提供。
OSM 署名保持可见，仅按当前视口加载在线瓦片，不进行批量预取。离线简图使用一次小范围 Overpass 矢量数据提取，不缓存或打包公共栅格瓦片。
参考：[OSM 瓦片使用政策](https://operations.osmfoundation.org/policies/tiles/)。

## 第三阶段如何查看

打开本地演示，点击顶栏“场景 A”，选择 10×；约 7 秒后可以看到方案与模板建议。

- 方案表显示开放泊位比例、受影响船舶、延误船时和残余风险。所有指标直接来自数据源。
- Agent 推荐方案带星标，默认选中；也可以用单选框改选“全港关闭”。
- 悬停方案行时，地图用红色虚线预览该方案的限制分区。聚焦证据分区会以青色高亮定位。
- 点击“批准”后，本地 mock 发出 decision 和 zone_changed 事件，页面显示已批准及仿真时间，地图对应分区变红。
- 重新启动场景 A 后可演示“驳回”；驳回不关闭分区。
- 一次仅发送一个操作请求。实时模式中，HTTP 请求被接受不等于已批准；必须收到 decision 事件才显示确认。
- 操作失败显示错误提示，按钮解除加载状态，不将失败请求标成成功。
- 顶栏的场景、重置、模式、断外网、暂停/继续和倍速控制已接入 REST 封装。本地模式使用 mock，不请求后端。
- 断外网改变的是仿真 network 字段，不会关闭电脑 Wi-Fi；连接徽标 LIVE/MOCK 与外网状态分开显示。
- 场景 B 提供预设模拟勘测节点与复航建议，见第五阶段。
- 右下方日志显示最近 50 条，带来源与等级颜色。底部风险条仅按权重绘制贡献，不重算风险总分或警报等级。
- 选中目标时显示其警报对应建议；选中无警报的鱼群不会误显示其他目标建议。
- 点击识别证据或地图选中目标后的“声呐图”，可查看预标框图像、类别、置信度、浮标、模型和时间。stub 明确标注为合成示意图。
- 重启场景会清除上一轮的方案选择、建议和确认记录；回放模式禁止所有 POST 操作。

完整 REST 封装在 src/data/api.ts。A3 自动检查验证的是模拟服务和事件流程，不等同于和 B/C 的真实联调。

## 第四阶段：水上/水下 3D

在实时、模拟或回放页面点击中央“3D 水下”，使用场景左上角的“目标”下拉框或直接点击模型选中目标；选中后相机会飞向该目标。水上白模、水面、海底、船舶、浮标、航线和风险区都使用同一业务坐标空间。

- 2D 与 3D 共用 selectedTrackId，切换视图不会清空选择。场景重启会清空目标选择，但保留当前 2D/3D 视图。
- 场景包含水面、NOAA 区域海底 DEM、USGS 3DEP 实测岸上高程网格、USGS/USDA NAIP 洛杉矶港正射影像贴地层、OSM 岸线/防波堤/码头线、洛杉矶县建筑 footprint 白模、浮标与声呐锥、移动船舶/水下目标、航迹、警戒柱及业务路线。实景影像按同一 EPSG:4326 范围贴到高程网格上，只在 NOAA 岸陆掩膜范围绘制；建筑底面按所在位置采样岸上高程。
- 可用“整体总览”“水上视角”“水下视角”“跟随选中”和“视角复位”。新选中目标时自动进入跟随；下拉框列出包括正常等级船舶在内的全部航迹。
- 相机飞行动画设为 1.5 秒；跟随目的地随当前目标位置更新。手动拖动会中止本次飞行，跟随模式仍保留对目标的平移跟踪。
- 拖动旋转，滚轮缩放，右键平移。“视角复位”恢复全局视野。图层可分别开关岸上白模/地形、海底、船舶、浮标、航线和风险区域。
- 可隐藏水面或在 5%–60% 之间调节水面透明度。水面固定为 0 m 演示参考平面，**不是实时潮位，也不是海图基准面**。
- 图层面板可独立开关海底网格和从当前网格插值出的 2 m 等深线（10 m 主等深线加亮）；NoData 单元不跨越绘制。海底使用 2× 双线性显示细分、平滑法线和深度配色，移除线框干扰；原始采样点保持不变，不添加虚构岩石、沟槽或测深信息。超过 150,000 个源采样点的外部 DEM 不再额外细分，避免网格规模失控。2 m 等深线间隔和细分网格间距不代表 2 m 测深精度。
- `Layers`、`Display Settings`、`Data sources`、目标信息和底部比例说明均可点击标题收起/展开（支持键盘）；默认收起，选中目标后自动展开该目标的信息。收起只隐藏内容，不重置图层、透明度、垂直比例或回放。数据类型、非真实比例和参考水位在收起后的标题中保留。窄画布用 `Scene Settings` 显示图层/显示设置入口；相机按画布宽高比调整总览距离，避免两侧港区被裁掉。
- 深度向下为正。为改善公里级总览的立体感，默认使用 **3× 垂直视觉增强**；可选 1×/2×/3×/4×/8×，并可用 `Restore true scale (1×)` 一键恢复真实比例。界面持续标出倍数和“非真实比例”。岸上 DEM、白模底部及高度、海床与等深线统一缩放，动态目标深度沿用相同显示倍数；水面始终为 0 m。原始高程、业务深度读数、经纬度和 2D 坐标不变。垂直比例只改变对象变换，不重建建筑/DEM/等深线网格；低角度总览和侧向光照帮助辨认起伏，不引入实时阴影开销。增强显示不代表测深精度提升或垂直基准已转换。
- 2026-10-18 回归：Build、Lint、A1–A6、恢复竞态与英文自动检查通过；A4 覆盖 1×/2×/3×/4×/8×/恢复 1×、源顶点不变、NoData 不跨越、细分网格范围与几何复用。浏览器访问问题已恢复，已实际检查水上/水下/总览、比例复位、收起/展开后设置保留、选中目标、播放/暂停、跨 A/B 跳转与 2D/3D 切换；不将文件回放当作真实后端联调。
- 目标按类别显示几何体并放大 5 倍，船舶具有船体、艏向、驾驶舱和桅杆，鱼群使用 30 个实例。模型位置、艏向、状态和标签全部取自当前状态快照；目标标签显示后端深度，不将放大后的场景高度当成真实深度。
- 历史航迹为实线，预测航迹为虚线，目标到水面有投影虚线及圆环。目标与航迹颜色沿用后端等级。
- 目标位置逐帧从 store 读取并更新 ref；航迹复用已有 GPU 属性缓冲区，不每 200 ms 重建整个场景。
- “简化风险体”只减少警戒柱复杂度；海底和各业务图层由独立开关控制。
- 底部信息栏明确显示“后端实时数据 / 本地模拟数据 / 文件回放数据”、场景、仿真时间、暂停状态，以及选中目标的状态、艏向、航速、深度和风险。回放播放器暂停、继续或拖动时间轴时，3D 使用同一 reducer 快照同步变化。
- 展开底部图例可查看约 1 秒窗口的实际帧率；“显示帧率面板”额外显示 FPS，也可使用 `?mock=1&stats=1`。Canvas 像素比为 1.5–2，负载升高时自适应至当前比例的 85%，不使用 pixelated 栅格放大；海底网格、航迹缓冲和实例保持复用。总览范围同时包含业务图层与 DEM 四角。高清模式的 GPU 负载高于旧版，最终持续性能仍须以目标演示电脑验收。
- 3D 资源在首次切换时按需加载；标签不下载外部字体，场景不下载额外模型或纹理。
- 3D 创建失败或渲染连接丢失时提供重试与返回 2D，其他面板继续保留。

A4 自动检查覆盖业务坐标 1×、默认 3× 显示与 1×/2×/3×/4×/8× 变换/复位、DEM 元数据/深度范围/NoData、细分插值与源采样保留、白模范围、脉冲衰减、船舶随时间变化和暂停恢复、各相机预设与窄画布取景、动画插值、视图选择保留，以及真实 Three.js 航迹属性缓冲区的 1500 次复用检查；未代替演示电脑的持续 GPU 帧率验收。

本轮本机浏览器实测：Windows / in-app Chromium，`?mock=1&stats=1`，视口 609×703，场景 A、4 个目标、10 个浮标、全部 3D 图层。已确认 3D 视图加载岸上数据和正射影像、切换水下/总览、隐藏水面后保留海底图层，以及返回 2D 后地图与回放仍运行。Vite 收到的浏览器控制台转发没有 error；有既存 `THREE.Clock` 弃用警告。帧率面板读数在不同采样窗口约 47–140 FPS（视口较小且视角/布局变化，不能作为 1920×1080 验收结果）；尚无 1920×1080 现场截图。本轮仍需在目标投屏分辨率及设备上复验。

### DEM 数据、基准与替换

The default `public/data/seabed-dem.json` is a crop of [NOAA H12617](https://www.ngdc.noaa.gov/nos/H12001-H14000/H12617.html), acquired with a **Reson 7125 multibeam echosounder in 2013**. Original finalized BAG products have 1 m and 2 m spacing. The harbor display grid is 1401×911 at ~8 m, with 599,472 supported samples, depths 1.15–28.27 m below MLLW. `seabed-detail-mb.json` adds an aligned 801×705 local ~2 m patch around the underwater preset. Only survey-supported cells render; the rest remain NoData. Do not equate display spacing, original spacing and measurement accuracy. Full provenance, uncertainty interpretation, source hashes, crop bounds, sign/CRS conversion and limitations are documented in [MULTIBEAM-SOURCE.md](public/data/MULTIBEAM-SOURCE.md).

Open **3D View → Underwater** to inspect the ~2 m patch. **Display Settings → Show water** hides the reference surface; opacity, orbit/zoom/pan, vertical scale and **Reset View** remain available. **Layers → 2 m multibeam inspection patch** toggles the local refinement without resetting playback; outside that patch the harbor is still ~8 m, not 2 m everywhere. At narrow widths first open **Scene Settings**. Data-source details identify historical acquisition, MLLW, unsupported coverage and unresolved shore datum alignment. See [current browser validation](MULTIBEAM-VALIDATION.md).

Run `python -m pip install --target work/gis-python -r scripts/requirements-bathymetry.txt`, then `npm.cmd run refresh:multibeam` to regenerate from official BAGs. Python is not needed for normal frontend startup. Native BAGs/dependencies stay in ignored `work/`. `refresh:noaa-bathy` is the **legacy regional CRM** overwrite command; `make:bathymetry` overwrites with **synthetic terrain**. Neither regenerates MBES. `VITE_BATHYMETRY_URL` accepts version-1 survey JSON; a custom URL disables the bundled detail patch. Different source/datum metadata also disables incompatible patches. Survey source classification identifies provenance, **not field acceptance**. Water is fixed 0 m MLLW, not MSL or live tide. Native UTM11N/NAD83 metres are sampled into NAD83 geographic rows north-to-south, depth positive down. No realization-specific NAD83/WGS84 or spatial vertical datum transformation is applied.

### 实测岸上高程与建筑落地

`public/data/shore-dem-usgs-3dep.json` 是 [USGS 3DEP Elevation ImageServer](https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer) 的洛杉矶港区裁剪；`public/data/shore-ortho-usgs-naip.png` 是 [USGS National Map NAIP 正射影像](https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer)，同范围贴图。运行 `npm.cmd run refresh:shore-dem` 重新生成两份静态快照；仅更新影像用 `npm.cmd run refresh:shore-imagery`（校验 PNG/尺寸后再覆盖；网络失败保留现有文件，不改变高程网格）。高程网格为 512×278 EPSG:4326，间距约 20–26 m；虽 3DEP 源服务在部分区域有 1 m 产品，本项目这份显示网格不是 1 m 数据。影像已从 1536×834 升为 3072×1668，显示像素数量提高 4 倍，约 3.6–4.3 m/显示像素，不代表源数据定位精度或采集分辨率。服务版权时间为 2025-01-09，但局部影像实际采集日期依区域而异。高程垂直基准 NAVD88、单位米、向上为正；NAIP 为正射影像拼接，不是实时视频。

**Vertical alignment remains unaccepted**: shore DEM is NAVD88; seabed/water is MLLW. No NOAA VDatum spatial transformation has been applied. Their zero-offset display is not an engineering elevation tie, current tide or construction level. USGS regional 3DEP is not a site ground survey. Replacement must retain documented CRS, vertical datum, units/sign, NoData and acquisition time; see `refresh-usgs-shore-dem.mjs` and the existing shore JSON format.

### 真实港区建筑白模

`public/data/lacounty-port-buildings.geojson` 保存洛杉矶县 GISNET Public 的 Countywide Building Outline (2023) 图层，几何坐标由服务投影到 EPSG:4326，与业务场景共用原点 `(33.73, -118.26)` 和 ENU 米制转换。原服务空间参考 EPSG:2229 为 US survey foot；`HEIGHT` 按 `1200/3937` 转米。查询范围与 DEM 覆盖范围一致，只保留 footprint 面积大于 10,000 平方英尺的建筑以控制 draw calls，本次静态数据为 487 栋；没有高度的记录不进入模型。3D 将建筑挤出网格合批绘制，场景“垂直显示”会同步缩放建筑高度。

The height field supplies building extrusion height; roof elevation has no verified datum, so building bases use sampled USGS shore elevations (NAVD88). Seabed/water is MLLW; absolute elevation alignment remains unverified. These are measured footprints/heights, not detailed LiDAR roof/façade models. See `public/data/LA-COUNTY-BUILDINGS.md` for provenance and attribution; `npm.cmd run refresh:buildings` updates footprints. Review county redistribution terms before external distribution.

## 第五阶段如何查看

在本地演示中点击“场景 B”，选择 10×，约 5 秒后查看右侧复航面板。

- 仿真第 12 秒部分分区变绿；24 秒出现封闭区和初步复航方案；45 秒更新为 6 个可复航、3 个待勘测、1 个封闭分区，并收到模板复航建议。此分布仅适用于内置 10 区示例，不是实际勘测结果。
- 2D/3D 灾害图例与分区颜色共用 clear / unsurveyed / blocked，显示后端 coverage。
- 复航面板直接展示 reopen_plan 的四组分区 ID 和 est_hours_saved，点击 ID 定位 2D 分区。前端不计算复航策略或节省时间；演示 4.5/9 小时为模拟服务预设响应。
- 展开“浮标故障注入”可选择浮标并模拟离线/恢复。覆盖区域增加灰色斜线，表示潜在盲区；未扣除其他浮标的重叠覆盖，不冒充后端盲区判定。
- “断外网”仅注入模拟 network 状态，不关闭电脑 Wi-Fi。红色横幅按实际 recommendation.model 区分模板、本地模型和待确认状态，不把模板冒充已训练 LoRA。
- 左下“合成数据指标”读取 /api/metrics。yolo / lora 为 null 显示“训练中”；网络错误显示不可用。非空对象按原始字段名和数值展示，不臆造字段、单位或指标。B/C 仍需提供实际评估结果并对齐内部字段。
- 真实模式声呐图读取 /api/sonar/{det_id}.png。模拟 SVG 是预标框示意图，不是真实声呐或 YOLO 输出。前端不运行识别模型。

### 文件回放

顶栏“演示回放”打开 demo_b.jsonl；demo_a.jsonl 还包含识别、模板建议和模拟批准事件。两份文件均由本地 mock 生成，不是 B 后端的录屏或真实录制。

- 文件逐行格式为 {"wall_ms":1234,"msg":{...}}，msg 沿用共享 StateMsg / EventMsg，不增加传输字段。
- 按 wall_ms 播放，而非仿真 t；同一 wall_ms 保留文件原始顺序。支持播放/暂停、1×/2×和拖动定位。
- 定位会按相同 reducer 重建截至该位置的状态与事件缓存，包括日志、识别、方案、建议、人工决策和复航方案；跨场景重置不保留上一场缓存。
- 回放模式全部 POST 被双重锁定（界面与请求层），不启动 WebSocket，不读后台指标，也不请求在线 OSM 瓦片。
- 回放配套图片需放入 public/ 并使用以 / 开头的本地图片路径；后端绝对 image_url 在回放中改读 /sonar/{det_id}.png，缺图会明确报错，不悄悄联网。
- 缺文件、倒序 wall_ms、无状态快照、错误 JSON 会报错，不偷偷切到 mock。文件上限 30 MB、20 万条消息。
- 重建演示文件：npm.cmd run make:replays。只用于生成明确标注的模拟回放，不替代 B 的录制文件。

### 离线简图与范围

public/data/harbor-osm.geojson 包含从 OSM 提取的洛杉矶港岸线、码头、防波堤及主要道路线，共 407 条要素。数据与许可证说明见 public/data/OSM-SOURCE.md。

点击“切换离线简图”，或回放/外网离线/瓦片加载失败时，改用本地矢量简图。它不含完整地名、地物填色或多级瓦片；视野超出提取范围时没有额外底图。业务分区与 OSM 岸线来源分开标记，内置矩形业务区仍为示例数据。

断开 Wi-Fi 后，本地开发/预览服务必须继续运行，再刷新本地演示或回放页面。所有演示数据、图像、岸线与 3D 依赖来自本机。尚未完成浏览器里的真实断网刷新验收；没有安装可在本地服务器关闭后运行的 PWA。

任务书列出的完整离线底图方式是 PMTiles 或缓存瓦片。公共 OSM 标准瓦片禁止离线批量预取，因此未实现任务书建议的批量平移缓存；目前采用任务书允许的底图失败降级并增加本地真实 OSM 线图。若要完整离线底图，仍需合法离线地图包与 PMTiles 接入，不能把当前简图视为等价验收。

## 第六阶段如何查看

先执行生产构建并打开预览，在中央视图右上角点击“演示准备”。

- 面板显示当前网页视口，并提供全屏切换。正式投屏目标是 1920 × 1080；代码只能检查视口，仍需在实际投影仪上从 3 米外确认正文、建议摘要和关键数字可读。
- “打开三分钟模拟回放”会进入 demo_full.jsonl：前 80 秒为场景 A，70 秒出现模拟批准；80 秒切换场景 B，约 125 秒出现最终复航方案，随后出现浮标离线和模拟外网断开。
- 录屏必须点击“选择页面并开始录屏”并在浏览器对话框中亲自选择 HarborGuard 页签。程序请求 1920 × 1080、30 fps，不请求声音，最多录制 180 秒、120 MB。
- 录制完成后先在面板内预览，再点击下载。视频只保存在本机内存和你选择的下载目录；关闭或刷新页面前必须下载，程序不会上传或自动写入仓库。
- 浏览器不支持页签录制、需要系统声音或最终格式不兼容时，改用 OBS 或系统录屏。浏览器通常输出 WebM；必须在演示电脑和共享位置各试播一次。
- 顶栏三级警报标签、目标行和地图标记会闪烁；无警报显示“全港正常”；后端断开时显示自动重连提示且不白屏。提示音按任务书的可砍范围未实现。

三分钟文件是本地 mock 生成的合成回放，不是 B 的真实录制，也不证明真实后端、真实网络或本地 LoRA 已通过验收。重新生成 demo_a、demo_b 和 demo_full：`npm.cmd run make:replays`。

## 配置和团队文件

### 实时刷新恢复与碎片识别

实时页面收到 WebSocket 的首个状态快照后，会显示恢复进度，读取现有 `GET /api/events?since_seq=0` 与 `GET /api/log`，重建事件时间轴、方案、识别、建议和人工决策状态，并与恢复期间到达的 WebSocket 消息合并。recommendation、detection 和 alert 优先使用已有稳定 ID 去重，其他事件沿用 `seq/event/t` 身份；当前警报标记 `options_ready` 或当前航迹带有 `detection_id` 时，还会通过已有详情接口补齐对应方案与识别记录。若重连后的状态 `seq` 小于断线前快照，前端判定后端已重启，清除旧会话派生状态并提示重启前历史无法确认，防止旧事件覆盖新会话。刷新不会重新 POST 操作或生成事件。

恢复范围受后端契约 v1 的缓存边界约束：事件接口最多返回后端当前缓存中的 500 条，且没有独立的人工决策历史列表或 Agent 建议列表接口；响应达到 500 条时界面显示“历史不完整”，事件或详情读取失败时显示相应降级提示。2026-10-18 源码复核确认 B 已为批准和驳回都生成结构化 `decision`，并已有持久化；旧版“驳回只写日志”的描述已过时。但持久化不等于冻结接口可分页查询旧审批，本轮后端 8000 端口未在线，未复验运行态。前端对旧服务/丢失事件仍保留兜底：HTTP 成功但未收到结构化事件时显示“状态无法确认”并防止重复提交，收到结构化事件后才显示确认结果。刷新后缺乏权威事件的记录不会误标待审批，也不会解析自由文本日志推断决策。历史复现与修正见 `B-HANDOFF.md`；本轮验收口径见 `ACCEPTANCE-A.md`。

灾害模式的“勘测与复航”面板包含“碎片识别记录”入口，只列出数据源实际发来的 `detection.cls === "debris"` 记录。点击后显示该记录的类别、置信度、浮标、模型、时间和后端图像。没有记录时明确显示尚无后端记录；`model: "stub"` 明确标注为演示识别，不冒充 YOLO 真实推理。

复制 `.env.example` 为只保存在本机的 `.env.local` 后，可配置：

```dotenv
VITE_API_BASE=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
VITE_BATHYMETRY_URL=/data/seabed-dem.json
```

没有配置时，默认使用任务书的 localhost:8000。

联调顺序：启动后端 → 打开 `/api/health` → 启动前端无参数页面 → 确认顶栏显示 LIVE → 启动场景 A/B → 切换 3D → 选中船舶并检查位置/艏向/时间变化 → 暂停/继续 → 检查浏览器控制台。后端不可用时用 `?mock=1`；需完全可复现时用 `?replay=demo_full.jsonl`。界面始终明确标出 LIVE、MOCK 或 REPLAY，不把演示数据冒充真实数据。

### 已接入接口

- WebSocket：`GET /ws`（完整 `state` 快照与 `event` 事件）。
- 读取：`GET /api/health`、`/state`、`/events`、`/zones`、`/assets`、`/buoys`、`/tracks/{id}`、`/alerts/{id}`、`/detections/{id}`、`/options/{alert_id}`、`/metrics`、`/log`、`/sonar/{det_id}.png`。
- 控制：`POST /api/scenario/{a|b}/start`、`/control`、`/mode`、`/inject`、`/decision`、`/recommendations`、`/log`、`/agent/ask`。
- REST 失败会显示错误并保持界面可用；几何图层依次降级为 `public/data/` 和明确标注的示例数据。回放模式禁止所有 POST。

B 提供的静态文件放入 public/data/。没有静态文件时，mock 使用标注为示例的数据。
请只根据 B 维护的共享契约修改 src/types/contract.ts，不要自行增加传输字段。

## 检查

```powershell
npm.cmd run build
npm.cmd run lint
npm.cmd run check:a1
npm.cmd run check:a2
npm.cmd run check:a3
npm.cmd run check:a4
npm.cmd run check:a5
npm.cmd run check:a6
npm.cmd run check:recovery
npm.cmd run check:english
npm.cmd run check:vessels
```

check:a1 验证事件时间点、模拟批准、选择状态、暂停与倍速、重置、缓存上限和 WebSocket 重连。
check:a2 验证坐标换算、36 点误差椭圆、GeoJSON 孔洞与多面、示例图层、业务文件/API 读取缓存、队友分区 ID 对齐、离线事件与 5 分钟模拟。模拟测试不等同于真实浏览器内存/流畅度验收。
check:a3 验证批准/驳回、方案默认与手动选择、警报上下文、风险贡献、控制按钮请求、回放锁定、后端事件确认、HTTP 错误、重复请求防护和场景重置。
check:a4 验证 2D/3D 业务相对坐标、默认 3× 显示与各档垂直转换/复位、分区/白模范围、相机预设及窄画布取景、1.5 秒插值和脉冲、DEM 元数据/NoData/实际起伏/细分源点保留、等深线插值、选中状态保留与 Three.js 航迹属性复用。
check:a5 验证灾害预设响应、复航原值、OSM 本地线图及来源、声呐本地路径、指标原值/空值、JSONL 校验、任意定位缓存恢复、跨场景清理、wall_ms 播放与暂停/2×/结束重启、回放 POST 锁和加载/清理错误流程。全部测试不访问浏览器或真实后端。
check:a6 验证三分钟合成回放的时长、场景切换、批准、复航、浮标故障和断网事件，以及页签录屏的 180 秒限制、格式选择、停止、取消和资源清理。它不自动授予浏览器录屏权限，也不能代替实际视频试播和投影检查。
check:recovery 验证 REST 历史延迟时合并 WebSocket 日志、刷新恢复审批状态、稳定事件身份去重、连接开始时固定序列基准、后端重启识别、重置/切换场景/重连后的过期请求隔离，以及 500 条历史上限的部分恢复提示。
check:english 检查界面字符串、三份演示回放及现有录制文件的已知消息均显示英文，并保留源数据 ID。
check:vessels 验证 T3/T4 全参考航线的 NOAA 水域掩膜、速度/速度分量/航向/位移一致性、转弯限速、加减速、终点停车、航向过北不绕圈、历史与预测、暂停/重置和三份合成回放的任意跳转。船速最高 3.8 m/s，参考航线两侧各偏移 40 m；这是预设合成交通，不是 AIS、自动避碰或港口官方通航规则。历史点间隔为 2 秒（最多 60 点），预测每 10 秒采样至 100 秒，均使用同一确定性运动模型。T1 的戏剧化警报场景节奏未改动，不能据船舶检查宣称 UUV 动力学已拟真。
work/ 是检查时生成的临时输出，不纳入版本控制。

## 生产预览

```powershell
npm.cmd run build
npm.cmd run preview
```

预览端口以终端输出为准。交付前仍需用演示电脑完成现场投影检查、真实 Wi-Fi 断开刷新、持续 3D 帧率与当前 B/C 服务联调。1920×1080 浏览器短时检查不等于现场投影验收；录屏已按用户要求取消，本轮没有录制或视频试播。A6 保持有条件演示、未全部验收。详见 `ACCEPTANCE-A.md`。
