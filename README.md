# 城市低空物流运营中心（LALOC）

> **Low-Altitude Logistics Operations Center** — 面向低空管理部门的城市低空物流 GIS 态势分析平台

---

## 项目简介

随着无人机物流行业的快速发展，城市低空空域管理需求日益迫切。LALOC 面向**低空管理部门**，以 **2D/3D GIS 地图**为核心载体，提供城市低空物流运行态势的可视化监控、智能航路规划、安全缓冲区分析以及低空密度热力分析能力。

项目围绕 **4 个 GIS 核心子系统** 构建：

| 编号 | 子系统 | 核心能力 |
|------|--------|----------|
| 1 | 综合态势大屏 | 2D/3D 地图上的航线监控、无人机动画、时间轴回放、空域与天气总览 |
| 2 | 智能航路规划 | A\* 栅格路径搜索 + 禁飞区/建筑约束绕行 + 应急迫降路径生成 |
| 3 | 安全缓冲区分析 | 多航线同时仿真、实时缓冲区碰撞检测与预警 |
| 4 | 安全热力分析 | 低空密度热力图、拥堵热点识别、区域密度统计图表 |

---

## 地图引擎

系统采用**双地图引擎架构**，通过 `MapContainer` 协调器实现一键切换，2D/3D 共享航线与区域数据：

| 模式 | 技术 | 能力 |
|------|------|------|
| 2D 平面地图 | 高德地图 JS API 2.0 | 轻量快速，适合日常监控与统计图表 |
| 3D 实景地球 | CesiumJS 1.121 | 全球地形、OSM Buildings 建筑白模、360° 自由视角 |

### 3D 场景特性

- **全球地形** — Cesium World Terrain，真实地表起伏
- **OSM 街道影像** — OpenStreetMap 高分辨率底图
- **OSM Buildings 白模** — 免费全球建筑 3D Tiles 图层，广州市区 45,000+ 栋
- **建筑交互** — 点击白模查看 OSM 属性（名称、高度、楼层数）
- **相机控制** — 左键旋转、右键缩放、中键俯仰

---

## 子系统一：综合态势大屏

> 路由 `/dashboard` — 默认首页

汇聚城市低空物流运行的核心指标与空间分布，形成统一的运行态势视图。

### 功能

- **核心指标卡片** — 禁飞区/限高区数量实时统计
- **航线列表** — 展示所有航线名称、距离、预计时间、状态（执行中/待执行）；点击某条航线高亮为琥珀色，其余航线降为半透明
- **无人机动画** — 2D/3D 模式下无人机沿航线循环飞行，带高度剖面
- **时间轴回放** — 选中航线后可切换为回放模式，拖拽时间轴查看无人机历史位置
- **3D 视角跟踪** — 回放模式下镜头自动锁定无人机实时跟随
- **天气面板** — 实时温度、湿度、风向风力 + 飞行适宜性指示
- **图例** — 禁飞区（红）、限高区（橙）、飞行阶段颜色图例

---

## 子系统二：智能航路规划

> 路由 `/path-planning` — 路径规划 · `/emergency-routing` — 应急航路

### 2.1 路径规划

基于**客户端 A\* 栅格算法**（前端 Vite 内置，无需后端即可运行），综合禁飞区、建筑群、限高区等多重约束生成安全飞行路径。

#### 算法设计

```
8 方向栅格 A* 搜索
  ├── 禁飞区（含 150m 安全缓冲）→ 不可通行，强制水平绕行
  ├── 建筑群 → 高于 20m 的建筑视为障碍 → 水平绕行
  │             低于 20m 的建筑 → 从上方飞越
  └── 防斜穿障碍角 → diagonal 移动时检查相邻两格
```

#### 后处理管线

```
A* 栅格路径 → 视线串拉拉直 → Chaikin 角切割柔滑 → 弧长均匀重采样 → 高度剖面生成
```

- **视线串拉（String Pulling）** — 消除栅格 45°/90° 阶梯锯齿，从起点尽量直连最远可见点（仅检查多边形内部，不重复缓冲带约束）
- **Chaikin 角切割** — 3 次迭代柔滑折线，曲线恒在控制多边形凸包内，不会过冲产生尖刺
- **弧长重采样** — 按固定距离（~36m）重采样为等距点，保证高度斜坡与阶段配色平滑
- **阶段分色** — 爬升段（绿）、巡航段（蓝）、下降段（橙）、禁飞区绕行（红）、建筑避让（紫）

#### 交互功能

- **地图点击选点** — 2D/3D 模式下直接点击地图设置起点、终点、途经点
- **坐标输入** — 支持手动输入 `lng,lat` 经纬度坐标
- **途经点支持** — 多个途经点，每段独立 A\* 规划后拼接，确保必经
- **禁飞区拦截** — 选点落入禁飞区时自动拒绝并弹窗提示
- **参数可调** — 无人机速度（5-30 m/s）、飞行限高（50-250m）、避障开关（禁飞区/限高区/建筑/天气）
- **进度反馈** — 规划过程实时显示进度条与阶段标签

### 2.2 应急航路规划

当无人机出现异常（低电量、设备故障、通信中断、天气突变等）时，自动搜索安全迫降点并生成应急飞行路径。

- **续航圈可视化** — 地图上绘制无人机当前电量的续航半径
- **安全点搜索** — 自动搜索续航范围内的充电站/配送站，按距离排序
- **一键规划** — 选择异常原因 → 点击故障无人机 → 自动推荐最近安全点 → 生成红色应急航路

---

## 子系统三：安全缓冲区分析

> 路由 `/safety-buffer/analysis`

支持多条航线同时仿真飞行，实时检测无人机之间的安全缓冲区碰撞，预警潜在冲突。

### 功能

- **安全范围配置** — 水平缓冲区（30-500m）、预警距离（50-800m）、垂直缓冲区（10-150m），滑条 + 输入框双重调节
- **多航线同时仿真** — 多架无人机沿不同航线同时飞行
- **实时碰撞检测** — 时间驱动的缓冲区重叠检测，碰撞时高亮警示
- **时间轴控制** — 仿真起止时间、回放速度、暂停/继续
- **2D/3D 统一** — 2D 模式渲染半透明圆形缓冲区，3D 模式渲染圆柱体缓冲区

---

## 子系统四：安全热力分析

> 路由 `/density/contour` — 热力分析 · `/density/hotspot` — 拥堵识别 · `/density/stats` — 密度统计

### 4.1 安全风险热力分析

综合低空运行密度与异常事件分布，生成安全风险热力图。

- **2D 热力图** — 基于高德 HeatMap 插件，低（绿）→ 中（黄）→ 高（红）三级分色
- **时间段筛选** — 早高峰/午间/晚高峰/全时段
- **时间动画** — 播放/暂停/重置，按时间切片动态渲染密度变化
- **透明度控制** — 2D 热力图透明度可调（0.1-1.0）
- **3D 密度柱体** — Cesium 模式下以柱状体高度表示密度

### 4.2 低空拥堵识别

按密度阈值自动识别低空空域拥堵热点。

- **参数配置** — 密度阈值、热点半径、分析时段
- **热点列表** — 高/中/低三级分类，点击聚焦到对应地图位置
- **2D 渲染** — 高德彩色圆形标记 + 信息窗（密度值、任务数）
- **3D 渲染** — Cesium 密度柱体叠加 OSM 建筑

### 4.3 区域密度统计

以 ECharts 图表形式展示区域密度统计数据。

- **统计卡片** — 总飞行架次、高密度空域数、最高密度值、预警空域数
- **高密度空域排名** — 柱状图（按飞行架次/小时）
- **高频航线统计** — 水平柱状图
- **多维度筛选** — 全时段/早高峰/午间/晚高峰 × Top 5/8/20

---

## 航线数据

系统内置 4 条广州城区 A\* 规划航线，覆盖天河、越秀、海珠、番禺、白云、黄埔六大行政区。每条航线由 `seed_routes.py` 通过 A\* 算法逐段规划生成（含禁飞区绕行 + 建筑高度剖面），共计 **23 个途经点**。

### 天河-海珠 急速配送线

`active` · 天河区 → 海珠区 · 约 7.2 km

| # | 途经点 | 坐标 |
|---|--------|------|
| 1 | 天河体育中心 | 113.3280, 23.1290 |
| 2 | 珠江新城 | 113.3190, 23.1180 |
| 3 | 广州塔 | 113.3050, 23.1050 |
| 4 | 海珠客运站 | 113.2800, 23.0850 |

### 越秀-番禺 干线物流

`active` · 越秀区 → 番禺区 · 约 17.1 km

| # | 途经点 | 坐标 |
|---|--------|------|
| 1 | 越秀公园 | 113.2690, 23.1450 |
| 2 | 海珠广场 | 113.2750, 23.1200 |
| 3 | 沥滘 | 113.2900, 23.0900 |
| 4 | 番禺广场 | 113.3200, 23.0500 |
| 5 | 番禺市桥 | 113.3500, 23.0200 |

### 白云-黄埔 长距运输线

`planned` · 白云区 → 黄埔区 · 约 23.3 km

| # | 途经点 | 坐标 |
|---|--------|------|
| 1 | 白云国际机场南 | 113.2680, 23.1650 |
| 2 | 白云新城 | 113.2900, 23.1550 |
| 3 | 天河智慧城 | 113.3300, 23.1400 |
| 4 | 大沙地 | 113.3800, 23.1200 |
| 5 | 黄埔开发区 | 113.4300, 23.1050 |
| 6 | 黄埔新港 | 113.4600, 23.0900 |

### 珠江新城 环城巡检线

`active` · 闭合环线 · 约 7.7 km

| # | 途经点 | 坐标 |
|---|--------|------|
| 1 | 花城广场 | 113.3200, 23.1200 |
| 2 | 广州大剧院 | 113.3300, 23.1250 |
| 3 | 天河城 | 113.3350, 23.1320 |
| 4 | 天河南 | 113.3300, 23.1380 |
| 5 | 体育西路 | 113.3200, 23.1400 |
| 6 | 珠江新城西 | 113.3120, 23.1350 |
| 7 | 猎德 | 113.3100, 23.1250 |
| 8 | 花城广场（闭合） | 113.3200, 23.1200 |

> 除种子航线外，系统支持通过 `POST /api/routes/` 动态创建新航线，路径规划页面也可实时生成自定义航线。

---

## 技术架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Vite 5)                          │
│  Element Plus 2.8 · Pinia · Vue Router 4 · ECharts 5              │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────────────────────────┐   │
│  │ Amap2DView      │  │ Cesium3DView                          │   │
│  │ 高德 2D 地图     │  │ CesiumJS + OSM Buildings 白模         │   │
│  └─────────────────┘  └──────────────────────────────────────┘   │
│              ↕ MapContainer 协调器                                 │
│                                                                   │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐               │
│  │态势大屏│ │航路规划│ │安全缓冲  │ │安全热力  │               │
│  │/dashboard│/path-  │ │/safety-  │ │/density  │               │
│  │        │ │planning│ │buffer    │ │/*        │               │
│  └────────┘ └────────┘ └──────────┘ └──────────┘               │
│                                                                   │
│  Vite 内联 Mock API（前端可独立开发调试）                           │
│  · 客户端 A* 栅格路径规划                                          │
│  · GeoJSON 禁飞区/限高区静态数据                                   │
│  · Cesium 静态资源 serve                                           │
└──────────────────────────┬───────────────────────────────────────┘
                           │ RESTful API (:8001)
┌──────────────────────────▼───────────────────────────────────────┐
│                  后端 (Python FastAPI 0.115)                       │
│  Uvicorn · SQLAlchemy 2.0 · GeoAlchemy2 · Pydantic V2            │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ zones    │ │ weather  │ │ path-    │ │ routes   │           │
│  │ 空域查询  │ │ 天气服务  │ │ finding  │ │ 航线管理  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ airspace │ │ safety   │ │ stat-    │ │ system   │           │
│  │ 空域CRUD │ │ 安全监管  │ │ istics   │ │ _mgmt    │           │
│  │          │ │          │ │ 统计决策  │ │ 系统管理  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└──────────────────────────┬───────────────────────────────────────┘
                           │ SQLAlchemy + GeoAlchemy2
┌──────────────────────────▼───────────────────────────────────────┐
│           数据库 (PostgreSQL 16 + PostGIS 3.4, Docker)            │
│  · no_fly_zones / height_limit_zones  (POLYGON, 空间索引)         │
│  · routes (LINESTRING, 含高度剖面) · buildings (OSM 45,644 栋)    │
│  · weather_records · anomaly_events · delivery_tasks ...         │
└──────────────────────────────────────────────────────────────────┘
```

### 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 (组合式 API) | `<script setup>` 语法 |
| 构建工具 | Vite 5 | HMR 热更新 |
| UI 组件 | Element Plus 2.8 | Vue 3 生态 |
| 2D 地图 | 高德 JS API 2.0 | 浅色主题 |
| 3D 引擎 | CesiumJS 1.121 | 地球 + 地形 + 建筑白模 |
| 图表 | ECharts 5 | 统计可视化 |
| 状态管理 | Pinia | Vue 3 官方推荐 |
| 后端框架 | FastAPI 0.115 | 异步 + 自动 OpenAPI 文档 |
| ORM | SQLAlchemy 2.0 + GeoAlchemy2 | PostGIS 空间查询 |
| 数据库 | PostgreSQL 16 + PostGIS 3.4 | Docker 部署 |
| GIS 处理 | GeoPandas + Shapely | Shapefile 导入 |

---

## 快速启动

### 前提条件

- Docker Desktop（运行数据库）
- Python 3.12+（后端）
- Node.js 20+（前端）
- [Cesium ion Token](https://ion.cesium.com/signup)（免费，用于 3D 地形与建筑白模）
- 高德 JS API Key（已内置在 `frontend/.env` 中）

### 1. 配置环境变量

**`frontend/.env`**（高德 Key 已配置，填写你的 Cesium ion Token）：
```env
VITE_AMAP_KEY=c11e639c1ff63561983c0b04b0384cb3
VITE_AMAP_SECURITY_CODE=c7a851501c339f3ad7bc403f8b32cdbc
VITE_CESIUM_ION_TOKEN=your_cesium_ion_token
```

**`backend/.env`**：
```env
DATABASE_URL=postgresql://admin:lowaltitude2024@localhost:15433/lowaltitude_logistics
AMAP_WEB_SERVICE_KEY=your_amap_web_service_key
```

### 2. 启动数据库

```bash
cd backend
docker compose up -d
```

> 容器映射端口 `15433:5432`，使用 15433 避免 Windows Hyper-V 保留端口冲突。

### 3. 初始化数据

```bash
cd backend
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt

# 导入禁飞区 / 限高区 Shapefile
python -m app.utils.shp_loader

# 生成模拟航线（A* 算法 + 建筑高度剖面）
python seed_routes.py

# (推荐) 导入广州 OSM 建筑数据（45,644 栋，约 2 分钟）
python -m app.utils.osm_loader

# 生成综合模拟数据
python seed_data.py
```

### 4. 启动后端

```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 6. 访问

| 页面 | 地址 |
|------|------|
| 态势大屏 | http://localhost:5173/ |
| 智能路径规划 | http://localhost:5173/path-planning |
| 应急航路规划 | http://localhost:5173/emergency-routing |
| 安全缓冲区分析 | http://localhost:5173/safety-buffer/analysis |
| 安全风险热力分析 | http://localhost:5173/density/contour |
| 低空拥堵识别 | http://localhost:5173/density/hotspot |
| 区域密度统计 | http://localhost:5173/density/stats |
| API 文档 (Swagger) | http://localhost:8001/docs |

### 关闭

```bash
# 前端 / 后端：Ctrl + C
docker stop lowaltitude-postgis    # 停止数据库（数据保留）
```

---

## 项目结构

```
LALOC/
├── README.md
├── docker-compose.yml
├── start.bat                         # Windows 一键启动脚本
│
├── frontend/                         # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── App.vue                   # 应用壳（顶部导航：4 个子系统）
│   │   ├── main.js                   # 入口
│   │   ├── api/                      # Axios API 封装
│   │   ├── components/               # 地图与通用组件
│   │   │   ├── MapContainer.vue      #   2D/3D 协调器
│   │   │   ├── Amap2DView.vue        #   高德 2D 地图
│   │   │   ├── Cesium3DView.vue      #   Cesium 3D 视图
│   │   │   ├── WeatherPanel.vue      #   天气面板
│   │   │   ├── ZoneLegend.vue        #   图例
│   │   │   └── TimelineSlider.vue    #   时间轴
│   │   ├── views/
│   │   │   ├── Dashboard.vue         #   子系统 1：态势大屏
│   │   │   ├── PathPlanning.vue      #   子系统 2：路径规划
│   │   │   ├── routing/
│   │   │   │   └── EmergencyRouting.vue  # 子系统 2：应急航路
│   │   │   ├── safety-buffer/
│   │   │   │   └── SafetyBufferAnalysis.vue  # 子系统 3：安全缓冲区
│   │   │   └── density/
│   │   │       ├── DensityContour.vue    # 子系统 4：热力分析
│   │   │       ├── HotspotAnalysis.vue   # 子系统 4：拥堵识别
│   │   │       └── DensityStats.vue      # 子系统 4：密度统计
│   │   ├── stores/                   # Pinia 状态
│   │   └── router/index.js           # 路由（7 条路由）
│   ├── public/
│   │   ├── geo/                      # GeoJSON 禁飞区/限高区（Mock API 用）
│   │   └── cesium/                   # Cesium 静态资源
│   ├── vite.config.js                # Vite 配置（Mock API + Cesium serve 插件）
│   ├── .env                          # 高德 Key + Cesium Token
│   └── package.json
│
├── backend/                          # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py                   # FastAPI 入口（CORS + 路由注册）
│   │   ├── config.py                 # 配置
│   │   ├── database.py               # 数据库连接
│   │   ├── api/                      # 路由模块
│   │   │   ├── zones.py              #   空域查询
│   │   │   ├── weather.py            #   天气服务
│   │   │   ├── pathfinding.py        #   路径规划
│   │   │   ├── routes.py             #   航线管理
│   │   │   ├── airspace.py           #   空域 CRUD
│   │   │   ├── safety.py             #   安全监管
│   │   │   ├── statistics.py         #   统计决策
│   │   │   └── system_mgmt.py        #   系统管理
│   │   ├── models/                   # SQLAlchemy 模型
│   │   ├── schemas/                  # Pydantic 校验
│   │   ├── services/                 # 业务逻辑
│   │   │   ├── astar.py              #   A* 算法（后端版）
│   │   │   ├── zone_service.py       #   空域服务
│   │   │   └── weather_service.py    #   天气服务
│   │   └── utils/
│   │       ├── shp_loader.py         #   Shapefile 导入
│   │       └── osm_loader.py         #   OSM 建筑导入
│   ├── seed_routes.py                # 模拟航线生成
│   ├── seed_data.py                  # 综合模拟数据
│   ├── .env
│   └── requirements.txt
│
├── data/
│   ├── nofly_zones/                  # 禁飞区 Shapefile
│   ├── height_limit_zones/           # 限高区 Shapefile
│   └── guangzhou_buildings.json      # OSM 建筑缓存
│
└── plans/                            # 设计文档
```

---

## API 接口

> 完整交互文档：http://localhost:8001/docs

### 前端调用的 GIS 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/zones/no-fly` | GET | 获取所有禁飞区（GeoJSON） |
| `/api/zones/height-limit` | GET | 获取所有限高区（GeoJSON） |
| `/api/zones/stats` | GET | 区域统计（禁飞区/限高区数量） |
| `/api/zones/check-point` | GET | 检查坐标是否在禁飞区/限高区内 |
| `/api/weather/live` | GET | 实时天气（温度/湿度/风向/风力） |
| `/api/weather/flyable` | GET | 飞行适宜性判断 |
| `/api/pathfinding/plan` | POST | A\* 路径规划（含建筑避障） |
| `/api/routes/` | GET | 获取所有航线（含高度剖面） |
| `/api/routes/{id}` | GET | 单条航线详情 |

### 路径规划请求示例

```json
POST /api/pathfinding/plan
{
  "start":      { "lng": 113.32, "lat": 23.12, "alt": 100 },
  "end":        { "lng": 113.264, "lat": 23.129, "alt": 100 },
  "waypoints":  [{ "lng": 113.30, "lat": 23.11, "alt": 100 }],
  "drone_speed":      15.0,
  "suggested_alt":    120,
  "avoid_buildings":  true,
  "avoid_no_fly":     true
}
```

### 后端完整路由一览

| 路由前缀 | 模块 | 主要端点 |
|----------|------|----------|
| `/api/zones` | 空域查询 | no-fly, height-limit, stats, check-point |
| `/api/weather` | 气象服务 | live, forecast, flyable |
| `/api/pathfinding` | 路径规划 | plan |
| `/api/routes` | 航线管理 | CRUD |
| `/api/airspace` | 空域管理 | no-fly-zones CRUD, height-limit-zones CRUD, query/point, query/range, compliance/check, stats |
| `/api/safety` | 安全监管 | conflict/check, congestion, risk-heatmap, events CRUD, records CRUD |
| `/api/statistics` | 统计决策 | city/overview, city/tasks-trend, city/route-utilization, enterprise/efficiency, service/quality, cost/analysis, station/layout |
| `/api/system` | 系统管理 | users CRUD, params, logs, service-status, gis-layers CRUD |

---

## 开发说明

### 前端独立开发

前端 Vite 配置内置 **Mock API 插件**，无需启动后端即可独立开发调试所有 4 个子系统：

- **禁飞区/限高区** — 从 `public/geo/*.geojson` 读取真实 Shapefile 转换数据
- **天气** — 返回模拟广州天气数据
- **航线** — 内置 3 条模拟航线
- **路径规划** — 完整的客户端 A\* 算法（8 方向栅格 + 广州建筑密度模型 + 150m 禁飞区缓冲 + 视线串拉 + Chaikin 柔滑）、禁飞区选点拦截

只需 `npm install && npm run dev` 即可开始前端开发。

### 数据库端口

| 配置位置 | 端口 | 说明 |
|----------|------|------|
| `docker-compose.yml` | `5433:5432` | 容器映射 |
| `backend/.env` | `15433` | 实际使用（避免 Hyper-V 占用） |

---

## 常见问题

### 3D 模式只有蓝色地球
- 检查 `frontend/.env` 中 `VITE_CESIUM_ION_TOKEN` 是否有效
- 在 [Cesium ion](https://ion.cesium.com/signup) 免费注册获取 Token
- 刷新后点击「3D 实景」按钮

### 路径规划穿模
- 使用后端时：确保已运行 `python -m app.utils.osm_loader` 导入广州建筑数据（45,644 栋）
- 使用前端 Mock 时：依赖内置的广州 8 个核心商圈建筑密度模型

### 地图空白
- 前端可独立于后端运行（Mock API），但地图需要有效的高德 Key
- 检查后端健康：`curl http://localhost:8001/health`

### 前端 API 404
- Mock API 仅拦截 zones、weather、routes、pathfinding/plan 四个模块
- 其余接口（airspace、safety、statistics、system）需启动后端

---

## 开源协议

MIT License
