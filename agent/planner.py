"""
LLM-based step planner for converting natural language tasks to browser actions.

This module implements the planner component of Agent B. It uses OpenAI's API
to convert natural language task descriptions into structured browser automation steps.

Key features:
- Generalizable: Can handle any task, any web app
- Runtime planning: Tasks are unknown ahead of time
- Structured output: Returns JSON array of executable steps
"""

import json
import time
from openai import OpenAI, RateLimitError, APIError
from config import OPENAI_API_KEY, MODEL

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# System prompt for step-by-step reactive planning
SYSTEM_PROMPT = """
You are a UI step planner for a multi-agent browser automation system.

You work step-by-step: you see the current UI state and plan the NEXT single action to take.

You receive:
1. The overall task goal (e.g., "contact sales", "request a demo")
2. The current page state (DOM content or description)

CRITICAL: Always match your actions to the task goal!
- If the task is to "contact sales", look for buttons/links with text like "Contact", "Sales", "Contact Sales", "Get in Touch", "Request Demo"
- Do NOT click on unrelated navigation items like "Product", "Features", "Pricing" unless they lead to the contact/sales page
- Read the task goal carefully and only click elements that help achieve that goal

Output a JSON object with a single "step" key containing ONE action to take next.

Actions must be one of these types:
- navigate: {"url": "..."} - Navigate to a URL
- click: {"text": "..."} or {"selector": "..."} - Click an element by visible text (PREFERRED) or CSS selector
- type: {"text": "...", "value": "..."} or {"selector": "...", "value": "..."} - Type text into an input by label text (PREFERRED) or CSS selector
- wait_for: {"text": "..."} or {"selector": "..."} - Wait for an element to appear by text or selector
- done: {} - Task is complete, no more steps needed

IMPORTANT SELECTOR GUIDELINES:
- ALWAYS use visible text from buttons/links you see in the DOM, NOT CSS selectors
- When you see a button with text "Contact", click it using: {"click": {"text": "Contact"}}
- When you see a link with text "Sales", click it using: {"click": {"text": "Sales"}}
- Look for the actual visible text content in the DOM (the text between tags like <button>Contact</button>)
- Only use "selector" if the element has no visible text at all
- Text-based selection is more reliable because CSS classes change, but button text usually stays the same

Examples:
- You see: <button>Contact</button> → Use: {"step": {"click": {"text": "Contact"}}}  ✓
- You see: <a href="/sales">Request Demo</a> → Use: {"step": {"click": {"text": "Request Demo"}}}  ✓
- You see: <button class="complex-css">Submit</button> → Use: {"step": {"click": {"text": "Submit"}}}  ✓ (ignore the CSS class!)
- You see: <input type="text" placeholder="Email"> → Use: {"step": {"type": {"text": "Email", "value": "test@example.com"}}}  ✓
- You see: <button class="xyz"></button> (no text) → Use: {"step": {"click": {"selector": "button.xyz"}}}  ✗ Only as last resort

You must ONLY output valid JSON in this format:
{"step": {"click": {"text": "Contact Sales"}}}

IMPORTANT: Only output ONE step at a time. After this step executes, you'll see the new state and plan the next step.
"""

def plan_next_step(task: str, current_state: str, step_history: list = None, max_retries=3):
    """
    Plan the NEXT single step based on current UI state (reactive planning).
    
    This is the core of the step-by-step reactive system. Instead of planning all steps
    upfront, we plan one step at a time based on what we see in the current UI state.
    
    Args:
        task: Natural language description of the overall goal
              Example: "Create a project in Linear" or "Contact sales for a demo"
        current_state: Description of current UI state (DOM content or page description)
        step_history: List of steps already taken (for context)
        max_retries: Maximum number of retry attempts for rate limit errors
    
    Returns:
        Single step dictionary containing the next action, or None if task is complete
        Example: {"click": {"selector": "button.submit"}} or None if done
    
    Raises:
        RateLimitError: If quota is exceeded or rate limit is hit after retries
        APIError: For other API errors
    """
    # Build context about what we've done so far
    history_context = ""
    if step_history:
        history_context = f"\n\nSteps taken so far:\n"
        for i, step in enumerate(step_history[-5:], 1):  # Last 5 steps for context
            history_context += f"{i}. {json.dumps(step)}\n"
        
        # Add warning about repeating steps
        history_context += "\n⚠️ CRITICAL: Do NOT repeat any of the steps above! Try a different action."
    
    # Create prompt with task, current state, and history
    # Limit DOM size to avoid token limits
    state_preview = current_state[:2000]
    
    prompt = f"""Task goal: {task}

REMEMBER: Your task is to "{task}". Only click on elements that help achieve this goal.
- Look in the DOM above for actual text that relates to your task
- Do NOT make up text - only use text that you can see in the "Current page state" section
- Do NOT click on: Product, Features, Pricing, Blog, About (unless they lead to contact/sales)
- Think: "Does clicking this help me contact sales?" If no, don't click it.

CRITICAL: Avoid repeating steps!
- Check the step history above - do NOT repeat any action you've already tried
- If a previous step didn't work, try a different approach or element
- If you're stuck, try navigating to a different page or looking for alternative paths

CRITICAL: Only use text that ACTUALLY EXISTS in the DOM above!
- Look at the "Current page state" section - find the EXACT text that appears there
- Do NOT make up or infer text like "Get in Touch" if you don't see it in the DOM
- Do NOT use common phrases - only use text that is actually present in the HTML
- Copy the exact text from the DOM (e.g., if you see <button>Contact Sales</button>, use "Contact Sales" exactly)
- If you don't see relevant text in the DOM, try a different approach (navigate, wait, or use selector)

Current page state:
{state_preview}
{history_context}

What is the NEXT single action to take? Make sure it:
1. Moves you closer to the task goal
2. Is DIFFERENT from previous steps (don't repeat!)
3. Uses ONLY text that appears in the DOM above (don't make up text!)
4. Output only ONE step."""
    
    # Retry logic for rate limit errors
    for attempt in range(max_retries):
        try:
            # Call OpenAI API with JSON response format to ensure valid JSON output
            res = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}  # Forces JSON output
            )

            # Parse the JSON response
            response_content = res.choices[0].message.content
            parsed_response = json.loads(response_content)
            
            # Extract the single step
            step = parsed_response.get("step")
            
            # Check if task is complete
            if step and "done" in step:
                return None  # Task complete
            
            return step
            
        except RateLimitError as e:
            # Handle rate limit and quota errors
            error_message = str(e)
            
            if "insufficient_quota" in error_message or "quota" in error_message.lower():
                # Quota exceeded - user needs to add billing/credits
                raise RateLimitError(
                    "OpenAI API quota exceeded. Please:\n"
                    "1. Check your OpenAI billing: https://platform.openai.com/account/billing\n"
                    "2. Add payment method or credits to your account\n"
                    "3. Consider using a cheaper model (gpt-4o-mini) - update MODEL in config.py\n"
                    f"Original error: {error_message}"
                ) from e
            else:
                # Rate limit hit - retry with exponential backoff
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                    print(f"[PLANNER] Rate limit hit. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise RateLimitError(
                        f"Rate limit exceeded after {max_retries} attempts. Please wait and try again later.\n"
                        f"Original error: {error_message}"
                    ) from e
                    
        except APIError as e:
            # Other API errors
            raise APIError(
                f"OpenAI API error: {str(e)}\n"
                "Please check your API key and account status."
            ) from e
