# tools/alpha_vantage_tools.py (FINAL - Corrected IndentationError and Production-Ready)

import os
import requests
import json
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from alpha_vantage.fundamentaldata import FundamentalData
import pandas as pd

# --- CONFIGURATION: Loading securely from environment ---
ALPHA_VANTAGE_API_KEY = "4A8LNUNXGL1ZH740"
if not ALPHA_VANTAGE_API_KEY:
    raise ValueError("CRITICAL: ALPHA_VANTAGE_API_KEY environment variable not found. Check your .env file.")

# --- HELPER FUNCTION FOR DIRECT API CALLS ---
def _fetch_av_data(function, ticker, **kwargs):
    """A centralized, clean helper to fetch data from Alpha Vantage's API."""
    base_url = "https://www.alphavantage.co/query?"
    params = f"function={function}&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}&entitlement=delayed"
    for key, value in kwargs.items():
        params += f"&{key}={value}"
    
    url = base_url + params
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    if "Error Message" in data or "Information" in data:
        return data
    return data

# --- TOOL 1: Advanced Technical Analysis Tool ---
class AdvancedTechnicalAnalysisTool(BaseTool):
    name: str = "Advanced Technical Analysis"
    description: str = (
        "Performs a comprehensive technical analysis by fetching multiple indicators and historical data. "
        "It analyzes trend strength, momentum, volume confirmation, and volatility to provide actionable insights, "
        "including calculated stop-loss and take-profit suggestions based on ATR."
    )

    def _run(self, ticker: str) -> str:
        try:
            daily_data_raw = _fetch_av_data("TIME_SERIES_DAILY", ticker, outputsize='full')
            daily_prices = daily_data_raw.get("Time Series (Daily)")
            if not daily_prices:
                return json.dumps({"error": "Failed to fetch daily price data.", "details": daily_data_raw})

            df = pd.DataFrame.from_dict(daily_prices, orient='index', dtype=float)
            df = df.rename(columns={
                '1. open': 'open', '2. high': 'high', 
                '3. low': 'low', '4. close': 'close', '5. volume': 'volume'
            })
            df = df.iloc[::-1]

            sma50_data = _fetch_av_data("SMA", ticker, interval='daily', time_period='50', series_type='close')
            sma200_data = _fetch_av_data("SMA", ticker, interval='daily', time_period='200', series_type='close')
            rsi_data = _fetch_av_data("RSI", ticker, interval='daily', time_period='14', series_type='close')
            atr_data = _fetch_av_data("ATR", ticker, interval='daily', time_period='14')

            latest_price = df['close'].iloc[-1]
            avg_volume_30d = df['volume'].tail(30).mean()
            latest_volume = df['volume'].iloc[-1]
            volume_analysis = {
                "latest_volume": f"{latest_volume:,.0f}",
                "30_day_avg_volume": f"{avg_volume_30d:,.0f}",
                "conclusion": "Above Average" if latest_volume > avg_volume_30d * 1.2 else "Below Average",
                "insight": "Strong volume confirms the latest price move." if latest_volume > avg_volume_30d * 1.2 else "Weak volume suggests a lack of conviction."
            }
            
            latest_sma50 = float(list(sma50_data['Technical Analysis: SMA'].values())[0]['SMA'])
            latest_sma200 = float(list(sma200_data['Technical Analysis: SMA'].values())[0]['SMA'])
            trend_conclusion = "Bullish" if latest_price > latest_sma50 > latest_sma200 else "Bearish" if latest_price < latest_sma50 < latest_sma200 else "Neutral/Ranging"
            trend_analysis = {"50_day_sma": latest_sma50, "200_day_sma": latest_sma200, "conclusion": trend_conclusion}

            latest_rsi = float(list(rsi_data['Technical Analysis: RSI'].values())[0]['RSI'])
            rsi_conclusion = "Overbought" if latest_rsi > 70 else "Oversold" if latest_rsi < 30 else "Neutral"
            momentum_analysis = {"rsi_14": latest_rsi, "conclusion": rsi_conclusion}

            latest_atr = float(list(atr_data['Technical Analysis: ATR'].values())[0]['ATR'])
            stop_loss_distance = round(latest_atr * 1.5, 2)
            volatility_analysis = {
                "atr_14": latest_atr,
                "insight": f"The stock has an average daily price movement range of approx. ${latest_atr:,.2f}.",
                "suggested_stop_loss_distance": stop_loss_distance
            }

            final_report = {
                "latest_price": latest_price,
                "trend_analysis": trend_analysis,
                "momentum_analysis": momentum_analysis,
                "volume_analysis": volume_analysis,
                "volatility_analysis": volatility_analysis,
                "expert_summary": (
                    f"The current trend is '{trend_conclusion}', with '{momentum_analysis['conclusion']}' momentum. "
                    f"The last day's volume was '{volume_analysis['conclusion']}', indicating "
                    f"{'strong conviction' if volume_analysis['conclusion'] == 'Above Average' else 'weak conviction'}. "
                    f"Expect a daily price fluctuation of around ${latest_atr:.2f}."
                )
            }
            return json.dumps(final_report, indent=2)
        except Exception as e:
            return json.dumps({"error": "Failed during advanced technical analysis.", "details": str(e)})

# --- TOOL 2: Fundamental Data ---
class FundamentalDataTool(BaseTool):
    name: str = "Get Company Overview & Fundamentals"
    description: str = "Retrieves comprehensive fundamental data for a given stock ticker."
    def _run(self, ticker: str) -> str:
        fd = FundamentalData(key=ALPHA_VANTAGE_API_KEY, output_format='json')
        try:
            overview, _ = fd.get_company_overview(symbol=ticker)
            return json.dumps(overview)
        except Exception as e:
            return f"Error retrieving fundamental data for {ticker}: {e}"

# --- TOOL 3: News & Sentiment ---
class NewsSentimentTool(BaseTool):
    name: str = "Get News & Market Sentiment"
    description: str = "Retrieves the latest news and sentiment analysis for a stock ticker."
    def _run(self, ticker: str) -> str:
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_API_KEY}'
        try:
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()
            return json.dumps(data.get('feed', []))
        except Exception as e:
            return f"Error retrieving news for {ticker}: {e}"

# --- TOOL 4: Yahoo Finance Screener ---
class YahooFinanceScreenerTool(BaseTool):
    name: str = "Yahoo Finance Stock Screener"
    description: str = "A tool that scrapes the Yahoo Finance 'Undervalued Large Caps' screener to find stable, low-risk companies."
    def _run(self) -> str:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            url = "https://finance.yahoo.com/screener/predefined/undervalued_large_caps"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            symbols = [a.text for a in soup.find_all('a', {'class': 'Fw(600) C($linkColor)'})]
            if not symbols:
                return "Could not find any stock tickers on the page."
            return ", ".join(symbols[:15])
        except Exception as e:
            return f"An error occurred while scraping Yahoo Finance: {e}"

# --- Instantiate all tools for the crew ---
fundamental_data_tool = FundamentalDataTool()
news_sentiment_tool = NewsSentimentTool()
yahoo_screener_tool = YahooFinanceScreenerTool()
advanced_technical_analysis_tool = AdvancedTechnicalAnalysisTool()