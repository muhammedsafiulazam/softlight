"""
DOM diffing utilities for detecting UI state changes.

This module handles comparing DOM states to detect when the UI has changed.
This is essential for capturing modals, dropdowns, and other UI states that
don't have unique URLs - a key requirement of the assignment.
"""

from bs4 import BeautifulSoup

def clean_dom(html: str):
    """
    Clean and normalize HTML for comparison.
    
    Removes dynamic content that changes frequently but doesn't represent
    actual UI state changes (scripts, styles, dynamic IDs, etc.).
    This makes DOM comparison more reliable for detecting meaningful UI changes.
    
    Args:
        html: Raw HTML string from the page
    
    Returns:
        Cleaned and normalized HTML string
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove dynamic script/style/meta tags that don't affect visible UI
    for tag in soup(["script", "style", "meta", "noscript"]):
        tag.decompose()

    # Remove attributes that change frequently (ids, data attributes, etc.)
    # These change on every page load but don't represent UI state changes
    for tag in soup.find_all(True):
        # Keep only essential attributes for UI state detection
        # These attributes actually affect what the user sees
        attrs_to_keep = ['class', 'type', 'role', 'aria-label']
        attrs_to_remove = [attr for attr in tag.attrs.keys() if attr not in attrs_to_keep]
        for attr in attrs_to_remove:
            del tag[attr]

    return soup.prettify()

def dom_changed(before_html: str, after_html: str, threshold=0.05):
    """
    Compare two HTML strings and determine if they represent different UI states.
    
    This function is crucial for the assignment requirement: capturing UI states
    that don't have URLs (like modals). By comparing DOM before/after actions,
    we can detect when a modal appears, even though the URL hasn't changed.
    
    Uses normalized string comparison with a similarity threshold to handle
    minor DOM fluctuations that don't represent actual UI state changes.
    
    Args:
        before_html: HTML before action
        after_html: HTML after action
        threshold: Minimum difference ratio to consider as changed (0.05 = 5% difference)
                   This filters out minor DOM fluctuations
    
    Returns:
        True if DOM changed significantly (indicating a UI state change), False otherwise
    
    Example:
        # Modal appears - URL doesn't change, but DOM does
        dom_changed(page_before_click, page_after_click)  # Returns True
    """
    # Clean both HTML strings for fair comparison
    before = clean_dom(before_html)
    after = clean_dom(after_html)
    
    # If strings are identical, no change
    if before == after:
        return False
    
    # Calculate similarity using sequence matching
    # This compares the structure and content of the cleaned HTML
    max_len = max(len(before), len(after))
    if max_len == 0:
        return False
    
    # Use SequenceMatcher to calculate similarity ratio
    # This is more robust than simple string comparison
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, before, after).ratio()
    difference_ratio = 1 - similarity
    
    # Return True if difference exceeds threshold
    # This means the UI state has meaningfully changed
    return difference_ratio > threshold

