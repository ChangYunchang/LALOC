# 城市低空物流运营中心（LALOC）

> **Low-Altitude Logistics Operations Center** — 面向低空管理部门的城市低空物流 GIS 态势分析平台

---

## 项目简介

随着无人机物流行业的快速发展，城市低空空域管理需求日益迫切。LALOC 面向**低空管理部门**，以 **2D/3D GIS 地图**为核心载体，提供城市低空物流运行态势的可视化监控、智能航路规划、林场/农田巡视巡逻、安全缓冲区分析以及低空密度热力分析能力。

项目围绕 **4 个 GIS 核心子系统** 构建：

| 编号 | 子系统 | 核心能力 | 入口路由 |
|------|--------|----------|----------|
| 1 | 综合态势大屏 | 2D/3D 航线监控、无人机动画、时间轴回放、天气与空域总览 | `/dashboard` |
| 2 | 智能航路规划 | 选点 Theta\* 路径搜索 + 林场/农田巡逻 + 应急迫降 | `/path-planning` `/emergency-routing` |
| 3 | 安全缓冲区分析 | 多航线同时仿真、实时碰撞检测与三级预警 | `/safety-buffer/analysis` |
| 4 | 安全热力分析 | 2D 热力图、拥堵热点识别、密度统计图表（ECharts） | `/density/contour` `/density/hotspot` `/density/stats` |

---

## 子系统一：综合态势大屏

> 路由 `/dashboard` — 默认首页

汇聚城市低空物流运行的核心指标与空间分布，形成统一的运行态势视图。

### 功能

- **左侧面板** — 实时天气组件、禁飞区/限高区数量统计卡片、航线列表（支持按名称/距离/时间筛选）、当前选中航线详细信息
- **2D/3D 地图切换** — 左上角一键切换高德 2D 平面地图与 Cesium 3D 实景地球
- **航线动画** — 无人机沿航线循环飞行，按飞行阶段（爬升/巡航/下降/限高区/建筑避让）分段着色
- **航线高亮** — 点击航线列表项，该航线高亮为琥珀色，其余航线降为半透明
- **时间轴回放** — 选中航线后切换为回放模式，拖拽时间轴查看历史位置（支持 0.5×/1×/2×/5× 速度）
- **3D 视角跟踪** — 回放模式下镜头自动锁定无人机实时跟随
- **图例** — 禁飞区（红）、限高区（橙）、飞行阶段颜色图例

### 阶段着色

| 阶段 | 颜色 | 说明 |
|------|------|------|
| 起飞爬升段 | 🟢 `#22c55e` | 起始至巡航高度 |
| 巡航段 | 🔵 `#3b82f6` | 稳定飞行 |
| 降落下降段 | 🟠 `#f59e0b` | 接近终点 |
| 限高区飞行段 | 🔵 `#3b82f6` | 限高区内压低高度飞行 |
| 建筑避让段 | 🟣 `#a855f7` | 越过高楼建筑 |

### 航线数据来源

Dashboard 聚合三个来源的航线数据：
1. **SAMPLE_ROUTES** — 9 条广州城区模拟航线（GCJ-02 坐标，内置前端）
2. **后端 API 航线** — 从数据库加载的航线（WGS-84 坐标，含 `crs` 标识自动转换）
3. **本地保存的航线** — 从路径规划页面保存的航线（WGS-84 坐标，跨页面共享）

> 系统通过 `crs` 字段自动识别坐标系：WGS-84（`crs: "wgs84"`）自动转换为 GCJ-02 以匹配高德 2D 地图，3D Cesium 直接使用 WGS-84 原生坐标，确保 2D/3D 位置一致。

---

## 子系统二：智能航路规划

### 2.1 智能路径规划

> 路由 `/path-planning`

提供两大规划模式：**选点规划**（基于 Theta\* 栅格算法）和 **林场/农田巡视巡逻**。

#### 模式一：选点规划

基于**后端 Theta\* 栅格路径搜索算法**，综合禁飞区、建筑群、限高区等多重约束生成安全飞行路径。

**算法设计：**

```
8 方向栅格 Theta* 搜索（任意角度路径）
  ├── 禁飞区（含 150m 安全缓冲）→ 不可通行，强制水平绕行
  ├── 建筑群 → 高于 15m 的建筑视为障碍 → 水平绕行
  │             低于 15m 的建筑 → 从上方飞越
  ├── 限高区 → 代价惩罚（<50m 限高代价翻倍）→ 引导绕行
  └── 防斜穿障碍角 → diagonal 移动时检查相邻两格
```

**高度剖面策略：**

限高区和建筑物检查具有**最高优先级**，即使起降段也必须遵守：

```
高度计算优先级（由高到低）：
  1. 限高区 → 压低至 min(巡航高度, 限高区最大高度)
  2. 建筑物 → 爬升至 max(巡航高度, 建筑高度 + 安全余量)
  3. 起飞段 → 地面爬升至巡航高度
  4. 降落段 → 巡航高度降至降落高度
  5. 巡航段 → 保持巡航高度
```

**后处理管线：**

```
栅格路径 → 视线串拉（String Pulling）→ 弧长均匀重采样 → 高度剖面生成
```

- **视线串拉** — 消除栅格 45°/90° 阶梯锯齿，从起点尽量直连最远可见点
- **弧长重采样** — 按固定距离重采样为等距点，保证高度斜坡与阶段配色平滑
- **阶段分色** — 爬升段（绿）、巡航段（蓝）、下降段（橙）、限高区飞行（蓝）、建筑避让（紫）

**交互功能：**

- **地图点击选点** — 2D/3D 模式下直接点击地图设置起点、终点、途经点，综合禁飞区/限高区实时检测
- **坐标输入** — 支持手动输入 `lng,lat` 经纬度坐标，自动检测限高区
- **途经点支持** — 多个途经点，每段独立规划后拼接，确保必经
- **限高区前置警告** — 规划前自动检测所有航点的限高区约束：当巡航高度超过限高区最大高度时弹出警告对话框，提示限高区名称和限高数值，用户必须返回调整巡航高度
- **禁飞区拦截** — 选点落入禁飞区时自动拒绝并弹窗提示
- **参数可调** — 无人机速度（5-30 m/s）、建议飞行高度（50-250m）、避障开关（禁飞区/考虑限高区最大高度/建筑物/天气）
- **进度反馈** — 3D 模式下规划过程实时显示进度条与阶段标签
- **保存航线** — 规划结果可命名并保存至态势大屏航线列表，跨页面共享

> **关于「考虑限高区的最大高度」**：勾选后，路径规划会遵循限高区的最大允许高度。当用户设置的巡航高度超过航点所在限高区的最大高度时，系统会在规划前弹出警告，提示用户调整巡航高度至限高区允许的范围。航线中的限高区段高度将被自动压低。

#### 模式二：林场/农田巡视巡逻

面向农业植保、林业巡检等场景，提供**沿线飞行**和**空域巡回**两种巡逻子模式。

**沿线飞行：** 在地图上手动绘制飞行线（折线），系统自动生成沿线巡视航线。

- 左键点击添加航路点，右键/Enter 完成，Esc 取消
- 离地飞行高度 30-200m（滑条调节）

**空域巡回：** 在地图上绘制多边形区域，系统根据空域自动生成巡逻路线。

| 巡逻模式 | 算法 | 适用场景 |
|----------|------|----------|
| **边界巡逻** | 沿多边形边界密集采样（最小间距 30m） | 边界巡查、围栏巡检 |
| **犁地式覆盖** | Boustrophedon 蛇形折返条带扫描 | 全覆盖植保喷洒、地毯式搜索 |

- 条带间距（30-500m）、巡逻方向角度（0°-180°）可调

**巡逻参数：** 离地飞行高度（30-200m 滑条）、无人机速度（5-30 m/s）、避障选项

### 2.2 应急航路规划

> 路由 `/emergency-routing` — 仅支持 2D 高德地图

当无人机出现异常时，自动搜索安全迫降点并生成应急飞行路径。

- **告警原因选择** — 低电量、设备故障、通信中断，支持筛选过滤
- **飞行中无人机列表** — 5 架预置无人机，含航线名称、电池电量、所在区域
- **一键触发** — 点击无人机触发告警，自动推荐最近安全点
- **续航圈可视化** — 地图上绘制无人机当前电量的续航半径
- **应急航路** — 二次贝塞尔曲线生成红色应急路径，含方向箭头和起终点标记
- **电池评估** — 充足/勉强/不足三级评估

---

## 子系统三：安全缓冲区分析

> 路由 `/safety-buffer/analysis`

支持多条航线同时仿真飞行，实时检测无人机之间的安全缓冲区碰撞，预警潜在冲突。

### 功能

- **安全范围配置** — 水平缓冲区（30-500m）、警戒距离（50-800m）、垂直缓冲区（10-150m）
- **多航线同时仿真** — 4 条交叉航线，最多 8 架无人机同时飞行（按时段变化）
- **实时碰撞检测** — 时间驱动的三维距离判定
- **三级预警** —

| 等级 | 条件 | 颜色 | 行为 |
|------|------|------|------|
| 正常 | 水平距离 > 警戒距离 | 🟢 绿色 | 全速飞行 |
| 警告 | 水平距离 < 警戒距离 | 🟡 黄色 | 减速至 50% |
| 冲突 | 水平距离 < 缓冲区 | 🔴 红色 | 停止/让行 |

- **让行策略** — 同航线跟随者停止，跨航线高索引让行
- **2D/3D 统一** — 2D 模式渲染半透明圆形缓冲区，3D 模式渲染圆柱体缓冲区

---

## 子系统四：安全热力分析

### 4.1 安全风险热力分析

> 路由 `/density/contour` — 仅支持 2D

综合低空运行密度分布，生成安全风险热力图。蓝色（低）→ 青色 → 黄色 → 橙色 → 红色（高）五级渐变。

### 4.2 低空拥堵识别

> 路由 `/density/hotspot` — 仅支持 2D

按密度阈值自动识别低空空域拥堵热点，支持高/中/低三级分类和地图联动。

### 4.3 区域密度统计

> 路由 `/density/stats`

以 ECharts 图表展示区域密度数据：高密度空域排行（柱状图）、高频航线统计（水平柱状图）、24 小时密度趋势（折线图）。

---

## 地图引擎

系统采用**双地图引擎架构**，通过 `MapContainer` 协调器实现一键切换：

| 模式 | 技术 | 坐标系 | 能力 |
|------|------|--------|------|
| 2D 平面地图 | 高德地图 JS API 2.0 | **GCJ-02**（国测局加密） | 轻量快速，支持热力图、绘图交互 |
| 3D 实景地球 | CesiumJS 1.121 | **WGS-84**（GPS 原生） | 全球地形、OSM Buildings 白模、360° 自由视角 |

### 坐标系处理

系统内部统一使用 **WGS-84** 坐标系，与数据库 PostGIS（SRID 4326）一致。2D 展示时自动转换为 GCJ-02：

| 航线来源 | 存储坐标系 | 2D 渲染 | 3D 渲染 |
|----------|-----------|---------|---------|
| 后端 API 航线 | WGS-84 (`crs: "wgs84"`) | WGS-84 → GCJ-02 自动转换 | 原生 WGS-84 |
| 路径规划保存 | WGS-84 (`crs: "wgs84"`) | WGS-84 → GCJ-02 自动转换 | 原生 WGS-84 |
| 内置示例航线 | GCJ-02 | 直接使用 | GCJ-02 → WGS-84 自动转换 |

> `crs` 字段是确保 2D/3D 位置一致的关键——前端根据此标志决定是否执行坐标转换，确保无论在哪个视图，航线位置都正确对应。

### 3D 场景特性

- **全球地形** — Cesium World Terrain，真实地表起伏
- **OSM 街道影像** — ESRI World Imagery 高清底图
- **OSM Buildings 白模** — 免费全球建筑 3D Tiles 图层
- **AGL 高度** — 所有航线高度为地面以上高度（Above Ground Level）

### MapContainer 统一接口

`MapContainer` 协调器提供统一的 2D/3D 代理接口，上层视图无需关心当前地图模式：

| 方法 | 用途 |
|------|------|
| `drawRoutes(routes)` | 绘制航线（含动画） |
| `drawBackgroundRoutes(routes)` | 绘制背景航线 |
| `highlightRoute(id)` / `resetRouteHighlight()` | 航线高亮/还原 |
| `drawPlanPath(path, profile)` / `clearPlanPath()` | 规划路径绘制/清除 |
| `addMarker(lng, lat, color)` / `removeMarker(m)` | 标记点管理 |
| `startDrawLine(cb)` / `startDrawPolygon(cb)` | 交互式绘制 |
| `addClickHandler(cb)` / `removeClickHandler()` | 地图点击选点 |
| `setDronePosition(id, progress)` | 无人机动画控制 |
| `getViewer()` | 获取 Cesium Viewer 实例 |

---

## 快速启动

### 前提条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop) — 运行数据库
- Python 3.12+ — 后端
- Node.js 20+ — 前端
- [Cesium ion Token](https://ion.cesium.com/signup) — 免费注册，用于 3D 地形与建筑白模
- 高德 JS API Key — 已内置在 `frontend/.env` 中

### 1. 配置环境变量

**`frontend/.env`**：

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

> 容器映射端口 `5433:5432`，数据库 `lowaltitude_logistics`，用户 `admin` / 密码 `lowaltitude2024`。

### 3. 安装依赖

```bash
# 后端 Python 依赖
cd backend
# Windows
venv\Scripts\activate
# macOS / Linux: source venv/bin/activate
pip install -r requirements.txt

# 前端依赖
cd ../frontend
npm install
```

### 4. 初始化数据库

```bash
cd backend
venv\Scripts\activate   # Windows

# 创建数据库表 + 生成模拟数据（企业、订单、任务、无人机、事件等）
python seed_data.py

# 导入禁飞区/限高区 GeoJSON 数据（32 个禁飞区 + 8 个限高区）
python -c "
import sys, json; sys.path.insert(0, '.')
from app.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
for table, file in [('height_limit_zones', '../frontend/public/geo/height_limit_zones.geojson'),
                      ('no_fly_zones', '../frontend/public/geo/nofly_zones.geojson')]:
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for feat in data['features']:
        coords = feat['geometry']['coordinates'][0]
        wkt = f\"POLYGON(({', '.join(f'{c[0]} {c[1]}' for c in coords)}))\"
        props = feat['properties']
        db.execute(text(f'INSERT INTO {table} (name, geometry, max_altitude, min_altitude, reason) VALUES (:name, ST_SetSRID(ST_GeomFromText(:wkt), 4326), :maxalt, :minalt, :reason)'),
            {'name': props.get('name',''), 'wkt': wkt, 'maxalt': props.get('max_altitude',120), 'minalt': props.get('min_altitude',0), 'reason': props.get('reason','')})
db.commit(); db.close()
print('GeoJSON data imported')
"

# 生成模拟航线
python seed_routes.py
```

### 5. 启动后端

```bash
cd backend
venv\Scripts\activate          # Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> `--reload` 启用热重载，代码修改后自动重启。后端运行在 **http://localhost:8000**。

### 6. 启动前端

```bash
cd frontend
npm run dev
```

> 前端运行在 **http://localhost:5173**。Vite 开发服务器会将 `/api` 请求代理转发到后端 `http://localhost:8000`。

### 7. 一键启动（Windows）

双击项目根目录下的 `start.bat`，自动依次启动数据库、后端、前端。

### 8. 访问地址

| 页面 | 地址 |
|------|------|
| 态势大屏（首页） | http://localhost:5173/ |
| 智能路径规划 | http://localhost:5173/path-planning |
| 应急航路规划 | http://localhost:5173/emergency-routing |
| 安全缓冲区分析 | http://localhost:5173/safety-buffer/analysis |
| 安全风险热力分析 | http://localhost:5173/density/contour |
| 低空拥堵识别 | http://localhost:5173/density/hotspot |
| 区域密度统计 | http://localhost:5173/density/stats |
| 后端 API 文档 (Swagger) | http://localhost:8000/docs |
| 后端健康检查 | http://localhost:8000/health |

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
├── Structure.md                      # 系统功能结构文档
├── docker-compose.yml
├── start.bat                         # Windows 一键启动脚本
│
├── frontend/                         # Vue 3 + Vite 前端（端口 5173）
│   ├── .env                          # 高德 Key + Cesium Token
│   ├── vite.config.js                # Vite 配置（API 代理 + Cesium 静态资源）
│   ├── package.json
│   ├── public/
│   │   └── geo/                      # GeoJSON 禁飞区/限高区数据
│   │       ├── nofly_zones.geojson   #   32 个禁飞区
│   │       └── height_limit_zones.geojson  # 8 个限高区（max_altitude=120m）
│   └── src/
│       ├── App.vue                   # 应用壳（顶部导航 + 4 个子系统入口 + 实时时钟）
│       ├── main.js                   # 入口（Element Plus + Pinia + Router）
│       ├── style.css                 # 全局样式（浅色科技风主题）
│       ├── api/                      # Axios API 封装
│       │   ├── request.js            #   Axios 实例 + 响应拦截器
│       │   ├── zones.js              #   空域查询 API（禁飞区/限高区/统计/点位检查）
│       │   ├── weather.js            #   天气 API（实时/预报/适飞判断）
│       │   ├── pathfinding.js        #   路径规划 API（POST plan）
│       │   └── routes.js             #   航线管理 API（CRUD）
│       ├── components/               # 地图与通用组件
│       │   ├── MapContainer.vue      #   2D/3D 协调器（统一接口代理）
│       │   ├── Amap2DView.vue        #   高德 2D 地图（含绘图交互、航线动画、坐标转换）
│       │   ├── Cesium3DView.vue      #   Cesium 3D 视图（懒加载、建筑绕行、地形采样）
│       │   ├── WeatherPanel.vue      #   天气面板（含飞行适宜性判断）
│       │   ├── ZoneLegend.vue        #   空域图例（区域数量 + 阶段颜色）
│       │   └── TimelineSlider.vue    #   时间轴组件（时段切换 + 回放控制）
│       ├── views/
│       │   ├── Dashboard.vue         #   子系统 1：态势大屏
│       │   ├── PathPlanning.vue      #   子系统 2：智能路径规划（选点 + 巡逻双模式）
│       │   ├── routing/
│       │   │   └── EmergencyRouting.vue  # 子系统 2：应急航路规划
│       │   ├── safety-buffer/
│       │   │   └── SafetyBufferAnalysis.vue  # 子系统 3：安全缓冲区分析
│       │   └── density/
│       │       ├── DensityContour.vue    # 子系统 4：安全风险热力分析
│       │       ├── HotspotAnalysis.vue   # 子系统 4：低空拥堵识别
│       │       └── DensityStats.vue      # 子系统 4：区域密度统计（ECharts）
│       ├── stores/                   # Pinia 状态管理
│       │   ├── map.js                #   地图状态（实例、航线、标记、模式切换）
│       │   └── zones.js              #   空域状态（禁飞区/限高区 GeoJSON + 统计）
│       ├── data/
│       │   └── sampleRoutes.js       #   9 条广州模拟航线（Catmull-Rom 样条 + 高度剖面）
│       ├── utils/
│       │   ├── coordConvert.js       #   WGS-84 ↔ GCJ-02 坐标转换
│       │   └── patrolRouteGenerator.js  # 巡逻路线生成引擎（边界 + 犁地式）
│       └── router/
│           └── index.js              # 路由配置（8 条路由，懒加载）
│
├── backend/                          # Python FastAPI 后端（端口 8000）
│   ├── requirements.txt
│   ├── seed_routes.py                # 模拟航线生成（调用 A* 引擎）
│   ├── seed_data.py                  # 综合模拟数据生成（7 类实体 + 建表）
│   ├── alembic/                      # 数据库迁移
│   ├── alembic.ini
│   └── app/
│       ├── main.py                   # FastAPI 入口（CORS + 路由注册）
│       ├── config.py                 # 配置（pydantic-settings，读取 .env）
│       ├── database.py               # 数据库连接（SQLAlchemy + psycopg 3）
│       ├── api/                      # 路由模块（9 个，共 52 个端点）
│       │   ├── zones.py              #   空域查询（4 个端点）
│       │   ├── weather.py            #   气象服务（3 个端点）
│       │   ├── pathfinding.py        #   路径规划（1 个端点）
│       │   ├── routes.py             #   航线管理（3 个端点）
│       │   ├── airspace.py           #   空域 CRUD + 查询 + 合规（14 个端点）
│       │   ├── logistics.py          #   物流协同 + 调度（18 个端点）
│       │   ├── safety.py             #   安全监管（10 个端点）
│       │   ├── statistics.py         #   统计决策（7 个端点）
│       │   └── system_mgmt.py        #   系统管理（12 个端点）
│       ├── models/                   # SQLAlchemy 模型（7 个模块，16 张表）
│       │   ├── zones.py              #   no_fly_zones / height_limit_zones（PostGIS POLYGON）
│       │   ├── buildings.py          #   buildings（OSM 建筑 + 空间索引）
│       │   ├── routes.py             #   routes（LINESTRING + JSON 途经点）
│       │   ├── drones.py             #   drone_flights / weather_records
│       │   ├── logistics.py          #   enterprises / orders / tasks / stations / drone_resources
│       │   ├── safety.py             #   anomaly_events / safety_records
│       │   └── system.py             #   system_users / params / logs / gis_layers
│       ├── schemas/                  # Pydantic 数据校验
│       │   ├── zones.py
│       │   ├── routes.py             #   含 crs 字段标识
│       │   └── pathfinding.py
│       └── services/                 # 业务逻辑
│           ├── astar.py              #   Theta* 路径规划引擎（含高度剖面计算）
│           ├── zone_service.py       #   空域查询服务（PostGIS 空间查询）
│           └── weather_service.py    #   天气服务（高德 API + 30 分钟缓存）
│
└── data/                             # 原始数据
    ├── nofly_zones/                  # 禁飞区 Shapefile
    ├── height_limit_zones/           # 限高区 Shapefile
    └── guangzhou_buildings.json      # 广州 OSM 建筑缓存
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
│  │ GCJ-02 坐标      │  │ WGS-84 坐标                           │   │
│  └─────────────────┘  └──────────────────────────────────────┘   │
│              ↕ MapContainer 协调器 (统一 2D/3D 接口)               │
│              ↕ coordConvert.js (WGS-84 ↔ GCJ-02)                  │
│                                                                   │
│  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │态势大屏│ │智能航路规划│ │安全缓冲  │ │安全热力  │             │
│  │子系统1 │ │子系统2   │ │子系统3   │ │子系统4   │             │
│  └────────┘ └──────────┘ └──────────┘ └──────────┘             │
│                                                                   │
│  Vite 开发代理：/api → http://localhost:8000                      │
└──────────────────────────┬───────────────────────────────────────┘
                           │ RESTful API (:8000)
┌──────────────────────────▼───────────────────────────────────────┐
│                  后端 (Python FastAPI)                             │
│  Uvicorn · SQLAlchemy 2.0 · GeoAlchemy2 · Pydantic V2            │
│                                                                   │
│  核心 GIS 模块（4 个子系统对应）：                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ zones    │ │ weather  │ │ path-    │ │ routes   │           │
│  │ 空域查询  │ │ 天气服务  │ │ finding  │ │ 航线管理  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                   │
│  扩展后端模块（API 已就绪，前端页面规划中）：                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ airspace │ │ logistics│ │ safety   │ │ statistics│           │
│  │ 空域管理  │ │ 物流协同  │ │ 安全监管  │ │ 统计决策  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐                                                   │
│  │ system   │                                                   │
│  │ _mgmt    │                                                   │
│  │ 系统管理  │                                                   │
│  └──────────┘                                                   │
│                                                                   │
│  核心服务：                                                       │
│  · astar.py — Theta* 路径规划 + 高度剖面（限高区/建筑物优先）       │
│  · zone_service.py — 禁飞区/限高区空间查询                        │
│  · weather_service.py — 高德天气 API + 缓存                       │
└──────────────────────────┬───────────────────────────────────────┘
                           │ SQLAlchemy + GeoAlchemy2 + psycopg 3
┌──────────────────────────▼───────────────────────────────────────┐
│           数据库 (PostgreSQL 16 + PostGIS 3.4, Docker)            │
│  · 32 个禁飞区 · 8 个限高区（全部 max_altitude=120m）              │
│  · routes (LINESTRING, SRID 4326) · buildings (45,644 栋)         │
│  · enterprises · orders · tasks · stations · drone_resources     │
│  · anomaly_events · safety_records · weather_records             │
│  · system_users · system_params · operation_logs · gis_layers    │
└──────────────────────────────────────────────────────────────────┘
```

### 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3.5（组合式 API） | `<script setup>` 语法 |
| 构建工具 | Vite 5 | HMR 热更新 + API 代理 |
| UI 组件 | Element Plus 2.8 | Vue 3 生态 |
| 2D 地图 | 高德 JS API 2.0 | GCJ-02 坐标，浅色主题 |
| 3D 引擎 | CesiumJS 1.121 | WGS-84 坐标，全球地形 + 建筑白模 |
| 图表 | ECharts 6 | 统计可视化 |
| 坐标转换 | coordConvert.js | 克拉索夫斯基椭球算法 |
| 状态管理 | Pinia 2.2 | Vue 3 官方推荐 |
| 后端框架 | FastAPI | 异步 + 自动 Swagger 文档 |
| ORM | SQLAlchemy 2.0 + GeoAlchemy2 | PostGIS 空间查询 |
| 数据库驱动 | psycopg 3 | Windows 编码兼容 |
| 数据库 | PostgreSQL 16 + PostGIS 3.4 | Docker 部署 |

---

## API 接口

### 核心 GIS 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/zones/no-fly` | GET | 获取所有禁飞区（GeoJSON FeatureCollection） |
| `/api/zones/height-limit` | GET | 获取所有限高区（GeoJSON FeatureCollection） |
| `/api/zones/stats` | GET | 区域统计（禁飞区/限高区数量） |
| `/api/zones/check-point` | GET | 检查坐标是否在禁飞区/限高区内 |
| `/api/weather/live` | GET | 实时天气 |
| `/api/weather/flyable` | GET | 飞行适宜性判断 |
| `/api/pathfinding/plan` | POST | 路径规划（Theta* 算法） |
| `/api/routes/` | GET | 获取所有航线（含 `crs` 字段 + 高度剖面） |
| `/api/routes/{id}` | GET | 单条航线详情 |
| `/api/routes/` | POST | 创建新航线 |

### 路径规划请求示例

```json
POST /api/pathfinding/plan
{
  "start":      { "lng": 113.32, "lat": 23.12, "alt": 100 },
  "end":        { "lng": 113.264, "lat": 23.129, "alt": 100 },
  "waypoints":  [],
  "drone_speed":       15.0,
  "cruise_alt":        120,
  "safety_margin":     50.0,
  "avoid_no_fly":      true,
  "avoid_height_limit": true,
  "avoid_buildings":   true,
  "consider_weather":  true
}
```

### 路径规划响应示例

```json
{
  "path": [
    { "lng": 113.32, "lat": 23.12, "alt": 0.0, "phase": "ascent" },
    { "lng": 113.35, "lat": 23.10, "alt": 120.0, "phase": "height_limit" },
    { "lng": 113.264, "lat": 23.129, "alt": 30.0, "phase": "descent" }
  ],
  "total_distance": 7130.16,
  "estimated_time": 475.34,
  "warnings": [],
  "is_feasible": true,
  "altitude_profile": [
    { "alt": 0.0, "phase": "ascent" },
    { "alt": 120.0, "phase": "height_limit" },
    { "alt": 30.0, "phase": "descent" }
  ]
}
```

### 后端路由一览

**核心 GIS 模块（4 个子系统前端调用）：**

| 路由前缀 | 模块 | 端点数量 | 主要功能 |
|----------|------|----------|----------|
| `/api/zones` | 空域查询 | 4 | no-fly, height-limit, stats, check-point |
| `/api/weather` | 气象服务 | 3 | live, forecast, flyable |
| `/api/pathfinding` | 路径规划 | 1 | plan（Theta* 搜索 + 高度剖面） |
| `/api/routes` | 航线管理 | 3 | CRUD（含 `crs` 坐标系标识） |

**扩展模块（后端 API 已就绪，前端页面待开发）：**

| 路由前缀 | 模块 | 端点数量 | 主要功能 |
|----------|------|----------|----------|
| `/api/airspace` | 空域管理 | 14 | 禁飞区/限高区 CRUD + 空间查询 + 合规审查 |
| `/api/logistics` | 物流协同 | 18 | 企业/订单/任务/站点/无人机 CRUD + 调度 |
| `/api/safety` | 安全监管 | 10 | 冲突检测/拥堵/热力/事件/台账 |
| `/api/statistics` | 统计决策 | 7 | 城市/企业/服务/成本/站点分析 |
| `/api/system` | 系统管理 | 12 | 用户/参数/日志/GIS 图层/服务监控 |

> 完整交互文档（含请求/响应模型）：http://localhost:8000/docs

---

## 航线数据

系统内置 **9 条广州城区模拟航线**（`frontend/src/data/sampleRoutes.js`），覆盖天河、越秀、海珠、白云、黄埔、荔湾、番禺、南沙八大行政区：

| # | 名称 | 途经区域 |
|---|------|----------|
| 1 | 番禺→天河干线 | 番禺 → 海珠 → 天河（珠江新城） |
| 2 | 白云→天河横线 | 白云 → 越秀 → 天河 |
| 3 | 黄埔→白云线 | 黄埔 → 天河 → 白云 |
| 4 | 南沙→黄埔线 | 南沙 → 番禺 → 黄埔 |
| 5 | 荔湾→天河线 | 荔湾 → 越秀 → 天河 |
| 6 | 越秀纵向线 | 越秀核心区南北向 |
| 7 | 白云横向线 | 白云区东西向 |
| 8 | 天河→黄埔线 | 天河 → 黄埔 |
| 9 | 番禺→天河南线 | 番禺 → 海珠南 → 天河南 |

> 除内置航线外，系统支持通过「智能路径规划」页面实时生成自定义航线（选点规划 / 沿线飞行 / 空域巡回），并保存至态势大屏航线列表跨页面共享。

---

## 空域数据

系统内置珠江三角洲地区的空域约束数据：

| 数据类型 | 数量 | 来源 | 典型区域 |
|----------|------|------|----------|
| 禁飞区 | 32 个 | GeoJSON | 广州白云机场、深圳宝安机场、珠海机场、佛山沙堤机场、大亚湾核电站、岭澳核电站、石化区、军事区 |
| 限高区 | 8 个 | GeoJSON | 各机场及直升机场安全区，统一限高 120m |

---

## 开发说明

### 数据库端口说明

| 配置位置 | 端口 | 说明 |
|----------|------|------|
| `docker-compose.yml` | `5433:5432` | 容器端口映射 |
| `backend/app/config.py` | `5433` | 应用连接使用 |
| `backend/alembic.ini` | `5432` | Alembic 直接连容器内部（如需迁移请修正为 5433） |

> 使用 5433 端口避免与 Windows Hyper-V 保留端口冲突。

### 前端开发

- Vite 开发服务器将 `/api` 请求代理转发到 `http://localhost:8000`
- 天气数据仍使用内置 Mock（高德 API Key 未配置时降级使用）
- CesiumJS 采用懒加载策略：仅在切换 3D 模式时动态加载，减小首屏体积

### 坐标系统

- 数据库（PostGIS SRID 4326）= WGS-84
- 后端路径规划 = WGS-84
- 前端内部存储 = WGS-84
- 高德 2D 地图 = GCJ-02
- Cesium 3D = WGS-84
- 转换函数：`frontend/src/utils/coordConvert.js`（wgs2gcj / gcj2wgs）

### 高度剖面优先级

航线高度计算按以下优先级：
1. **限高区** — 压低至 `min(巡航高度, 限高区最大高度)`
2. **建筑物** — 爬升至 `max(巡航高度, 建筑高度 + 安全余量)`
3. **起飞段** — 从地面爬升至巡航高度（前 5-15% 路径）
4. **降落段** — 降至降落高度（后 5-15% 路径）
5. **巡航段** — 保持巡航高度

> 限高区和建筑物检查在起降段之上具有最高优先级，确保任意位置的航线高度都遵守空域约束。

---

## 常见问题

### 3D 模式只有蓝色地球
- 检查 `frontend/.env` 中 `VITE_CESIUM_ION_TOKEN` 是否有效
- 在 [Cesium ion](https://ion.cesium.com/signup) 免费注册获取 Token
- 确认网络能访问 `api.cesium.com`

### 限高区前置警告不弹窗
- 确认后端数据库已导入限高区数据（`height_limit_zones` 表应有 8 条记录）
- 确认 `GET /api/zones/stats` 返回 `height_limit_zones_count: 8`
- 确认起点/终点坐标确实在限高区内（使用 `GET /api/zones/check-point?lng=X&lat=Y` 验证）
- 确认巡航高度 > 限高区最大高度（默认 120m）

### 2D/3D 航线位置不一致
- 确认后端 `GET /api/routes/` 返回的航线包含 `"crs": "wgs84"` 字段
- 缺少 `crs` 字段会导致 2D 高德地图上偏移约 300-500m

### 数据库连接失败
- 确认 Docker Desktop 已运行，容器 `lowaltitude-postgis` 状态为 Up
- 检查端口 5433 未被其他程序占用
- `backend/app/config.py` 中 `DATABASE_URL` 的端口应为 `5433`

---

## 开源协议

MIT License
