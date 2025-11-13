"""
UI state detection and screenshot capture.

This module handles capturing screenshots of UI states, including states that
don't have URLs (like modals, dropdowns, overlays). It uses DOM diffing to
detect when the UI state has changed.
"""

import os
import time
from agent.browser import dom_changed

def capture_state(page, task_name, step_index):
    """
    Capture a screenshot of the current page state.
    
    Screenshots are saved to dataset/{task_name}/ with sequential numbering.
    This allows tracking the UI state progression through the workflow.
    
    Args:
        page: Playwright page object
        task_name: Name of the task (used for folder naming)
        step_index: Step number (used for file naming, e.g., 01.png, 02.png)
    """
    # Create folder for this task's screenshots
    folder = f"dataset/{task_name}"
    os.makedirs(folder, exist_ok=True)

    # Save screenshot with zero-padded step number
    path = f"{folder}/{step_index:02d}.png"
    page.screenshot(path=path)
    print(f"[STATE] Saved screenshot → {path}")

def detect_and_capture(page, task_name, step_index, dom_before, always_capture=False):
    """
    Detect DOM changes and capture screenshot if state changed.
    
    This function compares the DOM before and after an action to determine
    if the UI state has changed. This is crucial for capturing modals and
    other UI states that don't have unique URLs.
    
    Args:
        page: Playwright page object
        task_name: Name of the task (for folder naming)
        step_index: Step number (for file naming)
        dom_before: DOM content before the action
        always_capture: If True, always capture regardless of DOM changes.
                       This ensures we don't miss subtle UI changes.
    
    Note:
        The always_capture flag is set to True by the executor to ensure
        we capture all UI states, even if DOM diffing misses subtle changes.
    """
    # Get DOM after the action
    dom_after = page.content()
    
    # Always capture if requested, or if DOM changed significantly
    # This handles both explicit capture requests and automatic change detection
    if always_capture or dom_changed(dom_before, dom_after):
        capture_state(page, task_name, step_index)

