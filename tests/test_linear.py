"""
Full end-to-end test for Linear - Request a demo from sales.

This test simulates the assignment scenario:
- Agent A sends a natural language task: "Go to linear.app and contact their sales to ask for a demo"
- Agent B (this system) plans steps using LLM, executes them, and captures UI states

This demonstrates all key requirements:
1. Natural language task handling at runtime
2. LLM-based step planning (generalizable across any web app)
3. Browser automation execution
4. UI state capture (including modals without URLs)
"""

import sys
from pathlib import Path

# Add project root to Python path so we can import agent modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.executor import Executor

if __name__ == "__main__":
    print("=" * 60)
    print("Linear Test - Request a Demo from Sales")
    print("=" * 60)
    print("\nThis demonstrates the full Agent B workflow:")
    print("  1. Receives natural language task at runtime")
    print("  2. Uses LLM to plan steps dynamically")
    print("  3. Executes steps in browser")
    print("  4. Captures screenshots of each UI state")
    print("=" * 60 + "\n")

    # Natural language task - this is what Agent A would send to Agent B
    # The system doesn't know this task ahead of time - it's received at runtime
    task_description = "Open linear.app and try to contact their sales team."
    
    print(f"[AGENT A] Task received: {task_description}\n")
    
    try:
        # Execute using reactive step-by-step planning
        # This is the key improvement: instead of planning all steps upfront,
        # we plan one step at a time based on what we see in the current UI state
        print("[EXECUTOR] Starting reactive browser automation...")
        print("This will plan each step based on the current UI state.\n")
        
        executor = Executor(task_name="test_linear", headless=False)
        executor.run_reactive(task_description, max_steps=20)
        
        print("\n" + "=" * 60)
        print("✅ Linear test completed!")
        print(f"📸 Screenshots saved to: dataset/linear_request_demo/")
        print("=" * 60)
        print("\nThis demonstrates:")
        print("  ✓ Natural language task → LLM-generated steps")
        print("  ✓ Generalizable across any web app")
        print("  ✓ Real-time UI state capture (including modals without URLs)")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        
        # Provide helpful guidance for common errors
        error_str = str(e).lower()
        if "quota" in error_str or "rate limit" in error_str:
            print("\n" + "=" * 60)
            print("💡 Solutions for quota/rate limit errors:")
            print("=" * 60)
            print("1. Check your OpenAI billing: https://platform.openai.com/account/billing")
            print("2. Add payment method or credits to your account")
            print("3. The system is already configured to use gpt-4o-mini (cheapest model)")
            print("4. You can test with hardcoded steps using tests/test.py instead")
            print("=" * 60)
        
        import traceback
        traceback.print_exc()
        sys.exit(1)

