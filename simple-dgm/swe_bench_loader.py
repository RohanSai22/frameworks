import json
import os
import tempfile
import subprocess
from pathlib import Path
from datasets import load_dataset
from typing import Dict, List, Optional
import shutil


class SWEBenchLoader:
    def __init__(self, data_dir="./swe_bench_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.dataset = None
        self.current_instances = []
        
    def load_swe_bench_verified(self, split="test", max_instances=50):
        """Load SWE-bench verified dataset"""
        print("Loading SWE-bench verified dataset...")
        try:
            # Load from HuggingFace
            self.dataset = load_dataset("princeton-nlp/SWE-bench_Verified", split=split)
            
            # Convert to list and limit
            self.current_instances = list(self.dataset)[:max_instances]
            print(f"Loaded {len(self.current_instances)} SWE-bench instances")
            
            return True
        except Exception as e:
            print(f"Error loading SWE-bench: {e}")
            return False
    
    def get_instance(self, instance_id: str) -> Optional[Dict]:
        """Get a specific instance by ID"""
        for instance in self.current_instances:
            if instance['instance_id'] == instance_id:
                return instance
        return None
    
    def get_random_instance(self) -> Dict:
        """Get a random instance for testing"""
        import random
        return random.choice(self.current_instances)
    
    def setup_repository(self, instance: Dict) -> str:
        """Setup repository for an instance"""
        instance_id = instance['instance_id']
        repo_name = instance['repo']
        base_commit = instance['base_commit']
        
        # Create temp directory for this instance
        repo_dir = self.data_dir / f"repos/{instance_id}"
        repo_dir.parent.mkdir(exist_ok=True)
        
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        
        print(f"Setting up repository for {instance_id}...")
        
        # Clone repository
        clone_cmd = f"git clone https://github.com/{repo_name}.git {repo_dir}"
        result = subprocess.run(clone_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to clone repository: {result.stderr}")
        
        # Checkout base commit
        checkout_cmd = f"cd {repo_dir} && git checkout {base_commit}"
        result = subprocess.run(checkout_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Warning: Could not checkout base commit: {result.stderr}")
        
        return str(repo_dir)
    
    def run_tests(self, repo_dir: str, instance: Dict) -> Dict:
        """Run tests for an instance"""
        test_patch = instance.get('test_patch', '')
        
        if not test_patch:
            return {"passed": False, "reason": "No test patch available"}
        
        try:
            # Apply test patch
            test_file = Path(repo_dir) / "test_patch.patch"
            test_file.write_text(test_patch)
            
            apply_cmd = f"cd {repo_dir} && git apply test_patch.patch"
            result = subprocess.run(apply_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"passed": False, "reason": f"Failed to apply test patch: {result.stderr}"}
            
            # Run tests (this varies by repository, simplified here)
            test_cmd = f"cd {repo_dir} && python -m pytest -xvs"
            result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=300)
            
            return {
                "passed": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except Exception as e:
            return {"passed": False, "reason": str(e)}
    
    def evaluate_patch(self, repo_dir: str, patch_content: str, instance: Dict) -> Dict:
        """Evaluate if a patch solves the issue"""
        try:
            # Reset repository
            reset_cmd = f"cd {repo_dir} && git checkout HEAD -- ."
            subprocess.run(reset_cmd, shell=True)
            
            # Apply the agent's patch
            patch_file = Path(repo_dir) / "agent_patch.patch"
            patch_file.write_text(patch_content)
            
            apply_cmd = f"cd {repo_dir} && git apply agent_patch.patch"
            result = subprocess.run(apply_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    "success": False, 
                    "reason": f"Patch failed to apply: {result.stderr}",
                    "score": 0.0
                }
            
            # Run the tests
            test_result = self.run_tests(repo_dir, instance)
            
            return {
                "success": test_result["passed"],
                "reason": test_result.get("reason", "Tests completed"),
                "score": 1.0 if test_result["passed"] else 0.0,
                "test_output": test_result.get("stdout", ""),
                "test_errors": test_result.get("stderr", "")
            }
            
        except Exception as e:
            return {"success": False, "reason": str(e), "score": 0.0}


# Global instance for easy access
swe_bench = SWEBenchLoader() 