"""
Lab5: Multi-Agent Handoff - 企業內部支援系統

這是一個 Multi-Agent Handoff 範例，展示如何使用 Handoff Orchestration（移交編排）
管理多個代理人之間的協作與任務轉移。

應用場景：企業內部支援系統
當員工提出 IT、HR 或合規相關問題時，系統根據問題類型轉交給對應的專責 Agent。

Agent 架構：
- TriageAgent：分流代理，負責判斷問題類別並轉交給對應專責代理
- HRAgent：人資代理，處理薪資、福利、假期等問題
- ITAgent：IT 代理，處理系統使用、帳號管理、軟硬體支援等問題
- ComplianceAgent：合規代理，處理法規遵循等問題

主要特色：
- 使用 StateGraph 建立工作流程
- 使用 add_conditional_edges 實現條件路由
- 根據 TriageAgent 的判斷結果進行移交
- 支援串流輸出與互動對話
"""

import os
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END


# =============================================================================
# 終端機顏色定義
# =============================================================================
class Colors:
    """
    終端機顏色代碼

    使用 ANSI 轉義序列在終端機中顯示彩色文字，
    讓不同角色的對話更容易區分。
    """

    # 重置顏色
    RESET = "\033[0m"

    # 一般顏色
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # 粗體顏色
    BOLD = "\033[1m"
    BOLD_GREEN = "\033[1;32m"
    BOLD_BLUE = "\033[1;34m"
    BOLD_CYAN = "\033[1;36m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_MAGENTA = "\033[1;35m"
    BOLD_RED = "\033[1;31m"

    # 角色顏色定義
    USER = "\033[1;32m"  # 粗體綠色 - 使用者
    TRIAGE = "\033[1;33m"  # 粗體黃色 - 分流代理
    HR = "\033[1;35m"  # 粗體紫色 - HR 代理
    IT = "\033[1;36m"  # 粗體青色 - IT 代理
    COMPLIANCE = "\033[1;34m"  # 粗體藍色 - 合規代理
    SYSTEM = "\033[90m"  # 灰色 - 系統訊息


# =============================================================================
# 狀態定義
# =============================================================================
class SupportState(TypedDict):
    """
    企業支援系統的狀態定義

    這個 TypedDict 定義了在整個工作流程中傳遞的狀態結構。
    每個 Agent 都可以讀取和更新這些狀態欄位。

    狀態流程說明：
    1. 使用者提問 → user_question 被設定
    2. TriageAgent 分析 → question_category 被設定（hr/it/compliance）
    3. 對應的專責 Agent 處理 → agent_response 被設定
    4. 最終輸出 agent_response 給使用者
    """

    # 使用者的原始問題
    user_question: str

    # TriageAgent 判斷的問題類別：hr, it, compliance
    question_category: str

    # 專責 Agent 的回應內容
    agent_response: str


# =============================================================================
# 環境設定
# =============================================================================
def load_environment():
    """
    載入環境變數

    從 .env 檔案載入 API 金鑰和模型設定。
    """
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("請設定 OPENAI_API_KEY 環境變數")

    return api_key


def create_llm():
    """
    建立 LLM 實例

    Returns:
        ChatOpenAI: 設定好的 LLM 實例
    """
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
    return ChatOpenAI(model=model_name, temperature=0.7, streaming=True)


# =============================================================================
# Agent 節點定義
# =============================================================================


def triage_agent(state: SupportState) -> dict:
    """
    分流代理（TriageAgent）

    職責：分析使用者的問題，判斷應該轉交給哪個專責代理處理。

    分類規則：
    - hr：薪資、福利、假期、考勤、招聘、培訓等人資相關問題
    - it：系統、帳號、密碼、軟體、硬體、網路等 IT 相關問題
    - compliance：法規、政策、合規、審計、風控等合規相關問題

    Args:
        state: 當前狀態，包含 user_question

    Returns:
        dict: 包含 question_category 的更新狀態
              這個 dict 會被 LangGraph 自動合併到主狀態中
    """
    print(f"\n{Colors.SYSTEM}[系統] TriageAgent 正在分析問題類別...{Colors.RESET}")

    llm = create_llm()

    # 分流代理的系統提示詞
    system_prompt = """你是一個企業內部支援系統的分流代理（Triage Agent）。
你的任務是分析員工的問題，判斷應該轉交給哪個部門處理。

分類規則：
1. hr - 人資相關：薪資、福利、假期、請假、考勤、招聘、培訓、績效考核、員工關係等
2. it - IT 相關：系統使用、帳號管理、密碼重設、軟體安裝、硬體問題、網路連線、VPN、電子郵件等
3. compliance - 合規相關：法規遵循、公司政策、內部稽核、風險管理、資料保護、保密協議等

請只回覆一個單詞：hr、it 或 compliance
不要包含任何其他文字或解釋。"""

    # 呼叫 LLM 進行分類
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"請分類以下問題：{state['user_question']}"),
    ]

    # 使用非串流方式取得分類結果（因為只需要簡短回應）
    response = llm.invoke(messages)
    category = response.content.strip().lower()

    # 確保分類結果有效
    valid_categories = ["hr", "it", "compliance"]
    if category not in valid_categories:
        # 如果無法判斷，預設為 it（最常見的問題類型）
        category = "it"

    # 顯示分類結果
    category_names = {"hr": "人資部門", "it": "IT 部門", "compliance": "合規部門"}
    print(
        f"{Colors.TRIAGE}[TriageAgent]{Colors.RESET} 判斷此問題屬於：{Colors.BOLD}{category_names[category]}{Colors.RESET}"
    )

    # 返回更新的狀態
    # 這個 dict 會被 LangGraph 自動合併到主狀態中
    # 只有 question_category 欄位會被更新，其他欄位保持不變
    return {"question_category": category}


def hr_agent(state: SupportState) -> dict:
    """
    人資代理（HRAgent）

    職責：處理人資相關問題，包括薪資、福利、假期等。

    Args:
        state: 當前狀態，包含 user_question 和 question_category

    Returns:
        dict: 包含 agent_response 的更新狀態
    """
    print(f"\n{Colors.HR}[HRAgent]{Colors.RESET} 正在處理人資相關問題...")
    print("-" * 50)

    llm = create_llm()

    # HR 代理的系統提示詞
    system_prompt = """你是企業內部的人資支援專員（HR Agent）。
你專門負責回答員工關於人資相關的問題。

你的專業領域包括：
- 薪資與獎金：薪資結構、發薪日期、年終獎金計算方式等
- 福利制度：保險、健檢、員工優惠、退休金等
- 假期管理：特休、病假、事假、婚喪假等請假規定
- 考勤制度：上下班時間、彈性工時、遲到早退規定
- 招聘流程：內部轉調、升遷管道、職缺資訊
- 培訓發展：教育訓練、進修補助、職涯發展

請以專業、友善的態度回答問題。
如果問題超出你的專業範圍，請建議員工聯繫其他部門。"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_question"]),
    ]

    # 串流輸出回應
    print(f"{Colors.HR}[HRAgent 回應]{Colors.RESET}: ", end="", flush=True)
    full_response = ""

    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_response += chunk.content

    print("\n")

    return {"agent_response": full_response}


def it_agent(state: SupportState) -> dict:
    """
    IT 代理（ITAgent）

    職責：處理 IT 相關問題，包括系統使用、帳號管理、軟硬體支援等。

    Args:
        state: 當前狀態，包含 user_question 和 question_category

    Returns:
        dict: 包含 agent_response 的更新狀態
    """
    print(f"\n{Colors.IT}[ITAgent]{Colors.RESET} 正在處理 IT 相關問題...")
    print("-" * 50)

    llm = create_llm()

    # IT 代理的系統提示詞
    system_prompt = """你是企業內部的 IT 支援專員（IT Agent）。
你專門負責回答員工關於 IT 相關的問題。

你的專業領域包括：
- 帳號管理：帳號申請、密碼重設、權限設定、AD 帳號
- 系統使用：ERP、CRM、HR系統、內部系統操作說明
- 軟體支援：Office 365、VPN、防毒軟體、常用軟體安裝
- 硬體問題：電腦故障、印表機、視訊會議設備
- 網路連線：Wi-Fi、有線網路、VPN 連線問題
- 資訊安全：可疑郵件處理、資料備份、安全軟體更新

請以專業、耐心的態度回答問題。
對於技術問題，請提供step-by-step的操作步驟。
如果需要現場支援，請引導員工提交 IT 服務單。"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_question"]),
    ]

    # 串流輸出回應
    print(f"{Colors.IT}[ITAgent 回應]{Colors.RESET}: ", end="", flush=True)
    full_response = ""

    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_response += chunk.content

    print("\n")

    return {"agent_response": full_response}


def compliance_agent(state: SupportState) -> dict:
    """
    合規代理（ComplianceAgent）

    職責：處理合規相關問題，包括法規遵循、公司政策等。

    Args:
        state: 當前狀態，包含 user_question 和 question_category

    Returns:
        dict: 包含 agent_response 的更新狀態
    """
    print(
        f"\n{Colors.COMPLIANCE}[ComplianceAgent]{Colors.RESET} 正在處理合規相關問題..."
    )
    print("-" * 50)

    llm = create_llm()

    # 合規代理的系統提示詞
    system_prompt = """你是企業內部的合規支援專員（Compliance Agent）。
你專門負責回答員工關於合規相關的問題。

你的專業領域包括：
- 法規遵循：相關法律法規、產業規範、監管要求
- 公司政策：行為準則、道德規範、內部規章制度
- 資料保護：個資法、GDPR、客戶資料處理規範
- 保密協議：NDA、競業禁止、智慧財產權保護
- 利益衝突：申報程序、迴避原則、禮品收受規定
- 內部稽核：稽核流程、自我評估、改善計畫
- 風險管理：風險識別、風險評估、風險應對措施

請以專業、謹慎的態度回答問題。
對於涉及法律風險的問題，請建議員工諮詢法務部門。
強調合規的重要性，但避免使用過於嚴厲的語氣。"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_question"]),
    ]

    # 串流輸出回應
    print(
        f"{Colors.COMPLIANCE}[ComplianceAgent 回應]{Colors.RESET}: ", end="", flush=True
    )
    full_response = ""

    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_response += chunk.content

    print("\n")

    return {"agent_response": full_response}


# =============================================================================
# 路由函數
# =============================================================================


def route_to_specialist(
    state: SupportState,
) -> Literal["hr_agent", "it_agent", "compliance_agent"]:
    """
    路由函數：根據 TriageAgent 的判斷結果，決定下一步要執行哪個 Agent

    這個函數被 add_conditional_edges 使用，用於實現條件路由。

    Handoff（移交）的核心概念：
    - TriageAgent 分析完問題後，將控制權「移交」給適合的專責 Agent
    - 這不是簡單的函數呼叫，而是工作流程的分支轉移
    - 每個專責 Agent 都是獨立的節點，有自己的 System Prompt 和專業知識

    Args:
        state: 當前狀態，包含 question_category

    Returns:
        str: 下一個要執行的節點名稱（hr_agent / it_agent / compliance_agent）
    """
    category = state["question_category"]

    # 根據分類結果，返回對應的節點名稱
    # LangGraph 會根據這個返回值，決定下一步執行哪個節點
    if category == "hr":
        return "hr_agent"
    elif category == "it":
        return "it_agent"
    else:
        return "compliance_agent"


# =============================================================================
# 建立工作流程
# =============================================================================


def create_support_workflow():
    """
    建立企業支援系統的工作流程

    工作流程說明：
    ┌─────────────────────────────────────────────────────────────┐
    │                    Handoff Orchestration                     │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │   START                                                      │
    │     │                                                        │
    │     ▼                                                        │
    │   ┌─────────────┐                                            │
    │   │TriageAgent  │  分析問題類別                               │
    │   └──────┬──────┘                                            │
    │          │                                                   │
    │          │ 條件路由（根據 question_category）                  │
    │          │                                                   │
    │    ┌─────┼─────┐                                             │
    │    │     │     │                                             │
    │    ▼     ▼     ▼                                             │
    │  ┌───┐ ┌───┐ ┌────────┐                                      │
    │  │HR │ │IT │ │Compliance│                                    │
    │  └─┬─┘ └─┬─┘ └────┬───┘                                      │
    │    │     │        │                                          │
    │    └─────┴────────┘                                          │
    │          │                                                   │
    │          ▼                                                   │
    │         END                                                  │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘

    Returns:
        CompiledGraph: 編譯後的工作流程圖
    """
    # ==========================================================================
    # 步驟 1：建立 StateGraph
    # ==========================================================================
    # StateGraph 是 LangGraph 的核心，用於定義狀態驅動的工作流程
    # 傳入 SupportState 作為狀態的型別定義
    workflow = StateGraph(SupportState)

    # ==========================================================================
    # 步驟 2：添加節點
    # ==========================================================================
    # 每個節點代表一個 Agent，負責處理特定的任務
    # 節點名稱（第一個參數）會在路由時使用

    # 分流代理節點：負責分析問題並判斷類別
    workflow.add_node("triage_agent", triage_agent)

    # 專責代理節點：各自處理特定類型的問題
    workflow.add_node("hr_agent", hr_agent)
    workflow.add_node("it_agent", it_agent)
    workflow.add_node("compliance_agent", compliance_agent)

    # ==========================================================================
    # 步驟 3：定義邊（Edges）
    # ==========================================================================

    # 起始邊：從 START 到 triage_agent
    # 這表示工作流程從 triage_agent 開始執行
    workflow.add_edge(START, "triage_agent")

    # ==========================================================================
    # 步驟 4：定義條件邊（Conditional Edges）- Handoff 的核心
    # ==========================================================================
    # add_conditional_edges 實現了 Handoff（移交）機制
    # 根據 route_to_specialist 函數的返回值，決定下一步執行哪個節點
    #
    # 參數說明：
    # - "triage_agent"：來源節點，表示從 triage_agent 之後開始路由
    # - route_to_specialist：路由函數，根據狀態決定下一個節點
    workflow.add_conditional_edges(
        "triage_agent",  # 來源節點
        route_to_specialist,  # 路由函數
    )

    # ==========================================================================
    # 步驟 5：定義結束邊
    # ==========================================================================
    # 所有專責代理處理完後，都會結束工作流程
    # 這是一種「扇入」（fan-in）模式：多個節點匯聚到同一個終點
    workflow.add_edge("hr_agent", END)
    workflow.add_edge("it_agent", END)
    workflow.add_edge("compliance_agent", END)

    # ==========================================================================
    # 步驟 6：編譯工作流程
    # ==========================================================================
    # 編譯後的工作流程可以被執行
    return workflow.compile()


# =============================================================================
# 執行支援請求
# =============================================================================


def process_support_request(app, user_question: str) -> str:
    """
    處理一個支援請求

    Args:
        app: 編譯後的工作流程
        user_question: 使用者的問題

    Returns:
        str: Agent 的回應
    """
    # 初始化狀態
    initial_state = {
        "user_question": user_question,
        "question_category": "",
        "agent_response": "",
    }

    # 執行工作流程
    # invoke 會執行整個工作流程，直到到達 END 節點
    # 過程中會依序執行：triage_agent → (hr/it/compliance)_agent
    final_state = app.invoke(initial_state)

    return final_state["agent_response"]


# =============================================================================
# 主程式
# =============================================================================


def main():
    """
    主程式入口

    展示 Handoff Orchestration 的工作流程：
    1. 先執行一個示範問答
    2. 進入互動模式，讓使用者自由提問
    """
    print("=" * 60)
    print("Lab5: Multi-Agent Handoff - 企業內部支援系統")
    print("=" * 60)

    # 載入環境變數
    try:
        load_environment()
        print("\n✓ 環境變數載入成功")
    except ValueError as e:
        print(f"\n✗ 錯誤：{e}")
        return

    # 建立工作流程
    print("\n正在建立支援系統工作流程...")
    app = create_support_workflow()
    print("✓ 工作流程建立完成")

    # 顯示系統架構
    print("\n" + "=" * 60)
    print("系統架構")
    print("=" * 60)
    print(
        """
    ┌─────────────┐
    │   使用者    │
    └──────┬──────┘
           │ 提問
           ▼
    ┌─────────────┐
    │TriageAgent  │ ← 分析問題類別
    └──────┬──────┘
           │
     ┌─────┴─────┐
     │ 條件路由   │
     └─────┬─────┘
       ┌───┼───┐
       │   │   │
       ▼   ▼   ▼
    ┌────┬────┬──────────┐
    │ HR │ IT │Compliance│
    └────┴────┴──────────┘
    """
    )

    # 示範問答
    print("=" * 60)
    print("示範：處理一個支援請求")
    print("=" * 60)

    demo_question = "我想請問一下，公司的特休假是怎麼計算的？入職滿一年有幾天假？"
    print(f"\n{Colors.USER}[使用者]{Colors.RESET}: {demo_question}")

    process_support_request(app, demo_question)

    # 互動模式
    print("\n" + "=" * 60)
    print("互動模式（輸入 'quit' 結束）")
    print("=" * 60)
    print("\n您可以詢問以下類型的問題：")
    print(f"  • {Colors.HR}人資相關{Colors.RESET}：薪資、福利、請假、考勤...")
    print(f"  • {Colors.IT}IT 相關{Colors.RESET}：帳號、系統、軟硬體、網路...")
    print(f"  • {Colors.COMPLIANCE}合規相關{Colors.RESET}：法規、政策、保密、稽核...")

    while True:
        try:
            user_input = input(f"\n{Colors.USER}[你]{Colors.RESET}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n感謝使用企業內部支援系統，再見！")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("\n感謝使用企業內部支援系統，再見！")
            break

        process_support_request(app, user_input)


if __name__ == "__main__":
    main()
