# 城市低空物流运营中心（LALOC）

> **Low-Altitude Logistics Operations Center** — 面向低空管理部门的城市低空物流 GIS 态势分析平台

---

## 项目简介

随着无人机物流行业的快速发展，城市低空空域管理需求日益迫切。LALOC 面向**低空管理部门**，以 **2D/3D GIS 地图**为核心载体，提供城市低空物流运行态势的可视化监控、智能航路规划、林场/农田巡视巡逻、安全缓冲区分析以及低空密度热力分析能力。

项目围绕 **4 个 GIS 核心子系统** 构建：

| 编号 | 子系统 | 核心能力 | 入口路由 |
|------|--------|----------|----------|
| 1 | 综合态势大屏 | 2D/3D 地图上的航线监控、无人机动画、时间轴回放、空域与天气总览 | `/dashboard` |
| 2 | 智能航路规划 | 选点 A\* 栅格路径搜索 + 林场/农田巡视巡逻 + 应急迫降路径生成 | `/path-planning` `/emergency-routing` |
| 3 | 安全缓冲区分析 | 多航线同时仿真、实时缓冲区碰撞检测与三级预警 | `/safety-buffer/analysis` |
| 4 | 安全热力分析 | 2D 低空密度热力图、拥堵热点识别、区域密度统计图表 | `/density/contour` `/density/hotspot` `/density/stats` |

---

## 子系统一：综合态势大屏

> 路由 `/dashboard` — 默认首页

汇聚城市低空物流运行的核心指标与空间分布，形成统一的运行态势视图。

### 功能

- **核心指标卡片** — 禁飞区/限高区数量实时统计
- **航线列表** — 展示 9 条模拟航线 + API 返回的航线 + 本地规划保存的航线，支持按名称、距离、时间、状态筛选；点击某条航线高亮为琥珀色，其余航线降为半透明
- **无人机动画** — 2D/3D 模式下无人机沿航线循环飞行，带高度剖面和阶段着色
- **时间轴回放** — 选中航线后可切换为回放模式，拖拽时间轴查看无人机历史位置（支持 0.5×/1×/2×/5× 速度）
- **3D 视角跟踪** — 回放模式下镜头自动锁定无人机实时跟随
- **天气面板** — 实时温度、湿度、风向风力 + 飞行适宜性指示（自动每 10 分钟刷新）
- **图例** — 禁飞区（红）、限高区（橙）、飞行阶段颜色图例

### 阶段着色

| 阶段 | 颜色 | 说明 |
|------|------|------|
| 起飞爬升段 | 🟢 `#22c55e` | 起始至巡航高度 |
| 巡航段 | 🔵 `#3b82f6` | 稳定飞行 |
| 降落下降段 | 🟠 `#f59e0b` | 接近终点 |
| 限高区绕行段 | 🔴 `#ef4444` | 受高度限制区域 |
| 建筑避让段 | 🟣 `#a855f7` | 绕过高楼建筑 |

---

## 子系统二：智能航路规划

### 2.1 智能路径规划

> 路由 `/path-planning`

提供两大规划模式：**选点规划**（基于客户端 Theta\* 栅格算法）和 **林场/农田巡视巡逻**。

#### 模式一：选点规划

基于**客户端栅格路径搜索算法**（前端 Vite Mock API 内置，无需后端即可运行），综合禁飞区、建筑群、限高区等多重约束生成安全飞行路径。

**算法设计：**

```
8 方向栅格 Theta* 搜索（任意角度路径）
  ├── 禁飞区（含 150m 安全缓冲）→ 不可通行，强制水平绕行
  ├── 建筑群 → 高于 20m 的建筑视为障碍 → 水平绕行
  │             低于 20m 的建筑 → 从上方飞越
  └── 防斜穿障碍角 → diagonal 移动时检查相邻两格
```

**后处理管线：**

```
栅格路径 → 视线串拉（String Pulling）→ Chaikin 角切割（3 次迭代）→ 弧长均匀重采样（~36m）→ 高度剖面生成
```

- **视线串拉** — 消除栅格 45°/90° 阶梯锯齿，从起点尽量直连最远可见点
- **Chaikin 角切割** — 曲线恒在控制多边形凸包内，不会过冲产生尖刺
- **弧长重采样** — 按固定距离重采样为等距点，保证高度斜坡与阶段配色平滑
- **阶段分色** — 爬升段（绿）、巡航段（蓝）、下降段（橙）、禁飞区绕行（红）、建筑避让（紫）

**交互功能：**

- **地图点击选点** — 2D/3D 模式下直接点击地图设置起点、终点、途经点
- **坐标输入** — 支持手动输入 `lng,lat` 经纬度坐标
- **途经点支持** — 多个途经点，每段独立规划后拼接，确保必经
- **禁飞区拦截** — 选点落入禁飞区时自动拒绝并弹窗提示
- **参数可调** — 无人机速度（5-30 m/s）、强制飞行限高（50-250m）、避障开关（禁飞区/限高区/建筑/天气）
- **进度反馈** — 3D 模式下规划过程实时显示"计算真实建筑绕行航线"进度条与阶段标签
- **保存航线** — 规划结果可命名并保存至态势大屏航线列表，跨页面共享

#### 模式二：林场/农田巡视巡逻

面向农业植保、林业巡检等场景，提供**沿线飞行**和**空域巡回**两种巡逻子模式。

**沿线飞行：** 在地图上手动绘制飞行线（折线），系统自动生成沿线巡视航线。

- 左键点击添加航路点，右键/Enter 完成，Esc 取消
- 实时显示航路点数量
- 离地飞行高度 30-200m（滑条调节）

**空域巡回：** 在地图上绘制多边形区域，系统根据空域自动生成巡逻路线。

| 巡逻模式 | 算法 | 适用场景 |
|----------|------|----------|
| **边界巡逻** | 沿多边形边界密集采样（最小间距 30m） | 边界巡查、围栏巡检 |
| **犁地式覆盖** | Boustrophedon 蛇形折返条带扫描 | 全覆盖植保喷洒、地毯式搜索 |

- 条带间距（30-500m）、巡逻方向角度（0°-180°）可调
- 点击"生成巡逻路线"后实时计算并展示航路点数量

**巡逻参数：** 离地飞行高度（30-200m 滑条）、无人机速度（5-30 m/s）、避障选项（禁飞区/限高区/天气）

### 2.2 应急航路规划

> 路由 `/emergency-routing` — 仅支持 2D 高德地图

当无人机出现异常时，自动搜索安全迫降点并生成应急飞行路径。

- **告警原因选择** — 低电量、设备故障、通信中断，支持筛选过滤
- **飞行中无人机列表** — 5 架预置无人机，含航线名称、电池电量、所在区域、告警原因；低电量（<30%）卡片高亮
- **一键触发** — 点击无人机触发告警，自动推荐最近安全点
- **续航圈可视化** — 地图上绘制无人机当前电量的续航半径（绿色安全圈/蓝色临界圈）
- **安全点搜索** — 6 个预置充电站/维修站，按距离排序，色标显示可用性
- **应急航路** — 二次贝塞尔曲线生成红色应急路径，含方向箭头和起终点标记
- **电池评估** — 充足/勉强/不足三级评估，实时显示预计飞行时间
- **导出 JSON** — 支持下载应急航路数据

---

## 子系统三：安全缓冲区分析

> 路由 `/safety-buffer/analysis`

**统一交互界面**，将安全范围配置与缓冲区重叠分析整合在同一页面。支持多条航线同时仿真飞行，实时检测无人机之间的安全缓冲区碰撞，预警潜在冲突。

### 功能

- **安全范围配置** — 水平缓冲区（30-500m）、警戒距离（50-800m）、垂直缓冲区（10-150m），滑条 + 输入框双重调节，支持应用/恢复默认
- **多航线同时仿真** — 4 条交叉航线，最多 8 架无人机同时飞行（按时段变化：早高峰 8 架、午间 4 架、下午 6 架、晚高峰 8 架）
- **实时碰撞检测** — 时间驱动的三维距离判定，碰撞时高亮警示
- **三级预警** —

| 等级 | 条件 | 颜色 | 行为 |
|------|------|------|------|
| 正常 | 水平距离 > 警戒距离 | 🟢 绿色 | 全速飞行 |
| 警告 | 水平距离 < 警戒距离 × 2 | 🟡 黄色 | 减速至 50% |
| 冲突 | 水平距离 < 缓冲区 × 2 | 🔴 红色 | 停止/让行 |

- **让行策略** — 同航线跟随者停止，跨航线高索引让行
- **无人机状态面板** — 每架无人机实时显示名称、颜色、状态标签（正常/减速/停止）、类型、航线名、进度、高度、有效速度
- **碰撞事件日志** — 带时间戳的事件记录，含事件类型和处置建议
- **时间轴控制** — 时段选择（早高峰/午间/下午/晚高峰）、仿真进度滑条、播放/暂停/重置
- **仿真速度调节** — 0.5× 至 8× 可调
- **2D/3D 统一** — 2D 模式渲染半透明圆形缓冲区，3D 模式渲染圆柱体缓冲区

---

## 子系统四：安全热力分析

> **仅支持 2D 高德地图模式**，聚焦低空密度数据的空间可视化与统计分析。

### 4.1 安全风险热力分析

> 路由 `/density/contour`

综合低空运行密度分布，生成安全风险热力图。

- **2D 热力图** — 基于高德 HeatMap 插件，蓝色（低）→ 青色 → 黄色 → 橙色 → 红色（高）五级渐变
- **时间段筛选** — 早高峰（08:00-10:00）/ 午间（11:00-13:00）/ 下午（14:00-18:00）/ 晚高峰（18:00-20:00）
- **时间轴动画** — 播放/暂停/重置，按时间切片（5 分钟步长）动态渲染密度变化
- **透明度控制** — 热力图透明度可调（10%-100%）
- **时刻信息牌** — 实时显示当前时段、时间点、已加载密度采样点数量
- **密度模拟** — 沿 9 条航线走廊生成采样点，含随机抖动和扩散点，按时段因子和峰谷因子加权
- **图例** — 底部低-中-高渐变图例

### 4.2 低空拥堵识别

> 路由 `/density/hotspot`

按密度阈值自动识别低空空域拥堵热点。

- **参数配置** — 密度阈值（5-100 飞行架次/小时）、热点半径（100-2000m）滑条调节
- **时段筛选** — 早高峰/午间/下午/晚高峰/全时段
- **热点列表** — 高/中/低三级分类（按密度阈值），显示坐标与飞行架次、峰值时段
- **2D 渲染** — 高德彩色圆形标记（红/橙/黄）+ 信息窗（密度值、关联航线）
- **地图联动** — 点击热点列表项自动聚焦到对应地图位置
- **7 个预置拥堵点** — 覆盖天河中心枢纽、白云东路、黄埔东部走廊、越秀纵向通道等

### 4.3 区域密度统计

> 路由 `/density/stats`

以 ECharts 图表形式展示区域密度统计数据，纯图表页面，不含地图。

- **统计卡片** — 总飞行架次、高密度空域数、最高密度值、预警空域数
- **高密度空域排名** — 柱状图（8 个空域区域，颜色按密度分级）
- **高频航线统计** — 水平柱状图（8 条核心航线，渐变着色）
- **24 小时密度趋势** — 折线图，含最大值标记、均值线、面积填充
- **多维度筛选** — 全时段/早高峰/午间/晚高峰 × Top 5/8/20

---

## 地图引擎

系统采用**双地图引擎架构**，通过 `MapContainer` 协调器实现一键切换，2D/3D 共享航线与区域数据：

| 模式 | 技术 | 能力 |
|------|------|------|
| 2D 平面地图 | 高德地图 JS API 2.0 | 轻量快速，适合日常监控与统计图表，支持热力图、绘图交互 |
| 3D 实景地球 | CesiumJS 1.121 | 全球地形、OSM 街道影像、OSM Buildings 建筑白模、360° 自由视角 |

### 3D 场景特性

- **全球地形** — Cesium World Terrain，真实地表起伏（超时 15s 自动回退椭球体）
- **OSM 街道影像** — ESRI World Imagery 高清底图
- **OSM Buildings 白模** — 免费全球建筑 3D Tiles 图层，自动异步加载
- **建筑交互** — 点击白模查看 OSM 属性（名称、高度、楼层数）
- **相机控制** — 左键旋转、右键缩放、中键俯仰
- **AGL 高度** — 所有航线高度为地面以上高度（Above Ground Level），非海平面高度

### MapContainer 统一接口

`MapContainer` 协调器提供统一的 2D/3D 代理接口，上层视图无需关心当前地图模式：

| 方法 | 用途 |
|------|------|
| `drawRoutes(routes)` / `drawBackgroundRoutes(routes)` | 绘制航线（动画/背景） |
| `highlightRoute(id)` / `resetRouteHighlight()` | 航线高亮/还原 |
| `drawPlanPath(path, profile, opts)` / `clearPlanPath()` | 规划路径绘制/清除 |
| `addMarker(lng, lat, color)` / `removeMarker(m)` / `clearCustomMarkers()` | 标记点管理 |
| `startDrawLine(cb)` / `startDrawPolygon(cb)` / `stopDrawing()` / `clearDrawing()` | 交互式绘制 |
| `addClickHandler(cb)` / `removeClickHandler()` | 地图点击选点 |
| `setDronePosition(id, progress)` / `pauseDrone()` / `resumeDrone()` | 无人机动画控制 |
| `getViewer()` | 获取 Cesium Viewer 实例（3D 专用） |
| `getViewMode()` | 获取当前模式（`'2D'` / `'3D'`） |

---

## 快速启动

### 前提条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop) — 运行数据库
- Python 3.12+ — 后端
- Node.js 20+ — 前端
- [Cesium ion Token](https://ion.cesium.com/signup) — 免费注册，用于 3D 地形与建筑白模
- 高德 JS API Key — 已内置在 `frontend/.env` 中，也可替换为自己的

### 1. 配置环境变量

**`frontend/.env`**（高德 Key 已配置，填写你的 Cesium ion Token）：

```env
VITE_AMAP_KEY=c11e639c1ff63561983c0b04b0384cb3
VITE_AMAP_SECURITY_CODE=c7a851501c339f3ad7bc403f8b32cdbc
VITE_CESIUM_ION_TOKEN=your_cesium_ion_token
```

**`backend/.env`**：

```env
DATABASE_URL=postgresql://admin:lowaltitude2024@localhost:5433/lowaltitude_logistics
AMAP_WEB_SERVICE_KEY=your_amap_web_service_key
AMAP_SECURITY_CODE=your_amap_security_code
```

### 2. 启动数据库

```bash
cd backend
docker compose up -d
```

> 容器映射端口 `5433:5432`。数据库启动后，PostgreSQL + PostGIS 即可使用。

### 3. 初始化数据（可选）

```bash
cd backend
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt

# 导入禁飞区 / 限高区 Shapefile
python -m app.utils.shp_loader

# 生成模拟航线
python seed_routes.py

# 生成综合模拟数据（企业、订单、任务、无人机、事件等）
python seed_data.py
```

> 前端内置 Mock API，即使不初始化数据库数据，核心 GIS 功能也可正常运行。

### 4. 启动后端

```bash
cd backend
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

> `--reload` 启用热重载，代码修改后自动重启。

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 6. 一键启动（Windows）

双击项目根目录下的 `start.bat`，自动依次启动数据库、后端（端口 8000）、前端（端口 5173）。

### 7. 访问地址

| 页面 | 地址 |
|------|------|
| 态势大屏（首页） | http://localhost:5173/ |
| 智能路径规划（选点 + 巡逻） | http://localhost:5173/path-planning |
| 应急航路规划 | http://localhost:5173/emergency-routing |
| 安全缓冲区分析 | http://localhost:5173/safety-buffer/analysis |
| 安全风险热力分析（仅 2D） | http://localhost:5173/density/contour |
| 低空拥堵识别（仅 2D） | http://localhost:5173/density/hotspot |
| 区域密度统计 | http://localhost:5173/density/stats |
| 后端 API 文档 (Swagger) | http://localhost:8001/docs |
| 后端健康检查 | http://localhost:8001/health |

### 关闭

```bash
# 前端 / 后端：Ctrl + C
docker stop lowaltitude-postgis    # 停止数据库（数据保留在 Docker volume 中）
```

---

## 项目结构

```
LALOC/
├── README.md
├── docker-compose.yml
├── start.bat                         # Windows 一键启动脚本
│
├── frontend/                         # Vue 3 + Vite 前端（端口 5173）
│   ├── index.html
│   ├── vite.config.js                # Vite 配置（Mock API 插件 + Cesium 静态资源 serve）
│   ├── .env                          # 高德 Key + Cesium Token
│   ├── package.json
│   ├── public/
│   │   ├── geo/                      # GeoJSON 禁飞区/限高区（Mock API 读取）
│   │   │   ├── nofly_zones.geojson
│   │   │   └── height_limit_zones.geojson
│   │   └── cesium/                   # Cesium 静态资源（dev 时由 Vite 从 node_modules serve）
│   └── src/
│       ├── App.vue                   # 应用壳（顶部导航：4 个子系统入口 + 实时时钟）
│       ├── main.js                   # 入口（注册 Element Plus + Pinia + Router）
│       ├── style.css                 # 全局样式（浅色科技风主题）
│       ├── api/                      # Axios API 封装（baseURL: /api）
│       │   ├── request.js            #   Axios 实例 + 响应拦截器
│       │   ├── zones.js              #   空域查询 API
│       │   ├── weather.js            #   天气 API
│       │   ├── pathfinding.js        #   路径规划 API
│       │   └── routes.js             #   航线管理 API
│       ├── components/               # 地图与通用组件
│       │   ├── MapContainer.vue      #   2D/3D 协调器（统一接口代理 + 缓存策略）
│       │   ├── Amap2DView.vue        #   高德 2D 地图（含绘图交互、航线动画、区域渲染）
│       │   ├── Cesium3DView.vue      #   Cesium 3D 视图（懒加载、建筑绕行 A*、地形采样）
│       │   ├── WeatherPanel.vue      #   天气面板（含飞行适宜性判断）
│       │   ├── ZoneLegend.vue        #   空域图例（区域数量 + 阶段颜色）
│       │   └── TimelineSlider.vue    #   时间轴组件（时段切换 + 回放控制）
│       ├── views/
│       │   ├── Dashboard.vue         #   子系统 1：态势大屏
│       │   ├── PathPlanning.vue      #   子系统 2：智能路径规划（选点 + 巡逻双模式）
│       │   ├── routing/
│       │   │   └── EmergencyRouting.vue  # 子系统 2：应急航路规划（自建 AMap 实例）
│       │   ├── safety-buffer/
│       │   │   └── SafetyBufferAnalysis.vue  # 子系统 3：安全缓冲区分析（统一界面）
│       │   └── density/
│       │       ├── DensityContour.vue    # 子系统 4：安全风险热力分析（仅 2D）
│       │       ├── HotspotAnalysis.vue   # 子系统 4：低空拥堵识别（仅 2D）
│       │       └── DensityStats.vue      # 子系统 4：区域密度统计（纯 ECharts）
│       ├── stores/                   # Pinia 状态管理
│       │   ├── map.js                #   地图状态（实例、航线、标记、模式切换）
│       │   └── zones.js              #   空域状态（禁飞区/限高区 GeoJSON + 统计）
│       ├── data/
│       │   └── sampleRoutes.js       #   9 条广州模拟航线（Catmull-Rom 样条 + 高度剖面）
│       ├── utils/
│       │   └── patrolRouteGenerator.js  # 巡逻路线生成引擎（边界巡逻 + 犁地式覆盖）
│       └── router/
│           └── index.js              # 路由配置（8 条路由，懒加载）
│
├── backend/                          # Python FastAPI 后端（端口 8001）
│   ├── .env
│   ├── requirements.txt
│   ├── seed_routes.py                # 模拟航线生成（调用 A* 引擎）
│   ├── seed_data.py                  # 综合模拟数据生成（7 类实体）
│   ├── alembic/                      # 数据库迁移（已配置，待生成版本文件）
│   ├── alembic.ini
│   └── app/
│       ├── main.py                   # FastAPI 入口（CORS + 9 个路由注册）
│       ├── config.py                 # 配置（pydantic-settings，读取 .env）
│       ├── database.py               # 数据库连接（SQLAlchemy + psycopg 3）
│       ├── api/                      # 路由模块（9 个）
│       │   ├── zones.py              #   空域查询（GET no-fly / height-limit / stats / check-point）
│       │   ├── weather.py            #   天气服务（live / forecast / flyable）
│       │   ├── pathfinding.py        #   路径规划（POST plan）
│       │   ├── routes.py             #   航线管理（CRUD）
│       │   ├── airspace.py           #   空域 CRUD + 空间查询 + 合规审查
│       │   ├── logistics.py          #   物流协同（企业/订单/任务/站点/无人机 + 调度）
│       │   ├── safety.py             #   安全监管（冲突检测/拥堵/热力/事件/台账）
│       │   ├── statistics.py         #   统计决策（城市/企业/服务/成本/站点）
│       │   └── system_mgmt.py        #   系统管理（用户/参数/日志/GIS 图层）
│       ├── models/                   # SQLAlchemy 模型（8 个模块）
│       │   ├── zones.py              #   no_fly_zones / height_limit_zones（含 PostGIS 几何）
│       │   ├── buildings.py          #   buildings（OSM 建筑，含空间索引）
│       │   ├── routes.py             #   routes（LINESTRING + JSON 途经点）
│       │   ├── drones.py             #   drone_flights / weather_records
│       │   ├── logistics.py          #   5 表：enterprises / orders / tasks / stations / drones
│       │   ├── safety.py             #   2 表：anomaly_events / safety_records
│       │   └── system.py             #   4 表：users / params / logs / gis_layers
│       ├── schemas/                  # Pydantic 校验
│       │   ├── zones.py
│       │   ├── routes.py
│       │   └── pathfinding.py
│       ├── services/                 # 业务逻辑
│       │   ├── astar.py              #   Theta* 路径规划引擎（Bresenham 视线 + 高度剖面）
│       │   ├── zone_service.py       #   空域查询服务（ST_AsGeoJSON / ST_Contains）
│       │   └── weather_service.py    #   天气服务（高德 API + 30 分钟缓存 + 回退）
│       └── utils/
│           ├── shp_loader.py         #   Shapefile → PostGIS 导入器
│           └── osm_loader.py         #   OSM 建筑数据导入器（Overpass API + 本地缓存）
│
└── data/                             # 原始数据
    ├── nofly_zones/                  # 禁飞区 Shapefile（JinFeiQu.*）
    ├── height_limit_zones/           # 限高区 Shapefile（XianGaoQu.*）
    └── guangzhou_buildings.json      # 广州 OSM 建筑缓存（~14 MB，45,644 栋）
```

---

## 技术架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Vite 5)                          │
│  Element Plus 2.8 · Pinia 2.2 · Vue Router 4 · ECharts 6        │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────────────────────────┐   │
│  │ Amap2DView      │  │ Cesium3DView                          │   │
│  │ 高德 JS API 2.0  │  │ CesiumJS 1.121 + OSM Buildings        │   │
│  └─────────────────┘  └──────────────────────────────────────┘   │
│              ↕ MapContainer 协调器 (统一 2D/3D 接口)               │
│                                                                   │
│  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │态势大屏│ │智能航路规划│ │安全缓冲  │ │安全热力  │             │
│  │/dashboard│/path-    │ │/safety-  │ │/density  │             │
│  │        │ │planning  │ │buffer    │ │/* (仅2D) │             │
│  │        │ │/emergency│ │          │ │          │             │
│  └────────┘ └──────────┘ └──────────┘ └──────────┘             │
│                                                                   │
│  Vite 内置 Mock API（前端可独立开发调试）                           │
│  · 客户端 Theta* 栅格路径规划（含建筑密度模型 + 禁飞区缓冲）         │
│  · GeoJSON 禁飞区/限高区静态数据                                   │
│  · 巡逻路线生成引擎（边界巡逻 + 犁地式覆盖）                         │
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
│  │ airspace │ │ logistics│ │ safety   │ │ statistics│           │
│  │ 空域CRUD │ │ 物流协同  │ │ 安全监管  │ │ 统计决策  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐                                                   │
│  │ system   │                                                   │
│  │ _mgmt    │                                                   │
│  │ 系统管理  │                                                   │
│  └──────────┘                                                   │
└──────────────────────────┬───────────────────────────────────────┘
                           │ SQLAlchemy + GeoAlchemy2 + psycopg 3
┌──────────────────────────▼───────────────────────────────────────┐
│           数据库 (PostgreSQL 16 + PostGIS 3.4, Docker)            │
│  · no_fly_zones / height_limit_zones  (POLYGON, 空间索引)         │
│  · routes (LINESTRING) · buildings (OSM 45,644 栋)                │
│  · enterprises · orders · tasks · stations · drone_resources     │
│  · anomaly_events · safety_records · weather_records             │
│  · system_users · system_params · operation_logs · gis_layers    │
└──────────────────────────────────────────────────────────────────┘
```

### 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3.5（组合式 API） | `<script setup>` 语法 |
| 构建工具 | Vite 5 | HMR 热更新 + Mock API 插件 |
| UI 组件 | Element Plus 2.8 | Vue 3 生态 |
| 2D 地图 | 高德 JS API 2.0 (`@amap/amap-jsapi-loader`) | 浅色主题 |
| 3D 引擎 | CesiumJS 1.121 | 地球 + 地形 + 建筑白模（懒加载） |
| 图表 | ECharts 6 | 统计可视化 |
| 状态管理 | Pinia 2.2 | Vue 3 官方推荐 |
| 后端框架 | FastAPI 0.115 | 异步 + 自动 OpenAPI 文档 |
| ORM | SQLAlchemy 2.0 + GeoAlchemy2 | PostGIS 空间查询 |
| 数据库驱动 | psycopg 3 | 解决 Windows 编码兼容性问题 |
| 数据库 | PostgreSQL 16 + PostGIS 3.4 | Docker 部署 |
| GIS 处理 | GeoPandas + Shapely + Pyogrio | Shapefile 导入 |

---

## 前端独立开发

前端 Vite 配置内置 **Mock API 插件**，无需启动后端即可独立开发调试所有 4 个子系统：

- **禁飞区/限高区** — 从 `public/geo/*.geojson` 读取真实 Shapefile 转换数据
- **天气** — 返回模拟广州天气数据（28°C，多云，东南风 3 级）
- **航线** — 内置 9 条模拟航线（Catmull-Rom 样条插值 + 高度剖面）
- **路径规划** — 完整的客户端栅格路径搜索算法（Theta\* 变体 + 广州 8 大商圈建筑密度模型 + 150m 禁飞区缓冲 + 视线串拉 + Chaikin 柔滑 + 禁飞区选点拦截）
- **巡逻路线** — 客户端巡逻路线生成引擎（边界巡逻 + 犁地式覆盖），无需后端
- **应急航路** — 客户端贝塞尔曲线生成 + 电池评估算法
- **安全缓冲区** — 客户端实时碰撞检测 + 多航线仿真引擎
- **热力分析** — 客户端密度采样点生成 + 时段加权 + ECharts 图表

只需 `npm install && npm run dev` 即可开始前端开发。

### Cesium 懒加载

CesiumJS 采用懒加载策略：仅在切换到 3D 模式时动态注入 `<script>` 和 `<link>` 标签加载 Cesium 库。减小首屏体积，加快 2D 模式初始化速度。

### Mock API 未覆盖的模块

Mock API 仅拦截 `zones`、`weather`、`routes`、`pathfinding/plan` 四个前端实际调用的模块。其余后端模块（`airspace`、`logistics`、`safety`、`statistics`、`system`）需启动后端 + 数据库才能使用。

---

## API 接口

### 前端调用的核心 GIS 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/zones/no-fly` | GET | 获取所有禁飞区（GeoJSON FeatureCollection） |
| `/api/zones/height-limit` | GET | 获取所有限高区（GeoJSON FeatureCollection） |
| `/api/zones/stats` | GET | 区域统计（禁飞区/限高区数量） |
| `/api/zones/check-point` | GET | 检查坐标是否在禁飞区/限高区内 |
| `/api/weather/live` | GET | 实时天气（温度/湿度/风向/风力） |
| `/api/weather/flyable` | GET | 飞行适宜性判断 |
| `/api/pathfinding/plan` | POST | 路径规划（支持选点 + 途经点） |
| `/api/routes/` | GET | 获取所有航线（含高度剖面与 GeoJSON 几何） |
| `/api/routes/{id}` | GET | 单条航线详情 |
| `/api/routes/` | POST | 创建新航线 |

### 路径规划请求示例

```json
POST /api/pathfinding/plan
{
  "start":      { "lng": 113.32, "lat": 23.12, "alt": 100 },
  "end":        { "lng": 113.264, "lat": 23.129, "alt": 100 },
  "waypoints":  [{ "lng": 113.30, "lat": 23.11, "alt": 100 }],
  "drone_speed":       15.0,
  "cruise_alt":        120,
  "safety_margin":     50.0,
  "avoid_no_fly":      true,
  "avoid_height_limit": true,
  "avoid_buildings":   true,
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
| `/api/airspace` | 空域管理 | no-fly-zones / height-limit-zones CRUD, query/point, query/range, compliance/check, stats |
| `/api/logistics` | 物流协同 | enterprises / orders / tasks / stations / drones CRUD, scheduling/match, scheduling/assign, scheduling/control |
| `/api/safety` | 安全监管 | conflict/check, congestion, risk-heatmap, events CRUD + handle, records CRUD + archive |
| `/api/statistics` | 统计决策 | city/overview, city/tasks-trend, city/route-utilization, enterprise/efficiency, service/quality, cost/analysis, station/layout |
| `/api/system` | 系统管理 | users CRUD, params + categories, logs, service-status, gis-layers CRUD |

> 完整交互文档（含请求/响应模型）：http://localhost:8001/docs

---

## 航线数据

系统内置 **9 条广州城区模拟航线**（`frontend/src/data/sampleRoutes.js`），覆盖天河、越秀、海珠、白云、黄埔、荔湾、番禺、南沙八大行政区。航线由 Catmull-Rom 样条插值生成（每条约 90 个路径点），含完整高度剖面和阶段着色信息。

| # | 名称 | 色标 | 途经区域 |
|---|------|------|----------|
| 1 | 番禺→天河干线 | 🔵 `#3b82f6` | 番禺 → 海珠 → 天河（珠江新城） |
| 2 | 白云→天河横线 | 🟣 `#8b5cf6` | 白云 → 越秀 → 天河 |
| 3 | 黄埔→白云线 | 🟢 `#10b981` | 黄埔 → 天河 → 白云 |
| 4 | 南沙→黄埔线 | 🟠 `#f59e0b` | 南沙 → 番禺 → 黄埔 |
| 5 | 荔湾→天河线 | 🩷 `#ec4899` | 荔湾 → 越秀 → 天河 |
| 6 | 越秀纵向线 | 🔷 `#06b6d4` | 越秀核心区南北向 |
| 7 | 白云横向线 | 🟠 `#f97316` | 白云区东西向 |
| 8 | 天河→黄埔线 | ⚫ `#64748b` | 天河 → 黄埔 |
| 9 | 番禺→天河南线 | 🔴 `#dc2626` | 番禺 → 海珠南 → 天河南 |

> 除模拟航线外，系统支持通过"智能路径规划"页面实时生成自定义航线（选点规划 / 沿线飞行 / 空域巡回），并保存至态势大屏航线列表跨页面共享。

---

## 开发说明

### 数据库端口说明

| 配置位置 | 端口 | 说明 |
|----------|------|------|
| `docker-compose.yml` | `5433:5432` | 容器端口映射 |
| `backend/.env` `DATABASE_URL` | `5433` | 应用连接使用 |
| `backend/alembic.ini` | `5432` | Alembic 直接连容器内部端口（需手动修正为 5433） |

> 使用 5433 端口避免与 Windows Hyper-V 保留端口冲突。注意 `alembic.ini` 中的端口与 `.env` 不一致，如需运行 Alembic 迁移请先修正。

### 地图组件开发

`MapContainer` 协调器提供统一的 2D/3D 代理接口。新增页面建议通过 `MapContainer` 使用地图，而非自建地图实例（`EmergencyRouting` 和 `SafetyBufferAnalysis` 出于历史原因自建了实例，后续可考虑统一迁移）。

3D 模式下新增航线需注意：
- 航线高度需从 AGL（地面以上高度）转换为 MSL（海平面高度），通过 `Cesium.sampleTerrainMostDetailed()` 采样地形高度
- 建筑白模高度通过 `Cesium.createOsmBuildingsAsync()` 异步获取

### 数据库模型扩展

后端模型分为 8 个模块文件。新增模型时需：
1. 在 `models/` 创建/更新模块文件
2. 在 `app/database.py` 中导入以注册到 `Base.metadata`
3. 如需 Alembic 管理迁移，在 `alembic/env.py` 中导入模型

---

## 常见问题

### 3D 模式只有蓝色地球
- 检查 `frontend/.env` 中 `VITE_CESIUM_ION_TOKEN` 是否有效
- 在 [Cesium ion](https://ion.cesium.com/signup) 免费注册获取 Token
- 确认网络能访问 `api.cesium.com`
- 刷新页面后重新点击「3D 实景」按钮

### 路径规划穿模
- **前端 Mock 模式**：依赖内置的广州 8 个核心商圈建筑密度模型，郊区无覆盖；3D 模式下会采样真实 OSM 建筑高度进行 A\* 绕行
- **后端模式**：确保已运行 `python -m app.utils.osm_loader` 导入广州建筑数据
- 建议设置合适的飞行限高（50-250m）以获得最佳避障效果

### 巡逻路线不显示
- **沿线飞行**：确认已绘制至少 2 个航路点的飞行线，点击"开始路径规划"
- **空域巡回**：确认先绘制多边形 → 选择巡逻模式（边界/犁地式）→ 点击"生成巡逻路线" → 再点击"开始路径规划"
- 巡逻模式路径规划依赖前端 Mock API（后端路径规划接口需另行适配巡逻参数）

### 地图空白
- 前端可独立于后端运行（Mock API），但地图需要有效的高德 Key
- 检查 `frontend/.env` 中 `VITE_AMAP_KEY` 和 `VITE_AMAP_SECURITY_CODE` 是否有效
- 检查后端健康：`curl http://localhost:8001/health`
- 确认浏览器控制台无 CORS 或 JS 加载错误

### 前端部分 API 返回 404
- Mock API 仅拦截 `zones`、`weather`、`routes`、`pathfinding/plan` 四个模块
- 其余接口（`airspace`、`safety`、`statistics`、`logistics`、`system`）需启动后端 + 数据库
- 确认后端已启动：`curl http://localhost:8001/health` 应返回 `{"status":"healthy"}`

### 数据库连接失败
- 确认 Docker Desktop 已运行，容器 `lowaltitude-postgis` 状态为 Up
- 检查端口 5433 未被其他程序占用
- `backend/.env` 中 `DATABASE_URL` 的端口应为 `5433`（非 5432）

---

## 开源协议

MIT License
