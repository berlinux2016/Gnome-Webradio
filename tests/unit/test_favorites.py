"""Unit tests for favorites manager"""

import unittest
import json
from pathlib import Path
import tempfile
import shutil
from webradio.favorites import FavoritesManager


class TestFavoritesManager(unittest.TestCase):
    """Test favorites management"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test
        self.test_dir = Path(tempfile.mkdtemp())
        self.manager = FavoritesManager()
        # Override config directory for testing
        self.manager.config_dir = self.test_dir
        self.manager.favorites_file = self.test_dir / 'favorites.json'
        self.manager.favorites = []

    def tearDown(self):
        """Clean up after tests"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_add_favorite(self):
        """Test adding a favorite station"""
        station = {
            'stationuuid': 'test-uuid-123',
            'name': 'Test Station',
            'url': 'http://example.com/stream',
            'country': 'Germany'
        }

        result = self.manager.add_favorite(station)
        self.assertTrue(result)
        self.assertEqual(len(self.manager.favorites), 1)
        self.assertEqual(self.manager.favorites[0]['name'], 'Test Station')

    def test_add_duplicate_favorite(self):
        """Test adding duplicate favorite"""
        station = {
            'stationuuid': 'test-uuid-123',
            'name': 'Test Station'
        }

        # Add first time
        self.manager.add_favorite(station)

        # Try to add again
        result = self.manager.add_favorite(station)
        self.assertFalse(result)
        self.assertEqual(len(self.manager.favorites), 1)

    def test_remove_favorite(self):
        """Test removing a favorite"""
        station = {
            'stationuuid': 'test-uuid-123',
            'name': 'Test Station'
        }

        self.manager.add_favorite(station)
        result = self.manager.remove_favorite('test-uuid-123')

        self.assertTrue(result)
        self.assertEqual(len(self.manager.favorites), 0)

    def test_is_favorite(self):
        """Test checking if station is favorite"""
        station = {
            'stationuuid': 'test-uuid-123',
            'name': 'Test Station'
        }

        self.assertFalse(self.manager.is_favorite('test-uuid-123'))

        self.manager.add_favorite(station)
        self.assertTrue(self.manager.is_favorite('test-uuid-123'))

    def test_save_and_load_favorites(self):
        """Test saving and loading favorites"""
        station = {
            'stationuuid': 'test-uuid-123',
            'name': 'Test Station',
            'url': 'http://example.com/stream'
        }

        self.manager.add_favorite(station)
        self.manager.save_favorites()

        # Create new manager and load
        new_manager = FavoritesManager()
        new_manager.config_dir = self.test_dir
        new_manager.favorites_file = self.test_dir / 'favorites.json'
        new_manager.load_favorites()

        self.assertEqual(len(new_manager.favorites), 1)
        self.assertEqual(new_manager.favorites[0]['name'], 'Test Station')

    def test_search_favorites(self):
        """Test searching favorites"""
        stations = [
            {'stationuuid': '1', 'name': 'Rock Station'},
            {'stationuuid': '2', 'name': 'Jazz Radio'},
            {'stationuuid': '3', 'name': 'Rock FM'}
        ]

        for station in stations:
            self.manager.add_favorite(station)

        results = self.manager.search_favorites('Rock*')
        self.assertEqual(len(results), 2)

    def test_get_count(self):
        """Test getting favorites count"""
        self.assertEqual(self.manager.get_count(), 0)

        station = {'stationuuid': '1', 'name': 'Test'}
        self.manager.add_favorite(station)

        self.assertEqual(self.manager.get_count(), 1)


if __name__ == '__main__':
    unittest.main()
