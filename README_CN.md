# 具身智能每日论文推送机器人

每天自动从 arXiv 抓取具身智能（Embodied AI / VLA）方向的最新论文，自动分类、精读，并挑选最多 3 篇最值得读的论文，于每天北京时间 10:30 推送到你的消息平台。

## 功能特性

- 每日自动抓取 arXiv 具身智能 / VLA 论文
- 基于大模型的多维度分类（方法 / 任务 / 热点方向）
- 调用 DeepSeek / Kimi API 进行论文精读
- 每日精选最多 3 篇，推荐理由用中文输出
- 多平台推送：PushPlus（个人微信）、飞书机器人、Kimi Claw
- 跨平台支持：macOS / Linux
- SQLite 持久化存储，自动去重
- 支持 Docker 一键部署

## 项目结构

```
embodied-paper-bot/
├── config/
│   └── config.yaml          # 配置文件（查询词、API key、推送时间）
├── src/                     # 核心源码
├── scripts/                 # 每日抓取和推送脚本
├── data/                    # SQLite 数据库
├── logs/                    # 日志文件
├── systemd/                 # Linux 系统服务模板
├── launchd/                 # macOS 后台服务模板
├── docker/                  # Dockerfile
├── docker-compose.yml       # Docker Compose 部署文件
├── requirements.txt
├── run.py                   # 统一跨平台入口
├── README.md                # 英文文档
└── README_CN.md             # 中文文档
```

## 快速开始

### 1. 准备 API Key

运行前需要准备：

- **DeepSeek API Key**：从 [DeepSeek 开放平台](https://platform.deepseek.com/) 获取（也可用 [Kimi](https://platform.moonshot.cn/)）
- **PushPlus Token**（可选）：微信关注「PushPlus 推送加」公众号获取
- **飞书机器人 Webhook 地址**（可选）：在飞书群里添加自定义机器人

### 2. 安装依赖

```bash
cd embodied-paper-bot
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux 通用
pip install -r requirements.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=你的_deepseek_api_key
PUSHPLUS_TOKEN=你的_pushplus_token
FEISHU_WEBHOOK_URL=你的_飞书_webhook_地址
```

### 4. 选择推送渠道

编辑 `config/config.yaml`：

```yaml
push:
  channel: feishu               # pushplus / feishu / claw
  feishu_webhook_url: ${FEISHU_WEBHOOK_URL}
```

### 5. 启动调度器

```bash
python run.py
```

启动后会自动在后台调度：

- `10:00`：抓取 → 分类 → 精读论文
- `10:30`：推送当日 Top 3 论文到指定消息平台

## Docker 部署（推荐）

长期 24/7 运行推荐使用 Docker。

### 构建并运行

```bash
cd embodied-paper-bot
docker-compose up -d
```

### 查看日志

```bash
docker-compose logs -f
```

### 停止服务

```bash
docker-compose down
```

### 代码更新后重新构建

```bash
docker-compose down
docker-compose up -d --build
```

## 配置说明

编辑 `config/config.yaml` 可自定义查询词、标签、推送时间等。

```yaml
arxiv:
  queries:
    - "vision-language-action robot"
    - "robotic manipulation learning"
    # 可继续添加...
  max_results_per_query: 30
  candidate_pool_size: 12

llm:
  provider: deepseek
  api_key: ${DEEPSEEK_API_KEY}
  model: deepseek-v4-pro
  base_url: https://api.deepseek.com/v1

push:
  max_papers_per_day: 3
  channel: feishu
  feishu_webhook_url: ${FEISHU_WEBHOOK_URL}

schedule:
  fetch_time: "10:00"
  push_time: "10:30"
  timezone: Asia/Shanghai
```

## 推送渠道

### PushPlus（个人微信）

1. 微信关注「PushPlus 推送加」公众号
2. 注册后获取 token
3. 设置 `channel: pushplus` 并填写 `pushplus_token`

### 飞书机器人

1. 打开飞书群，进入 **设置 → 群机器人 → 添加机器人**
2. 选择「自定义机器人」，复制 Webhook 地址
3. 设置 `channel: feishu` 并填写 `feishu_webhook_url`

### Kimi Claw（本地桌面端）

Kimi Claw 的本地消息 API 需要 **Kimi Desktop 桌面版** 在运行，并且和 bot 在同一台机器上。

```yaml
push:
  channel: claw
  claw_webhook_url: "http://localhost:18789/api/sessions/main/messages"
  claw_payload_template: '{"role":"user","content":"{title}\n\n{content}"}'
```

> **注意**：如果你在远程服务器上运行 bot，而 Kimi Desktop 在本地笔记本上，`localhost:18789` 是无法访问的。请改用 PushPlus / 飞书，或者配置 SSH 端口转发。

## 其他部署方式

### Linux systemd

```bash
sudo cp systemd/embodied-paper-bot.service /etc/systemd/system/
# 编辑 /etc/systemd/system/embodied-paper-bot.service，把 YOUR_USERNAME 改成你的用户名
sudo systemctl daemon-reload
sudo systemctl enable embodied-paper-bot
sudo systemctl start embodied-paper-bot
```

### macOS launchd

```bash
cp launchd/com.embodiedpaperbot.plist ~/Library/LaunchAgents/
# 编辑 plist 文件，填入正确的路径
launchctl load ~/Library/LaunchAgents/com.embodiedpaperbot.plist
launchctl start com.embodiedpaperbot
```

### tmux（临时后台）

```bash
tmux new -s paperbot
cd embodied-paper-bot
source .venv/bin/activate
python run.py
# 按 Ctrl+B 再按 D 退出会话
```

## 注意事项

- 保持电脑 / 服务器在每天 10:00-10:30 期间开机联网，或部署到云服务器。
- 首次运行会消耗较多 API token，因为历史库为空；后续每天只处理新论文。
- 所有源码注释已按要求使用英文。
- 请勿将 `.env` 或 `data/*.db` 提交到 GitHub，它们已在 `.gitignore` 中排除。
