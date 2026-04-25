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

    upcoming_hours = h[:18]  # 未来18小时
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
你是一个贴心的天气生活助手，请根据下面的天气数据，生成一段通过邮件发送给用户的建议。

要求：
1. 开头用一句自然的早安问候，然后直接切入天气
2. 内容需包含：
   - 今日天气特点概括（气温趋势、是否有雨）
   - 穿衣建议（结合体感温度和风力）
   - 是否需要带伞
   - 是否适合户外运动（结合气温、降水、风力判断）
   - 一句结合{data['meta']['city']}城市特点的简洁生活建议或祝福
3. 风格：亲切、实用，适合早晨阅读，用户需要根据建议安排一天的活动
4. 不分点，一段话完成，尽量控制在200字以内，但注意不在最后截断

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

def analyze_with_llm(prompt: str, max_retries: int = 3) -> str:
    client = openai.OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
    
    for attempt in range(max_retries + 1):
        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[
                {"role": "system", "content": "你是一个专业的天气生活助手。输出要完整，不要中途截断。"},
                {"role": "user", "content": prompt},
            ],
            temperature=Config.LLM_TEMP,
            max_tokens=500,  # 足够容纳 250 字中文
        )
        result = response.choices[0].message.content.strip()
        
        # 检查是否可能被截断（以不完整标点或句子结尾）
        if result and result[-1] in "。！？…":
            return result
        
        # 如果被截断且还有重试次数，重新生成
        if attempt < max_retries:
            logger.warning(f"输出可能被截断（结尾：{result[-20:]}），重新生成...")
            continue
    
    return result  # 返回最后一次结果

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