import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from .config import Config
from .database import WeatherDB

logger = logging.getLogger(__name__)

def safe_float(val):
    try:
        return float(val) if val not in (None, "") else None
    except (ValueError, TypeError):
        return None

def safe_int(val):
    try:
        return int(val) if val not in (None, "") else None
    except (ValueError, TypeError):
        return None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
def call_qweather(endpoint: str, params: dict, city_id: str) -> dict:
    url = f"{Config.QWEATHER_API_HOST}{endpoint}"
    headers = {"X-QW-Api-Key": Config.QWEATHER_KEY, "Accept-Encoding": "gzip"}
    params["location"] = city_id
    params.setdefault("lang", "zh")
    params.setdefault("unit", "m")

    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") not in {"200", "204"}:
        raise RuntimeError(f"API 错误: {data.get('code')} - {data.get('message')}")
    return data

def fetch_current_weather(city_id: str) -> dict:
    return call_qweather("/v7/weather/now", {}, city_id)

def fetch_hourly_forecast(city_id: str, hours: str = "24h") -> dict:
    return call_qweather(f"/v7/weather/{hours}", {}, city_id)

def transform_current(raw: dict, collect_time: str) -> dict:
    now = raw["now"]
    return {
        "time": collect_time,
        "temp_c": safe_float(now.get("temp")),
        "feels_like_c": safe_float(now.get("feelsLike")),
        "humidity_pct": safe_float(now.get("humidity")),
        "weather_text": now.get("text", ""),
        "weather_icon": now.get("icon", ""),
        "wind_direction": now.get("windDir", ""),
        "wind_angle": safe_int(now.get("wind360")),
        "wind_speed_kmh": safe_float(now.get("windSpeed")),
        "wind_scale": now.get("windScale", ""),
        "visibility_km": safe_float(now.get("vis")),
        "pressure_hpa": safe_float(now.get("pressure")),
        "cloud_pct": safe_float(now.get("cloud")),
        "dew_point_c": safe_float(now.get("dew")),
        "precip_mm": safe_float(now.get("precip")),
    }

def transform_hourly(raw: dict) -> List[dict]:
    result = []
    for item in raw["hourly"]:
        result.append({
            "hour": item.get("fxTime", ""),
            "temp_c": safe_float(item.get("temp")),
            "humidity_pct": safe_float(item.get("humidity")),
            "weather_text": item.get("text", ""),
            "weather_icon": item.get("icon", ""),
            "pop_pct": safe_float(item.get("pop")),
            "precip_mm": safe_float(item.get("precip")),
            "cloud_pct": safe_float(item.get("cloud")),
            "pressure_hpa": safe_float(item.get("pressure")),
            "dew_point_c": safe_float(item.get("dew")),
            "wind_direction": item.get("windDir", ""),
            "wind_angle": safe_int(item.get("wind360")),
            "wind_speed_kmh": safe_float(item.get("windSpeed")),
            "wind_scale": item.get("windScale", ""),
        })
    return result

def collect_city(city_name: str, city_id: str, forecast_hours: str = "24h") -> Tuple[Dict, List[Dict]]:
    """采集单个城市数据，返回 (current_dict, hourly_list)"""
    tz = timezone(timedelta(hours=8))
    collect_time = datetime.now(tz).isoformat()
    logger.info(f"采集城市: {city_name} ({city_id}) 时间: {collect_time}")

    raw_current = fetch_current_weather(city_id)
    current = transform_current(raw_current, collect_time)

    raw_hourly = fetch_hourly_forecast(city_id, forecast_hours)
    hourly = transform_hourly(raw_hourly)

    return current, hourly

def archive_json(batch_id: str, collect_time: str, city_name: str, city_id: str,
                 current: Dict, hourly: List[Dict], forecast_hours: str):
    dt = datetime.fromisoformat(collect_time)
    date_str = dt.strftime("%Y-%m-%d")
    archive_path = Config.ARCHIVE_DIR / date_str / f"{city_id}_{batch_id}.json"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    full_payload = {
        "meta": {
            "batch_id": batch_id,
            "collection_time": collect_time,
            "city": city_name,
            "city_id": city_id,
            "forecast_hours": forecast_hours,
            "hourly_count": len(hourly),
        },
        "current": current,
        "hourly": hourly,
    }
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(full_payload, f, ensure_ascii=False, indent=2)
    logger.info(f"归档 JSON → {archive_path}")

def run_collection(city_name: str, city_id: str, forecast_hours: str = "24h") -> bool:
    """执行完整采集流程（API + 数据库 + 归档），返回是否成功"""
    db = WeatherDB()
    tz = timezone(timedelta(hours=8))
    collect_time = datetime.now(tz).isoformat()
    batch_id = datetime.now(tz).strftime("%Y%m%d_%H%M%S") + f"_{city_id}"

    try:
        current, hourly = collect_city(city_name, city_id, forecast_hours)
        db.save_batch(batch_id, collect_time, city_name, city_id, current, hourly)
        archive_json(batch_id, collect_time, city_name, city_id, current, hourly, forecast_hours)
        logger.info(f"城市 {city_name} 采集完成，batch_id={batch_id}, 小时数据={len(hourly)}")
        return True
    except Exception as e:
        logger.error(f"城市 {city_name} 采集失败: {e}")
        db.log_failure(batch_id, collect_time, city_name, city_id, str(e))
        return False