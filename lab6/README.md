# Lab6: Multi-Agent Concurrent - 產品手冊多語言翻譯實作

## 概述

這是一個 **Multi-Agent Concurrent** 範例，展示如何使用 **Concurrent Orchestration（並行編排）** 將同一份輸入同時廣播給多個 Agent 平行處理，最後彙整結果。

以「產品手冊多語言翻譯」為應用場景，將英文產品手冊同時翻譯成中文、日文、法文三種語言。

## 應用場景

當需要將內容翻譯成多種語言時：
- 各語言翻譯之間沒有依賴關係
- 可以同時進行，提高效率
- 最後需要彙整所有翻譯結果

透過 Concurrent Orchestration，可以大幅縮短整體翻譯時間。

## 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                  Concurrent Orchestration 架構               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   [英文產品手冊]                                              │
│         │                                                    │
│         │ Fan-out（扇出）：同時廣播到多個節點                  │
│         │                                                    │
│   ┌─────┼─────┐                                              │
│   │     │     │                                              │
│   ▼     ▼     ▼                                              │
│ ┌─────────┐┌─────────┐┌─────────┐                            │
│ │ Chinese ││Japanese ││ French  │                            │
│ │Translator││Translator││Translator│  ← 並行執行              │
│ └────┬────┘└────┬────┘└────┬────┘                            │
│      │          │          │                                 │
│      │ Fan-in（扇入）：等待所有節點完成                        │
│      │          │          │                                 │
│      └──────────┼──────────┘                                 │
│                 │                                            │
│                 ▼                                            │
│          ┌────────────┐                                      │
│          │ Aggregator │  彙整所有翻譯結果                     │
│          └─────┬──────┘                                      │
│                │                                             │
│                ▼                                             │
│       [多語言翻譯結果]                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 三個 Agent 職責

| Agent                   | 名稱       | 職責                         |
| ----------------------- | ---------- | ---------------------------- |
| ChineseTranslatorAgent  | 中文翻譯   | 將產品手冊翻譯成繁體中文     |
| JapaneseTranslatorAgent | 日文翻譯   | 將產品手冊翻譯成日文         |
| FrenchTranslatorAgent   | 法文翻譯   | 將產品手冊翻譯成法文         |

## Concurrent Orchestration 核心概念

### Fan-out（扇出）與 Fan-in（扇入）

Concurrent Orchestration 的核心是兩個模式：

1. **Fan-out（扇出）**：將輸入同時廣播給多個節點
2. **Fan-in（扇入）**：等待所有節點完成後收斂

### StateGraph 與並行執行

```python
from langgraph.graph import StateGraph, START, END

# 定義狀態結構
class TranslationState(TypedDict):
    source_content: str          # 原始英文內容
    chinese_translation: str     # 中文翻譯結果
    japanese_translation: str    # 日文翻譯結果
    french_translation: str      # 法文翻譯結果
    aggregated_result: str       # 彙整結果

# 建立工作流程
workflow = StateGraph(TranslationState)
```

### Fan-out 邊定義

```python
# 從 START 同時連接到三個翻譯節點
# LangGraph 會並行執行這三個節點
workflow.add_edge(START, "chinese_translator")
workflow.add_edge(START, "japanese_translator")
workflow.add_edge(START, "french_translator")
```

### Fan-in 邊定義

```python
# 所有翻譯節點都連接到 aggregator
# aggregator 會等待所有翻譯完成後才執行
workflow.add_edge("chinese_translator", "aggregator")
workflow.add_edge("japanese_translator", "aggregator")
workflow.add_edge("french_translator", "aggregator")

# 結束
workflow.add_edge("aggregator", END)
```

### 狀態合併機制

```python
def chinese_translator_agent(state: TranslationState) -> dict:
    # 執行翻譯...
    translation = "..."

    # 只返回需要更新的欄位
    # LangGraph 會自動合併到主狀態
    return {"chinese_translation": translation}
```

並行執行時，每個 Agent 只更新自己負責的欄位，LangGraph 會自動將所有更新合併。

## 使用技術

- **LangGraph StateGraph**: 狀態圖工作流程
- **Fan-out Pattern**: 並行分發到多個節點
- **Fan-in Pattern**: 等待並收斂結果
- **Streaming**: 各 Agent 即時串流輸出
- **Aggregator**: 結果彙整節點

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
python lab6/lab6_multi_agent_concurrent.py
```

## 程式碼結構

```
lab6/
├── lab6_multi_agent_concurrent.py  # 主程式
└── README.md                       # 說明文件
```

### 主要組件

**狀態定義**：
- `TranslationState`: 定義翻譯系統的狀態結構

**Agent 節點**：
- `chinese_translator_agent()`: 中文翻譯 Agent
- `japanese_translator_agent()`: 日文翻譯 Agent
- `french_translator_agent()`: 法文翻譯 Agent
- `aggregator()`: 結果彙整節點

**工作流程**：
- `create_translation_workflow()`: 建立並編譯工作流程

## 輸出範例

```
============================================================
Lab6: Multi-Agent Concurrent - 產品手冊多語言翻譯系統
============================================================

✓ 環境變數載入成功

正在建立翻譯系統工作流程...
✓ 工作流程建立完成

============================================================
示範：翻譯產品手冊
============================================================

[原文]:
AirPure Pro - Smart Air Purifier
...

============================================================
開始並行翻譯...
（三個翻譯 Agent 同時工作）
============================================================

[ChineseTranslatorAgent] 開始翻譯成中文...
--------------------------------------------------
[中文翻譯]:
AirPure Pro - 智能空氣清淨機

產品概述：
AirPure Pro 是專為現代家庭設計的新一代智能空氣清淨機...

[JapaneseTranslatorAgent] 開始翻譯成日文...
--------------------------------------------------
[日文翻譯]:
AirPure Pro - スマート空気清浄機

製品概要：
AirPure Pro は、現代の家庭向けに設計された次世代スマート空気清浄機です...

[FrenchTranslatorAgent] 開始翻譯成法文...
--------------------------------------------------
[法文翻譯]:
AirPure Pro - Purificateur d'air intelligent

Présentation du produit :
L'AirPure Pro est un purificateur d'air intelligent de nouvelle génération...

[Aggregator] 彙整所有翻譯結果...
============================================================
[彙整完成]

============================================================
多語言翻譯結果彙整
============================================================
...

============================================================
互動模式（輸入 'quit' 結束）
============================================================

輸入英文文字，系統會自動翻譯成三種語言。
可以輸入多行，輸入空行後按 Enter 開始翻譯。

[請輸入英文內容（輸入空行結束）]:
```

## 學習重點

1. **Concurrent Pattern**: 了解並行執行的設計模式
2. **Fan-out / Fan-in**: 學習扇出與扇入的概念
3. **狀態合併**: 理解並行執行時狀態如何合併
4. **Aggregator**: 設計結果彙整節點

## 與其他 Lab 的比較

| 項目       | Lab4 (Sequential)  | Lab5 (Handoff)        | Lab6 (Concurrent)      |
| ---------- | ------------------ | --------------------- | ---------------------- |
| 執行方式   | 依序執行           | 條件分支              | 並行執行               |
| Agent 關係 | 串接（前後相依）   | 擇一執行              | 同時執行               |
| 適用場景   | 流程固定的任務     | 需要分類路由的任務    | 無依賴的平行任務       |
| 結果處理   | 逐步累積           | 單一 Agent 回應       | 彙整多個結果           |

## 延伸學習

- **動態 Agent 數量**: 根據需求動態決定並行 Agent 的數量
- **超時處理**: 為各個並行 Agent 設定超時機制
- **錯誤處理**: 當某個 Agent 失敗時的容錯機制
- **結果投票**: 多個 Agent 產生結果後進行投票或共識
