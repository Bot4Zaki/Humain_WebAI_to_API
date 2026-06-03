# Humain WebAI to API Proxy

This is a local Python proxy server that wraps the [Humain AI (ALLaM)](https://chat.humain.ai/) web chat interface and exposes it as a standard OpenAI-compatible Streaming API.

It is designed to seamlessly integrate Humain's ALLaM model into Agentic IDEs like **OpenClaw**, allowing you to use ALLaM as a coding assistant with full memory retention, dynamic web search, and perfect timeout management.

## Features
- **100% OpenAI API Compatible**: Exposes `/v1/chat/completions`.
- **True Memory**: Re-uses native Humain `conversation_id`s, ensuring flawless memory retention across multi-turn chats.
- **Smart Web Search**: Detects phrases like `"search the web"`, `"google"`, or `"latest news"` in your prompt and automatically triggers Humain's web search tool. It streams back `*(Searching the web for: ...)*` to your UI so you're never waiting blindly.
- **Agent-Ready Timings**: Instantly yields an initialization chunk back to the IDE to defeat the strict 10-second streaming timeouts commonly found in Agentic AI clients.
- **Auto Token Refresh**: Runs a persistent, headless Playwright browser instance in the background to automatically refresh the short-lived API tokens every 30 minutes.

## Requirements
- Python 3.9+
- Chrome/Chromium installed (for Playwright)

## Installation

1. Clone this repository.
2. Create a virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## First-Time Setup (Login)

You need to authorize the proxy to use your Humain account. Because the proxy uses a persistent Playwright browser profile, you only need to do this once (or whenever your underlying Humain session cookie expires, usually every few weeks).

Run the login script:
```bash
python login.py
```
This will open a visible Chrome window. Log in to `chat.humain.ai`. Once you are fully logged in and can see the chat interface, **close the browser window**. Your session is now securely saved locally.

## Running the Proxy

Start the proxy server:
```bash
python run.py
```
The server will start on `http://127.0.0.1:8100/v1`.

## Using with OpenClaw

Configure OpenClaw to point to your local proxy:
```bash
export OPENAI_API_BASE="http://127.0.0.1:8100/v1"
export OPENAI_API_KEY="dummy"
```

## Security & Credentials
- **No Hardcoded Secrets**: This codebase does NOT contain any API keys, usernames, passwords, or hardcoded tokens.
- **Local Storage Only**: All authentication is done securely by Playwright into a local folder named `browser_data`. This folder is excluded via `.gitignore` to ensure your session cookies are never accidentally pushed to GitHub.
