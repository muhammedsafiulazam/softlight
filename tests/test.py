"""
Simple test for the Executor component.

This test verifies basic executor functionality with hardcoded steps.
It's useful for testing the executor without requiring LLM API calls or complex workflows.
"""

import sys
from pathlib import Path

# Add project root to Python path so we can import agent modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.executor import Executor

if __name__ == "__main__":
    # Simple, hard-coded steps that don't require login
    # This tests the executor's ability to handle basic navigate and wait_for actions
    steps = [
        {"navigate": {"url": "https://example.com"}},
        {"wait_for": {"selector": "body"}},
    ]

    # Create executor and run the steps
    # Screenshots will be saved to dataset/test/
    executor = Executor(task_name="test")
    executor.run(steps)