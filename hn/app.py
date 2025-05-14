import sys
import webbrowser
import time
from datetime import date, timedelta, datetime
from functools import partial

from textual.app import App, ComposeResult
from textual.containers import Grid, Center
from textual.widgets import DataTable, Footer, Header, LoadingIndicator, Static
from textual.binding import Binding
from textual.worker import get_current_worker
from rich.style import Style
from rich.text import Text
from rich.spinner import Spinner

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
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("j", "next_day", "Later Day"),
        Binding("k", "prev_day", "Earlier Day"),
        Binding("1", "show_top_10", "Top 10"),
        Binding("2", "show_top_20", "Top 20"),
        Binding("3", "show_top_half", "Top 50%"),
        Binding("4", "show_all", "Show All"),
        # Sorting bindings
        Binding("p", "sort_by_points", "Sort by Points"),
        Binding("c", "sort_by_comments", "Sort by Comments"),
        Binding("d", "sort_by_date", "Sort by Date"),
        # Story selection bindings
        Binding("enter", "open_comments", "Open Comments"),
        Binding("space", "open_story", "Open Story"),
    ]
    
    def __init__(self):
        super().__init__()
        # Set default date as 2 days ago since that's the latest available data
        self.current_date = date.today() - timedelta(days=2)
        self.filter_mode = "all"     # Default filter mode - show all stories
        self.sort_mode = "date"      # Default sort mode (points, comments, or date)
        self.stories = []
        self.api = HackerNewsAPI()
        
        # Cache of stories by date to avoid refetching
        self.story_cache = {}
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield DataTable()
        
        # Create a loading overlay with a spinner
        with Grid(id="loading"):
            with Center(id="spinner-container"):
                yield Static(Spinner("dots", text="Loading stories..."))
                
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        table = self.query_one(DataTable)
        table.add_columns("Title", "Points / Comments")
        table.cursor_type = "row"
        
        # Hide loading overlay initially
        loading = self.query_one("#loading")
        loading.display = False
        
        self.refresh_stories()
    
    def action_refresh(self) -> None:
        """Refresh the current stories."""
        # Remove from cache to force refresh
        date_str = self.current_date.strftime("%Y-%m-%d")
        if date_str in self.story_cache:
            del self.story_cache[date_str]
        self.refresh_stories()
    
    def action_next_day(self) -> None:
        """Go to the next day."""
        # Latest available data is 2 days ago
        latest_available = date.today() - timedelta(days=2)
        
        if self.current_date < latest_available:
            self.current_date += timedelta(days=1)
            # Refresh will automatically show loading only if needed
            self.refresh_stories()
        # If we're already at the latest date, do nothing
    
    def action_prev_day(self) -> None:
        """Go to the previous day."""
        self.current_date -= timedelta(days=1)
        # Refresh will automatically show loading only if needed
        self.refresh_stories()
    
    def action_show_top_10(self) -> None:
        self.filter_mode = "top_10"
        self.update_title()
        self.populate_table(refresh_data=False)
    
    def action_show_top_20(self) -> None:
        self.filter_mode = "top_20"
        self.update_title()
        self.populate_table(refresh_data=False)
    
    def action_show_top_half(self) -> None:
        self.filter_mode = "top_half"
        self.update_title()
        self.populate_table(refresh_data=False)
    
    def action_show_all(self) -> None:
        self.filter_mode = "all"
        self.update_title()
        self.populate_table(refresh_data=False)
    
    def action_sort_by_points(self) -> None:
        """Sort stories by points (high to low)."""
        self.sort_mode = "points"
        self.sort_stories()
        self.update_title()
        self.populate_table(refresh_data=False)
        
    def action_sort_by_comments(self) -> None:
        """Sort stories by comments (high to low)."""
        self.sort_mode = "comments"
        self.sort_stories()
        self.update_title()
        self.populate_table(refresh_data=False)
        
    def action_sort_by_date(self) -> None:
        """Sort stories by date (newest first)."""
        self.sort_mode = "date"
        self.sort_stories()
        self.update_title()
        self.populate_table(refresh_data=False)
    
    def sort_stories(self) -> None:
        """Sort stories based on the current sort mode."""
        if not self.stories:
            return
            
        if self.sort_mode == "points":
            self.stories.sort(key=lambda x: int(x.get("points") or 0), reverse=True)
        elif self.sort_mode == "comments":
            self.stories.sort(key=lambda x: int(x.get("comments") or 0), reverse=True)
        elif self.sort_mode == "date":
            self.stories.sort(key=lambda x: int(x.get("time") or 0), reverse=True)
    
    def refresh_stories(self) -> None:
        """Fetch and display stories for the current date."""
        # Check if we already have cached data for this date
        date_str = self.current_date.strftime("%Y-%m-%d")
        if date_str in self.story_cache:
            # Use cached data without loading animation
            self.stories = self.story_cache[date_str]
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
        date_str = self.current_date.strftime("%Y-%m-%d")
        
        # Fetch new data
        self.stories = self.api.get_stories(self.current_date)
        
        # Cache the result
        if self.stories:
            self.story_cache[date_str] = self.stories
            
        # Allow loading animation to show for at least a short time
        self.set_timer(0.3, self.finish_loading)
    
    def finish_loading(self) -> None:
        """Called when data loading is complete."""
        # Sort the fetched stories
        self.sort_stories()
            
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
            self.title = f"Hacker News - {date_str} - {status}"
        else:
            self.title = f"Hacker News - {date_str} - {filter_names[self.filter_mode]} - Sort: {sort_names[self.sort_mode]}"
    
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
            title = story.get("link_text", "No title")
            
            # Handle cases where points or comments might be None
            points = story.get("points")
            points = int(points) if points is not None else 0
            
            comments = story.get("comments")
            comments = int(comments) if comments is not None else 0
            
            points_comments = f"{points} / {comments}"
            
            # Get the style for this story
            style = self.get_story_style(story, filtered_stories)
            
            # When sorted by date, we'll handle time differently
            # We no longer show "1d ago" or "2d ago" in the title
            
            # Create styled Text objects for the cells
            title_text = Text(title, style=style)
            points_comments_text = Text(points_comments, style=style)
            
            # Add row with styled Text objects
            table.add_row(title_text, points_comments_text)
    
    def filter_stories(self) -> list:
        """Filter stories based on the current filter mode."""
        if not self.stories:
            return []
            
        if self.filter_mode == "top_10":
            return self.stories[:10]
        elif self.filter_mode == "top_20":
            return self.stories[:20]
        elif self.filter_mode == "top_half":
            half_count = len(self.stories) // 2
            return self.stories[:half_count]
        else:  # "all"
            return self.stories
    
    def format_time_ago(self, timestamp: int) -> str:
        """Format a Unix timestamp as a human-readable 'time ago' string."""
        try:
            now = int(time.time())
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
            
            # Color coding based on specs:
            # - top 10 of the day - green
            # - top 11-20 of the day - yellow
            # - the top 50% of the day (exclude the top 20) - blue
            # - the rest of the homepage stories - white
            # - the rest of the stories - grey
            
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
        except Exception as e:
            # In case of any error, default to white
            print(f"Error getting style: {e}")
            return Style(color="white")
    
    def action_open_comments(self) -> None:
        """Open the comments page for the currently selected story."""
        self.open_selected_item("comments")
    
    def action_open_story(self) -> None:
        """Open the story URL for the currently selected story."""
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
                    print(f"Opening comments URL: {comment_url}")
                    webbrowser.open(comment_url)
        except Exception as e:
            print(f"Error opening {target}: {e}")
    
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
                    print(f"Opening comments URL: {comment_url}")
                    webbrowser.open(comment_url)
        except Exception as e:
            print(f"Error handling row selection: {e}")

def main():
    app = HackerNewsApp()
    app.run()

if __name__ == "__main__":
    main()