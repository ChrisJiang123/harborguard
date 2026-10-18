# 洛杉矶港建筑轮廓数据来源

- 来源：Los Angeles County GISNET Public，MapServer layer 434，**Building Outline (2023)**。
- 服务地址：<https://rpgis.isd.lacounty.gov/arcgis/rest/services/GISNET_Public/MapServer/434>。
- 服务提供者标注的版权方：LARIAC、County of Los Angeles、Pictometry、EagleView。
- 许可证/使用条件：County of Los Angeles eGIS 自定义条款，见 <https://egis-lacounty.hub.arcgis.com/pages/terms-of-use>。本项目保留来源、数据时间和版权方；项目公开分发前需复核自定义条款是否允许打包再分发。
- 县级服务描述称该层包含建筑轮廓、高度、面积及屋顶 elevation；服务记录注明从影像提取，详情同时出现 2017 LARIAC5 acquisition 与 Building Outline (2023) 图层名称。不得将其描述为 2023 年新航测，源元数据存在日期口径差异。
- 服务空间参考：EPSG:2229（NAD83 / California zone 5，US survey foot）；输出几何经服务转换为 EPSG:4326，经纬度单位为度。`HEIGHT` 保留原始英尺值供追溯，并按 `1 US survey foot = 1200/3937 m` 转换为场景高度。
- `ELEV` 是服务中的屋顶 elevation 字段，但没有找到可确认的垂直基准说明，前端不使用它定位建筑底面。白模从场景参考平面起建；建筑绝对地面高程仍未与水面或海底基准对齐。
- 选择范围：西 -118.31、南 33.70、东 -118.19、北 33.765（覆盖当前演示 DEM）。按 `Shape.STArea() > 10000` 平方英尺过滤大建筑，减轻浏览器网格和 GPU 负担。
- 当前打包数据：487 个有效 footprint，所有保留记录都有正的 `HEIGHT` 值。每个要素保留 County `OBJECTID`、原始高度（英尺）、换算高度（米）及更新状态。
- 更新：在 `frontend/` 目录运行 `npm.cmd run refresh:buildings`。脚本只在请求成功且含有效 Polygon 与高度时写入文件。该文件是服务查询的静态快照，不会在浏览器运行时访问县级服务器。

此数据让白模 footprint 和建筑高度来自真实县级 GIS；它不提供完整三维屋顶结构、室内模型、实时施工状态或可用于航行/应急决策的地面高程。
