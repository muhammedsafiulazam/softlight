# Softlight Take-Home — Multi-Agent UI State Capture System

This project implements **Agent B**: A generalizable UI state exploration agent that automatically navigates web apps, executes tasks, and captures screenshots of each UI state in real-time.

## 🎯 Overview

Agent B receives natural language tasks from Agent A at runtime (e.g., "Open linear.app and contact their sales team") and:
- Plans steps dynamically using LLM (no hardcoded workflows)
- Executes actions step-by-step based on current UI state
- Captures screenshots of each UI state change
- Works across any web app (Linear, Notion, Asana, etc.)

## ✨ Key Features

- **Step-by-Step Reactive Planning**: Plans one action at a time based on current UI state (not all steps upfront)
- **Precise DOM-Based Selectors**: OpenAI analyzes DOM structure to generate precise CSS selectors, XPath, or coordinates
- **Form Filling**: Automatically identifies and fills form fields (input, textarea) with appropriate values
- **UI State Detection**: Captures screenshots even for modals/overlays without URL changes
- **Generalizable**: Handles any task, any web app - no hardcoding required
- **Error Handling**: Detects repeated steps, validates selectors, handles failures gracefully

## 🏗️ Architecture

```
Agent A (sends task)
    ↓
Agent B (this system)
    ├── Planner (LLM) → Generates next step based on current UI state
    ├── Executor → Executes step in browser
    ├── Browser Utils → DOM diffing for state detection
    └── Capture → Saves screenshots to dataset/
```

### Components

- **`agent/planner.py`**: LLM-based step planner (reactive, step-by-step)
  - Analyzes DOM structure to generate precise selectors
  - Plans next action based on current UI state and task goal
- **`agent/executor.py`**: Browser automation executor with dynamic action registry
  - Executes actions: navigate, click, type, wait_for
  - Supports CSS selectors, XPath, and coordinates
- **`agent/capture.py`**: UI state detection and screenshot capture
  - Captures screenshots after each action
  - Detects UI state changes via DOM diffing
- **`agent/browser.py`**: DOM diffing utilities for detecting UI changes
  - Cleans DOM for comparison
  - Detects significant UI state changes

## 🚀 Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your-openai-api-key-here
```

Get your API key from: https://platform.openai.com/api-keys

### 4. Configure Model (Optional)

Edit `config.py` to change the OpenAI model:
- `gpt-4o-mini` (cheapest, default)
- `gpt-4o` (recommended for production)
- `gpt-4-turbo` (higher quality)

## 📖 Usage

### Running Tests

**Linear Test** (contact sales):
```bash
python tests/test_linear.py
```

**Simple Test** (hardcoded steps, no LLM):
```bash
python tests/test.py
```

### Programmatic Usage

```python
from agent.executor import Executor

# Create executor
executor = Executor(task_name="my_task", headless=False)

# Run reactive step-by-step execution
executor.run_reactive(
    task="Go to linear.app and contact their sales team",
    max_steps=20
)

# Screenshots saved to: dataset/my_task/
```

### Supported Actions

The system supports the following action types:

- **`navigate`**: Navigate to a URL
  ```json
  {"navigate": {"url": "https://example.com"}}
  ```

- **`click`**: Click an element (supports CSS selector, XPath, or coordinates)
  ```json
  {"click": {"selector": "button.submit"}}
  {"click": {"xpath": "//button[contains(text(), 'Submit')]"}}
  {"click": {"coordinates": {"x": 100, "y": 200}}}
  ```

- **`type`**: Fill an input field with text
  ```json
  {"type": {"selector": "input[name='email']", "value": "test@example.com"}}
  {"type": {"xpath": "//input[@type='email']", "value": "test@example.com"}}
  ```

- **`wait_for`**: Wait for an element to appear
  ```json
  {"wait_for": {"selector": "div.loading"}}
  {"wait_for": {"xpath": "//div[@class='content']"}}
  ```

- **`done`**: Mark task as complete
  ```json
  {"done": {}}
  ```

## 🔄 How It Works

### Step-by-Step Reactive Planning

Unlike traditional automation that plans all steps upfront, this system:

1. **Observes** current UI state (DOM content)
2. **Plans** next single action using LLM based on DOM analysis
3. **Executes** the action using precise selectors
4. **Captures** screenshot of new state
5. **Repeats** until task complete

This reactive approach:
- Adapts to dynamic UIs
- Handles unexpected page structures
- Works without knowing the workflow ahead of time

### Precise DOM-Based Selectors

The system uses OpenAI to analyze the DOM structure and generate precise selectors:

- ✅ **CSS Selectors**: `{"click": {"selector": "button.contact-sales"}}` - Specific, reliable
- ✅ **XPath**: `{"click": {"xpath": "//button[contains(text(), 'Contact')]"}}` - Complex queries
- ✅ **Coordinates**: `{"click": {"coordinates": {"x": 100, "y": 200}}}` - Last resort

OpenAI analyzes element attributes, classes, IDs, text content, and DOM hierarchy to create the most specific selector possible. This approach:
- Works across different web apps without hardcoding
- Handles dynamic class names and complex DOM structures
- Provides exact click instructions based on DOM analysis

### Form Filling (Typing)

The system can fill out forms by typing text into input fields:

- ✅ **CSS Selectors**: `{"type": {"selector": "input[name='email']", "value": "test@example.com"}}`
- ✅ **XPath**: `{"type": {"xpath": "//input[@type='email']", "value": "test@example.com"}}`
- ✅ **Textarea Support**: `{"type": {"selector": "textarea#message", "value": "Hello world"}}`

OpenAI automatically:
- Identifies input fields (input, textarea) in forms
- Generates precise selectors using attributes (name, id, placeholder, type)
- Fills fields with appropriate test values (emails, names, messages, etc.)
- Handles multi-field forms by filling each field sequentially

## 📁 Project Structure

```
PythonSoftlight/
├── agent/
│   ├── planner.py      # LLM step planner (reactive)
│   ├── executor.py     # Browser automation executor
│   ├── capture.py      # Screenshot capture & state detection
│   └── browser.py      # DOM diffing utilities
├── tests/
│   ├── test_linear.py  # Linear contact sales test
│   └── test.py         # Simple test (no LLM)
├── dataset/            # Screenshots (gitignored)
├── config.py           # Configuration (API keys, model)
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🎬 Example Workflow

**Task**: "Open linear.app and contact their sales team"

1. **Step 1**: Navigate to `https://linear.app`
2. **Step 2**: LLM analyzes DOM, finds contact button → generates precise selector → clicks it
   - Example: `{"click": {"selector": "a[href='/contact']"}}` or `{"click": {"xpath": "//button[contains(@class, 'contact')]"}}`
3. **Step 3**: LLM analyzes contact form DOM → identifies input fields → fills each field
   - Example: `{"type": {"selector": "input[name='email']", "value": "test@example.com"}}`
   - Example: `{"type": {"selector": "input[name='name']", "value": "John Doe"}}`
   - Example: `{"type": {"selector": "textarea[name='message']", "value": "I'm interested in a demo"}}`
4. **Step 4**: LLM finds submit button in DOM → generates selector → clicks it
5. **Done**: Task complete, screenshots saved

Each step is planned reactively based on DOM analysis. OpenAI generates precise selectors that uniquely identify target elements.

## 🛠️ Troubleshooting

### OpenAI Rate Limit & Quota Errors

**⚠️ IMPORTANT: Rate limits ≠ Quota limits!**

**Rate Limits** (requests per minute):
- Free tier accounts: ~3 requests/minute (even with credits!)
- Paid plans: Much higher limits (e.g., 500 requests/minute)
- **Solution**: Wait 1-2 minutes and try again, or upgrade to a paid plan

**Quota Limits** (spending limit):
- If you see `insufficient_quota` errors:
  1. Check billing: https://platform.openai.com/account/billing
  2. Add payment method or credits
  3. System uses `gpt-4o-mini` by default (cheapest option)

**Why you might hit rate limits even with credits:**
- Free tier accounts have strict per-minute request limits
- Even if you have $5 credit, you're still limited to ~3 requests/minute
- The system automatically retries with exponential backoff (10s, 20s, 40s)
- Consider reducing `max_steps` to make fewer API calls

### Selector Not Found Errors

If you see "Selector 'X' not found or not clickable":
- The LLM generated a selector that doesn't match any element
- System will stop execution to prevent errors
- Check screenshots in `dataset/` to see what's actually on the page
- The DOM structure may have changed or the selector needs refinement

### Repeated Steps

The system automatically detects and prevents repeating the same step:
- Warns when a step is repeated
- Tries alternative approaches
- Stops if stuck in a loop (2+ consecutive repeats)

## 📝 Notes

- **Screenshots**: Saved to `dataset/{task_name}/` (gitignored) with sequential numbering (00.png, 01.png, ...)
- **Browser Mode**: Runs in visible mode by default (`headless=False`) - set `headless=True` for background execution
- **Step Limits**: Maximum steps default: 20 (configurable in `run_reactive()`)
- **Selector Validation**: System validates selectors exist and are visible before clicking/typing
- **DOM Analysis**: OpenAI analyzes DOM structure (first 2000 chars) to generate precise selectors
- **Selector Types**: Supports CSS selectors, XPath, and coordinates for maximum flexibility
- **Form Handling**: Automatically fills forms with appropriate test values (emails, names, messages)
- **Error Recovery**: Captures screenshots even on errors for debugging
- **Loop Prevention**: Automatically detects and prevents infinite loops from repeated steps

## 🔧 Development

### Adding Custom Actions

```python
from agent.executor import Executor

executor = Executor(task_name="test")

# Register custom action
def handle_scroll(page, params):
    page.evaluate(f"window.scrollTo(0, {params['pixels']})")

executor.register_action("scroll", handle_scroll)
```

### Extending the System

- **New action types**: Register handlers via `register_action()`
- **Better DOM analysis**: Enhance `browser.py` for smarter state detection
- **Improved prompts**: Update `SYSTEM_PROMPT` in `planner.py` for better LLM guidance on selector generation
- **Selector strategies**: Customize how OpenAI generates selectors by modifying the prompt in `planner.py`

## 📄 License

This is a take-home assignment project for Softlight.
