import logging
from datetime import datetime
from typing import Dict, List, Optional
import openai
from .config import Config
from .database import WeatherDB

logger = logging.getLogger(__name__)

def build_prompt(data: Dict) -> str:
    c = data["current"]
    h = data["hourly"]
    collect_time = c.get("collect_time", "")
    date_str = collect_time[:10] if collect_time else "今天"
    time_str = collect_time[11:19] if len(collect_time) > 19 else "当前"

    upcoming_hours = h[:6]  # 未来6小时
    hourly_lines = []
    for item in upcoming_hours:
        hour_label = item.get("forecast_hour", "")[-5:]
        temp = item.get("temp_c")
        temp_str = f"{temp}°C" if temp is not None else "无数据"
        weather = item.get("weather_text", "未知")
        precip = item.get("precip_mm", 0) or 0
        humidity = item.get("humidity_pct")
        humidity_str = f"{humidity}%" if humidity is not None else "无"
        cloud = item.get("cloud_pct")
        cloud_str = f"{cloud}%" if cloud is not None else "无"
        hourly_lines.append(
            f"{hour_label}  {temp_str}  {weather}  降水{precip}mm  湿度{humidity_str}  云量{cloud_str}"
        )

    def safe_val(val, unit=""):
        return f"{val}{unit}" if val is not None else "暂无"

    prompt = f"""
你是一个贴心的生活助手，请根据下面的天气数据，生成一段通过邮件发送给用户的建议。

要求：
- 开头简洁说明今天是{date_str}，城市是{data['meta']['city']}
- 用一两句话概括今日天气特点
- 给出穿衣建议（考虑体感温度和风力）
- 说明是否需要带伞
- 简单判断是否适合户外运动并解释
- 最后加一句建议做的事情、生活祝福或提醒
- 整段话连贯自然，不分点，控制在200字以内
- 注意邮件发送时间一般是早上，请结合这一特点

天气数据：
{data['meta']['city']}实时观测：{date_str} {time_str}
温度 {safe_val(c.get('temp_c'),'°C')}（体感 {safe_val(c.get('feels_like_c'),'°C')}）
天气：{c.get('weather_text','未知')}
湿度：{safe_val(c.get('humidity_pct'),'%')}
风力：{c.get('wind_direction','')} {safe_val(c.get('wind_speed_kmh'),'km/h')}（{c.get('wind_scale','')}）
能见度：{safe_val(c.get('visibility_km'),'km')}
气压：{safe_val(c.get('pressure_hpa'),'hPa')}
云量：{safe_val(c.get('cloud_pct'),'%')}
降水：{safe_val(c.get('precip_mm'),'mm')}

未来几小时预报：
{chr(10).join(hourly_lines)}
"""
    return prompt.strip()

def analyze_with_llm(prompt: str) -> str:
    client = openai.OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
    response = client.chat.completions.create(
        model=Config.LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是一个专业的天气生活助手。"},
            {"role": "user", "content": prompt},
        ],
        temperature=Config.LLM_TEMP,
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()

def generate_analysis_for_city(city_name: str) -> Optional[str]:
    """根据数据库中最新数据生成分析文本，失败返回None"""
    db = WeatherDB()
    data = db.get_latest_batch_data(city_name)
    if not data:
        logger.error(f"未找到城市 {city_name} 的天气数据，无法分析")
        return None
    prompt = build_prompt(data)
    try:
        analysis = analyze_with_llm(prompt)
        return analysis
    except Exception as e:
        logger.error(f"LLM分析失败: {e}")
        return None