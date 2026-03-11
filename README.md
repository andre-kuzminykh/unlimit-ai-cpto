# Process-to-Agent Telegram Bot

A Telegram bot that turns a text or voice description of a business process into a concise executive summary plus a premium HTML report containing AS-IS, TO-BE, PRD, and Architecture for an AI-agentized version of the process.

## Features

- **Text input**: Send any business process description as text
- **Voice input**: Send a voice message — automatically transcribed
- **Single response**: One concise Telegram message with process title, summary, automation split, and HTML link
- **Premium HTML report**: Glassmorphism + Aurora UI with tabs for AS-IS, TO-BE, PRD, and Architecture
- **Mermaid diagrams**: Auto-generated and rendered process flow diagrams
- **English output**: All outputs in English regardless of input language

## Setup

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API Key

### Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:
- `TELEGRAM_BOT_TOKEN` — Your Telegram bot token
- `OPENAI_API_KEY` — Your OpenAI API key
- `OPENAI_MODEL` — Model to use (default: `gpt-4o`)
- `REPORT_BASE_URL` — Public URL where reports are served
- `REPORT_SERVER_PORT` — Port for the report HTTP server (default: `8080`)

### Run Locally

```bash
pip install -r requirements.txt
python main.py
```

### Run with Docker

```bash
docker compose up --build
```

## Architecture

| Layer | Components |
|-------|-----------|
| **AI Services** | OpenAI (process analysis), Whisper (voice transcription), Mermaid.ink (diagram rendering) |
| **Application** | Telegram bot, orchestration pipeline, HTML generator, report server |
| **Data** | SQLite (job tracking), file system (reports, diagrams) |
| **Infrastructure** | Docker, aiohttp static server |

## How It Works

1. User sends text or voice message to Telegram bot
2. Voice messages are transcribed via OpenAI Whisper
3. OpenAI generates full structured analysis (AS-IS, TO-BE, PRD, Architecture)
4. Mermaid diagrams are rendered to images via mermaid.ink
5. Premium HTML report is generated with all content embedded
6. Bot sends one final Telegram message with summary + report link
