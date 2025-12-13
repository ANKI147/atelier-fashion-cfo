from datetime import datetime
from typing import Optional


class Memory:
    """
    Simple memory storage for the fashion AI.
    
    Usage:
        memory = Memory()
        memory.add_message("user", "Analyze my silk dress")
        memory.add_message("assistant", "I found it needs 4.5 yards")
        memory.add_optimization(1, "Silk", 45.0, 120.0, 20.8, False)
    """
    
    def __init__(self):
        """Initialize empty memory."""
        self.conversation = []      # List of messages
        self.optimizations = []     # List of optimization attempts
        self.final_result = None    # Final recommendation
        self.created_at = datetime.now()
    
    # =========================================================================
    # CONVERSATION HISTORY
    # =========================================================================
    
    def add_message(self, role: str, content: str, agent_name: str = None):
        """
        Add a message to conversation history.
        
        Args:
            role: "user" or "assistant"
            content: What was said
            agent_name: Which agent said it (optional)
        """
        self.conversation.append({
            "role": role,
            "content": content,
            "agent": agent_name,
            "time": datetime.now().strftime("%H:%M:%S")
        })
    
    def get_conversation(self) -> list:
        """Get all conversation messages."""
        return self.conversation
    
    def get_last_message(self) -> Optional[dict]:
        """Get the most recent message."""
        if self.conversation:
            return self.conversation[-1]
        return None
    
    # =========================================================================
    # OPTIMIZATION HISTORY
    # =========================================================================
    
    def add_optimization(
        self,
        iteration: int,
        fabric: str,
        fabric_cost: float,
        selling_price: float,
        margin_percent: float,
        is_profitable: bool
    ):
        """
        Record an optimization attempt.
        
        Args:
            iteration: Which attempt (1, 2, 3...)
            fabric: What fabric was tried
            fabric_cost: Total fabric cost
            selling_price: Market selling price
            margin_percent: Profit margin as percentage
            is_profitable: Did it meet the target?
        """
        self.optimizations.append({
            "iteration": iteration,
            "fabric": fabric,
            "fabric_cost": fabric_cost,
            "selling_price": selling_price,
            "profit": selling_price - fabric_cost - 50,  # -50 for labor
            "margin_percent": margin_percent,
            "is_profitable": is_profitable,
            "time": datetime.now().strftime("%H:%M:%S")
        })
    
    def get_optimizations(self) -> list:
        """Get all optimization attempts."""
        return self.optimizations
    
    def get_best_optimization(self) -> Optional[dict]:
        """Get the optimization with highest margin."""
        if not self.optimizations:
            return None
        return max(self.optimizations, key=lambda x: x["margin_percent"])
    
    def get_iteration_count(self) -> int:
        """How many optimization attempts so far."""
        return len(self.optimizations)
    
    # =========================================================================
    # FINAL RESULT
    # =========================================================================
    
    def set_final_result(self, recommendation: str, details: dict):
        """
        Store the final recommendation.
        
        Args:
            recommendation: "GREENLIGHT" or "NEEDS_REVIEW"
            details: Dictionary with final numbers
        """
        self.final_result = {
            "recommendation": recommendation,
            "details": details,
            "time": datetime.now().strftime("%H:%M:%S")
        }
    
    def get_final_result(self) -> Optional[dict]:
        """Get the final result if set."""
        return self.final_result
    
    # =========================================================================
    # SUMMARY & DISPLAY
    # =========================================================================
    
    def get_summary(self) -> str:
        """Get a human-readable summary of what happened."""
        lines = [
            "=" * 50,
            "THREAD-LOGIC SESSION SUMMARY",
            "=" * 50,
            f"Started: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Messages: {len(self.conversation)}",
            f"Optimization attempts: {len(self.optimizations)}",
            ""
        ]
        
        # Show optimization history
        if self.optimizations:
            lines.append("OPTIMIZATION HISTORY:")
            for opt in self.optimizations:
                status = "✅" if opt["is_profitable"] else "❌"
                lines.append(
                    f"  {status} Attempt {opt['iteration']}: "
                    f"{opt['fabric']} → {opt['margin_percent']}% margin"
                )
            lines.append("")
        
        # Show final result
        if self.final_result:
            lines.append("FINAL RESULT:")
            lines.append(f"  {self.final_result['recommendation']}")
        
        lines.append("=" * 50)
        return "\n".join(lines)
    
    def clear(self):
        """Clear all memory."""
        self.conversation = []
        self.optimizations = []
        self.final_result = None


# ============================================================================
# SIMPLE GLOBAL INSTANCE
# ============================================================================
# You can import this directly: from memory import session_memory

session_memory = Memory()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================
if __name__ == "__main__":
    # Demo the memory module
    mem = Memory()
    
    # Add conversation
    mem.add_message("user", "Analyze my emerald green silk dress")
    mem.add_message("assistant", "Analyzing your dress...", "analyzer")
    mem.add_message("assistant", "Found: Silk Charmeuse, 4.5 yards needed", "analyzer")
    
    # Add optimizations
    mem.add_optimization(
        iteration=1,
        fabric="Silk Charmeuse",
        fabric_cost=45.00,
        selling_price=120.00,
        margin_percent=20.8,
        is_profitable=False
    )
    
    mem.add_optimization(
        iteration=2,
        fabric="Polyester Satin",
        fabric_cost=15.75,
        selling_price=120.00,
        margin_percent=45.2,
        is_profitable=True
    )
    
    # Set final result
    mem.set_final_result("GREENLIGHT", {
        "fabric": "Polyester Satin",
        "profit": 54.25,
        "margin": 45.2
    })
    
    # Print summary
    print(mem.get_summary())