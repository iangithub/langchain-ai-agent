"""
Lab2: Single-Agent 行銷文案生成器（使用 create_agent 方式）

這是一個 Single-Agent 範例，與 Lab1 功能相同，但改用 LangChain 1.x 的
create_agent 方式實作，展示 LangChain 1.x 新的 Agent 建立標準。

主要差異：
- Lab1: 使用 LCEL (prompt | llm | output_parser) 串接
- Lab2: 使用 create_agent 函數建立 Agent，搭配 Tool 使用

本範例包含兩種回應模式：
- invoke: 一次性取得完整回應
- stream: 串流式逐步輸出回應（即時顯示生成過程）

適用場景：
- 需要使用 Tools 的任務
- 需要 Agent 自主決策的流程
- 需要擴展更多功能的應用
"""

import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain.chat_models import init_chat_model


def load_environment():
    """
    載入環境變數

    從 .env 檔案載入 API 金鑰和模型設定。
    確保在執行前已正確設定環境變數。
    """
    load_dotenv()

    # 檢查必要的環境變數
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("請設定 OPENAI_API_KEY 環境變數")

    return api_key


@tool
def generate_marketing_copy(
    product_name: str, product_features: str, target_audience: str, marketing_goal: str
) -> str:
    """
    根據產品資訊生成行銷文案。

    這個工具會根據提供的產品資訊，生成一份專業的行銷文案，
    包含吸引人的標題、副標題、正文和行動呼籲。

    Args:
        product_name: 產品名稱
        product_features: 產品特點和賣點
        target_audience: 目標受眾描述
        marketing_goal: 行銷目標（如提升知名度、促進銷售等）

    Returns:
        str: 生成的完整行銷文案
    """
    # 這個 Tool 主要用於讓 Agent 知道如何處理行銷文案請求
    # 實際的文案生成會由 Agent 內部的 LLM 完成
    return f"""請根據以下資訊生成行銷文案：
產品名稱：{product_name}
產品特點：{product_features}
目標受眾：{target_audience}
行銷目標：{marketing_goal}

請按照以下格式輸出：
【標題】一句話吸引眼球的標題
【副標題】補充說明，強化標題訴求
【正文】詳細的行銷文案內容，3-5段
【行動呼籲】引導讀者採取行動的結尾"""


def create_marketing_agent():
    """
    使用 create_agent 建立行銷文案 Agent

    這是 LangChain 1.x 推薦的 Agent 建立方式，
    透過 create_agent 函數簡化 Agent 的建立過程。

    Returns:
        Agent: 配置好的行銷文案 Agent
    """
    # 從環境變數取得模型名稱
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o")

    # 定義系統提示詞
    system_prompt = """你是一位專業的行銷文案撰寫專家，擅長創作吸引人且具說服力的行銷內容。

你的專長包括：
1. 撰寫吸引眼球的標題，能在3秒內抓住讀者注意力
2. 創作具有情感連結的文案，讓讀者產生共鳴
3. 設計有效的行動呼籲（Call to Action）
4. 根據不同目標受眾調整文案風格

當使用者提供產品資訊時，請使用 generate_marketing_copy 工具來生成專業的行銷文案。
確保文案突出產品的核心價值和獨特賣點。"""

    # 使用 create_agent 建立 Agent
    # 這是 LangChain 1.x 的新標準 API
    agent = create_agent(
        model=model_name, tools=[generate_marketing_copy], system_prompt=system_prompt
    )

    return agent


def run_marketing_agent(product_info: dict) -> str:
    """
    執行行銷文案 Agent

    Args:
        product_info: 包含產品資訊的字典
            - product_name: 產品名稱
            - product_features: 產品特點
            - target_audience: 目標受眾
            - marketing_goal: 行銷目標

    Returns:
        str: Agent 生成的回應
    """
    # 建立 Agent
    agent = create_marketing_agent()

    # 組合使用者訊息
    user_message = f"""請幫我撰寫以下產品的行銷文案：

產品名稱：{product_info['product_name']}
產品特點：{product_info['product_features']}
目標受眾：{product_info['target_audience']}
行銷目標：{product_info['marketing_goal']}

請生成一份完整的行銷文案，包含標題、副標題、正文和行動呼籲。"""

    # 使用 invoke 執行 Agent
    # create_agent 使用 messages 格式作為輸入
    result = agent.invoke({"messages": [{"role": "user", "content": user_message}]})

    # 從結果中提取回應內容
    # create_agent 的回傳格式包含 messages 列表
    if "messages" in result:
        # 取得最後一條 AI 訊息
        for msg in reversed(result["messages"]):
            if hasattr(msg, "content") and msg.content:
                return msg.content

    return str(result)


def stream_marketing_agent(product_info: dict) -> None:
    """
    使用串流模式執行行銷文案 Agent

    串流模式會即時輸出 Agent 生成的內容，而不是等待完整回應。
    這對於長文本生成特別有用，可以讓使用者即時看到生成過程。

    Args:
        product_info: 包含產品資訊的字典
            - product_name: 產品名稱
            - product_features: 產品特點
            - target_audience: 目標受眾
            - marketing_goal: 行銷目標
    """
    # 建立 Agent
    agent = create_marketing_agent()

    # 組合使用者訊息
    user_message = f"""請幫我撰寫以下產品的行銷文案：

產品名稱：{product_info['product_name']}
產品特點：{product_info['product_features']}
目標受眾：{product_info['target_audience']}
行銷目標：{product_info['marketing_goal']}

請生成一份完整的行銷文案，包含標題、副標題、正文和行動呼籲。"""

    # 使用 stream 執行 Agent
    # stream() 會返回一個生成器，逐步產出回應內容
    print("=" * 60)
    print("Agent 生成的行銷文案（串流模式）")
    print("=" * 60)

    # 使用 stream_mode="messages" 進行 token 級別的串流
    # 返回格式為 (message_chunk, metadata) 元組
    for message_chunk, metadata in agent.stream(
        {"messages": [{"role": "user", "content": user_message}]},
        stream_mode="messages"
    ):
        # message_chunk 包含 LLM 串流的 token
        if message_chunk.content:
            # 即時輸出內容，不換行
            print(message_chunk.content, end="", flush=True)

    # 結束後換行
    print("\n" + "=" * 60)


def stream_marketing_agent_detailed(product_info: dict) -> None:
    """
    使用串流模式執行 Agent，並顯示詳細的事件資訊

    這個函數展示如何處理串流中的各種事件類型，
    包括工具呼叫、中間步驟等詳細資訊。

    Args:
        product_info: 包含產品資訊的字典
    """
    # 建立 Agent
    agent = create_marketing_agent()

    # 組合使用者訊息
    user_message = f"""請幫我撰寫以下產品的行銷文案：

產品名稱：{product_info['product_name']}
產品特點：{product_info['product_features']}
目標受眾：{product_info['target_audience']}
行銷目標：{product_info['marketing_goal']}

請生成一份完整的行銷文案，包含標題、副標題、正文和行動呼籲。"""

    print("=" * 60)
    print("Agent 串流執行（詳細模式）")
    print("=" * 60)
    print("顯示 token 串流及其 metadata 資訊\n")

    # 使用 stream_mode="messages" 進行 token 級別串流
    # 同時顯示每個 chunk 的 metadata 資訊
    current_node = None

    for message_chunk, metadata in agent.stream(
        {"messages": [{"role": "user", "content": user_message}]},
        stream_mode="messages"
    ):
        # 檢查是否切換到新節點
        node_name = metadata.get("langgraph_node", "unknown")
        if node_name != current_node:
            current_node = node_name
            print(f"\n\n[節點: {node_name}]")
            print(f"[訊息類型: {type(message_chunk).__name__}]")
            print("-" * 40)

        # 顯示串流內容
        if message_chunk.content:
            print(message_chunk.content, end="", flush=True)

        # 顯示工具呼叫資訊
        if hasattr(message_chunk, "tool_calls") and message_chunk.tool_calls:
            for tool_call in message_chunk.tool_calls:
                print(f"\n[工具呼叫: {tool_call.get('name', 'unknown')}]")
                print(f"[參數: {tool_call.get('args', {})}]")

        # 顯示工具呼叫的 chunk（部分參數）
        if hasattr(message_chunk, "tool_call_chunks") and message_chunk.tool_call_chunks:
            for tc_chunk in message_chunk.tool_call_chunks:
                if tc_chunk.get("name"):
                    print(f"\n[工具: {tc_chunk.get('name')}]", end="", flush=True)
                if tc_chunk.get("args"):
                    print(tc_chunk.get("args"), end="", flush=True)

    print("\n\n" + "=" * 60)


def main():
    """
    主程式入口

    展示如何使用 create_agent 方式建立並執行行銷文案 Agent。
    提供三種執行模式：一般模式、串流模式、串流詳細模式。
    """
    print("=" * 60)
    print("Lab2: Single-Agent 行銷文案生成器")
    print("（使用 LangChain 1.x create_agent 方式）")
    print("=" * 60)

    # 載入環境變數
    try:
        load_environment()
        print("\n✓ 環境變數載入成功")
    except ValueError as e:
        print(f"\n✗ 錯誤：{e}")
        return

    # 範例產品資訊
    sample_product = {
        "product_name": "智能空氣清淨機 AirPure Pro",
        "product_features": "HEPA 13級濾網、智能空氣品質偵測、App遠端控制、超靜音設計（僅25分貝）、適用30坪空間",
        "target_audience": "注重生活品質的都市家庭，特別是有小孩或過敏體質的家庭",
        "marketing_goal": "提升品牌知名度，促進線上購買轉換",
    }

    print("\n" + "-" * 60)
    print("使用範例產品資訊生成文案...")
    print("-" * 60)
    print(f"產品名稱：{sample_product['product_name']}")
    print(f"產品特點：{sample_product['product_features']}")
    print(f"目標受眾：{sample_product['target_audience']}")
    print(f"行銷目標：{sample_product['marketing_goal']}")
    print("-" * 60)

    # 選擇執行模式
    print("\n請選擇執行模式：")
    print("1. 一般模式 (invoke) - 等待完整回應")
    print("2. 串流模式 (stream) - 即時顯示生成過程")
    print("3. 串流詳細模式 (stream detailed) - 顯示詳細事件資訊")

    try:
        choice = input("\n請輸入選項 (1/2/3，預設為 2): ").strip() or "2"
    except EOFError:
        # 非互動模式時使用預設值
        choice = "2"

    print()

    try:
        if choice == "1":
            # 一般模式：使用 invoke
            print("正在執行 Agent 生成行銷文案（一般模式）...\n")
            result = run_marketing_agent(sample_product)
            print("=" * 60)
            print("Agent 生成的行銷文案")
            print("=" * 60)
            print(result)
            print("=" * 60)

        elif choice == "3":
            # 串流詳細模式：顯示所有事件
            print("正在執行 Agent 生成行銷文案（串流詳細模式）...\n")
            stream_marketing_agent_detailed(sample_product)

        else:
            # 串流模式：即時輸出（預設）
            print("正在執行 Agent 生成行銷文案（串流模式）...\n")
            stream_marketing_agent(sample_product)

    except Exception as e:
        print(f"\n✗ 執行失敗：{e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
