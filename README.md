# Embodied AI Daily Paper Bot

Automatically fetch the latest embodied AI / VLA papers from arXiv, classify them, deep-read the top candidates, and push up to 3 recommended papers to your messaging platform every day at 10:30 (Beijing time).

## Features

- Daily arXiv crawling for embodied AI / VLA papers
- LLM-based classification (method / task / hot research direction)
- Deep reading with DeepSeek / Kimi API
- Top-3 paper selection with recommendation reasons in Chinese
- Multi-channel push: PushPlus (personal WeChat), Feishu (Lark), Kimi Claw
- Cross-platform: macOS and Linux
- SQLite persistence for deduplication and history
- Docker deployment support

## Project Structure

```
embodied-paper-bot/
├── config/
│   └── config.yaml          # Configuration (queries, API keys, schedule)
├── src/                     # Core source code
├── scripts/                 # Daily fetch and push scripts
├── data/                    # SQLite database
├── logs/                    # Log files
├── systemd/                 # Linux systemd service template
├── launchd/                 # macOS launchd plist template
├── docker/                  # Dockerfile
├── docker-compose.yml       # Docker Compose deployment
├── requirements.txt
├── run.py                   # Unified cross-platform entry point
├── README.md                # English documentation
└── README_CN.md             # Chinese documentation
```

## Quick Start

### 1. Prepare API Keys

Before running, you need:

- **DeepSeek API Key**: get from [DeepSeek](https://platform.deepseek.com/) (or Kimi from [Moonshot AI](https://platform.moonshot.cn/))
- **PushPlus Token** (optional): follow the "PushPlus 推送加" WeChat official account
- **Feishu Webhook URL** (optional): add a custom bot in a Feishu group

### 2. Install Dependencies

```bash
cd embodied-paper-bot
python3 -m venv .venv
source .venv/bin/activate        # works on both macOS and Linux
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file at the project root:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
PUSHPLUS_TOKEN=your_pushplus_token
FEISHU_WEBHOOK_URL=your_feishu_webhook_url
```

### 4. Select Push Channel

Edit `config/config.yaml`:

```yaml
push:
  channel: feishu               # pushplus / feishu / claw
  feishu_webhook_url: ${FEISHU_WEBHOOK_URL}
```

### 5. Run the Scheduler

```bash
python run.py
```

This starts a background scheduler that runs:

- `10:00` - fetch, classify, and deep-read papers
- `10:30` - push the top 3 papers to your messaging platform

## Docker Deployment

The recommended way for long-term 24/7 operation is Docker.

### Build and Run

```bash
cd embodied-paper-bot
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f
```

### Stop

```bash
docker-compose down
```

### Update After Code Changes

```bash
docker-compose down
docker-compose up -d --build
```

## Configuration

Edit `config/config.yaml` to customize queries, tags, schedule, etc.

```yaml
arxiv:
  queries:
    - "vision-language-action robot"
    - "robotic manipulation learning"
    # add more...
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

## Push Channels

### PushPlus (Personal WeChat)

1. Follow the "PushPlus 推送加" WeChat official account
2. Get your token
3. Set `channel: pushplus` and `pushplus_token` in `config.yaml`

### Feishu (Lark)

1. In a Feishu group, go to **Settings -> Bots -> Custom Bot**
2. Copy the webhook URL
3. Set `channel: feishu` and `feishu_webhook_url` in `config.yaml`

### Kimi Claw (Local Desktop)

Kimi Claw's local messages API is available only when **Kimi Desktop** is running on the same machine.

```yaml
push:
  channel: claw
  claw_webhook_url: "http://localhost:18789/api/sessions/main/messages"
  claw_payload_template: '{"role":"user","content":"{title}\n\n{content}"}'
```

> **Note**: If you run this bot on a remote server but Kimi Desktop is on your local laptop, `localhost:18789` will not work. Use PushPlus/Feishu instead, or set up an SSH port forward from your laptop to the server.

## Other Deployment Methods

### Linux systemd

```bash
sudo cp systemd/embodied-paper-bot.service /etc/systemd/system/
# Edit /etc/systemd/system/embodied-paper-bot.service and replace YOUR_USERNAME
sudo systemctl daemon-reload
sudo systemctl enable embodied-paper-bot
sudo systemctl start embodied-paper-bot
```

### macOS launchd

```bash
cp launchd/com.embodiedpaperbot.plist ~/Library/LaunchAgents/
# Edit the plist to set the correct paths
launchctl load ~/Library/LaunchAgents/com.embodiedpaperbot.plist
launchctl start com.embodiedpaperbot
```

### tmux (Quick Temporary)

```bash
tmux new -s paperbot
cd embodied-paper-bot
source .venv/bin/activate
python run.py
# Press Ctrl+B then D to detach
```

## Notes

- Keep your computer / server powered on and online between 10:00 and 10:30, or deploy to a cloud server.
- The first run may consume more API tokens because it has no history. Subsequent runs only process new papers.
- All source code comments are in English as requested.
- Do not commit `.env` or `data/*.db` to GitHub. They are already listed in `.gitignore`.
