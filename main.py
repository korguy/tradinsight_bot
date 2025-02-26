import os
import pytz
import asyncio
import schedule
import time
from typing import List
from supabase import Client, create_client
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from src.technical_analysis import technical_analysis
from src.sentimental_analysis import sentimental_analysis
from src.schemas import Report, OrderBook
from src.utils import *
from src.prompts import portfolio_management_system_prompt

from src.logger import setup_logger
from dotenv import load_dotenv
load_dotenv()


logger = setup_logger("main", "project.log")

async def async_technical_analysis(target: str, config: dict):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, technical_analysis, target, config['technical_analysis'])
    return result

async def async_sentiment_analysis(target: str, config: dict):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, sentimental_analysis, target, config['sentiment_analysis'])
    return result

async def generate_reports(targets: List[str], config: dict) -> List[Report]:
    tech_tasks = [async_technical_analysis(target, config) for target in targets]
    sentiment_tasks = [async_sentiment_analysis(target, config) for target in targets]
    
    # Combine both lists into a single list and run them concurrently.
    all_tasks = tech_tasks + sentiment_tasks
    all_results = await asyncio.gather(*all_tasks)

    n = len(targets)
    tech_results = all_results[:n]
    sentiment_results = all_results[n:]

    reports = [
        Report(
            name=target,
            technical_analysis=tech,
            sentimental_analysis=sent
        )
        for target, tech, sent in zip(targets, tech_results, sentiment_results)
    ]
    return reports

def main(config):
    name = config['name']
    targets = config['target']
    current_time = datetime.now(pytz.utc).isoformat()
    logger.info("Strategy: %s", name)
    logger.info("Current Time: %s", current_time)
    logger.info("Targets: %s", targets)

    # 0. initialize the database
    db: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    # 1. clear incomplete orders
    clear_orders()
    logger.info("Incomplete orders cleared")

    # 1. generate technical/sentimental_analysis
    reports = asyncio.run(generate_reports(targets, config))

    for report in reports:
        try:
            response = (
                db.table("analysis")
                .insert({
                    "name": name,
                    'type': "technical",
                    'content': report.technical_analysis.summary,
                    'created': current_time,
                    'target': report.name
                })
                .execute()
            )
        except Exception as e:
            logger.error("Error inserting analysis: %s", e)
        try:
            response = (
                db.table("analysis")
                .insert({
                    "name": name,
                    'type': "sentimental",
                    'content': report.sentimental_analysis.summary,
                    'created': current_time,
                    'target': report.name
                })
                .execute()
            )
        except Exception as e:
            logger.error("Error inserting analysis: %s", e)
    
    # 2. get current portfolio
    portfolio = get_current_portfolio(targets)
    current_prices = get_current_prices(targets)
    logger.info("Portfolio: %s", portfolio)
    logger.info("Current Prices: %s", current_prices)

    # 3. get orders
    model = get_llm(config['management']['model'])
    # model_with_structure = model.with_structured_output(OrderBook)

    user_prompt = f"""portfolio: {portfolio}
    # current prices: {current_prices}"""

    for report in reports:
        user_prompt += f"""

        # {report.name}
        ## Technical Analysis
        {report.technical_analysis.summary}

        ## Sentimental Analysis
        {report.sentimental_analysis.summary}
        """

    messages = [
        SystemMessage(content=portfolio_management_system_prompt),
        HumanMessage(content=user_prompt)
    ]

    response = model.invoke(messages)
    formatter = get_llm(config['management']['parser'])
    formatter = formatter.with_structured_output(OrderBook)
    formatted_response = formatter.invoke(response.content)
    orders = formatted_response.orders

    logger.info("Orders: %s", orders)

    # 4. execute orders
    for order in orders:
        if order.side == 'BUY':
            try:
                create_otoco_order(order.symbol, order.price, order.quantity, order.take_profit, order.stop_loss)
                logger.info("BUY order created: %s %s", order.symbol, order.quantity)
            except Exception as e:
                logger.error("Error creating otooco order: %s", e)
        elif order.side == 'SELL':
            try:
                create_market_order(order.symbol, order.quantity)
                logger.info("SELL order created: %s %s", order.symbol, order.quantity)
            except Exception as e:
                logger.error("Error creating market order: %s", e)
        else:
            logger.info("HOLD %s", order.symbol)

def mainWrapper():
    import yaml
    config = yaml.safe_load(open('config.yaml', 'r'))
    main(config)


if __name__ == "__main__":
    schedule.every().day.at("00:00").do(mainWrapper)
    schedule.every().day.at("04:00").do(mainWrapper)
    schedule.every().day.at("08:00").do(mainWrapper)
    schedule.every().day.at("12:00").do(mainWrapper)
    schedule.every().day.at("16:00").do(mainWrapper)
    schedule.every().day.at("20:00").do(mainWrapper)

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute