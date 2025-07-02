# tools/alpha_vantage_tools.py (FINAL - Using BaseTool Class Inheritance)

import os
import requests
import json
from alpha_vantage.fundamentaldata import FundamentalData
from alpha_vantage.techindicators import TechIndicators
from crewai.tools import BaseTool # <-- THE CORRECT IMPORT from the core crewai library

# --- CONFIGURATION ---
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
if not ALPHA_VANTAGE_API_KEY:
    raise ValueError("ALPHA_VANTAGE_API_KEY environment variable not set.")

# --- TOOL 1: Fundamental Data ---
class FundamentalDataTool(BaseTool):
    name: str = "Get Company Overview & Fundamentals"
    description: str = "Retrieves comprehensive fundamental data for a given stock ticker, including P/E ratio, EPS, and other key financial metrics from Alpha Vantage. Returns a JSON string with the company overview."

    def _run(self, ticker: str) -> str:
        fd = FundamentalData(key=ALPHA_VANTAGE_API_KEY, output_format='json')
        try:
            overview, _ = fd.get_company_overview(symbol=ticker)
            return json.dumps(overview)
        except Exception as e:
            return f"Error retrieving fundamental data for {ticker}: {e}"

# --- TOOL 2: Technical Data ---
class TechnicalDataTool(BaseTool):
    name: str = "Get Comprehensive Technical Data"
    description: str = "Retrieves a comprehensive set of key technical indicators (SMA, RSI, MACD, Bollinger Bands, OBV) and crossover events for a given stock ticker from Alpha Vantage. Returns a JSON string with the most recent data points."

    def _run(self, ticker: str) -> str:
        ti = TechIndicators(key=ALPHA_VANTAGE_API_KEY, output_format='json')
        latest_data = {}
        try:
            # Moving Averages & Crossover
            sma50, _ = ti.get_sma(symbol=ticker, interval='daily', time_period='50', series_type='close')
            sma200, _ = ti.get_sma(symbol=ticker, interval='daily', time_period='200', series_type='close')
            if sma50 and sma200 and len(list(sma50.values())) > 1 and len(list(sma200.values())) > 1:
                latest_sma50 = float(list(sma50.values())[0]['SMA'])
                latest_sma200 = float(list(sma200.values())[0]['SMA'])
                previous_sma50 = float(list(sma50.values())[1]['SMA'])
                previous_sma200 = float(list(sma200.values())[1]['SMA'])
                if previous_sma50 <= previous_sma200 and latest_sma50 > latest_sma200:
                    latest_data['Crossover_Event'] = "Golden Cross (Recent Bullish Signal)"
                elif previous_sma50 >= previous_sma200 and latest_sma50 < latest_sma200:
                    latest_data['Crossover_Event'] = "Death Cross (Recent Bearish Signal)"
                else:
                    latest_data['Crossover_Event'] = "None"
            else:
                latest_data['Crossover_Event'] = "Not enough data"
            
            # Other Indicators
            rsi, _ = ti.get_rsi(symbol=ticker, interval='daily', time_period='14', series_type='close')
            macd_data, _ = ti.get_macd(symbol=ticker, interval='daily', series_type='close')
            bbands, _ = ti.get_bbands(symbol=ticker, interval='daily', time_period='20', series_type='close')
            obv, _ = ti.get_obv(symbol=ticker, interval='daily')
            
            latest_data['SMA_50'] = list(sma50.values())[0] if sma50 else "N/A"
            latest_data['SMA_200'] = list(sma200.values())[0] if sma200 else "N/A"
            latest_data['RSI'] = list(rsi.values())[0] if rsi else "N/A"
            latest_data['MACD'] = list(macd_data.values())[0] if macd_data else "N/A"
            latest_data['Bollinger_Bands'] = list(bbands.values())[0] if bbands else "N/A"
            latest_data['On_Balance_Volume'] = list(obv.values())[0] if obv else "N/A"
            
            return json.dumps(latest_data)
        except Exception as e:
            return f"Error retrieving comprehensive technical data for {ticker}: {e}"

# --- TOOL 3: News & Sentiment ---
class NewsSentimentTool(BaseTool):
    name: str = "Get News & Market Sentiment"
    description: str = "Retrieves the latest news and sentiment analysis for a given stock ticker from Alpha Vantage. Returns a JSON string of the most relevant news feed items."

    def _run(self, ticker: str) -> str:
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_API_KEY}'
        try:
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            if 'feed' in data and data['feed']:
                return json.dumps(data['feed'][:10])
            else:
                return f"No news or sentiment data found for {ticker}. Response: {json.dumps(data)}"
        except Exception as e:
            return f"Error retrieving news and sentiment for {ticker}: {e}"

# --- Instantiate the tools for use in the crew ---
fundamental_data_tool = FundamentalDataTool()
technical_data_tool = TechnicalDataTool()
news_sentiment_tool = NewsSentimentTool()