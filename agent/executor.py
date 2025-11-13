"""
Browser automation executor with dynamic action registry.

This module implements the executor component of Agent B. It uses a registry pattern
to handle different action types dynamically, making it extensible without hardcoding.

Key features:
- Dynamic action registry (not hardcoded if/elif)
- Automatic UI state capture after each action
- Error handling with state capture even on failures
- Configurable browser settings
"""

from playwright.sync_api import sync_playwright
from agent.capture import detect_and_capture

class Executor:
    """
    Executes browser automation steps and captures UI states.
    
    Uses a dynamic action registry pattern instead of hardcoded conditionals,
    making it easy to extend with new action types.
    """
    
    def __init__(self, task_name, headless=False, browser_type="chromium"):
        """
        Initialize the executor.
        
        Args:
            task_name: Name for this task (used for screenshot folder naming)
            headless: Whether to run browser in headless mode
            browser_type: Browser to use ("chromium", "firefox", or "webkit")
        """
        self.task_name = task_name
        self.headless = headless
        self.browser_type = browser_type
        self.action_handlers = {}  # Dynamic registry of action handlers
        self._register_default_actions()

    def _register_default_actions(self):
        """
        Register default action handlers. Can be extended with custom actions.
        
        This method registers the standard action types that the planner can generate.
        Users can extend this by calling register_action() with custom handlers.
        """
        self.register_action("navigate", self._handle_navigate)
        self.register_action("click", self._handle_click)
        self.register_action("type", self._handle_type)
        self.register_action("wait_for", self._handle_wait_for)

    def register_action(self, action_name, handler):
        """
        Register a custom action handler.
        
        This allows extending the executor with new action types without modifying
        the core code. The handler should accept (page, params) as arguments.
        
        Args:
            action_name: Name of the action (e.g., "scroll", "hover")
            handler: Function that takes (page, params) and executes the action
        """
        self.action_handlers[action_name] = handler

    def _handle_navigate(self, page, params):
        """
        Handle navigate action - loads a URL in the browser.
        
        Args:
            page: Playwright page object
            params: Dict containing "url" key
        """
        if "url" not in params:
            raise ValueError("navigate action missing 'url' parameter")
        page.goto(params["url"], wait_until="domcontentloaded")
        # Wait for network to be idle to ensure page is fully loaded
        page.wait_for_load_state("networkidle", timeout=5000)

    def _handle_click(self, page, params):
        """
        Handle click action - clicks an element on the page.
        
        Supports both text-based and CSS selector-based clicking.
        Text-based is preferred as it's more reliable.
        
        Args:
            page: Playwright page object
            params: Dict containing either "text" or "selector" key
        """
        if "text" in params:
            # Text-based selection (preferred)
            text = params["text"]
            # Check if the text actually exists on the page
            try:
                element = page.get_by_text(text, exact=False).first
                element.wait_for(timeout=3000)
                # Verify element is actually visible and clickable
                if not element.is_visible():
                    raise ValueError(f"Text '{text}' found but element is not visible")
                element.click()
            except Exception as e:
                # Text doesn't exist - this means LLM hallucinated the text
                raise ValueError(
                    f"Text '{text}' not found on page. The LLM may have suggested text that doesn't exist. "
                    f"Please check the actual DOM content. Error: {e}"
                )
        elif "selector" in params:
            # CSS selector-based selection (fallback)
            page.wait_for_selector(params["selector"])
            page.click(params["selector"])
        else:
            raise ValueError("click action missing 'text' or 'selector' parameter")
        
        # Wait for UI to update after click (modals, dropdowns, etc.)
        page.wait_for_timeout(500)

    def _handle_type(self, page, params):
        """
        Handle type action - fills an input field with text.
        
        Supports both text-based (by label) and CSS selector-based input.
        Text-based is preferred as it's more reliable.
        
        Args:
            page: Playwright page object
            params: Dict containing "value" and either "text" (label) or "selector" key
        """
        if "value" not in params:
            raise ValueError("type action missing 'value' parameter")
        
        value = params["value"]
        
        if "text" in params:
            # Text-based selection - find input by its label text
            label_text = params["text"]
            # Try multiple strategies to find the input field
            try:
                # Strategy 1: get_by_label (for proper label associations)
                page.get_by_label(label_text, exact=False).first.wait_for(timeout=2000)
                page.get_by_label(label_text, exact=False).first.fill(value)
            except:
                try:
                    # Strategy 2: Find input by aria-label or placeholder
                    input_elem = page.locator(f'input[aria-label*="{label_text}"], input[placeholder*="{label_text}"]').first
                    input_elem.wait_for(timeout=2000)
                    input_elem.fill(value)
                except:
                    try:
                        # Strategy 3: Find input near label text element
                        page.get_by_text(label_text, exact=False).first.locator('..').locator('input').fill(value)
                    except:
                        try:
                            # Strategy 4: Role-based search
                            page.get_by_role("textbox", name=label_text, exact=False).first.fill(value)
                        except:
                            # Strategy 5: Last resort - find by placeholder containing text
                            page.locator(f'input[placeholder*="{label_text}"]').first.fill(value)
        elif "selector" in params:
            # CSS selector-based selection (fallback)
            page.wait_for_selector(params["selector"])
            page.fill(params["selector"], value)
        else:
            raise ValueError("type action missing 'text' (label) or 'selector' parameter")
        
        # Wait for UI to update after typing (autocomplete, validation, etc.)
        page.wait_for_timeout(300)

    def _handle_wait_for(self, page, params):
        """
        Handle wait_for action - waits for an element to appear.
        
        Supports both text-based and CSS selector-based waiting.
        
        Args:
            page: Playwright page object
            params: Dict containing either "text" or "selector" key
        """
        if "text" in params:
            # Text-based waiting (preferred)
            page.get_by_text(params["text"], exact=False).first.wait_for()
        elif "selector" in params:
            # CSS selector-based waiting (fallback)
            page.wait_for_selector(params["selector"])
        else:
            raise ValueError("wait_for action missing 'text' or 'selector' parameter")

    def run(self, steps):
        """
        Execute a list of steps and capture UI states.
        
        This is the main execution loop. For each step:
        1. Validates the step format
        2. Captures DOM before the action
        3. Executes the action using the registered handler
        4. Waits for network/UI to stabilize
        5. Captures screenshot of the new UI state
        
        Args:
            steps: List of step dictionaries, each with an action name and params
                  Example: [{"navigate": {"url": "https://example.com"}}]
        """
        with sync_playwright() as p:
            # Launch browser (chromium, firefox, or webkit)
            browser_launcher = getattr(p, self.browser_type)
            browser = browser_launcher.launch(headless=self.headless)
            page = browser.new_page()

            # Capture initial state (empty page before any actions)
            # This gives us a baseline screenshot
            from agent.capture import capture_state
            capture_state(page, self.task_name, 0)

            step_index = 1

            for step in steps:
                # Validate step format
                if not isinstance(step, dict) or len(step) == 0:
                    print(f"[WARN] Skipping invalid step {step_index}: {step}")
                    step_index += 1
                    continue

                # Extract action name and parameters from step
                # Steps are in format: {"action_name": {"param": "value"}}
                action = list(step.keys())[0]
                params = step[action]

                if not isinstance(params, dict):
                    print(f"[WARN] Skipping step {step_index}: invalid params format")
                    step_index += 1
                    continue

                print(f"[EXEC] Step {step_index}: {action} → {params}")

                # Capture DOM before action to detect state changes
                dom_before = page.content()

                try:
                    # Get handler for this action from the registry
                    # This is the dynamic dispatch - no hardcoded if/elif!
                    handler = self.action_handlers.get(action)
                    if not handler:
                        print(f"[WARN] Step {step_index}: Unknown action type '{action}', skipping")
                        step_index += 1
                        continue

                    # Execute the action handler
                    handler(page, params)

                    # Wait for network to be idle (helps catch async updates like API calls)
                    # This ensures we capture the final state after all async operations complete
                    try:
                        page.wait_for_load_state("networkidle", timeout=2000)
                    except:
                        pass  # Continue if timeout - page might already be stable

                    # Detect UI state changed → capture screenshot
                    # always_capture=True ensures we get screenshots even if DOM change detection misses subtle changes
                    detect_and_capture(page, self.task_name, step_index, dom_before, always_capture=True)

                except Exception as e:
                    print(f"[ERROR] Step {step_index} failed: {e}")
                    # Still try to capture state even if action failed
                    # This helps debug what went wrong
                    try:
                        detect_and_capture(page, self.task_name, step_index, dom_before, always_capture=True)
                    except:
                        pass

                step_index += 1

            browser.close()

    def run_reactive(self, task: str, max_steps=20):
        """
        Execute task step-by-step using reactive planning.
        
        This is the new reactive approach: instead of planning all steps upfront,
        we plan one step at a time based on the current UI state.
        
        Process:
        1. Get current page state (DOM)
        2. Plan next step based on current state
        3. Execute the step
        4. Capture screenshot
        5. Repeat until task complete or max steps reached
        
        Args:
            task: Natural language description of what to do
                  Example: "Go to linear.app and contact their sales team to ask for a demo"
            max_steps: Maximum number of steps to prevent infinite loops
        """
        from agent.planner import plan_next_step
        from agent.browser import clean_dom
        from agent.capture import capture_state, detect_and_capture
        
        with sync_playwright() as p:
            # Launch browser
            browser_launcher = getattr(p, self.browser_type)
            browser = browser_launcher.launch(headless=self.headless)
            page = browser.new_page()

            # Capture initial state (empty page)
            capture_state(page, self.task_name, 0)

            step_index = 1
            step_history = []
            repeated_step_count = 0  # Track consecutive repeated steps

            print(f"[REACTIVE] Starting reactive execution for task: {task}")
            print(f"[REACTIVE] Maximum steps: {max_steps}\n")

            while step_index <= max_steps:
                try:
                    # Get current page state (cleaned DOM for planning)
                    current_dom = page.content()
                    current_state = clean_dom(current_dom)
                    
                    # Limit state size to avoid token limits
                    # Use first 2000 chars of cleaned DOM
                    state_summary = current_state[:2000]
                    
                    print(f"[PLANNER] Planning step {step_index} based on current UI state...")
                    
                    # Plan next step based on current state
                    next_step = plan_next_step(
                        task=task,
                        current_state=state_summary,
                        step_history=step_history
                    )
                    
                    # Check if task is complete
                    if next_step is None:
                        print(f"[REACTIVE] Task completed after {step_index - 1} steps!")
                        break
                    
                    # Validate step format
                    if not isinstance(next_step, dict) or len(next_step) == 0:
                        print(f"[WARN] Invalid step format: {next_step}")
                        break
                    
                    # Check for repeated steps
                    if next_step in step_history[-3:]:  # Check last 3 steps
                        repeated_step_count += 1
                        print(f"[WARN] Step repeated! This step was already tried: {next_step}")
                        print(f"[WARN] Repeated step count: {repeated_step_count}")
                        
                        if repeated_step_count >= 2:
                            print(f"[ERROR] Too many repeated steps. Stopping to avoid infinite loop.")
                            print(f"[INFO] Last 5 steps were: {step_history[-5:]}")
                            break
                        
                        # Skip this step and plan again
                        print(f"[INFO] Skipping repeated step, planning alternative...")
                        continue
                    else:
                        # Reset counter if we have a new step
                        repeated_step_count = 0
                    
                    # Extract action and params
                    action = list(next_step.keys())[0]
                    params = next_step[action]
                    
                    if not isinstance(params, dict):
                        print(f"[WARN] Invalid params format in step: {next_step}")
                        break
                    
                    print(f"[EXEC] Step {step_index}: {action} → {params}")
                    
                    # Capture DOM before action
                    dom_before = page.content()
                    
                    try:
                        # Get handler for this action
                        handler = self.action_handlers.get(action)
                        if not handler:
                            print(f"[ERROR] Unknown action type '{action}', stopping")
                            break
                        
                        # Execute the action
                        handler(page, params)
                        
                        # Wait for network to stabilize
                        try:
                            page.wait_for_load_state("networkidle", timeout=2000)
                        except:
                            pass
                        
                        # Capture screenshot of new state
                        detect_and_capture(page, self.task_name, step_index, dom_before, always_capture=True)
                        
                        # Add to history
                        step_history.append(next_step)
                        
                    except Exception as e:
                        print(f"[ERROR] Step {step_index} failed: {e}")
                        # Still capture state for debugging
                        try:
                            detect_and_capture(page, self.task_name, step_index, dom_before, always_capture=True)
                        except:
                            pass
                        # Continue to next step
                    
                    step_index += 1
                    
                except Exception as e:
                    print(f"[ERROR] Planning or execution error: {e}")
                    break
            
            if step_index > max_steps:
                print(f"[WARN] Reached maximum steps ({max_steps}). Task may not be complete.")
            
            browser.close()
