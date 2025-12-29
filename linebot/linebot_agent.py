"""
Lab8: Linebot 結合 AI Agent 系統

這是一個結合 LINE Bot 與 Multi-Agent Handoff 系統的範例。
使用 FastAPI 作為後端框架，整合 LINE Messaging API 與 LangGraph 工作流程。

系統架構：
- FastAPI：處理 LINE Webhook 請求
- line-bot-sdk：處理 LINE 訊息收發
- LangGraph：實作 Multi-Agent Handoff 企業支援系統

Agent 架構（移植自 Lab5）：
- TriageAgent：分流代理，負責判斷問題類別並轉交給對應專責代理
- HRAgent：人資代理，處理薪資、福利、假期等問題
- ITAgent：IT 代理，處理系統使用、帳號管理、軟硬體支援等問題
- ComplianceAgent：合規代理，處理法規遵循等問題

環境變數需求：
- LINE_CHANNEL_ACCESS_TOKEN：LINE Channel Access Token
- LINE_CHANNEL_SECRET：LINE Channel Secret
- OPENAI_API_KEY：OpenAI API 金鑰
- OPENAI_MODEL：使用的模型名稱（預設 gpt-4o）
"""

import os
from typing import TypedDict, Literal
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END


# =============================================================================
# 環境變數載入
# =============================================================================
load_dotenv()


# =============================================================================
# LINE Bot 設定
# =============================================================================
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# 驗證 LINE 設定是否存在
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    raise ValueError(
        "請設定 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET 環境變數"
    )

# 建立 LINE Bot 設定
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# =============================================================================
# LLM 設定
# =============================================================================
def create_llm():
    """
    建立 LLM 實例

    Returns:
        ChatOpenAI: 設定好的 LLM 實例
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("請設定 OPENAI_API_KEY 環境變數")

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
    return ChatOpenAI(model=model_name, temperature=0.7)


# =============================================================================
# 狀態定義（移植自 Lab5）
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
    user_question: str
    question_category: str
    agent_response: str


# =============================================================================
# Agent 節點定義（移植自 Lab5）
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
    """
    print(f"[TriageAgent] 正在分析問題類別...")

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

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"請分類以下問題：{state['user_question']}"),
    ]

    response = llm.invoke(messages)
    category = response.content.strip().lower()

    # 確保分類結果有效
    valid_categories = ["hr", "it", "compliance"]
    if category not in valid_categories:
        category = "it"

    print(f"[TriageAgent] 判斷此問題屬於：{category}")
    return {"question_category": category}


def hr_agent(state: SupportState) -> dict:
    """
    人資代理（HRAgent）

    職責：處理人資相關問題，包括薪資、福利、假期等。

    Args:
        state: 當前狀態

    Returns:
        dict: 包含 agent_response 的更新狀態
    """
    print(f"[HRAgent] 正在處理人資相關問題...")

    llm = create_llm()

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
如果問題超出你的專業範圍，請建議員工聯繫其他部門。
回答請簡潔扼要，適合在 LINE 訊息中閱讀。"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_question"]),
    ]

    response = llm.invoke(messages)
    return {"agent_response": response.content}


def it_agent(state: SupportState) -> dict:
    """
    IT 代理（ITAgent）

    職責：處理 IT 相關問題，包括系統使用、帳號管理、軟硬體支援等。

    Args:
        state: 當前狀態

    Returns:
        dict: 包含 agent_response 的更新狀態
    """
    print(f"[ITAgent] 正在處理 IT 相關問題...")

    llm = create_llm()

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
對於技術問題，請提供簡潔的操作步驟。
如果需要現場支援，請引導員工提交 IT 服務單。
回答請簡潔扼要，適合在 LINE 訊息中閱讀。"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_question"]),
    ]

    response = llm.invoke(messages)
    return {"agent_response": response.content}


def compliance_agent(state: SupportState) -> dict:
    """
    合規代理（ComplianceAgent）

    職責：處理合規相關問題，包括法規遵循、公司政策等。

    Args:
        state: 當前狀態

    Returns:
        dict: 包含 agent_response 的更新狀態
    """
    print(f"[ComplianceAgent] 正在處理合規相關問題...")

    llm = create_llm()

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
強調合規的重要性，但避免使用過於嚴厲的語氣。
回答請簡潔扼要，適合在 LINE 訊息中閱讀。"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_question"]),
    ]

    response = llm.invoke(messages)
    return {"agent_response": response.content}


# =============================================================================
# 路由函數
# =============================================================================
def route_to_specialist(
    state: SupportState,
) -> Literal["hr_agent", "it_agent", "compliance_agent"]:
    """
    路由函數：根據 TriageAgent 的判斷結果，決定下一步要執行哪個 Agent

    Args:
        state: 當前狀態，包含 question_category

    Returns:
        str: 下一個要執行的節點名稱
    """
    category = state["question_category"]

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

    工作流程：
    START → TriageAgent → (條件路由) → HR/IT/Compliance Agent → END

    Returns:
        CompiledGraph: 編譯後的工作流程圖
    """
    # 建立 StateGraph
    workflow = StateGraph(SupportState)

    # 添加節點
    workflow.add_node("triage_agent", triage_agent)
    workflow.add_node("hr_agent", hr_agent)
    workflow.add_node("it_agent", it_agent)
    workflow.add_node("compliance_agent", compliance_agent)

    # 定義邊
    workflow.add_edge(START, "triage_agent")

    # 條件邊（Handoff 核心）
    workflow.add_conditional_edges(
        "triage_agent",
        route_to_specialist,
    )

    # 結束邊
    workflow.add_edge("hr_agent", END)
    workflow.add_edge("it_agent", END)
    workflow.add_edge("compliance_agent", END)

    return workflow.compile()


# =============================================================================
# 處理支援請求
# =============================================================================
def process_support_request(user_question: str) -> str:
    """
    處理一個支援請求

    Args:
        user_question: 使用者的問題

    Returns:
        str: Agent 的回應
    """
    # 建立工作流程
    app = create_support_workflow()

    # 初始化狀態
    initial_state = {
        "user_question": user_question,
        "question_category": "",
        "agent_response": "",
    }

    # 執行工作流程
    final_state = app.invoke(initial_state)

    return final_state["agent_response"]


# =============================================================================
# FastAPI 應用程式
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理

    在應用程式啟動時初始化資源，關閉時釋放資源。
    """
    # 啟動時執行
    print("=" * 60)
    print("Lab8: Linebot + AI Agent 系統啟動")
    print("=" * 60)
    print("\n系統架構：")
    print("  LINE Bot → FastAPI → Multi-Agent Handoff System")
    print("\nAgent 配置：")
    print("  - TriageAgent：問題分流")
    print("  - HRAgent：人資支援")
    print("  - ITAgent：IT 支援")
    print("  - ComplianceAgent：合規支援")
    print("\n等待 LINE Webhook 請求...")
    print("=" * 60)

    yield

    # 關閉時執行
    print("\n系統關閉中...")


# 建立 FastAPI 應用程式
app = FastAPI(
    title="Lab8: Linebot + AI Agent",
    description="LINE Bot 結合 Multi-Agent Handoff 企業支援系統",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """
    根路徑，用於健康檢查
    """
    return {
        "status": "running",
        "service": "Lab8: Linebot + AI Agent",
        "description": "LINE Bot 結合 Multi-Agent Handoff 企業支援系統",
    }


@app.post("/webhook")
async def webhook(request: Request):
    """
    LINE Webhook 端點

    接收來自 LINE Platform 的 Webhook 請求，驗證簽章後處理訊息事件。

    Args:
        request: FastAPI Request 物件

    Returns:
        str: 回應字串
    """
    # 取得 X-Line-Signature header
    signature = request.headers.get("X-Line-Signature", "")

    # 取得請求 body
    body = await request.body()
    body_text = body.decode("utf-8")

    print(f"\n[Webhook] 收到請求")
    print(f"[Webhook] Body: {body_text[:200]}...")

    # 驗證簽章並處理事件
    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        print("[Webhook] 簽章驗證失敗")
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    """
    處理文字訊息事件

    當收到使用者的文字訊息時，使用 Multi-Agent Handoff 系統處理，
    並將結果回覆給使用者。

    Args:
        event: LINE MessageEvent 物件
    """
    # 取得使用者訊息
    user_message = event.message.text
    user_id = event.source.user_id

    print(f"\n[訊息處理] 使用者 {user_id[:8]}... 傳送: {user_message}")

    try:
        # 使用 Multi-Agent Handoff 系統處理訊息
        response = process_support_request(user_message)
        print(f"[訊息處理] AI 回應: {response[:100]}...")

    except Exception as e:
        print(f"[訊息處理] 處理錯誤: {e}")
        response = "抱歉，系統目前發生問題，請稍後再試。"

    # 回覆訊息給使用者
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response)],
            )
        )

    print(f"[訊息處理] 已回覆使用者")


# =============================================================================
# 主程式入口
# =============================================================================
if __name__ == "__main__":
    import uvicorn

    # 取得 PORT 環境變數，預設為 8000
    port = int(os.getenv("PORT", "8000"))

    print(f"\n啟動伺服器於 http://0.0.0.0:{port}")
    print("Webhook URL: http://your-domain:{port}/webhook")

    # 啟動 FastAPI 伺服器
    uvicorn.run(app, host="0.0.0.0", port=port)
