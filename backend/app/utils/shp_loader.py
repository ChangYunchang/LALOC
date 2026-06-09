"""
Shapefile 数据导入工具
将禁飞区和限高区的 .shp 文件导入 PostgreSQL + PostGIS 数据库
"""
import geopandas as gpd
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine


def import_shapefile_to_postgis(
    shp_path: str,
    table_name: str,
    name_prefix: str = "",
    max_altitude: float = None,
    reason: str = "",
):
    """
    将 Shapefile 导入 PostGIS 数据表

    参数:
        shp_path: .shp 文件路径
        table_name: 目标数据库表名
        name_prefix: 区域名称前缀
        max_altitude: 限高区的最大高度（仅限高区需要）
        reason: 区域原因说明
    """
    print(f"正在读取 Shapefile: {shp_path}")

    # 读取 Shapefile
    gdf = gpd.read_file(shp_path)
    print(f"  读取到 {len(gdf)} 个要素")
    print(f"  坐标系: {gdf.crs}")
    print(f"  几何类型: {gdf.geom_type.unique()}")
    print(f"  列名: {list(gdf.columns)}")

    # 确保是 WGS84 坐标系
    if gdf.crs is None:
        print("  警告: 无坐标系信息，假设为 WGS84")
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        print(f"  转换坐标系从 {gdf.crs} 到 WGS84")
        gdf = gdf.to_crs(epsg=4326)

    # 获取数据库会话
    db = SessionLocal()

    try:
        # 先检查表是否存在
        result = db.execute(
            text(f"SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
        )
        table_exists = result.fetchone()[0]

        if not table_exists:
            print(f"  错误: 表 {table_name} 不存在，请先运行数据库迁移")
            return

        # 清空现有数据
        db.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"))
        db.commit()
        print(f"  已清空表 {table_name}")

        # 逐行插入数据
        inserted = 0
        for idx, row in gdf.iterrows():
            geom = row.geometry

            if geom is None or geom.is_empty:
                continue

            # 确保是 Polygon 或 MultiPolygon
            if geom.geom_type == 'MultiPolygon':
                # MultiPolygon 拆分为多个 Polygon
                for poly in geom.geoms:
                    _insert_polygon(db, table_name, poly, idx, name_prefix, max_altitude, reason)
                    inserted += 1
            elif geom.geom_type == 'Polygon':
                _insert_polygon(db, table_name, geom, idx, name_prefix, max_altitude, reason)
                inserted += 1
            else:
                print(f"  跳过非多边形几何: {geom.geom_type}")
                continue

        db.commit()
        print(f"  成功导入 {inserted} 个区域到 {table_name}")

    except Exception as e:
        db.rollback()
        print(f"  导入失败: {e}")
        raise
    finally:
        db.close()


def _insert_polygon(
    db: Session,
    table_name: str,
    polygon,
    idx: int,
    name_prefix: str,
    max_altitude: float,
    reason: str,
):
    """插入单个多边形"""
    # 去掉 Z 维度，只保留 2D 坐标
    from shapely import force_2d
    polygon_2d = force_2d(polygon)
    # 将 Shapely 几何转为 WKT
    wkt = polygon_2d.wkt

    if table_name == "no_fly_zones":
        db.execute(
            text(f"""
                INSERT INTO {table_name} (name, geometry, altitude_min, altitude_max, reason)
                VALUES (
                    :name,
                    ST_SetSRID(ST_GeomFromText(:wkt), 4326),
                    0,
                    9999,
                    :reason
                )
            """),
            {
                "name": f"{name_prefix}-{idx + 1}" if name_prefix else f"禁飞区-{idx + 1}",
                "wkt": wkt,
                "reason": reason,
            }
        )
    elif table_name == "height_limit_zones":
        db.execute(
            text(f"""
                INSERT INTO {table_name} (name, geometry, max_altitude, min_altitude, reason)
                VALUES (
                    :name,
                    ST_SetSRID(ST_GeomFromText(:wkt), 4326),
                    :max_alt,
                    0,
                    :reason
                )
            """),
            {
                "name": f"{name_prefix}-{idx + 1}" if name_prefix else f"限高区-{idx + 1}",
                "wkt": wkt,
                "max_alt": max_altitude or 120,
                "reason": reason,
            }
        )


def import_all_data():
    """导入所有禁飞区和限高区数据"""
    import os
    from pathlib import Path

    # 优先从项目 data 目录读取，否则从桌面读取
    project_root = Path(__file__).parent.parent.parent.parent
    data_dir = project_root / "data"
    desktop_dir = Path.home() / "Desktop"

    # 禁飞区
    nofly_shp = data_dir / "nofly_zones" / "JinFeiQu.shp"
    if not nofly_shp.exists():
        nofly_shp = desktop_dir / "禁飞区" / "JinFeiQu.shp"
    if nofly_shp.exists():
        import_shapefile_to_postgis(
            shp_path=str(nofly_shp),
            table_name="no_fly_zones",
            name_prefix="禁飞区",
            reason="政府划定的禁飞区域",
        )
    else:
        print(f"禁飞区文件不存在，请将数据放到 data/nofly_zones/ 或桌面/禁飞区/")

    # 限高区
    height_shp = data_dir / "height_limit_zones" / "XianGaoQu.shp"
    if not height_shp.exists():
        height_shp = desktop_dir / "限高区" / "XianGaoQu.shp"
    if height_shp.exists():
        import_shapefile_to_postgis(
            shp_path=str(height_shp),
            table_name="height_limit_zones",
            name_prefix="限高区",
            max_altitude=120,  # 默认限高120米
            reason="政府划定的限高区域",
        )
    else:
        print(f"限高区文件不存在，请将数据放到 data/height_limit_zones/ 或桌面/限高区/")


if __name__ == "__main__":
    import_all_data()
