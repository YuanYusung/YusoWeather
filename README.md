# 🌤️ YusoWeather

自动采集指定城市未来24小时内天气逐小时预报，调用语言大模型生成生活建议，并通过邮件推送给指定用户 

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
> ⚠️ **学习项目声明**  
> 本项目是我学习 LLM API 调用与与 Python 自动化的初次实践，代码结构相对简单，可能存在较多 bug 或不完善之处。欢迎提 Issue 或 PR 反馈问题，我会不断改进。感谢理解与支持！

## ✨ 功能特性

- ✅ **自动天气采集** – 获取实时天气 + 未来 24/72/168 小时逐小时预报  
- 💾 **双重存储** – SQLite 数据库（结构化查询）+ JSON 归档（便于 LLM 直接读取）  
- 🤖 **LLM 智能分析** – 接入 DeepSeek / OpenAI 等大语言模型，生成每日生活建议（穿衣、带伞、运动、祝福语等）  
- 📧 **邮件推送** – 发送 HTML 邮件，支持单用户 / 多用户批量发送  
- 🗂️ **多城市支持** – 可为不同城市多用户分别推送天气提醒


## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/yuanyusung/YusoWeather.git
cd YusoWeather
```
### 2. 安装依赖
```bash
pip install -r requirements.txt
```
### 3. 配置环境变量
复制 .env.example 为 .env，并填入真实信息：
```bash
cp .env.example .env
vim .env   # 或使用任意编辑器
```
必填项：
- QWEATHER_KEY – [和风天气](https://dev.qweather.com)开发 API 密钥（免费版即可）
- LLM_API_KEY – DeepSeek / OpenAI API Key
💡 推荐使用 DeepSeek 作为 LLM，性价比高，LLM_BASE_URL=https://api.deepseek.com，- - LLM_MODEL=deepseek-v4-flash。
- SMTP_USER + SMTP_PASSWORD – 你的邮箱（QQ 邮箱需使用授权码）

### 4. 运行单一城市
```python
# 采集武汉的天气，生成分析，发送到指定邮箱
python run.py --city 武汉 --city-id 101200101 --email your@qq.com
```
参数说明：
- --city：城市名称（用于数据库和邮件显示）
- --city-id：和风城市 ID（[查询对照表](https://github.com/qwd/LocationList)）
- --email：收件邮箱，多个用逗号分隔
- --skip-collect：跳过采集，仅使用已有数据分析和发送
- --forecast-hours：预报时长（24h / 72h / 168h），默认 24h

### 4. 多城市多用户批量发送
准备一个 CSV 文件（例如 cities.csv），格式如下：
```csv
city_name,city_id,emails
武汉,101200101,user1@qq.com,user2@qq.com
上海,101020100,shanghai@example.com
北京,101010100,beijing@qq.com
```
然后执行：
```bash
python batch_send.py --file cities.csv
```
参数说明：
- --skip-collect – 跳过采集（适合已有数据、仅重发）
- --forecast-hours – 预报时长

## ⚙️ 环境变量完整说明

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `QWEATHER_API_HOST` | 和风 API 地址 | `https://api.qweather.com` |
| `QWEATHER_KEY` | 和风密钥（必填） | `xxxxxxxxxxxxxxxx` |
| `LLM_API_KEY` | LLM API 密钥（必填） | `sk-xxxx` |
| `LLM_BASE_URL` | LLM 接口地址 | `https://api.deepseek.com` |
| `LLM_MODEL` | 模型名称 | `deepseek-chat` |
| `LLM_TEMP` | 生成温度 | `0.3` |
| `SMTP_SERVER` | 邮件服务器 | `smtp.qq.com` |
| `SMTP_PORT` | 端口 | `587` |
| `SMTP_USER` | 登录账号 | `your@qq.com` |
| `SMTP_PASSWORD` | 密码/授权码 | `xxxxxxxxxxxx` |
| `SENDER_NAME` | 发件人显示名 | `鱼松天气` |
| `SENDER_EMAIL` | 发件邮箱 | `your@qq.com` |
| `DATA_DIR` | 数据存储目录 | `./data` |

## 📦 项目结构
weather-llm/  
├── .env.example                 # 环境变量模板  
├── .gitignore  
├── README.md  
├── requirements.txt  
├── run.py                       # 单城市入口（采集+分析+发送）  
├── batch_send.py                # 多城市批量发送入口  
├── weather_pkg/  
│   ├── __init__.py  
│   ├── config.py                # 统一配置（从 .env 加载）  
│   ├── collector.py             # 和风天气 API 采集、转换、入库  
│   ├── analyzer.py              # 构建 prompt + 调用 LLM 生成分析文本  
│   ├── notifier.py              # HTML 邮件生成与 SMTP 发送  
│   └── database.py              # SQLite 多城市封装  
└── data/                        # 运行时生成（自动创建）  
    ├── weather.db               # SQLite 数据库  
    ├── archive/                 # JSON 归档按日期分目录  
    └── latest_analysis_*.txt    # 最近一次分析文本缓存  

## 📬 联系方式

如有问题、建议或合作意向，欢迎联系：

- **项目作者**：鱼松
- **邮箱**：yusong.yuan@cug.edu.cn
- **GitHub**：[https://github.com/yuanyusung/YusoWeather](https://github.com/yuanyusung/YusoWeather)
- **Issue反馈**：[提交 Issue](https://github.com/yuanyusung/YusoWeather/issues)

> 欢迎 Star ⭐ 和 Fork，也期待你的 Pull Request～




