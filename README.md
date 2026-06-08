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

- **2D/3D 地图切换** — 一键切换平面地图与 3D 实景视角
- **360° 自由视角** — 鼠标中键拖拽旋转/俯仰，滚轮缩放
- **白模建筑渲染** — 高德地图 3D Buildings 图层，白色建筑模型
- **POI 地物信息** — 显示商场、学校、医院等地物名称
- **浅色主题** — 浅色地图底图（whitesmoke），白色基调 UI

### 空域管理

- **禁飞区可视化** — 红色虚线标注，点击查看禁飞原因
- **限高区可视化** — 橙色区域标注，点击查看限高数值
- **Shapefile 数据导入** — 支持 WGS84 坐标系的 .shp 文件自动入库
- **PostGIS 空间查询** — 基于 PostgreSQL + PostGIS 的地理数据管理

### 气象监测

- **实时天气** — 接入高德天气 API（前端直接调用），展示温度、湿度、风向、风力
- **飞行适宜性判断** — 自动评估当前天气是否适合无人机飞行
- **预警提示** — 大风、暴雨、雾霾等恶劣天气预警

### 智能路径规划

- **地图交互选点** — 在地图上点击选择起点、终点、途经点
- **坐标输入** — 支持手动输入经纬度坐标
- **A\* 算法** — 自研路径规划算法，网格化搜索
- **约束避障** — 自动绕开禁飞区，考虑限高区约束
- **参数调节** — 可调无人机速度、安全距离等参数
- **路径可视化** — 蓝色路径线 + 方向箭头展示规划结果

### 态势大屏

- **区域统计** — 禁飞区/限高区数量统计卡片
- **航线列表** — 显示所有航线名称、距离、预计时间、状态
- **航线高亮** — 点击航线列表，地图上琥珀色高亮该航线，其他航线降为半透明
- **无人机动画** — SVG 无人机图标沿航线循环飞行
- **视角跟踪** — 选中航线后，地图自动跟踪无人机位置移动
- **时间轴回放** — 选中航线后切换为回放模式，支持播放/暂停/0.5x~5x 倍速/拖拽跳转
- **天气面板** — 实时天气信息 + 飞行适宜性指示

### 模拟航线数据

已预置 4 条广州市模拟航线（通过 `backend/seed_routes.py` 生成）：

| 航线 | 距离 | 途经点 | 状态 |
|------|------|--------|------|
| 天河-海珠 急速配送线 | 7.0 km | 4 个 | 执行中 |
| 越秀-番禺 干线物流 | 15.9 km | 5 个 | 执行中 |
| 白云-黄埔 长距运输线 | 21.4 km | 6 个 | 待执行 |
| 珠江新城 环城巡检线 | 7.3 km | 8 个 | 执行中 |

---

## 待开发功能

### 实时监控（规划中）

- [ ] 无人机实时位置追踪
- [ ] 飞行轨迹动态绘制
- [ ] 无人机状态面板（电量、速度、高度）
- [ ] 异常报警（闯入禁飞区、信号丢失）
- [ ] 多无人机同时监控

### 数据分析（规划中）

- [ ] 物流量统计图表（日/周/月）
- [ ] 热力图展示高频飞行区域
- [ ] 航线拥堵度分析
- [ ] 历史数据回放与导出
- [ ] 运营报表自动生成

### 运营方 Web 端（规划中）

- [ ] 企业入驻与资质审核
- [ ] 航线申请与审批流程
- [ ] 无人机调度管理
- [ ] 配送任务管理
- [ ] 订单追踪与客户通知

### 预警与应急（规划中）

- [ ] 气象灾害预警联动
- [ ] 空域冲突检测
- [ ] 应急迫降点推荐
- [ ] 突发事件一键停飞
- [ ] 应急预案管理

### 系统管理（规划中）

- [ ] 用户权限管理（RBAC）
- [ ] 操作日志审计
- [ ] 系统配置管理
- [ ] 数据备份与恢复

### 第三方集成（规划中）

- [ ] UOM（无人机运营管理平台）对接
- [ ] 气象局专业气象数据接入
- [ ] ADS-B 无人机应答信号接入
- [ ] 电子围栏动态更新

---

## 技术架构

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
│  FastAPI + SQLAlchemy + GeoAlchemy2                          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │ 空域管理    │ │ 路径规划    │ │ 气象服务    │              │
│  └────────────┘ └────────────┘ └────────────┘              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              数据库 (PostgreSQL + PostGIS)                    │
│  Docker 容器，端口 5433                                       │
└─────────────────────────────────────────────────────────────┘
```

### 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 + Vite | 响应式框架，HMR 热更新 |
| UI 组件 | Element Plus | Vue 3 生态组件库 |
| 地图引擎 | AMap JS API 2.0 | 高德地图，2D/3D/Buildings |
| 状态管理 | Pinia | Vue 3 官方状态管理 |
| 后端框架 | FastAPI | Python 高性能异步框架 |
| ORM | SQLAlchemy + GeoAlchemy2 | 支持 PostGIS 空间查询 |
| 数据库 | PostgreSQL 16 + PostGIS 3.4 | 专业地理数据库 |
| 容器化 | Docker Compose | 一键部署数据库 |
| 路径规划 | 自研 A\* 算法 | 网格化 + 空间约束 |

---

## 每次开机启动流程

> 以下为 Windows 环境下的启动步骤，每次开机后按顺序执行。

### 前提条件

- Docker Desktop 已安装并运行
- Python 3.12+ 已安装
- Node.js 20+ 已安装
- 项目已克隆到本地

### 第一步：启动 Docker 数据库

打开 Docker Desktop，等待其完全启动（状态栏显示 Docker 图标为绿色），然后：

```bash
cd backend
docker compose up -d
```

验证数据库运行：

```bash
docker ps
# 应看到 lowaltitude-postgis 容器，状态为 Up，端口 5433->5432
```

### 第二步：启动后端

```bash
cd backend

# 激活虚拟环境
venv\Scripts\activate

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

看到以下输出表示启动成功：

```
城市低空物流运营中心 v1.0.0 starting...
API docs: http://localhost:8000/docs
INFO:     Uvicorn running on http://0.0.0.0:8000
```

验证后端运行：

```bash
curl http://localhost:8000/health
# 返回 {"status":"healthy"}
```

### 第三步：启动前端

**新开一个终端窗口**（保持后端终端不关闭）：

```bash
cd frontend

# 首次运行需安装依赖（之后可跳过）
npm install

# 启动前端开发服务器
npm run dev
```

看到以下输出表示启动成功：

```
VITE v5.x.x  ready in xxxx ms

➜  Local:   http://localhost:5173/
```

### 第四步：访问系统

在浏览器打开：**http://localhost:5173**

| 页面 | 地址 | 说明 |
|------|------|------|
| 态势大屏 | http://localhost:5173/ | 默认首页，航线监控 |
| 路径规划 | http://localhost:5173/path-planning | A\* 路径规划 |
| API 文档 | http://localhost:8000/docs | Swagger 交互文档 |

### 快速启动脚本（可选）

如果觉得每次手动启动麻烦，可以创建一个批处理文件 `start.bat` 放在项目根目录：

```bat
@echo off
echo [1/3] Starting Docker database...
cd backend
docker compose up -d

echo [2/3] Starting backend...
start "LALOC Backend" cmd /k "venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [3/3] Starting frontend...
cd ..\frontend
start "LALOC Frontend" cmd /k "npm run dev"

echo.
echo All services started!
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000/docs
echo.
pause
```

之后双击 `start.bat` 即可一键启动所有服务。

### 关闭服务

开发结束后，按以下顺序关闭：

1. **前端终端**：按 `Ctrl + C` 停止 Vite
2. **后端终端**：按 `Ctrl + C` 停止 Uvicorn
3. **数据库**（可选）：`docker compose down`（数据会保留）
   - 如需清除数据：`docker compose down -v`

---

## 项目结构

```
LALOC/
├── frontend/                        # 前端项目
│   ├── src/
│   │   ├── api/                     # API 请求封装（Axios）
│   │   │   ├── request.js           #   Axios 实例配置
│   │   │   ├── zones.js             #   禁飞区/限高区 API
│   │   │   ├── weather.js           #   天气 API
│   │   │   ├── pathfinding.js       #   路径规划 API
│   │   │   └── routes.js            #   航线 API
│   │   ├── components/              # 通用组件
│   │   │   ├── MapContainer.vue     #   地图容器（2D/3D、航线、无人机）
│   │   │   ├── WeatherPanel.vue     #   天气面板
│   │   │   ├── ZoneLegend.vue       #   图例
│   │   │   └── TimelineSlider.vue   #   时间轴（普通/回放模式）
│   │   ├── views/                   # 页面
│   │   │   ├── Dashboard.vue        #   态势大屏
│   │   │   └── PathPlanning.vue     #   路径规划
│   │   ├── stores/                  # Pinia 状态管理
│   │   │   ├── map.js               #   地图状态（实例、航线、选中状态）
│   │   │   └── zones.js             #   区域数据状态
│   │   ├── router/                  # Vue Router 路由
│   │   ├── App.vue                  # 应用壳（导航栏）
│   │   ├── main.js                  # 入口
│   │   └── style.css                # 全局样式
│   ├── .env                         # 环境变量（高德 Key）
│   ├── vite.config.js               # Vite 配置（代理）
│   └── package.json
│
├── backend/                         # 后端项目
│   ├── app/
│   │   ├── api/                     # FastAPI 路由
│   │   │   ├── zones.py             #   禁飞区/限高区接口
│   │   │   ├── weather.py           #   天气查询接口
│   │   │   ├── pathfinding.py       #   路径规划接口
│   │   │   └── routes.py            #   航线管理接口
│   │   ├── models/                  # SQLAlchemy 模型
│   │   │   ├── zones.py             #   禁飞区/限高区（PostGIS）
│   │   │   ├── routes.py            #   航线（LINESTRING）
│   │   │   └── drones.py            #   无人机飞行/天气记录
│   │   ├── schemas/                 # Pydantic 请求/响应模型
│   │   ├── services/                # 业务逻辑
│   │   │   ├── astar.py             #   A* 路径规划算法
│   │   │   ├── zone_service.py      #   区域查询服务
│   │   │   └── weather_service.py   #   天气服务
│   │   ├── utils/
│   │   │   └── shp_loader.py        #   Shapefile 导入工具
│   │   ├── config.py                # 配置（数据库、API Key）
│   │   ├── database.py              # 数据库连接（psycopg v3）
│   │   └── main.py                  # FastAPI 入口
│   ├── seed_routes.py               # 模拟航线种子数据脚本
│   ├── .env                         # 环境变量
│   └── requirements.txt
│
├── docker-compose.yml               # PostgreSQL + PostGIS 容器
├── start.bat                        # 一键启动脚本（可选）
├── .gitignore
└── README.md
```

---

## API 接口

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
| `/api/routes/{id}` | GET | 获取单条航线详情 |
| `/api/routes/` | POST | 创建新航线 |

> 完整 API 文档：http://localhost:8000/docs

---

## 数据说明

### 禁飞区 / 限高区

- 格式：Shapefile (.shp)
- 坐标系：WGS84 (EPSG:4326)
- 导入命令：`cd backend && python -m app.utils.shp_loader`

### 模拟航线

- 生成命令：`cd backend && python seed_routes.py`
- 会清除旧数据并重新插入 4 条航线

---

## 界面说明

### 态势大屏（/）

- **左侧**：天气面板、区域统计、航线列表（点击高亮）、选中航线详情
- **中央**：3D 地图（禁飞区/限高区/航线/无人机）
- **底部**：时间轴（无选中时为时间显示，选中航线后变为回放控制）
- **左上角**：2D/3D 切换按钮
- **右下角**：图例

### 路径规划（/path-planning）

- **左侧**：起终点设置、参数调节、规划结果
- **中央**：3D 地图（禁飞区/限高区 + 规划路径）
- **左上角**：2D/3D 切换按钮
- **右下角**：图例

---

## 常见问题

### Docker 启动失败

- 确保 Docker Desktop 已完全启动（系统托盘图标为绿色）
- 如果端口 5433 被占用：修改 `docker-compose.yml` 中的端口映射

### 后端连接数据库失败

- 检查 Docker 容器是否运行：`docker ps`
- 检查端口是否正确：默认 5433（不是 5432）
- 检查 `.env` 中的 `DATABASE_URL` 是否正确

### 前端页面空白

- 检查后端是否启动（前端通过 Vite proxy 转发 API 请求到后端）
- 检查 `frontend/.env` 中的高德 Key 是否正确

### 3D 地图卡顿

- 减少同时显示的航线数量
- 关闭浏览器其他标签页
- 降低浏览器窗口大小

### 中键旋转不生效

- 确保鼠标中键可以正常点击（部分鼠标需要安装驱动）
- 尝试刷新页面重新加载地图

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
style:    代码格式（不影响逻辑）
refactor: 代码重构
test:     测试相关
chore:    构建/工具相关
```

---

## 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

## 致谢

- [高德开放平台](https://lbs.amap.com/) — 地图与天气 API
- [PostGIS](https://postgis.net/) — 空间数据库扩展
- [FastAPI](https://fastapi.tiangolo.com/) — Python Web 框架
- [Vue.js](https://vuejs.org/) — 前端框架
- [Element Plus](https://element-plus.org/) — UI 组件库
