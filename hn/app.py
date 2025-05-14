import sys
import webbrowser
import time
import pytz
from datetime import date, timedelta, datetime
from functools import partial

def get_pdt_now():
    """Get current time in PDT timezone."""
    return datetime.now(pytz.timezone('America/Los_Angeles'))

def get_pdt_today():
    """Get today's date in PDT timezone."""
    return get_pdt_now().date()

from textual.app import App, ComposeResult
from textual.containers import Grid, Center
from textual.widgets import DataTable, Footer, Header, LoadingIndicator, Static
from textual.binding import Binding, BindingType
from textual.worker import get_current_worker
from textual.keys import Keys
from rich.style import Style
from rich.text import Text
from rich.spinner import Spinner

from .scraper import update_stories

class HNFooter(Footer):
    """Custom footer that ensures the most important bindings are always visible"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_mount(self) -> None:
        """Customize which bindings to show."""
        super().on_mount()
        # Ensure these actions are always visible in the footer
        self.highlight_keys = {
            "open_story",
            "open_comments",
            "prev_day",
            "next_day",
            "refresh",
            "quit",
        }

from .api import HackerNewsAPI

class HackerNewsApp(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1;
        grid-rows: 1fr;
    }

    DataTable {
        height: 100%;
        width: 100%;
    }

    LoadingIndicator {
        width: 100%;
        height: 100%;
    }

    #loading {
        width: 100%;
        height: 100%;
        background: $background;
        content-align: center middle;
    }

    #spinner-container {
        content-align: center middle;
        height: 5;
        width: 30;
    }

    Footer {
        background: $panel;
    }
    """

    BINDINGS = [
        Binding("space", "open_story", "Story"),
        Binding("l", "open_comments", "Comments"),

        Binding("k", "next_day", "Later Day"),
        Binding("j", "prev_day", "Earlier Day"),
        Binding("r", "refresh", "Refresh"),

        Binding("1", "show_top_10", "Top 10"),
        Binding("2", "show_top_20", "Top 20"),
        Binding("3", "show_top_half", "Top 50%"),
        Binding("4", "show_all", "All"),

        Binding("p", "sort_by_points", "Sort: Points"),
        Binding("c", "sort_by_comments", "Sort: Comments"),
        Binding("d", "sort_by_date", "Sort: Date"),

        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        # Set default date to today in PDT timezone
        self.current_date = get_pdt_today()
        self.filter_mode = "all"     # Default filter mode - show all stories
        self.sort_mode = "date"      # Default sort mode (points, comments, or date)
        self.stories = []
        self.api = HackerNewsAPI()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield DataTable()

        with Grid(id="loading"):
            with Center(id="spinner-container"):
                yield Static(Spinner("dots", text="Fetching Hacker News stories..."))

        yield HNFooter()

    def on_mount(self) -> None:
        """Called when app is mounted."""
        table = self.query_one(DataTable)
        table.add_columns("Story Title", "Score / Comments")
        table.cursor_type = "row"

        loading = self.query_one("#loading")
        loading.display = False

        # Show loading animation immediately
        self.show_loading_animation()
        self.update_title("Updating stories cache...")
        
        # Schedule the initial data load for after the UI is mounted
        self.set_timer(0.1, self.initial_load)
    
    def initial_load(self) -> None:
        """Initial data load when the app starts."""
        # Update stories on app start (fetch and cache latest 2 days)
        try:
            updated_dates = update_stories(days=2)
            
            # Only after update is complete, refresh the display
            self.load_new_stories()
        except Exception:
            # Even if update fails, try to refresh from whatever might be in the cache
            self.refresh_stories()
            
        self.set_timer(0.5, self.ensure_table_focus)

    def action_refresh(self) -> None:
        """Refresh the current stories."""
        # Remove from cache to force refresh
        self.api.clear_cache_for_date(self.current_date)
            
        # If refreshing today or yesterday, update from the website
        today = get_pdt_today()
        yesterday = today - timedelta(days=1)
        
        if self.current_date == today or self.current_date == yesterday:
            self.show_loading_animation()
            self.update_title("Updating from hckrnews.com...")
            day_diff = (today - self.current_date).days
            try:
                # Update just this specific day
                update_stories(days=1, start_day=day_diff)
            except Exception:
                pass
                
        self.refresh_stories()

    def action_next_day(self) -> None:
        """Go to the next day."""
        # Latest available data is today in PDT timezone
        latest_available = get_pdt_today()

        if self.current_date < latest_available:
            self.current_date += timedelta(days=1)
            # Refresh will automatically show loading only if needed
            self.refresh_stories()
            # Ensure focus is on the data table after refresh
            self.set_timer(0.5, self.ensure_table_focus)
        # If we're already at the latest date, do nothing

    def action_prev_day(self) -> None:
        """Go to the previous day."""
        self.current_date -= timedelta(days=1)
        # Refresh will automatically show loading only if needed
        self.refresh_stories()
        # Ensure focus is on the data table after refresh
        self.set_timer(0.5, self.ensure_table_focus)

    def ensure_table_focus(self) -> None:
        """Ensure focus is on the data table and first row is selected."""
        table = self.query_one(DataTable)
        if len(table.rows) > 0:
            self.set_focus(table)
            if table.cursor_row is None:
                table.move_cursor(row=0, column=0)

    def action_show_top_10(self) -> None:
        self.filter_mode = "top_10"
        self.update_title()
        self.populate_table(refresh_data=False)
        self.ensure_table_focus()

    def action_show_top_20(self) -> None:
        self.filter_mode = "top_20"
        self.update_title()
        self.populate_table(refresh_data=False)
        self.ensure_table_focus()

    def action_show_top_half(self) -> None:
        self.filter_mode = "top_half"
        self.update_title()
        self.populate_table(refresh_data=False)
        self.ensure_table_focus()

    def action_show_all(self) -> None:
        self.filter_mode = "all"
        self.update_title()
        self.populate_table(refresh_data=False)
        self.ensure_table_focus()

    def action_sort_by_points(self) -> None:
        """Sort stories by points (high to low)."""
        self.sort_mode = "points"
        self.sort_stories()
        self.update_title()
        self.populate_table(refresh_data=False)
        self.ensure_table_focus()

    def action_sort_by_comments(self) -> None:
        """Sort stories by comments (high to low)."""
        self.sort_mode = "comments"
        self.sort_stories()
        self.update_title()
        self.populate_table(refresh_data=False)
        self.ensure_table_focus()

    def action_sort_by_date(self) -> None:
        """Sort stories by date (newest first)."""
        self.sort_mode = "date"
        self.sort_stories()
        self.update_title()
        self.populate_table(refresh_data=False)
        self.ensure_table_focus()

    def sort_stories(self) -> None:
        """Sort stories based on the current sort mode."""
        if not self.stories:
            return

        if self.sort_mode == "points":
            self.stories.sort(key=lambda x: self._get_int_value(x, "points"), reverse=True)
        elif self.sort_mode == "comments":
            self.stories.sort(key=lambda x: self._get_int_value(x, "comments"), reverse=True)
        elif self.sort_mode == "date":
            self.stories.sort(key=lambda x: self._get_int_value(x, "time"), reverse=True)
    
    def _get_int_value(self, story, key):
        """Helper to safely get integer values from story dictionary."""
        value = story.get(key)
        
        # Handle value based on its type
        if isinstance(value, int):
            return value
        elif isinstance(value, str) and value.isdigit():
            return int(value)
        else:
            return 0

    def refresh_stories(self) -> None:
        """Fetch and display stories for the current date."""
        # Format the date string for API and caching (YYYY-MM-DD for cache key)
        date_str = self.current_date.strftime("%Y-%m-%d")
        
        # Check if we already have cached data for this date
        cached_stories = self.api.get_cached_stories(self.current_date)
        if cached_stories:
            # Use cached data without loading animation
            self.stories = cached_stories
            self.sort_stories()
            self.update_title()
            self.populate_table(refresh_data=True)
        else:
            # Only show loading animation for non-cached data
            self.show_loading_animation()
            # Load after a small delay to ensure animation shows
            self.set_timer(0.05, self.load_new_stories)

    def show_loading_animation(self) -> None:
        """Show the loading animation and hide the table."""
        loading = self.query_one("#loading")
        table = self.query_one(DataTable)

        # Make sure the loading animation is visible and table is hidden
        loading.display = True
        table.display = False

        # Update title to show loading
        self.update_title("Loading...")

    def load_new_stories(self) -> None:
        """Load new (non-cached) stories for the current date."""
        # Fetch new data using the API (which automatically caches)
        self.stories = self.api.get_stories(self.current_date)
        
        # Sort the stories right away
        self.sort_stories()
        
        # Allow loading animation to show for at least a short time
        self.set_timer(0.3, self.finish_loading)

    def finish_loading(self) -> None:
        """Called when data loading is complete."""
        # Stories have already been sorted in load_new_stories
        # Update UI
        self.update_stories_complete()

    def update_stories_complete(self) -> None:
        """Called when stories have been fetched and processed."""
        # Hide loading animation and show table
        loading = self.query_one("#loading")
        table = self.query_one(DataTable)

        loading.display = False
        table.display = True

        # Update UI
        self.update_title()
        self.populate_table(refresh_data=True)

        # Ensure table has focus after populating
        self.set_timer(0.1, self.ensure_table_focus)

    def update_title(self, status: str = None) -> None:
        """Update the app title with current date, filter and sort mode."""
        date_str = self.current_date.strftime("%Y-%m-%d")

        filter_names = {
            "top_10": "Top 10",
            "top_20": "Top 20",
            "top_half": "Top 50%",
            "all": "All Stories"
        }

        sort_names = {
            "points": "Points",
            "comments": "Comments",
            "date": "Date"
        }

        if status:
            self.title = f"HN: {date_str} | {status}"
        else:
            self.title = f"HN: {date_str} | {filter_names[self.filter_mode]} | Sort: {sort_names[self.sort_mode]}"

    def populate_table(self, refresh_data: bool = True) -> None:
        """Populate the table with filtered stories.

        Args:
            refresh_data: If True, reload data; if False, just refilter/sort existing data
        """
        # Only clear and update the table if we have stories
        if not self.stories:
            if refresh_data:
                # First time loading, show the loading message
                table = self.query_one(DataTable)
                table.clear()
                table.add_row("No stories found", "")
            return

        # Clear the current table
        table = self.query_one(DataTable)
        table.clear()

        # Get the stories to display based on the current filter
        filtered_stories = self.filter_stories()
        if not filtered_stories:
            table.add_row("No stories found", "")
            return

        # Add each story to the table
        for story in filtered_stories:
            title = story.get("link_text")

            # Skip stories with undefined titles
            if not title:
                continue

            # Handle cases where points or comments might be None, empty string, or already an int
            points = story.get("points")
            if isinstance(points, int):
                points = points  # Already an int, keep as is
            elif points and (isinstance(points, str) and points.isdigit()):
                points = int(points)
            else:
                points = 0

            comments = story.get("comments")
            if isinstance(comments, int):
                comments = comments  # Already an int, keep as is
            elif comments and (isinstance(comments, str) and comments.isdigit()):
                comments = int(comments)
            else:
                comments = 0

            points_comments = f"{points} pts · {comments} comments"

            # Get the style for this story
            style = self.get_story_style(story, filtered_stories)

            # Create styled Text objects for the cells
            title_text = Text(title, style=style)
            points_comments_text = Text(points_comments, style=style)

            # Add row with styled Text objects
            table.add_row(title_text, points_comments_text)

    def filter_stories(self) -> list:
        """Filter stories based on the current filter mode using points regardless of sort mode."""
        if not self.stories:
            return []

        # Filter out stories with undefined titles
        valid_stories = [story for story in self.stories if story.get("link_text")]
        
        # Create a points-based ranking of stories
        # This ensures filtering by top N is always based on points
        points_sorted = sorted(
            valid_stories,
            key=lambda x: self._get_int_value(x, "points"),
            reverse=True
        )
        
        # Get the original indices of the points-sorted stories
        points_sorted_ids = [story.get("id") for story in points_sorted]
        
        if self.filter_mode == "top_10":
            # Get the IDs of the top 10 stories by points
            top_ids = set(story.get("id") for story in points_sorted[:10])
            # Filter the current sorted view to only include these stories
            return [story for story in self.stories if story.get("id") in top_ids]
        elif self.filter_mode == "top_20":
            # Get the IDs of the top 20 stories by points
            top_ids = set(story.get("id") for story in points_sorted[:20])
            # Filter the current sorted view to only include these stories
            return [story for story in self.stories if story.get("id") in top_ids]
        elif self.filter_mode == "top_half":
            # Get the IDs of the top half stories by points
            half_count = len(valid_stories) // 2
            top_ids = set(story.get("id") for story in points_sorted[:half_count])
            # Filter the current sorted view to only include these stories
            return [story for story in self.stories if story.get("id") in top_ids]
        else:  # "all"
            return valid_stories

    def format_time_ago(self, timestamp: int) -> str:
        """Format a Unix timestamp as a human-readable 'time ago' string."""
        try:
            # Use PDT timezone for 'now'
            now = int(get_pdt_now().timestamp())
            diff = now - timestamp

            if diff < 60:
                return "just now"
            elif diff < 3600:
                minutes = diff // 60
                return f"{minutes}m ago"
            elif diff < 86400:
                hours = diff // 3600
                return f"{hours}h ago"
            else:
                days = diff // 86400
                return f"{days}d ago"
        except Exception:
            return ""

    def get_story_style(self, story, filtered_stories) -> Style:
        """Get the appropriate style for a story based on its score ranking."""
        try:
            # Always use points-based ranking for color coding regardless of sort mode
            story_id = story.get("id")

            # Get a sorted list of stories by points for styling reference
            # regardless of current sort mode
            points_sorted = sorted(
                self.stories,
                key=lambda x: int(x.get("points") or 0),
                reverse=True
            )

            # Find the story by ID to avoid issues with dictionary comparison
            story_rank = -1
            for i, s in enumerate(points_sorted):
                if s.get("id") == story_id:
                    story_rank = i
                    break

            total_stories = len(self.stories)

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
            # In case of any error, default to white
            return Style(color="white")

    def action_open_comments(self) -> None:
        """Open the comments page for the currently selected story."""
        # If no row is selected, select the first row
        table = self.query_one(DataTable)
        if table.cursor_row is None and len(table.rows) > 0:
            table.move_cursor(row=0, column=0)
        self.open_selected_item("comments")

    def action_open_story(self) -> None:
        """Open the story URL for the currently selected story."""
        # If no row is selected, select the first row
        table = self.query_one(DataTable)
        if table.cursor_row is None and len(table.rows) > 0:
            table.move_cursor(row=0, column=0)
        self.open_selected_item("story")

    def open_selected_item(self, target: str) -> None:
        """Open either the story or comments for the selected row."""
        try:
            if not self.stories:
                return

            # Get the selected row index
            table = self.query_one(DataTable)
            if table.cursor_row is None:
                return

            # Get the story at the selected index
            filtered_stories = self.filter_stories()
            row_index = table.cursor_row
            if row_index >= len(filtered_stories):
                return

            story = filtered_stories[row_index]

            # Open the appropriate URL
            if target == "story":
                # Open story link in browser
                link = story.get("link")
                if link and link.strip():  # Make sure link is not empty
                    webbrowser.open(link)
            else:  # comments
                # Open comments page in browser
                story_id = story.get("id")
                if story_id:
                    # Directly construct the HN comments URL
                    story_id = str(story_id)
                    comment_url = f"https://news.ycombinator.com/item?id={story_id}"
                    webbrowser.open(comment_url)
        except Exception:
            pass

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection event."""
        try:
            if not self.stories:
                return

            filtered_stories = self.filter_stories()
            if event.row_index >= len(filtered_stories):
                return

            story = filtered_stories[event.row_index]

            # Determine if title or points/comments column was clicked
            if event.column_index == 0:  # Title column
                # Open story link in browser
                link = story.get("link")
                if link and link.strip():  # Make sure link is not empty
                    webbrowser.open(link)
            else:  # Points/Comments column
                # Open comments page in browser
                story_id = story.get("id")
                if story_id:
                    # Directly construct the HN comments URL
                    story_id = str(story_id)
                    comment_url = f"https://news.ycombinator.com/item?id={story_id}"
                    webbrowser.open(comment_url)
        except Exception:
            pass

    def on_data_table_key(self, event) -> None:
        """Handle keyboard events in the DataTable."""
        key = event.key

        if key == "l":
            self.action_open_comments()
            event.prevent_default()
            event.stop()
        elif key == "space":
            self.action_open_story()
            event.prevent_default()
            event.stop()

    def on_key(self, event) -> None:
        """Global key handler for the entire app."""
        if event.key == "l":
            self.action_open_comments()
            event.prevent_default()
            event.stop()
        elif event.key == Keys.Space:
            self.action_open_story()
            event.prevent_default()
            event.stop()

def main():
    app = HackerNewsApp()
    app.run()

if __name__ == "__main__":
    main()