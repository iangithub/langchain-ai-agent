"""
Lab6: Multi-Agent Concurrent - 產品手冊多語言翻譯系統

這是一個 Multi-Agent Concurrent 範例，展示如何使用 Concurrent Orchestration（並行編排）
將同一份輸入同時廣播給多個 Agent 平行處理，最後彙整結果。

應用場景：產品手冊多語言翻譯
將英文產品手冊同時翻譯成中文、日文、法文三種語言。

Agent 架構：
- ChineseTranslatorAgent：負責翻譯成中文
- JapaneseTranslatorAgent：負責翻譯成日文
- FrenchTranslatorAgent：負責翻譯成法文

主要特色：
- 使用 StateGraph 建立工作流程
- 使用 Fan-out 模式實現並行執行
- 三個翻譯 Agent 同時運作
- 使用 Aggregator 彙整所有翻譯結果
"""

import os
from typing import TypedDict, Annotated
import operator
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
    讓不同語言的翻譯結果更容易區分。
    """

    # 重置顏色
    RESET = "\033[0m"

    # 粗體顏色
    BOLD = "\033[1m"
    BOLD_GREEN = "\033[1;32m"
    BOLD_BLUE = "\033[1;34m"
    BOLD_CYAN = "\033[1;36m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_MAGENTA = "\033[1;35m"
    BOLD_RED = "\033[1;31m"

    # 角色顏色定義
    USER = "\033[1;32m"      # 粗體綠色 - 使用者
    CHINESE = "\033[1;31m"   # 粗體紅色 - 中文翻譯
    JAPANESE = "\033[1;35m"  # 粗體紫色 - 日文翻譯
    FRENCH = "\033[1;34m"    # 粗體藍色 - 法文翻譯
    SYSTEM = "\033[90m"      # 灰色 - 系統訊息
    AGGREGATOR = "\033[1;33m"  # 粗體黃色 - 彙整結果


# =============================================================================
# 狀態定義
# =============================================================================
class TranslationState(TypedDict):
    """
    多語言翻譯系統的狀態定義

    這個 TypedDict 定義了在整個工作流程中傳遞的狀態結構。

    Concurrent（並行）執行的狀態管理重點：
    1. 原始內容（source_content）：所有 Agent 共享的輸入
    2. 各語言翻譯結果：每個 Agent 獨立更新自己負責的欄位
    3. 彙整結果（aggregated_result）：最後由 Aggregator 整合

    並行執行時，LangGraph 會確保狀態的正確合併：
    - 每個 Agent 只更新自己負責的欄位
    - LangGraph 自動將所有更新合併到最終狀態
    """

    # 原始英文內容（輸入）
    source_content: str

    # 各語言的翻譯結果（並行執行時各自更新）
    chinese_translation: str
    japanese_translation: str
    french_translation: str

    # 彙整後的完整結果
    aggregated_result: str


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

def chinese_translator_agent(state: TranslationState) -> dict:
    """
    中文翻譯代理（ChineseTranslatorAgent）

    職責：將英文產品手冊翻譯成繁體中文，保留原文的語氣和風格。

    並行執行說明：
    - 此 Agent 與其他翻譯 Agent 同時執行
    - 只更新 chinese_translation 欄位
    - LangGraph 會自動將結果合併到主狀態

    Args:
        state: 當前狀態，包含 source_content

    Returns:
        dict: 包含 chinese_translation 的更新狀態
    """
    print(f"\n{Colors.CHINESE}[ChineseTranslatorAgent]{Colors.RESET} 開始翻譯成中文...")
    print("-" * 50)

    llm = create_llm()

    # 中文翻譯代理的系統提示詞
    system_prompt = """你是一位專業的英文到繁體中文翻譯專家。

你的任務是將產品手冊從英文翻譯成繁體中文。

翻譯原則：
1. 保持原文的專業語氣和風格
2. 使用繁體中文，符合台灣用語習慣
3. 技術術語使用業界通用的中文翻譯
4. 確保翻譯流暢自然，易於理解
5. 保留產品名稱的英文原文（可加註中文說明）

請直接輸出翻譯結果，不需要額外說明。"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"請將以下產品手冊翻譯成繁體中文：\n\n{state['source_content']}")
    ]

    # 串流輸出翻譯結果
    print(f"{Colors.CHINESE}[中文翻譯]{Colors.RESET}:\n")
    full_response = ""

    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_response += chunk.content

    print("\n")

    # 返回更新的狀態
    # 只更新 chinese_translation 欄位，其他欄位保持不變
    return {"chinese_translation": full_response}


def japanese_translator_agent(state: TranslationState) -> dict:
    """
    日文翻譯代理（JapaneseTranslatorAgent）

    職責：將英文產品手冊翻譯成日文，保留原文的語氣和風格。

    並行執行說明：
    - 此 Agent 與其他翻譯 Agent 同時執行
    - 只更新 japanese_translation 欄位
    - LangGraph 會自動將結果合併到主狀態

    Args:
        state: 當前狀態，包含 source_content

    Returns:
        dict: 包含 japanese_translation 的更新狀態
    """
    print(f"\n{Colors.JAPANESE}[JapaneseTranslatorAgent]{Colors.RESET} 開始翻譯成日文...")
    print("-" * 50)

    llm = create_llm()

    # 日文翻譯代理的系統提示詞
    system_prompt = """あなたはプロの英日翻訳者です。

製品マニュアルを英語から日本語に翻訳することがあなたの任務です。

翻訳の原則：
1. 原文のプロフェッショナルなトーンとスタイルを維持する
2. 自然で読みやすい日本語を使用する
3. 技術用語は業界標準の日本語訳を使用する
4. 敬語を適切に使用し、丁寧な表現を心がける
5. 製品名は英語のまま残す（必要に応じて日本語の説明を追加）

翻訳結果のみを出力してください。追加の説明は不要です。"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"以下の製品マニュアルを日本語に翻訳してください：\n\n{state['source_content']}")
    ]

    # 串流輸出翻譯結果
    print(f"{Colors.JAPANESE}[日文翻譯]{Colors.RESET}:\n")
    full_response = ""

    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_response += chunk.content

    print("\n")

    # 返回更新的狀態
    return {"japanese_translation": full_response}


def french_translator_agent(state: TranslationState) -> dict:
    """
    法文翻譯代理（FrenchTranslatorAgent）

    職責：將英文產品手冊翻譯成法文，保留原文的語氣和風格。

    並行執行說明：
    - 此 Agent 與其他翻譯 Agent 同時執行
    - 只更新 french_translation 欄位
    - LangGraph 會自動將結果合併到主狀態

    Args:
        state: 當前狀態，包含 source_content

    Returns:
        dict: 包含 french_translation 的更新狀態
    """
    print(f"\n{Colors.FRENCH}[FrenchTranslatorAgent]{Colors.RESET} 開始翻譯成法文...")
    print("-" * 50)

    llm = create_llm()

    # 法文翻譯代理的系統提示詞
    system_prompt = """Vous êtes un traducteur professionnel anglais-français.

Votre tâche est de traduire le manuel du produit de l'anglais vers le français.

Principes de traduction :
1. Maintenir le ton professionnel et le style du texte original
2. Utiliser un français naturel et fluide
3. Utiliser les termes techniques standards en français
4. Adapter les expressions idiomatiques au contexte français
5. Conserver les noms de produits en anglais (avec explication en français si nécessaire)

Veuillez fournir uniquement la traduction, sans explications supplémentaires."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Veuillez traduire le manuel produit suivant en français :\n\n{state['source_content']}")
    ]

    # 串流輸出翻譯結果
    print(f"{Colors.FRENCH}[法文翻譯]{Colors.RESET}:\n")
    full_response = ""

    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_response += chunk.content

    print("\n")

    # 返回更新的狀態
    return {"french_translation": full_response}


def aggregator(state: TranslationState) -> dict:
    """
    結果彙整節點（Aggregator）

    職責：將所有翻譯 Agent 的結果彙整成一份完整的多語言翻譯報告。

    Fan-in 模式說明：
    - 此節點在所有翻譯 Agent 完成後執行
    - 讀取所有翻譯結果並彙整
    - 這是 Concurrent Orchestration 的「收斂」點

    Args:
        state: 包含所有翻譯結果的狀態

    Returns:
        dict: 包含 aggregated_result 的更新狀態
    """
    print(f"\n{Colors.AGGREGATOR}[Aggregator]{Colors.RESET} 彙整所有翻譯結果...")
    print("=" * 60)

    # 彙整所有翻譯結果
    aggregated = f"""
{'=' * 60}
多語言翻譯結果彙整
{'=' * 60}

【原文 (English)】
{state['source_content']}

{'─' * 60}

【繁體中文翻譯】
{state['chinese_translation']}

{'─' * 60}

【日本語翻訳】
{state['japanese_translation']}

{'─' * 60}

【Traduction française】
{state['french_translation']}

{'=' * 60}
翻譯完成！共產生 3 種語言版本。
{'=' * 60}
"""

    print(f"{Colors.AGGREGATOR}[彙整完成]{Colors.RESET}")

    return {"aggregated_result": aggregated}


# =============================================================================
# 建立工作流程
# =============================================================================

def create_translation_workflow():
    """
    建立多語言翻譯系統的工作流程

    Concurrent Orchestration 工作流程說明：
    ┌─────────────────────────────────────────────────────────────┐
    │                  Concurrent Orchestration                    │
    ├─────────────────────────────────────────────────────────────┤
    │                                                              │
    │   START                                                      │
    │     │                                                        │
    │     │ Fan-out（扇出）：同時廣播到多個節點                      │
    │     │                                                        │
    │     ├──────────────┬──────────────┐                          │
    │     │              │              │                          │
    │     ▼              ▼              ▼                          │
    │  ┌──────┐     ┌──────┐      ┌──────┐                         │
    │  │中文  │     │日文  │      │法文  │   ← 並行執行             │
    │  │翻譯  │     │翻譯  │      │翻譯  │                         │
    │  └──┬───┘     └──┬───┘      └──┬───┘                         │
    │     │            │             │                             │
    │     │ Fan-in（扇入）：等待所有節點完成                        │
    │     │            │             │                             │
    │     └────────────┼─────────────┘                             │
    │                  │                                           │
    │                  ▼                                           │
    │            ┌──────────┐                                      │
    │            │Aggregator│  ← 彙整結果                          │
    │            └────┬─────┘                                      │
    │                 │                                            │
    │                 ▼                                            │
    │                END                                           │
    │                                                              │
    └─────────────────────────────────────────────────────────────┘

    Returns:
        CompiledGraph: 編譯後的工作流程圖
    """
    # ==========================================================================
    # 步驟 1：建立 StateGraph
    # ==========================================================================
    workflow = StateGraph(TranslationState)

    # ==========================================================================
    # 步驟 2：添加節點
    # ==========================================================================
    # 三個翻譯 Agent 節點（將並行執行）
    workflow.add_node("chinese_translator", chinese_translator_agent)
    workflow.add_node("japanese_translator", japanese_translator_agent)
    workflow.add_node("french_translator", french_translator_agent)

    # 彙整節點（等待所有翻譯完成後執行）
    workflow.add_node("aggregator", aggregator)

    # ==========================================================================
    # 步驟 3：定義 Fan-out 邊（扇出 - 並行分發）
    # ==========================================================================
    # 從 START 同時連接到三個翻譯節點
    # LangGraph 會並行執行這三個節點
    #
    # 關鍵概念：
    # - 當一個節點有多個出邊時，LangGraph 會並行執行所有目標節點
    # - 這就是 Fan-out（扇出）模式
    workflow.add_edge(START, "chinese_translator")
    workflow.add_edge(START, "japanese_translator")
    workflow.add_edge(START, "french_translator")

    # ==========================================================================
    # 步驟 4：定義 Fan-in 邊（扇入 - 等待並收斂）
    # ==========================================================================
    # 所有翻譯節點都連接到 aggregator
    # LangGraph 會等待所有翻譯完成後，才執行 aggregator
    #
    # 關鍵概念：
    # - 當多個節點都指向同一個節點時，該節點會等待所有前置節點完成
    # - 這就是 Fan-in（扇入）模式
    # - aggregator 會收到包含所有翻譯結果的完整狀態
    workflow.add_edge("chinese_translator", "aggregator")
    workflow.add_edge("japanese_translator", "aggregator")
    workflow.add_edge("french_translator", "aggregator")

    # ==========================================================================
    # 步驟 5：定義結束邊
    # ==========================================================================
    workflow.add_edge("aggregator", END)

    # ==========================================================================
    # 步驟 6：編譯工作流程
    # ==========================================================================
    return workflow.compile()


# =============================================================================
# 範例產品手冊
# =============================================================================

SAMPLE_PRODUCT_MANUAL = """
AirPure Pro - Smart Air Purifier

Product Overview:
The AirPure Pro is a next-generation smart air purifier designed for modern homes.
With its advanced HEPA-13 filtration system, it captures 99.97% of airborne particles
as small as 0.3 microns, including dust, pollen, and pet dander.

Key Features:
1. Smart Air Quality Monitoring - Real-time PM2.5, VOC, and humidity detection
2. App Control - Control your purifier from anywhere using our mobile app
3. Ultra-Quiet Operation - As low as 25dB, perfect for bedrooms
4. Coverage Area - Suitable for rooms up to 500 sq ft (46 sq m)
5. Energy Efficient - ENERGY STAR certified, uses only 45W on high setting

Getting Started:
1. Remove the purifier from packaging
2. Remove the plastic wrap from the filter
3. Install the filter and close the back panel
4. Plug in and press the power button
5. Download the AirPure app to connect via WiFi

Maintenance:
- Replace the HEPA filter every 6-12 months depending on usage
- Clean the pre-filter monthly with a vacuum
- Wipe the exterior with a soft, damp cloth

For support, visit www.airpure.com/support or call 1-800-AIR-PURE.
"""


# =============================================================================
# 執行翻譯請求
# =============================================================================

def process_translation_request(app, content: str) -> str:
    """
    處理一個翻譯請求

    Args:
        app: 編譯後的工作流程
        content: 要翻譯的英文內容

    Returns:
        str: 彙整後的翻譯結果
    """
    # 初始化狀態
    initial_state = {
        "source_content": content,
        "chinese_translation": "",
        "japanese_translation": "",
        "french_translation": "",
        "aggregated_result": ""
    }

    # 執行工作流程
    # invoke 會執行整個工作流程
    # 三個翻譯 Agent 會並行執行，完成後 aggregator 彙整結果
    final_state = app.invoke(initial_state)

    return final_state["aggregated_result"]


# =============================================================================
# 主程式
# =============================================================================

def main():
    """
    主程式入口

    展示 Concurrent Orchestration 的工作流程：
    1. 先執行範例產品手冊的翻譯示範
    2. 進入互動模式，讓使用者輸入自己的內容進行翻譯
    """
    print("=" * 60)
    print("Lab6: Multi-Agent Concurrent - 產品手冊多語言翻譯系統")
    print("=" * 60)

    # 載入環境變數
    try:
        load_environment()
        print("\n✓ 環境變數載入成功")
    except ValueError as e:
        print(f"\n✗ 錯誤：{e}")
        return

    # 建立工作流程
    print("\n正在建立翻譯系統工作流程...")
    app = create_translation_workflow()
    print("✓ 工作流程建立完成")

    # 顯示系統架構
    print("\n" + "=" * 60)
    print("系統架構 - Concurrent Orchestration")
    print("=" * 60)
    print("""
         ┌─────────────┐
         │  英文原文   │
         └──────┬──────┘
                │
        ┌───────┼───────┐  Fan-out（並行分發）
        │       │       │
        ▼       ▼       ▼
    ┌──────┐┌──────┐┌──────┐
    │ 中文 ││ 日文 ││ 法文 │  ← 同時執行
    │ 翻譯 ││ 翻譯 ││ 翻譯 │
    └──┬───┘└──┬───┘└──┬───┘
       │       │       │
       └───────┼───────┘  Fan-in（等待並收斂）
               │
               ▼
        ┌────────────┐
        │ Aggregator │  ← 彙整結果
        └─────┬──────┘
              │
              ▼
      ┌──────────────┐
      │ 多語言翻譯結果 │
      └──────────────┘
    """)

    # 示範翻譯
    print("=" * 60)
    print("示範：翻譯產品手冊")
    print("=" * 60)

    print(f"\n{Colors.USER}[原文]{Colors.RESET}:")
    print(SAMPLE_PRODUCT_MANUAL)

    print("\n" + "=" * 60)
    print("開始並行翻譯...")
    print("（三個翻譯 Agent 同時工作）")
    print("=" * 60)

    result = process_translation_request(app, SAMPLE_PRODUCT_MANUAL)
    print(result)

    # 互動模式
    print("\n" + "=" * 60)
    print("互動模式（輸入 'quit' 結束）")
    print("=" * 60)
    print("\n輸入英文文字，系統會自動翻譯成三種語言。")
    print("可以輸入多行，輸入空行後按 Enter 開始翻譯。")

    while True:
        try:
            print(f"\n{Colors.USER}[請輸入英文內容（輸入空行結束）]{Colors.RESET}:")
            lines = []
            while True:
                line = input()
                if line.lower() == "quit":
                    print("\n感謝使用多語言翻譯系統，再見！")
                    return
                if line == "":
                    break
                lines.append(line)

            if not lines:
                continue

            content = "\n".join(lines)

            print("\n" + "=" * 60)
            print("開始並行翻譯...")
            print("=" * 60)

            result = process_translation_request(app, content)
            print(result)

        except (EOFError, KeyboardInterrupt):
            print("\n\n感謝使用多語言翻譯系統，再見！")
            break


if __name__ == "__main__":
    main()
