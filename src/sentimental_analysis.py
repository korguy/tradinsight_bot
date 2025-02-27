import os
import requests
from datetime import datetime, timedelta

from pytrends.request import TrendReq
from langchain_core.messages import HumanMessage, SystemMessage

from src.schemas import SentimentalAnalysis
from src.utils import get_llm, NAMES
from src.prompts import sentiment_analysis_system_prompt

from src.logger import setup_logger

logger = setup_logger('sentimental_analysis', 'project.log')

def get_news_sentiment(symbol, days=7, limit=50):
    # get contents
    tickers = f"Cypto:{symbol.strip('USDT')}"
    time_from = (datetime.utcnow() - timedelta(days=days)).strftime("%Y%m%dT%H%M")
    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={tickers}&time_from={time_from}&apikey={os.getenv("ALPHAVANTAGE_API_KEY")}'
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data

def fetch_fear_and_greed_index(days=7):
    url = f"https://api.alternative.me/fng/?limit={days}&format=json"
    
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()["data"]

    return {
        "date": [datetime.fromtimestamp(int(x["timestamp"])).strftime("%d-%m-%Y") for x in data],
        "value": [x["value"] for x in data],
        "classification": [x["value_classification"] for x in data]
    }

def get_google_trends(symbol, days=7):
    # pytrends = TrendReq()
    # pytrends.build_payload(kw_list=[symbol], timeframe=f"now {days}-d", geo="US")

    # data = pytrends.interest_over_time()
    data = []
    return data

def sentimental_analysis(target: str, config: dict) -> SentimentalAnalysis:
    logger.info("Starting sentimental analysis for %s", target)

    news_sentiment = get_news_sentiment(target)
    fear_and_greed_index = fetch_fear_and_greed_index()
    # google_trends = get_google_trends(NAMES[target])

    model = get_llm(config['llm']['model'])
    user_prompt = f"""
        DATE: {datetime.now().strftime("%d-%m-%Y")}
        Target Cryptocurrency: {target}

        News Sentiment: {news_sentiment}
        Fear and Greed Index: {fear_and_greed_index}
    """
    messages = [
        SystemMessage(content=sentiment_analysis_system_prompt),
        HumanMessage(content=user_prompt)
    ]

    response = model.invoke(messages)

    logger.info("Finished sentimental analysis for %s", target)

    return SentimentalAnalysis(
        summary=response.content
    )