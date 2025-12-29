"""
Lab3: Single-Agent 行銷文案生成器（含對話歷史記錄）

這是一個 Single-Agent 範例，基於 Lab2 的 create_agent 實作，
新增對話歷史記錄功能，讓 Agent 能夠記住之前的對話內容。

主要特色：
- 使用 InMemorySaver 保存對話歷史
- 使用 thread_id 區分不同對話
- 只保留 streaming 模式回應
- 支援多輪對話

適用場景：
- 需要上下文記憶的對話
- 多輪互動的任務
- 需要追蹤對話狀態的應用
"""

import os
import uuid
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver


class Colors:
    """
    終端機顏色代碼

    使用 ANSI 轉義序列在終端機中顯示彩色文字。
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

    # 角色顏色定義
    USER = "\033[1;32m"  # 粗體綠色 - 使用者
    ASSISTANT = "\033[1;36m"  # 粗體青色 - 助理
    SYSTEM = "\033[1;33m"  # 粗體黃色 - 系統訊息
    INFO = "\033[90m"  # 灰色 - 資訊


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


@tool
def generate_marketing_copy(
    product_name: str, product_features: str, target_audience: str, marketing_goal: str
) -> str:
    """
    根據產品資訊生成行銷文案。

    Args:
        product_name: 產品名稱
        product_features: 產品特點和賣點
        target_audience: 目標受眾描述
        marketing_goal: 行銷目標

    Returns:
        str: 生成的完整行銷文案
    """
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


class MarketingAgentWithMemory:
    """
    帶有對話記憶的行銷文案 Agent

    這個類別封裝了 Agent 和 Checkpointer，
    提供對話歷史記錄功能。
    """

    # 建構子函式初始化相關屬性
    def __init__(self):
        """
        初始化 Agent 和記憶體

        使用 InMemorySaver 作為 checkpointer，
        在記憶體中保存對話歷史。
        """
        # 建立 checkpointer 用於保存對話歷史
        self.checkpointer = InMemorySaver()

        # 從環境變數取得模型名稱
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")

        # 定義系統提示詞
        system_prompt = """你是一位專業的行銷文案撰寫專家，擅長創作吸引人且具說服力的行銷內容。

你的專長包括：
1. 撰寫吸引眼球的標題，能在3秒內抓住讀者注意力
2. 創作具有情感連結的文案，讓讀者產生共鳴
3. 設計有效的行動呼籲（Call to Action）
4. 根據不同目標受眾調整文案風格

當使用者提供產品資訊時，請幫助生成專業的行銷文案。
你可以記住之前的對話內容，並根據使用者的反饋進行修改和優化。"""

        # 使用 create_agent 建立 Agent，並加入 checkpointer
        self.agent = create_agent(
            model=model_name,
            tools=[generate_marketing_copy],
            system_prompt=system_prompt,
            checkpointer=self.checkpointer,  # 加入 checkpointer 以保存對話歷史
        )

        # 用於追蹤當前的 thread_id
        self.current_thread_id = None

    # 建立新的對話並回傳 thread_id，借助 UUID 產生唯一識別碼做為對話 ID
    def new_conversation(self) -> str:
        """
        開始新的對話

        生成新的 thread_id，開始一個全新的對話。

        Returns:
            str: 新的 thread_id
        """
        self.current_thread_id = str(uuid.uuid4())
        return self.current_thread_id

    def stream_chat(self, user_message: str, thread_id: str = None) -> None:
        """
        以串流方式進行對話

        Args:
            user_message: 使用者訊息
            thread_id: 對話 ID（可選，如未提供則使用當前 thread_id）
        """
        # 使用提供的 thread_id 或當前的 thread_id
        if thread_id:
            self.current_thread_id = thread_id
        elif not self.current_thread_id:
            self.new_conversation()

        # 設定 config，包含 thread_id 以追蹤對話歷史
        config = {"configurable": {"thread_id": self.current_thread_id}}

        print("-" * 60)
        print(f"{Colors.INFO}[對話 ID: {self.current_thread_id[:8]}...]{Colors.RESET}")
        print(f"{Colors.USER}[使用者]{Colors.RESET}: {user_message}")
        print("-" * 60)
        print(f"{Colors.ASSISTANT}[助理]{Colors.RESET}: ", end="", flush=True)

        # 使用 stream_mode="messages" 進行 token 級別串流
        for message_chunk, metadata in self.agent.stream(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,  # 傳入 config 以使用對話歷史
            stream_mode="messages",
        ):
            # 即時輸出內容
            if message_chunk.content:
                print(message_chunk.content, end="", flush=True)

        print("\n")

    def get_conversation_history(self, thread_id: str = None) -> list:
        """
        取得對話歷史

        Args:
            thread_id: 對話 ID（可選）

        Returns:
            list: 對話歷史訊息列表
        """
        tid = thread_id or self.current_thread_id
        if not tid:
            return []

        config = {"configurable": {"thread_id": tid}}

        try:
            # 取得當前狀態
            state = self.agent.get_state(config)
            if state and state.values:
                return state.values.get("messages", [])
        except Exception:
            pass

        return []

    def show_conversation_history(self, thread_id: str = None) -> None:
        """
        顯示對話歷史

        Args:
            thread_id: 對話 ID（可選）
        """
        messages = self.get_conversation_history(thread_id)

        if not messages:
            print("目前沒有對話歷史")
            return

        print("=" * 60)
        print("對話歷史")
        print("=" * 60)

        for msg in messages:
            role = type(msg).__name__
            content = msg.content if hasattr(msg, "content") else str(msg)

            # 截取過長的內容
            if len(content) > 200:
                content = content[:200] + "..."

            # 根據角色使用不同顏色
            if "Human" in role or "User" in role:
                color = Colors.USER
                display_role = "使用者"
            elif "AI" in role or "Assistant" in role:
                color = Colors.ASSISTANT
                display_role = "助理"
            else:
                color = Colors.INFO
                display_role = role

            print(f"{color}[{display_role}]{Colors.RESET}: {content}")
            print("-" * 40)


def main():
    """
    主程式入口

    展示如何使用帶有對話記憶的 Agent 進行多輪對話。
    """
    print("=" * 60)
    print("Lab3: Single-Agent 行銷文案生成器")
    print("（含對話歷史記錄功能）")
    print("=" * 60)

    # 載入環境變數
    try:
        load_environment()
        print("\n✓ 環境變數載入成功")
    except ValueError as e:
        print(f"\n✗ 錯誤：{e}")
        return

    # 建立帶有記憶的 Agent
    agent = MarketingAgentWithMemory()

    # 開始新對話
    thread_id = agent.new_conversation()
    print(f"✓ 開始新對話 (ID: {thread_id[:8]}...)")

    print("\n" + "=" * 60)
    print("開始多輪對話展示")
    print("=" * 60)

    # 第一輪對話：提供產品資訊
    print("\n【第一輪】提供產品資訊")
    agent.stream_chat(
        """請幫我撰寫以下產品的行銷文案：

產品名稱：智能空氣清淨機 AirPure Pro
產品特點：HEPA 13級濾網、智能空氣品質偵測、App遠端控制、超靜音設計（僅25分貝）、適用30坪空間
目標受眾：注重生活品質的都市家庭，特別是有小孩或過敏體質的家庭
行銷目標：提升品牌知名度，促進線上購買轉換

請生成一份完整的行銷文案。"""
    )

    # 第二輪對話：要求修改
    print("\n【第二輪】要求修改文案")
    agent.stream_chat(
        "請把標題改得更有情感一點，並且在正文中加入一個使用者見證的故事。"
    )

    # 第三輪對話：詢問建議
    print("\n【第三輪】詢問其他建議")
    agent.stream_chat("你覺得這個文案還可以怎麼優化？有什麼其他的行銷建議嗎？")

    # 顯示對話歷史
    print("\n" + "=" * 60)
    print("查看對話歷史記錄")
    print("=" * 60)
    agent.show_conversation_history()

    print("\n" + "=" * 60)
    print("互動模式（輸入 'quit' 結束，'new' 開始新對話，'history' 查看歷史）")
    print("=" * 60)

    # 互動模式
    while True:
        try:
            user_input = input(f"\n{Colors.USER}[你]{Colors.RESET}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n再見！")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("\n再見！")
            break
        elif user_input.lower() == "new":
            thread_id = agent.new_conversation()
            print(f"\n✓ 開始新對話 (ID: {thread_id[:8]}...)")
            continue
        elif user_input.lower() == "history":
            agent.show_conversation_history()
            continue

        agent.stream_chat(user_input)


if __name__ == "__main__":
    main()
