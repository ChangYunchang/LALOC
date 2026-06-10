"""
OSM 建筑数据导入工具

通过 Overpass API 获取广州市区建筑数据，解析并导入 PostGIS。
用于 A* 路径规划的建筑障碍物避让。

使用方式:
    cd backend
    venv\\Scripts\\activate
    python -m app.utils.osm_loader

首次运行会从 Overpass API 下载数据（约 1-3 分钟），后续使用本地缓存。
"""
import json
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models.buildings import Building

# Overpass API 端点（优先使用主站，备选国内镜像）
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# 广州市区范围 (~30km x 30km)
GUANGZHOU_BBOX = {
    "south": 22.95,
    "west": 113.10,
    "north": 23.25,
    "east": 113.60,
}

# 本地缓存文件
CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
CACHE_FILE = CACHE_DIR / "guangzhou_buildings.json"


def build_overpass_query(bbox: dict) -> str:
    """构建 Overpass API 查询"""
    return f"""
    [out:json][timeout:120];
    (
      way["building"]({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']});
    );
    out body;
    >;
    out skel qt;
    """


async def fetch_buildings_from_overpass(bbox: dict) -> list[dict]:
    """从 Overpass API 获取建筑数据"""
    query = build_overpass_query(bbox)
    print(f"查询范围: ({bbox['south']}, {bbox['west']}) -> ({bbox['north']}, {bbox['east']})")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "User-Agent": "LALOC/1.0",
        "Accept": "application/json, */*",
    }

    last_error = None
    for url in OVERPASS_URLS:
        try:
            async with httpx.AsyncClient(timeout=120.0, headers=headers, follow_redirects=True) as client:
                print(f"  尝试: {url}")
                response = await client.post(url, content=f"data={query}")
                response.raise_for_status()
                data = response.json()
                print(f"  成功！从 {url} 获取数据")
                break
        except Exception as e:
            print(f"  失败: {e}")
            last_error = e
    else:
        raise RuntimeError(f"所有 Overpass API 端点均不可用，最后错误: {last_error}")

    elements = data.get("elements", [])
    print(f"获取到 {len(elements)} 个 OSM 元素")

    # 解析：ways 是建筑多边形，nodes 是坐标点
    nodes = {}
    ways = []

    for el in elements:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])
        elif el["type"] == "way":
            ways.append(el)

    # 构建 GeoJSON 风格的建筑数据
    buildings = []
    skipped_no_nodes = 0
    skipped_no_coords = 0

    for way in ways:
        tags = way.get("tags", {})

        # 必须有 building 标签
        if "building" not in tags:
            continue

        # 获取坐标
        node_ids = way.get("nodes", [])
        if not node_ids:
            skipped_no_nodes += 1
            continue

        coords = []
        for nid in node_ids:
            if nid in nodes:
                coords.append(list(nodes[nid]))
            else:
                # 节点可能在 out skel 中缺失，跳过不完整的
                coords = None
                break

        if coords is None:
            skipped_no_coords += 1
            continue

        # 确保多边形闭合 (首尾相同)
        if len(coords) >= 3 and coords[0] != coords[-1]:
            coords.append(coords[0])

        if len(coords) < 4:
            continue

        # 提取属性
        name = tags.get("name")
        height = tags.get("height")
        levels = tags.get("building:levels")

        # 解析高度值
        height_val = None
        if height:
            try:
                height_str = str(height).replace("m", "").replace("米", "").strip()
                height_val = float(height_str)
            except (ValueError, TypeError):
                pass

        levels_val = None
        if levels:
            try:
                levels_val = int(float(str(levels)))
            except (ValueError, TypeError):
                pass

        buildings.append({
            "osm_id": way["id"],
            "name": name,
            "coordinates": [coords],  # GeoJSON Polygon 格式
            "height": height_val,
            "levels": levels_val,
        })

    print(f"解析建筑: {len(buildings)} 个")
    if skipped_no_nodes:
        print(f"  跳过(无节点): {skipped_no_nodes}")
    if skipped_no_coords:
        print(f"  跳过(坐标缺失): {skipped_no_coords}")

    # 统计高度信息覆盖
    with_height = sum(1 for b in buildings if b["height"] is not None)
    with_levels = sum(1 for b in buildings if b["levels"] is not None)
    print(f"  含 height 标签: {with_height}")
    print(f"  含 building:levels 标签: {with_levels}")

    return buildings


def import_buildings_to_db(db: Session, buildings: list[dict], clear_existing: bool = True):
    """将建筑数据导入 PostGIS"""
    if clear_existing:
        print("清除旧建筑数据...")
        db.execute(text("TRUNCATE TABLE buildings RESTART IDENTITY CASCADE"))
        db.commit()

    # 批量插入
    batch_size = 500
    total = len(buildings)
    inserted = 0

    for i in range(0, total, batch_size):
        batch = buildings[i:i + batch_size]
        for b in batch:
            coords = b["coordinates"][0]
            # 构建 WKT POLYGON
            coord_str = ", ".join(f"{c[0]} {c[1]}" for c in coords)
            wkt = f"POLYGON(({coord_str}))"

            building = Building(
                osm_id=b["osm_id"],
                name=b["name"],
                geometry=wkt,
                height=b["height"],
                levels=b["levels"],
            )
            db.add(building)

        db.commit()
        inserted += len(batch)
        print(f"  进度: {inserted}/{total} ({inserted * 100 // total}%)")

    print(f"导入完成: {inserted} 栋建筑")


def create_table_if_not_exists():
    """确保 buildings 表存在"""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS buildings (
                id SERIAL PRIMARY KEY,
                osm_id BIGINT,
                name VARCHAR(255),
                geometry GEOMETRY(POLYGON, 4326),
                height DOUBLE PRECISION,
                levels INTEGER
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_buildings_geom
            ON buildings USING GIST (geometry)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_buildings_osm_id
            ON buildings (osm_id)
        """))
    print("buildings 表已就绪")


def main():
    """主流程：获取建筑数据 -> 导入 PostGIS"""
    import asyncio

    print("=" * 50)
    print("  LALOC OSM 建筑数据导入工具")
    print("=" * 50)
    print()

    # 1. 确保表存在
    create_table_if_not_exists()

    # 2. 获取数据
    buildings = None

    # 检查本地缓存
    if CACHE_FILE.exists():
        cache_age = time.time() - CACHE_FILE.stat().st_mtime
        if cache_age < 86400:  # 24小时内
            print(f"使用本地缓存 ({(cache_age / 3600):.1f} 小时前)")
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                buildings = json.load(f)
            print(f"缓存建筑: {len(buildings)} 个")

    if buildings is None:
        buildings = asyncio.run(fetch_buildings_from_overpass(GUANGZHOU_BBOX))

        # 缓存到本地
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(buildings, f, ensure_ascii=False)
        print(f"已缓存到: {CACHE_FILE}")

    # 3. 导入数据库
    db = SessionLocal()
    try:
        import_buildings_to_db(db, buildings)
    finally:
        db.close()

    # 4. 统计
    db = SessionLocal()
    try:
        count = db.query(Building).count()
        with_height = db.query(Building).filter(Building.height.isnot(None)).count()
        with_levels = db.query(Building).filter(Building.levels.isnot(None)).count()
        print()
        print("=" * 50)
        print(f"  数据库统计:")
        print(f"    总建筑数:    {count}")
        print(f"    含高度标签:  {with_height}")
        print(f"    含楼层标签:  {with_levels}")
        print(f"    高度覆盖:    {max(with_height, with_levels)}/{count}")
        print("=" * 50)
    finally:
        db.close()


if __name__ == "__main__":
    main()
