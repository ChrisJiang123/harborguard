# 团队静态数据

将 B 提供的 assets.json、buoys.json、zones.geojson 和 vessels.json 复制到这里。
没有团队文件时，本地 mock 使用明确标注的示例坐标，不冒充真实港口数据。

harbor-osm.geojson 是单独的 OSM 地理岸线简图（并非业务分区），来源和 ODbL 许可见 OSM-SOURCE.md。
sonar-stub.svg 是模拟声呐示意图，不是真实声呐或训练模型输出。
B 提供的 JSONL 放入 public/；回放配套图片也需本地打包，例如 public/sonar/det-1.png。

`seabed-fill-regional.json` is a separate NOAA CRM regional model/interpolation layer, not additional H12617 measurements. Its metadata explicitly retain native datum/resolution and the unresolved vertical tie. See [current shoreline validation](../../../docs/3d-shoreline-realism/README.md).
