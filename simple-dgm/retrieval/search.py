import requests
import os
from typing import List, Dict

class WebSearchService:
    def __init__(self):
        self.api_key = os.getenv('BRAVE_API_KEY')
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        
    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search the web and return results"""
        if not self.api_key:
            print("Warning: No Brave API key found")
            return []
            
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }
        
        params = {
            "q": query,
            "count": max_results
        }
        
        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('web', {}).get('results', [])
            else:
                print(f"Search API error: {response.status_code}")
                return []
        except Exception as e:
            print(f"Search error: {e}")
            return [] 