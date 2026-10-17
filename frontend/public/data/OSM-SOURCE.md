# 洛杉矶港本地简图来源

- 来源：© OpenStreetMap contributors，Overpass API。
- 许可证：[Open Database License 1.0 / OSM 版权与署名](https://www.openstreetmap.org/copyright)。这是 OSM 数据的筛选与坐标格式转换，分发时保留来源与 ODbL 说明。
- 提取时间：2026-10-17T06:17:27.416Z。
- OSM 数据基准时间：2026-10-17T06:16:02Z。
- 查询范围：南 33.705、西 -118.29、北 33.765、东 -118.215。输出几何边缘可能保留相邻点，以维持线段连续性。
- 共 407 条线要素：岸线 62、道路 76、码头 244、防波堤 25。
- 文件 harbor-osm.geojson 保留原始 OSM way ID、提取时间、查询式与许可证声明，可追溯原始要素。

仅做一次有界的矢量数据查询，没有下载任何 OSM 栅格瓦片。刷新脚本为项目 scripts/fetch-osm.mjs（npm.cmd run refresh:osm），不要高频运行。脚本只在查询成功且有岸线时更新文件；重新提取后请同步本说明的时间和数量。

参考：[Overpass 有界几何输出](https://dev.overpass-api.de/overpass-doc/en/full_data/bbox.html)，[OSM 标准瓦片使用政策](https://operations.osmfoundation.org/policies/tiles/)。

本文件是小范围线图，不是完整离线地图包，不用于导航。业务分区、安防资产、浮标位置及模拟复航策略并非本次 OSM 提取结果。
