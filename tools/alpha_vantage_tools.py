# tools/alpha_vantage_tools.py (FINAL - With API Call Delays)

import os
import requests
import json
import time # Import the time module
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from alpha_vantage.fundamentaldata import FundamentalData

# --- CONFIGURATION: Using the hardcoded key for testing ---
ALPHA_VANTAGE_API_KEY = "4A8LNUNXGL1ZH740"

# --- HELPER FUNCTION FOR DIRECT API CALLS WITH DELAY ---
def _fetch_av_data(function, ticker, **kwargs):
    """A centralized helper to fetch data from Alpha Vantage's API, with a built-in delay."""
    # This delay is the most critical part of the fix.
    # It ensures we don't hit the API's rate limit (e.g., 30 calls per minute).
    # A 2.1-second delay keeps us safely under that limit.
    print(f"--- Waiting for 2.1 seconds to respect API rate limits... ---")
    time.sleep(2.1)
    
    print(f"--- Fetching {function} for {ticker}... ---")
    base_url = "https://www.alphavantage.co/query?"
    params = f"function={function}&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}&entitlement=delayed"
    for key, value in kwargs.items():
        params += f"&{key}={value}"
    
    url = base_url + params
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    # Check for the API's own rate limit message
    if "Information" in data and "rate limit" in data["Information"]:
        print(f"--- RATE LIMIT EXCEEDED FOR {ticker} on {function}. Waiting and retrying once... ---")
        time.sleep(60) # Wait for a full minute if we get a rate limit error
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

    if "Error Message" in data:
        return data

    return data

# --- Yahoo Screener Tool (Unchanged, as it calls a different service) ---
class YahooFinanceScreenerTool(BaseTool):
    name: str = "Yahoo Finance Stock Screener"
    description: str = (
        "A targeted tool that scrapes the Yahoo Finance screener for 'Undervalued Large Cap' stocks. "
        "It's a great starting point for finding stable, low-risk companies. This tool does not take any arguments."
    )
    def _run(self) -> str:
        # ... (implementation is unchanged)
        try:
            print("--- Scraping Yahoo Finance for undervalued large-cap stocks... ---")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            url = "https://finance.yahoo.com/screener/predefined/undervalued_large_caps"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            symbols = [a.text for a in soup.find_all('a', {'class': 'Fw(600) C($linkColor)'})]
            if not symbols:
                return "Could not find any stock tickers on the page. The page layout may have changed."
            return ", ".join(symbols[:15])
        except Exception as e:
            return f"An error occurred while scraping Yahoo Finance: {e}"

# --- Fundamental Data Tool (Updated to use the helper function) ---
class FundamentalDataTool(BaseTool):
    name: str = "Get Company Overview & Fundamentals"
    description: str = "Retrieves comprehensive fundamental data for a given stock ticker."
    def _run(self, ticker: str) -> str:
        # Using the centralized helper now
        data = _fetch_av_data("OVERVIEW", ticker)
        return json.dumps(data)

# --- Premium Technical Analysis Tool (Updated to use the helper function) ---
class PremiumTechnicalAnalysisTool(BaseTool):
    name: str = "Get Premium Technical Indicators"
    description: str = "Retrieves a comprehensive set of key technical indicators."
    def _run(self, ticker: str) -> str:
        indicators = {}
        try:
            sma50_data = _fetch_av_data("SMA", ticker, interval='daily', time_period='50', series_type='close')
            sma200_data = _fetch_av_data("SMA", ticker, interval='daily', time_period='200', series_type='close')
            rsi_data = _fetch_av_data("RSI", ticker, interval='daily', time_period='14', series_type='close')
            macd_data = _fetch_av_data("MACD", ticker, interval='daily', series_type='close')
            bbands_data = _fetch_av_data("BBANDS", ticker, interval='daily', time_period='20', series_type='close')
            
            indicators['SMA_50'] = list(sma50_data['Technical Analysis: SMA'].values())[0] if 'Technical Analysis: SMA' in sma50_data else "N/A"
            indicators['SMA_200'] = list(sma200_data['Technical Analysis: SMA'].values())[0] if 'Technical Analysis: SMA' in sma200_data else "N/A"
            indicators['RSI'] = list(rsi_data['Technical Analysis: RSI'].values())[0] if 'Technical Analysis: RSI' in rsi_data else "N/A"
            indicators['MACD'] = list(macd_data['Technical Analysis: MACD'].values())[0] if 'Technical Analysis: MACD' in macd_data else "N/A"
            indicators['Bollinger_Bands'] = list(bbands_data['Technical Analysis: BBANDS'].values())[0] if 'Technical Analysis: BBANDS' in bbands_data else "N/A"
            
            return json.dumps(indicators)
        except Exception as e:
            return f"An error occurred while fetching premium technical indicators: {e}"

# --- News & Sentiment Tool (Unchanged, as it's a different API endpoint) ---
class NewsSentimentTool(BaseTool):
    name: str = "Get News & Market Sentiment"
    description: str = "Retrieves the latest news and sentiment analysis for a given stock ticker."
    def _run(self, ticker: str) -> str:
        time.sleep(1) # Still good practice to add a small delay
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_API_KEY}'
        try:
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            return json.dumps(data.get('feed', []))
        except Exception as e:
            return f"Error retrieving news for {ticker}: {e}"

# --- Daily Price History Tool (Updated to use the helper function) ---
class DailyPriceTool(BaseTool):
    name: str = "Get Daily Stock Price History"
    description: str = "Retrieves the daily time series for the last 100 days for a given stock ticker."
    def _run(self, ticker: str) -> str:
        data = _fetch_av_data("TIME_SERIES_DAILY", ticker, outputsize='compact')
        return json.dumps(data.get("Time Series (Daily)", data))

# --- Instantiate all tools for the crew ---
fundamental_data_tool = FundamentalDataTool()
premium_technical_analysis_tool = PremiumTechnicalAnalysisTool()
news_sentiment_tool = NewsSentimentTool()
daily_price_tool = DailyPriceTool()
yahoo_screener_tool = YahooFinanceScreenerTool()