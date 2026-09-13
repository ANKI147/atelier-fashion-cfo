"""Modified for the standalone edition: isolate agent settings for each run."""

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


def build_root_agent(max_iterations: int = 3) -> SequentialAgent:
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or max_iterations < 1:
        raise ValueError("max_iterations must be a positive integer")

    configured_agent = root_agent.clone()
    configured_agent.sub_agents[1].max_iterations = max_iterations
    return configured_agent


