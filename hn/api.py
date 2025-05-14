import datetime
import json
import requests
from typing import Dict, List, Optional, Any, Tuple

class HackerNewsAPI:
    BASE_URL = "https://hckrnews.com/data/{}.js"
    # In-memory cache for stories
    _story_cache = {}
    
    @classmethod
    def get_stories(cls, date: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
        """Fetch stories from HackerNews API for a specific date."""
        if date is None:
            date = datetime.date.today()
            
        date_str = date.strftime("%Y%m%d")
        cache_key = date.strftime("%Y-%m-%d")
        
        # First check if we have data in our in-memory cache
        if cache_key in cls._story_cache:
            print(f"Loaded {len(cls._story_cache[cache_key])} stories from memory cache for {date_str}")
            return cls._story_cache[cache_key]
        
        # Otherwise fetch from API
        url = cls.BASE_URL.format(date_str)
        print(f"Fetching from API: {url}")
        
        try:
            headers = {"User-Agent": "HackerNewsClient/1.0"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = json.loads(response.text)
            
            if not isinstance(data, list):
                print(f"API returned unexpected data format: {type(data)}")
                return []
            
            # Store in memory cache
            cls._story_cache[cache_key] = data
            return data
            
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            return []
        except requests.exceptions.ConnectionError as e:
            print(f"Connection Error: {e}")
            return []
        except requests.exceptions.Timeout as e:
            print(f"Timeout Error: {e}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching data: {e}")
            return []
    
    @classmethod
    def cache_stories(cls, date: datetime.date, stories: List[Dict[str, Any]]) -> None:
        """Cache stories for a specific date."""
        cache_key = date.strftime("%Y-%m-%d")
        cls._story_cache[cache_key] = stories
        
    @classmethod
    def get_cached_stories(cls, date: datetime.date) -> Optional[List[Dict[str, Any]]]:
        """Get stories from cache if they exist."""
        cache_key = date.strftime("%Y-%m-%d")
        return cls._story_cache.get(cache_key)
    
    @classmethod
    def clear_cache_for_date(cls, date: datetime.date) -> bool:
        """Clear cache for a specific date."""
        cache_key = date.strftime("%Y-%m-%d")
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
