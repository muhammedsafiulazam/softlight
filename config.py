"""
Configuration settings for the Agent B system.

This module loads environment variables and sets up configuration for the LLM planner.
All sensitive values (like API keys) should be stored in a .env file.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API key for the LLM planner
# Get this from: https://platform.openai.com/api-keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI model to use for step planning
# Valid options: gpt-4, gpt-4-turbo, gpt-4o, gpt-4o-mini
# 
# Cost comparison (approximate):
# - gpt-4o-mini: Cheapest option, good for testing
# - gpt-4o: Best balance of quality and cost (recommended)
# - gpt-4-turbo: More expensive, higher quality
# - gpt-4: Most expensive
#
# If you're hitting quota limits, try switching to gpt-4o-mini
MODEL = "gpt-4o-mini"  # Changed to cheaper model to avoid quota issues

# Validate that API key is set
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY is not set. Add it to your .env file.\n"
        "Create a .env file in the project root with:\n"
        "OPENAI_API_KEY=your-api-key-here"
    )