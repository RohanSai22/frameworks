import os
import json
import time
from pathlib import Path
from agent.multi_model_agent import ActionForcingAgent, ModelProvider
from config.settings import Settings

class SelfImprovingFramework:
    def __init__(self):
        self.agent = ActionForcingAgent()
        self.settings = Settings()
        self.iteration_count = 0
        self.best_score = 0.0

        # Create directories
        self.settings.ARCHIVE_DIR.mkdir(exist_ok=True)
        self.settings.EVAL_DIR.mkdir(exist_ok=True)

    def run_evolution_loop(self):
        """Main self-improvement loop"""
        print("🧬 Starting Self-Improvement Evolution Loop")
        print(f"📊 Available models: {[p.value for p in self.agent.get_available_providers()]}")
        print(f"🎯 Current provider: {self.agent.current_provider.value}")

        while self.iteration_count < 10:
            try:
                print(f"\n🔁 Iteration {self.iteration_count}")
                score = self.evaluate_agent()
                print(f"🏅 Score: {score:.2%}")

                if score > self.best_score:
                    self.best_score = score
                    self.archive_agent(score)
                    print(f"🎉 New best score: {score:.2%}")

                improvement = self.generate_improvement()
                print(f"🔧 Generated improvement: {improvement['content'][:200]}...")

                self.iteration_count += 1

                time.sleep(2)

            except Exception as e:
                print(f"❌ Error in iteration {self.iteration_count}: {e}")
                print(f"💡 Consider switching providers manually or check {self.agent.current_provider.value} connection")
                self.iteration_count += 1

        print(f"🏁 Evolution complete! Best score: {self.best_score:.2%}")

    def switch_provider(self, provider: ModelProvider):
        """Manually switch to different provider"""
        try:
            self.agent.set_provider(provider)
            print(f"✅ Successfully switched to {provider.value}")
        except Exception as e:
            print(f"❌ Failed to switch to {provider.value}: {e}")

    def evaluate_agent(self) -> float:
        """Evaluate agent performance with current provider"""
        test_issue = """
        Create a Python function that calculates the factorial of a number.
        The function should handle edge cases like 0 and negative numbers.
        """

        try:
            result = self.agent.solve_task(test_issue, "/tmp/test_repo")

            content = result.get("content", "")

            score = 0.0
            if "def " in content:
                score += 0.3
            if "tool_call" in content:
                score += 0.4
            if "factorial" in content.lower():
                score += 0.3

            return min(score, 1.0)

        except Exception as e:
            print(f"❌ Evaluation failed: {e}")
            return 0.0

    def generate_improvement(self) -> dict:
        """Generate self-improvement suggestion with current provider"""
        performance_log = f"""
        Iteration: {self.iteration_count}
        Current Score: {self.best_score:.2%}
        Provider: {self.agent.current_provider.value}

        Recent issues:
        - Agent may not be using tools effectively
        - Need better action-forcing prompts
        - Could improve error handling
        """

        return self.agent.self_modify(performance_log)

    def archive_agent(self, score: float):
        """Archive successful agent version"""
        archive_data = {
            "iteration": self.iteration_count,
            "score": score,
            "provider": self.agent.current_provider.value,
            "timestamp": time.time(),
            "agent_config": "current_agent_version"
        }

        archive_file = self.settings.ARCHIVE_DIR / f"agent_v{self.iteration_count}.json"
        with open(archive_file, "w") as f:
            json.dump(archive_data, f, indent=2)


def main():
    """Run the framework"""
    print("🤖 Multi-Model Self-Improving Agent Framework")

    from dotenv import load_dotenv
    load_dotenv()

    framework = SelfImprovingFramework()

    framework.run_evolution_loop()


if __name__ == "__main__":
    main()
