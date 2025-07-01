import os
import json
import yaml
from dotenv import load_dotenv
from pathlib import Path
import streamlit as st

from crewai import Agent, Crew, Process, Task
from langchain_openai import ChatOpenAI
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

load_dotenv()

# --- Secure and Flexible API Key Handling ---
OPENAI_API_KEY = None
SERPER_API_KEY = None
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
except (KeyError, FileNotFoundError):
    print("Secrets not found on Streamlit, falling back to .env file.")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not OPENAI_API_KEY or not SERPER_API_KEY:
    raise ValueError("API keys for OpenAI and Serper are not set. Please add them to your .env file or Streamlit secrets.")

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["SERPER_API_KEY"] = SERPER_API_KEY
# --- End of Key Handling ---


class StockAnalysisCrew:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini")

        # reliably load config files relative to this file
        base_dir = Path(__file__).resolve().parent
        with open(base_dir / 'config' / 'agents.yaml', 'r') as f:
            self.agents_config = yaml.safe_load(f)
        with open(base_dir / 'config' / 'tasks.yaml', 'r') as f:
            self.tasks_config = yaml.safe_load(f)

        self.search_tool = SerperDevTool()
        self.scrape_tool = ScrapeWebsiteTool()

    def _create_agent(self, name: str, extra_tools: list = None) -> Agent:
        agent_config = self.agents_config[name]
        tools = extra_tools if extra_tools else []
        verbose_flag = agent_config.get('verbose', False)
        return Agent(
            role=agent_config['role'],
            goal=agent_config['goal'],
            backstory=agent_config['backstory'],
            llm=self.llm,
            tools=tools,
            allow_delegation=False,
            verbose=verbose_flag
        )

    def _run_analysis_crew(self, ticker: str, query: str) -> str:
        """Runs the sequential analysis crew for a single stock ticker."""
        technical_analyst = self._create_agent('technical_analyst', [self.search_tool, self.scrape_tool])
        sentiment_analyst = self._create_agent('sentiment_analyst', [self.search_tool, self.scrape_tool])
        recommendation_architect = self._create_agent('recommendation_architect')

        tech_analysis_task = Task(
            description=self.tasks_config['analyze_technical_patterns']['description'].format(ticker=ticker),
            expected_output=self.tasks_config['analyze_technical_patterns']['expected_output'],
            agent=technical_analyst
        )

        sentiment_analysis_task = Task(
            description=self.tasks_config['analyze_market_sentiment']['description'].format(ticker=ticker),
            expected_output=self.tasks_config['analyze_market_sentiment']['expected_output'],
            agent=sentiment_analyst
        )

        synthesis_task = Task(
            description=self.tasks_config['synthesize_trade_recommendation']['description'].format(ticker=ticker, query=query),
            expected_output=self.tasks_config['synthesize_trade_recommendation']['expected_output'].format(ticker=ticker),
            agent=recommendation_architect,
            context=[tech_analysis_task, sentiment_analysis_task]
        )

        analysis_crew = Crew(
            agents=[technical_analyst, sentiment_analyst, recommendation_architect],
            tasks=[tech_analysis_task, sentiment_analysis_task, synthesis_task],
            process=Process.sequential,
            verbose=True
        )

        analysis_result = analysis_crew.kickoff()
        return analysis_result.raw if hasattr(analysis_result, 'raw') else str(analysis_result)

    def kickoff(self, inputs: dict):
        query = inputs['query']
        print(f"--- Running routing for query: {query} ---")

        # 1) Route the user query
        router_agent = self._create_agent('router_agent')
        routing_task = Task(
            description=self.tasks_config['route_user_query']['description'].format(query=query),
            expected_output=self.tasks_config['route_user_query']['expected_output'],
            agent=router_agent
        )
        routing_crew = Crew(agents=[router_agent], tasks=[routing_task], verbose=True)
        routing_result = routing_crew.kickoff()

        # ── NEW: safely extract text from result.raw or fallback to str(...)
        routing_output = routing_result.raw if hasattr(routing_result, 'raw') else str(routing_result)
        try:
            routing_decision = json.loads(routing_output)
        except (json.JSONDecodeError, TypeError):
            print(f"--- Error: Could not parse routing decision. Raw output: {routing_output} ---")
            return "Error: The router's response was unclear. Please rephrase your query."

        print(f"--- Routing Decision: {routing_decision} ---")
        route = routing_decision.get('route')
        extracted_info = routing_decision.get('extracted_info')

        # 2) Handle ticker-specific analysis
        if route == 'ticker_specific_analysis':
            tickers_to_analyze = [t.strip().upper() for t in extracted_info.split(',')]
            reports = [self._run_analysis_crew(t, query) for t in tickers_to_analyze]
            return "\n\n".join(reports)

        # 3) Handle market screening
        elif route == 'market_screening':
            screener_agent = self._create_agent('stock_screener_agent', [self.search_tool, self.scrape_tool])
            screening_task = Task(
                description=self.tasks_config['screen_market_for_tickers']['description'].format(query=extracted_info),
                expected_output=self.tasks_config['screen_market_for_tickers']['expected_output'],
                agent=screener_agent
            )
            screening_crew = Crew(agents=[screener_agent], tasks=[screening_task], verbose=True)
            screening_result = screening_crew.kickoff()

            ticker_list_str = screening_result.raw if hasattr(screening_result, 'raw') else str(screening_result)
            if not ticker_list_str.strip():
                return "The market screener was unable to find any stocks matching your criteria."

            tickers = [t.strip().upper() for t in ticker_list_str.split(',')]
            details = [self._run_analysis_crew(t, query) for t in tickers]

            # Final executive summary
            summarizer_agent = self._create_agent('executive_summarizer_agent')
            full_context = "\n\n".join(details)
            summary_task = Task(
                description=(
                    f"Review the following collection of stock analyses provided below, inside the 'ANALYSIS REPORTS' section.\n"
                    f"The user's original request was: '{query}'.\n\n"
                    f"ANALYSIS REPORTS:\n{full_context}"
                ),
                expected_output=self.tasks_config['summarize_findings']['expected_output'],
                agent=summarizer_agent
            )
            summary_crew = Crew(agents=[summarizer_agent], tasks=[summary_task], verbose=True)
            summary_result = summary_crew.kickoff()
            final_summary = summary_result.raw if hasattr(summary_result, 'raw') else str(summary_result)

            return f"{final_summary}\n\n## Detailed Analysis of Candidates\n\n{full_context}"

        # 4) Handle general QA fallback
        elif route == 'general_qa':
            return (
                "Thank you for your question. This version of the advisor is optimized for stock analysis "
                "and screening. Please ask a question about a specific stock or ask me to find stocks "
                "with certain criteria."
            )

        # 5) Unknown route
        else:
            return "Error: The router failed to classify the query correctly. Please try again."
