"""
Unit tests for Playlist Manager

This module contains tests for managing playlists.
"""

import unittest
import tempfile
import os
from pathlib import Path

from webradio.playlist_manager import PlaylistManager


class TestPlaylistManager(unittest.TestCase):
    """Tests for Playlist Manager"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temp directory for test
        self.temp_dir = tempfile.mkdtemp()
        self.manager = PlaylistManager(config_dir=self.temp_dir)

        self.test_station = {
            'stationuuid': 'test-uuid-123',
            'name': 'Test Station',
            'url': 'http://stream.example.com',
            'url_resolved': 'http://stream.example.com'
        }

    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temp directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_playlist(self):
        """Test creating a new playlist"""
        playlist_id = self.manager.create_playlist('My Playlist', 'Test description')

        self.assertIsNotNone(playlist_id)
        self.assertEqual(self.manager.get_playlist_count(), 1)

        playlist = self.manager.get_playlist(playlist_id)
        self.assertEqual(playlist['name'], 'My Playlist')
        self.assertEqual(playlist['description'], 'Test description')

    def test_delete_playlist(self):
        """Test deleting a playlist"""
        playlist_id = self.manager.create_playlist('Test Playlist')
        self.assertEqual(self.manager.get_playlist_count(), 1)

        success = self.manager.delete_playlist(playlist_id)
        self.assertTrue(success)
        self.assertEqual(self.manager.get_playlist_count(), 0)

    def test_delete_nonexistent_playlist(self):
        """Test deleting a non-existent playlist"""
        success = self.manager.delete_playlist('nonexistent-id')
        self.assertFalse(success)

    def test_rename_playlist(self):
        """Test renaming a playlist"""
        playlist_id = self.manager.create_playlist('Old Name')

        success = self.manager.rename_playlist(playlist_id, 'New Name')
        self.assertTrue(success)

        playlist = self.manager.get_playlist(playlist_id)
        self.assertEqual(playlist['name'], 'New Name')

    def test_add_station(self):
        """Test adding a station to a playlist"""
        playlist_id = self.manager.create_playlist('My Playlist')

        success = self.manager.add_station(playlist_id, self.test_station)
        self.assertTrue(success)

        stations = self.manager.get_stations(playlist_id)
        self.assertEqual(len(stations), 1)
        self.assertEqual(stations[0]['name'], 'Test Station')

    def test_add_duplicate_station(self):
        """Test adding a duplicate station"""
        playlist_id = self.manager.create_playlist('My Playlist')

        self.manager.add_station(playlist_id, self.test_station)
        success = self.manager.add_station(playlist_id, self.test_station)

        # Should fail on duplicate
        self.assertFalse(success)
        self.assertEqual(self.manager.get_station_count(playlist_id), 1)

    def test_remove_station(self):
        """Test removing a station from a playlist"""
        playlist_id = self.manager.create_playlist('My Playlist')
        self.manager.add_station(playlist_id, self.test_station)

        success = self.manager.remove_station(playlist_id, 'test-uuid-123')
        self.assertTrue(success)

        self.assertEqual(self.manager.get_station_count(playlist_id), 0)

    def test_is_station_in_playlist(self):
        """Test checking if station is in playlist"""
        playlist_id = self.manager.create_playlist('My Playlist')

        # Should not be in playlist initially
        self.assertFalse(self.manager.is_station_in_playlist(playlist_id, 'test-uuid-123'))

        # Add station
        self.manager.add_station(playlist_id, self.test_station)

        # Should now be in playlist
        self.assertTrue(self.manager.is_station_in_playlist(playlist_id, 'test-uuid-123'))

    def test_get_all_playlists(self):
        """Test getting all playlists"""
        self.manager.create_playlist('Playlist 1')
        self.manager.create_playlist('Playlist 2')
        self.manager.create_playlist('Playlist 3')

        playlists = self.manager.get_all_playlists()
        self.assertEqual(len(playlists), 3)

    def test_search_playlists(self):
        """Test searching playlists"""
        self.manager.create_playlist('Rock Music', 'Hard rock stations')
        self.manager.create_playlist('Jazz Classics', 'Classic jazz')
        self.manager.create_playlist('Morning Drive', 'News and rock')

        # Search by name
        results = self.manager.search_playlists('rock')
        self.assertEqual(len(results), 2)  # Rock Music and Morning Drive

        # Search by description
        results = self.manager.search_playlists('classic')
        self.assertEqual(len(results), 1)  # Jazz Classics

    def test_update_description(self):
        """Test updating playlist description"""
        playlist_id = self.manager.create_playlist('Test', 'Old description')

        success = self.manager.update_description(playlist_id, 'New description')
        self.assertTrue(success)

        playlist = self.manager.get_playlist(playlist_id)
        self.assertEqual(playlist['description'], 'New description')

    def test_persistence(self):
        """Test that playlists persist across manager instances"""
        playlist_id = self.manager.create_playlist('Persistent Playlist')
        self.manager.add_station(playlist_id, self.test_station)

        # Create new manager instance with same config dir
        new_manager = PlaylistManager(config_dir=self.temp_dir)

        # Should load existing playlists
        self.assertEqual(new_manager.get_playlist_count(), 1)
        playlist = new_manager.get_playlist(playlist_id)
        self.assertEqual(playlist['name'], 'Persistent Playlist')
        self.assertEqual(len(playlist['stations']), 1)


if __name__ == '__main__':
    unittest.main()
