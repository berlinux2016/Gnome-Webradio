"""
Playlist Manager for Gnome Web Radio

This module provides functionality to create, manage, and organize
playlists of radio stations.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from webradio.logger import get_logger

logger = get_logger(__name__)


class PlaylistManager:
    """
    Manages playlists of radio stations.

    Playlists allow users to organize stations into themed collections
    (e.g., "Morning Coffee", "Workout", "Jazz Night").
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the playlist manager.

        Args:
            config_dir: Configuration directory path (default: ~/.config/webradio/)
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'webradio')

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.playlists_file = self.config_dir / 'playlists.json'
        self.playlists = self._load_playlists()

        logger.info(f"Playlist manager initialized: {self.playlists_file}")

    def _load_playlists(self) -> Dict:
        """
        Load playlists from disk.

        Returns:
            dict: Dictionary of playlists {playlist_id: playlist_data}
        """
        if not self.playlists_file.exists():
            logger.info("No playlists file found, starting fresh")
            return {}

        try:
            with open(self.playlists_file, 'r', encoding='utf-8') as f:
                playlists = json.load(f)
            logger.info(f"Loaded {len(playlists)} playlists")
            return playlists
        except Exception as e:
            logger.error(f"Failed to load playlists: {e}")
            return {}

    def _save_playlists(self):
        """Save playlists to disk."""
        try:
            with open(self.playlists_file, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=2, ensure_ascii=False)
            logger.debug("Playlists saved")
        except Exception as e:
            logger.error(f"Failed to save playlists: {e}")

    def create_playlist(self, name: str, description: str = "") -> str:
        """
        Create a new playlist.

        Args:
            name: Name of the playlist
            description: Optional description

        Returns:
            str: Playlist ID
        """
        import uuid
        playlist_id = str(uuid.uuid4())

        self.playlists[playlist_id] = {
            'id': playlist_id,
            'name': name,
            'description': description,
            'stations': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        self._save_playlists()
        logger.info(f"Created playlist: {name} (ID: {playlist_id})")
        return playlist_id

    def delete_playlist(self, playlist_id: str) -> bool:
        """
        Delete a playlist.

        Args:
            playlist_id: ID of the playlist to delete

        Returns:
            bool: True if deleted, False if not found
        """
        if playlist_id in self.playlists:
            name = self.playlists[playlist_id]['name']
            del self.playlists[playlist_id]
            self._save_playlists()
            logger.info(f"Deleted playlist: {name}")
            return True
        return False

    def rename_playlist(self, playlist_id: str, new_name: str) -> bool:
        """
        Rename a playlist.

        Args:
            playlist_id: ID of the playlist
            new_name: New name for the playlist

        Returns:
            bool: True if renamed, False if not found
        """
        if playlist_id in self.playlists:
            old_name = self.playlists[playlist_id]['name']
            self.playlists[playlist_id]['name'] = new_name
            self.playlists[playlist_id]['updated_at'] = datetime.now().isoformat()
            self._save_playlists()
            logger.info(f"Renamed playlist: {old_name} -> {new_name}")
            return True
        return False

    def update_description(self, playlist_id: str, description: str) -> bool:
        """
        Update playlist description.

        Args:
            playlist_id: ID of the playlist
            description: New description

        Returns:
            bool: True if updated, False if not found
        """
        if playlist_id in self.playlists:
            self.playlists[playlist_id]['description'] = description
            self.playlists[playlist_id]['updated_at'] = datetime.now().isoformat()
            self._save_playlists()
            logger.debug(f"Updated playlist description: {self.playlists[playlist_id]['name']}")
            return True
        return False

    def add_station(self, playlist_id: str, station: Dict) -> bool:
        """
        Add a station to a playlist.

        Args:
            playlist_id: ID of the playlist
            station: Station dictionary

        Returns:
            bool: True if added, False if not found or already exists
        """
        if playlist_id not in self.playlists:
            return False

        # Check if station already in playlist
        station_uuid = station.get('stationuuid', '')
        stations = self.playlists[playlist_id]['stations']

        if any(s.get('stationuuid') == station_uuid for s in stations):
            logger.debug(f"Station already in playlist: {station.get('name')}")
            return False

        # Add station
        stations.append(station)
        self.playlists[playlist_id]['updated_at'] = datetime.now().isoformat()
        self._save_playlists()
        logger.info(f"Added station to playlist: {station.get('name')} -> {self.playlists[playlist_id]['name']}")
        return True

    def remove_station(self, playlist_id: str, station_uuid: str) -> bool:
        """
        Remove a station from a playlist.

        Args:
            playlist_id: ID of the playlist
            station_uuid: UUID of the station to remove

        Returns:
            bool: True if removed, False if not found
        """
        if playlist_id not in self.playlists:
            return False

        stations = self.playlists[playlist_id]['stations']
        original_length = len(stations)

        # Filter out the station
        self.playlists[playlist_id]['stations'] = [
            s for s in stations if s.get('stationuuid') != station_uuid
        ]

        if len(self.playlists[playlist_id]['stations']) < original_length:
            self.playlists[playlist_id]['updated_at'] = datetime.now().isoformat()
            self._save_playlists()
            logger.info(f"Removed station from playlist: {self.playlists[playlist_id]['name']}")
            return True

        return False

    def get_playlist(self, playlist_id: str) -> Optional[Dict]:
        """
        Get a specific playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            dict: Playlist data, or None if not found
        """
        return self.playlists.get(playlist_id)

    def get_all_playlists(self) -> List[Dict]:
        """
        Get all playlists.

        Returns:
            List of playlist dictionaries
        """
        return list(self.playlists.values())

    def get_playlist_count(self) -> int:
        """
        Get the number of playlists.

        Returns:
            int: Number of playlists
        """
        return len(self.playlists)

    def get_stations(self, playlist_id: str) -> List[Dict]:
        """
        Get all stations in a playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of station dictionaries
        """
        if playlist_id in self.playlists:
            return self.playlists[playlist_id]['stations']
        return []

    def get_station_count(self, playlist_id: str) -> int:
        """
        Get the number of stations in a playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            int: Number of stations in playlist
        """
        if playlist_id in self.playlists:
            return len(self.playlists[playlist_id]['stations'])
        return 0

    def is_station_in_playlist(self, playlist_id: str, station_uuid: str) -> bool:
        """
        Check if a station is in a playlist.

        Args:
            playlist_id: ID of the playlist
            station_uuid: UUID of the station

        Returns:
            bool: True if station is in playlist
        """
        if playlist_id not in self.playlists:
            return False

        return any(
            s.get('stationuuid') == station_uuid
            for s in self.playlists[playlist_id]['stations']
        )

    def search_playlists(self, query: str) -> List[Dict]:
        """
        Search playlists by name or description.

        Args:
            query: Search query

        Returns:
            List of matching playlists
        """
        query = query.lower()
        results = []

        for playlist in self.playlists.values():
            if (query in playlist['name'].lower() or
                query in playlist.get('description', '').lower()):
                results.append(playlist)

        logger.debug(f"Search '{query}' found {len(results)} playlists")
        return results


def create_playlist_manager(config_dir: Optional[str] = None) -> PlaylistManager:
    """
    Factory function to create a playlist manager.

    Args:
        config_dir: Configuration directory path

    Returns:
        PlaylistManager: Configured playlist manager
    """
    return PlaylistManager(config_dir)
