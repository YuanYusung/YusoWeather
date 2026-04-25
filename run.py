#!/usr/bin/env python3
"""
统一入口：采集指定城市的天气，生成分析，并发送邮件。
用法：
    python run.py --city 武汉 --city-id 101200101 --email friend@example.com
    或使用环境变量默认值（需设置 CITY_NAME, CITY_ID, RECEIVER_EMAIL）
"""

import argparse
import logging
import sys
from weather_pkg.config import Config
from weather_pkg.collector import run_collection
from weather_pkg.analyzer import generate_analysis_for_city
from weather_pkg.notifier import notify_city

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default=os.getenv("CITY_NAME"), help="城市名称")
    parser.add_argument("--city-id", default=os.getenv("CITY_ID"), help="和风城市ID")
    parser.add_argument("--email", default=os.getenv("RECEIVER_EMAIL"), help="收件邮箱，多个用逗号分隔")
    parser.add_argument("--skip-collect", action="store_true", help="跳过采集，直接使用已有数据分析发送")
    parser.add_argument("--forecast-hours", default="24h", help="预报时长 24h/72h/168h")
    args = parser.parse_args()

    if not args.city or not args.city_id:
        logger.error("必须提供 --city 和 --city-id (或设置环境变量 CITY_NAME, CITY_ID)")
        sys.exit(1)
    if not args.email:
        logger.error("必须提供 --email (或设置环境变量 RECEIVER_EMAIL)")
        sys.exit(1)

    Config.ensure_dirs()
    to_emails = [e.strip() for e in args.email.split(",") if e.strip()]

    if not args.skip_collect:
        success = run_collection(args.city, args.city_id, args.forecast_hours)
        if not success:
            logger.error("采集失败，停止后续")
            sys.exit(1)

    analysis = generate_analysis_for_city(args.city)
    if not analysis:
        logger.error("生成分析失败")
        sys.exit(1)

    # 可选：保存分析文本到文件
    analysis_file = Config.DATA_DIR / f"latest_analysis_{args.city}.txt"
    analysis_file.write_text(analysis, encoding="utf-8")
    logger.info(f"分析文本已保存至 {analysis_file}")

    if notify_city(args.city, to_emails, analysis):
        logger.info("邮件发送成功")
    else:
        logger.error("邮件发送失败")
        sys.exit(1)

if __name__ == "__main__":
    import os
    main()