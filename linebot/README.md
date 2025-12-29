# Lab8: Linebot 結合 AI Agent 系統

這是一個結合 LINE Bot 與 Multi-Agent Handoff 系統的範例，展示如何將 AI Agent 系統整合到 LINE 聊天機器人中。

## 系統架構

```
LINE 使用者
    │
    ▼
LINE Platform
    │
    ▼ (Webhook)
┌─────────────────────────────────────────────┐
│             FastAPI Server                   │
│                                              │
│  ┌─────────────────────────────────────┐    │
│  │     Multi-Agent Handoff System      │    │
│  │                                     │    │
│  │  ┌─────────────┐                    │    │
│  │  │TriageAgent  │ ← 問題分流          │    │
│  │  └──────┬──────┘                    │    │
│  │         │                           │    │
│  │   ┌─────┼─────┐                     │    │
│  │   │     │     │                     │    │
│  │   ▼     ▼     ▼                     │    │
│  │ ┌───┐ ┌───┐ ┌────────┐             │    │
│  │ │HR │ │IT │ │Compliance│            │    │
│  │ └───┘ └───┘ └────────┘             │    │
│  │                                     │    │
│  └─────────────────────────────────────┘    │
│                                              │
└─────────────────────────────────────────────┘
```

## Agent 說明

| Agent | 職責 | 處理範圍 |
|-------|------|----------|
| TriageAgent | 問題分流 | 分析問題類別，轉交給對應專責代理 |
| HRAgent | 人資支援 | 薪資、福利、假期、考勤、招聘、培訓 |
| ITAgent | IT 支援 | 帳號、系統、軟硬體、網路、資安 |
| ComplianceAgent | 合規支援 | 法規、政策、稽核、風控、資料保護 |

## 環境設定

### 1. 建立 LINE Messaging API Channel

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)
2. 建立新的 Provider（或使用現有的）
3. 建立新的 Messaging API Channel
4. 在 Channel 設定頁面取得：
   - Channel Secret（Basic settings）
   - Channel Access Token（Messaging API）

### 2. 設定環境變數

在專案根目錄的 `.env` 檔案中加入：

```env
# LINE Bot 設定
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
LINE_CHANNEL_SECRET=your_channel_secret

# OpenAI API 設定（已有）
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
```

### 3. 安裝依賴套件

```bash
pip install -r requirements.txt
```

需要的新套件：
- `line-bot-sdk>=3.0.0`：LINE Messaging API SDK
- `fastapi>=0.100.0`：Web 框架
- `uvicorn>=0.20.0`：ASGI 伺服器

## 啟動服務

### 本地開發

```bash
# 啟動伺服器（預設 port 8000）
python linebot/linebot_agent.py

# 或指定 port
PORT=8080 python linebot/linebot_agent.py
```

### 使用 ngrok 進行本地測試

由於 LINE Webhook 需要 HTTPS 公開網址，開發時可使用 ngrok：

```bash
# 安裝 ngrok（如果尚未安裝）
# https://ngrok.com/download

# 啟動 ngrok
ngrok http 8000
```

將 ngrok 提供的 HTTPS URL 設定到 LINE Developers Console：
- Webhook URL: `https://xxxx.ngrok.io/webhook`

## 測試

1. 在 LINE App 中加入你的 Bot 為好友
2. 傳送訊息測試，例如：
   - 「請問特休假怎麼計算？」→ 會由 HRAgent 回答
   - 「我的電腦連不上 VPN」→ 會由 ITAgent 回答
   - 「公司的保密協議規定是什麼？」→ 會由 ComplianceAgent 回答

## API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 健康檢查 |
| `/webhook` | POST | LINE Webhook 接收端點 |

## 部署到 Azure Web App

### 方法一：使用 Azure CLI 部署

#### 1. 前置準備

確保已安裝 [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)

```bash
# 登入 Azure
az login

# 設定訂閱（如有多個訂閱）
az account set --subscription "your-subscription-name"
```

#### 2. 建立資源群組和 App Service Plan

```bash
# 建立資源群組
az group create --name rg-linebot-agent --location eastasia

# 建立 App Service Plan (Linux, Python)
az appservice plan create \
    --name plan-linebot-agent \
    --resource-group rg-linebot-agent \
    --sku B1 \
    --is-linux
```

#### 3. 建立 Web App

```bash
# 建立 Web App
az webapp create \
    --name your-linebot-app-name \
    --resource-group rg-linebot-agent \
    --plan plan-linebot-agent \
    --runtime "PYTHON:3.11"
```

#### 4. 設定環境變數

```bash
az webapp config appsettings set \
    --name your-linebot-app-name \
    --resource-group rg-linebot-agent \
    --settings \
    LINE_CHANNEL_ACCESS_TOKEN="your_token" \
    LINE_CHANNEL_SECRET="your_secret" \
    OPENAI_API_KEY="your_openai_key" \
    OPENAI_MODEL="gpt-4o"
```

#### 5. 設定啟動命令

```bash
az webapp config set \
    --name your-linebot-app-name \
    --resource-group rg-linebot-agent \
    --startup-file "gunicorn -w 4 -k uvicorn.workers.UvicornWorker linebot_agent:app --bind 0.0.0.0:8000"
```

#### 6. 部署程式碼

從 `linebot` 目錄部署：

```bash
cd linebot

# 壓縮並部署
az webapp deploy \
    --name your-linebot-app-name \
    --resource-group rg-linebot-agent \
    --src-path . \
    --type zip
```

或使用 Git 部署：

```bash
# 設定本地 Git 部署
az webapp deployment source config-local-git \
    --name your-linebot-app-name \
    --resource-group rg-linebot-agent

# 取得部署 URL 後，加入 remote 並 push
git remote add azure <deployment-url>
git push azure main
```

### 方法二：使用 VS Code Azure 擴充功能

1. 安裝 [Azure App Service 擴充功能](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azureappservice)
2. 在 VS Code 中登入 Azure
3. 右鍵點擊 `linebot` 資料夾 → Deploy to Web App
4. 依照提示完成部署
5. 在 Azure Portal 設定環境變數

### 部署後設定

#### 1. 取得 Web App URL

部署完成後，你的 Web App URL 為：
```
https://your-linebot-app-name.azurewebsites.net
```

#### 2. 設定 LINE Webhook URL

前往 [LINE Developers Console](https://developers.line.biz/console/)：
1. 選擇你的 Channel
2. 進入 Messaging API 頁籤
3. 設定 Webhook URL：`https://your-linebot-app-name.azurewebsites.net/webhook`
4. 開啟 Use webhook
5. 點擊 Verify 測試連線

#### 3. 檢查日誌

```bash
# 即時查看日誌
az webapp log tail \
    --name your-linebot-app-name \
    --resource-group rg-linebot-agent
```

### Azure 部署檔案說明

| 檔案 | 說明 |
|------|------|
| `requirements.txt` | Python 依賴套件清單 |
| `startup.txt` | Azure Web App 啟動命令參考 |
| `linebot_agent.py` | 主程式 |

## 其他部署方式

### 使用 Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "linebot_agent:app", "--bind", "0.0.0.0:8000"]
```

### 其他雲端平台

- **Heroku**：設定 Procfile 和環境變數
- **Google Cloud Run**：使用 Docker 映像
- **AWS Lambda**：搭配 API Gateway

## 注意事項

1. **Webhook URL 必須是 HTTPS**：LINE Platform 只接受 HTTPS 的 Webhook URL
2. **回應時間限制**：LINE 要求在一定時間內回應，複雜查詢可能需要優化
3. **API 費用**：注意 OpenAI API 和 LINE Messaging API 的使用量和費用
4. **安全性**：確保環境變數不要提交到版本控制系統

## 相關資源

- [LINE Messaging API 文件](https://developers.line.biz/en/docs/messaging-api/)
- [line-bot-sdk-python](https://github.com/line/line-bot-sdk-python)
- [FastAPI 文件](https://fastapi.tiangolo.com/)
- [LangGraph 文件](https://langchain-ai.github.io/langgraph/)
