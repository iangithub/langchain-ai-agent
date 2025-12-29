# Lab2: Single-Agent 行銷文案生成器（create_agent 方式）

## 概述

這是一個 **Single-Agent** 範例，與 Lab1 功能相同，但改用 **LangChain 1.x 的 `create_agent`** 方式實作。

`create_agent` 是 LangChain 1.x 推出的新標準 API，簡化了 Agent 的建立過程，並支援 Tools 和 Middleware 的整合。

本範例同時展示兩種回應模式：
- **invoke**: 一次性取得完整回應
- **stream**: 串流式逐步輸出，即時顯示生成過程

## Lab1 vs Lab2 差異

| 項目 | Lab1 | Lab2 |
|------|------|------|
| 實作方式 | LCEL Chain | create_agent |
| 語法 | `prompt \| llm \| output_parser` | `create_agent(model, tools, ...)` |
| 工具支援 | 不支援 | 原生支援 Tools |
| 擴展性 | 需手動串接 | 支援 Middleware |
| 適用場景 | 簡單線性流程 | 需要工具呼叫的任務 |

## 架構說明

```
┌─────────────────────────────────────────────────────────┐
│              create_agent 架構                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   [使用者輸入]                                           │
│        │                                                │
│        ▼                                                │
│   ┌─────────────────────────────────────┐              │
│   │           create_agent              │              │
│   │  ┌─────────┐  ┌─────────────────┐  │              │
│   │  │  Model  │  │     Tools       │  │              │
│   │  │ (LLM)   │  │ - marketing_copy│  │              │
│   │  └─────────┘  └─────────────────┘  │              │
│   │         ┌───────────────┐          │              │
│   │         │ System Prompt │          │              │
│   │         └───────────────┘          │              │
│   └─────────────────────────────────────┘              │
│                      │                                  │
│                      ▼                                  │
│               [行銷文案輸出]                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## create_agent 核心概念

### 基本用法

```python
from langchain.agents import create_agent
from langchain.tools import tool

@tool
def my_tool(param: str) -> str:
    """工具描述"""
    return f"處理結果: {param}"

agent = create_agent(
    model="gpt-4o",
    tools=[my_tool],
    system_prompt="你是一個助手..."
)

result = agent.invoke({
    "messages": [
        {"role": "user", "content": "請幫我..."}
    ]
})
```

### 主要參數

| 參數 | 說明 |
|------|------|
| `model` | 模型名稱或模型實例 |
| `tools` | 工具列表，Agent 可呼叫的功能 |
| `system_prompt` | 系統提示詞，定義 Agent 角色 |
| `middleware` | 中介層，用於攔截和處理請求 |

## 串流模式 (Stream)

串流模式允許即時輸出 Agent 生成的內容，而不是等待完整回應。這對於長文本生成特別有用。

### invoke vs stream 比較

| 方法 | 說明 | 適用場景 |
|------|------|----------|
| `invoke()` | 等待完整回應後返回 | 需要完整結果的後處理 |
| `stream()` | 逐步產出回應內容 | 即時顯示、改善使用者體驗 |

### Stream 用法 (stream_mode="messages")

使用 `stream_mode="messages"` 進行 token 級別的串流，即時顯示生成過程：

```python
# 使用 stream_mode="messages" 進行 token 級別串流
# 返回格式為 (message_chunk, metadata) 元組
for message_chunk, metadata in agent.stream(
    {"messages": [{"role": "user", "content": "..."}]},
    stream_mode="messages"
):
    if message_chunk.content:
        # 即時輸出，不換行
        print(message_chunk.content, end="", flush=True)
```

### Stream 詳細模式（含 metadata）

使用 `stream_mode="messages"` 同時顯示 metadata 資訊：

```python
# 串流並顯示 metadata 資訊
current_node = None

for message_chunk, metadata in agent.stream(
    {"messages": [{"role": "user", "content": "..."}]},
    stream_mode="messages"
):
    # 顯示節點切換資訊
    node_name = metadata.get("langgraph_node", "unknown")
    if node_name != current_node:
        current_node = node_name
        print(f"\n[節點: {node_name}]")

    # 即時輸出內容
    if message_chunk.content:
        print(message_chunk.content, end="", flush=True)

    # 顯示工具呼叫
    if hasattr(message_chunk, "tool_call_chunks") and message_chunk.tool_call_chunks:
        for tc_chunk in message_chunk.tool_call_chunks:
            if tc_chunk.get("name"):
                print(f"\n[工具: {tc_chunk.get('name')}]")
```

### Metadata 常用欄位

| 欄位 | 說明 |
|------|------|
| `langgraph_node` | 目前執行的節點名稱 |
| `langgraph_step` | 執行步驟編號 |
| `langgraph_triggers` | 觸發此節點的來源 |

## 使用技術

- **LangChain 1.x**: `create_agent` 新標準 API
- **@tool 裝飾器**: 定義 Agent 可使用的工具
- **init_chat_model**: 統一的模型初始化方式

## 安裝與設定

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

複製 `.env.example` 為 `.env`，並填入你的 API 金鑰：

```bash
cp .env.example .env
```

編輯 `.env` 檔案：

```
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o
```

### 3. 執行程式

```bash
python lab2/lab2_single_agent.py
```

## 程式碼結構

```
lab2/
├── lab2_single_agent.py  # 主程式
└── README.md             # 說明文件
```

### 主要函數

- `load_environment()`: 載入環境變數
- `generate_marketing_copy()`: 行銷文案生成工具（@tool）
- `create_marketing_agent()`: 使用 create_agent 建立 Agent
- `run_marketing_agent()`: 使用 invoke 執行 Agent
- `stream_marketing_agent()`: 使用 stream 串流執行 Agent
- `stream_marketing_agent_detailed()`: 串流執行並顯示詳細事件
- `main()`: 程式入口（提供模式選擇）

## 輸出範例

```
============================================================
Lab2: Single-Agent 行銷文案生成器
（使用 LangChain 1.x create_agent 方式）
============================================================

✓ 環境變數載入成功

------------------------------------------------------------
使用範例產品資訊生成文案...
------------------------------------------------------------
產品名稱：智能空氣清淨機 AirPure Pro
產品特點：HEPA 13級濾網、智能空氣品質偵測...
目標受眾：注重生活品質的都市家庭...
行銷目標：提升品牌知名度，促進線上購買轉換
------------------------------------------------------------

請選擇執行模式：
1. 一般模式 (invoke) - 等待完整回應
2. 串流模式 (stream) - 即時顯示生成過程
3. 串流詳細模式 (stream detailed) - 顯示詳細事件資訊

請輸入選項 (1/2/3，預設為 2): 2

正在執行 Agent 生成行銷文案（串流模式）...

============================================================
Agent 生成的行銷文案（串流模式）
============================================================
【標題】
讓每一口呼吸，都是對家人的守護

【副標題】
AirPure Pro 智能空氣清淨機 — 醫療級濾淨，給家人最純淨的空氣

【正文】
...（內容會逐字即時顯示）

【行動呼籲】
立即前往官網，享受限時早鳥優惠！

============================================================
```

## 學習重點

1. **create_agent API**: 了解 LangChain 1.x 新的 Agent 建立標準
2. **@tool 裝飾器**: 學習如何定義 Agent 可使用的工具
3. **Messages 格式**: 理解 create_agent 的輸入輸出格式
4. **invoke vs stream**: 理解兩種執行模式的差異與適用場景
5. **串流事件處理**: 學習如何處理 stream 產生的各種事件

## 延伸學習

- **Middleware**: 可加入 PIIMiddleware、SummarizationMiddleware 等中介層
- **Structured Output**: 使用 Pydantic 模型定義結構化輸出
- **Multiple Tools**: 擴展更多工具讓 Agent 具備更多能力
- **Async Stream**: 使用 `astream()` 進行非同步串流處理
