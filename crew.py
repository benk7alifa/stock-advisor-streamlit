import os
import json
import yaml
import re
from dotenv import load_dotenv
from pathlib import Path
import streamlit as st

from crewai import Agent, Crew, Process, Task
from langchain_openai import ChatOpenAI
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

# Your Alpha Vantage screener
from tools.alpha_vantage_tools import alpha_vantage_screen

load_dotenv()

# --- API Key Handling ---
OPENAI_API_KEY = None
SERPER_API_KEY = None
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
except (KeyError, FileNotFoundError):
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
if not OPENAI_API_KEY or not SERPER_API_KEY:
    raise ValueError("Set OPENAI_API_KEY and SERPER_API_KEY in .env or Streamlit secrets")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["SERPER_API_KEY"] = SERPER_API_KEY
# -------------------------

class StockAnalysisCrew:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini")

        base = Path(__file__).resolve().parent
        with open(base / 'config' / 'agents.yaml') as f:
            self.agents_config = yaml.safe_load(f)
        with open(base / 'config' / 'tasks.yaml') as f:
            self.tasks_config = yaml.safe_load(f)

        self.search_tool = SerperDevTool()
        self.scrape_tool = ScrapeWebsiteTool()

    def _create_agent(self, name, extra_tools=None):
        cfg = self.agents_config[name]
        return Agent(
            role=cfg['role'],
            goal=cfg['goal'],
            backstory=cfg['backstory'],
            llm=self.llm,
            tools=extra_tools or [],
            allow_delegation=False,
            verbose=True
        )

    def _run_analysis_crew(self, ticker, query):
        print(f"\n=== Starting full analysis for {ticker} ===")
        # --- Technical analysis phase ---
        print(f"--- Phase: Technical Analysis for {ticker} ---")
        tech = self._create_agent('technical_analyst', [self.search_tool, self.scrape_tool])
        tech_task = Task(
            description=self.tasks_config['analyze_technical_patterns']['description'].format(ticker=ticker),
            expected_output=self.tasks_config['analyze_technical_patterns']['expected_output'],
            agent=tech
        )
        tech_crew = Crew(agents=[tech], tasks=[tech_task], process=Process.sequential, verbose=True)
        tech_res = tech_crew.kickoff()
        tech_output = tech_res.raw if hasattr(tech_res, 'raw') else str(tech_res)
        print(f"--- Completed Technical Analysis for {ticker} ---")

        # --- Sentiment analysis phase ---
        print(f"--- Phase: Sentiment Analysis for {ticker} ---")
        sent = self._create_agent('sentiment_analyst', [self.search_tool, self.scrape_tool])
        sent_task = Task(
            description=self.tasks_config['analyze_market_sentiment']['description'].format(ticker=ticker),
            expected_output=self.tasks_config['analyze_market_sentiment']['expected_output'],
            agent=sent
        )
        sent_crew = Crew(agents=[sent], tasks=[sent_task], process=Process.sequential, verbose=True)
        sent_res = sent_crew.kickoff()
        sent_output = sent_res.raw if hasattr(sent_res, 'raw') else str(sent_res)
        print(f"--- Completed Sentiment Analysis for {ticker} ---")

        # --- Synthesis phase ---
        print(f"--- Phase: Synthesis for {ticker} ---")
        rec = self._create_agent('recommendation_architect')
        synth_task = Task(
            description=self.tasks_config['synthesize_trade_recommendation']['description']
                .format(ticker=ticker, query=query),
            expected_output=self.tasks_config['synthesize_trade_recommendation']['expected_output']
                .format(ticker=ticker),
            agent=rec,
            context=[tech_task, sent_task]
        )
        synth_crew = Crew(agents=[rec], tasks=[synth_task], process=Process.sequential, verbose=True)
        synth_res = synth_crew.kickoff()
        synth_output = synth_res.raw if hasattr(synth_res, 'raw') else str(synth_res)
        print(f"--- Completed Synthesis for {ticker} ===\n")

        # Combine all
        return "\n\n".join([tech_output, sent_output, synth_output])

    def kickoff(self, inputs):
        query = inputs['query']
        print(f"\n--- Running routing for query: {query} ---")

        # Routing
        router = self._create_agent('router_agent')
        route_task = Task(
            description=self.tasks_config['route_user_query']['description'].format(query=query),
            expected_output=self.tasks_config['route_user_query']['expected_output'],
            agent=router
        )
        routing = Crew(agents=[router], tasks=[route_task], verbose=True).kickoff()
        routing_text = routing.raw if hasattr(routing, 'raw') else str(routing)
        print(f"--- Routing output: {routing_text} ---")

        try:
            decision = json.loads(routing_text)
        except Exception:
            return "Error: Router output unclear. Please rephrase."

        route = decision.get('route')
        info  = decision.get('extracted_info') or ""
        print(f"--- Routing Decision: {decision} ---")

        # Ticker-specific
        if route == 'ticker_specific_analysis':
            tickers = [t.strip().upper() for t in info.split(',')]
            return "\n\n".join(self._run_analysis_crew(t, query) for t in tickers)

        # Market screening
        if route == 'market_screening':
            # parse parameters (as before)...
            n = int(re.search(r'(\d+)\s+stocks?', info, re.I).group(1)) if re.search(r'\d+\s+stocks?', info) else 5
            risk_map = {'low':(0.005,0.015),'medium':(0.015,0.03),'high':(0.03,0.1)}
            m_r = re.search(r'\b(low|medium|high)\s+risk', info, re.I)
            risk_band = risk_map[m_r.group(1).lower()] if m_r else (0,1)
            m_ret = re.search(r'(\d+)%', info)
            min_return = float(m_ret.group(1))/100 if m_ret else 0.0
            days = 5 if 'week' in info.lower() else (int(re.search(r'(\d+)\s+days?', info, re.I).group(1)) if re.search(r'(\d+)\s+days?', info, re.I) else 5)

            print(f"--- Market screening parameters → n={n}, risk_band={risk_band}, min_return={min_return:.2%}, days={days} ---")

            tickers = alpha_vantage_screen(n=n, risk_band=risk_band, min_return=min_return, return_window_days=days)
            print(f"--- Screened tickers: {tickers} ---")
            if not tickers:
                return "I couldn’t find any stocks matching those criteria right now."

            # Detailed + summary
            detailed = [self._run_analysis_crew(t, query) for t in tickers]
            summarizer = self._create_agent('executive_summarizer_agent')
            full_ctx = "\n\n".join(detailed)
            summary_task = Task(
                description=f"Summarize these analyses for '{query}':\n\n{full_ctx}",
                expected_output=self.tasks_config['summarize_findings']['expected_output'],
                agent=summarizer
            )
            summary_res = Crew(agents=[summarizer], tasks=[summary_task], verbose=True).kickoff()
            summary = summary_res.raw if hasattr(summary_res, 'raw') else str(summary_res)
            return f"{summary}\n\n## Detailed Analysis of Candidates\n\n{full_ctx}"

        # General QA fallback
        if route == 'general_qa':
            return ("This advisor is optimized for stock analysis and screening. "
                    "Ask about a specific ticker or screening criteria instead.")

        return "Error: The router failed to classify the query correctly."
