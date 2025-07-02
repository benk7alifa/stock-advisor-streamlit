# tools/alpha_vantage_tools.py (FINAL - Hardcoded Key for Testing)

import os
import requests
import json
from alpha_vantage.fundamentaldata import FundamentalData
from crewai.tools import BaseTool

# --- CONFIGURATION: Using the hardcoded key as per AV support's recommendation ---
ALPHA_VANTAGE_API_KEY = "4A8LNUNXGL1ZH740"

# --- TOOL 1: Fundamental Data (Updated to use the hardcoded key) ---
class FundamentalDataTool(BaseTool):
    name: str = "Get Company Overview & Fundamentals"
    description: str = "Retrieves comprehensive fundamental data for a given stock ticker."
    def _run(self, ticker: str) -> str:
        # We manually pass the key to bypass any potential library reliance on environment variables
        fd = FundamentalData(key=ALPHA_VANTAGE_API_KEY, output_format='json')
        try:
            overview, _ = fd.get_company_overview(symbol=ticker)
            return json.dumps(overview)
        except Exception as e:
            return f"Error retrieving fundamental data for {ticker}: {e}"

# --- TOOL 2: Premium Technical Analysis Tool (Updated for direct requests with hardcoded key) ---
class PremiumTechnicalAnalysisTool(BaseTool):
    name: str = "Get Premium Technical Indicators"
    description: str = "Retrieves a comprehensive set of key technical indicators using a premium Alpha Vantage key."
    def _run(self, ticker: str) -> str:
        latest_data = {}
        
        def fetch_indicator(function, **kwargs):
            base_url = "https://www.alphavantage.co/query?"
            # Build the URL with the hardcoded key
            params = f"function={function}&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}&entitlement=delayed"
            for key, value in kwargs.items():
                params += f"&{key}={value}"
            
            url = base_url + params
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if "Error Message" in data or "Information" in data:
                return data
            
            data_key = next((key for key in data if 'Technical Analysis' in key), None)
            if not data_key:
                return {"error": f"Could not find data key for {function}"}
            
            return list(data[data_key].values())[0]

        try:
            latest_data['SMA_50'] = fetch_indicator("SMA", interval='daily', time_period='50', series_type='close')
            latest_data['SMA_200'] = fetch_indicator("SMA", interval='daily', time_period='200', series_type='close')
            latest_data['RSI'] = fetch_indicator("RSI", interval='daily', time_period='14', series_type='close')
            latest_data['MACD'] = fetch_indicator("MACD", interval='daily', series_type='close')
            latest_data['Bollinger_Bands'] = fetch_indicator("BBANDS", interval='daily', time_period='20', series_type='close')
            
            return json.dumps(latest_data)
        except Exception as e:
            return f"An error occurred while fetching premium technical indicators: {e}"

# --- TOOL 3: News & Sentiment (Updated for direct requests with hardcoded key) ---
class NewsSentimentTool(BaseTool):
    name: str = "Get News & Market Sentiment"
    description: str = "Retrieves the latest news and sentiment analysis for a given stock ticker."
    def _run(self, ticker: str) -> str:
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_API_KEY}'
        try:
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            if 'feed' in data and data['feed']:
                return json.dumps(data['feed'][:10])
            else:
                return f"No news or sentiment data found. Response: {json.dumps(data)}"
        except Exception as e:
            return f"Error retrieving news for {ticker}: {e}"

# --- TOOL 4: Daily Price History (Updated for direct requests with hardcoded key) ---
class DailyPriceTool(BaseTool):
    name: str = "Get Daily Stock Price History"
    description: str = "Retrieves the daily time series for the last 100 days for a given stock ticker."
    def _run(self, ticker: str) -> str:
        url = (f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY"
               f"&symbol={ticker}"
               f"&outputsize=compact"
               f"&entitlement=delayed"
               f"&apikey={ALPHA_VANTAGE_API_KEY}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if "Time Series (Daily)" in data:
                return json.dumps(data["Time Series (Daily)"])
            else:
                return json.dumps(data)
        except Exception as e:
            return f"Error retrieving daily price data for {ticker}: {e}"

# --- Instantiate all tools for the crew ---
fundamental_data_tool = FundamentalDataTool()
premium_technical_analysis_tool = PremiumTechnicalAnalysisTool()
news_sentiment_tool = NewsSentimentTool()
daily_price_tool = DailyPriceTool()