import logging
import smtplib
import html
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
from .config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

def format_email_html(analysis_text: str, city_name: str = None) -> str:
    safe_text = html.escape(analysis_text).replace('\n', '<br>')
    city_display = f"【{city_name}】" if city_name else ""
    html_body = f"""
    <div style="max-width:600px;margin:0 auto;font-family:'Microsoft YaHei', Arial, sans-serif;background:#f5f7fa;border-radius:16px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,0.06);">
        <div style="background: linear-gradient(135deg, #a0c4ff 0%, #74a6f2 100%); padding: 28px 30px 20px; text-align: center;">
            <div style="font-size:48px; margin-bottom:8px;">🌤️</div>
            <h2 style="color:white; margin:0; font-size:26px;">今日{city_display}天气提醒</h2>
            <p style="color: rgba(255,255,255,0.85); margin:8px 0 0; font-size:14px;">出门前，花十秒看一眼天气 🌿</p>
        </div>
        <div style="background:white; margin: -12px 16px 20px; padding: 24px 24px 18px; border-radius: 14px; box-shadow: 0 2px 12px rgba(0,0,0,0.04); line-height: 1.9; font-size: 15px; color: #2e3b4e;">
            {safe_text}
        </div>
        <div style="padding: 0 20px 24px; text-align: center; color: #8899aa; font-size: 12px;">
            <div style="border-top: 1px solid #e8edf2; width: 40px; margin: 0 auto 12px;"></div>
            📬 此邮件由 <strong>{Config.SENDER_NAME}</strong> 自动生成<br>
            🌅 每天早晨为您定时推送
        </div>
    </div>
    """
    return html_body

def send_email(subject: str, html_content: str, to_emails: list) -> bool:
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        logger.error("SMTP未配置")
        return False
    msg = MIMEText(html_content, "html", "utf-8")
    msg["From"] = formataddr((Config.SENDER_NAME, Config.SENDER_EMAIL))
    msg["To"] = ",".join(to_emails)
    msg["Subject"] = Header(subject, "utf-8")
    try:
        if Config.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=15)
            server.starttls()
        server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        server.sendmail(Config.SENDER_EMAIL, to_emails, msg.as_string())
        server.quit()
        logger.info(f"邮件已发送至 {', '.join(to_emails)}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False

def notify_city(city_name: str, to_emails: list, analysis_text: str = None) -> bool:
    """为单个城市发送邮件提醒。若不提供analysis_text则自动生成。"""
    if analysis_text is None:
        from .analyzer import generate_analysis_for_city
        analysis_text = generate_analysis_for_city(city_name)
        if not analysis_text:
            return False
    subject = f"{datetime.now().strftime('%Y-%m-%d')} {city_name} 天气提醒"
    html_body = format_email_html(analysis_text, city_name)
    return send_email(subject, html_body, to_emails)