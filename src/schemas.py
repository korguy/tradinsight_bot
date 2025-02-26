from typing import List, Optional

from pydantic import BaseModel, Field

class TechnicalAnalysis(BaseModel):
    ohlcv: dict = Field(description="The ohlcv of the target cryptocurrency")
    indicators: dict = Field(description="The indicators of the target cryptocurrency")
    summary: str = Field(description="The summary of the technical analysis")

class SentimentalAnalysis(BaseModel):
    summary: str = Field(description="The summary of the sentimental analysis")

class Report(BaseModel):
    name: str = Field("The name of the target cryptocurrency")
    technical_analysis: TechnicalAnalysis = Field("The technical analysis of the target cryptocurrency")
    sentimental_analysis: SentimentalAnalysis = Field("The sentimental analysis of the target cryptocurrency")

class State(BaseModel):
    strategy: str = Field(description="The strategy of the user")
    portfolio: str = Field(description="The portfolio of the user")
    report: List[Report] = Field(description="The report of the user")
    config: dict = Field(description="The config of the user")

class Order(BaseModel):
    symbol: str = Field(description="The symbol of the order")
    side: str = Field(description="The side of the order. either 'BUY','SELL', or 'HOLD'")
    reason: str = Field(description="The reasoning for the order")
    quantity: Optional[float] = Field(description="The quantity of the order")
    price: Optional[float] = Field(description="The price of the order")
    take_profit: Optional[float] = Field(description="The take profit of the order")
    stop_loss: Optional[float] = Field(description="The stop loss of the order")

class OrderBook(BaseModel):
    orders: List[Order] = Field(description="The orders of the user")