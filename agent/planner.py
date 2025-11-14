"""
LLM-based step planner for converting natural language tasks to browser actions.

This module implements the planner component of Agent B. It uses OpenAI's API
to convert natural language task descriptions into structured browser automation steps.

Key features:
- Generalizable: Can handle any task, any web app
- Runtime planning: Tasks are unknown ahead of time
- DOM-based: Analyzes DOM structure to provide precise selectors
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
2. The current page state (DOM content)

CRITICAL: Always match your actions to the task goal!
- If the task is to "contact sales", look for buttons/links with text like "Contact", "Sales", "Contact Sales", "Get in Touch", "Request Demo"
- Do NOT click on unrelated navigation items like "Product", "Features", "Pricing" unless they lead to the contact/sales page
- Read the task goal carefully and only click elements that help achieve that goal
- When you see forms, use the "type" action to fill input fields with appropriate values
- For contact forms, fill fields like: name, email, message, company, etc. with reasonable test values

Output a JSON object with a single "step" key containing ONE action to take next.

Actions must be one of these types:
- navigate: {"url": "..."} - Navigate to a URL
- click: {"selector": "..."} or {"xpath": "..."} or {"coordinates": {"x": 100, "y": 200}} - Click an element using precise selector
- type: {"selector": "...", "value": "..."} or {"xpath": "...", "value": "..."} - Type text into an input using precise selector
- wait_for: {"selector": "..."} or {"xpath": "..."} - Wait for an element to appear
- done: {} - Task is complete, no more steps needed

IMPORTANT: Provide PRECISE selectors based on DOM analysis!
- Analyze the DOM structure carefully to identify the exact element
- Use CSS selectors that uniquely identify the element (e.g., "button.contact-sales", "a[href='/contact']")
- Use XPath for complex selections (e.g., "//button[contains(text(), 'Contact')]")
- Use coordinates only as last resort if selector is not possible: {"coordinates": {"x": 100, "y": 200}}
- Create the most specific selector possible by analyzing element attributes, classes, text content, and DOM hierarchy

IMPORTANT SELECTOR GUIDELINES:
- Provide PRECISE selectors that uniquely identify the target element
- Analyze the DOM structure to create the most specific selector possible
- Use CSS selectors: "button.contact-btn", "a[href='/contact']", "nav > button:first-child"
- Use XPath for complex cases: "//button[contains(@class, 'contact')]", "//a[text()='Contact Sales']"
- Use coordinates as last resort: {"coordinates": {"x": 100, "y": 200}}
- Make selectors specific enough to avoid ambiguity (multiple matches)

Examples:
- You see: <button class="contact-btn">Contact</button> → Use: {"step": {"click": {"selector": "button.contact-btn"}}}  ✓
- You see: <a href="/sales">Request Demo</a> → Use: {"step": {"click": {"selector": "a[href='/sales']"}}}  ✓
- You see: <button class="btn primary">Submit</button> → Use: {"step": {"click": {"selector": "button.btn.primary"}}}  ✓
- You see: <input type="text" placeholder="Email"> → Use: {"step": {"type": {"selector": "input[placeholder='Email']", "value": "test@example.com"}}}  ✓
- You see: <input name="name" type="text"> → Use: {"step": {"type": {"selector": "input[name='name']", "value": "John Doe"}}}  ✓
- You see: <textarea id="message"></textarea> → Use: {"step": {"type": {"selector": "textarea#message", "value": "I'm interested in learning more"}}}  ✓
- Complex case: Use XPath → {"step": {"click": {"xpath": "//button[contains(text(), 'Contact') and @class='primary']"}}}  ✓
- Form filling: {"step": {"type": {"xpath": "//input[@type='email']", "value": "demo@example.com"}}}  ✓

You must ONLY output valid JSON in this format:
{"step": {"click": {"selector": "button.contact-sales"}}}

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
        current_state: Description of current UI state (DOM content)
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
- Analyze the DOM structure carefully to identify the exact element to interact with
- Create PRECISE selectors (CSS or XPath) that uniquely identify the target element
- Do NOT click on: Product, Features, Pricing, Blog, About (unless they lead to contact/sales)
- Think: "Does clicking this help me contact sales?" If no, don't click it.
- When you encounter forms, fill them out using the "type" action:
  * Identify input fields (input, textarea) using their attributes (name, id, placeholder, type)
  * Fill with appropriate test values (e.g., email: "test@example.com", name: "John Doe", message: "I'm interested")
  * After filling all fields, click the submit button

CRITICAL: Avoid repeating steps!
- Check the step history above - do NOT repeat any action you've already tried
- If a previous step didn't work, try a different approach or element
- If you're stuck, try navigating to a different page or looking for alternative paths

CRITICAL: Provide PRECISE selectors based on DOM analysis!
- Analyze the DOM structure carefully - look at element attributes, classes, IDs, text content, and hierarchy
- Create specific CSS selectors or XPath that uniquely identify the element
- Use element attributes (id, class, data-*, aria-*), text content, and parent/child relationships
- Make selectors specific enough to avoid ambiguity (multiple matches)
- Example: Instead of "button", use "button.contact-btn" or "nav > button:first-child"

Current page state (DOM):
{state_preview}
{history_context}

What is the NEXT single action to take? Provide a PRECISE selector (CSS or XPath) that uniquely identifies the target element. Make sure it:
1. Moves you closer to the task goal
2. Is DIFFERENT from previous steps (don't repeat!)
3. Uses a PRECISE selector that uniquely identifies the element based on DOM structure
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
                # Rate limit hit - this is different from quota!
                # Free tier accounts have strict per-minute limits (e.g., 3 requests/min for gpt-4o-mini)
                # Even with credits, you can hit rate limits if making too many requests too quickly
                if attempt < max_retries - 1:
                    # Longer wait times for rate limits (free tier needs more time)
                    wait_time = (2 ** attempt) * 10  # Exponential backoff: 10s, 20s, 40s
                    print(f"[PLANNER] ⚠️  Rate limit hit (requests per minute exceeded).")
                    print(f"[PLANNER] Waiting {wait_time} seconds before retry (attempt {attempt + 1}/{max_retries})...")
                    print(f"[PLANNER] 💡 Tip: Free tier accounts have strict rate limits. Consider:")
                    print(f"[PLANNER]    - Waiting longer between requests")
                    print(f"[PLANNER]    - Upgrading to a paid plan for higher limits")
                    print(f"[PLANNER]    - Using fewer steps (reduce max_steps)")
                    time.sleep(wait_time)
                else:
                    raise RateLimitError(
                        f"Rate limit exceeded after {max_retries} attempts.\n\n"
                        "⚠️  IMPORTANT: Rate limits are different from quota limits!\n"
                        "Even with credits, free tier accounts have strict per-minute request limits.\n\n"
                        "Solutions:\n"
                        "1. Wait 1-2 minutes and try again (rate limits reset per minute)\n"
                        "2. Upgrade to a paid plan for higher rate limits: https://platform.openai.com/account/billing\n"
                        "3. Reduce max_steps to make fewer API calls\n"
                        "4. Use tests/test.py for testing without LLM calls\n\n"
                        f"Original error: {error_message}"
                    ) from e
                    
        except APIError as e:
            # Other API errors
            raise APIError(
                f"OpenAI API error: {str(e)}\n"
                "Please check your API key and account status."
            ) from e
