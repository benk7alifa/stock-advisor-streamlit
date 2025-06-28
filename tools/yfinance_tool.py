# import yfinance as yf
# # The import path must also be simplified here
# from crewai_tools import BaseTool

# class StockPriceTool(BaseTool):
#     name: str = "Stock Price Tool"
#     description: str = (
#         "A tool to get the latest closing price for a stock ticker using yfinance. "
#         "The input should be a single stock ticker symbol (e.g., 'AAPL')."
#     )

#     def _run(self, ticker: str) -> str:
#         """The main execution method for the tool."""
#         try:
#             stock = yf.Ticker(ticker)
#             price = stock.history(period="1d")['Close']
#             if price.empty:
#                 return f"Could not find price data for {ticker}. It might be delisted or an invalid ticker."
#             return f"The latest closing price for {ticker} is ${price.iloc[-1]:.2f}."
#         except Exception as e:
#             return f"An error occurred while fetching the stock price for {ticker}: {e}"