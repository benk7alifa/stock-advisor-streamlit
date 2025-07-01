# tools/alpha_vantage_tools.py

import os
import pandas as pd
from alpha_vantage.timeseries import TimeSeries

# Load your API key (correct env var name)
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
if not API_KEY:
    raise ValueError("Set ALPHA_VANTAGE_API_KEY in your .env or Streamlit secrets")

# Initialize the client using the free TIME_SERIES_DAILY endpoint
ts = TimeSeries(key=API_KEY, output_format="pandas", indexing_type="date")


def get_sp500_tickers() -> list[str]:
    """Fetch the current S&P 500 constituents from Wikipedia."""
    table = pd.read_html(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    )[0]
    return table.Symbol.tolist()


def alpha_vantage_screen(
    n: int,
    risk_band: tuple[float, float],
    min_return: float,
    return_window_days: int = 5,
) -> list[str]:
    """
    Screen the S&P 500 for:
      • daily volatility in risk_band
      • cumulative return over return_window_days ≥ min_return
    Returns up to n tickers that match, with debug prints.
    """
    candidates = []
    universe = get_sp500_tickers()
    total = len(universe)
    print(f"--- alpha_vantage_screen: universe size = {total} tickers ---")

    for idx, symbol in enumerate(universe, start=1):
        print(f"[{idx}/{total}] Fetching daily for {symbol}…")
        try:
            # FREE endpoint
            data, _ = ts.get_daily(symbol=symbol, outputsize="compact")
        except Exception as e:
            print(f"    → Skipping {symbol}: {e}")
            continue

        # '4. close' is the standard close price in get_daily
        if '4. close' not in data:
            print(f"    → No close price for {symbol}, skipping")
            continue

        close = data["4. close"].sort_index()
        returns = close.pct_change().dropna()
        vol = returns.std()

        # Volatility filter
        if not (risk_band[0] <= vol <= risk_band[1]):
            continue

        # Enough history?
        if len(close) < return_window_days + 1:
            continue

        cum_ret = close.iloc[-1] / close.iloc[-(return_window_days + 1)] - 1
        if cum_ret >= min_return:
            print(f"    → Candidate {symbol}: vol={vol:.4%}, ret={cum_ret:.2%}")
            candidates.append(symbol)

        if len(candidates) >= n:
            break

    print(f"--- Screening complete: found {len(candidates)} candidate(s) ---")
    return candidates
