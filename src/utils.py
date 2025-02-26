import os
import time
import hmac
import json
import hashlib
import urllib.parse
import requests
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv  
load_dotenv()

NAMES = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "SOLUSDT": "Solana",
    "XRPUSDT": "Ripple",
}

TRADING_FEE = {
    "maker": 0.1,
    "taker": 0.1
}

BINANCE_BASE_URL = "https://api.binance.com"
API_CLIENT = os.getenv('BINANCE_CLIENT_ID')
API_SECRET = os.getenv('BINANCE_CLIENT_SECRET')
print(API_SECRET)

def get_current_prices(symbols):
    endpoint = "/api/v3/ticker/price"
    url = f"{BINANCE_BASE_URL}{endpoint}"

    params = {
        "symbols": json.dumps(symbols).replace(" ", "")
    }

    response = requests.get(url, params=params)
    return response.json()
    

def get_current_portfolio(symbols):
    endpoint = "/api/v3/account"
    url = f"{BINANCE_BASE_URL}{endpoint}"

    timestamp = int(time.time() * 1000)

    params = {
        "timestamp": timestamp,
    }
    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    headers = {
        "X-MBX-APIKEY": API_CLIENT
    }

    response = requests.get(url, headers=headers, params=params)
    balances = response.json()['balances']

    symbols = set(x[:3] for x in symbols) | {'USDT'}
    return {
        balance['asset']: round(float(balance['free']), 4)
        for balance in balances
        if balance['asset'] in symbols
    }

def create_market_order(
    symbol: str,
    quantity: float,
):
    endpoint = "/api/v3/order"
    url = f"{BINANCE_BASE_URL}{endpoint}"

    timestamp = int(time.time() * 1000)

    params = {
        "symbol": symbol,
        "type": "MARKET",
        "side": "SELL",
        "quantity": quantity,
        "timestamp": timestamp
    }
    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    headers = {
        "X-MBX-APIKEY": API_CLIENT
    }

    response = requests.post(url, headers=headers, params=params)

    return response.json()

def create_oco_order(
    symbol: str,
    quantity: float,
    take_profit: float,
    stop_loss: float,
):
    endpoint = "/api/v3/orderList/oco"
    url = f"{BINANCE_BASE_URL}{endpoint}"

    # Binance requires a timestamp
    timestamp = int(time.time() * 1000)

    params = {
        "symbol": symbol,
        "side": "SELL",
        "quantity": quantity,
        "aboveType": "LIMIT_MAKER",
        "abovePrice": take_profit,
        "aboveStopPrice": take_profit,  # Required: adjust as needed
        "aboveTimeInForce": "GTC",       # Required for aboveType if using STOP_LOSS_LIMIT/TAKE_PROFIT_LIMIT
        "belowType": "STOP_LOSS_LIMIT",
        "belowStopPrice": stop_loss,     # Required: adjust as needed
        "belowTimeInForce": "GTC",       # Required for belowType if using STOP_LOSS_LIMIT/TAKE_PROFIT_LIMIT
        "timestamp": timestamp
    }

    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    headers = {
        "X-MBX-APIKEY": API_CLIENT
    }

    response = requests.post(url, headers=headers, params=params)

    return response.json()
    

def create_otoco_order(
    symbol: str,
    price: float,
    quantity: float,
    take_profit: float,
    stop_loss: float,      
):
    endpoint = "/api/v3/orderList/otoco"
    url = f"{BINANCE_BASE_URL}{endpoint}"

    # Binance requires a timestamp
    timestamp = int(time.time() * 1000)

    params = {
        "symbol": symbol,
        "workingSide": "BUY",
        "workingType": "LIMIT",
        "workingPrice": price,
        "workingQuantity": quantity,
        "workingTimeInForce": "GTC",
        "pendingSide": "SELL",
        "pendingQuantity": quantity,
        "pendingAbovePrice": take_profit,
        "pendingAboveType": "LIMIT_MAKER",
        "pendingBelowPrice": stop_loss,
        "pendingBelowStopPrice": stop_loss,
        "pendingBelowType": "STOP_LOSS_LIMIT",
        "pendingBelowTimeInForce": "GTC",
        "timestamp": timestamp
    }

    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    # Headers
    headers = {
        "X-MBX-APIKEY": API_CLIENT
    }

    # Send request
    response = requests.post(url, headers=headers, params=params)

    return response.json()

def cancel_order(symbol, order_id):
    endpoint = "/api/v3/order"
    url = f"{BINANCE_BASE_URL}{endpoint}"

    timestamp = int(time.time() * 1000)

    params = {
        "symbol": symbol,
        "orderId": order_id,
        "timestamp": timestamp,
    }
    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    headers = {
        "X-MBX-APIKEY": API_CLIENT
    }

    response = requests.delete(url, headers=headers, params=params)


def clear_orders():
    endpoint = "/api/v3/openOrders"
    url = f"{BINANCE_BASE_URL}{endpoint}"

    timestamp = int(time.time() * 1000)

    params = {
        "timestamp": timestamp,
    }
    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    headers = {
        "X-MBX-APIKEY": API_CLIENT
    }

    response = requests.get(url, headers=headers, params=params)
    orders = response.json()

    if len(orders) == 0:
        return

    for order in orders:
        try:
            symbol = order['symbol']
            order_id = order['orderId']
            cancel_order(symbol, order_id)
        except Exception as e:
            print(f"Error canceling order {order_id} for {symbol}: {e}")


def get_llm(
    model: str,
    config: Optional[dict] = None
):
    if model == 'gpt-4o' or model== 'o1-2024-12-17' or model == 'gpt-4o-mini':
        return ChatOpenAI(model=model,
                          api_key=os.getenv('OPENAI_API_KEY'),
        )
    elif model == 'deepseek-chat' or model == 'deepseek-reasoner':
        return ChatOpenAI(
            model=model,
            base_url="https://api.deepseek.com",
            api_key=os.getenv('DEEPSEEK_API_KEY')
        )
    elif 'gemini' in model: # gemini-2.0-flash-thinking-exp-01-21 or gemini-2.0-pro-exp-02-05
        return ChatGoogleGenerativeAI(model=model,
                                    google_api_key=os.getenv('GEMINI_API_KEY'),
                                    temperature=0
                                    )
    else:
        raise ValueError(f'Model {model} not found')


if __name__ == "__main__":
    messages = [
    (
        "system",
        "You are a helpful assistant that translates English to French. Translate the user sentence.",
        ),
        ("human", "I love programming."),
    ]   
    llm = get_llm(model='gemini-2.0-flash-thinking-exp-01-21')
    ai_msg = llm.invoke(messages)
    print(ai_msg.content)