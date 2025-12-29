"""
Job1: Single-Agent 行銷文案生成器

這是一個 Single-Agent 範例，展示簡單的 prompt -> LLM -> output 流程。
Agent 負責根據使用者提供的產品資訊，生成專業的行銷文案。

適用場景：
- 任務相對單純
- 不需要專業分工
- 對話流程線性
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


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


def create_llm():
    """
    建立 LLM 實例

    使用 LangChain 的 ChatOpenAI 來連接 OpenAI API。
    模型名稱和其他參數透過環境變數設定。

    Returns:
        ChatOpenAI: 配置好的 LLM 實例
    """
    # 從環境變數取得模型名稱，預設使用 gpt-4o
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o")

    # 從環境變數取得 temperature，預設 0.7（適合創意寫作）
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    llm = ChatOpenAI(model=model_name, temperature=temperature)

    return llm


def create_marketing_prompt():
    """
    建立行銷文案生成的 Prompt 模板

    這個 Prompt 設計用於引導 LLM 生成專業的行銷文案。
    包含產品名稱、特點和目標受眾等關鍵資訊。

    Returns:
        ChatPromptTemplate: 配置好的 Prompt 模板
    """
    template = """你是一位專業的行銷文案撰寫專家，擅長創作吸引人且具說服力的行銷內容。

請根據以下產品資訊，撰寫一份完整的行銷文案：

## 產品資訊
- 產品名稱：{product_name}
- 產品特點：{product_features}
- 目標受眾：{target_audience}
- 行銷目標：{marketing_goal}

## 文案要求
1. 標題要吸引眼球，能夠在3秒內抓住讀者注意力
2. 內容要突出產品的核心價值和獨特賣點
3. 使用具有情感連結的語言，讓讀者產生共鳴
4. 結尾要有明確的行動呼籲（Call to Action）
5. 整體風格要符合目標受眾的偏好

請按照以下格式輸出：

【標題】
（一句話吸引眼球的標題）

【副標題】
（補充說明，強化標題訴求）

【正文】
（詳細的行銷文案內容，3-5段）

【行動呼籲】
（引導讀者採取行動的結尾）
"""

    prompt = ChatPromptTemplate.from_template(template)
    return prompt


def create_marketing_agent():
    """
    建立行銷文案 Agent（Chain）

    使用 LangChain Expression Language (LCEL) 建立一個簡單的 Chain，
    將 Prompt、LLM 和 Output Parser 串接起來。

    這展示了 Single-Agent 的核心架構：
    prompt -> LLM -> output

    Returns:
        chain: 可執行的 LangChain Chain
    """
    # 建立各個組件
    prompt = create_marketing_prompt()
    llm = create_llm()
    output_parser = StrOutputParser()

    # 使用 LCEL 語法串接組件
    # | 運算子用於連接 Chain 的各個部分
    chain = prompt | llm | output_parser

    return chain


def generate_marketing_copy(product_info: dict) -> str:
    """
    生成行銷文案

    這是主要的執行函數，接收產品資訊並返回生成的行銷文案。

    Args:
        product_info: 包含以下鍵值的字典：
            - product_name: 產品名稱
            - product_features: 產品特點
            - target_audience: 目標受眾
            - marketing_goal: 行銷目標

    Returns:
        str: 生成的行銷文案
    """
    # 建立 Agent（Chain）
    agent = create_marketing_agent()

    # 執行 Chain 並獲取結果
    # invoke() 方法會依序執行 prompt -> LLM -> output_parser
    result = agent.invoke(product_info)

    return result


def main():
    """
    主程式入口

    展示如何使用 Single-Agent 生成行銷文案。
    包含範例產品資訊和互動式輸入兩種模式。
    """
    print("=" * 60)
    print("Job1: Single-Agent 行銷文案生成器")
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

    # 生成行銷文案
    print("\n正在生成行銷文案，請稍候...\n")

    try:
        result = generate_marketing_copy(sample_product)
        print("=" * 60)
        print("生成的行銷文案")
        print("=" * 60)
        print(result)
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ 生成失敗：{e}")


if __name__ == "__main__":
    main()
