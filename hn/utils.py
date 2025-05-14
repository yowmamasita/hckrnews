"""
Utility functions shared across the HN application.
"""
import datetime
import pytz
from typing import Dict, Any, Union

def get_pdt_now() -> datetime.datetime:
    """Get current time in PDT timezone."""
    return datetime.datetime.now(pytz.timezone('America/Los_Angeles'))

def get_pdt_today() -> datetime.date:
    """Get today's date in PDT timezone."""
    return get_pdt_now().date()

def format_date_for_url(date: datetime.date) -> str:
    """Format date as YYYYMMDD for API URL."""
    return date.strftime("%Y%m%d")

def format_date_for_cache_key(date: datetime.date) -> str:
    """Format date as YYYY-MM-DD for cache key."""
    return date.strftime("%Y-%m-%d")

def get_int_value(story: Dict[str, Any], key: str, default: int = 0) -> int:
    """Helper to safely get integer values from story dictionary."""
    value = story.get(key)
    
    if isinstance(value, int):
        return value
    elif isinstance(value, str) and value.isdigit():
        return int(value)
    else:
        return default

def format_time_ago(timestamp: Union[int, str]) -> str:
    """Format a Unix timestamp as a human-readable 'time ago' string."""
    try:
        if isinstance(timestamp, str) and timestamp.isdigit():
            timestamp = int(timestamp)
        elif not isinstance(timestamp, int):
            return ""
            
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