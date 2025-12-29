"""
Lab4: Multi-Agent Sequential - 合約內容審查系統

這是一個 Multi-Agent Sequential 範例，展示如何使用 Sequential Orchestration
編排多個 Agent 依序完成合約內容的多方面審查。

系統包含三個審查階段：
- Agent 1：合約內容文字審查（清晰度、歧義、模糊用語）
- Agent 2：法律風險評估審查（不平等條款、責任限制）
- Agent 3：合約修正建議審查（根據前兩階段意見提出修正）

適用場景：
- 需要多個專業角色依序處理的任務
- 每個階段的輸出是下一階段的輸入
- 需要專業分工的複雜任務
"""

import os
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END


# =============================================================================
# 終端機顏色定義
# =============================================================================


class Colors:
    """終端機顏色代碼"""

    RESET = "\033[0m"
    BOLD = "\033[1m"

    # Agent 顏色
    AGENT1 = "\033[1;33m"  # 粗體黃色 - 文字審查
    AGENT2 = "\033[1;35m"  # 粗體紫色 - 法律風險
    AGENT3 = "\033[1;36m"  # 粗體青色 - 修正建議

    # 其他顏色
    INFO = "\033[90m"  # 灰色 - 資訊
    SUCCESS = "\033[1;32m"  # 粗體綠色 - 成功
    TITLE = "\033[1;34m"  # 粗體藍色 - 標題


# =============================================================================
# 範例合約內容（教學用，寫死在程式中），實際應用可改為從檔案或資料庫讀取
# =============================================================================

SAMPLE_CONTRACT = """
軟體服務合約

甲方：ABC科技股份有限公司（以下簡稱「甲方」）
乙方：使用者（以下簡稱「乙方」）

第一條：服務內容
甲方同意提供乙方使用本公司開發之雲端軟體服務，包括但不限於資料儲存、運算處理等功能。
服務內容可能隨時調整，届時會通知乙方。

第二條：費用與付款
1. 乙方應於每月5號前支付當月服務費用。
2. 若乙方逾期未付款，甲方有權立即終止服務，不另行通知。
3. 所有已支付費用概不退還。

第三條：資料處理
1. 乙方上傳之資料由甲方代為保管。
2. 甲方得使用乙方資料進行服務改善及相關用途。
3. 若發生資料遺失，甲方之賠償責任以該月服務費為上限。

第四條：服務中斷
因任何原因導致服務中斷，甲方不負任何責任。乙方不得以此為由要求退費或賠償。

第五條：智慧財產權
乙方使用本服務所產生之任何成果，其智慧財產權歸甲方所有。

第六條：合約終止
1. 甲方得隨時終止本合約，届時將通知乙方。
2. 合約終止後，乙方資料將於30天內刪除。

第七條：其他
本合約之解釋及爭議處理，雙方同意以甲方所在地法院為管轄法院。
"""


# =============================================================================
# 狀態定義
# =============================================================================
#
# 【StateGraph 狀態管理機制說明】
#
# StateGraph 使用 TypedDict 定義的狀態結構來管理資料流。
# 狀態是一個字典，在整個工作流程中被傳遞和更新。
#
# 狀態傳遞流程：
# 1. 初始狀態由 invoke() 傳入
# 2. 每個節點（Agent）接收當前完整狀態
# 3. 節點返回的字典會「合併」到現有狀態中（不是取代）
# 4. 更新後的狀態傳遞給下一個節點
# 5. 最終狀態由 invoke() 返回
#
# 範例流程：
# initial_state = {contract_content: "...", text_review: "", legal_review: "", revision_suggestions: ""}
#      ↓
# Agent1 返回 {text_review: "審查結果..."} → 合併到狀態
#      ↓
# 狀態變成 {contract_content: "...", text_review: "審查結果...", legal_review: "", revision_suggestions: ""}
#      ↓
# Agent2 接收上述完整狀態，可讀取 text_review
# =============================================================================


class ContractReviewState(TypedDict):
    """
    合約審查狀態

    這是 StateGraph 的核心資料結構，定義了在工作流程中傳遞的所有資料欄位。
    TypedDict 提供型別提示，但實際上是一個普通的 Python 字典。

    【重要】StateGraph 的狀態更新機制：
    - 每個節點函數接收「完整的當前狀態」作為參數
    - 節點函數返回一個字典，只包含「要更新的欄位」
    - StateGraph 會自動將返回的字典「合併」到現有狀態中
    - 未被返回的欄位會保持原值不變
    """

    # 原始合約內容（由 invoke 時的初始狀態提供，各 Agent 都可讀取）
    contract_content: str

    # Agent 1：文字審查結果
    # - 由 agent1_text_review 節點寫入
    # - agent2_legal_review 和 agent3_revision_suggestions 可讀取
    text_review: str

    # Agent 2：法律風險評估結果
    # - 由 agent2_legal_review 節點寫入
    # - agent3_revision_suggestions 可讀取
    legal_review: str

    # Agent 3：修正建議結果
    # - 由 agent3_revision_suggestions 節點寫入
    # - 最終輸出的一部分
    revision_suggestions: str


# =============================================================================
# 環境設定
# =============================================================================


def load_environment():
    """載入環境變數"""
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("請設定 OPENAI_API_KEY 環境變數")

    return api_key


def create_llm():
    """建立 LLM 實例"""
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
    return ChatOpenAI(model=model_name, temperature=0.3, streaming=True)


# =============================================================================
# Agent 節點定義
# =============================================================================


def agent1_text_review(state: ContractReviewState) -> dict:
    """
    Agent 1：合約內容文字審查

    職責：審查合約內容的文字表達是否清晰、無歧義、
    是否有模糊不清的用語或是潛在的灰色地帶

    【狀態傳遞說明】
    輸入 state: 包含初始狀態的完整字典
        - state['contract_content']: 原始合約內容（可讀取）
        - state['text_review']: 空字串（尚未填入）
        - state['legal_review']: 空字串
        - state['revision_suggestions']: 空字串

    輸出 dict: 只返回要更新的欄位
        - {"text_review": "..."}: 此審查結果會被合併到狀態中
        - 其他欄位保持不變
    """
    print(f"\n{Colors.AGENT1}{'='*60}")
    print("【Agent 1】合約內容文字審查")
    print(f"{'='*60}{Colors.RESET}\n")

    llm = create_llm()

    system_prompt = """你是一位專業的合約文字審查專家。

你的任務是審查合約內容的文字表達，找出以下問題：
1. 文字表達不清晰的地方
2. 可能產生歧義的用語
3. 模糊不清或定義不明確的條款
4. 潛在的灰色地帶

請以條列方式說明發現的問題，並引用具體的條款內容。
最後給出文字清晰度的整體評分（1-10分）。"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"請審查以下合約內容：\n\n{state['contract_content']}"),
    ]

    # 串流輸出
    result_content = ""
    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            result_content += chunk.content

    print("\n")

    # 【狀態更新】只返回 text_review 欄位
    # StateGraph 會自動將此結果合併到現有狀態中
    # 合併後狀態: {contract_content: "原始", text_review: "審查結果", legal_review: "", revision_suggestions: ""}
    return {"text_review": result_content}


def agent2_legal_review(state: ContractReviewState) -> dict:
    """
    Agent 2：法律風險評估審查

    職責：評估合約內容可能帶來的法律風險，
    包括不平等條款、責任限制等

    【狀態傳遞說明】
    輸入 state: 包含 Agent 1 結果的完整字典
        - state['contract_content']: 原始合約內容（可讀取）
        - state['text_review']: Agent 1 的審查結果（可讀取，作為參考）
        - state['legal_review']: 空字串（尚未填入）
        - state['revision_suggestions']: 空字串

    輸出 dict: 只返回要更新的欄位
        - {"legal_review": "..."}: 此評估結果會被合併到狀態中
    """
    print(f"\n{Colors.AGENT2}{'='*60}")
    print("【Agent 2】法律風險評估審查")
    print(f"{'='*60}{Colors.RESET}\n")

    llm = create_llm()

    system_prompt = """你是一位專業的法律風險評估專家。

你的任務是評估合約內容可能帶來的法律風險：
1. 不平等條款（明顯偏向一方的條款）
2. 責任限制是否合理
3. 可能違反消費者保護法或其他法規的條款
4. 免責條款是否過於廣泛
5. 權利義務是否對等

請針對每個風險項目說明：
- 問題條款的具體內容
- 風險等級（高/中/低）
- 可能的法律後果

最後給出整體法律風險評分（1-10分，10分為風險最高）。"""

    # 【讀取狀態】包含前一階段的審查結果作為參考
    # state['contract_content'] - 從初始狀態傳入的原始合約
    # state['text_review'] - 從 Agent 1 傳入的文字審查結果
    user_content = f"""請評估以下合約的法律風險：

【合約內容】
{state['contract_content']}

【文字審查意見（參考）】
{state.get('text_review', '尚無')}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    # 串流輸出
    result_content = ""
    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            result_content += chunk.content

    print("\n")

    # 【狀態更新】只返回 legal_review 欄位
    # 合併後狀態: {contract_content: "原始", text_review: "Agent1結果", legal_review: "Agent2結果", revision_suggestions: ""}
    return {"legal_review": result_content}


def agent3_revision_suggestions(state: ContractReviewState) -> dict:
    """
    Agent 3：合約修正建議審查

    職責：根據前兩個階段的審查意見，
    提出合約內容的修正建議

    【狀態傳遞說明】
    輸入 state: 包含 Agent 1 和 Agent 2 結果的完整字典
        - state['contract_content']: 原始合約內容（可讀取）
        - state['text_review']: Agent 1 的審查結果（可讀取）
        - state['legal_review']: Agent 2 的評估結果（可讀取）
        - state['revision_suggestions']: 空字串（尚未填入）

    輸出 dict: 只返回要更新的欄位
        - {"revision_suggestions": "..."}: 此建議會被合併到狀態中
        - 這是最後一個節點，合併後的狀態即為最終輸出
    """
    print(f"\n{Colors.AGENT3}{'='*60}")
    print("【Agent 3】合約修正建議")
    print(f"{'='*60}{Colors.RESET}\n")

    llm = create_llm()

    system_prompt = """你是一位專業的合約修訂顧問。

根據文字審查和法律風險評估的結果，你需要提出具體的修正建議：
1. 針對每個問題條款提出修改建議
2. 提供修改前後的對照
3. 說明修改的理由
4. 按照優先順序排列建議（從最重要到次要）

請確保修改後的條款：
- 文字清晰無歧義
- 權利義務對等
- 符合相關法規
- 保護雙方合法權益"""

    # 【讀取狀態】此 Agent 可以讀取前面所有階段的結果
    # state['contract_content'] - 原始合約（從初始狀態）
    # state['text_review'] - Agent 1 的文字審查結果
    # state['legal_review'] - Agent 2 的法律風險評估結果
    user_content = f"""請根據以下審查結果，提出合約修正建議：

【原始合約內容】
{state['contract_content']}

【文字審查結果】
{state.get('text_review', '尚無')}

【法律風險評估結果】
{state.get('legal_review', '尚無')}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    # 串流輸出
    result_content = ""
    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            result_content += chunk.content

    print("\n")

    # 【狀態更新】返回最後一個欄位
    # 最終狀態: {contract_content: "原始", text_review: "Agent1結果", legal_review: "Agent2結果", revision_suggestions: "Agent3結果"}
    # 此最終狀態會由 workflow.invoke() 返回給調用者
    return {"revision_suggestions": result_content}


# =============================================================================
# 建立工作流程
# =============================================================================


def create_contract_review_workflow():
    """
    建立合約審查工作流程

    使用 LangGraph StateGraph 實現 Sequential Orchestration，
    依序執行三個審查 Agent。

    流程：START -> Agent1 -> Agent2 -> Agent3 -> END

    【StateGraph 工作原理】
    1. StateGraph 以 ContractReviewState 作為狀態類型
    2. 每個節點是一個函數，接收 state 並返回更新
    3. 邊定義了節點的執行順序
    4. compile() 將圖編譯成可執行的工作流程
    """
    # 【建立 StateGraph】
    # 傳入狀態類型 ContractReviewState，StateGraph 會用它來管理狀態
    workflow = StateGraph(ContractReviewState)

    # 【添加節點】每個節點對應一個 Agent 函數
    # 節點名稱（字串）用於定義邊的連接
    # 節點函數簽名：(state: ContractReviewState) -> dict
    workflow.add_node("text_review", agent1_text_review)
    workflow.add_node("legal_review", agent2_legal_review)
    workflow.add_node("revision_suggestions", agent3_revision_suggestions)

    # 【定義邊】決定節點的執行順序
    # add_edge(from, to) 表示從 from 節點執行完後，接著執行 to 節點
    # START 是特殊的起點，END 是特殊的終點
    workflow.add_edge(START, "text_review")           # 起點 -> Agent1
    workflow.add_edge("text_review", "legal_review")  # Agent1 -> Agent2
    workflow.add_edge("legal_review", "revision_suggestions")  # Agent2 -> Agent3
    workflow.add_edge("revision_suggestions", END)    # Agent3 -> 終點

    # 【編譯】將圖編譯成可執行的工作流程
    # 編譯後可以使用 invoke() 或 stream() 執行
    return workflow.compile()


# =============================================================================
# 主程式
# =============================================================================


def print_summary(state: ContractReviewState):
    """印出審查摘要"""
    print(f"\n{Colors.SUCCESS}{'='*60}")
    print("審查完成摘要")
    print(f"{'='*60}{Colors.RESET}\n")

    print(f"{Colors.INFO}合約已經過三階段審查：{Colors.RESET}")
    print(f"  1. {Colors.AGENT1}文字審查{Colors.RESET} - 檢查文字清晰度與歧義")
    print(f"  2. {Colors.AGENT2}法律風險評估{Colors.RESET} - 評估法律風險與不平等條款")
    print(f"  3. {Colors.AGENT3}修正建議{Colors.RESET} - 提出具體修改方案")

    print(f"\n{Colors.INFO}各階段詳細結果已於上方顯示。{Colors.RESET}")


def main():
    """主程式入口"""
    print(f"{Colors.TITLE}{'='*60}")
    print("Lab4: Multi-Agent Sequential - 合約內容審查系統")
    print(f"{'='*60}{Colors.RESET}")

    # 載入環境變數
    try:
        load_environment()
        print(f"\n{Colors.SUCCESS}✓ 環境變數載入成功{Colors.RESET}")
    except ValueError as e:
        print(f"\n✗ 錯誤：{e}")
        return

    # 顯示合約內容
    print(f"\n{Colors.TITLE}{'='*60}")
    print("待審查合約內容")
    print(f"{'='*60}{Colors.RESET}")
    print(SAMPLE_CONTRACT)

    # 建立工作流程
    print(f"\n{Colors.INFO}正在建立審查工作流程...{Colors.RESET}")
    workflow = create_contract_review_workflow()
    print(f"{Colors.SUCCESS}✓ 工作流程建立完成{Colors.RESET}")

    # 顯示流程說明
    print(f"\n{Colors.INFO}審查流程：{Colors.RESET}")
    print(f"  {Colors.AGENT1}[Agent 1: 文字審查]{Colors.RESET}")
    print(f"       ↓")
    print(f"  {Colors.AGENT2}[Agent 2: 法律風險]{Colors.RESET}")
    print(f"       ↓")
    print(f"  {Colors.AGENT3}[Agent 3: 修正建議]{Colors.RESET}")

    # 執行審查
    print(f"\n{Colors.INFO}開始執行合約審查...{Colors.RESET}")

    # 【初始狀態】
    # 這是傳入 workflow 的起始狀態
    # - contract_content: 要審查的合約內容
    # - 其他欄位設為空字串，會在各 Agent 執行後被填入
    initial_state = {
        "contract_content": SAMPLE_CONTRACT,
        "text_review": "",        # 將由 Agent 1 填入
        "legal_review": "",       # 將由 Agent 2 填入
        "revision_suggestions": "",  # 將由 Agent 3 填入
    }

    # 【執行工作流程】
    # invoke() 會依序執行: START -> Agent1 -> Agent2 -> Agent3 -> END
    # 每個 Agent 執行後，其返回的字典會被合併到狀態中
    # 最終返回包含所有結果的完整狀態
    final_state = workflow.invoke(initial_state)

    # 【最終狀態】
    # final_state 現在包含所有審查結果：
    # {
    #     "contract_content": "原始合約...",
    #     "text_review": "Agent 1 的文字審查結果...",
    #     "legal_review": "Agent 2 的法律風險評估...",
    #     "revision_suggestions": "Agent 3 的修正建議..."
    # }

    # 印出摘要
    print_summary(final_state)


if __name__ == "__main__":
    main()
