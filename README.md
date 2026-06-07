# 🚁 城市低空物流运营中心

城市低空物流运营管理系统，管理方 Web 端，用于政府监管低空物流运行态势。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + AMap JS API 2.0 |
| 后端 | Python FastAPI + SQLAlchemy + GeoAlchemy2 |
| 数据库 | PostgreSQL 16 + PostGIS 3.4 (Docker) |
| 路径规划 | 自研 A* 算法（考虑禁飞区/限高区/天气约束） |

## 功能

1. **城市三维场景构建** - 2D/3D 地图展示，禁飞区、限高区、航线、无人机轨迹可视化
2. **实时天气监控** - 接入高德天气 API，显示飞行适宜性
3. **时间轴回放** - 拖动时间轴查看不同时刻物流运行态势
4. **智能路径规划** - 考虑禁飞区、限高区、天气约束的 A* 路径规划

## 快速开始

### 前提条件

- 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- 安装 [Python 3.12+](https://www.python.org/)
- 安装 [Node.js 20+](https://nodejs.org/)
- 高德地图 API Key（[申请地址](https://lbs.amap.com/)）

### 1. 启动数据库

```bash
# 在项目根目录执行
docker compose up -d
```

等待 PostgreSQL + PostGIS 启动完成（首次需要下载镜像，约1-2分钟）。

### 2. 启动后端

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
# Windows 激活虚拟环境
venv\Scripts\activate
# Linux/Mac
# source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 初始化数据库表
python -c "from app.database import engine, Base; from app.models import zones, routes, drones; Base.metadata.create_all(bind=engine); print('数据库表创建成功')"

# 导入禁飞区和限高区数据
python -m app.utils.shp_loader

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端 API 文档: http://localhost:8000/docs

### 3. 启动前端

```bash
# 进入前端目录（新终端）
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端地址: http://localhost:5173

### 4. 配置 API Key

编辑 `frontend/.env`，填入你的高德地图 Key：

```
VITE_AMAP_KEY=你的JS_API_Key
VITE_AMAP_SECURITY_CODE=你的安全密钥
```

编辑 `backend/.env`，填入高德 Web 服务 Key：

```
AMAP_WEB_SERVICE_KEY=你的Web服务Key
```

## 项目结构

```
├── frontend/          # Vue 3 前端
│   ├── src/
│   │   ├── api/       # API 请求封装
│   │   ├── components/# 通用组件
│   │   ├── views/     # 页面视图
│   │   ├── stores/    # Pinia 状态管理
│   │   └── router/    # 路由配置
│   └── package.json
│
├── backend/           # Python 后端
│   ├── app/
│   │   ├── api/       # API 路由
│   │   ├── models/    # 数据库模型
│   │   ├── schemas/   # 数据校验
│   │   ├── services/  # 业务逻辑
│   │   └── utils/     # 工具函数
│   └── requirements.txt
│
└── docker-compose.yml # Docker 编排
```
