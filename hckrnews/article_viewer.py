from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, ScrollView
from textual.binding import Binding

class ArticleScreen(Screen):
    """Screen to display an article fetched from the web."""

    BINDINGS = [Binding("escape", "pop_screen", "Back")]

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url
        self._text_widget = Static("Loading article...", id="article-text")

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollView(self._text_widget, id="article-view")
        yield Footer()

    def on_mount(self) -> None:
        self.set_timer(0.1, self.load_article)

    def load_article(self) -> None:
        """Fetch and display the article from the URL."""
        try:
            from newspaper import Article

            article = Article(self.url)
            article.download()
            article.parse()
            text = article.text.strip()
            if not text:
                text = "Unable to extract article."
            self._text_widget.update(text)
        except Exception:
            self._text_widget.update("Error loading article.")
