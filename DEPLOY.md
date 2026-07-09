# LALOC 快速部署文档

> 在新电脑上从零部署本项目。将此文档提供给 Claude，说一句 **"请根据DEPLOY.md完成部署"** 即可自动完成全部安装与启动。

---

## 部署环境要求

| 软件 | 最低版本 | 用途 |
|------|----------|------|
| Docker Desktop | 最新稳定版 | PostgreSQL + PostGIS 数据库 |
| Python | 3.12+ | FastAPI 后端服务 |
| Node.js | 20+ | Vue 3 + Vite 前端构建 |
| npm | 10+ | 前端包管理（随 Node.js 自带） |
| Git | 2.40+ | 版本管理（可选，用于克隆仓库） |

> **操作系统**：Windows / macOS / Linux 均可，本文以 Windows 为主要示例。

---

## 部署步骤

### 步骤 1：安装基础软件

根据操作系统安装以下软件：

**Windows：**
- [Docker Desktop](https://www.docker.com/products/docker-desktop) — 安装后启动，确保右下角图标显示 "Engine running"
- [Python 3.12+](https://www.python.org/downloads/) — 安装时勾选 "Add Python to PATH"
- [Node.js 20+](https://nodejs.org/) — 下载 LTS 版本安装

**验证安装：**
```bash
docker --version
python --version
node --version
npm --version
```

### 步骤 2：创建 Python 虚拟环境

```bash
cd backend
python -m venv venv
```

**激活虚拟环境：**
```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 步骤 3：安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 步骤 4：启动数据库

```bash
cd backend
docker compose up -d
```

> 启动后 PostgreSQL 16 + PostGIS 3.4 运行在端口 **5433**（容器内 5432 → 宿主机 5433）
>
> 数据库：`lowaltitude_logistics` | 用户：`admin` | 密码：`lowaltitude2024`

验证数据库：
```bash
docker ps --filter "name=lowaltitude-postgis"
```

### 步骤 5：初始化数据

```bash
cd backend

# 5a. 创建数据库表 + 生成模拟数据（7 类实体：无人机、配送站、物流订单等）
python seed_data.py

# 5b. 导入禁飞区 & 限高区 GeoJSON
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
print('GeoJSON import done')
"

# 5c. 生成模拟航线
python seed_routes.py
```

### 步骤 6：安装前端依赖

```bash
cd frontend
npm install
```

### 步骤 7：启动所有服务

**需要两个终端窗口：**

**终端 1 — 后端（端口 8000）：**
```bash
cd backend
# 激活虚拟环境（如未激活）
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**终端 2 — 前端（端口 5173）：**
```bash
cd frontend
npm run dev
```

> **Windows 用户可选**：项目根目录下有 `start.bat`，双击即可一键启动所有服务（前提是 venv 已创建、依赖已安装）。

---

## 访问地址

| 页面 | 地址 |
|------|------|
| 态势大屏（首页） | http://localhost:5173 |
| 智能路径规划 | http://localhost:5173/path-planning |
| 应急航路规划 | http://localhost:5173/emergency-routing |
| 安全缓冲区分析 | http://localhost:5173/safety-buffer/analysis |
| 安全风险热力分析 | http://localhost:5173/density/contour |
| 低空拥堵识别 | http://localhost:5173/density/hotspot |
| 区域密度统计 | http://localhost:5173/density/stats |
| 后端 API 文档 (Swagger) | http://localhost:8000/docs |
| 后端健康检查 | http://localhost:8000/health |

---

## 关闭服务

```bash
# 前端 / 后端：在各自终端窗口按 Ctrl + C
# 数据库：
cd backend
docker compose down
```

---

## 环境变量参考

项目的 `.env` 文件已预配置开发环境默认值，一般无需修改。

| 文件 | 变量 | 说明 | 默认值 |
|------|------|------|--------|
| `frontend/.env` | `VITE_AMAP_KEY` | 高德地图 API Key（2D 地图） | 已内置 |
| `frontend/.env` | `VITE_AMAP_SECURITY_CODE` | 高德安全密钥 | 已内置 |
| `frontend/.env` | `VITE_CESIUM_ION_TOKEN` | Cesium ion Token（3D 地形） | 已内置 |
| `backend/.env` | `DATABASE_URL` | PostgreSQL 连接串 | `postgresql://admin:lowaltitude2024@localhost:5433/lowaltitude_logistics` |
| `backend/.env` | `AMAP_WEB_SERVICE_KEY` | 高德 Web 服务 Key（天气 API） | 已内置 |

---

## 常见问题

### Q: Docker 启动失败？
确保 Docker Desktop 已启动并显示 "Engine running"。如果端口 5433 被占用，修改 `docker-compose.yml` 中的端口映射（如 `"5434:5432"`），同时更新 `backend/.env` 中的 `DATABASE_URL`。

### Q: `seed_data.py` 执行报错？
确认数据库已启动（`docker ps`），虚拟环境已激活，`requirements.txt` 中的依赖已安装。

### Q: 前端地图不显示？
检查 `frontend/.env` 中的 `VITE_AMAP_KEY` 和 `VITE_CESIUM_ION_TOKEN` 是否有效。

### Q: 后端接口返回 500 错误？
查看后端终端日志，常见原因：数据库未启动、数据未初始化、GeoJSON 未导入。

### Q: 路径规划功能在 2D/3D 下坐标偏移？
坐标转换逻辑已内置（GCJ-02 ↔ WGS-84），无需额外配置。若出现偏移，确认 `frontend/src/utils/coordConvert.js` 存在且未被修改。

---

## 技术栈速览

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端框架 | Vue 3（组合式 API） | 3.5 |
| 构建工具 | Vite | 5.4 |
| UI 组件库 | Element Plus | 2.8 |
| 2D 地图 | 高德 JS API（GCJ-02） | 2.0 |
| 3D 引擎 | CesiumJS（WGS-84） | 1.121 |
| 图表 | ECharts | 6.1 |
| 状态管理 | Pinia | 2.2 |
| 后端框架 | FastAPI | 0.115 |
| ORM | SQLAlchemy + GeoAlchemy2 | 2.0 |
| 数据库 | PostgreSQL + PostGIS | 16 + 3.4 |
