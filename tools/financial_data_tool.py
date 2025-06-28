# import os
# from alpha_vantage.timeseries import TimeSeries
# from .base_tool import BaseTool # Import from our local base_tool.py

# class FinancialDataTool(BaseTool):
#     name: str = "Real-Time Stock Price Tool"
#     description: str = (
#         "A tool to get the latest closing price for a stock ticker. "
#         "Use this tool specifically for fetching the current or most recent trading price of a stock."
#     )

#     def _run(self, ticker: str) -> str:
#         try:
#             api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
#             if not api_key: return "Error: ALPHA_VANTAGE_API_KEY is not set."
#             ts = TimeSeries(key=api_key, output_format='json')
#             data, _ = ts.get_quote_endpoint(symbol=ticker)
#             if not data: return f"Error: Could not retrieve data for ticker {ticker}."
#             return f"The latest price for {ticker} is ${data.get('05. price')}."
#         except Exception as e:
#             return f"An error occurred while fetching stock data for {ticker}: {e}"