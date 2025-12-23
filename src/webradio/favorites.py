"""Favorites management for radio stations"""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path


class FavoritesManager:
    """Manage favorite radio stations"""

    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'webradio'
        self.favorites_file = self.config_dir / 'favorites.json'
        self.favorites: List[Dict] = []
        self._ensure_config_dir()
        self.load_favorites()

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_favorites(self):
        """Load favorites from file"""
        try:
            if self.favorites_file.exists():
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    self.favorites = json.load(f)
            else:
                self.favorites = []
        except Exception as e:
            print(f"Error loading favorites: {e}")
            self.favorites = []

    def save_favorites(self):
        """Save favorites to file"""
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving favorites: {e}")

    def add_favorite(self, station: Dict) -> bool:
        """Add a station to favorites"""
        # Check if already in favorites
        if self.is_favorite(station.get('stationuuid', '')):
            return False

        # Store essential station info
        favorite = {
            'stationuuid': station.get('stationuuid', ''),
            'name': station.get('name', ''),
            'url': station.get('url', ''),
            'url_resolved': station.get('url_resolved', ''),
            'favicon': station.get('favicon', ''),
            'country': station.get('country', ''),
            'language': station.get('language', ''),
            'tags': station.get('tags', ''),
            'codec': station.get('codec', ''),
            'bitrate': station.get('bitrate', 0),
            'homepage': station.get('homepage', ''),
        }

        self.favorites.append(favorite)
        self.save_favorites()
        return True

    def remove_favorite(self, station_uuid: str) -> bool:
        """Remove a station from favorites"""
        original_length = len(self.favorites)
        self.favorites = [f for f in self.favorites if f.get('stationuuid') != station_uuid]

        if len(self.favorites) < original_length:
            self.save_favorites()
            return True
        return False

    def is_favorite(self, station_uuid: str) -> bool:
        """Check if a station is in favorites"""
        return any(f.get('stationuuid') == station_uuid for f in self.favorites)

    def get_favorites(self) -> List[Dict]:
        """Get all favorite stations"""
        return self.favorites.copy()

    def search_favorites(self, query: str) -> List[Dict]:
        """Search in favorites by name (supports wildcards)"""
        if not query:
            return self.get_favorites()

        # Convert wildcard to regex pattern
        import re
        pattern = query.replace('*', '.*').replace('?', '.')
        pattern = re.compile(pattern, re.IGNORECASE)

        return [
            station for station in self.favorites
            if pattern.search(station.get('name', ''))
        ]

    def clear_favorites(self):
        """Clear all favorites"""
        self.favorites = []
        self.save_favorites()

    def get_favorite_by_uuid(self, station_uuid: str) -> Optional[Dict]:
        """Get a favorite station by UUID"""
        for station in self.favorites:
            if station.get('stationuuid') == station_uuid:
                return station
        return None

    def update_favorite(self, station_uuid: str, updated_data: Dict):
        """Update favorite station data"""
        for i, station in enumerate(self.favorites):
            if station.get('stationuuid') == station_uuid:
                self.favorites[i].update(updated_data)
                self.save_favorites()
                return True
        return False

    def get_count(self) -> int:
        """Get number of favorites"""
        return len(self.favorites)
