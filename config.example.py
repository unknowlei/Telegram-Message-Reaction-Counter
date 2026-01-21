"""
Telegram API 配置文件

使用前请按以下步骤获取 API 凭证：
1. 访问 https://my.telegram.org
2. 使用你的手机号登录
3. 点击 "API development tools"
4. 填写应用信息并创建
5. 将获得的 api_id 和 api_hash 填入下方
6. 将此文件重命名为 config.py
"""

# ============================================
# Telegram API 凭证（必填）
# ============================================

# API ID - 在 my.telegram.org 获取的数字 ID
API_ID = 12345678  # 替换为你的 api_id

# API Hash - 在 my.telegram.org 获取的字符串
API_HASH = "your_api_hash_here"  # 替换为你的 api_hash

# 会话名称 - 用于保存登录状态（不用管）
SESSION_NAME = "telegram_session"


# ============================================
# 命令行模式默认设置
# 注意：以下配置主要用于命令行模式 (main.py)
# 如果使用 Web 界面 (web_app.py)，这些都可以在界面上配置
# ============================================

# 目标频道/群组（支持以下格式）
# - 用户名: "channel_name" 或 "@channel_name"
# - 邀请链接: "https://t.me/+xxxxx"
# - 频道 ID: -1001234567890
# 【Web 界面可配置】
TARGET_CHANNEL = "your_channel"  # 替换为你要统计的频道

# 要获取的最大消息数量
# 注意：数量越大，耗时越长
MAX_MESSAGES = 1000

# 最小反应数阈值 - 低于此数量的消息将被过滤
# 【Web 界面可配置】
MIN_REACTIONS = 5

# 是否只统计包含媒体文件的消息
# 【Web 界面可配置】
MEDIA_ONLY = True


# ============================================
# 系统设置（一般无需修改）
# ============================================

# 每批次获取消息后的延迟（秒）- 用于避免触发速率限制
BATCH_DELAY = 1.0

# 每批次处理的消息数量
BATCH_SIZE = 100


# ============================================
# 输出设置（仅命令行模式使用）
# ============================================

# 输出目录
OUTPUT_DIR = "output"

# 输出文件名（不含扩展名）
OUTPUT_FILENAME = "top_messages"

# 输出格式：可选 "json", "csv", "both"
OUTPUT_FORMAT = "both"

# 在终端显示的 Top N 消息数量
TOP_N_DISPLAY = 20