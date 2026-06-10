# 城市低空物流运营中心（LALOC）

> **Low-Altitude Logistics Operations Center** — 面向政府监管部门的城市低空物流运行态势管理平台

---

## 项目简介

随着无人机物流行业的快速发展，城市低空空域的管理需求日益迫切。本系统为政府监管部门提供一套可视化的低空物流运营管理平台，实现对城市低空物流运行态势的实时监控、智能分析和科学决策支持。

### 核心定位

| 角色 | 说明 | 状态 |
|------|------|------|
| 管理方 Web 端 | 政府监管部门使用，监控全市低空物流态势 | 开发中 |
| 运营方 Web 端 | 物流企业使用（美团、顺丰、淘宝闪送等） | 规划中 |

---

## 已实现功能

### 城市三维场景

- **2D/3D 地图切换** — 2D 使用高德地图，3D 使用 CesiumJS + OSM Buildings 白模
- **双引擎架构** — MapContainer 协调器自动切换，2D/3D 共享航线与区域数据
- **Cesium 3D 实景** — 全球地形 (Cesium World Terrain)、OSM 街道影像、OSM Buildings 建筑白模
- **建筑物交互** — 3D 模式下点击建筑白模可查看 OSM 属性（名称、高度、楼层）
- **360° 自由视角** — Cesium 原生相机控制（左键旋转、右键缩放、中键俯仰）
- **浅色主题** — 白色基调 UI，统一视觉风格

### 空域管理

- **禁飞区可视化** — 红色标注，2D/3D 统一渲染，点击查看禁飞原因
- **限高区可视化** — 橙色标注，点击查看限高数值
- **Shapefile 数据导入** — 支持 WGS84 坐标系的 .shp 文件自动入库
- **PostGIS 空间查询** — 基于 PostgreSQL + PostGIS 的地理数据管理

### 气象监测

- **实时天气** — 接入高德天气 API，展示温度、湿度、风向、风力
- **飞行适宜性判断** — 自动评估当前天气是否适合无人机飞行
- **天气缓存** — 30 分钟本地缓存，减少 API 调用

### 智能路径规划

- **地图交互选点** — 2D/3D 模式下点击地图选择起点、终点、途经点
- **坐标输入** — 支持手动输入经纬度坐标
- **A\* 算法** — 自研路径规划算法，50m 网格精度
- **多约束避障** — 自动绕开禁飞区，考虑限高区、建筑物高度约束
- **建筑感知** — 基于 OSM 45,000+ 栋广州建筑数据，计算建筑高度并自动爬升避让
- **途经点支持** — 支持多个途经点，地图点击或手动输入
- **参数可调** — 无人机速度可调，飞行时间实时更新
- **禁飞区拦截** — 选点时若落在禁飞区内则拒绝并提示
- **阶段可视化** — 航线按飞行阶段分色显示（爬升/巡航/下降/限高/建筑避让）

### 态势大屏

- **区域统计** — 禁飞区/限高区数量统计卡片
- **航线列表** — 显示所有航线名称、距离、预计时间、状态
- **航线高亮** — 点击航线列表，该航线高亮（琥珀色），其他航线降为半透明
- **无人机动画** — 2D/3D 模式下无人机沿航线循环飞行
- **时间轴回放** — 选中航线后切换为回放模式，支持拖拽跳转
- **3D 视角跟踪** — 3D 模式下拖动时间轴，镜头锁定无人机实时跟随
- **天气面板** — 实时天气信息 + 飞行适宜性指示

### 模拟航线数据

通过 `backend/seed_routes.py` 生成，使用 A\* 算法含建筑感知的高度剖面：

| 航线 | 距离 | 途经点 | 状态 |
|------|------|--------|------|
| 天河-海珠 急速配送线 | ~7.2 km | 4 个 | 执行中 |
| 越秀-番禺 干线物流 | ~17.1 km | 5 个 | 执行中 |
| 白云-黄埔 长距运输线 | ~23.3 km | 6 个 | 待执行 |
| 珠江新城 环城巡检线 | ~7.7 km | 8 个 | 执行中 |

---

## 技术架构

```
┌──────────────────────────────────────────────────────────────┐
│                      前端 (Vue 3)                             │
│  Vite + Element Plus + Pinia                                  │
│  ┌───────────────┐  ┌──────────────────────────────────┐     │
│  │ Amap2DView    │  │ Cesium3DView                      │     │
│  │ (高德 2D 地图) │  │ (CesiumJS + OSM Buildings 白模)   │     │
│  └───────────────┘  └──────────────────────────────────┘     │
│              ↕ MapContainer 协调器 (2D/3D 切换)               │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐               │
│  │ 态势大屏    │ │ 路径规划    │ │ 数据分析    │  (规划中)     │
│  └────────────┘ └────────────┘ └────────────┘               │
└────────────────────────┬─────────────────────────────────────┘
                         │ RESTful API (Vite Proxy)
┌────────────────────────▼─────────────────────────────────────┐
│                    后端 (Python)                               │
│  FastAPI + SQLAlchemy + GeoAlchemy2                           │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐               │
│  │ 空域管理    │ │ A* 路径规划 │ │ 气象服务    │               │
│  │ PostGIS 查询│ │ 建筑感知    │ │ 高德 API    │               │
│  └────────────┘ └────────────┘ └────────────┘               │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│            数据库 (PostgreSQL 16 + PostGIS 3.4)                │
│  Docker 容器                                                  │
│  ├─ no_fly_zones (禁飞区 POLYGON)                             │
│  ├─ height_limit_zones (限高区 POLYGON)                        │
│  ├─ routes (航线 LINESTRING)                                  │
│  ├─ buildings (OSM 建筑 POLYGON, 45,644 栋)                   │
│  └─ weather_records (天气缓存)                                │
└──────────────────────────────────────────────────────────────┘
```

### 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 + Vite | 响应式框架，HMR 热更新 |
| UI 组件 | Element Plus | Vue 3 生态组件库 |
| 2D 地图 | AMap JS API 2.0 | 高德地图，浅色主题 |
| 3D 引擎 | CesiumJS 1.121 | 3D 地球，地形，OSM Buildings |
| 建筑数据 | Cesium OSM Buildings | 免费 3D Tiles 白模图层 |
| 状态管理 | Pinia | Vue 3 官方状态管理 |
| 后端框架 | FastAPI | Python 高性能异步框架 |
| ORM | SQLAlchemy + GeoAlchemy2 | 支持 PostGIS 空间查询 |
| 数据库 | PostgreSQL 16 + PostGIS 3.4 | 专业地理数据库 |
| 容器化 | Docker | 一键部署数据库 |
| 路径规划 | 自研 A\* 算法 | 50m 网格 + 禁飞区/限高区/建筑约束 |

### 飞行阶段颜色

| 颜色 | 阶段 | 说明 |
|------|------|------|
| 🟢 `#22c55e` | 爬升段 (ascent) | 起飞后爬升至巡航高度 |
| 🔵 `#3b82f6` | 巡航段 (cruise) | 保持巡航高度飞行 |
| 🟠 `#f59e0b` | 下降段 (descent) | 降落前下降高度 |
| 🔴 `#ef4444` | 限高区飞行 (height_limit) | 在限高区内降低高度飞行 |
| 🟣 `#a855f7` | 建筑避让 (building) | 爬升越过高层建筑 |

---

## 快速启动

### 前提条件

- Docker Desktop 已安装并运行
- Python 3.12+ 已安装
- Node.js 20+ 已安装
- 注册 [Cesium ion](https://ion.cesium.com/signup) 获取免费 Access Token

### 第一步：配置环境变量

**`frontend/.env`**（已配置高德 Key，需填入 Cesium ion Token）：
```
VITE_AMAP_KEY=your_amap_key
VITE_AMAP_SECURITY_CODE=your_amap_security_code
VITE_CESIUM_ION_TOKEN=your_cesium_ion_token
```

**`backend/.env`**（数据库端口如冲突可改为 15433 等）：
```
DATABASE_URL=postgresql://admin:lowaltitude2024@localhost:15433/lowaltitude_logistics
```

### 第二步：启动数据库

```bash
docker run -d --name lowaltitude-postgis \
  -e POSTGRES_DB=lowaltitude_logistics \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=lowaltitude2024 \
  -e POSTGRES_HOST_AUTH_METHOD=trust \
  -p 15433:5432 \
  postgis/postgis:16-3.4
```

> 注：端口 5433 在部分 Windows 系统上被 Hyper-V 保留，故改用 15433。

### 第三步：初始化数据

```bash
cd backend
venv\Scripts\activate

# 导入禁飞区和限高区
python -m app.utils.shp_loader

# 生成模拟航线
python seed_routes.py

# (可选) 导入广州建筑数据（约 2 分钟）
python -m app.utils.osm_loader
```

### 第四步：启动后端

```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 第五步：启动前端

```bash
cd frontend
npm install  # 首次运行
npm run dev
```

### 第六步：访问系统

| 页面 | 地址 | 说明 |
|------|------|------|
| 态势大屏 | http://localhost:5173/ | 默认首页，航线监控 |
| 路径规划 | http://localhost:5173/path-planning | A\* 路径规划 |
| API 文档 | http://localhost:8001/docs | Swagger 交互文档 |

### 关闭服务

1. 前端：`Ctrl + C`
2. 后端：`Ctrl + C`
3. 数据库：`docker stop lowaltitude-postgis`（数据保留）

---

## 项目结构

```
LALOC/
├── frontend/                          # 前端项目 (Vue 3)
│   ├── src/
│   │   ├── api/                       # Axios API 封装
│   │   │   ├── request.js
│   │   │   ├── zones.js
│   │   │   ├── weather.js
│   │   │   ├── pathfinding.js
│   │   │   └── routes.js
│   │   ├── components/                # 通用组件
│   │   │   ├── MapContainer.vue       #   2D/3D 协调器
│   │   │   ├── Amap2DView.vue         #   高德 2D 地图视图
│   │   │   ├── Cesium3DView.vue       #   Cesium 3D 视图
│   │   │   ├── WeatherPanel.vue       #   天气面板
│   │   │   ├── ZoneLegend.vue         #   图例（区域 + 飞行阶段）
│   │   │   └── TimelineSlider.vue     #   时间轴 / 回放控制
│   │   ├── views/                     # 页面
│   │   │   ├── Dashboard.vue          #   态势大屏
│   │   │   └── PathPlanning.vue       #   路径规划
│   │   ├── stores/                    # Pinia 状态管理
│   │   │   ├── map.js
│   │   │   └── zones.js
│   │   ├── router/index.js            # Vue Router
│   │   ├── App.vue                    # 应用壳
│   │   ├── main.js                    # 入口
│   │   └── style.css                  # 全局样式
│   ├── public/cesium/                 # Cesium 静态资源
│   ├── .env                           # 高德 Key + Cesium Token
│   ├── vite.config.js                 # Vite 配置（代理 + Cesium serve）
│   └── package.json
│
├── backend/                           # 后端项目 (FastAPI)
│   ├── app/
│   │   ├── api/                       # API 路由
│   │   │   ├── zones.py               #   禁飞区/限高区 CRUD
│   │   │   ├── weather.py             #   天气查询
│   │   │   ├── pathfinding.py         #   路径规划
│   │   │   └── routes.py              #   航线管理
│   │   ├── models/                    # SQLAlchemy 模型
│   │   │   ├── zones.py               #   NoFlyZone, HeightLimitZone
│   │   │   ├── routes.py              #   Route (LINESTRING)
│   │   │   ├── buildings.py           #   Building (OSM 数据)
│   │   │   └── drones.py              #   WeatherRecord
│   │   ├── schemas/                   # Pydantic 请求/响应模型
│   │   │   └── pathfinding.py
│   │   ├── services/                  # 业务逻辑
│   │   │   ├── astar.py               #   A* 算法（建筑感知）
│   │   │   ├── zone_service.py        #   区域查询
│   │   │   └── weather_service.py     #   天气服务
│   │   ├── utils/
│   │   │   ├── shp_loader.py          #   Shapefile 导入
│   │   │   └── osm_loader.py          #   OSM 建筑数据导入
│   │   ├── config.py                  # 配置
│   │   ├── database.py                # 数据库连接
│   │   └── main.py                    # FastAPI 入口
│   ├── seed_routes.py                 # 模拟航线生成
│   ├── .env                           # 数据库 + 高德 Key
│   └── requirements.txt
│
├── data/                              # 数据文件
│   ├── nofly_zones/                   # 禁飞区 Shapefile
│   ├── height_limit_zones/            # 限高区 Shapefile
│   └── guangzhou_buildings.json       # OSM 建筑缓存
│
├── docker-compose.yml                 # PostgreSQL + PostGIS
└── README.md
```

---

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/zones/no-fly` | GET | 获取所有禁飞区（GeoJSON） |
| `/api/zones/height-limit` | GET | 获取所有限高区（GeoJSON） |
| `/api/zones/stats` | GET | 获取区域统计信息 |
| `/api/zones/check-point` | GET | 检查点是否在禁飞区/限高区内 |
| `/api/weather/live` | GET | 获取实时天气 |
| `/api/weather/forecast` | GET | 获取天气预报 |
| `/api/weather/flyable` | GET | 检查飞行适宜性 |
| `/api/pathfinding/plan` | POST | 智能路径规划（含建筑避障） |
| `/api/routes/` | GET | 获取所有航线（含高度剖面） |
| `/api/routes/{id}` | GET | 获取单条航线详情 |
| `/api/routes/` | POST | 创建新航线 |

> 完整 API 文档：http://localhost:8001/docs

### 路径规划请求示例

```json
POST /api/pathfinding/plan
{
  "start": { "lng": 113.32, "lat": 23.12, "alt": 100 },
  "end": { "lng": 113.264, "lat": 23.129, "alt": 100 },
  "waypoints": [{ "lng": 113.30, "lat": 23.11, "alt": 100 }],
  "drone_speed": 15.0,
  "avoid_buildings": true,
  "avoid_no_fly": true,
  "avoid_height_limit": true,
  "consider_weather": false
}
```

---

## 常见问题

### Docker 端口被占用

Windows 上端口 5433 可能被 Hyper-V 保留，改用 15433：
```bash
docker run -d --name lowaltitude-postgis ... -p 15433:5432 ...
```
同时更新 `backend/.env` 中的 `DATABASE_URL` 端口号。

### 3D 模式只有蓝色地球

- 检查 `frontend/.env` 中 `VITE_CESIUM_ION_TOKEN` 是否正确
- 刷新页面后点击「3D 实景」按钮
- 如 ion token 无效：OSM 影像仍可加载，但地形和建筑物白模不可用

### 3D 模式建筑白模不显示

- 需要有效的 Cesium ion Token
- 检查 F12 控制台是否有 CORS 或网络错误
- 建筑数据加载需要 ~5-10 秒

### 航线不显示建筑避让阶段

- 确认已运行 `python -m app.utils.osm_loader` 导入建筑数据
- 确认 `buildings` 表中有数据（`SELECT COUNT(*) FROM buildings`）

### 路径规划穿模

- 确保 buildings 表已导入数据（45,644 条广州建筑记录）
- 建筑采样为全路径点采样，确保每个路径点的高度计算都考虑了建筑

### 地图空白

- 检查后端是否启动：`curl http://localhost:8001/health`
- 检查 Vite 代理配置：`frontend/vite.config.js` 中 proxy target 端口
- 检查高德 Key 是否有效

---

## 参与贡献

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'feat: add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

### Commit 规范

```
feat:     新功能
fix:      修复 Bug
docs:     文档更新
style:    代码格式
refactor: 代码重构
test:     测试相关
chore:    构建/工具相关
```

---

## 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

## 致谢

- [CesiumJS](https://cesium.com/) — 3D 地球引擎
- [Cesium OSM Buildings](https://cesium.com/platform/cesium-ion/content/cesium-osm-buildings/) — 全球建筑白模
- [OpenStreetMap](https://www.openstreetmap.org/) — 建筑与地图数据
- [高德开放平台](https://lbs.amap.com/) — 2D 地图与天气 API
- [PostGIS](https://postgis.net/) — 空间数据库扩展
- [FastAPI](https://fastapi.tiangolo.com/) — Python Web 框架
- [Vue.js](https://vuejs.org/) — 前端框架
- [Element Plus](https://element-plus.org/) — UI 组件库
