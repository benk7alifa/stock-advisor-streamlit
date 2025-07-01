# app.py

import streamlit as st

# ─── MUST be the first Streamlit command ──────────────────────────────────────
st.set_page_config(page_title="AI Stock Trading Advisor", page_icon="📈")
# ────────────────────────────────────────────────────────────────────────────────

# Optional: fix for Chromadb’s Linux-only sqlite3 requirement
try:
    import pysqlite3
    import sys as _sys
    _sys.modules['sqlite3'] = _sys.modules.pop('pysqlite3')
except ImportError:
    pass

import sys
import io
import re

from crew import StockAnalysisCrew


def clean_ansi_codes(text: str) -> str:
    """Strip ANSI escape codes (coloured-text artifacts) from a log string."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


class StreamlitLogHandler(io.StringIO):
    """Capture print() output from CrewAI and render it live in Streamlit."""
    def __init__(self, container):
        super().__init__()
        self.container = container
        self.buffer = ""  # in-memory log buffer

    def write(self, s):
        cleaned = clean_ansi_codes(s)
        self.buffer += cleaned
        # render the entire buffer in a code block
        self.container.code(self.buffer, language='bash')
        # still print colored to your real terminal
        sys.__stdout__.write(s)
        super().write(s)

    def flush(self):
        sys.__stdout__.flush()


# ─── UI LAYOUT ────────────────────────────────────────────────────────────────
st.title("📈 AI Stock Trading Advisor")
st.markdown("Welcome! Enter your stock query below and let our AI crew analyze it for you.")
st.markdown("*(Example: Should I buy more AAPL shares today?)*")

user_query = st.text_input(
    "Your Query:",
    placeholder="e.g., Which stocks are showing bullish patterns right now?"
)

if st.button("Analyze"):
    if not user_query:
        st.warning("Please enter a query to analyze.")
    else:
        st.markdown("---")
        st.subheader("🤖 Crew Thinking Process…")

        # create a blank container for our logs
        log_container = st.empty()
        original_stdout = sys.stdout

        try:
            # swap in our handler so print() from CrewAI streams here
            sys.stdout = StreamlitLogHandler(log_container)
            crew = StockAnalysisCrew()
            result = crew.kickoff(inputs={'query': user_query})

            # restore stdout
            sys.stdout = original_stdout

            st.markdown("---")
            st.subheader("✅ Final Advisor’s Report")
            st.markdown(result)

        except Exception as e:
            # always restore stdout on error
            sys.stdout = original_stdout
            st.error(f"An unexpected error occurred: {e}")
