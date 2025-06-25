import requests
import json
import os
from dotenv import load_dotenv
import subprocess
import tempfile
from pathlib import Path

# Load environment variables
load_dotenv()

class SimpleAgent:
    def __init__(self, code_dir):
        """Initialize the basic coding agent with LM Studio"""
        self.code_dir = code_dir
        self.base_url = "http://localhost:1234/v1"  # LM Studio default
        self.model_name = "deepseek/deepseek-r1-0528-qwen3-8b"
        
    def _call_lm_studio(self, messages, temperature=0.1, max_tokens=2000):
        """Call LM Studio API with OpenAI-compatible interface"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"Error: LM Studio API returned {response.status_code}: {response.text}"
                
        except Exception as e:
            return f"Error calling LM Studio: {str(e)}"
    
    def solve_task(self, problem_description, repo_path=None):
        """Main function that solves a coding task"""
        if repo_path:
            self.code_dir = repo_path
            
        prompt = f"""
You are an expert software engineer. Analyze and solve this GitHub issue:

## Problem Description:
{problem_description}

## Repository Location: 
{self.code_dir}

## Available Tools:
1. view_file(path) - View contents of a file
2. edit_file(path, content) - Write/overwrite a file with new content  
3. run_command(command) - Execute bash commands
4. list_files(directory) - List files in a directory

## CRITICAL INSTRUCTIONS:
1. First, explore the repository structure to understand the codebase
2. Identify the root cause of the issue
3. Implement a targeted fix with minimal changes
4. After making changes, generate a git diff patch

## REQUIRED OUTPUT FORMAT:
After you solve the issue, you MUST end your response with a properly formatted git patch like this:

```
diff --git a/path/to/file.py b/path/to/file.py
index abc123..def456 100644
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -10,3 +10,3 @@ def function():
-    old_line
+    new_line
```

Use the run_command tool with "git diff" to generate this patch after making your changes.

Please solve this step by step, explaining your reasoning, then provide the git diff.
"""

        messages = [{"role": "user", "content": prompt}]
        response = self._call_lm_studio(messages)

        # Always try to generate a git diff after the agent finishes
        try:
            diff_cmd = f"cd {self.code_dir} && git diff"
            import subprocess
            result = subprocess.run(diff_cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0 and result.stdout.strip():
                response += f"\n\nGenerated git patch:\n```\n{result.stdout}\n```"
        except Exception as e:
            print(f"Could not generate git diff: {e}")

        return response
    
    def self_modify(self, failure_logs, current_score):
        """Propose improvements to itself based on failures"""
        prompt = f"""
You are a meta-engineer improving a coding agent.

## Current Agent Performance:
- Success Rate: {current_score:.1%}
- Model: DeepSeek R1 on LM Studio

## Recent Failures:
{failure_logs}

## Current Agent Capabilities:
- File viewing and editing
- Command execution  
- Basic problem analysis
- Simple patch generation

## Your Task:
Analyze the failures and propose ONE specific improvement to make this coding agent better at solving SWE-bench issues.

Focus on:
1. Better code analysis techniques
2. Improved debugging strategies  
3. More sophisticated patch generation
4. Enhanced testing approaches
5. Better error handling

Respond with:
1. Root cause analysis of failures
2. Specific improvement proposal
3. Implementation details
4. Expected impact on success rate

Be concrete and actionable.
"""
        
        messages = [{"role": "user", "content": prompt}]
        return self._call_lm_studio(messages, temperature=0.3)
    
    def get_code(self):
        """Return the current agent code (for archiving)"""
        return f"DeepSeek_R1_Agent_LMStudio_v1"

# Enhanced tools for SWE-bench tasks
def view_file(path, line_range=None):
    """View contents of a file, optionally with line range"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            if line_range:
                lines = f.readlines()
                start, end = line_range
                return ''.join(lines[start-1:end])
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def edit_file(path, content):
    """Write content to a file"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {e}"

def run_command(command, cwd=None):
    """Execute a bash command"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60,
            cwd=cwd
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"error": str(e)}

def list_files(directory, max_depth=2):
    """List files in directory up to max_depth"""
    try:
        result = subprocess.run(
            f"find {directory} -maxdepth {max_depth} -type f | head -50",
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip().split('\n') if result.stdout else []
    except Exception as e:
        return [f"Error: {e}"]