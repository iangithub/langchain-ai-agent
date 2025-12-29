# Lab4: Multi-Agent Sequential - 合約內容審查實作

## 概述

這是一個 **Multi-Agent Sequential** 範例，展示如何使用 **Sequential Orchestration（順序編排）** 管理多個 Agent 依序完成任務。

以「合約內容審查」為應用場景，設計三個專業 Agent 依序審查合約，展示 Multi-Agent 協作的實作方式。

## 應用場景

合約審查是企業日常運營中重要的一環，需要從多個角度進行審查：
- 文字表達是否清晰
- 法律風險是否可控
- 如何修正問題條款

## 系統架構

```
┌─────────────────────────────────────────────────────────────────┐
│                 Sequential Orchestration 架構                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   [合約內容輸入]                                                 │
│         │                                                       │
│         ▼                                                       │
│   ┌─────────────────┐                                           │
│   │    Agent 1      │  文字審查                                  │
│   │  Text Review    │  - 清晰度檢查                              │
│   │                 │  - 歧義識別                                │
│   │                 │  - 模糊用語                                │
│   └────────┬────────┘                                           │
│            │ 審查結果                                            │
│            ▼                                                    │
│   ┌─────────────────┐                                           │
│   │    Agent 2      │  法律風險評估                              │
│   │  Legal Review   │  - 不平等條款                              │
│   │                 │  - 責任限制                                │
│   │                 │  - 合規檢查                                │
│   └────────┬────────┘                                           │
│            │ 風險評估                                            │
│            ▼                                                    │
│   ┌─────────────────┐                                           │
│   │    Agent 3      │  修正建議                                  │
│   │   Revision      │  - 具體修改方案                            │
│   │                 │  - 修改前後對照                            │
│   │                 │  - 優先順序排列                            │
│   └────────┬────────┘                                           │
│            │                                                    │
│            ▼                                                    │
│   [完整審查報告輸出]                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 三個 Agent 職責

| Agent   | 名稱         | 職責                                     |
| ------- | ------------ | ---------------------------------------- |
| Agent 1 | 文字審查     | 檢查文字清晰度、歧義、模糊用語、灰色地帶 |
| Agent 2 | 法律風險評估 | 評估不平等條款、責任限制、合規問題       |
| Agent 3 | 修正建議     | 根據前兩階段結果提出具體修改方案         |

## Sequential Orchestration 核心概念

### StateGraph 定義

```python
from langgraph.graph import StateGraph, START, END

# 定義狀態結構
class ContractReviewState(TypedDict):
    contract_content: str      # 原始合約
    text_review: str           # Agent 1 結果
    legal_review: str          # Agent 2 結果
    revision_suggestions: str  # Agent 3 結果

# 建立工作流程
workflow = StateGraph(ContractReviewState)
```

### 添加節點與邊

```python
# 添加節點（每個 Agent 一個節點）
workflow.add_node("text_review", agent1_text_review)
workflow.add_node("legal_review", agent2_legal_review)
workflow.add_node("revision_suggestions", agent3_revision_suggestions)

# 定義順序執行的邊
workflow.add_edge(START, "text_review")
workflow.add_edge("text_review", "legal_review")
workflow.add_edge("legal_review", "revision_suggestions")
workflow.add_edge("revision_suggestions", END)

# 編譯
app = workflow.compile()
```

### 執行工作流程

```python
initial_state = {
    "contract_content": "合約內容...",
    "text_review": "",
    "legal_review": "",
    "revision_suggestions": ""
}

final_state = app.invoke(initial_state)
```

## 使用技術

- **LangGraph StateGraph**: 狀態圖工作流程
- **Sequential Edges**: 順序執行的邊定義
- **Streaming**: 各 Agent 即時串流輸出
- **State Passing**: 狀態在 Agent 間傳遞

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
python lab4/lab4_multi_agent_sequential.py
```

## 程式碼結構

```
lab4/
├── lab4_multi_agent_sequential.py  # 主程式
└── README.md                       # 說明文件
```

### 主要組件

**狀態定義**：
- `ContractReviewState`: 定義合約審查的狀態結構

**Agent 節點**：
- `agent1_text_review()`: 文字審查 Agent
- `agent2_legal_review()`: 法律風險評估 Agent
- `agent3_revision_suggestions()`: 修正建議 Agent

**工作流程**：
- `create_contract_review_workflow()`: 建立並編譯工作流程

## 輸出範例

```
============================================================
Lab4: Multi-Agent Sequential - 合約內容審查系統
============================================================

✓ 環境變數載入成功

============================================================
待審查合約內容
============================================================
軟體服務合約
...

正在建立審查工作流程...
✓ 工作流程建立完成

審查流程：
  [Agent 1: 文字審查]
       ↓
  [Agent 2: 法律風險]
       ↓
  [Agent 3: 修正建議]

開始執行合約審查...

============================================================
【Agent 1】合約內容文字審查
============================================================

1. 第一條「服務內容可能隨時調整」
   - 問題：「隨時」過於模糊，未明確調整的條件和通知期限
   - 建議：明確說明調整的情況和提前通知的天數
...

============================================================
【Agent 2】法律風險評估審查
============================================================

1. 不平等條款分析
   - 第二條第2項：「立即終止服務，不另行通知」
   - 風險等級：高
   - 問題：未給予合理的補救期限
...

============================================================
【Agent 3】合約修正建議
============================================================

優先修改建議：

1. 【高優先】第二條第2項 - 付款與終止

   修改前：
   「若乙方逾期未付款，甲方有權立即終止服務，不另行通知。」

   修改後：
   「若乙方逾期未付款，甲方應以書面通知乙方，乙方有7個工作日
   的補救期限。逾期仍未付款者，甲方得終止服務。」
...

============================================================
審查完成摘要
============================================================

合約已經過三階段審查：
  1. 文字審查 - 檢查文字清晰度與歧義
  2. 法律風險評估 - 評估法律風險與不平等條款
  3. 修正建議 - 提出具體修改方案
```

## 學習重點

1. **StateGraph**: 了解 LangGraph 的狀態圖工作流程
2. **Sequential Edges**: 學習如何定義順序執行的邊
3. **State Passing**: 理解狀態如何在 Agent 間傳遞
4. **Multi-Agent 協作**: 設計多個專業 Agent 分工合作

## 與其他 Lab 的比較

| 項目       | Lab1-3     | Lab4            |
| ---------- | ---------- | --------------- |
| Agent 數量 | 單一 Agent | 多個 Agent      |
| 執行方式   | 線性對話   | Sequential 編排 |
| 狀態管理   | Messages   | TypedDict State |
| 工作流程   | 簡單 Chain | StateGraph      |

## 延伸學習

- **Parallel Execution**: 平行執行多個 Agent
- **Conditional Routing**: 根據條件選擇不同的 Agent
- **Human-in-the-Loop**: 在流程中加入人工審核
- **Persistence**: 將審查結果保存到資料庫
