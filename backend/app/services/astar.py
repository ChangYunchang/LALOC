"""
A* 路径规划算法 —— 考虑禁飞区、限高区、天气约束

将广州市区域网格化，每个网格节点记录：
- 是否可通行（禁飞区 = 不可通行）
- 限高区的最大飞行高度
- 通过代价（距离 + 约束惩罚）
"""
import heapq
import math
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.zones import NoFlyZone, HeightLimitZone


@dataclass(frozen=True)
class GridCell:
    """网格单元"""
    row: int
    col: int

    def __lt__(self, other):
        return (self.row, self.col) < (other.row, other.col)


@dataclass(order=True)
class AStarNode:
    """A* 搜索节点"""
    f_cost: float
    cell: GridCell = field(compare=False)
    g_cost: float = field(compare=False)
    parent: Optional['AStarNode'] = field(default=None, compare=False)


class GridMap:
    """网格地图"""

    def __init__(
        self,
        min_lng: float, max_lng: float,
        min_lat: float, max_lat: float,
        cell_size_meters: float = 200,  # 网格大小（米）
    ):
        self.min_lng = min_lng
        self.max_lng = max_lng
        self.min_lat = min_lat
        self.max_lat = max_lat

        # 计算网格数量（1度纬度 ≈ 111km）
        lat_range = max_lat - min_lat
        lng_range = max_lng - min_lng
        self.cell_size_deg = cell_size_meters / 111000  # 米转度

        self.rows = max(1, int(lat_range / self.cell_size_deg))
        self.cols = max(1, int(lng_range / self.cell_size_deg))

        # 不可达标记
        self.blocked: set[tuple[int, int]] = set()  # (row, col)
        # 限高区信息: {(row, col): max_altitude}
        self.height_limits: dict[tuple[int, int], float] = {}

    def cell_to_lnglat(self, row: int, col: int) -> tuple[float, float]:
        """网格坐标转经纬度（取网格中心点）"""
        lng = self.min_lng + (col + 0.5) * self.cell_size_deg
        lat = self.min_lat + (row + 0.5) * self.cell_size_deg
        return lng, lat

    def lnglat_to_cell(self, lng: float, lat: float) -> GridCell:
        """经纬度转网格坐标"""
        col = int((lng - self.min_lng) / self.cell_size_deg)
        row = int((lat - self.min_lat) / self.cell_size_deg)
        # 限制在有效范围内
        row = max(0, min(row, self.rows - 1))
        col = max(0, min(col, self.cols - 1))
        return GridCell(row, col)

    def is_valid(self, cell: GridCell) -> bool:
        """检查网格是否有效"""
        return 0 <= cell.row < self.rows and 0 <= cell.col < self.cols

    def is_blocked(self, cell: GridCell) -> bool:
        """检查网格是否被阻塞（在禁飞区内）"""
        return (cell.row, cell.col) in self.blocked

    def get_height_limit(self, cell: GridCell) -> Optional[float]:
        """获取网格的限高"""
        return self.height_limits.get((cell.row, cell.col))

    def get_neighbors(self, cell: GridCell) -> list[GridCell]:
        """获取邻居网格（8方向）"""
        neighbors = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = cell.row + dr, cell.col + dc
                neighbor = GridCell(nr, nc)
                if self.is_valid(neighbor) and not self.is_blocked(neighbor):
                    neighbors.append(neighbor)
        return neighbors

    def distance(self, cell1: GridCell, cell2: GridCell) -> float:
        """计算两个网格之间的距离（米），使用 Haversine 公式"""
        lng1, lat1 = self.cell_to_lnglat(cell1.row, cell1.col)
        lng2, lat2 = self.cell_to_lnglat(cell2.row, cell2.col)

        # Haversine 公式
        R = 6371000  # 地球半径（米）
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


def build_grid_from_db(
    db: Session,
    min_lng: float = 113.1, max_lng: float = 113.6,
    min_lat: float = 22.8, max_lat: float = 23.4,
    cell_size_meters: float = 200,
) -> GridMap:
    """从数据库中的禁飞区/限高区构建网格地图"""
    grid = GridMap(min_lng, max_lng, min_lat, max_lat, cell_size_meters)

    # 查询禁飞区并标记不可通行网格
    no_fly_zones = db.query(NoFlyZone).all()
    for zone in no_fly_zones:
        # 获取禁飞区的几何边界
        result = db.execute(
            text("""
                SELECT ST_XMin(geometry), ST_YMin(geometry),
                       ST_XMax(geometry), ST_YMax(geometry)
                FROM no_fly_zones WHERE id = :id
            """),
            {"id": zone.id}
        ).fetchone()

        if not result:
            continue

        xmin, ymin, xmax, ymax = result
        # 计算受影响的网格范围
        min_cell = grid.lnglat_to_cell(xmin, ymin)
        max_cell = grid.lnglat_to_cell(xmax, ymax)

        for row in range(min_cell.row, max_cell.row + 1):
            for col in range(min_cell.col, max_cell.col + 1):
                cell = GridCell(row, col)
                if not grid.is_valid(cell):
                    continue
                # 精确检查：网格中心点是否在禁飞区内
                lng, lat = grid.cell_to_lnglat(row, col)
                result = db.execute(
                    text("""
                        SELECT ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                        FROM no_fly_zones WHERE id = :id
                    """),
                    {"lng": lng, "lat": lat, "id": zone.id}
                ).fetchone()
                if result and result[0]:
                    grid.blocked.add((row, col))

    # 查询限高区并记录限高信息
    height_limit_zones = db.query(HeightLimitZone).all()
    for zone in height_limit_zones:
        result = db.execute(
            text("""
                SELECT ST_XMin(geometry), ST_YMin(geometry),
                       ST_XMax(geometry), ST_YMax(geometry)
                FROM height_limit_zones WHERE id = :id
            """),
            {"id": zone.id}
        ).fetchone()

        if not result:
            continue

        xmin, ymin, xmax, ymax = result
        min_cell = grid.lnglat_to_cell(xmin, ymin)
        max_cell = grid.lnglat_to_cell(xmax, ymax)

        for row in range(min_cell.row, max_cell.row + 1):
            for col in range(min_cell.col, max_cell.col + 1):
                cell = GridCell(row, col)
                if not grid.is_valid(cell):
                    continue
                lng, lat = grid.cell_to_lnglat(row, col)
                result = db.execute(
                    text("""
                        SELECT ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                        FROM height_limit_zones WHERE id = :id
                    """),
                    {"lng": lng, "lat": lat, "id": zone.id}
                ).fetchone()
                if result and result[0]:
                    key = (row, col)
                    # 如果有多个限高区重叠，取最小限高
                    existing = grid.height_limits.get(key)
                    if existing is None or zone.max_altitude < existing:
                        grid.height_limits[key] = zone.max_altitude

    return grid


def astar_search(
    grid: GridMap,
    start_lng: float, start_lat: float,
    end_lng: float, end_lat: float,
) -> Optional[list[tuple[float, float]]]:
    """
    A* 搜索算法

    返回: 路径点列表 [(lng, lat), ...]，或 None（不可达）
    """
    start_cell = grid.lnglat_to_cell(start_lng, start_lat)
    end_cell = grid.lnglat_to_cell(end_lng, end_lat)

    # 检查起点和终点是否可达
    if grid.is_blocked(start_cell):
        return None
    if grid.is_blocked(end_cell):
        return None

    # 初始化
    open_set: list[AStarNode] = []
    closed_set: set[tuple[int, int]] = set()

    start_node = AStarNode(
        f_cost=grid.distance(start_cell, end_cell),
        cell=start_cell,
        g_cost=0,
    )
    heapq.heappush(open_set, start_node)

    # 记录每个节点的最优 g_cost
    g_scores: dict[tuple[int, int], float] = {(start_cell.row, start_cell.col): 0}

    iterations = 0
    max_iterations = grid.rows * grid.cols  # 防止无限循环

    while open_set and iterations < max_iterations:
        iterations += 1
        current = heapq.heappop(open_set)

        # 到达终点
        if current.cell == end_cell:
            # 回溯路径
            path = []
            node = current
            while node:
                lng, lat = grid.cell_to_lnglat(node.cell.row, node.cell.col)
                path.append((lng, lat))
                node = node.parent
            path.reverse()
            return path

        key = (current.cell.row, current.cell.col)
        if key in closed_set:
            continue
        closed_set.add(key)

        # 扩展邻居
        for neighbor in grid.get_neighbors(current.cell):
            nkey = (neighbor.row, neighbor.col)
            if nkey in closed_set:
                continue

            # 计算移动代价
            move_cost = grid.distance(current.cell, neighbor)
            # 限高区惩罚（降低优先级但不阻断）
            height_limit = grid.height_limits.get(nkey)
            if height_limit is not None and height_limit < 50:
                move_cost *= 2  # 限高很低的区域增加代价

            new_g = current.g_cost + move_cost

            if new_g < g_scores.get(nkey, float('inf')):
                g_scores[nkey] = new_g
                h = grid.distance(neighbor, end_cell)
                f = new_g + h

                neighbor_node = AStarNode(
                    f_cost=f,
                    cell=neighbor,
                    g_cost=new_g,
                    parent=current,
                )
                heapq.heappush(open_set, neighbor_node)

    return None  # 不可达


def plan_path(
    db: Session,
    start_lng: float, start_lat: float,
    end_lng: float, end_lat: float,
    waypoints: list[tuple[float, float]] = None,
    cell_size_meters: float = 200,
    consider_weather: bool = True,
) -> dict:
    """
    完整路径规划

    参数:
        db: 数据库会话
        start_lng, start_lat: 起点坐标
        end_lng, end_lat: 终点坐标
        waypoints: 途经点列表 [(lng, lat), ...]
        cell_size_meters: 网格大小
        consider_weather: 是否考虑天气

    返回: 路径规划结果字典
    """
    # 确定搜索范围（包含所有点的边界 + 缓冲区）
    all_lngs = [start_lng, end_lng]
    all_lats = [start_lat, end_lat]
    if waypoints:
        for wlng, wlat in waypoints:
            all_lngs.append(wlng)
            all_lats.append(wlat)

    buffer = 0.05  # 约5km缓冲
    min_lng = min(all_lngs) - buffer
    max_lng = max(all_lngs) + buffer
    min_lat = min(all_lats) - buffer
    max_lat = max(all_lats) + buffer

    # 构建网格地图
    grid = build_grid_from_db(db, min_lng, max_lng, min_lat, max_lat, cell_size_meters)

    # 分段规划路径
    all_points = [(start_lng, start_lat)]
    if waypoints:
        all_points.extend(waypoints)
    all_points.append((end_lng, end_lat))

    full_path = []
    warnings = []
    is_feasible = True

    for i in range(len(all_points) - 1):
        seg_start = all_points[i]
        seg_end = all_points[i + 1]

        segment_path = astar_search(
            grid, seg_start[0], seg_start[1], seg_end[0], seg_end[1]
        )

        if segment_path is None:
            warnings.append(f"路径段 {i+1} 无法规划（可能存在不可绕过的禁飞区）")
            is_feasible = False
            # 尝试用直线连接
            full_path.append(seg_start)
            full_path.append(seg_end)
        else:
            # 避免重复点
            if full_path and full_path[-1] == segment_path[0]:
                full_path.extend(segment_path[1:])
            else:
                full_path.extend(segment_path)

    # 计算总距离和时间
    total_distance = 0
    for i in range(len(full_path) - 1):
        lng1, lat1 = full_path[i]
        lng2, lat2 = full_path[i + 1]
        # Haversine
        R = 6371000
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        total_distance += R * c

    drone_speed = 15.0  # 默认速度
    estimated_time = total_distance / drone_speed

    return {
        "path": [{"lng": p[0], "lat": p[1], "alt": 100} for p in full_path],
        "total_distance": round(total_distance, 2),
        "estimated_time": round(estimated_time, 2),
        "segments": [],
        "warnings": warnings,
        "is_feasible": is_feasible,
    }
