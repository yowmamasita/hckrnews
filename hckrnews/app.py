import webbrowser
from datetime import timedelta

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header
from textual.binding import Binding
from textual.keys import Keys
from rich.text import Text

from .utils import get_pdt_today, get_int_value
from .ui_utils import prepare_loading_ui, get_story_style, filter_stories
from .scraper import update_stories
from .api import HckrnewsAPI

class HNFooter(Footer):
    """Custom footer that ensures the most important bindings are always visible"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_mount(self) -> None:
        """Customize which bindings to show."""
        super().on_mount()
        self.highlight_keys = {
            "open_story",
            "open_comments",
            "prev_day",
            "next_day",
            "refresh",
            "quit",
        }

class HckrnewsApp(App):
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

    Footer {
        background: $panel;
    }
    """

    BINDINGS = [

        Binding("j", "prev_day", "Earlier Day"),
        Binding("k", "next_day", "Later Day"),

        Binding("l", "open_comments", "Comments"),
        Binding("space", "open_story", "Story"),

        Binding("1", "show_top_10", "Top 10"),
        Binding("2", "show_top_20", "Top 20"),
        Binding("3", "show_top_half", "Top 50%"),
        Binding("4", "show_all", "All"),

        Binding("p", "sort_by_points", "Sort: Points"),
        Binding("c", "sort_by_comments", "Sort: Comments"),
        Binding("d", "sort_by_date", "Sort: Date"),

        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.current_date = get_pdt_today()
        self.filter_mode = "all"
        self.sort_mode = "date"
        self.stories = []
        self.api = HckrnewsAPI()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield DataTable()
        yield HNFooter()

    def on_mount(self) -> None:
        """Called when app is mounted."""
        table = self.query_one(DataTable)
        table.add_columns("Story Title", "Score / Comments")
        table.cursor_type = "row"

        self.update_title("Updating stories cache...")
        self.set_timer(0.1, self.initial_load)

    def initial_load(self) -> None:
        """Initial data load when the app starts."""
        try:
            table = self.query_one(DataTable)
            prepare_loading_ui(table)
            self.set_timer(0.1, self.perform_initial_load)
        except Exception:
            self.refresh_stories()

        self.set_timer(0.5, self.ensure_table_focus)

    def perform_initial_load(self) -> None:
        """Perform the actual initial data loading."""
        try:
            update_stories(days=2)
            self.stories = self.api.get_stories(self.current_date)
            self.sort_stories()
            self.update_title()
            self.populate_table(refresh_data=True)
        except Exception:
            self.refresh_stories()

    def action_refresh(self) -> None:
        """Refresh the current stories."""
        self.api.clear_cache_for_date(self.current_date)
        table = self.query_one(DataTable)
        prepare_loading_ui(table)
        self.update_title("Refreshing...")
        self.set_timer(0.1, self.perform_refresh)

    def perform_refresh(self) -> None:
        """Perform the actual refresh of stories."""
        try:
            today = get_pdt_today()
            yesterday = today - timedelta(days=1)

            if self.current_date == today or self.current_date == yesterday:
                day_diff = (today - self.current_date).days
                try:
                    update_stories(days=1, start_day=day_diff)
                except Exception:
                    pass

            self.stories = self.api.get_stories(self.current_date)
            self.sort_stories()
            self.update_title()
            self.populate_table(refresh_data=True)
        except Exception:
            table = self.query_one(DataTable)
            table.clear()
            table.add_row("Error refreshing stories", "")

    def action_next_day(self) -> None:
        """Go to the next day."""
        latest_available = get_pdt_today()

        if self.current_date < latest_available:
            self.current_date += timedelta(days=1)
            self.refresh_stories()
            self.set_timer(0.5, self.ensure_table_focus)

    def action_prev_day(self) -> None:
        """Go to the previous day."""
        self.current_date -= timedelta(days=1)
        self.refresh_stories()
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
            self.stories.sort(key=lambda x: get_int_value(x, "points"), reverse=True)
        elif self.sort_mode == "comments":
            self.stories.sort(key=lambda x: get_int_value(x, "comments"), reverse=True)
        elif self.sort_mode == "date":
            self.stories.sort(key=lambda x: get_int_value(x, "time"), reverse=True)

    def refresh_stories(self) -> None:
        """Fetch and display stories for the current date."""
        table = self.query_one(DataTable)

        cached_stories = self.api.get_cached_stories(self.current_date)
        if cached_stories:
            self.stories = cached_stories
            self.sort_stories()
            self.update_title()
            self.populate_table(refresh_data=True)
        else:
            prepare_loading_ui(table)
            self.set_timer(0.1, self.perform_load_new_stories)

    def perform_load_new_stories(self) -> None:
        """Perform the actual loading of new stories."""
        try:
            self.stories = self.api.get_stories(self.current_date)
            self.sort_stories()
            self.update_title()
            self.populate_table(refresh_data=True)
        except Exception:
            table = self.query_one(DataTable)
            table.clear()
            table.add_row("Error loading stories", "")

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
            self.title = f"hckrnews: {date_str} | {status}"
        else:
            self.title = f"hckrnews: {date_str} | {filter_names[self.filter_mode]} | Sort: {sort_names[self.sort_mode]}"

    def populate_table(self, refresh_data: bool = True) -> None:
        """Populate the table with filtered stories."""
        if not self.stories:
            if refresh_data:
                table = self.query_one(DataTable)
                table.clear()
                table.add_row("No stories found", "")
            return

        table = self.query_one(DataTable)
        table.clear()

        filtered_stories = filter_stories(self.stories, self.filter_mode, get_int_value)
        if not filtered_stories:
            table.add_row("No stories found", "")
            return

        for story in filtered_stories:
            title = story.get("link_text")

            if not title:
                continue

            points = get_int_value(story, "points")
            comments = get_int_value(story, "comments")

            points_comments = f"{points} pts · {comments} comments"
            style = get_story_style(story, self.stories)

            title_text = Text(title, style=style)
            points_comments_text = Text(points_comments, style=style)

            table.add_row(title_text, points_comments_text)

    def action_open_comments(self) -> None:
        """Open the comments page for the currently selected story."""
        table = self.query_one(DataTable)
        if table.cursor_row is None and len(table.rows) > 0:
            table.move_cursor(row=0, column=0)
        self.open_selected_item("comments")

    def action_open_story(self) -> None:
        """Open the story URL for the currently selected story."""
        table = self.query_one(DataTable)
        if table.cursor_row is None and len(table.rows) > 0:
            table.move_cursor(row=0, column=0)
        self.open_selected_item("story")

    def open_selected_item(self, target: str) -> None:
        """Open either the story or comments for the selected row."""
        try:
            if not self.stories:
                return

            table = self.query_one(DataTable)
            if table.cursor_row is None:
                return

            filtered_stories = filter_stories(self.stories, self.filter_mode, get_int_value)
            row_index = table.cursor_row
            if row_index >= len(filtered_stories):
                return

            story = filtered_stories[row_index]

            if target == "story":
                link = story.get("link")
                if link and link.strip():
                    webbrowser.open(link)
            else:
                story_id = story.get("id")
                if story_id:
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

            filtered_stories = filter_stories(self.stories, self.filter_mode, get_int_value)
            if event.row_index >= len(filtered_stories):
                return

            story = filtered_stories[event.row_index]

            if event.column_index == 0:
                link = story.get("link")
                if link and link.strip():
                    webbrowser.open(link)
            else:
                story_id = story.get("id")
                if story_id:
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
    app = HckrnewsApp()
    app.run()

if __name__ == "__main__":
    main()