# This block attempts to import the Linux-only fix.
# If it fails (because we are on Windows), it will be skipped.
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ModuleNotFoundError:
    print("pysqlite3-binary not found, running with system's sqlite3.")
    pass
# Import necessary libraries

import streamlit as st
import sys
import io
import re # ADDED: Import the regular expression library

# We only need to import the crew class.
from crew import StockAnalysisCrew

# --- 1. ADDED: A function to clean the ANSI codes ---
def clean_ansi_codes(text):
    """
    Removes ANSI escape codes (used for color in terminals) from a string.
    """
    # This is a regular expression that finds and removes the color codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


# --- 2. MODIFIED: The Logging Handler Class ---
# This class will capture the print statements from CrewAI and display them in Streamlit
class StreamlitLogHandler(io.StringIO):
    def __init__(self, container):
        super().__init__()
        self.container = container
        # Initialize an empty string in session state to hold the log
        if 'log_output' not in st.session_state:
            st.session_state.log_output = ""

    def write(self, s):
        # Clean the incoming string 's' to remove color codes
        cleaned_s = clean_ansi_codes(s)

        # Append the CLEANED log messages to the session state variable
        st.session_state.log_output += cleaned_s

        # Display the accumulated CLEANED logs in a code block
        self.container.code(st.session_state.log_output, language='bash')
        
        # Also write the ORIGINAL (colored) string to the real terminal
        sys.__stdout__.write(s)
        
        # We must also call the superclass's write method for compatibility
        super().write(s)

    def flush(self):
        sys.__stdout__.flush()


# --- Page Configuration ---
st.set_page_config(page_title="AI Stock Trading Advisor", page_icon="📈")
st.title("📈 AI Stock Trading Advisor")
st.markdown("Welcome! Enter your stock query below and let our AI crew analyze it for you.")
st.markdown("*(Example: Should I buy more AAPL shares today?)*")

# --- User Input ---
user_query = st.text_input(
    "Your Query:",
    placeholder="e.g., Which stocks are showing bullish patterns right now?"
)

# --- Analysis Button ---
if st.button("Analyze"):
    if user_query:
        st.markdown("---")
        st.subheader("🤖 Crew Thinking Process...")
        
        log_container = st.empty()
        st.session_state.log_output = ""
        original_stdout = sys.stdout

        try:
            sys.stdout = StreamlitLogHandler(log_container)

            inputs = {'query': user_query}
            crew = StockAnalysisCrew()
            result = crew.kickoff(inputs=inputs)

            st.markdown("---")
            st.subheader("✅ Final Advisor's Report")
            st.markdown(result)

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
        finally:
            sys.stdout = original_stdout
    else:
        st.warning("Please enter a query to analyze.")