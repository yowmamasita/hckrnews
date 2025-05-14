import datetime
import json
import requests
from typing import Dict, List, Optional, Any, Tuple

class HackerNewsAPI:
    BASE_URL = "https://hckrnews.com/data/{}.js"
    
    @staticmethod
    def get_stories(date: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
        """Fetch stories from HackerNews API for a specific date."""
        if date is None:
            date = datetime.date.today()
            
        date_str = date.strftime("%Y%m%d")
        url = HackerNewsAPI.BASE_URL.format(date_str)
        
        try:
            headers = {"User-Agent": "HackerNewsClient/1.0"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = json.loads(response.text)
            
            if not isinstance(data, list):
                print(f"API returned unexpected data format: {type(data)}")
                return []
                
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
    
    @staticmethod
    def get_comment_url(story_id: str) -> str:
        """Generate the URL for the comments page of a story."""
        return f"https://news.ycombinator.com/item?id={story_id}"
