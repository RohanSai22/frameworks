import os
import time
import json
import signal
import sys
from datetime import datetime
from typing import Dict, List
import traceback

# Import our components
from agent import SimpleAgent
from archive import SimpleArchive
from evaluator import SWEBenchEvaluator
from swe_bench_loader import swe_bench

class InfiniteSelfImprovingFramework:
    def __init__(self):
        self.archive = SimpleArchive()
        self.evaluator = SWEBenchEvaluator(max_instances=30)
        self.running = True
        
        # Performance tracking
        self.iteration = 0
        self.best_score = 0.0
        self.improvement_log = []
        
        print("🚀 Infinite Self-Improving Framework with SWE-bench")
        print("🤖 Model: DeepSeek R1 on LM Studio")
        print("📊 Benchmark: SWE-bench Verified")
        print("🔄 Mode: Continuous Self-Improvement")
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown_handler)
        
    def shutdown_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n⏹️  Shutting down gracefully...")
        self.running = False
        self.export_final_results()
        sys.exit(0)
        
    def run_infinite_improvement(self):
        """Main infinite self-improvement loop"""
        print("\n🔄 Starting Infinite Self-Improvement Loop")
        print("Press Ctrl+C to stop and export results")
        print("=" * 60)
        
        # Create initial agent
        current_agent = SimpleAgent("./workspace")
        
        # Initial evaluation
        print(f"\n🧪 Initial Evaluation (Iteration 0)")
        initial_score = self.evaluator.evaluate_agent(current_agent, num_tasks=10)
        
        # Save initial agent
        initial_id = self.archive.save_agent(
            code=current_agent.get_code(),
            score=initial_score,
            description="Initial DeepSeek R1 agent",
            metadata={
                "iteration": 0, 
                "model": "deepseek-r1",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        self.best_score = initial_score
        self.log_improvement(0, initial_score, "Initial baseline")
        
        # Infinite improvement loop
        while self.running:
            try:
                self.iteration += 1
                print(f"\n{'='*60}")
                print(f"🔄 ITERATION {self.iteration}")
                print(f"🏆 Current Best Score: {self.best_score:.2%}")
                print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                
                # Generate failure analysis
                failure_logs = self.generate_failure_analysis()
                
                # Self-improve
                print("🧠 Generating self-improvement...")
                improvement = current_agent.self_modify(failure_logs, self.best_score)
                print(f"💡 Improvement idea: {improvement[:200]}...")
                
                # Create new agent (simplified - in practice you'd apply the improvement)
                new_agent = SimpleAgent("./workspace")
                new_agent.improvement_applied = improvement
                
                # Evaluate new agent
                print("🧪 Evaluating improved agent...")
                new_score = self.evaluator.evaluate_agent(new_agent, num_tasks=15)
                
                # Determine if this is an improvement
                is_improvement = new_score > self.best_score
                score_change = new_score - self.best_score
                
                # Save to archive
                agent_id = self.archive.save_agent(
                    code=new_agent.get_code(),
                    score=new_score,
                    parent_id=initial_id,
                    description=f"Iteration {self.iteration} - {'Improvement' if is_improvement else 'Exploration'}",
                    metadata={
                        "iteration": self.iteration,
                        "improvement": improvement[:500],
                        "score_change": score_change,
                        "is_improvement": is_improvement,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                # Update best if improved
                if is_improvement:
                    self.best_score = new_score
                    current_agent = new_agent
                    print(f"🎉 NEW BEST SCORE: {new_score:.2%} (+{score_change:.2%})")
                    self.log_improvement(self.iteration, new_score, "Performance improvement")
                else:
                    print(f"📊 Score: {new_score:.2%} ({score_change:+.2%}) - No improvement")
                    self.log_improvement(self.iteration, new_score, "Exploration attempt")
                
                # Show progress trends
                self.show_progress_summary()
                
                # Auto-save results every 5 iterations
                if self.iteration % 5 == 0:
                    self.export_intermediate_results()
                
                # Brief pause
                time.sleep(10)
                
            except Exception as e:
                print(f"❌ Error in iteration {self.iteration}: {e}")
                print(traceback.format_exc())
                time.sleep(30)  # Longer pause on error
                continue
                
    def generate_failure_analysis(self) -> str:
        """Generate analysis of recent failures for self-improvement"""
        recent_results = self.evaluator.results_history[-3:] if self.evaluator.results_history else []
        
        if not recent_results:
            return "No recent evaluation data available for analysis."
        
        failure_analysis = f"""
Recent Performance Analysis (Last {len(recent_results)} evaluations):

Performance Trend:
"""
        
        for i, result in enumerate(recent_results):
            score = result['score']
            failed_tasks = [r for r in result['results'] if not r['success']]
            
            failure_analysis += f"\nEvaluation {i+1}: {score:.1%} success rate\n"
            failure_analysis += f"Failed {len(failed_tasks)} out of {result['num_tasks']} tasks\n"
            
            if failed_tasks:
                failure_analysis += "Common failure patterns:\n"
                for task in failed_tasks[:3]:  # Show top 3 failures
                    failure_analysis += f"- {task['instance_id']}: {task['reason']}\n"
        
        # Add improvement suggestions
        failure_analysis += f"""
Improvement Areas Needed:
1. Better code understanding and analysis
2. More sophisticated debugging techniques
3. Improved patch generation strategies
4. Enhanced test-driven development
5. Better error handling and edge case coverage

Current Best Score: {self.best_score:.1%}
Target: Achieve >50% success rate on SWE-bench
"""
        
        return failure_analysis
    
    def log_improvement(self, iteration: int, score: float, description: str):
        """Log improvement for tracking"""
        self.improvement_log.append({
            "iteration": iteration,
            "score": score,
            "timestamp": datetime.now().isoformat(),
            "description": description
        })
    
    def show_progress_summary(self):
        """Show recent progress trends"""
        if len(self.improvement_log) < 2:
            return
            
        recent_scores = [entry["score"] for entry in self.improvement_log[-10:]]
        trend = "📈" if recent_scores[-1] > recent_scores else "📉" if recent_scores[-1] < recent_scores else "➡️"
        
        print(f"\n📊 Progress Summary:")
        print(f"   Recent Trend: {trend}")
        print(f"   Best Score: {max(recent_scores):.2%}")
        print(f"   Current Score: {recent_scores[-1]:.2%}")
        print(f"   Total Iterations: {self.iteration}")
        
        # Show improvement metrics
        metrics = self.evaluator.get_improvement_metrics()
        if metrics["trend"] != "insufficient_data":
            print(f"   Improvement Trend: {metrics['trend']} ({metrics['improvement']:+.2%})")
    
    def export_intermediate_results(self):
        """Export intermediate results"""
        filename = f"swe_bench_progress_iter_{self.iteration}.json"
        
        results = {
            "framework_info": {
                "model": "deepseek-r1-on-lm-studio",
                "benchmark": "swe-bench-verified",
                "current_iteration": self.iteration,
                "best_score": self.best_score,
                "export_time": datetime.now().isoformat()
            },
            "improvement_log": self.improvement_log,
            "evaluation_history": self.evaluator.results_history,
            "archive_stats": self.archive.get_statistics()
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"💾 Progress saved to {filename}")
    
    def export_final_results(self):
        """Export final comprehensive results"""
        filename = f"final_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        results = {
            "experiment_summary": {
                "model": "deepseek-r1-on-lm-studio",
                "benchmark": "swe-bench-verified", 
                "total_iterations": self.iteration,
                "best_score_achieved": self.best_score,
                "start_time": self.improvement_log["timestamp"] if self.improvement_log else None,
                "end_time": datetime.now().isoformat(),
                "total_runtime_hours": (time.time() - (time.time() - self.iteration * 600)) / 3600  # Rough estimate
            },
            "improvement_trajectory": self.improvement_log,
            "detailed_evaluations": self.evaluator.results_history,
            "archive_final_state": self.archive.get_statistics(),
            "best_agents": self.archive.get_top_agents(5)
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📁 Final results exported to {filename}")
        print(f"🏆 Final best score: {self.best_score:.2%}")
        print(f"🔄 Total iterations completed: {self.iteration}")

def main():
    """Main function to start infinite self-improvement"""
    print("🤖 DeepSeek R1 Self-Improving Agent Framework")
    print("📊 SWE-bench Verified Benchmark")
    print("🏠 Running on LM Studio (localhost:1234)")
    print("\nMake sure LM Studio is running with deepseek-r1-0528-qwen3-8b loaded!")
    
    # Test LM Studio connection
    try:
        import requests
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            print("✅ LM Studio connection successful")
        else:
            print("❌ LM Studio connection failed")
            return
    except Exception as e:
        print(f"❌ Cannot connect to LM Studio: {e}")
        print("Please start LM Studio and load the DeepSeek R1 model")
        return
    
    # Start infinite improvement
    framework = InfiniteSelfImprovingFramework()
    framework.run_infinite_improvement()

if __name__ == "__main__":
    main()
