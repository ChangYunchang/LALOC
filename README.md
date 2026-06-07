# 🚁 城市低空物流运营中心（LALOC）

> **Low-Altitude Logistics Operations Center** — 面向政府监管部门的城市低空物流运行态势管理平台

---

## 📖 项目简介

随着无人机物流行业的快速发展，城市低空空域的管理需求日益迫切。本系统为政府监管部门提供一套可视化的低空物流运营管理平台，实现对城市低空物流运行态势的实时监控、智能分析和科学决策支持。

### 核心定位

| 角色 | 说明 | 状态 |
|------|------|------|
| 🏛️ **管理方 Web 端** | 政府监管部门使用，监控全市低空物流态势 | ✅ 开发中 |
| 🏢 **运营方 Web 端** | 物流企业使用（美团、顺丰、淘宝闪送等） | 📋 规划中 |

---

## ✨ 已实现功能

### 🗺️ 城市三维场景

- **2D/3D 地图切换** — 一键切换平面地图与 3D 实景视角
- **360° 自由视角** — 鼠标右键拖拽旋转，滚轮缩放，自由观察
- **白模建筑渲染** — 高德地图 3D Buildings 图层，白色建筑模型
- **POI 地物信息** — 显示商场、学校、医院等地物名称
- **深色/浅色主题** — 浅色地图底图，白色基调 UI

### 🚫 空域管理

- **禁飞区可视化** — 红色虚线标注，点击查看禁飞原因
- **限高区可视化** — 橙色区域标注，点击查看限高数值
- **Shapefile 数据导入** — 支持 WGS84 坐标系的 .shp 文件自动入库
- **PostGIS 空间查询** — 基于 PostgreSQL + PostGIS 的地理数据管理

### 🌤️ 气象监测

- **实时天气** — 接入高德天气 API，展示温度、湿度、风向、风力
- **飞行适宜性判断** — 自动评估当前天气是否适合无人机飞行
- **预警提示** — 大风、暴雨、雾霾等恶劣天气预警

### 🛤️ 智能路径规划

- **地图交互选点** — 在地图上点击选择起点、终点、途经点
- **坐标输入** — 支持手动输入经纬度坐标
- **A\* 算法** — 自研路径规划算法，网格化搜索
- **约束避障** — 自动绕开禁飞区，考虑限高区约束
- **参数调节** — 可调无人机速度、安全距离等参数
- **路径可视化** — 蓝色路径线 + 方向箭头展示规划结果

### 📊 态势大屏

- **区域统计** — 禁飞区/限高区数量统计
- **航线列表** — 已有航线信息展示
- **时间轴回放** — 拖动时间轴查看不同时刻运行态势
- **天气面板** — 实时天气信息 + 飞行适宜性指示

---

## 🔮 待开发功能

### 📡 实时监控（规划中）

- [ ] 无人机实时位置追踪
- [ ] 飞行轨迹动态绘制
- [ ] 无人机状态面板（电量、速度、高度）
- [ ] 异常报警（闯入禁飞区、信号丢失）
- [ ] 多无人机同时监控

### 📈 数据分析（规划中）

- [ ] 物流量统计图表（日/周/月）
- [ ] 热力图展示高频飞行区域
- [ ] 航线拥堵度分析
- [ ] 历史数据回放与导出
- [ ] 运营报表自动生成

### 🏢 运营方 Web 端（规划中）

- [ ] 企业入驻与资质审核
- [ ] 航线申请与审批流程
- [ ] 无人机调度管理
- [ ] 配送任务管理
- [ ] 订单追踪与客户通知

### 🔔 预警与应急（规划中）

- [ ] 气象灾害预警联动
- [ ] 空域冲突检测
- [ ] 应急迫降点推荐
- [ ] 突发事件一键停飞
- [ ] 应急预案管理

### 🗂️ 系统管理（规划中）

- [ ] 用户权限管理（RBAC）
- [ ] 操作日志审计
- [ ] 系统配置管理
- [ ] 数据备份与恢复
- [ ] API 接口文档自动生成

### 🌐 第三方集成（规划中）

- [ ] UOM（无人机运营管理平台）对接
- [ ] 气象局专业气象数据接入
- [ ] ADS-B 无人机应答信号接入
- [ ] 电子围栏动态更新
- [ ] 地理编码与逆地理编码

---

## 🛠️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (Vue 3)                            │
│  Vite + Element Plus + AMap JS API 2.0 + Pinia              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │ 态势大屏    │ │ 路径规划    │ │ 数据分析    │  (规划中)     │
│  └────────────┘ └────────────┘ └────────────┘              │
└────────────────────────┬────────────────────────────────────┘
                         │ RESTful API
┌────────────────────────▼────────────────────────────────────┐
│                    后端 (Python)                              │
│  FastAPI + SQLAlchemy + GeoAlchemy2 + GeoPandas              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │ 空域管理    │ │ 路径规划    │ │ 气象服务    │              │
│  └────────────┘ └────────────┘ └────────────┘              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              数据库 (PostgreSQL + PostGIS)                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │ 禁飞区      │ │ 限高区      │ │ 航线/无人机  │              │
│  └────────────┘ └────────────┘ └────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

### 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 + Vite | 响应式框架，快速构建 |
| UI 组件 | Element Plus | Vue 3 生态最成熟的组件库 |
| 地图引擎 | AMap JS API 2.0 | 高德地图，支持 2D/3D |
| 状态管理 | Pinia | Vue 3 官方推荐 |
| 后端框架 | FastAPI | Python 高性能异步框架 |
| ORM | SQLAlchemy + GeoAlchemy2 | 支持 PostGIS 空间查询 |
| 数据库 | PostgreSQL 16 + PostGIS 3.4 | 专业地理数据库 |
| 容器化 | Docker Compose | 一键部署数据库 |
| 路径规划 | 自研 A\* 算法 | 网格化 + 空间约束 |

---

## 🚀 快速开始

### 环境要求

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — 运行数据库
- [Python 3.12+](https://www.python.org/) — 后端运行环境
- [Node.js 20+](https://nodejs.org/) — 前端构建工具
- 高德地图 API Key — [申请地址](https://lbs.amap.com/)

### 1. 克隆项目

```bash
git clone https://github.com/ChangYunchang/LALOC.git
cd LALOC
```

### 2. 启动数据库

```bash
docker compose up -d
```

> 首次运行需要下载 PostgreSQL + PostGIS 镜像，约 1-2 分钟

### 3. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 初始化数据库表
python -c "from app.database import engine, Base; from app.models import zones, routes, drones; Base.metadata.create_all(bind=engine)"

# 导入禁飞区/限高区数据
python -m app.utils.shp_loader

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端 API 文档: http://localhost:8000/docs

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

### 5. 配置 API Key

**前端** — 编辑 `frontend/.env`：

```env
VITE_AMAP_KEY=你的高德JS_API_Key
VITE_AMAP_SECURITY_CODE=你的安全密钥
```

**后端** — 编辑 `backend/.env`：

```env
DATABASE_URL=postgresql://admin:lowaltitude2024@localhost:5433/lowaltitude_logistics
AMAP_WEB_SERVICE_KEY=你的Web服务Key
```

> ⚠️ 数据库默认端口 5433，避免与本地 PostgreSQL 冲突

---

## 📁 项目结构

```
LALOC/
├── frontend/                    # 前端项目
│   ├── public/
│   ├── src/
│   │   ├── api/                 # API 请求封装
│   │   │   ├── request.js       # Axios 实例
│   │   │   ├── zones.js         # 禁飞区/限高区 API
│   │   │   ├── weather.js       # 天气 API
│   │   │   ├── pathfinding.js   # 路径规划 API
│   │   │   └── routes.js        # 航线 API
│   │   ├── components/          # 通用组件
│   │   │   ├── MapContainer.vue # 地图容器（2D/3D）
│   │   │   ├── WeatherPanel.vue # 天气面板
│   │   │   ├── ZoneLegend.vue   # 图例
│   │   │   └── TimelineSlider.vue # 时间轴
│   │   ├── views/               # 页面
│   │   │   ├── Dashboard.vue    # 态势大屏
│   │   │   └── PathPlanning.vue # 路径规划
│   │   ├── stores/              # Pinia 状态管理
│   │   ├── router/              # 路由配置
│   │   ├── App.vue
│   │   ├── main.js
│   │   └── style.css            # 全局样式
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── backend/                     # 后端项目
│   ├── app/
│   │   ├── api/                 # API 路由
│   │   │   ├── zones.py         # 禁飞区/限高区接口
│   │   │   ├── weather.py       # 天气查询接口
│   │   │   ├── pathfinding.py   # 路径规划接口
│   │   │   └── routes.py        # 航线管理接口
│   │   ├── models/              # 数据库模型
│   │   │   ├── zones.py         # 禁飞区/限高区模型
│   │   │   ├── routes.py        # 航线模型
│   │   │   └── drones.py        # 无人机/天气模型
│   │   ├── schemas/             # Pydantic 数据校验
│   │   ├── services/            # 业务逻辑
│   │   │   ├── astar.py         # A* 路径规划算法
│   │   │   ├── zone_service.py  # 区域查询服务
│   │   │   └── weather_service.py # 天气服务
│   │   ├── utils/
│   │   │   └── shp_loader.py    # Shapefile 导入工具
│   │   ├── config.py            # 配置文件
│   │   ├── database.py          # 数据库连接
│   │   └── main.py              # FastAPI 入口
│   ├── alembic/                 # 数据库迁移
│   └── requirements.txt
│
├── docker-compose.yml           # Docker 编排
├── .gitignore
└── README.md
```

---

## 📡 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/zones/no-fly` | GET | 获取所有禁飞区（GeoJSON） |
| `/api/zones/height-limit` | GET | 获取所有限高区（GeoJSON） |
| `/api/zones/stats` | GET | 获取区域统计信息 |
| `/api/zones/check-point` | GET | 检查点的约束信息 |
| `/api/weather/live` | GET | 获取实时天气 |
| `/api/weather/forecast` | GET | 获取天气预报 |
| `/api/weather/flyable` | GET | 检查飞行适宜性 |
| `/api/pathfinding/plan` | POST | 智能路径规划 |
| `/api/routes/` | GET | 获取所有航线 |
| `/api/routes/` | POST | 创建新航线 |

> 完整 API 文档访问: http://localhost:8000/docs

---

## 🗺️ 数据说明

### 禁飞区数据

- 格式：Shapefile (.shp)
- 坐标系：WGS84 (EPSG:4326)
- 存储位置：`D:\桌面\禁飞区\JinFeiQu.shp`
- 数据量：32 个多边形区域

### 限高区数据

- 格式：Shapefile (.shp)
- 坐标系：WGS84 (EPSG:4326)
- 存储位置：`D:\桌面\限高区\XianGaoQu.shp`
- 数据量：8 个多边形区域

### 数据导入

```bash
cd backend
python -m app.utils.shp_loader
```

---

## 🖥️ 界面说明

### 态势大屏

- **左侧**：天气面板、区域统计、航线列表
- **中央**：3D 地图（禁飞区/限高区/航线/无人机）
- **底部**：时间轴控制条
- **左上角**：2D/3D 切换按钮
- **右下角**：图例

### 路径规划

- **左侧**：起终点设置、参数调节、规划结果
- **中央**：3D 地图（禁飞区/限高区 + 规划路径）
- **左上角**：2D/3D 切换按钮
- **右下角**：图例

---

## 🤝 参与贡献

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
style:    代码格式（不影响逻辑）
refactor: 代码重构
test:     测试相关
chore:    构建/工具相关
```

---

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- [高德开放平台](https://lbs.amap.com/) — 地图与天气 API
- [PostGIS](https://postgis.net/) — 空间数据库扩展
- [FastAPI](https://fastapi.tiangolo.com/) — Python Web 框架
- [Vue.js](https://vuejs.org/) — 前端框架
- [Element Plus](https://element-plus.org/) — UI 组件库
