"""
HackerNews scraper module for fetching and parsing stories from hckrnews.com.
"""
import datetime
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import pytz
from .api import HackerNewsAPI

def get_pdt_now():
    """Get current time in PDT timezone."""
    return datetime.datetime.now(pytz.timezone('America/Los_Angeles'))

def get_pdt_today():
    """Get today's date in PDT timezone."""
    return get_pdt_now().date()

def fetch_stories(date_str: Optional[str] = None) -> str:
    """Fetch HTML from hckrnews.com for a given date."""
    if date_str is None:
        # Today's date
        url = "https://hckrnews.com"
    else:
        # Specific date
        url = f"https://hckrnews.com/{date_str}"
    
    headers = {"User-Agent": "HackerNewsClient/1.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def parse_stories(html: str) -> List[Dict[str, Any]]:
    """Parse HTML and extract story data with date separation.
    
    This function parses the HTML from hckrnews.com and extracts story data,
    and determines the date of each story based on its timestamp.
    
    For separating stories by date, we use two approaches:
    1. We detect day separators in the HTML (<li class="row day">) to segment stories
    2. We also use the timestamp in data-date attribute to determine exact publication date
    """
    soup = BeautifulSoup(html, 'html.parser')
    stories = []
    
    # Find all list items (both stories and day separators)
    list_items = soup.select('li.row')
    
    # Flag to track if we're processing stories from today or yesterday based on separators
    from_today = True
    
    # Get today's date at midnight in PDT for timestamp comparison
    today = get_pdt_now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_timestamp = int(today.timestamp())
    
    for item in list_items:
        # Check if this is a day separator
        if 'day' in item.get('class', []):
            # Found a day separator, all stories after this are from previous days
            from_today = False
            continue
        
        # Skip if not an entry (story)
        if 'entry' not in item.get('class', []):
            continue
            
        # Skip job listings
        if item.select_one('a.hn') and 'job' in item.select_one('a.hn').get('class', []):
            continue
        
        story_id = item.get('id')
        
        # Get points and comments
        points_elem = item.select_one('span.points')
        comments_elem = item.select_one('span.comments')
        
        # Extract points and comments, ensuring we have valid integers
        points_text = points_elem.text.strip() if points_elem else ""
        points = points_text if points_text.isdigit() else "0"
        
        comments_text = comments_elem.text.strip() if comments_elem else ""
        comments = comments_text if comments_text.isdigit() else "0"
        
        # Get story link and title
        link_elem = item.select_one('a.link')
        link = link_elem.get('href') if link_elem else ""
        link_text = link_elem.text.strip() if link_elem else ""
        
        # Clean up the title text (remove source domain at the end)
        source_span = link_elem.select_one('span.source')
        if source_span:
            source_text = source_span.text
            link_text = link_text.replace(source_text, '').strip()
        
        # Get timestamp from the data-date attribute
        hn_link = item.select_one('a.hn')
        timestamp_str = hn_link.get('data-date') if hn_link else "0"
        timestamp = int(timestamp_str) if timestamp_str.isdigit() else 0
        
        # Determine if the story is from today based on its timestamp
        is_from_today_by_timestamp = timestamp >= today_timestamp if timestamp else False
        
        # Combine both methods: use the day separator as a hint, but also check timestamp
        # If either method says it's not from today, consider it from yesterday
        is_from_today = from_today and is_from_today_by_timestamp
        
        # Check if it's a homepage story (has 'homepage' class)
        homepage = 'homepage' in points_elem.get('class', []) if points_elem else False
        
        story = {
            "id": story_id,
            "points": points,
            "comments": comments,
            "link": link,
            "link_text": link_text,
            "time": timestamp_str,
            "homepage": homepage,
            "from_today": is_from_today  # Add a flag to indicate if the story is from today
        }
        
        stories.append(story)
    
    return stories

def update_stories(days: int = 2, start_day: int = 0) -> List[str]:
    """Update stories for the specified number of days.
    
    Args:
        days: Number of days to update (starting from today and going backwards)
        start_day: Day offset to start from (0 = today, 1 = yesterday, etc.)
        
    Returns:
        List of date strings that were updated in the in-memory cache
    """
    updated_dates = []
    
    # If we're updating today and yesterday in one go, we can optimize by fetching once
    if start_day == 0 and days >= 2:
        today = get_pdt_today()
        yesterday = today - datetime.timedelta(days=1)
        
        # Format dates for cache keys
        today_cache_key = today.strftime("%Y-%m-%d")
        yesterday_cache_key = yesterday.strftime("%Y-%m-%d")
        
        try:
            # Fetch homepage which contains both today's and yesterday's stories
            html = fetch_stories(None)
            all_stories = parse_stories(html)
            
            # Separate stories by day using the from_today flag
            # This flag is now set based on both day separators and timestamps
            today_stories = [story for story in all_stories if story.get("from_today")]
            yesterday_stories = [story for story in all_stories if not story.get("from_today")]
            
            # Remove the temporary from_today field before caching
            for story in today_stories + yesterday_stories:
                if "from_today" in story:
                    del story["from_today"]
            
            # Store in API's in-memory cache
            if today_stories:
                HackerNewsAPI.cache_stories(today, today_stories)
                updated_dates.append(today_cache_key)
            
            if yesterday_stories:
                HackerNewsAPI.cache_stories(yesterday, yesterday_stories)
                updated_dates.append(yesterday_cache_key)
            
            # If we need more days, handle them individually
            for i in range(2, start_day + days):
                date = today - datetime.timedelta(days=i)
                date_str = date.strftime("%Y%m%d")
                cache_key = date.strftime("%Y-%m-%d")
                
                try:
                    # Fetch specific date
                    html = fetch_stories(date_str)
                    stories = parse_stories(html)
                    
                    # Remove the temporary from_today field before caching
                    for story in stories:
                        if "from_today" in story:
                            del story["from_today"]
                    
                    # Store in API's in-memory cache
                    HackerNewsAPI.cache_stories(date, stories)
                    updated_dates.append(cache_key)
                except Exception:
                    pass
        
        except Exception:
            pass
    
    else:
        # Handle individual days as before
        for i in range(start_day, start_day + days):
            date = get_pdt_today() - datetime.timedelta(days=i)
            
            # Format for URL path needs to be YYYYMMDD
            date_str = date.strftime("%Y%m%d")
            cache_key = date.strftime("%Y-%m-%d")
            
            try:
                # For yesterday (i=1), we need to use the date in URL
                # For today (i=0), we use the homepage URL without date
                html = fetch_stories(None if i == 0 else date_str)
                stories = parse_stories(html)
                
                # For homepage (today), filter out yesterday's stories if present
                if i == 0:
                    stories = [story for story in stories if story.get("from_today")]
                
                # Remove the temporary from_today field before caching
                for story in stories:
                    if "from_today" in story:
                        del story["from_today"]
                
                # Store in API's in-memory cache
                HackerNewsAPI.cache_stories(date, stories)
                updated_dates.append(cache_key)
            except Exception:
                pass
    
    return updated_dates