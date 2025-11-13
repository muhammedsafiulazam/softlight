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
- **Text-Based Element Selection**: Uses visible button/link text instead of brittle CSS selectors
- **UI State Detection**: Captures screenshots even for modals/overlays without URL changes
- **Generalizable**: Handles any task, any web app - no hardcoding required
- **Error Handling**: Detects repeated steps, validates text existence, handles failures gracefully

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
- **`agent/executor.py`**: Browser automation executor with dynamic action registry
- **`agent/capture.py`**: UI state detection and screenshot capture
- **`agent/browser.py`**: DOM diffing utilities for detecting UI changes

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

## 🔄 How It Works

### Step-by-Step Reactive Planning

Unlike traditional automation that plans all steps upfront, this system:

1. **Observes** current UI state (DOM content)
2. **Plans** next single action using LLM
3. **Executes** the action
4. **Captures** screenshot of new state
5. **Repeats** until task complete

This reactive approach:
- Adapts to dynamic UIs
- Handles unexpected page structures
- Works without knowing the workflow ahead of time

### Text-Based Selection

The system prefers clicking elements by their visible text:
- ✅ `{"click": {"text": "Contact Sales"}}` - Uses actual button text
- ❌ `{"click": {"selector": "button.complex-css"}}` - Avoids brittle CSS

This makes it more reliable across different web apps.

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
2. **Step 2**: LLM sees page, finds "Contact" button → clicks it
3. **Step 3**: LLM sees contact page, finds form → fills it out
4. **Step 4**: LLM sees submit button → clicks it
5. **Done**: Task complete, screenshots saved

Each step is planned reactively based on what the LLM sees in the current UI state.

## 🛠️ Troubleshooting

### OpenAI Quota Errors

If you see `insufficient_quota` errors:
1. Check billing: https://platform.openai.com/account/billing
2. Add payment method or credits
3. System uses `gpt-4o-mini` by default (cheapest option)

### Text Not Found Errors

If you see "Text 'X' not found on page":
- The LLM suggested text that doesn't exist
- System will automatically try alternative approaches
- Check screenshots in `dataset/` to see what's actually on the page

### Repeated Steps

The system automatically detects and prevents repeating the same step:
- Warns when a step is repeated
- Tries alternative approaches
- Stops if stuck in a loop (2+ consecutive repeats)

## 📝 Notes

- Screenshots are saved to `dataset/{task_name}/` (gitignored)
- Browser runs in visible mode by default (`headless=False`)
- Maximum steps default: 20 (configurable in `run_reactive()`)
- System validates text exists before clicking (prevents hallucinated text)

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
- **Improved prompts**: Update `SYSTEM_PROMPT` in `planner.py` for better LLM guidance

## 📄 License

This is a take-home assignment project for Softlight.
