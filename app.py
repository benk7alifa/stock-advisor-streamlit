# app.py (FINAL - With ChromaDB/SQLite3 Fix for Deployment)

import streamlit as st
import sys

# --- THIS MUST BE THE VERY FIRST IMPORT IN YOUR SCRIPT ---
# This is the magic snippet that swaps out the old sqlite3 version
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass
# -------------------------------------------------------------

import io
import re
from contextlib import redirect_stdout
from crew import StockAnalysisCrew

# Must be the first Streamlit command
st.set_page_config(page_title="AI Stock Trading Advisor", page_icon="📈")

def clean_ansi_codes(text: str) -> str:
    """Strip ANSI escape codes from a log string."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# --- UI LAYOUT ---
st.title("📈 AI Stock Trading Advisor")
st.markdown("Welcome! Enter your stock query below and let our AI crew analyze it for you.")

with st.form(key='query_form'):
    user_query = st.text_input(
        "Your Query:",
        placeholder="e.g., Which stocks are showing bullish patterns right now?"
    )
    submit_button = st.form_submit_button(label='Analyze')

if submit_button and user_query:
    st.markdown("---")
    
    with st.spinner("🤖 Crew is thinking... This may take several minutes for market screening..."):
        log_stream = io.StringIO()
        with redirect_stdout(log_stream):
            try:
                crew = StockAnalysisCrew()
                result = crew.kickoff(inputs={'query': user_query})
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
                st.subheader("📋 Crew Process Log (on error)")
                log_contents = clean_ansi_codes(log_stream.getvalue())
                st.code(log_contents, language='bash')
                st.stop()
        
        st.subheader("✅ Crew Process Completed")
        with st.expander("Show Thinking Process"):
            log_contents = clean_ansi_codes(log_stream.getvalue())
            st.code(log_contents, language='bash')

        st.markdown("---")
        st.subheader("Final Advisor’s Report")
        st.markdown(result)

elif submit_button and not user_query:
    st.warning("Please enter a query to analyze.")