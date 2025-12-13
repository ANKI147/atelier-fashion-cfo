from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

# Import agents from planner
from .planner import (
    agent_analyzer,
    agent_sourcer,
    agent_market,
    agent_optimizer
)


# ============================================================================
# STEP 1: Create PARALLEL workflow
# ============================================================================
# Agent B (Sourcer) and Agent C (Market) run at the SAME TIME
# Why? Because finding fabric prices and market prices are independent tasks

parallel_research = ParallelAgent(
    name="research_team",
    description="Runs fabric sourcing and market research at the same time",
    sub_agents=[agent_sourcer, agent_market]
)


# ============================================================================
# STEP 2: Create LOOP workflow  
# ============================================================================
# This contains: Parallel research → Optimizer
# Keeps repeating until optimizer calls exit_loop (or max 3 times)

optimization_loop = LoopAgent(
    name="optimization_loop",
    description="Keeps optimizing until profit target is met",
    sub_agents=[parallel_research, agent_optimizer],
    max_iterations=3  # Safety limit - don't loop forever!
)


# ============================================================================
# STEP 3: Create SEQUENTIAL workflow (the main pipeline)
# ============================================================================
# This is the complete workflow:
#   1. First: Analyzer (must finish before anything else)
#   2. Then: Optimization loop (contains parallel + optimizer)

root_agent = SequentialAgent(
    name="fashion_advisor",
    description="Complete fashion design profitability analyzer",
    sub_agents=[agent_analyzer, optimization_loop]
)


