# --- FINAL, v2 - CORRECTED crew.py ---

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
        with open('config/agents.yaml', 'r') as f:
            self.agents_config = yaml.safe_load(f)
        with open('config/tasks.yaml', 'r') as f:
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

        router_agent = self._create_agent('router_agent')
        routing_task = Task(
            description=self.tasks_config['route_user_query']['description'].format(query=query),
            expected_output=self.tasks_config['route_user_query']['expected_output'],
            agent=router_agent
        )

        routing_crew = Crew(agents=[router_agent], tasks=[routing_task], verbose=True)
        routing_result = routing_crew.kickoff()

        try:
            routing_decision = json.loads(routing_result.raw)
        except (json.JSONDecodeError, TypeError):
            print(f"--- Error: Could not parse routing decision. Raw output: {routing_result.raw if hasattr(routing_result, 'raw') else routing_result} ---")
            return "Error: The router's response was unclear. Please rephrase your query."
        
        print(f"--- Routing Decision: {routing_decision} ---")
        
        route = routing_decision.get('route')
        extracted_info = routing_decision.get('extracted_info')
        
        if route == 'ticker_specific_analysis':
            print(f"--- Ticker-Specific Analysis for: {extracted_info} ---")
            tickers_to_analyze = [ticker.strip().upper() for ticker in extracted_info.split(',')]
            
            final_reports = []
            for ticker in tickers_to_analyze:
                print(f"\n--- Analyzing Ticker: {ticker} ---")
                report = self._run_analysis_crew(ticker, query)
                final_reports.append(report)
            return "\n\n".join(final_reports)

        elif route == 'market_screening':
            print(f"--- Market Screening for query: {extracted_info} ---")
            screener_agent = self._create_agent('stock_screener_agent', [self.search_tool, self.scrape_tool])
            screening_task = Task(
                description=self.tasks_config['screen_market_for_tickers']['description'].format(query=extracted_info),
                expected_output=self.tasks_config['screen_market_for_tickers']['expected_output'],
                agent=screener_agent
            )

            screening_crew = Crew(agents=[screener_agent], tasks=[screening_task], verbose=True)
            
            screening_result = screening_crew.kickoff()
            ticker_list_str = screening_result.raw if hasattr(screening_result, 'raw') else str(screening_result)

            if not ticker_list_str or not ticker_list_str.strip():
                return "The market screener was unable to find any stocks matching your criteria."

            print(f"--- Screener found tickers: {ticker_list_str} ---")
            tickers_to_analyze = [ticker.strip().upper() for ticker in ticker_list_str.split(',')]
            
            detailed_reports = []
            for ticker in tickers_to_analyze:
                print(f"\n--- Analyzing Ticker: {ticker} ---")
                report = self._run_analysis_crew(ticker, query)
                detailed_reports.append(report)
            
            # === FINAL SUMMARY STEP (CORRECTED) ===
            print("\n--- Assembling Final Executive Summary ---")

            summarizer_agent = self._create_agent('executive_summarizer_agent')
            
            # First, join the reports into a single string variable.
            full_context_for_summary = "\n\n".join(detailed_reports)

            # Then, create the final, clear description for the summarizer's task using the variable.
            summary_task_description = f"""
            Review the following collection of stock analyses provided below, inside the 'ANALYSIS REPORTS' section.
            The user's original request was: '{query}'.

            Your task is to write a final, top-level executive summary that will be presented to the user. This summary must directly and clearly answer the user's original question.

            ANALYSIS REPORTS:
            {full_context_for_summary}
            """

            summary_task = Task(
                description=summary_task_description,
                expected_output=self.tasks_config['summarize_findings']['expected_output'],
                agent=summarizer_agent
            )

            summary_crew = Crew(
                agents=[summarizer_agent],
                tasks=[summary_task],
                verbose=True
            )

            final_summary = summary_crew.kickoff()
            final_summary_text = final_summary.raw if hasattr(final_summary, 'raw') else str(final_summary)

            # Combine the executive summary with the detailed reports for the final output
            return f"{final_summary_text}\n\n## Detailed Analysis of Candidates\n\n" + full_context_for_summary

        elif route == 'general_qa':
            return "Thank you for your question. This version of the advisor is optimized for stock analysis and screening. Please ask a question about a specific stock or ask me to find stocks with certain criteria."
        
        else:
            return "Error: The router failed to classify the query correctly. Please try again."