"""
Hckrnews scraper module for fetching and parsing stories from hckrnews.com.
"""
import datetime
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

from .utils import get_pdt_now, get_pdt_today, format_date_for_url, format_date_for_cache_key
from .api import HckrnewsAPI

def fetch_stories(date_str: Optional[str] = None) -> str:
    """Fetch HTML from hckrnews.com for a given date."""
    if date_str is None:
        url = "https://hckrnews.com"
    else:
        url = f"https://hckrnews.com/{date_str}"

    headers = {"User-Agent": "HckrnewsClient/0.1"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def parse_stories(html: str) -> List[Dict[str, Any]]:
    """Parse HTML and extract story data with date separation."""
    soup = BeautifulSoup(html, 'html.parser')
    stories = []

    list_items = soup.select('li.row')
    from_today = True

    today = get_pdt_now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_timestamp = int(today.timestamp())

    for item in list_items:
        if 'day' in item.get('class', []):
            from_today = False
            continue

        if 'entry' not in item.get('class', []):
            continue

        if item.select_one('a.hn') and 'job' in item.select_one('a.hn').get('class', []):
            continue

        story_id = item.get('id')

        points_elem = item.select_one('span.points')
        comments_elem = item.select_one('span.comments')

        points_text = points_elem.text.strip() if points_elem else ""
        points = points_text if points_text.isdigit() else "0"

        comments_text = comments_elem.text.strip() if comments_elem else ""
        comments = comments_text if comments_text.isdigit() else "0"

        link_elem = item.select_one('a.link')
        link = link_elem.get('href') if link_elem else ""
        link_text = link_elem.text.strip() if link_elem else ""

        source_span = link_elem.select_one('span.source')
        if source_span:
            source_text = source_span.text
            link_text = link_text.replace(source_text, '').strip()

        hn_link = item.select_one('a.hn')
        timestamp_str = hn_link.get('data-date') if hn_link else "0"
        timestamp = int(timestamp_str) if timestamp_str.isdigit() else 0

        is_from_today_by_timestamp = timestamp >= today_timestamp if timestamp else False
        is_from_today = from_today and is_from_today_by_timestamp

        homepage = 'homepage' in points_elem.get('class', []) if points_elem else False

        story = {
            "id": story_id,
            "points": points,
            "comments": comments,
            "link": link,
            "link_text": link_text,
            "time": timestamp_str,
            "homepage": homepage,
            "from_today": is_from_today
        }

        stories.append(story)

    return stories

def update_stories(days: int = 2, start_day: int = 0) -> List[str]:
    """Update stories for the specified number of days."""
    updated_dates = []

    if start_day == 0 and days >= 2:
        today = get_pdt_today()
        yesterday = today - datetime.timedelta(days=1)

        today_cache_key = format_date_for_cache_key(today)
        yesterday_cache_key = format_date_for_cache_key(yesterday)

        try:
            html = fetch_stories(None)
            all_stories = parse_stories(html)

            today_stories = [story for story in all_stories if story.get("from_today")]
            yesterday_stories = [story for story in all_stories if not story.get("from_today")]

            for story in today_stories + yesterday_stories:
                if "from_today" in story:
                    del story["from_today"]

            if today_stories:
                HckrnewsAPI.cache_stories(today, today_stories)
                updated_dates.append(today_cache_key)

            if yesterday_stories:
                HckrnewsAPI.cache_stories(yesterday, yesterday_stories)
                updated_dates.append(yesterday_cache_key)

            for i in range(2, start_day + days):
                date = today - datetime.timedelta(days=i)
                date_str = format_date_for_url(date)
                cache_key = format_date_for_cache_key(date)

                try:
                    html = fetch_stories(date_str)
                    stories = parse_stories(html)

                    for story in stories:
                        if "from_today" in story:
                            del story["from_today"]

                    HckrnewsAPI.cache_stories(date, stories)
                    updated_dates.append(cache_key)
                except Exception:
                    pass

        except Exception:
            pass

    else:
        for i in range(start_day, start_day + days):
            date = get_pdt_today() - datetime.timedelta(days=i)

            date_str = format_date_for_url(date)
            cache_key = format_date_for_cache_key(date)

            try:
                html = fetch_stories(None if i == 0 else date_str)
                stories = parse_stories(html)

                if i == 0:
                    stories = [story for story in stories if story.get("from_today")]

                for story in stories:
                    if "from_today" in story:
                        del story["from_today"]

                HckrnewsAPI.cache_stories(date, stories)
                updated_dates.append(cache_key)
            except Exception:
                pass

    return updated_dates