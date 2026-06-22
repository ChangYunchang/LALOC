# 城市低空物流运营中心（LALOC）

> **Low-Altitude Logistics Operations Center** — 面向低空管理部门的城市低空物流 GIS 态势分析平台

---

## 项目简介

随着无人机物流行业的快速发展，城市低空空域管理需求日益迫切。LALOC 面向**低空管理部门**，以 **2D/3D GIS 地图**为核心载体，提供城市低空物流运行态势的可视化监控、智能航路规划、林场/农田巡视巡逻、安全缓冲区分析以及低空密度热力分析能力。

项目围绕 **4 个 GIS 核心子系统** 构建：

| 编号 | 子系统 | 核心能力 |
|------|--------|----------|
| 1 | 综合态势大屏 | 2D/3D 地图上的航线监控、无人机动画、时间轴回放、空域与天气总览 |
| 2 | 智能航路规划 | 选点 A\* 栅格路径搜索 + 林场/农田巡视巡逻（沿线飞行 & 空域巡回）+ 应急迫降路径生成 |
| 3 | 安全缓冲区分析 | 多航线同时仿真、实时缓冲区碰撞检测与预警（统一交互界面） |
| 4 | 安全热力分析 | 2D 低空密度热力图、拥堵热点识别、区域密度统计图表 |

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
- **航线列表** — 展示所有航线名称、距离、预计时间、状态（执行中/待执行）；点击某条航线高亮为琥珀色，其余航线降为半透明；支持本地规划航线跨页面共享
- **无人机动画** — 2D/3D 模式下无人机沿航线循环飞行，带高度剖面
- **时间轴回放** — 选中航线后可切换为回放模式，拖拽时间轴查看无人机历史位置
- **3D 视角跟踪** — 回放模式下镜头自动锁定无人机实时跟随
- **天气面板** — 实时温度、湿度、风向风力 + 飞行适宜性指示
- **图例** — 禁飞区（红）、限高区（橙）、飞行阶段颜色图例

---

## 子系统二：智能航路规划

> 路由 `/path-planning` — 智能路径规划 · `/emergency-routing` — 应急航路

### 2.1 智能路径规划

提供两大规划模式：**选点规划**（基于客户端 A\* 栅格算法）和 **林场/农田巡视巡逻**（沿线飞行 & 空域巡回）。

#### 模式一：选点规划

基于**客户端 A\* 栅格算法**（前端 Vite 内置，无需后端即可运行），综合禁飞区、建筑群、限高区等多重约束生成安全飞行路径。

##### 算法设计

```
8 方向栅格 A* 搜索
  ├── 禁飞区（含 150m 安全缓冲）→ 不可通行，强制水平绕行
  ├── 建筑群 → 高于 20m 的建筑视为障碍 → 水平绕行
  │             低于 20m 的建筑 → 从上方飞越
  └── 防斜穿障碍角 → diagonal 移动时检查相邻两格
```

##### 后处理管线

```
A* 栅格路径 → 视线串拉拉直 → Chaikin 角切割柔滑 → 弧长均匀重采样 → 高度剖面生成
```

- **视线串拉（String Pulling）** — 消除栅格 45°/90° 阶梯锯齿，从起点尽量直连最远可见点（仅检查多边形内部，不重复缓冲带约束）
- **Chaikin 角切割** — 3 次迭代柔滑折线，曲线恒在控制多边形凸包内，不会过冲产生尖刺
- **弧长重采样** — 按固定距离（~36m）重采样为等距点，保证高度斜坡与阶段配色平滑
- **阶段分色** — 爬升段（绿）、巡航段（蓝）、下降段（橙）、禁飞区绕行（红）、建筑避让（紫）

##### 交互功能

- **地图点击选点** — 2D/3D 模式下直接点击地图设置起点、终点、途经点
- **坐标输入** — 支持手动输入 `lng,lat` 经纬度坐标
- **途经点支持** — 多个途经点，每段独立 A\* 规划后拼接，确保必经
- **禁飞区拦截** — 选点落入禁飞区时自动拒绝并弹窗提示
- **参数可调** — 无人机速度（5-30 m/s）、强制飞行限高（50-250m）、避障开关（禁飞区/限高区/建筑/天气）
- **进度反馈** — 3D 模式下规划过程实时显示"计算真实建筑绕行航线"进度条与阶段标签

#### 模式二：林场/农田巡视巡逻

面向农业植保、林业巡检等场景，提供**沿线飞行**和**空域巡回**两种巡逻子模式。

##### 沿线飞行

在地图上手动绘制飞行线（折线），系统自动生成沿线巡视航线，无人机按照地形跟随逻辑沿线路飞行。

- **交互绘制** — 左键点击添加航路点，右键/Enter 完成，Esc 取消
- **实时反馈** — 绘制中显示各顶点，完成后展示航路点数量
- **一键清除** — 支持清除重绘
- **参数** — 离地飞行高度 30-200m（滑条调节）

##### 空域巡回

在地图上绘制多边形空域区域，系统根据空域自动生成巡逻路线。支持两种巡逻模式：

| 巡逻模式 | 算法 | 适用场景 |
|----------|------|----------|
| **边界巡逻** | 沿多边形边界密集采样（最小间距 30m） | 边界巡查、围栏巡检 |
| **犁地式覆盖** | Boustrophedon 蛇形折返条带扫描 | 全覆盖植保喷洒、地毯式搜索 |

- **交互绘制** — 左键点击添加顶点，点击首点/右键/Enter 闭合
- **犁地式参数** — 条带间距（30-500m）、巡逻方向角度（0°-180°）
- **路线生成** — 点击"生成巡逻路线"后实时计算并展示航路点数量

##### 规划参数

- **离地飞行高度** — 30-200m 滑条调节，巡逻模式下无人机按此高度跟随地形
- **无人机速度** — 5-30 m/s
- **避障选项** — 避开禁飞区、避开限高区、考虑天气
- **进度反馈** — 3D 模式下显示路径绘制过程（巡逻模式无建筑绕行进度条）

##### 保存航线

规划的巡逻航线可保存至态势大屏航线列表，跨页面共享。

### 2.2 应急航路规划

当无人机出现异常（低电量、设备故障、通信中断、天气突变等）时，自动搜索安全迫降点并生成应急飞行路径。

- **告警原因选择** — 低电量、设备故障、通信中断、天气突变、其他
- **无人机列表** — 展示飞行中无人机，含航线名称、电池电量、所在区域
- **一键触发** — 点击无人机触发告警，自动推荐最近安全点
- **续航圈可视化** — 地图上绘制无人机当前电量的续航半径
- **安全点搜索** — 自动搜索续航范围内的充电站/配送站，按距离排序
- **应急航路** — 生成红色应急路径，在地图上高亮显示

---

## 子系统三：安全缓冲区分析

> 路由 `/safety-buffer/analysis`

**统一交互界面**，将安全范围配置与缓冲区重叠分析整合在同一页面。支持多条航线同时仿真飞行，实时检测无人机之间的安全缓冲区碰撞，预警潜在冲突。

### 功能

- **安全范围配置** — 水平缓冲区（30-500m）、警戒距离（50-800m）、垂直缓冲区（10-150m），滑条 + 输入框双重调节，支持应用/恢复默认
- **多航线同时仿真** — 3 条预设交叉航线，5 架无人机同时飞行
- **实时碰撞检测** — 时间驱动的缓冲区重叠检测，碰撞时高亮警示（红/黄/绿三级状态指示）
- **无人机状态面板** — 每架无人机实时显示名称、颜色、冲突状态、当前位置坐标
- **时间轴控制** — 时段选择（早高峰/午间/下午/晚高峰/全时段）、仿真进度滑条、播放/暂停/重置
- **仿真速度调节** — 0.5× 至 8× 可调
- **2D/3D 统一** — 2D 模式渲染半透明圆形缓冲区，3D 模式渲染圆柱体缓冲区

### 碰撞检测算法

- **时间离散化** — 按仿真步长推进，逐帧检测所有无人机对
- **三维距离判定** — 水平距离 vs 水平缓冲区，垂直间距 vs 垂直缓冲区
- **三级预警** — 正常（绿色，距离 > 警戒距离）、警告（黄色，缓冲区重叠但未碰撞）、冲突（红色，严重重叠）

---

## 子系统四：安全热力分析

> 路由 `/density/contour` — 热力分析 · `/density/hotspot` — 拥堵识别 · `/density/stats` — 密度统计

**仅支持 2D 高德地图模式**，聚焦低空密度数据的空间可视化与统计分析。

### 4.1 安全风险热力分析

综合低空运行密度分布，生成安全风险热力图。

- **2D 热力图** — 基于高德 HeatMap 插件，低（绿）→ 中（黄）→ 高（红）三级分色
- **时间段筛选** — 早高峰（08:00-10:00）/ 午间（11:00-13:00）/ 下午（14:00-18:00）/ 晚高峰（18:00-20:00）
- **时间轴动画** — 播放/暂停/重置，按时间切片（5 分钟步长）动态渲染密度变化
- **透明度控制** — 热力图透明度可调（10%-100%）
- **时刻信息牌** — 实时显示当前时段、时间点、已加载密度采样点数量
- **图例** — 底部低-中-高渐变图例

### 4.2 低空拥堵识别

按密度阈值自动识别低空空域拥堵热点。

- **参数配置** — 密度阈值（1-100 飞行架次/小时）、热点半径（100-2000m）滑条调节
- **时段筛选** — 早高峰/午间/下午/晚高峰/全时段
- **热点列表** — 高/中/低三级分类（按密度阈值），显示坐标与飞行架次
- **2D 渲染** — 高德彩色圆形标记（红/橙/黄） + 信息窗（密度值、任务数）
- **地图联动** — 点击热点列表项自动聚焦到对应地图位置

### 4.3 区域密度统计

以 ECharts 图表形式展示区域密度统计数据。

- **统计卡片** — 总飞行架次、高密度空域数、最高密度值、预警空域数
- **高密度空域排名** — 柱状图（按飞行架次/小时）
- **高频航线统计** — 水平柱状图
- **多维度筛选** — 全时段/早高峰/午间/晚高峰 × Top 5/8/20
- **ECharts 5 渲染** — 支持交互式 tooltip、图例切换

---

## 航线数据

系统内置 3 条广州城区模拟航线，覆盖天河、越秀、海珠、白云、黄埔、荔湾六大行政区。航线由前端 Mock API 内置，含途经点坐标与高度信息。

### 天河→番禺干线

`active` · 天河区 → 番禺区 · 约 18.5 km

| # | 途经点 | 坐标 |
|---|--------|------|
| 1 | 天河体育中心 | 113.3245, 23.1201 |
| 2 | 海珠中转 | 113.3100, 23.0800 |
| 3 | 番禺广场 | 113.2994, 23.0500 |

### 白云→荔湾横线

`active` · 白云区 → 荔湾区 · 约 12.3 km

| # | 途经点 | 坐标 |
|---|--------|------|
| 1 | 白云新城 | 113.2994, 23.1540 |
| 2 | 越秀中 | 113.2800, 23.1380 |
| 3 | 荔湾老城 | 113.2500, 23.1050 |

### 黄埔→天河东线

`standby` · 黄埔区 → 天河区 · 约 15.8 km

| # | 途经点 | 坐标 |
|---|--------|------|
| 1 | 黄埔开发区 | 113.4500, 23.1100 |
| 2 | 天河智慧城 | 113.3900, 23.1200 |
| 3 | 珠江新城 | 113.3400, 23.1201 |

> 除模拟航线外，系统支持通过"智能路径规划"页面实时生成自定义航线（选点规划 / 沿线飞行 / 空域巡回），并保存至态势大屏航线列表跨页面共享。

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
│              ↕ MapContainer 协调器 (2D/3D 统一接口)                │
│                                                                   │
│  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │态势大屏│ │智能航路规划│ │安全缓冲  │ │安全热力  │             │
│  │/dashboard│/path-    │ │/safety-  │ │/density  │             │
│  │        │ │planning  │ │buffer    │ │/*        │             │
│  │        │ │/emergency│ │          │ │(仅 2D)   │             │
│  └────────┘ └──────────┘ └──────────┘ └──────────┘             │
│                                                                   │
│  巡逻路线生成引擎 (patrolRouteGenerator.js)                        │
│  · 边界巡逻 ─ 多边形密集采样                                       │
│  · 犁地式覆盖 ─ Boustrophedon 蛇形条带扫描                         │
│                                                                   │
│  Vite 内联 Mock API（前端可独立开发调试）                           │
│  · 客户端 A* 栅格路径规划（含建筑密度模型）                          │
│  · 禁飞区选点拦截 + 逐段规划 + 途经点拼接                           │
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
| 构建工具 | Vite 5 | HMR 热更新 + Mock API 插件 |
| UI 组件 | Element Plus 2.8 | Vue 3 生态 |
| 2D 地图 | 高德 JS API 2.0 (`@amap/amap-jsapi-loader`) | 浅色主题 |
| 3D 引擎 | CesiumJS 1.121 | 地球 + 地形 + 建筑白模（懒加载） |
| 图表 | ECharts 5 | 统计可视化 |
| 状态管理 | Pinia 2.2 | Vue 3 官方推荐 |
| 后端框架 | FastAPI 0.115 | 异步 + 自动 OpenAPI 文档 |
| ORM | SQLAlchemy 2.0 + GeoAlchemy2 | PostGIS 空间查询 |
| 数据库 | PostgreSQL 16 + PostGIS 3.4 | Docker 部署 |
| GIS 处理 | GeoPandas + Shapely + Pyogrio | Shapefile 导入 |

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

# （可选）生成模拟航线
python seed_routes.py

# （推荐）导入广州 OSM 建筑数据（45,644 栋，约 2 分钟）
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
| 智能路径规划（选点 + 巡逻） | http://localhost:5173/path-planning |
| 应急航路规划 | http://localhost:5173/emergency-routing |
| 安全缓冲区分析 | http://localhost:5173/safety-buffer/analysis |
| 安全风险热力分析（仅 2D） | http://localhost:5173/density/contour |
| 低空拥堵识别（仅 2D） | http://localhost:5173/density/hotspot |
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
│   │   ├── App.vue                   # 应用壳（顶部导航：4 个子系统下拉菜单）
│   │   ├── main.js                   # 入口
│   │   ├── api/                      # Axios API 封装
│   │   │   ├── request.js            #   Axios 实例（baseURL + 拦截器）
│   │   │   ├── zones.js              #   空域查询 API
│   │   │   ├── weather.js            #   天气 API
│   │   │   ├── pathfinding.js        #   路径规划 API
│   │   │   └── routes.js             #   航线管理 API
│   │   ├── components/               # 地图与通用组件
│   │   │   ├── MapContainer.vue      #   2D/3D 协调器（统一接口代理）
│   │   │   ├── Amap2DView.vue        #   高德 2D 地图（含绘图交互）
│   │   │   ├── Cesium3DView.vue      #   Cesium 3D 视图（懒加载，含绘图交互）
│   │   │   ├── WeatherPanel.vue      #   天气面板
│   │   │   ├── ZoneLegend.vue        #   空域图例
│   │   │   └── TimelineSlider.vue    #   时间轴组件
│   │   ├── views/
│   │   │   ├── Dashboard.vue         #   子系统 1：态势大屏
│   │   │   ├── PathPlanning.vue      #   子系统 2：智能路径规划（选点 + 巡逻双模式）
│   │   │   ├── routing/
│   │   │   │   └── EmergencyRouting.vue  # 子系统 2：应急航路规划
│   │   │   ├── safety-buffer/
│   │   │   │   └── SafetyBufferAnalysis.vue  # 子系统 3：安全缓冲区分析（统一界面）
│   │   │   └── density/
│   │   │       ├── DensityContour.vue    # 子系统 4：安全风险热力分析（仅 2D）
│   │   │       ├── HotspotAnalysis.vue   # 子系统 4：低空拥堵识别（仅 2D）
│   │   │       └── DensityStats.vue      # 子系统 4：区域密度统计
│   │   ├── stores/                   # Pinia 状态
│   │   │   ├── map.js                #   地图状态（实例、航线、标记）
│   │   │   └── zones.js              #   空域状态（禁飞区/限高区数据）
│   │   ├── utils/
│   │   │   └── patrolRouteGenerator.js  # 巡逻路线生成引擎（边界巡逻 + 犁地式覆盖）
│   │   └── router/index.js           # 路由配置（7 条路由）
│   ├── public/
│   │   ├── geo/                      # GeoJSON 禁飞区/限高区（Mock API 用）
│   │   │   ├── nofly_zones.geojson
│   │   │   └── height_limit_zones.geojson
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
│   │   │   ├── logistics.py          #   物流协同
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
| `/api/pathfinding/plan` | POST | 路径规划（支持选点 + 巡逻模式） |
| `/api/routes/` | GET | 获取所有航线（含高度剖面） |
| `/api/routes/{id}` | GET | 单条航线详情 |

### 路径规划请求示例

```json
POST /api/pathfinding/plan
{
  "start":      { "lng": 113.32, "lat": 23.12, "alt": 100 },
  "end":        { "lng": 113.264, "lat": 23.129, "alt": 100 },
  "waypoints":  [{ "lng": 113.30, "lat": 23.11, "alt": 100 }],
  "drone_speed":       15.0,
  "suggested_alt":     120,
  "avoid_buildings":   true,
  "avoid_no_fly":      true,
  "avoid_height_limit": true,
  "consider_weather":  true
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
| `/api/logistics` | 物流协同 | tasks CRUD, dispatch, tracking, delivery confirmation |
| `/api/system` | 系统管理 | users CRUD, params, logs, service-status, gis-layers CRUD |

---

## 开发说明

### 前端独立开发

前端 Vite 配置内置 **Mock API 插件**，无需启动后端即可独立开发调试所有 4 个子系统：

- **禁飞区/限高区** — 从 `public/geo/*.geojson` 读取真实 Shapefile 转换数据
- **天气** — 返回模拟广州天气数据（28°C，多云，东南风3级）
- **航线** — 内置 3 条模拟航线（天河→番禺、白云→荔湾、黄埔→天河）
- **路径规划** — 完整的客户端 A\* 算法（8 方向栅格 + 广州 8 大商圈建筑密度模型 + 150m 禁飞区缓冲 + 视线串拉 + Chaikin 柔滑 + 禁飞区选点拦截）
- **巡逻路线** — 客户端巡逻路线生成引擎（边界巡逻 + 犁地式覆盖），无需后端

只需 `npm install && npm run dev` 即可开始前端开发。

### Cesium 懒加载

CesiumJS 采用懒加载策略，仅在切换到 3D 模式时动态加载，减小首屏体积，加快 2D 模式初始化速度。

### 地图组件接口

`MapContainer` 协调器提供统一的 2D/3D 代理接口，上层视图无需关心当前地图模式：

- `drawPlanPath()` / `clearPlanPath()` — 绘制/清除规划路径
- `addMarker()` / `removeMarker()` — 标记点管理
- `startDrawLine()` / `startDrawPolygon()` / `stopDrawing()` — 交互式绘制
- `addClickHandler()` / `removeClickHandler()` — 地图点击选点
- `getViewer()` — 获取 Cesium Viewer 实例（3D 专用）

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

### 巡逻路线不显示
- 沿线飞行：确认已绘制至少 2 个航路点的飞行线
- 空域巡回：确认先绘制多边形 → 选择巡逻模式 → 点击"生成巡逻路线" → 再点击"开始路径规划"
- 巡逻模式路径规划仅在前端 Mock 模式下可用（后端路径规划接口需另行适配巡逻参数）

### 地图空白
- 前端可独立于后端运行（Mock API），但地图需要有效的高德 Key
- 检查后端健康：`curl http://localhost:8001/health`

### 前端 API 404
- Mock API 仅拦截 `zones`、`weather`、`routes`、`pathfinding/plan` 四个模块
- 其余接口（airspace、safety、statistics、logistics、system）需启动后端

---

## 开源协议

MIT License
