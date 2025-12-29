# Lab5: Multi-Agent Handoff - 企業內部支援實作

## 概述

這是一個 **Multi-Agent Handoff** 範例，展示如何使用 **Handoff Orchestration（移交編排）** 管理多個代理人之間的協作與任務轉移。

以「企業內部支援系統」為應用場景，當員工提出問題時，由分流代理判斷問題類型，並將控制權轉交給對應的專責代理處理。

## 應用場景

企業內部經常有來自不同領域的員工詢問：
- 人資問題：薪資、福利、假期
- IT 問題：系統使用、帳號管理、軟硬體
- 合規問題：法規遵循、公司政策

透過 Handoff 機制，系統能自動判斷問題類型並轉交給最適合的專家處理。

## 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                  Handoff Orchestration 架構                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   [使用者提問]                                                │
│         │                                                    │
│         ▼                                                    │
│   ┌─────────────────┐                                        │
│   │  TriageAgent    │  分流代理                               │
│   │                 │  - 分析問題內容                         │
│   │                 │  - 判斷問題類別                         │
│   │                 │  - 決定移交對象                         │
│   └────────┬────────┘                                        │
│            │                                                 │
│            │ Conditional Routing（條件路由）                  │
│            │                                                 │
│      ┌─────┼─────┐                                           │
│      │     │     │                                           │
│      ▼     ▼     ▼                                           │
│   ┌─────┬─────┬─────────────┐                                │
│   │ HR  │ IT  │ Compliance  │                                │
│   │Agent│Agent│   Agent     │                                │
│   └──┬──┴──┬──┴──────┬──────┘                                │
│      │     │         │                                       │
│      └─────┴─────────┘                                       │
│            │                                                 │
│            ▼                                                 │
│   [專業回應輸出]                                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 四個 Agent 職責

| Agent           | 名稱     | 職責                                         |
| --------------- | -------- | -------------------------------------------- |
| TriageAgent     | 分流代理 | 分析問題類別，決定移交給哪個專責代理         |
| HRAgent         | 人資代理 | 處理薪資、福利、假期、考勤等人資相關問題     |
| ITAgent         | IT 代理  | 處理系統使用、帳號管理、軟硬體支援等 IT 問題 |
| ComplianceAgent | 合規代理 | 處理法規遵循、公司政策、內部稽核等合規問題   |

## Handoff Orchestration 核心概念

### 什麼是 Handoff？

Handoff（移交）是指將對話的控制權從一個 Agent 轉移到另一個 Agent。這與簡單的函數呼叫不同：

- **函數呼叫**：呼叫者保持控制權，等待結果返回
- **Handoff**：控制權完全轉移，由接收者決定後續流程

### StateGraph 與條件路由

```python
from langgraph.graph import StateGraph, START, END

# 定義狀態結構
class SupportState(TypedDict):
    user_question: str       # 使用者問題
    question_category: str   # 問題類別 (hr/it/compliance)
    agent_response: str      # Agent 回應

# 建立工作流程
workflow = StateGraph(SupportState)

# 添加節點
workflow.add_node("triage_agent", triage_agent)
workflow.add_node("hr_agent", hr_agent)
workflow.add_node("it_agent", it_agent)
workflow.add_node("compliance_agent", compliance_agent)
```

### 條件邊定義

```python
def route_to_specialist(state: SupportState) -> str:
    """根據分類結果決定下一個節點"""
    category = state["question_category"]
    if category == "hr":
        return "hr_agent"
    elif category == "it":
        return "it_agent"
    else:
        return "compliance_agent"

# 添加條件邊 - Handoff 的核心
workflow.add_conditional_edges(
    "triage_agent",       # 來源節點
    route_to_specialist   # 路由函數
)

# 結束邊
workflow.add_edge("hr_agent", END)
workflow.add_edge("it_agent", END)
workflow.add_edge("compliance_agent", END)
```

### 執行工作流程

```python
initial_state = {
    "user_question": "如何申請特休假？",
    "question_category": "",
    "agent_response": ""
}

final_state = app.invoke(initial_state)
print(final_state["agent_response"])
```

## 使用技術

- **LangGraph StateGraph**: 狀態圖工作流程
- **Conditional Edges**: 條件路由實現 Handoff
- **Streaming**: 各 Agent 即時串流輸出
- **TypedDict State**: 型別安全的狀態定義

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
python lab5/lab5_multi_agent_handoff.py
```

## 程式碼結構

```
lab5/
├── lab5_multi_agent_handoff.py  # 主程式
└── README.md                    # 說明文件
```

### 主要組件

**狀態定義**：
- `SupportState`: 定義支援系統的狀態結構

**Agent 節點**：
- `triage_agent()`: 分流代理，判斷問題類別
- `hr_agent()`: 人資代理
- `it_agent()`: IT 代理
- `compliance_agent()`: 合規代理

**路由函數**：
- `route_to_specialist()`: 根據分類結果決定移交對象

**工作流程**：
- `create_support_workflow()`: 建立並編譯工作流程

## 輸出範例

```
============================================================
Lab5: Multi-Agent Handoff - 企業內部支援系統
============================================================

✓ 環境變數載入成功

正在建立支援系統工作流程...
✓ 工作流程建立完成

============================================================
示範：處理一個支援請求
============================================================

[使用者]: 我想請問一下，公司的特休假是怎麼計算的？入職滿一年有幾天假？

[系統] TriageAgent 正在分析問題類別...
[TriageAgent] 判斷此問題屬於：人資部門

[HRAgent] 正在處理人資相關問題...
--------------------------------------------------
[HRAgent 回應]: 關於特休假的計算方式，根據勞動基準法規定：

1. **入職滿6個月未滿1年**：3天特休假
2. **入職滿1年未滿2年**：7天特休假
3. **入職滿2年未滿3年**：10天特休假
4. **入職滿3年未滿5年**：每年14天
5. **入職滿5年未滿10年**：每年15天
6. **入職滿10年以上**：每滿1年加1天，最多30天

所以，入職滿一年的員工可以享有 **7天** 的特休假。

如果您需要申請特休假，請透過 HR 系統提交申請...

============================================================
互動模式（輸入 'quit' 結束）
============================================================

您可以詢問以下類型的問題：
  • 人資相關：薪資、福利、請假、考勤...
  • IT 相關：帳號、系統、軟硬體、網路...
  • 合規相關：法規、政策、保密、稽核...

[你]: 我的 VPN 連不上，該怎麼辦？

[系統] TriageAgent 正在分析問題類別...
[TriageAgent] 判斷此問題屬於：IT 部門

[ITAgent] 正在處理 IT 相關問題...
--------------------------------------------------
[ITAgent 回應]: VPN 連線問題可以依照以下步驟排查：

1. **檢查網路連線**
   - 確認您的網路可以正常上網
   - 嘗試開啟網頁確認連線狀態

2. **重新啟動 VPN 軟體**
   - 完全關閉 VPN 程式
   - 重新開啟並嘗試連線
...
```

## 學習重點

1. **Handoff 概念**: 了解控制權轉移的設計模式
2. **Conditional Edges**: 學習如何使用條件路由
3. **多 Agent 協作**: 設計分工明確的 Agent 系統
4. **分流機制**: 實現智能的問題分類與路由

## 與其他 Lab 的比較

| 項目       | Lab4 (Sequential) | Lab5 (Handoff)        |
| ---------- | ----------------- | --------------------- |
| 執行順序   | 固定順序執行      | 條件分支執行          |
| Agent 關係 | 串接（前後相依）  | 平行（專責分工）      |
| 路由方式   | add_edge          | add_conditional_edges |
| 適用場景   | 流程固定的任務    | 需要分類路由的任務    |

## 延伸學習

- **多層 Handoff**: 實現更複雜的多層路由
- **Fallback 機制**: 當無法分類時的預設處理
- **Human-in-the-Loop**: 在分流不確定時請求人工介入
- **記憶整合**: 結合 Checkpointer 實現多輪對話
