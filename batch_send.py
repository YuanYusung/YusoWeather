#!/usr/bin/env python3
import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from weather_pkg.config import Config
from weather_pkg.collector import run_collection
from weather_pkg.analyzer import generate_analysis_for_city
from weather_pkg.notifier import notify_city

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def load_cities_from_csv(filepath):
    cities = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            emails = [e.strip() for e in row["emails"].split(",") if e.strip()]
            cities.append({
                "city_name": row["city_name"],
                "city_id": row["city_id"],
                "emails": emails
            })
    return cities

def load_cities_from_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    cities = []
    for item in data:
        if isinstance(item["emails"], str):
            emails = [e.strip() for e in item["emails"].split(",")]
        else:
            emails = item["emails"]
        cities.append({
            "city_name": item["city_name"],
            "city_id": item["city_id"],
            "emails": emails
        })
    return cities

def main():
    parser = argparse.ArgumentParser(description="批量采集多城市天气并发送邮件")
    parser.add_argument("--file", required=True, help="城市配置文件 (csv 或 json)")
    parser.add_argument("--skip-collect", action="store_true", help="跳过采集，使用已有数据")
    parser.add_argument("--forecast-hours", default="24h")
    args = parser.parse_args()

    Config.ensure_dirs()
    file_path = Path(args.file)
    if not file_path.exists():
        logger.error(f"文件不存在: {file_path}")
        sys.exit(1)

    if file_path.suffix.lower() == ".csv":
        cities = load_cities_from_csv(file_path)
    elif file_path.suffix.lower() in (".json", ".jsonc"):
        cities = load_cities_from_json(file_path)
    else:
        logger.error("仅支持 .csv 或 .json 格式")
        sys.exit(1)

    if not cities:
        logger.error("未读取到任何城市配置")
        sys.exit(1)

    success_all = True
    for city in cities:
        cname = city["city_name"]
        cid = city["city_id"]
        emails = city["emails"]
        logger.info(f"开始处理城市: {cname} ({cid}) -> {emails}")

        if not args.skip_collect:
            if not run_collection(cname, cid, args.forecast_hours):
                logger.error(f"采集失败，跳过 {cname}")
                continue

        analysis = generate_analysis_for_city(cname)
        if not analysis:
            logger.error(f"分析失败，跳过 {cname}")
            continue

        if notify_city(cname, emails, analysis):
            logger.info(f"{cname} 邮件发送成功")
        else:
            logger.error(f"{cname} 邮件发送失败")
            success_all = False

    if success_all:
        logger.info("批量任务完成，所有城市均成功")
    else:
        logger.warning("批量任务完成，部分城市失败")

if __name__ == "__main__":
    main()