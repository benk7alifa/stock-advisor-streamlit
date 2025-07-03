# crew.py (FINAL - Corrected Summarizer Kickoff)

import os
import json
import yaml
from dotenv import load_dotenv
from pathlib import Path
import streamlit as st

# All imports and setup are correct.
USE_MOCK_DATA = False
load_dotenv()
from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperDevTool

if USE_MOCK_DATA:
    from tools.mock_alpha_vantage_tools import *
else:
    from tools.alpha_vantage_tools import *

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY")

class StockAnalysisCrew:
    # __init__, _create_agent, and _run_analysis_crew are all correct and do not need changes.
    def __init__(self):
        # ... (implementation is correct)
        self.agents_config = yaml.safe_load(Path('config/agents.yaml').read_text())
        self.tasks_config = yaml.safe_load(Path('config/tasks.yaml').read_text())
        self.search_tool = SerperDevTool()

    def _create_agent(self, name: str, tools: list) -> Agent:
        # ... (implementation is correct)
        return Agent(config=self.agents_config[name], tools=tools, allow_delegation=False, verbose=True)

    def _run_analysis_crew(self, ticker: str, query: str) -> str:
        # ... (implementation is correct)
        fundamental_analyst = self._create_agent('fundamental_analyst', [fundamental_data_tool])
        technical_analyst = self._create_agent('expert_technical_analyst', [advanced_technical_analysis_tool])
        sentiment_analyst = self._create_agent('sentiment_analyst', [news_sentiment_tool])
        recommendation_architect = self._create_agent('recommendation_architect', [])
        fundamental_task = Task(description=self.tasks_config['analyze_fundamentals']['description'].format(ticker=ticker), expected_output=self.tasks_config['analyze_fundamentals']['expected_output'], agent=fundamental_analyst)
        advanced_technical_task = Task(description=self.tasks_config['analyze_advanced_technicals']['description'].format(ticker=ticker), expected_output=self.tasks_config['analyze_advanced_technicals']['expected_output'], agent=technical_analyst)
        sentiment_task = Task(description=self.tasks_config['analyze_market_sentiment']['description'].format(ticker=ticker), expected_output=self.tasks_config['analyze_market_sentiment']['expected_output'], agent=sentiment_analyst)
        synthesis_task = Task(description=self.tasks_config['synthesize_trade_recommendation']['description'].format(ticker=ticker, query=query), expected_output=self.tasks_config['synthesize_trade_recommendation']['expected_output'].format(ticker=ticker), agent=recommendation_architect, context=[fundamental_task, advanced_technical_task, sentiment_task])
        analysis_crew = Crew(agents=[fundamental_analyst, technical_analyst, sentiment_analyst, recommendation_architect], tasks=[fundamental_task, advanced_technical_task, sentiment_task, synthesis_task], process=Process.sequential, verbose=True)
        return str(analysis_crew.kickoff())

    def kickoff(self, inputs: dict):
        query = inputs['query']
        print(f"--- Running routing for query: {query} ---")
        
        router_agent = self._create_agent('router_agent', [])
        routing_task = Task(description=self.tasks_config['route_user_query']['description'].format(query=query), expected_output=self.tasks_config['route_user_query']['expected_output'], agent=router_agent)
        routing_crew = Crew(agents=[router_agent], tasks=[routing_task], verbose=True)
        routing_result = routing_crew.kickoff()
        
        try:
            raw_output = str(routing_result)
            json_start = raw_output.find('{')
            json_end = raw_output.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_string = raw_output[json_start:json_end]
                routing_decision = json.loads(json_string)
            else:
                raise ValueError("No valid JSON object found in router's output.")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"--- Error parsing routing decision. Raw: {routing_result}. Error: {e} ---")
            return "Error: Router's response was unclear. Please rephrase your query."
        
        print(f"--- Routing Decision: {routing_decision} ---")
        
        route = routing_decision.get('route', '').lower()
        extracted_info = routing_decision.get('extracted_info')

        if route == 'ticker_specific_analysis':
            # This workflow is correct and robust
            tickers_to_analyze = []
            if isinstance(extracted_info, dict):
                tickers = extracted_info.get('tickers', [])
                if isinstance(tickers, list): tickers_to_analyze = tickers
                else:
                    ticker_val = extracted_info.get('ticker')
                    if isinstance(ticker_val, str): tickers_to_analyze = [ticker_val]
            elif isinstance(extracted_info, str):
                tickers_to_analyze = [t.strip().upper() for t in extracted_info.split(',')]
            if not tickers_to_analyze:
                return "Router identified a ticker query but could not extract any ticker symbols."
            print(f"--- Ticker analysis for: {tickers_to_analyze} ---")
            reports = [self._run_analysis_crew(t, query) for t in tickers_to_analyze]
            return "\n\n".join(reports)
        
        elif route == 'market_screening':
            print("--- Entering Intelligent Market Screening Funnel ---")
            
            broad_screener = self._create_agent('broad_screener_agent', [yahoo_screener_tool])
            qualitative_filter = self._create_agent('qualitative_filter_agent', [self.search_tool])
            screening_task = Task(description=self.tasks_config['screen_market_for_tickers']['description'].format(query=query), expected_output=self.tasks_config['screen_market_for_tickers']['expected_output'], agent=broad_screener)
            filtering_task = Task(description=self.tasks_config['filter_and_select_candidates']['description'].format(query=query), expected_output=self.tasks_config['filter_and_select_candidates']['expected_output'], agent=qualitative_filter, context=[screening_task])
            screening_funnel_crew = Crew(agents=[broad_screener, qualitative_filter], tasks=[screening_task, filtering_task], process=Process.sequential, verbose=True)
            final_ticker_list_str = str(screening_funnel_crew.kickoff())

            if not final_ticker_list_str or not final_ticker_list_str.strip():
                return "The screening funnel was unable to identify any promising stocks."

            print(f"--- Funnel identified top candidates: {final_ticker_list_str} ---")
            tickers = [t.strip().upper() for t in final_ticker_list_str.split(',') if t.strip()]
            
            details = [str(self._run_analysis_crew(t, query)) for t in tickers]
            
            # --- CORRECTED SUMMARIZER LOGIC ---
            summarizer_agent = self._create_agent('executive_summarizer_agent', [])
            
            # Join the reports into a single string for the context
            full_reports_text = "\n\n".join(details)
            
            summary_task = Task(
                # Format the description with the user query AND the full text of the reports
                description=self.tasks_config['summarize_findings']['description'].format(
                    query=query, 
                    reports_text=full_reports_text
                ),
                expected_output=self.tasks_config['summarize_findings']['expected_output'],
                agent=summarizer_agent
                # No 'context' needed here, as the info is now directly in the description
            )
            summary_crew = Crew(agents=[summarizer_agent], tasks=[summary_task], verbose=True)
            final_summary = str(summary_crew.kickoff())
            
            return f"{final_summary}\n\n## Detailed Analysis of Candidates\n\n{full_reports_text}"
        
        else:
            return "Error: Could not determine workflow from router's decision."