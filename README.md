# 📊 Telegram Reaction Counter

一个用于统计 Telegram 频道/群组消息反应的工具，帮助你找出最热门的内容。

## ✨ 功能特点

- 🔐 **安全登录**：通过 Telegram 手机验证码登录，支持两步验证
- 📢 **频道分析**：分析你加入的任何频道或群组
- 🎭 **表情筛选**：选择特定表情进行统计排序
- 📅 **时间范围**：支持自定义时间范围（3天/7天/30天/自定义）
- 🔗 **快速跳转**：点击直接在 Telegram 中打开消息
- 📂 **历史记录**：本地保存分析结果，随时查看
- 📤 **数据导出**：支持导出为 JSON 格式

## 🚀 快速开始

### Windows 用户（推荐）

**双击 `start.bat` 即可一键启动！**

首次运行会自动：
1. ✅ 检查 Python 环境
2. ✅ 创建虚拟环境
3. ✅ 安装所有依赖
4. ✅ 引导你获取并输入 Telegram API 凭证
5. ✅ 启动 Web 应用并打开浏览器

之后每次运行只需双击 `start.bat`，会自动启动并打开浏览器。

### 手动安装

<details>
<summary>点击展开手动安装步骤</summary>

#### 1. 获取 Telegram API 凭证

1. 访问 [https://my.telegram.org](https://my.telegram.org)
2. 使用你的手机号登录
3. 点击 "API development tools"
4. 填写应用信息并创建
5. 记录获得的 `api_id` 和 `api_hash`

#### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/your-username/telegram-reaction-counter.git
cd telegram-reaction-counter

# 安装依赖
pip install -r requirements.txt
```

#### 3. 配置

```bash
# 复制配置模板
cp config.example.py config.py

# 编辑 config.py，填入你的 API 凭证
# API_ID = 你的API_ID
# API_HASH = "你的API_HASH"
```

#### 4. 运行

```bash
python web_app.py
```

然后在浏览器中打开 [http://localhost:5000](http://localhost:5000)

</details>

## 📱 使用方法

1. **登录**：输入手机号，接收验证码并登录
2. **选择频道**：输入频道用户名或从列表中选择
3. **设置参数**：
   - 选择时间范围
   - 选择要统计的表情（可多选）
   - 设置最小反应数阈值
   - 选择消息类型（全部/仅媒体）
4. **开始分析**：点击"开始分析"按钮
5. **查看结果**：消息按选中表情数量排序显示

## 📁 项目结构

```
telegram-reaction-counter/
├── web_app.py          # Web 应用主程序
├── fetcher.py          # Telegram 消息获取模块
├── analyzer.py         # 数据分析模块
├── exporter.py         # 数据导出模块
├── config.py           # 配置文件（需自行创建）
├── config.example.py   # 配置文件模板
├── requirements.txt    # Python 依赖
├── templates/
│   └── index.html      # Web 前端页面
└── output/             # 导出文件目录
```

## ⚠️ 注意事项

- 请勿将 `config.py` 提交到公开仓库，其中包含你的 API 凭证
- Session 文件（`*.session`）包含登录信息，请妥善保管
- 请遵守 Telegram 的使用条款，避免滥用 API

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！