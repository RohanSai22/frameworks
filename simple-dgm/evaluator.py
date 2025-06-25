import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import time
import re
from swe_bench_loader import swe_bench


class SWEBenchEvaluator:
    def __init__(self, max_instances=20):
        """Initialize evaluator with SWE-bench data"""
        self.max_instances = max_instances
        self.current_instances = []
        self.results_history = []
        
        # Load SWE-bench data
        success = swe_bench.load_swe_bench_verified(max_instances=max_instances)
        if success:
            self.current_instances = swe_bench.current_instances
            print(f"✅ Loaded {len(self.current_instances)} SWE-bench instances")
        else:
            print("❌ Failed to load SWE-bench data")
            
    def evaluate_agent(self, agent, num_tasks=10, timeout=300):
        """
        Evaluate agent on SWE-bench tasks
        """
        if not self.current_instances:
            print("No SWE-bench instances available")
            return 0.0
        
        num_tasks = min(num_tasks, len(self.current_instances))
        passed = 0
        results = []
        
        print(f"\n=== Evaluating Agent on {num_tasks} SWE-bench Tasks ===")
        
        for i in range(num_tasks):
            instance = self.current_instances[i]
            instance_id = instance['instance_id']
            problem = instance['problem_statement']
            
            print(f"\n🔍 Task {i+1}/{num_tasks}: {instance_id}")
            print(f"Repository: {instance['repo']}")
            
            try:
                start_time = time.time()
                
                # Setup repository
                repo_dir = swe_bench.setup_repository(instance)
                
                # Run agent on the problem
                solution = agent.solve_task(problem, repo_dir)
                
                # Extract patch from solution (simplified)
                patch = self.extract_patch_from_solution(solution, repo_dir)
                
                # Evaluate the patch
                evaluation = swe_bench.evaluate_patch(repo_dir, patch, instance)
                
                elapsed_time = time.time() - start_time
                
                result = {
                    "instance_id": instance_id,
                    "repo": instance['repo'],
                    "success": evaluation["success"],
                    "score": evaluation["score"],
                    "reason": evaluation["reason"],
                    "elapsed_time": elapsed_time,
                    "solution": solution[:500] + "..." if len(solution) > 500 else solution
                }
                
                results.append(result)
                
                if evaluation["success"]:
                    passed += 1
                    print(f"✅ PASSED: {evaluation['reason']}")
                else:
                    print(f"❌ FAILED: {evaluation['reason']}")
                
                print(f"⏱️  Time: {elapsed_time:.1f}s")
                
                # Cleanup
                if Path(repo_dir).exists():
                    shutil.rmtree(repo_dir)
                    
            except Exception as e:
                print(f"❌ ERROR: {str(e)}")
                results.append({
                    "instance_id": instance_id,
                    "success": False,
                    "score": 0.0,
                    "reason": f"Exception: {str(e)}",
                    "elapsed_time": 0
                })
                
        score = passed / num_tasks if num_tasks > 0 else 0.0
        
        # Store results
        evaluation_result = {
            "timestamp": time.time(),
            "num_tasks": num_tasks,
            "passed": passed,
            "score": score,
            "results": results
        }
        
        self.results_history.append(evaluation_result)
        
        print(f"\n=== Final Score: {score:.2%} ({passed}/{num_tasks}) ===")
        return score
    
    def extract_patch_from_solution(self, solution: str, repo_dir: str) -> str:
        """
        Extract git patch from agent solution with multiple fallback strategies
        """
        try:
            # Strategy 1: Look for diff blocks in the solution
            diff_pattern = r'``````'
            diff_matches = re.findall(diff_pattern, solution, re.DOTALL)
            if diff_matches:
                print("Found diff block in solution")
                return diff_matches[0]

            # Strategy 2: Look for any diff content starting with "diff --git"
            lines = solution.split('\n')
            diff_lines = []
            in_diff = False

            for line in lines:
                if line.startswith('diff --git'):
                    in_diff = True
                if in_diff:
                    diff_lines.append(line)

            if diff_lines:
                print("Found git diff in solution text")
                return '\n'.join(diff_lines)

            # Strategy 3: Generate git diff from current changes
            diff_cmd = f"cd {repo_dir} && git diff"
            import subprocess
            result = subprocess.run(diff_cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0 and result.stdout.strip():
                print("Generated git diff from current state")
                return result.stdout

            # Strategy 4: Check if there are any unstaged changes
            status_cmd = f"cd {repo_dir} && git status --porcelain"
            status_result = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)

            if status_result.stdout.strip():
                print("Found unstaged changes, generating diff")
                # Add all changes and create diff
                add_cmd = f"cd {repo_dir} && git add -A"
                subprocess.run(add_cmd, shell=True)

                diff_cached_cmd = f"cd {repo_dir} && git diff --cached"
                cached_result = subprocess.run(diff_cached_cmd, shell=True, capture_output=True, text=True)

                if cached_result.returncode == 0:
                    return cached_result.stdout

            print("No patch could be extracted - agent may not have made changes")
            return ""

        except Exception as e:
            print(f"Error extracting patch: {e}")
            return ""
    
    def is_agent_functional(self, agent) -> Tuple[bool, str]:
        """Check if agent can still perform basic operations"""
        try:
            # Simple functionality test
            test_response = agent.solve_task("Print 'Hello World'")
            
            if test_response and len(test_response) > 10:
                return True, "Agent responds to basic tasks"
            else:
                return False, "Agent gives minimal or no response"
                
        except Exception as e:
            return False, f"Agent error: {str(e)}"
    
    def get_improvement_metrics(self) -> Dict:
        """Get metrics showing improvement over time"""
        if len(self.results_history) < 2:
            return {"improvement": 0.0, "trend": "insufficient_data"}
        
        recent_scores = [r["score"] for r in self.results_history[-5:]]
        earlier_scores = [r["score"] for r in self.results_history[-10:-5]] if len(self.results_history) >= 10 else [self.results_history[-1]["score"]]
        
        recent_avg = sum(recent_scores) / len(recent_scores)
        earlier_avg = sum(earlier_scores) / len(earlier_scores)
        
        improvement = recent_avg - earlier_avg
        trend = "improving" if improvement > 0.01 else "declining" if improvement < -0.01 else "stable"
        
        return {
            "improvement": improvement,
            "trend": trend,
            "recent_avg": recent_avg,
            "earlier_avg": earlier_avg,
            "total_evaluations": len(self.results_history)
        }
    
    def export_results(self, filename="swe_bench_results.json"):
        """Export all evaluation results"""
        with open(filename, 'w') as f:
            json.dump({
                "evaluation_history": self.results_history,
                "summary": self.get_improvement_metrics()
            }, f, indent=2)
        print(f"📊 Results exported to {filename}")

if __name__ == "__main__":
    # Test the evaluator
    from agent import SimpleAgent
    
    # Create a dummy agent for testing
    class DummyAgent:
        def __init__(self):
            self.git_tempdir = None
            
        def solve_task(self, problem):
            # Dummy implementation
            if "add_numbers" in problem:
                return "def add_numbers(a, b):\n    return a + b"
            elif "Calculator" in problem:
                return "class Calculator:\n    def add(self, a, b):\n        return a + b\n    def subtract(self, a, b):\n        return a - b"
            else:
                return "# Solution placeholder"
    
    # Test the evaluator
    evaluator = SWEBenchEvaluator()
    dummy_agent = DummyAgent()
    
    print("Testing evaluator with dummy agent...")
    score = evaluator.evaluate_agent(dummy_agent, num_tasks=3)
    print(f"\nDummy agent scored: {score:.2%}")
    
    # Test agent functionality check
    is_functional, reason = evaluator.is_agent_functional(dummy_agent)
    print(f"Agent functional: {is_functional}, Reason: {reason}")
