"""
UI utilities for the Hacker News application.
"""
from typing import Dict, Any, List, Callable
from rich.text import Text
from rich.style import Style
from rich.spinner import Spinner
from textual.widgets import DataTable

def prepare_loading_ui(table: DataTable, message: str = "Fetching Hacker News stories...") -> None:
    """Show loading message in DataTable."""
    table.clear()
    
    # Create a simple text message instead of using a spinner 
    # (spinners require a console which we don't have direct access to here)
    loading_text = Text(f"Loading... {message}", style="bold green")
    
    table.add_row(loading_text, "")

def get_story_style(story: Dict[str, Any], all_stories: List[Dict[str, Any]]) -> Style:
    """Get the appropriate style for a story based on its score ranking."""
    try:
        story_id = story.get("id")
        points_sorted = sorted(
            all_stories,
            key=lambda x: int(x.get("points") or 0),
            reverse=True
        )

        story_rank = -1
        for i, s in enumerate(points_sorted):
            if s.get("id") == story_id:
                story_rank = i
                break

        total_stories = len(all_stories)

        if story_rank < 10 and story_rank >= 0:
            return Style(color="bright_green")
        elif story_rank < 20:
            return Style(color="bright_yellow")
        elif story_rank < total_stories // 2:
            return Style(color="bright_blue")
        elif story.get("homepage", False):
            return Style(color="white")
        else:
            return Style(color="bright_black")
    except Exception:
        return Style(color="white")

def filter_stories(stories: List[Dict[str, Any]], filter_mode: str, 
                  value_getter: Callable[[Dict[str, Any], str], int]) -> List[Dict[str, Any]]:
    """Filter stories based on the current filter mode."""
    if not stories:
        return []

    valid_stories = [story for story in stories if story.get("link_text")]
    
    points_sorted = sorted(
        valid_stories,
        key=lambda x: value_getter(x, "points"),
        reverse=True
    )
    
    if filter_mode == "top_10":
        top_ids = set(story.get("id") for story in points_sorted[:10])
        return [story for story in stories if story.get("id") in top_ids]
    elif filter_mode == "top_20":
        top_ids = set(story.get("id") for story in points_sorted[:20])
        return [story for story in stories if story.get("id") in top_ids]
    elif filter_mode == "top_half":
        half_count = len(valid_stories) // 2
        top_ids = set(story.get("id") for story in points_sorted[:half_count])
        return [story for story in stories if story.get("id") in top_ids]
    else:  # "all"
        return valid_stories