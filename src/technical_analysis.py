import os
import time
import json
import talib
import requests
import numpy as np
from typing import Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from binance import Client

from src.prompts import technical_analysis_system_prompt
from src.schemas import TechnicalAnalysis
from src.utils import get_llm

from src.logger import setup_logger

logger = setup_logger('technical_analysis', 'project.log')

def get_ohlcv(
    symbol: int, 
    interval: Optional[str] = '4h', 
    limit: Optional[int] = None
):
    """
    Get OHLCV data from Binance API
    
    Args:
        symbol: str, symbol of the asset
        interval: str, interval of the data
        limit: int, number of data points to return
        
    Returns:
        dict: OHLCV data
    """
    interval_map = {
        '1h': Client.KLINE_INTERVAL_1HOUR,
        '4h': Client.KLINE_INTERVAL_4HOUR,
        '1d': Client.KLINE_INTERVAL_1DAY
    }
    client = Client(
        api_key=os.getenv('BINANCE_CLIENT_ID'),
        api_secret=os.getenv('BINANCE_CLIENT_SECRET')
    )
    candles = client.get_klines(
        symbol=symbol,
        interval=interval_map[interval],
        limit=limit
    )
    return {
        'open_time': np.array([int(candle[0]) for candle in candles]),
        'open': np.array([float(candle[1]) for candle in candles]),
        'high': np.array([float(candle[2]) for candle in candles]),
        'low': np.array([float(candle[3]) for candle in candles]),
        'close': np.array([float(candle[4]) for candle in candles]),
        'volume': np.array([float(candle[5]) for candle in candles]),
        'quote_volume': np.array([float(candle[7]) for candle in candles]),
        'trades': np.array([int(candle[8]) for candle in candles]),
        'taker_buy_volume': np.array([float(candle[9]) for candle in candles]),
        'taker_buy_quote_volume': np.array([float(candle[10]) for candle in candles])
    }

def get_indicators(
    data: dict,
    **kwargs  # Changed from config: dict to **kwargs
):
    """
    Get indicators from data
    """
    indicators = {}
    for key in kwargs:
        if key == 'EMA':
            indicators[f'EMA_{kwargs[key]["timeperiod"]}'] = talib.EMA(data['close'], timeperiod=kwargs[key]['timeperiod'])
        elif key == 'RSI':
            indicators[f'RSI_{kwargs[key]["timeperiod"]}'] = talib.RSI(data['close'], timeperiod=kwargs[key]['timeperiod'])
        elif key == 'MACD':
            indicators[f'MACD_{kwargs[key]["fastperiod"]}_{kwargs[key]["slowperiod"]}_{kwargs[key]["signalperiod"]}'], _, _ = talib.MACD(data['close'], fastperiod=kwargs[key]['fastperiod'], slowperiod=kwargs[key]['slowperiod'], signalperiod=kwargs[key]['signalperiod'])
        elif key == 'BBANDS':
            indicators[f'BBANDS_{kwargs[key]["timeperiod"]}'] = talib.BBANDS(data['close'], timeperiod=kwargs[key]['timeperiod'])
    return indicators

def get_bitcoin_dominance(
    days: int
):
    """
    Get bitcoin dominance from bitcoin-data
    """
    try:
        url = "https://bitcoin-data.com/v1/bitcoin-dominance"
        response = requests.get(url)
        data = response.json()[-days:]
    except Exception as e:
        logger.error("Error getting bitcoin dominance: %s", e)
        return {
            'date': [],
            'bitcoin_dominance': [],
        }
    
    return {
        'date': [x['d'].split()[0] for x in data],
        'bitcoin_dominance': [float(x['bitcoinDominance']) for x in data],
    }

def get_derivative_data(
    symbol: str,
    config: dict,
):
    """
    Get derivative data from Coinalyze
    """
    derivative = {}
    symbol += "_PERP.A"
    to_timestamp = int(time.time())
    interval_seconds = 3600*4 if config['interval'] == '4hour' else 3600*24
    from_timestamp = to_timestamp - interval_seconds * config['lookback']
    params = {
        "api_key": os.getenv('COINALYZE_API_KEY'),
        "symbols": symbol,
        "interval": config['interval'],
        "from": from_timestamp,
        "to": to_timestamp
    }

    if 'open_interest' in config['indicators']:
        url_open_interest = "https://api.coinalyze.net/v1/open-interest-history"
        response = requests.get(url_open_interest, params=params)
        open_interest = response.json()
        derivative['open_interest'] = {
            'open_time': [int(x['t']) * 1000 for x in open_interest[0]['history']],
            'open': [float(x['o']) for x in open_interest[0]['history']],
            'high': [float(x['h']) for x in open_interest[0]['history']],
            'low': [float(x['l']) for x in open_interest[0]['history']],
            'close': [float(x['c']) for x in open_interest[0]['history']],
        }


    if 'funding_rate' in config['indicators']:
        url_funding_rate = "https://api.coinalyze.net/v1/funding-rate-history"
        response = requests.get(url_funding_rate, params=params)
        funding_rate = response.json()
        derivative['funding_rate'] = {
            'open_time': [int(x['t']) * 1000 for x in funding_rate[0]['history']],
            'open': [float(x['o']) for x in funding_rate[0]['history']],
            'high': [float(x['h']) for x in funding_rate[0]['history']],
            'low': [float(x['l']) for x in funding_rate[0]['history']],
            'close': [float(x['c']) for x in funding_rate[0]['history']],
        }

    if 'liquidation' in config['indicators']:
        url_liquidation = "https://api.coinalyze.net/v1/liquidation-history"
        response = requests.get(url_liquidation, params=params)
        liquidation = response.json()
        derivative['liquidation'] = {
            'open_time': [int(x['t']) * 1000 for x in liquidation[0]['history']],
            'long': [float(x['l']) for x in liquidation[0]['history']],
            'short': [float(x['s']) for x in liquidation[0]['history']],
        }

    if 'long_short_ratio' in config['indicators']:
        params['indicators'] = 'long_short_ratio'
        url_long_short_ratio = "https://api.coinalyze.net/v1/long-short-ratio-history"
        response = requests.get(url_long_short_ratio, params=params)
        long_short_ratio = response.json()
        derivative['long_short_ratio'] = {
            'open_time': [int(x['t']) * 1000 for x in long_short_ratio[0]['history']],
            'ratio': [float(x['r']) for x in long_short_ratio[0]['history']],
            'long': [float(x['l']) for x in long_short_ratio[0]['history']],
            'short': [float(x['s']) for x in long_short_ratio[0]['history']],
        }
    
    return derivative 

def technical_analysis(
    target: str,
    config: dict
) -> TechnicalAnalysis:
    """
    Perform technical analysis on the target cryptocurrency
    """
    logger.info("Starting technical analysis for %s", target)
    ohlcv = get_ohlcv(target, config['data']['interval'], config['data']['lookback'])
    indicators = get_indicators(ohlcv, **config['indicators'])
    bitcoin_dominance = get_bitcoin_dominance(config['bitcoin_dominance']['days'])
    derivative = get_derivative_data(target, config['derivative'])

    user_prompt = f"""
    DATE: {datetime.now().strftime("%d-%m-%Y")}
    Target Cryptocurrency: {target}
    """

    user_prompt += f"""
    Historical Prices ({config['data']['interval']} OHLCV in chronological order):
    - open price: {ohlcv['open']}
    - high price: {ohlcv['high']}
    - low price: {ohlcv['low']}
    - close price: {ohlcv['close']}
    - volume: {ohlcv['volume']}
    """

    user_prompt += f"""
    Technical Indicators:
    """
    for key in indicators:
        user_prompt += f"- {key}: {indicators[key]}"    
    
    user_prompt += f"""
    Derivative Market Data (last {config['derivative']['lookback']} in {config['derivative']['interval']} interval):
    """
    for key in derivative:
        user_prompt += f"- {key}: {json.dumps(derivative[key])}"
    
    user_prompt += f"""
    Bitcoin Dominance (last {config['bitcoin_dominance']['days']} days):
    - {bitcoin_dominance['date']}: {bitcoin_dominance['bitcoin_dominance']}
    """
    
    llm = get_llm(config['llm']['model'])
    
    try:
        summary = llm.invoke([
            SystemMessage(content=technical_analysis_system_prompt),
            HumanMessage(content=user_prompt)
        ])
    except Exception as e:
        logger.error("Error during LLM invocation: %s", e)
        raise

    logger.info(f"Finished technical analysis for {target}")

    _indicators = {}
    for key in indicators:
        _indicators[key] = indicators[key]

    return TechnicalAnalysis(
        ohlcv=ohlcv,
        indicators=_indicators,
        summary=summary.content
    )

