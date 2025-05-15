import datetime
import json
import requests
from typing import Dict, List, Optional, Any

from .utils import get_pdt_today, format_date_for_url, format_date_for_cache_key

class HckrnewsAPI:
    BASE_URL = "https://hckrnews.com/data/{}.js"
    _story_cache = {}

    @classmethod
    def get_stories(cls, date: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
        """Fetch stories from Hckrnews API for a specific date."""
        if date is None:
            date = get_pdt_today()

        date_str = format_date_for_url(date)
        cache_key = format_date_for_cache_key(date)

        if cache_key in cls._story_cache:
            return cls._story_cache[cache_key]

        url = cls.BASE_URL.format(date_str)

        try:
            headers = {"User-Agent": "HckrnewsClient/0.1"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = json.loads(response.text)

            if not isinstance(data, list):
                return []

            cls._story_cache[cache_key] = data
            return data

        except (requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException,
                json.JSONDecodeError,
                Exception):
            return []

    @classmethod
    def cache_stories(cls, date: datetime.date, stories: List[Dict[str, Any]]) -> None:
        """Cache stories for a specific date."""
        cache_key = format_date_for_cache_key(date)
        cls._story_cache[cache_key] = stories

    @classmethod
    def get_cached_stories(cls, date: datetime.date) -> Optional[List[Dict[str, Any]]]:
        """Get stories from cache if they exist."""
        cache_key = format_date_for_cache_key(date)
        return cls._story_cache.get(cache_key)

    @classmethod
    def clear_cache_for_date(cls, date: datetime.date) -> bool:
        """Clear cache for a specific date."""
        cache_key = format_date_for_cache_key(date)
        if cache_key in cls._story_cache:
            del cls._story_cache[cache_key]
            return True
        return False

    @classmethod
    def clear_all_cache(cls) -> None:
        """Clear all cached stories."""
        cls._story_cache.clear()

    @staticmethod
    def get_comment_url(story_id: str) -> str:
        """Generate the URL for the comments page of a story."""
        return f"https://news.ycombinator.com/item?id={story_id}"