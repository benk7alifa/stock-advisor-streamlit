# tools/alpha_vantage_tools.py (REFACTORED to use BaseTool)

import os
import requests
import json
from langchain.tools import BaseTool
from dotenv import load_dotenv

load_dotenv()

def get_alpha_vantage_api_key():
    """Helper function to securely get the Alpha Vantage API key."""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("ALPHA_VANTAGE_API_KEY")
        except (ImportError, AttributeError, KeyError):
            api_key = None
    if not api_key:
        raise ValueError("Alpha Vantage API key not found. Please set it in your .env file or Streamlit secrets.")
    return api_key

class GetDailyTimeSeriesTool(BaseTool):
    name: str = "Get Daily Time Series Stock Data"
    description: str = (
        "Fetches the daily time series (last 100 days) for a given stock symbol from Alpha Vantage. "
        "This includes open, high, low, close prices, and volume. The most recent data point contains the latest closing price. "
        "Use this tool as your primary source for all technical analysis, including getting the current stock price."
    )

    def _run(self, symbol: str) -> str:
        api_key = get_alpha_vantage_api_key()
        base_url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "apikey": api_key,
            "outputsize": "compact"
        }
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "Error Message" in data:
                return f"Error fetching data for {symbol}: {data['Error Message']}"
            
            time_series = data.get("Time Series (Daily)", {})
            if not time_series:
                return f"No daily time series data found for {symbol}. The symbol might be incorrect or delisted."

            simplified_data = {
                "symbol": symbol,
                "last_refreshed": data.get("Meta Data", {}).get("3. Last Refreshed"),
                "recent_data": {day: values for day, values in list(time_series.items())[:30]}
            }
            return json.dumps(simplified_data, indent=2)

        except requests.exceptions.RequestException as e:
            return f"An error occurred during API request: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

class GetNewsSentimentTool(BaseTool):
    name: str = "Get News and Sentiment for a Stock"
    description: str = (
        "Fetches recent news articles and their sentiment scores for a given stock symbol from Alpha Vantage. "
        "The data is already filtered to be recent. Do not perform extra web searches for news. "
        "Use this tool for all sentiment analysis tasks."
    )

    def _run(self, symbol: str) -> str:
        api_key = get_alpha_vantage_api_key()
        base_url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": api_key,
            "limit": "20"
        }
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data or 'feed' not in data or not data['feed']:
                 return f"No news or sentiment data found for {symbol}."

            simplified_feed = [{
                "title": item.get('title'),
                "summary": item.get('summary'),
                "overall_sentiment_score": item.get('overall_sentiment_score'),
                "overall_sentiment_label": item.get('overall_sentiment_label')
            } for item in data.get('feed', [])]
            return json.dumps(simplified_feed, indent=2)
            
        except requests.exceptions.RequestException as e:
            return f"An error occurred during API request: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"