import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from .config import Config

class WeatherDB:
    def __init__(self, db_path: Path = None):
        self.db_path = str(db_path or Config.DB_PATH)
        self._init_tables()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self._get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weather_current (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collect_time TEXT NOT NULL,
                    city TEXT NOT NULL,
                    city_id TEXT NOT NULL,
                    temp_c REAL,
                    feels_like_c REAL,
                    humidity_pct REAL,
                    weather_text TEXT,
                    wind_direction TEXT,
                    wind_speed_kmh REAL,
                    wind_scale TEXT,
                    visibility_km REAL,
                    pressure_hpa REAL,
                    cloud_pct REAL,
                    dew_point_c REAL,
                    precip_mm REAL,
                    raw_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weather_hourly (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collect_batch_id TEXT NOT NULL,
                    city TEXT NOT NULL,
                    city_id TEXT NOT NULL,
                    forecast_hour TEXT NOT NULL,
                    temp_c REAL,
                    humidity_pct REAL,
                    weather_text TEXT,
                    pop_pct REAL,
                    precip_mm REAL,
                    cloud_pct REAL,
                    pressure_hpa REAL,
                    dew_point_c REAL,
                    wind_direction TEXT,
                    wind_speed_kmh REAL,
                    wind_scale TEXT,
                    wind_angle INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collect_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL UNIQUE,
                    collect_time TEXT NOT NULL,
                    city TEXT NOT NULL,
                    city_id TEXT NOT NULL,
                    status TEXT,
                    hourly_count INTEGER,
                    error_msg TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def save_batch(self, batch_id: str, collect_time: str,
                   city_name: str, city_id: str,
                   current: Dict, hourly: List[Dict]):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO weather_current
                    (collect_time, city, city_id, temp_c, feels_like_c,
                     humidity_pct, weather_text, wind_direction, wind_speed_kmh,
                     wind_scale, visibility_km, pressure_hpa, cloud_pct,
                     dew_point_c, precip_mm, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                collect_time, city_name, city_id,
                current.get("temp_c"), current.get("feels_like_c"),
                current.get("humidity_pct"), current.get("weather_text"),
                current.get("wind_direction"), current.get("wind_speed_kmh"),
                current.get("wind_scale"), current.get("visibility_km"),
                current.get("pressure_hpa"), current.get("cloud_pct"),
                current.get("dew_point_c"), current.get("precip_mm"),
                json.dumps(current, ensure_ascii=False)
            ))

            rows = []
            for h in hourly:
                rows.append((
                    batch_id, city_name, city_id, h["hour"],
                    h["temp_c"], h["humidity_pct"], h["weather_text"],
                    h["pop_pct"], h["precip_mm"], h["cloud_pct"],
                    h["pressure_hpa"], h["dew_point_c"],
                    h["wind_direction"], h["wind_speed_kmh"],
                    h["wind_scale"], h["wind_angle"]
                ))
            conn.executemany("""
                INSERT INTO weather_hourly
                    (collect_batch_id, city, city_id, forecast_hour,
                     temp_c, humidity_pct, weather_text, pop_pct,
                     precip_mm, cloud_pct, pressure_hpa, dew_point_c,
                     wind_direction, wind_speed_kmh, wind_scale, wind_angle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

            conn.execute("""
                INSERT INTO collect_log (batch_id, collect_time, city, city_id, status, hourly_count)
                VALUES (?, ?, ?, ?, 'success', ?)
            """, (batch_id, collect_time, city_name, city_id, len(hourly)))

            conn.commit()

    def log_failure(self, batch_id: str, collect_time: str, city_name: str, city_id: str, error_msg: str):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO collect_log (batch_id, collect_time, city, city_id, status, error_msg)
                VALUES (?, ?, ?, ?, 'failed', ?)
            """, (batch_id, collect_time, city_name, city_id, error_msg))
            conn.commit()

    def get_latest_batch_data(self, city_name: str) -> Optional[Dict]:
        """获取某个城市最新一次成功采集的完整数据"""
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT batch_id, collect_time FROM collect_log WHERE city=? AND status='success' ORDER BY id DESC LIMIT 1",
                (city_name,)
            )
            row = cur.fetchone()
            if not row:
                return None
            batch_id = row["batch_id"]
            collect_time = row["collect_time"]

            cur2 = conn.execute(
                "SELECT * FROM weather_current WHERE city=? AND collect_time=? ORDER BY id DESC LIMIT 1",
                (city_name, collect_time)
            )
            current_row = cur2.fetchone()
            if not current_row:
                return None

            cur3 = conn.execute(
                "SELECT * FROM weather_hourly WHERE city=? AND collect_batch_id=? ORDER BY forecast_hour",
                (city_name, batch_id)
            )
            hourly_rows = cur3.fetchall()

            return {
                "meta": {
                    "batch_id": batch_id,
                    "collection_time": collect_time,
                    "city": city_name,
                    "city_id": current_row["city_id"],
                },
                "current": dict(current_row),
                "hourly": [dict(r) for r in hourly_rows],
            }