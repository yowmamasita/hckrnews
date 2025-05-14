# HN - Hacker News CLI Viewer

A command line tool to display the top stories from Hacker News using the API provided by hckrnews.com.

## Features

- View top stories from Hacker News in your terminal
- Color-coded titles based on story score
- 2-column layout showing titles and points/comments
- Various filtering options (top 10, top 20, etc.)
- Navigation between different days
- Keyboard shortcuts for all actions

## Installation

Clone this repository and install with pip:

```bash
cd hn
pip install -e .
```

Or if you're using uv:

```bash
cd hn
uv pip install -e .
```

## Usage

Simply run the `hn` command to start the application:

```bash
hn
```

### Keyboard Shortcuts

- `q` - Quit the application
- `r` - Refresh current view
- `j` - Jump to next day
- `k` - Jump to previous day
- `1` - Show top 10 stories (default)
- `2` - Show top 20 stories
- `3` - Show top 50% stories
- `4` - Show homepage stories only
- `5` - Show all stories

### Interaction

- Select a story title (first column) to open the story URL in your browser
- Select the points/comments cell (second column) to open the comments page for that story

## Data Source

Data is fetched from the hckrnews.com API:
`https://hckrnews.com/data/YYYYMMDD.js`