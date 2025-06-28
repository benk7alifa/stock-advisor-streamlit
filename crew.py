# --- Your NEW and IMPROVED crew.py ---

import os
import json
import yaml
from dotenv import load_dotenv
from pathlib import Path
import streamlit as st # ADDED for secrets handling

from crewai import Agent, Crew, Process, Task
from langchain_openai import ChatOpenAI
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

# Load environment variables from .env file for local development
load_dotenv()

# --- NEW: Secure and Flexible API Key Handling ---
# This new logic checks for Streamlit's secrets first,
# and if it's not found (i.e., we are running locally),
# it falls back to using the .env file.
try:
    # This will work when deployed on Streamlit Cloud
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
except KeyError:
    # This will work when running locally
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Set the keys as environment variables for the tools to use
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["SERPER_API_KEY"] = SERPER_API_KEY
# --- End of New Logic ---

class StockAnalysisCrew:
    def __init__(self):
        # MODIFIED: Use the llm variable we defined above
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
        return Agent(
            **agent_config,
            llm=self.llm,
            tools=tools,
            allow_delegation=False,
        )

    # The rest of your kickoff method remains EXACTLY THE SAME...
    def kickoff(self, inputs: dict):
        query = inputs['query']
        print(f"--- Running routing for query: {query} ---")

        router_agent = self._create_agent('router_agent')
        technical_analyst = self._create_agent('technical_analyst', [self.search_tool, self.scrape_tool])
        sentiment_analyst = self._create_agent('sentiment_analyst', [self.search_tool, self.scrape_tool])
        recommendation_architect = self._create_agent('recommendation_architect')
        
        routing_task = Task(
            description=self.tasks_config['route_user_query']['description'].format(query=query),
            expected_output=self.tasks_config['route_user_query']['expected_output'],
            agent=router_agent,
        )

        routing_crew = Crew(agents=[router_agent], tasks=[routing_task], verbose=True)
        routing_result = routing_crew.kickoff()

        try:
            routing_decision = json.loads(str(routing_result))
        except (json.JSONDecodeError, TypeError):
            print(f"--- Error: Could not parse routing decision. Raw output: {routing_result} ---")
            return "Error: The router's response was unclear. Please rephrase your query."
        
        print(f"--- Routing Decision: {routing_decision} ---")
        
        route = routing_decision.get('route')
        extracted_info = routing_decision.get('extracted_info')
        tickers_to_analyze = []

        if route == 'market_wide_screening':
            print("Market-wide screening is not fully implemented in this version.")
            return "Market-wide screening is not fully implemented in this version."
        elif route == 'ticker_specific_analysis' and extracted_info:
            print(f"--- Ticker-Specific Analysis for: {extracted_info} ---")
            tickers_to_analyze = [extracted_info.upper()]
        
        if not tickers_to_analyze:
             return "No tickers were identified for analysis."

        ticker = tickers_to_analyze[0]
        
        tech_analysis_task = Task(
            description=self.tasks_config['analyze_technical_patterns']['description'].format(ticker=ticker),
            expected_output=self.tasks_config['analyze_technical_patterns']['expected_output'].format(ticker=ticker),
            agent=technical_analyst
        )
        
        sentiment_analysis_task = Task(
            description=self.tasks_config['analyze_market_sentiment']['description'].format(ticker=ticker),
            expected_output=self.tasks_config['analyze_market_sentiment']['expected_output'].format(ticker=ticker),
            agent=sentiment_analyst
        )
        
        synthesis_task = Task(
            description=self.tasks_config['synthesize_trade_recommendation']['description'],
            expected_output=self.tasks_config['synthesize_trade_recommendation']['expected_output'],
            agent=recommendation_architect,
            context=[tech_analysis_task, sentiment_analysis_task]
        )

        analysis_crew = Crew(
            agents=[technical_analyst, sentiment_analyst, recommendation_architect],
            tasks=[tech_analysis_task, sentiment_analysis_task, synthesis_task],
            process=Process.sequential,
            verbose=True
        )

        return analysis_crew.kickoff()