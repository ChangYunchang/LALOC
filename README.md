# 城市低空物流运营中心（LALOC）

> **L**ow-**A**ltitude **L**ogistics **O**perations **C**enter — 面向低空管理部门的城市低空物流 GIS 态势分析平台

---

## 项目简介

随着无人机物流行业快速发展，城市低空空域管理需求日益迫切。LALOC 面向低空管理部门和物流运营企业，以 **2D/3D GIS 地图**为核心载体，提供低空物流运行态势可视化监控、智能航路规划、林场/农田巡视巡逻、安全缓冲区分析及低空密度热力分析能力。

前端目前实现了 **4 个 GIS 核心子系统**：

| 编号 | 子系统 | 路由 | 核心能力 |
|------|--------|------|----------|
| 1 | 综合态势大屏 | `/dashboard` | 2D/3D 航线监控、无人机动画、时间轴回放 |
| 2 | 智能航路规划 | `/path-planning` `/emergency-routing` | 选点/巡逻路径规划 + 应急迫降 |
| 3 | 安全缓冲区分析 | `/safety-buffer/analysis` | 多航线仿真、实时碰撞检测与三级预警 |
| 4 | 安全热力分析 | `/density/contour` `/density/hotspot` `/density/stats` | 热力图、拥堵识别、密度统计 |

---

## 快速启动

### 前提条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- Python 3.12+
- Node.js 20+

### 1. 启动数据库

```bash
cd backend
docker compose up -d
```

> PostgreSQL 16 + PostGIS 3.4，端口 `5433`，数据库 `lowaltitude_logistics`，用户 `admin` / 密码 `lowaltitude2024`

### 2. 初始化数据

```bash
cd backend
venv\Scripts\activate          # Windows（macOS/Linux: source venv/bin/activate）
pip install -r requirements.txt

# 创建数据库表 + 生成模拟数据
python seed_data.py

# 导入禁飞区/限高区 GeoJSON
python -c "
import json, sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
for table, file in [('height_limit_zones', '../frontend/public/geo/height_limit_zones.geojson'),
                      ('no_fly_zones', '../frontend/public/geo/nofly_zones.geojson')]:
    with open(file, 'r', encoding='utf-8') as f: data = json.load(f)
    for feat in data['features']:
        coords = feat['geometry']['coordinates'][0]
        wkt = f\"POLYGON(({', '.join(f'{c[0]} {c[1]}' for c in coords)}))\"
        props = feat['properties']
        db.execute(text(f'INSERT INTO {table} (name, geometry, max_altitude, min_altitude, reason) VALUES (:name, ST_SetSRID(ST_GeomFromText(:wkt), 4326), :maxalt, :minalt, :reason)'),
            {'name': props.get('name',''), 'wkt': wkt, 'maxalt': props.get('max_altitude',120), 'minalt': props.get('min_altitude',0), 'reason': props.get('reason','')})
db.commit(); db.close()
print('Done')
"

# 生成模拟航线
python seed_routes.py
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动服务

```bash
# 后端（终端 1）
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端（终端 2）
cd frontend
npm run dev
```

> **Windows 一键启动**：双击项目根目录 `start.bat`

### 5. 访问地址

| 页面 | 地址 |
|------|------|
| 态势大屏（首页） | http://localhost:5173 |
| 智能路径规划 | http://localhost:5173/path-planning |
| 应急航路规划 | http://localhost:5173/emergency-routing |
| 安全缓冲区分析 | http://localhost:5173/safety-buffer/analysis |
| 安全风险热力分析 | http://localhost:5173/density/contour |
| 低空拥堵识别 | http://localhost:5173/density/hotspot |
| 区域密度统计 | http://localhost:5173/density/stats |
| 后端 API 文档 | http://localhost:8000/docs |

### 关闭

```bash
# 前端 / 后端：Ctrl + C
docker stop lowaltitude-postgis
```

---

## 地图引擎

系统采用**双地图引擎**，通过 `MapContainer` 协调器一键切换：

| 模式 | 引擎 | 坐标系 | 能力 |
|------|------|--------|------|
| 2D 平面 | 高德地图 JS API 2.0 | GCJ-02 | 轻量快速、热力图、绘图交互 |
| 3D 实景 | CesiumJS 1.121 | WGS-84 | 全球地形、OSM 建筑白模、AGL 高度 |

### 坐标系处理

系统内部统一使用 **WGS-84**（与 PostGIS SRID 4326 一致），UI 层自动转换：

| 数据来源 | 存储 | 2D 渲染 | 3D 渲染 |
|----------|------|---------|---------|
| 后端 API（`crs: "wgs84"`） | WGS-84 | WGS→GCJ 自动转换 | 原生 WGS-84 |
| 内置示例航线 | GCJ-02 | 直接使用 | GCJ→WGS 自动转换 |
| 路径规划结果 | WGS-84 | WGS→GCJ 自动转换 | 原生 WGS-84 |

转换模块：`frontend/src/utils/coordConvert.js`（`wgs2gcj` / `gcj2wgs`）

---

## 子系统一：综合态势大屏

> 路由 `/dashboard` — 默认首页

汇聚低空物流运行核心指标与空间分布，提供统一的运行态势视图。

### 功能

- **核心指标卡片** — 实时天气、禁飞区/限高区数量统计
- **航线列表** — 9 条内置 + 后端 API + 本地保存航线，支持名称/距离/时间筛选
- **2D/3D 一键切换** — 左上角切换高德平面地图与 Cesium 3D 地球
- **航线动画** — 无人机沿航线循环飞行，按飞行阶段分段着色
- **航线高亮** — 点击列表项高亮为琥珀色，其余降为半透明
- **时间轴回放** — 拖拽时间轴查看历史位置（0.5×/1×/2×/5× 速度）
- **3D 视角跟踪** — 回放时镜头自动锁定无人机跟随

### 飞行阶段着色

| 阶段 | 颜色 | 说明 |
|------|------|------|
| 起飞爬升段 | `#22c55e` 🟢 | 地面 → 巡航高度 |
| 巡航段 | `#3b82f6` 🔵 | 稳定巡航 |
| 降落下降段 | `#f59e0b` 🟠 | 巡航高度 → 地面 |
| 建筑避让段 | `#a855f7` 🟣 | 绕行高层建筑 |
| 禁飞区绕行段 | `#3b82f6` 🔵 | 沿禁飞区边缘绕行 |

---

## 子系统二：智能航路规划

### 2.1 智能路径规划

> 路由 `/path-planning`

支持**选点规划**和**林场/农田巡视巡逻**两大模式。

#### 模式一：选点规划

基于 A* 栅格搜索算法，综合禁飞区（含 150m 安全缓冲）、建筑群（高于 20m 视为障碍）、限高区等多重约束，生成安全飞行路径。

**算法管线：**

```
8 方向栅格 A* → 视线串拉（String Pulling）→ Chaikin 切角柔滑 → 弧长均匀重采样 → 高度剖面
```

**交互功能：**

- **地图点击选点** — 2D/3D 下直接点击地图设置起/终/途经点
- **坐标输入** — 手动输入 `lng,lat` 经纬度
- **途经点** — 多途经点逐段独立规划后拼接
- **限高区前置警告** — 规划前自动检测航点限高约束，巡航高度超限时弹窗提示
- **禁飞区拦截** — 选点落入禁飞区时自动拒绝
- **参数可调** — 巡航高度（50-250m）、速度（5-30 m/s）、避障开关
- **进度反馈** — 3D 模式实时显示规划进度
- **保存航线** — 规划结果可命名保存至态势大屏

#### 模式二：林场/农田巡视巡逻

面向农业植保、林业巡检场景：

| 子模式 | 算法 | 场景 |
|--------|------|------|
| **沿线飞行** | 沿绘制的折线生成航线 | 电力线巡检、河道巡查 |
| **边界巡逻** | 沿多边形边界密集采样 | 围栏巡检、边界巡查 |
| **犁地式覆盖** | Boustrophedon 蛇形条带扫描 | 全覆盖喷洒、地毯式搜索 |

### 2.2 应急航路规划

> 路由 `/emergency-routing`

无人机异常时自动搜索安全迫降点：

- 告警原因过滤（低电量/设备故障/通信中断）
- 飞行中无人机列表，一键触发应急
- 续航圈可视化 + 二次贝塞尔应急路径
- 电池三级评估

---

## 子系统三：安全缓冲区分析

> 路由 `/safety-buffer/analysis`

多条航线同时仿真，实时检测无人机间安全缓冲区碰撞：

- **安全范围** — 水平/垂直缓冲区 + 警戒距离可配置
- **多航线仿真** — 最多 8 架无人机同时飞行
- **三级预警** —

| 等级 | 条件 | 颜色 | 行为 |
|------|------|------|------|
| 正常 | 距离 > 警戒距离 | 🟢 绿色 | 全速飞行 |
| 警告 | 距离 < 警戒距离 | 🟡 黄色 | 减速至 50% |
| 冲突 | 距离 < 缓冲区 | 🔴 红色 | 停止/让行 |

- **2D/3D 统一** — 2D 半透明圆形缓冲，3D 圆柱体缓冲

---

## 子系统四：安全热力分析

| 页面 | 路由 | 说明 |
|------|------|------|
| 安全风险热力分析 | `/density/contour` | 低空密度热力图，五级渐变 |
| 低空拥堵识别 | `/density/hotspot` | 高/中/低三级拥堵热点 |
| 区域密度统计 | `/density/stats` | ECharts 柱状图 + 折线图 |

---

## 项目结构

```
LALOC/
├── README.md
├── Structure.md                         # 系统功能结构文档（9 个子系统完整定义）
├── start.bat                            # Windows 一键启动脚本
├── docker-compose.yml                   # PostgreSQL + PostGIS
│
├── frontend/                            # Vue 3 + Vite 5（端口 5173）
│   ├── vite.config.js                   # 配置（API 代理 + Cesium 静态资源 + Mock 路径规划）
│   ├── package.json
│   ├── public/geo/                      # GeoJSON 禁飞区/限高区
│   └── src/
│       ├── App.vue                      # 应用壳（导航 + 实时时钟）
│       ├── main.js                      # 入口（Pinia + Router）
│       ├── api/                         # Axios 封装
│       │   ├── request.js               #   实例 + 拦截器
│       │   ├── zones.js                 #   空域查询
│       │   ├── pathfinding.js           #   路径规划
│       │   ├── routes.js                #   航线 CRUD
│       │   └── weather.js               #   天气服务
│       ├── components/                  # 地图与通用组件
│       │   ├── MapContainer.vue         #   2D/3D 协调器
│       │   ├── Amap2DView.vue           #   高德 2D 地图
│       │   ├── Cesium3DView.vue         #   Cesium 3D 视图
│       │   ├── WeatherPanel.vue         #   天气面板
│       │   ├── ZoneLegend.vue           #   空域图例
│       │   └── TimelineSlider.vue       #   时间轴
│       ├── views/
│       │   ├── Dashboard.vue            #   子系统 1：态势大屏
│       │   ├── PathPlanning.vue         #   子系统 2：路径规划
│       │   ├── routing/
│       │   │   └── EmergencyRouting.vue #   子系统 2：应急航路
│       │   ├── safety-buffer/
│       │   │   └── SafetyBufferAnalysis.vue  # 子系统 3：安全缓冲
│       │   └── density/
│       │       ├── DensityContour.vue       # 子系统 4：热力分析
│       │       ├── HotspotAnalysis.vue      # 子系统 4：拥堵识别
│       │       └── DensityStats.vue         # 子系统 4：密度统计
│       ├── stores/                      # Pinia 状态
│       │   ├── map.js                   #   地图状态
│       │   └── zones.js                 #   空域状态
│       ├── data/sampleRoutes.js         #   9 条广州模拟航线
│       ├── utils/
│       │   ├── coordConvert.js          #   WGS-84 ↔ GCJ-02
│       │   └── patrolRouteGenerator.js  #   巡逻路线生成
│       └── router/index.js              #   路由（8 条路由，懒加载）
│
├── backend/                             # Python FastAPI（端口 8000）
│   ├── requirements.txt
│   ├── seed_data.py                     # 模拟数据生成（7 类实体 + 建表）
│   ├── seed_routes.py                   # 模拟航线生成
│   ├── alembic/                         # 数据库迁移
│   └── app/
│       ├── main.py                      # 入口（CORS + 9 组路由注册）
│       ├── config.py                    # 配置（pydantic-settings）
│       ├── database.py                  # 数据库连接
│       ├── api/                         # 10 个路由模块
│       │   ├── zones.py                 #   空域查询（4 端点）
│       │   ├── pathfinding.py           #   路径规划（1 端点）
│       │   ├── routes.py                #   航线管理（3 端点）
│       │   ├── weather.py               #   气象服务（3 端点）
│       │   ├── airspace.py              #   空域管理（14 端点）
│       │   ├── logistics.py             #   物流协同（18 端点）
│       │   ├── safety.py                #   安全监管（10 端点）
│       │   ├── statistics.py            #   统计决策（7 端点）
│       │   └── system_mgmt.py           #   系统管理（12 端点）
│       ├── models/                      # 7 个模型模块
│       ├── schemas/                     # Pydantic 校验
│       └── services/                    # 业务逻辑
│           ├── astar.py                 #   A* 路径规划引擎
│           ├── zone_service.py          #   空域空间查询
│           └── weather_service.py       #   天气缓存服务
│
├── data/                                # 原始数据
│   ├── nofly_zones/                     # 禁飞区 Shapefile
│   ├── height_limit_zones/              # 限高区 Shapefile
│   └── guangzhou_buildings.json         # 广州 OSM 建筑缓存
│
├── tools/                               # 开发工具
├── deliverables/                        # 交付文档与架构图
└── plans/                               # 规划文档
```

---

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端框架 | Vue 3（组合式 API） | 3.5 |
| 构建工具 | Vite | 5.4 |
| UI 组件库 | Element Plus | 2.8 |
| 2D 地图 | 高德 JS API | 2.0 |
| 3D 引擎 | CesiumJS | 1.121 |
| 图表 | ECharts | 6.1 |
| 状态管理 | Pinia | 2.2 |
| 坐标转换 | 克拉索夫斯基椭球算法 | — |
| 后端框架 | FastAPI | 0.115 |
| ORM | SQLAlchemy + GeoAlchemy2 | 2.0 |
| 数据库 | PostgreSQL + PostGIS | 16 + 3.4 |
| 数据库驱动 | psycopg 3 | 3.2 |
| 地理处理 | GeoPandas + Shapely | 1.1 |

---

## API 接口

### 前端调用的核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/zones/no-fly` | GET | 禁飞区 GeoJSON |
| `/api/zones/height-limit` | GET | 限高区 GeoJSON |
| `/api/zones/stats` | GET | 空域统计 |
| `/api/zones/check-point?lng=&lat=` | GET | 点位约束检查 |
| `/api/weather/live` | GET | 实时天气 |
| `/api/pathfinding/plan` | POST | 路径规划 |
| `/api/routes/` | GET | 航线列表（含 `crs` + 高度剖面） |
| `/api/routes/` | POST | 创建航线 |

### 路径规划 API

```json
POST /api/pathfinding/plan
{
  "start":      { "lng": 113.32, "lat": 23.12, "alt": 100 },
  "end":        { "lng": 113.26, "lat": 23.13, "alt": 100 },
  "waypoints":  [],
  "drone_speed": 15,
  "cruise_alt":  120,
  "avoid_no_fly":      true,
  "avoid_height_limit": true,
  "avoid_buildings":   true
}
```

```json
{
  "is_feasible": true,
  "total_distance": 7130,
  "estimated_time": 475,
  "path": [
    { "lng": 113.32, "lat": 23.12, "alt": 20,  "index": 0 },
    { "lng": 113.35, "lat": 23.10, "alt": 120, "index": 1 }
  ],
  "altitude_profile": [
    { "index": 0, "alt": 20,  "phase": "ascent" },
    { "index": 1, "alt": 120, "phase": "cruise"  }
  ],
  "warnings": ["已水平绕行禁飞区（保持安全缓冲距离）"]
}
```

---

## 内置航线

系统内置 9 条广州城区模拟航线（`frontend/src/data/sampleRoutes.js`）：

| # | 名称 | 途经区域 |
|---|------|----------|
| 1 | 番禺→天河干线 | 番禺 → 海珠 → 天河 |
| 2 | 白云→天河横线 | 白云 → 越秀 → 天河 |
| 3 | 黄埔→白云线 | 黄埔 → 天河 → 白云 |
| 4 | 南沙→黄埔线 | 南沙 → 番禺 → 黄埔 |
| 5 | 荔湾→天河线 | 荔湾 → 越秀 → 天河 |
| 6 | 越秀纵向线 | 越秀核心区南北向 |
| 7 | 白云横向线 | 白云区东西向 |
| 8 | 天河→黄埔线 | 天河 → 黄埔 |
| 9 | 番禺→天河南线 | 番禺 → 海珠南 → 天河 |

---

## 空域数据

内置珠江三角洲地区空域约束数据（`public/geo/`）：

| 类型 | 数量 | 典型区域 |
|------|------|----------|
| 禁飞区 | 32 个 | 白云机场、宝安机场、珠海机场、大亚湾核电站、石化区、军事区 |
| 限高区 | 8 个 | 各机场及直升机场安全区（限高 120m） |

---

## 开发说明

### 坐标系

- 数据库 PostGIS：SRID 4326（WGS-84）
- 后端/前端内部：WGS-84
- 高德 2D 地图：GCJ-02（渲染时自动 `wgs2gcj` 转换）
- Cesium 3D：WGS-84（禁飞区/限高区渲染时自动 `gcj2wgs` 转换）

### 前端开发

- Vite `/api` 请求代理到 `http://localhost:8000`
- 禁飞区/限高区接口已对接真实数据库，天气使用 Mock（高德 API Key 缺省时降级）
- CesiumJS 懒加载：仅在切换 3D 模式时动态加载

### 数据库端口

- 容器内部 `5432`，映射到宿主机 `5433`（避免 Windows Hyper-V 端口冲突）

---

## 开源协议

MIT License
