"""
MCP Server - 產品與訂單查詢服務

這是一個使用 Anthropic 官方 MCP Python SDK 實作的 MCP Server，
透過 Streamable HTTP 模式提供工具給 Agent 系統使用。

提供的工具：
1. 產品資訊查詢工具 (get_product_info)：根據產品名稱查詢產品詳細資訊
2. 訂單狀態查詢工具 (get_order_status)：根據訂單號碼查詢訂單狀態

技術特色：
- 使用 FastMCP 簡化 MCP Server 開發
- Streamable HTTP 傳輸模式（推薦用於生產環境）
- 模擬產品與訂單資料庫

啟動方式：
    python mcpserver/mcp_server.py

預設服務位置：http://localhost:8000/mcp
"""

from mcp.server.fastmcp import FastMCP
from datetime import datetime, timedelta
import random


# =============================================================================
# MCP Server 設定
# =============================================================================

# 建立 FastMCP 實例
# json_response=True：返回 JSON 格式的回應，適合 HTTP 傳輸
mcp = FastMCP(
    name="產品與訂單查詢服務",
    json_response=True
)


# =============================================================================
# 模擬資料庫
# =============================================================================

# 模擬產品資料庫
PRODUCTS_DATABASE = {
    "airpure pro": {
        "name": "AirPure Pro 智能空氣清淨機",
        "description": "專為現代家庭設計的新一代智能空氣清淨機，配備 HEPA-13 濾網，"
                       "可捕捉 99.97% 的空氣微粒，包括灰塵、花粉和寵物皮屑。",
        "price": 12800,
        "currency": "TWD",
        "stock_status": "有庫存",
        "stock_quantity": 156,
        "category": "家電",
        "features": [
            "HEPA-13 級濾網",
            "智能空氣品質偵測 (PM2.5, VOC)",
            "App 遠端控制",
            "超靜音設計 (25dB)",
            "適用 30 坪空間"
        ],
        "warranty": "2年保固"
    },
    "智能手錶": {
        "name": "SmartWatch X1 智能手錶",
        "description": "全方位健康監測智能手錶，支援心率、血氧、睡眠追蹤，"
                       "內建 GPS 和防水功能，是您的運動健康好夥伴。",
        "price": 8990,
        "currency": "TWD",
        "stock_status": "有庫存",
        "stock_quantity": 89,
        "category": "穿戴裝置",
        "features": [
            "24小時心率監測",
            "血氧濃度偵測",
            "睡眠品質分析",
            "內建 GPS",
            "5ATM 防水",
            "7天續航力"
        ],
        "warranty": "1年保固"
    },
    "無線耳機": {
        "name": "SoundPods Ultra 真無線藍牙耳機",
        "description": "Hi-Fi 音質真無線藍牙耳機，支援主動降噪功能，"
                       "配備觸控操作和長效電池，帶來沉浸式聆聽體驗。",
        "price": 3990,
        "currency": "TWD",
        "stock_status": "有庫存",
        "stock_quantity": 234,
        "category": "音訊設備",
        "features": [
            "主動降噪 (ANC)",
            "Hi-Fi 音質",
            "觸控操作",
            "單次續航 8 小時",
            "充電盒總續航 32 小時",
            "IPX5 防水"
        ],
        "warranty": "1年保固"
    },
    "筆記型電腦": {
        "name": "ProBook 15 輕薄筆電",
        "description": "輕薄高效能筆記型電腦，搭載最新處理器和高解析度螢幕，"
                       "適合專業人士和創作者使用。",
        "price": 42900,
        "currency": "TWD",
        "stock_status": "預購中",
        "stock_quantity": 0,
        "category": "電腦",
        "features": [
            "15.6 吋 2K IPS 螢幕",
            "第 13 代 Intel Core i7",
            "16GB DDR5 記憶體",
            "512GB NVMe SSD",
            "指紋辨識",
            "Thunderbolt 4 連接埠"
        ],
        "warranty": "2年保固"
    }
}

# 模擬訂單資料庫
ORDERS_DATABASE = {
    "ORD-2024-001": {
        "order_id": "ORD-2024-001",
        "status": "已送達",
        "status_code": "delivered",
        "product": "AirPure Pro 智能空氣清淨機",
        "quantity": 1,
        "total_amount": 12800,
        "order_date": "2024-12-20",
        "shipping_date": "2024-12-21",
        "delivery_date": "2024-12-23",
        "shipping_address": "台北市信義區松仁路 100 號",
        "tracking_number": "TW123456789"
    },
    "ORD-2024-002": {
        "order_id": "ORD-2024-002",
        "status": "運送中",
        "status_code": "shipping",
        "product": "SmartWatch X1 智能手錶",
        "quantity": 2,
        "total_amount": 17980,
        "order_date": "2024-12-27",
        "shipping_date": "2024-12-28",
        "delivery_date": None,
        "estimated_delivery": "2024-12-30",
        "shipping_address": "新北市板橋區中山路 50 號",
        "tracking_number": "TW987654321"
    },
    "ORD-2024-003": {
        "order_id": "ORD-2024-003",
        "status": "處理中",
        "status_code": "processing",
        "product": "SoundPods Ultra 真無線藍牙耳機",
        "quantity": 1,
        "total_amount": 3990,
        "order_date": "2024-12-29",
        "shipping_date": None,
        "delivery_date": None,
        "estimated_shipping": "2024-12-30",
        "shipping_address": "台中市西屯區台灣大道 200 號",
        "tracking_number": None
    },
    "ORD-2024-004": {
        "order_id": "ORD-2024-004",
        "status": "已取消",
        "status_code": "cancelled",
        "product": "ProBook 15 輕薄筆電",
        "quantity": 1,
        "total_amount": 42900,
        "order_date": "2024-12-15",
        "cancel_date": "2024-12-16",
        "cancel_reason": "客戶要求取消",
        "refund_status": "已退款"
    }
}


# =============================================================================
# MCP 工具定義
# =============================================================================

@mcp.tool()
def get_product_info(product_name: str) -> str:
    """
    根據產品名稱查詢產品的詳細資訊。

    這個工具可以查詢產品的名稱、描述、價格、庫存狀態、
    產品特色和保固資訊。

    Args:
        product_name: 要查詢的產品名稱（支援模糊搜尋）

    Returns:
        產品的詳細資訊，包括名稱、描述、價格、庫存和特色等
    """
    # 將查詢轉換為小寫以進行模糊比對
    search_term = product_name.lower().strip()

    # 尋找匹配的產品
    matched_product = None
    for key, product in PRODUCTS_DATABASE.items():
        # 檢查產品鍵或產品名稱是否包含搜尋詞
        if (search_term in key.lower() or
            search_term in product["name"].lower() or
            any(search_term in feature.lower() for feature in product.get("features", []))):
            matched_product = product
            break

    if not matched_product:
        # 列出所有可用產品
        available_products = [p["name"] for p in PRODUCTS_DATABASE.values()]
        return (
            f"找不到名為「{product_name}」的產品。\n\n"
            f"目前可查詢的產品有：\n" +
            "\n".join(f"- {name}" for name in available_products)
        )

    # 格式化產品資訊
    features_text = "\n".join(f"  - {f}" for f in matched_product["features"])

    result = f"""
【產品資訊】

產品名稱：{matched_product['name']}
產品類別：{matched_product['category']}

產品描述：
{matched_product['description']}

價格：NT$ {matched_product['price']:,} {matched_product['currency']}

庫存狀態：{matched_product['stock_status']}
{"庫存數量：" + str(matched_product['stock_quantity']) + " 件" if matched_product['stock_quantity'] > 0 else ""}

產品特色：
{features_text}

保固期間：{matched_product['warranty']}
"""
    return result.strip()


@mcp.tool()
def get_order_status(order_id: str) -> str:
    """
    根據訂單號碼查詢訂單的當前狀態。

    這個工具可以查詢訂單的處理狀態、配送資訊、
    預計送達時間等相關資訊。

    Args:
        order_id: 訂單號碼（格式：ORD-YYYY-XXX）

    Returns:
        訂單的詳細狀態，包括處理進度、配送資訊和預計送達時間
    """
    # 標準化訂單號碼格式
    order_id_upper = order_id.upper().strip()

    # 查詢訂單
    order = ORDERS_DATABASE.get(order_id_upper)

    if not order:
        # 列出可用的範例訂單號
        sample_orders = list(ORDERS_DATABASE.keys())[:3]
        return (
            f"找不到訂單號碼「{order_id}」。\n\n"
            f"請確認訂單號碼格式是否正確（例如：ORD-2024-001）。\n\n"
            f"範例訂單號碼：{', '.join(sample_orders)}"
        )

    # 根據訂單狀態格式化不同的資訊
    status_emoji = {
        "delivered": "✅",
        "shipping": "🚚",
        "processing": "⏳",
        "cancelled": "❌"
    }

    emoji = status_emoji.get(order["status_code"], "📦")

    result = f"""
【訂單狀態查詢】

訂單號碼：{order['order_id']}
訂單狀態：{emoji} {order['status']}

訂購商品：{order['product']}
數量：{order['quantity']} 件
訂單金額：NT$ {order['total_amount']:,}

訂購日期：{order['order_date']}
"""

    # 根據狀態添加不同資訊
    if order["status_code"] == "delivered":
        result += f"""出貨日期：{order['shipping_date']}
送達日期：{order['delivery_date']}
物流編號：{order['tracking_number']}
配送地址：{order['shipping_address']}

訂單已順利送達！感謝您的訂購。
"""
    elif order["status_code"] == "shipping":
        result += f"""出貨日期：{order['shipping_date']}
預計送達：{order['estimated_delivery']}
物流編號：{order['tracking_number']}
配送地址：{order['shipping_address']}

您的訂單正在運送途中，請留意收件。
"""
    elif order["status_code"] == "processing":
        result += f"""預計出貨：{order['estimated_shipping']}
配送地址：{order['shipping_address']}

訂單正在處理中，將盡快為您出貨。
"""
    elif order["status_code"] == "cancelled":
        result += f"""取消日期：{order['cancel_date']}
取消原因：{order['cancel_reason']}
退款狀態：{order['refund_status']}
"""

    return result.strip()


@mcp.tool()
def list_available_products() -> str:
    """
    列出所有可查詢的產品清單。

    這個工具會返回系統中所有可查詢的產品名稱和簡要資訊，
    方便使用者了解有哪些產品可以查詢。

    Returns:
        所有可用產品的清單，包含名稱、價格和庫存狀態
    """
    result = "【可查詢產品清單】\n\n"

    for product in PRODUCTS_DATABASE.values():
        stock_info = "有庫存" if product["stock_quantity"] > 0 else product["stock_status"]
        result += f"📦 {product['name']}\n"
        result += f"   價格：NT$ {product['price']:,}\n"
        result += f"   狀態：{stock_info}\n"
        result += f"   類別：{product['category']}\n\n"

    result += "使用 get_product_info 工具可查詢產品詳細資訊。"
    return result.strip()


@mcp.tool()
def list_sample_orders() -> str:
    """
    列出範例訂單號碼供查詢測試。

    這個工具會返回系統中可供測試查詢的訂單號碼，
    以及各訂單的當前狀態摘要。

    Returns:
        範例訂單號碼清單和狀態摘要
    """
    status_emoji = {
        "delivered": "✅",
        "shipping": "🚚",
        "processing": "⏳",
        "cancelled": "❌"
    }

    result = "【範例訂單清單】\n\n"

    for order in ORDERS_DATABASE.values():
        emoji = status_emoji.get(order["status_code"], "📦")
        result += f"{emoji} {order['order_id']}\n"
        result += f"   商品：{order['product']}\n"
        result += f"   狀態：{order['status']}\n\n"

    result += "使用 get_order_status 工具可查詢訂單詳細狀態。"
    return result.strip()


# =============================================================================
# 主程式
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MCP Server - 產品與訂單查詢服務")
    print("=" * 60)
    print()
    print("使用 Streamable HTTP 傳輸模式")
    print("服務位置：http://localhost:8000/mcp")
    print()
    print("可用工具：")
    print("  - get_product_info: 查詢產品資訊")
    print("  - get_order_status: 查詢訂單狀態")
    print("  - list_available_products: 列出所有產品")
    print("  - list_sample_orders: 列出範例訂單")
    print()
    print("按 Ctrl+C 停止服務")
    print("=" * 60)

    # 啟動 Streamable HTTP 服務
    # 伺服器會在 http://localhost:8000/mcp 運行
    # 如需自定義 host/port，請使用 uvicorn 搭配 mcp.streamable_http_app()
    mcp.run(transport="streamable-http")
