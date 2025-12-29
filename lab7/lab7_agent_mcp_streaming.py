"""
Lab7: Agent 系統透過 Streamable HTTP 連接 MCP Server

這是一個展示如何使用 LangChain MCP Adapters 連接 MCP Server 的範例。
Agent 透過 Streamable HTTP 傳輸模式連接到 MCP Server，
取得產品資訊查詢和訂單狀態查詢工具，並使用這些工具回應使用者查詢。

主要特色：
- 使用 langchain-mcp-adapters 連接 MCP Server
- Streamable HTTP 傳輸模式
- 動態載入 MCP Server 提供的工具
- 使用 create_agent 建立 Agent

使用方式：
1. 先啟動 MCP Server：python mcpserver/mcp_server.py
2. 再執行此程式：python lab7/lab7_agent_mcp_streaming.py
"""

import os
import asyncio
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient


# =============================================================================
# 終端機顏色定義
# =============================================================================
class Colors:
    """
    終端機顏色代碼

    使用 ANSI 轉義序列在終端機中顯示彩色文字。
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

    # 角色顏色定義
    USER = "\033[1;32m"  # 粗體綠色 - 使用者
    ASSISTANT = "\033[1;36m"  # 粗體青色 - 助理
    SYSTEM = "\033[1;33m"  # 粗體黃色 - 系統訊息
    TOOL = "\033[1;35m"  # 粗體紫色 - 工具呼叫
    INFO = "\033[90m"  # 灰色 - 資訊


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


# =============================================================================
# MCP Client 設定
# =============================================================================

# MCP Server 連線設定
MCP_SERVER_CONFIG = {
    "product_order_service": {
        "url": "http://localhost:8000/mcp",
        "transport": "streamable_http",
    }
}


# =============================================================================
# Agent 建立與執行
# =============================================================================


async def create_mcp_agent():
    """
    建立連接 MCP Server 的 Agent

    使用 MultiServerMCPClient 連接到 MCP Server，
    取得可用的工具，並建立 Agent。

    Returns:
        tuple: (agent, mcp_client) 包含 Agent 實例和 MCP 客戶端
    """
    print(f"\n{Colors.SYSTEM}[系統]{Colors.RESET} 正在連接 MCP Server...")

    # 建立 MCP 客戶端
    # MultiServerMCPClient 可以同時連接多個 MCP Server
    mcp_client = MultiServerMCPClient(MCP_SERVER_CONFIG)

    # 取得 MCP Server 提供的工具
    # 這會將 MCP 工具轉換為 LangChain 相容的工具格式
    tools = await mcp_client.get_tools()

    print(f"{Colors.SYSTEM}[系統]{Colors.RESET} 成功連接 MCP Server")
    print(f"{Colors.INFO}[資訊]{Colors.RESET} 載入的工具：")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:50]}...")

    # 從環境變數取得模型名稱
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o")

    # 定義系統提示詞
    system_prompt = """你是一位專業的客戶服務助理，負責幫助客戶查詢產品資訊和訂單狀態。

你可以使用以下工具來協助客戶：
1. get_product_info - 查詢產品的詳細資訊（名稱、描述、價格、庫存等）
2. get_order_status - 查詢訂單的當前狀態（處理進度、配送資訊等）
3. list_available_products - 列出所有可查詢的產品
4. list_sample_orders - 列出範例訂單號碼供測試

服務原則：
1. 親切有禮，使用繁體中文回應
2. 主動提供完整的資訊
3. 如果客戶詢問的產品或訂單找不到，引導客戶提供正確資訊
4. 適時推薦相關產品或服務

請根據客戶的需求，選擇適當的工具來查詢資訊並回應。"""

    # 使用 create_agent 建立 Agent
    agent = create_agent(
        model=model_name,
        tools=tools,
        system_prompt=system_prompt,
    )

    return agent, mcp_client


async def stream_chat(agent, user_message: str) -> None:
    """
    以串流方式進行對話

    Args:
        agent: Agent 實例
        user_message: 使用者訊息
    """
    print(f"\n{Colors.USER}[使用者]{Colors.RESET}: {user_message}")
    print("-" * 60)
    print(f"{Colors.ASSISTANT}[助理]{Colors.RESET}: ", end="", flush=True)

    # 使用 stream_mode="messages" 進行 token 級別串流
    current_node = None

    async for message_chunk, metadata in agent.astream(
        {"messages": [{"role": "user", "content": user_message}]},
        stream_mode="messages",
    ):
        # 檢查是否有節點切換（用於顯示工具呼叫資訊）
        node_name = metadata.get("langgraph_node", "")

        # 如果是工具呼叫節點，顯示工具資訊
        if node_name == "tools" and node_name != current_node:
            if hasattr(message_chunk, "name") and message_chunk.name:
                print(f"\n{Colors.TOOL}[工具呼叫: {message_chunk.name}]{Colors.RESET}")
            current_node = node_name
        elif node_name != "tools":
            current_node = node_name

        # 輸出內容
        if message_chunk.content:
            print(message_chunk.content, end="", flush=True)

    print("\n")


async def run_demo():
    """
    執行展示模式

    展示 Agent 如何使用 MCP 工具回應各種查詢。
    """
    print("\n" + "=" * 60)
    print("展示：Agent 使用 MCP 工具回應查詢")
    print("=" * 60)

    # 建立 Agent
    agent, mcp_client = await create_mcp_agent()

    # 示範查詢
    demo_queries = [
        "請幫我查詢 AirPure Pro 空氣清淨機的產品資訊",
        "我想查詢訂單 ORD-2024-002 的配送狀態",
        "有哪些產品可以查詢？",
    ]

    for query in demo_queries:
        await stream_chat(agent, query)
        print("=" * 60)


async def run_interactive():
    """
    執行互動模式

    讓使用者自由輸入查詢，Agent 會使用 MCP 工具回應。
    """
    print("\n" + "=" * 60)
    print("互動模式（輸入 'quit' 結束）")
    print("=" * 60)
    print("\n您可以詢問產品資訊或訂單狀態，例如：")
    print("  - 請查詢智能手錶的價格和功能")
    print("  - 訂單 ORD-2024-001 目前的狀態是什麼？")
    print("  - 有什麼產品可以推薦？")

    # 建立 Agent
    agent, mcp_client = await create_mcp_agent()

    while True:
        try:
            user_input = input(f"\n{Colors.USER}[你]{Colors.RESET}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n感謝使用，再見！")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("\n感謝使用，再見！")
            break

        await stream_chat(agent, user_input)


async def main():
    """
    主程式入口

    展示如何透過 Streamable HTTP 連接 MCP Server，
    並使用 MCP 工具建立 Agent 來回應使用者查詢。
    """
    print("=" * 60)
    print("Lab7: Agent 透過 Streamable HTTP 連接 MCP Server")
    print("=" * 60)

    # 載入環境變數
    try:
        load_environment()
        print("\n✓ 環境變數載入成功")
    except ValueError as e:
        print(f"\n✗ 錯誤：{e}")
        return

    # 檢查 MCP Server 連線
    print(
        f"\n{Colors.INFO}[資訊]{Colors.RESET} MCP Server 位置: http://localhost:8000/mcp"
    )
    print(
        f"{Colors.INFO}[提示]{Colors.RESET} 請確認已啟動 MCP Server (python mcpserver/mcp_server.py)"
    )

    # 顯示系統架構
    print("\n" + "=" * 60)
    print("系統架構")
    print("=" * 60)
    print(
        """
    ┌─────────────────┐         ┌─────────────────────────┐
    │                 │  HTTP   │                         │
    │  Agent 系統     │◄───────►│     MCP Server          │
    │  (LangChain)    │Streamable│  (FastMCP + FastAPI)   │
    │                 │         │                         │
    └────────┬────────┘         └────────────┬────────────┘
             │                               │
             │                     ┌─────────┴─────────┐
             │                     │                   │
             ▼                     ▼                   ▼
    ┌─────────────────┐   ┌─────────────┐   ┌─────────────────┐
    │   使用者介面    │   │ 產品查詢工具 │   │ 訂單查詢工具     │
    │   (互動對話)    │   │             │   │                 │
    └─────────────────┘   └─────────────┘   └─────────────────┘
    """
    )

    # 選擇執行模式
    print("\n請選擇執行模式：")
    print("1. 展示模式 - 自動執行範例查詢")
    print("2. 互動模式 - 自由輸入查詢")

    try:
        choice = input("\n請輸入選項 (1/2，預設為 1): ").strip() or "1"
    except EOFError:
        choice = "1"

    try:
        if choice == "2":
            await run_interactive()
        else:
            await run_demo()
            # 展示完成後進入互動模式
            print("\n" + "=" * 60)
            print("展示完成！進入互動模式...")
            await run_interactive()

    except ConnectionError as e:
        print(f"\n{Colors.BOLD_YELLOW}[警告]{Colors.RESET} 無法連接 MCP Server")
        print(f"錯誤訊息：{e}")
        print("\n請確認：")
        print("1. MCP Server 已啟動 (python mcpserver/mcp_server.py)")
        print("2. MCP Server 運行在 http://localhost:8000")

    except Exception as e:
        print(f"\n{Colors.BOLD_YELLOW}[錯誤]{Colors.RESET} {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
