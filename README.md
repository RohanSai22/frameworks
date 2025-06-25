# my-self-improving-framework

## Setup

1. Install dependencies and create directories using the setup script:
   ```bash
   ./setup.sh
   ```
2. Copy the example environment file and add your API keys:
   ```bash
   cp .env.example .env
   # edit .env and set GROQ_API_KEY and OPENROUTER_API_KEY
   ```
3. Start LM Studio so that it is accessible at `http://localhost:1234` and run the framework:
   ```bash
   python main.py
   ```
4. The `SelfImprovingFramework` uses `ActionForcingAgent` to talk to multiple providers. You can switch providers at runtime with `framework.agent.set_provider(ModelProvider.YOUR_CHOICE)`.
# frameworks
