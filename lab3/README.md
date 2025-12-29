# Lab3: Single-Agent 行銷文案生成器（含對話歷史記錄）

## 概述

這是一個 **Single-Agent** 範例，基於 Lab2 的 `create_agent` 實作，新增 **對話歷史記錄功能**。

使用 LangGraph 的 `InMemorySaver` 作為 checkpointer，讓 Agent 能夠記住之前的對話內容，實現多輪對話。

## Lab2 vs Lab3 差異

| 項目 | Lab2 | Lab3 |
|------|------|------|
| 對話記憶 | 無 | 有（InMemorySaver） |
| 多輪對話 | 不支援 | 支援 |
| 執行模式 | invoke / stream / stream detailed | 只保留 stream |
| thread_id | 無 | 有，用於區分對話 |

## 架構說明

```
┌─────────────────────────────────────────────────────────┐
│           對話歷史記錄架構                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   [使用者輸入] ──────────────────────────┐              │
│        │                                 │              │
│        ▼                                 │              │
│   ┌─────────────────────────────────────┐│              │
│   │           create_agent              ││              │
│   │  ┌─────────┐  ┌─────────────────┐  ││              │
│   │  │  Model  │  │     Tools       │  ││              │
│   │  └─────────┘  └─────────────────┘  ││              │
│   │         ┌───────────────┐          ││              │
│   │         │ System Prompt │          ││              │
│   │         └───────────────┘          ││              │
│   └─────────────────────────────────────┘│              │
│                      │                   │              │
│                      ▼                   │              │
│   ┌─────────────────────────────────────┐│              │
│   │         InMemorySaver               ││              │
│   │  ┌──────────────────────────────┐  ││              │
│   │  │  thread_id: "abc123"         │◄─┘│              │
│   │  │  messages: [...]             │   │              │
│   │  └──────────────────────────────┘   │              │
│   └─────────────────────────────────────┘              │
│                      │                                  │
│                      ▼                                  │
│               [串流輸出回應]                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 對話記憶核心概念

### Checkpointer

Checkpointer 用於保存和恢復對話狀態：

```python
from langgraph.checkpoint.memory import InMemorySaver

# 建立 checkpointer
checkpointer = InMemorySaver()

# 建立 Agent 時加入 checkpointer
agent = create_agent(
    model="gpt-4o",
    tools=[...],
    system_prompt="...",
    checkpointer=checkpointer  # 加入此參數
)
```

### Thread ID

使用 `thread_id` 區分不同的對話：

```python
# 每個對話有獨立的 thread_id
config = {
    "configurable": {
        "thread_id": "conversation-1"
    }
}

# 串流時傳入 config
for chunk, metadata in agent.stream(
    {"messages": [{"role": "user", "content": "..."}]},
    config=config,  # 傳入 config
    stream_mode="messages"
):
    print(chunk.content, end="", flush=True)
```

### 取得對話歷史

```python
# 取得特定對話的狀態
config = {"configurable": {"thread_id": "conversation-1"}}
state = agent.get_state(config)

# 取得訊息列表
messages = state.values.get("messages", [])
```

## 使用技術

- **LangChain 1.x**: `create_agent` API
- **LangGraph**: `InMemorySaver` checkpointer
- **Thread ID**: 對話識別與管理
- **Streaming**: token 級別串流輸出

## 安裝與設定

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入 OPENAI_API_KEY
```

### 3. 執行程式

```bash
python lab3/lab3_single_agent.py
```

## 程式碼結構

```
lab3/
├── lab3_single_agent.py  # 主程式
└── README.md             # 說明文件
```

### 主要類別與函數

**MarketingAgentWithMemory 類別**：
- `__init__()`: 初始化 Agent 和 checkpointer
- `new_conversation()`: 開始新對話，生成新的 thread_id
- `stream_chat()`: 以串流方式進行對話
- `get_conversation_history()`: 取得對話歷史
- `show_conversation_history()`: 顯示對話歷史

**其他函數**：
- `load_environment()`: 載入環境變數
- `generate_marketing_copy()`: 行銷文案生成工具
- `main()`: 程式入口

## 輸出範例

```
============================================================
Lab3: Single-Agent 行銷文案生成器
（含對話歷史記錄功能）
============================================================

✓ 環境變數載入成功
✓ 開始新對話 (ID: a1b2c3d4...)

============================================================
開始多輪對話展示
============================================================

【第一輪】提供產品資訊
------------------------------------------------------------
[對話 ID: a1b2c3d4...]
[使用者]: 請幫我撰寫以下產品的行銷文案...
------------------------------------------------------------
[助理]: 【標題】
讓每一口呼吸，都是對家人的守護
...

【第二輪】要求修改文案
------------------------------------------------------------
[對話 ID: a1b2c3d4...]
[使用者]: 請把標題改得更有情感一點...
------------------------------------------------------------
[助理]: 好的，我來修改標題，讓它更有情感...
（Agent 記得之前的文案內容，進行修改）

【第三輪】詢問其他建議
------------------------------------------------------------
[對話 ID: a1b2c3d4...]
[使用者]: 你覺得這個文案還可以怎麼優化？
------------------------------------------------------------
[助理]: 根據我們之前討論的內容，我有以下建議...
（Agent 基於整個對話脈絡提供建議）

============================================================
互動模式（輸入 'quit' 結束，'new' 開始新對話，'history' 查看歷史）
============================================================

[你]: _
```

## 互動指令

| 指令 | 說明 |
|------|------|
| `quit` | 結束程式 |
| `new` | 開始新的對話（生成新的 thread_id） |
| `history` | 顯示當前對話的歷史記錄 |
| 其他文字 | 作為訊息發送給 Agent |

## 學習重點

1. **Checkpointer**: 了解 LangGraph 的狀態持久化機制
2. **Thread ID**: 學習如何使用 thread_id 管理多個對話
3. **多輪對話**: 實現具有上下文記憶的對話系統
4. **狀態管理**: 使用 `get_state()` 取得對話歷史

## 延伸學習

- **持久化儲存**: 使用 `PostgresSaver` 或 `MongoDBSaver` 將對話保存到資料庫
- **多使用者**: 加入 `user_id` 實現多使用者對話管理
- **記憶搜尋**: 結合 `Store` 實現語意搜尋對話記憶
