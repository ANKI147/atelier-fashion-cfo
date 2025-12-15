from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Import agents from planner
from .planner import (
    agent_analyzer,
    agent_sourcer,
    agent_market,
    agent_optimizer
)



parallel_research = ParallelAgent(
    name="research_team",
    description="Runs fabric sourcing and market research at the same time",
    sub_agents=[agent_sourcer, agent_market]
)



optimization_loop = LoopAgent(
    name="optimization_loop",
    description="Keeps optimizing until profit target is met",
    sub_agents=[parallel_research, agent_optimizer],
    max_iterations=3  # Safety limit 
)



root_agent = SequentialAgent(
    name="fashion_advisor",
    description="Complete fashion design profitability analyzer",
    sub_agents=[agent_analyzer, optimization_loop]
)


