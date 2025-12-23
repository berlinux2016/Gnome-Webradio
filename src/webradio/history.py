"""History management for recently played radio stations"""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta
import time


class HistoryManager:
    """Manage history of recently played radio stations"""

    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'webradio'
        self.history_file = self.config_dir / 'history.json'
        self.history: List[Dict] = []
        self._ensure_config_dir()
        self.load_history()
        self._cleanup_old_entries()

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_history(self):
        """Load history from file"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            else:
                self.history = []
        except Exception as e:
            print(f"Error loading history: {e}")
            self.history = []

    def save_history(self):
        """Save history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history: {e}")

    def add_entry(self, station: Dict, metadata: Optional[Dict] = None) -> bool:
        """Add a station play event to history"""
        try:
            # Create history entry
            entry = {
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
                'timestamp': datetime.now().isoformat(),
                'unix_timestamp': int(time.time()),
                'last_metadata': metadata or {},
                'play_count': 1,  # Will be incremented if station exists
            }

            # Check if station was recently played (within last hour)
            recent_play = self._find_recent_play(entry['stationuuid'], hours=1)

            if recent_play:
                # Update existing entry instead of creating new one
                recent_play['timestamp'] = entry['timestamp']
                recent_play['unix_timestamp'] = entry['unix_timestamp']
                recent_play['play_count'] = recent_play.get('play_count', 1) + 1
                recent_play['last_metadata'] = entry['last_metadata']
            else:
                # Add new entry at the beginning (most recent first)
                self.history.insert(0, entry)

            # Limit history to 500 most recent entries
            if len(self.history) > 500:
                self.history = self.history[:500]

            self.save_history()
            return True

        except Exception as e:
            print(f"Error adding history entry: {e}")
            return False

    def _find_recent_play(self, station_uuid: str, hours: int = 1) -> Optional[Dict]:
        """Find if station was played recently"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        for entry in self.history:
            if entry.get('stationuuid') == station_uuid:
                try:
                    entry_time = datetime.fromisoformat(entry.get('timestamp', ''))
                    if entry_time >= cutoff_time:
                        return entry
                except:
                    pass

        return None

    def get_recent(self, limit: int = 50) -> List[Dict]:
        """Get recent station history"""
        return self.history[:limit]

    def get_all(self) -> List[Dict]:
        """Get all history entries"""
        return self.history

    def search_history(self, query: str) -> List[Dict]:
        """Search history by station name or tags"""
        if not query:
            return self.history

        query_lower = query.lower()
        results = []

        for entry in self.history:
            name = entry.get('name', '').lower()
            tags = entry.get('tags', '').lower()
            country = entry.get('country', '').lower()

            if (query_lower in name or
                query_lower in tags or
                query_lower in country):
                results.append(entry)

        return results

    def get_by_station_uuid(self, station_uuid: str) -> List[Dict]:
        """Get all history entries for a specific station"""
        return [e for e in self.history if e.get('stationuuid') == station_uuid]

    def get_most_played(self, limit: int = 10) -> List[Dict]:
        """Get most played stations"""
        # Sort by play_count (descending)
        sorted_history = sorted(
            self.history,
            key=lambda x: x.get('play_count', 0),
            reverse=True
        )
        return sorted_history[:limit]

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get history entries within date range"""
        results = []

        for entry in self.history:
            try:
                entry_time = datetime.fromisoformat(entry.get('timestamp', ''))
                if start_date <= entry_time <= end_date:
                    results.append(entry)
            except:
                pass

        return results

    def clear_history(self) -> bool:
        """Clear all history"""
        try:
            self.history = []
            self.save_history()
            return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False

    def clear_old(self, days: int = 30) -> int:
        """Remove entries older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            original_count = len(self.history)

            self.history = [
                entry for entry in self.history
                if datetime.fromisoformat(entry.get('timestamp', datetime.now().isoformat())) >= cutoff_date
            ]

            removed_count = original_count - len(self.history)

            if removed_count > 0:
                self.save_history()

            return removed_count

        except Exception as e:
            print(f"Error cleaning old history: {e}")
            return 0

    def _cleanup_old_entries(self, days: int = 90):
        """Auto-cleanup entries older than 90 days on initialization"""
        removed = self.clear_old(days)
        if removed > 0:
            print(f"Cleaned up {removed} history entries older than {days} days")

    def get_count(self) -> int:
        """Get total number of history entries"""
        return len(self.history)

    def get_stations_played_today(self) -> List[Dict]:
        """Get stations played today"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now()
        return self.get_by_date_range(today_start, today_end)

    def update_entry_metadata(self, station_uuid: str, metadata: Dict):
        """Update metadata for the most recent entry of a station"""
        for entry in self.history:
            if entry.get('stationuuid') == station_uuid:
                entry['last_metadata'] = metadata
                self.save_history()
                return True
        return False

    def remove_station_from_history(self, station_uuid: str) -> int:
        """Remove all entries for a specific station"""
        original_count = len(self.history)
        self.history = [e for e in self.history if e.get('stationuuid') != station_uuid]
        removed_count = original_count - len(self.history)

        if removed_count > 0:
            self.save_history()

        return removed_count
