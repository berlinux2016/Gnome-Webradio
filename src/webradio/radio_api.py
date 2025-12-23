"""Radio Browser API integration"""

import requests
import json
import random
from typing import List, Dict, Optional
from urllib.parse import quote


class RadioBrowserAPI:
    """Interface to the Radio Browser API"""

    def __init__(self):
        self.base_url = self._get_server_url()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WebRadioPlayer/1.0.0',
            'Content-Type': 'application/json'
        })

    def _get_server_url(self) -> str:
        """Get a random Radio Browser server"""
        try:
            # Get list of available servers
            response = requests.get('https://all.api.radio-browser.info/json/servers')
            servers = response.json()
            if servers:
                # Pick a random server
                server = random.choice(servers)
                return f"https://{server['name']}"
        except Exception:
            pass
        # Fallback to default server
        return 'https://de1.api.radio-browser.info'

    def search_stations(self, name: str = '', limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Search for radio stations by name
        Supports wildcard search with *
        """
        try:
            # Convert wildcard to API format
            search_term = name.replace('*', '%')

            url = f"{self.base_url}/json/stations/byname/{quote(search_term)}"
            params = {
                'limit': limit,
                'offset': offset,
                'order': 'votes',
                'reverse': 'true'
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print(f"Error searching stations: {e}")
            return []

    def get_top_stations(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get top voted stations"""
        try:
            url = f"{self.base_url}/json/stations/topvote/{limit}"
            params = {'offset': offset}
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting top stations: {e}")
            return []

    def search_by_tag(self, tag: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Search stations by tag"""
        try:
            url = f"{self.base_url}/json/stations/bytag/{quote(tag)}"
            params = {'limit': limit, 'offset': offset}
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error searching by tag: {e}")
            return []

    def search_by_country(self, country: str, limit: int = 100) -> List[Dict]:
        """Search stations by country"""
        try:
            url = f"{self.base_url}/json/stations/bycountry/{quote(country)}"
            params = {'limit': limit}
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error searching by country: {e}")
            return []

    def get_station_by_uuid(self, uuid: str) -> Optional[Dict]:
        """Get a station by its UUID"""
        try:
            url = f"{self.base_url}/json/stations/byuuid/{uuid}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            stations = response.json()
            return stations[0] if stations else None
        except Exception as e:
            print(f"Error getting station by UUID: {e}")
            return None

    def register_click(self, station_uuid: str):
        """Register a click (play) on a station"""
        try:
            url = f"{self.base_url}/json/url/{station_uuid}"
            self.session.get(url, timeout=5)
        except Exception:
            pass  # Non-critical operation

    def vote_for_station(self, station_uuid: str):
        """Vote for a station"""
        try:
            url = f"{self.base_url}/json/vote/{station_uuid}"
            self.session.get(url, timeout=5)
        except Exception:
            pass  # Non-critical operation

    def get_countries(self, limit: int = 300) -> List[Dict]:
        """Get list of all countries with station counts"""
        try:
            url = f"{self.base_url}/json/countries"
            params = {'limit': limit}
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting countries: {e}")
            return []
