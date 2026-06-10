# 建筑物空间数据可行性分析

## 问题

> 能否通过高德 3D 实景中的建筑物白模，获取建筑物的空间位置和体积数据，用于路径规划？

## 结论：不可行 ❌

**高德 JS API 2.0 的 `AMap.Buildings` 图层是纯渲染层，不暴露任何建筑物几何数据。**

---

## 1. 技术分析

### 1.1 当前实现方式

[MapContainer.vue:108-119](frontend/src/components/MapContainer.vue#L108-L119) 中的建筑物白模：

```js
buildingsLayer = new AMap.Buildings({
  zooms: [14, 20],
  heightFactor: 1.5,
  wallColor: 'rgba(255, 255, 255, 0.9)',
  roofColor: 'rgba(240, 240, 245, 0.95)',
  borderColor: 'rgba(200, 200, 210, 0.6)',
  borderWeight: 1,
})
```

`AMap.Buildings` 的全部配置项都是**视觉样式参数**（颜色、透明度、高度缩放因子、缩放级别范围），没有任何数据获取相关的选项。

### 1.2 为什么无法获取数据

| 原因 | 说明 |
|------|------|
| **瓦片渲染架构** | 建筑物白模以地图瓦片形式由高德服务端预渲染，客户端只接收可视化结果，不接收结构化几何数据 |
| **无查询 API** | `AMap.Buildings` 实例上没有 `getBuildings()`、`queryBuilding()`、`getBuildingAt()` 等方法 |
| **无事件回调** | 不支持 click/hover 返回被点击建筑的 ID 或几何信息 |
| **黑盒设计** | 建筑数据是高德的核心商业资产，通过付费数据服务单独售卖，不通过免费 JS API 暴露 |

### 1.3 验证结果

- 搜索了 `@amap/amap-jsapi-loader` npm 包 —— **无任何建筑数据相关类型定义**
- 搜索了高德官方 JS API 文档 —— **无 Buildings 数据提取接口**
- 搜索了 GitHub 上 Amap 建筑数据获取项目 —— 均使用**其他数据源或爬虫方式**，而非 JS API

---

## 2. 替代方案对比

### 方案 A：OpenStreetMap (OSM) 建筑数据 ✅ 推荐

| 维度 | 评估 |
|------|------|
| **数据覆盖** | 广州市区建筑轮廓覆盖良好，含 `building:levels`（层数）和 `height`（高度）标签 |
| **数据精度** | 米级精度，适合路径规划 |
| **获取方式** | Overpass API / GeoFabrik 下载 / osm2pgsql 导入 PostGIS |
| **成本** | 完全免费开源 |
| **更新频率** | 社区持续更新 |
| **集成难度** | 中等 — 需要 ETL 管道导入 PostGIS，复用现有 `build_grid_from_db()` 模式 |

**数据字段示例：**
```json
{
  "building": "yes",
  "building:levels": "25",
  "height": "85",
  "name": "广州国际金融中心"
}
```

### 方案 B：高德商业数据服务

| 维度 | 评估 |
|------|------|
| **数据覆盖** | 完整，与白模渲染数据同源 |
| **数据精度** | 高精度 |
| **获取方式** | 需联系高德商务购买，非自助 |
| **成本** | 高（商业授权费） |
| **集成难度** | 未知（取决于交付格式） |

### 方案 C：其他数据源

| 来源 | 评估 |
|------|------|
| **百度地图 Buildings** | 同样为渲染层，不暴露数据 |
| **天地图** | 有建筑数据服务但需申请 |
| **Microsoft Building Footprints** | 全球覆盖，但仅2D轮廓，无高度 |

---

## 3. 对现有架构的影响

### 3.1 现有路径规划架构

[astar.py](backend/app/services/astar.py) 当前约束模型：

| 约束类型 | 数据来源 | 精度 |
|----------|----------|------|
| 禁飞区（blocked cells） | PostGIS `no_fly_zones` 表 | 200m网格 |
| 限高区（height limits） | PostGIS `height_limit_zones` 表 | 200m网格 |
| 建筑物障碍 | **无** | — |

### 3.2 引入建筑数据后需要的改动

| 改动 | 说明 |
|------|------|
| **新增数据表** | `buildings` 表（PolygonZ 或 MultiPolygonZ 几何 + height 属性） |
| **数据导入** | OSM → PostGIS ETL 管道 |
| **A\* 精度提升** | 网格从 200m 缩小到 **20-50m**（建筑级避障需要） |
| **3D 约束** | 在 `build_grid_from_db()` 中增加建筑物阻塞检查 |
| **高度剖面** | `compute_altitude_profile()` 已支持限高区，可扩展为建筑高度避让 |
| **性能优化** | 更细的网格 = 更大的搜索空间，可能需要分层 A\* 或 JPS |

### 3.3 概念架构

```
OSM 建筑数据 (.pbf / .osm)
        │
        ▼ osm2pgsql
PostGIS buildings 表 (PolygonZ)
        │
        ▼ build_grid_from_db() 增加建筑约束
GridMap { blocked, height_limits, building_heights }
        │
        ▼ astar_search() 使用更细网格
路径（避开建筑物 + 禁飞区 + 限高区）
```

---

## 4. 建议

### 短期（本周可做）

采用 **OSM 建筑物数据**作为路径规划的建筑物障碍数据源：

1. 从 GeoFabrik 下载广东省 OSM 数据
2. 使用 `osm2pgsql` 导入建筑相关数据到 PostGIS
3. 新增 `buildings` 表，存储建筑轮廓和高度
4. 将 A\* 网格精度从 200m 降到 50m
5. 在 `build_grid_from_db()` 中增加建筑物碰撞检测

### 中期

- 实现分层路径规划（粗粒度全局规划 + 细粒度局部避障）
- 添加建筑高度 3D 可视化层（2.5D 拉伸或自定义 3D 模型）

### 长期

- 如果预算允许，联系高德购买建筑 3D 数据获得更完整的覆盖
- 多数据源融合（OSM + 高德 + 实时感知）

---

## 5. 关键结论

> **高德 3D 白模是"看的"，不是"用的"。** 它提供了优秀的可视化效果，但无法作为路径规划的数据输入。路径规划需要的建筑空间数据，应通过 OSM（免费）或高德商业数据服务（付费）获取，存入 PostGIS 后在 A\* 算法中使用。