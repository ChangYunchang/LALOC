"""
A* 路径规划算法 —— 考虑禁飞区、限高区、建筑物、天气约束

将广州市区域网格化，每个网格节点记录：
- 是否可通行（禁飞区/建筑 = 不可通行）
- 限高区的最大飞行高度
- 建筑物的高度（需爬升越过）
- 通过代价（距离 + 约束惩罚）
"""
import heapq
import math
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.zones import NoFlyZone, HeightLimitZone
from app.models.buildings import Building


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

        # 不可达标记 (禁飞区)
        self.blocked: set[tuple[int, int]] = set()  # (row, col)
        # 建筑物阻塞 (地面层不可通行，需爬升越过)
        self.building_blocked: set[tuple[int, int]] = set()  # (row, col)
        # 建筑物高度: {(row, col): height_meters}
        self.building_heights: dict[tuple[int, int], float] = {}
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
    cell_size_meters: float = 50,
    include_buildings: bool = False,  # 默认关闭—45k建筑建网格太慢，改用高度剖面检查
) -> GridMap:
    """从数据库中的禁飞区/限高区/建筑物构建网格地图"""
    grid = GridMap(min_lng, max_lng, min_lat, max_lat, cell_size_meters)

    # ── 1. 禁飞区 → 完全阻塞 ─────────────────
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

    # ── 3. 建筑物 → 高度记录（高效批量空间查询）────
    if include_buildings:
        try:
            table_exists = db.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'buildings')")
            ).fetchone()[0]

            if table_exists:
                # 获取该区域所有高层建筑（>=20m），用一次 SQL 查询
                print("  查询建筑数据 (高度>=20m)...")
                tall_buildings = db.query(Building).filter(
                    text("""
                        (height >= 20 OR (levels >= 7 AND height IS NULL) OR (height IS NULL AND levels IS NULL))
                        AND geometry && ST_MakeEnvelope(:xmin, :ymin, :xmax, :ymax, 4326)
                    """),
                    {"xmin": min_lng, "ymin": min_lat, "xmax": max_lng, "ymax": max_lat}
                ).limit(3000).all()

                print(f"  覆盖 {len(tall_buildings)} 栋建筑")

                # 对每个网格单元，批量查询是否在建筑内
                building_cells = 0
                processed_cells = set()

                for building in tall_buildings:
                    bh = building.effective_height
                    if bh < 15:
                        continue  # 低于15m不影响飞行

                    # 使用建筑边界框快速填充网格
                    bbox = db.execute(
                        text("""
                            SELECT ST_XMin(geometry), ST_YMin(geometry),
                                   ST_XMax(geometry), ST_YMax(geometry)
                            FROM buildings WHERE id = :id
                        """),
                        {"id": building.id}
                    ).fetchone()
                    if not bbox:
                        continue

                    xmin, ymin, xmax, ymax = bbox
                    min_cell = grid.lnglat_to_cell(xmin, ymin)
                    max_cell = grid.lnglat_to_cell(xmax, ymax)
                    dx = max(1, max_cell.col - min_cell.col + 1)
                    dy = max(1, max_cell.row - min_cell.row + 1)

                    # 小建筑直接按边界框填充，大建筑才逐格检查
                    if dx * dy <= 9:  # <= 3x3 cells
                        for row in range(min_cell.row, min(min_cell.row + dy, grid.rows)):
                            for col in range(min_cell.col, min(min_cell.col + dx, grid.cols)):
                                key = (row, col)
                                if key in processed_cells:
                                    existing_h = grid.building_heights.get(key, 0)
                                    if bh > existing_h:
                                        grid.building_heights[key] = bh
                                else:
                                    grid.building_blocked.add(key)
                                    grid.building_heights[key] = bh
                                    processed_cells.add(key)
                                    building_cells += 1
                    # 大建筑才做精确的 ST_Contains 查询
                    else:
                        for r_offset in range(min(dy, 10)):
                            row = min_cell.row + r_offset
                            for c_offset in range(min(dx, 10)):
                                col = min_cell.col + c_offset
                                cell = GridCell(row, col)
                                if not grid.is_valid(cell):
                                    continue
                                key = (row, col)
                                if key in processed_cells:
                                    existing_h = grid.building_heights.get(key, 0)
                                    if bh > existing_h:
                                        grid.building_heights[key] = bh
                                    continue
                                lng, lat = grid.cell_to_lnglat(row, col)
                                result = db.execute(
                                    text("""
                                        SELECT 1 FROM buildings WHERE id = :id
                                        AND ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                                    """),
                                    {"lng": lng, "lat": lat, "id": building.id}
                                ).fetchone()
                                if result:
                                    grid.building_blocked.add(key)
                                    grid.building_heights[key] = bh
                                    processed_cells.add(key)
                                    building_cells += 1

                print(f"  建筑覆盖网格: {building_cells} 个")
        except Exception as e:
            print(f"  [提示] 建筑数据不可用: {e}")

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
            # 建筑物惩罚：高于巡航高度的建筑增加代价
            building_h = grid.building_heights.get(nkey, 0)
            if building_h > 100:  # 超过巡航高度
                move_cost *= (1 + building_h / 200)  # 越高代价越大

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


def compute_altitude_profile(
    db: Session,
    path: list[tuple[float, float]],
    cruise_alt: float = 100.0,
    takeoff_alt: float = 0.0,
    landing_alt: float = 30.0,
    building_safety_margin: float = 20.0,
) -> list[dict]:
    """
    为路径计算高度剖面，考虑限高区、建筑物高度。

    高度策略：
    - 起飞段（前 5%）：从地面爬升至巡航高度
    - 巡航段：保持巡航高度（但在建筑上方时爬升越过）
    - 限高区段：降至限高区内允许的最大高度
    - 建筑区段：爬升至建筑高度 + 安全余量上方
    - 降落段（最后 5%）：从巡航高度降至降落高度

    返回: [{"alt": 高度, "phase": 飞行阶段}, ...]
    """
    if not path or len(path) < 2:
        return [{"alt": cruise_alt, "phase": "cruise"}] * len(path)

    n = len(path)
    SAFETY = building_safety_margin

    # ── 1. 查询限高区 ────────────────────────
    height_limit_zones = db.query(HeightLimitZone).all()
    zone_info = []

    for zone in height_limit_zones:
        for lng, lat in path[::max(1, n // 20)]:
            result = db.execute(
                text("""
                    SELECT ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                    FROM height_limit_zones WHERE id = :id
                """),
                {"lng": lng, "lat": lat, "id": zone.id}
            ).fetchone()
            if result and result[0]:
                zone_info.append({"id": zone.id, "max_altitude": zone.max_altitude})
                break

    in_height_limit = [False] * n
    min_height_limit = [cruise_alt] * n

    if zone_info:
        for i, (lng, lat) in enumerate(path):
            for zone in zone_info:
                result = db.execute(
                    text("""
                        SELECT ST_Contains(
                            (SELECT geometry FROM height_limit_zones WHERE id = :zid),
                            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
                        )
                    """),
                    {"zid": zone["id"], "lng": lng, "lat": lat}
                ).fetchone()
                if result and result[0]:
                    in_height_limit[i] = True
                    min_height_limit[i] = min(min_height_limit[i], zone["max_altitude"])

    # ── 2. 查询建筑物（高效：采样路径点，单次SQL聚合查询）────
    building_height_at_point = [0.0] * n

    try:
        table_exists = db.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'buildings')")
        ).fetchone()[0]

        if table_exists:
            # 采样路径点（每隔5个点取一个），大幅减少查询次数
            sample_indices = list(range(0, n, max(1, n // 40)))
            for idx in sample_indices:
                lng, lat = path[idx]
                # 单次查询：获取该点所在建筑的最高高度
                result = db.execute(
                    text("""
                        SELECT MAX(COALESCE(height, levels * 3.0, 10))
                        FROM buildings
                        WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                        AND (height >= 15 OR levels >= 5 OR (height IS NULL AND levels IS NULL))
                    """),
                    {"lng": lng, "lat": lat}
                ).fetchone()

                if result and result[0] and result[0] > 0:
                    # 将建筑高度应用到该采样点及其附近的点
                    for j in range(max(0, idx - 2), min(n, idx + 3)):
                        building_height_at_point[j] = max(
                            building_height_at_point[j],
                            float(result[0])
                        )
    except Exception as e:
        print(f"  [提示] 建筑高度查询跳过: {e}")

    # ── 3. 计算高度剖面 ──────────────────────
    profile = []
    min_phase_points = 3
    takeoff_pct = max(0.05, min(0.15, min_phase_points / max(n, 1)))
    landing_pct = max(0.05, min(0.15, min_phase_points / max(n, 1)))
    takeoff_end = max(1, int(n * takeoff_pct))
    landing_start = max(takeoff_end + 1, min(n - 2, n - int(n * landing_pct)))

    for i in range(n):
        if i <= takeoff_end:
            t = i / takeoff_end
            alt = takeoff_alt + (cruise_alt - takeoff_alt) * t
            phase = "ascent"
        elif i >= landing_start:
            t = (i - landing_start) / max(1, (n - 1 - landing_start))
            alt = cruise_alt + (landing_alt - cruise_alt) * t
            phase = "descent"
        elif in_height_limit[i]:
            target_alt = min(cruise_alt, min_height_limit[i])
            alt = target_alt
            phase = "height_limit"
        elif building_height_at_point[i] > 0:
            # 建筑上方：爬升到建筑高度 + 安全余量
            target_alt = max(cruise_alt, building_height_at_point[i] + SAFETY)
            alt = target_alt
            phase = "building"
        else:
            alt = cruise_alt
            phase = "cruise"

        profile.append({"alt": round(alt, 1), "phase": phase})

    # ── 4. 平滑处理 ──────────────────────────
    for i in range(1, n - 1):
        if profile[i]["phase"] == "height_limit" and profile[i - 1]["phase"] == "cruise":
            # 进入限高区：开始下降
            profile[i]["phase"] = "descent"
        elif profile[i]["phase"] == "cruise" and profile[i - 1]["phase"] == "height_limit":
            # 离开限高区：开始爬升
            profile[i]["phase"] = "ascent"

    return profile


def plan_path(
    db: Session,
    start_lng: float, start_lat: float,
    end_lng: float, end_lat: float,
    waypoints: list[tuple[float, float]] = None,
    cell_size_meters: float = 50,
    consider_weather: bool = True,
    include_buildings_in_grid: bool = False,  # 建筑数据量大，建网格时默认跳过
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

    # 修复起止点偏移：确保路径首尾点为精确的起止坐标
    if full_path:
        full_path[0] = (start_lng, start_lat)
        full_path[-1] = (end_lng, end_lat)

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

    # 计算高度剖面（考虑限高区和建筑物高度）
    altitude_profile = compute_altitude_profile(db, full_path)

    return {
        "path": [
            {"lng": p[0], "lat": p[1], "alt": altitude_profile[i]["alt"], "phase": altitude_profile[i]["phase"]}
            for i, p in enumerate(full_path)
        ],
        "total_distance": round(total_distance, 2),
        "estimated_time": round(estimated_time, 2),
        "segments": [],
        "warnings": warnings,
        "is_feasible": is_feasible,
        "altitude_profile": altitude_profile,
    }
