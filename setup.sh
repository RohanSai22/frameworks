#!/bin/bash
echo "🚀 Setting up Self-Improving Agent Framework"

# Install requirements
pip install -r requirements.txt

# Create directories
mkdir -p swe_bench_data/repos
mkdir -p workspace
mkdir -p archive

# Test LM Studio connection
echo "🧪 Testing LM Studio connection..."
curl -s http://localhost:1234/v1/models > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ LM Studio is running"
else
    echo "❌ LM Studio not detected. Please start it first!"
    exit 1
fi

echo "✅ Setup complete! Run: python main.py" 