import os
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from openai import OpenAI
import requests
from enum import Enum

class ModelProvider(Enum):
    LM_STUDIO = "lm_studio"
    GROQ = "groq"
    OPENROUTER = "openrouter"

@dataclass
class ModelConfig:
    provider: ModelProvider
    model_name: str
    api_key: Optional[str]
    base_url: str
    max_tokens: int = 4000
    temperature: float = 0.6
    requests_per_minute: int = 30

class MultiModelAgent:
    def __init__(self):
        self.models = {
            ModelProvider.LM_STUDIO: ModelConfig(
                provider=ModelProvider.LM_STUDIO,
                model_name="deepseek/deepseek-r1-0528-qwen3-8b",
                api_key=None,
                base_url="http://localhost:1234/v1",
                max_tokens=8000,
                temperature=0.3
            ),
            ModelProvider.GROQ: ModelConfig(
                provider=ModelProvider.GROQ,
                model_name="qwen-qwq-32b",
                api_key=os.getenv("GROQ_API_KEY"),
                base_url="https://api.groq.com/openai/v1",
                max_tokens=4000,
                temperature=0.6,
                requests_per_minute=30
            ),
            ModelProvider.OPENROUTER: ModelConfig(
                provider=ModelProvider.OPENROUTER,
                model_name="deepseek/deepseek-r1-0528:free",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1",
                max_tokens=6000,
                temperature=0.3,
                requests_per_minute=20
            )
        }

        self.clients = {}
        self._initialize_clients()
        self.current_provider = ModelProvider.GROQ  # Default provider

    def _initialize_clients(self):
        """Initialize OpenAI clients for each provider"""
        for provider, config in self.models.items():
            try:
                if config.api_key or provider == ModelProvider.LM_STUDIO:
                    self.clients[provider] = OpenAI(
                        api_key=config.api_key or "not-needed",
                        base_url=config.base_url
                    )
                    print(f"✅ {provider.value} client initialized")
                else:
                    print(f"⚠️ {provider.value} API key not found, skipping")
            except Exception as e:
                print(f"❌ Failed to initialize {provider.value}: {e}")

    def get_available_providers(self) -> List[ModelProvider]:
        """Get list of available model providers"""
        return list(self.clients.keys())

    def set_provider(self, provider: ModelProvider):
        """Manually set the active provider"""
        if provider in self.clients:
            self.current_provider = provider
            print(f"🔄 Switched to {provider.value}")
        else:
            raise ValueError(f"Provider {provider.value} not available")

    def call_model(self, messages: List[Dict], provider: Optional[ModelProvider] = None) -> Dict:
        """Call model with specified provider (no fallback)"""
        if provider is None:
            provider = self.current_provider

        if provider not in self.clients:
            raise Exception(f"Provider {provider.value} not available")

        return self._make_request(provider, messages)

    def _make_request(self, provider: ModelProvider, messages: List[Dict]) -> Dict:
        """Make request to specific provider"""
        client = self.clients[provider]
        config = self.models[provider]

        kwargs = {
            "model": config.model_name,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature
        }

        if provider == ModelProvider.GROQ:
            kwargs.update({
                "top_p": 0.95,
                "stop": [""]
            })

        response = client.chat.completions.create(**kwargs)

        return {
            "content": response.choices[0].message.content,
            "provider": provider.value,
            "model": config.model_name,
            "finish_reason": response.choices[0].finish_reason,
            "usage": response.usage.dict() if response.usage else None
        }

class ActionForcingAgent(MultiModelAgent):
    """Agent that forces models to take actual actions"""

    def __init__(self):
        super().__init__()
        self.tools = {
            "bash": self._bash_tool,
            "str_replace_editor": self._editor_tool,
            "web_search": self._web_search_tool
        }

    def solve_task(self, issue_text: str, repo_path: str, provider: Optional[ModelProvider] = None) -> Dict:
        """Solve coding task with action-forcing prompts"""

        system_prompt = """You are a coding agent that MUST take concrete actions to solve problems.

CRITICAL RULES:
1. You MUST use tools to make actual file changes - never just describe solutions
2. For every problem, follow this sequence:
   - Use str_replace_editor to VIEW the relevant files first
   - Use str_replace_editor to EDIT files with specific changes  
   - Use bash to run tests and verify changes
   - Always end with actual file modifications

3. Your response must include actual tool calls, not just explanations
4. Think step by step, but ALWAYS execute the steps with tools

Available tools: bash, str_replace_editor, web_search

Format your tool calls as:

{"tool": "tool_name", "parameters": {...}}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
Fix this GitHub issue in the repository at {repo_path}:

{issue_text}

You MUST:
1. First examine the relevant files using str_replace_editor
2. Make the necessary code changes using str_replace_editor  
3. Test your changes using bash
4. Provide a summary of what you changed

START WORKING NOW - use the tools immediately, don't just plan.
"""}
        ]

        try:
            return self.call_model(messages, provider)
        except Exception as e:
            raise Exception(f"Task failed with {self.current_provider.value}: {e}")

    def self_modify(self, performance_log: str, provider: Optional[ModelProvider] = None) -> Dict:
        """Generate self-improvement suggestions"""
        messages = [
            {"role": "system", "content": "You are improving an AI agent's code. Suggest ONE specific code change that would improve performance based on the failure log."},
            {"role": "user", "content": f"""
Performance log:
{performance_log}

Suggest ONE concrete improvement to the agent code. Be specific about what file to change and what code to modify.
"""}
        ]

        try:
            return self.call_model(messages, provider)
        except Exception as e:
            raise Exception(f"Self-modification failed with {self.current_provider.value}: {e}")

    def _bash_tool(self, command: str) -> str:
        """Execute bash command"""
        import subprocess
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            return f"Exit code: {result.returncode}\nStdout: {result.stdout}\nStderr: {result.stderr}"
        except Exception as e:
            return f"Error executing command: {e}"

    def _editor_tool(self, action: str, **kwargs) -> str:
        """File editor tool"""
        if action == "view":
            try:
                with open(kwargs["path"], "r") as f:
                    content = f.read()
                return f"File content:\n{content}"
            except Exception as e:
                return f"Error reading file: {e}"

        elif action == "str_replace":
            try:
                with open(kwargs["path"], "r") as f:
                    content = f.read()

                new_content = content.replace(kwargs["old_str"], kwargs["new_str"])

                with open(kwargs["path"], "w") as f:
                    f.write(new_content)

                return f"File {kwargs['path']} updated successfully"
            except Exception as e:
                return f"Error updating file: {e}"

    def _web_search_tool(self, query: str) -> str:
        """Placeholder web search - integrate with your preferred search API"""
        return f"Search results for: {query}\n[Implement with SerpAPI, Brave, etc.]"
