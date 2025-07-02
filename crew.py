# crew.py (FINAL CORRECTED - Boolean Verbosity)

import os
import json
import yaml
from dotenv import load_dotenv
from pathlib import Path
import streamlit as st

from crewai import Agent, Crew, Process, Task
from langchain_openai import ChatOpenAI
from crewai_tools import SerperDevTool

# --- Import our custom tool INSTANCES ---
from tools.alpha_vantage_tools import (
    fundamental_data_tool,
    technical_data_tool,
    news_sentiment_tool
)

load_dotenv()

# --- API Key Handling ---
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
if "SERPER_API_KEY" not in os.environ:
    os.environ["SERPER_API_KEY"] = st.secrets["SERPER_API_KEY"]
if "ALPHA_VANTAGE_API_KEY" not in os.environ:
    os.environ["ALPHA_VANTAGE_API_KEY"] = st.secrets["ALPHA_VANTAGE_API_KEY"]


class StockAnalysisCrew:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o")
        base_dir = Path(__file__).resolve().parent
        with open(base_dir / 'config' / 'agents.yaml', 'r') as f:
            self.agents_config = yaml.safe_load(f)
        with open(base_dir / 'config' / 'tasks.yaml', 'r') as f:
            self.tasks_config = yaml.safe_load(f)
        self.search_tool = SerperDevTool()

    def _create_agent(self, name: str, tools: list) -> Agent:
        """Helper function to create an agent from the YAML config."""
        agent_config = self.agents_config[name]
        return Agent(
            role=agent_config['role'],
            goal=agent_config['goal'],
            backstory=agent_config['backstory'],
            llm=self.llm,
            tools=tools,
            allow_delegation=False,
            verbose=agent_config.get('verbose', True)
        )

    def _run_analysis_crew(self, ticker: str, query: str) -> str:
        """Runs the hierarchical analysis crew for a single stock ticker."""
        fundamental_analyst = self._create_agent('fundamental_analyst', [fundamental_data_tool])
        technical_analyst = self._create_agent('technical_analyst', [technical_data_tool])
        sentiment_analyst = self._create_agent('sentiment_analyst', [news_sentiment_tool])
        recommendation_architect = self._create_agent('recommendation_architect', [])

        fundamental_task = Task(
            description=self.tasks_config['analyze_fundamentals']['description'].format(ticker=ticker),
            expected_output=self.tasks_config['analyze_fundamentals']['expected_output'],
            agent=fundamental_analyst
        )
        technical_task = Task(
            description=self.tasks_config['analyze_technical_patterns']['description'].format(ticker=ticker),
            expected_output=self.tasks_config['analyze_technical_patterns']['expected_output'],
            agent=technical_analyst
        )
        sentiment_task = Task(
            description=self.tasks_config['analyze_market_sentiment']['description'].format(ticker=ticker),
            expected_output=self.tasks_config['analyze_market_sentiment']['expected_output'],
            agent=sentiment_analyst
        )
        synthesis_task = Task(
            description=self.tasks_config['synthesize_trade_recommendation']['description'].format(ticker=ticker, query=query),
            expected_output=self.tasks_config['synthesize_trade_recommendation']['expected_output'].format(ticker=ticker),
            agent=recommendation_architect,
            context=[fundamental_task, technical_task, sentiment_task]
        )
        
        analysis_crew = Crew(
            agents=[fundamental_analyst, technical_analyst, sentiment_analyst, recommendation_architect],
            tasks=[fundamental_task, technical_task, sentiment_task, synthesis_task],
            process=Process.hierarchical,
            manager_llm=self.llm,
            verbose=True  # <-- CORRECTED
        )
        analysis_result = analysis_crew.kickoff()
        return str(analysis_result)

    def kickoff(self, inputs: dict):
        """The main entry point for the application."""
        query = inputs['query']
        print(f"--- Running routing for query: {query} ---")

        router_agent = self._create_agent('router_agent', [])
        routing_task = Task(
            description=self.tasks_config['route_user_query']['description'].format(query=query),
            expected_output=self.tasks_config['route_user_query']['expected_output'],
            agent=router_agent
        )
        routing_crew = Crew(
            agents=[router_agent], 
            tasks=[routing_task], 
            verbose=True  # <-- CORRECTED
        )
        routing_result = routing_crew.kickoff()
        
        try:
            cleaned_result = str(routing_result).strip()
            if cleaned_result.startswith("```json"):
                cleaned_result = cleaned_result[7:-3].strip()
            routing_decision = json.loads(cleaned_result)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"--- Error: Could not parse routing decision. Raw output: {routing_result}. Error: {e} ---")
            return "Error: The router's response was unclear. Please rephrase your query."

        print(f"--- Routing Decision: {routing_decision} ---")
        route = routing_decision.get('route')
        extracted_info = routing_decision.get('extracted_info')

        if route == 'ticker_specific_analysis':
            if not extracted_info:
                return "The router identified this as a ticker-specific query but could not extract a ticker."
            tickers_to_analyze = [t.strip().upper() for t in extracted_info.split(',')]
            reports = [self._run_analysis_crew(t, query) for t in tickers_to_analyze]
            return "\n\n".join(reports)
        
        elif route == 'market_screening':
            screener_agent = self._create_agent('stock_screener_agent', [self.search_tool])
            screening_task = Task(
                description=self.tasks_config['screen_market_for_tickers']['description'].format(query=extracted_info),
                expected_output=self.tasks_config['screen_market_for_tickers']['expected_output'],
                agent=screener_agent
            )
            screening_crew = Crew(
                agents=[screener_agent], 
                tasks=[screening_task], 
                verbose=True  # <-- CORRECTED
            )
            screening_result = screening_crew.kickoff()
            ticker_list_str = str(screening_result)
            
            if not ticker_list_str.strip():
                return "The market screener was unable to find any stocks matching your criteria."
            
            tickers = [t.strip().upper() for t in ticker_list_str.split(',')]
            details = [self._run_analysis_crew(t, query) for t in tickers]
            
            summarizer_agent = self._create_agent('executive_summarizer_agent', [])
            full_context = "\n\n".join(details)
            summary_task = Task(
                description=self.tasks_config['summarize_findings']['description'].format(query=query),
                expected_output=self.tasks_config['summarize_findings']['expected_output'],
                agent=summarizer_agent,
                context=details
            )
            summary_crew = Crew(
                agents=[summarizer_agent], 
                tasks=[summary_task], 
                verbose=True  # <-- CORRECTED
            )
            summary_result = summary_crew.kickoff()
            final_summary = str(summary_result)
            
            return f"{final_summary}\n\n## Detailed Analysis of Candidates\n\n{full_context}"
        
        elif route == 'general_qa':
            return "Thank you for your question. This AI advisor is optimized for specific stock analysis and market screening."
        
        else:
            return "Error: The router failed to classify the query correctly. Please try again."