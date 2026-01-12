"""
Unit tests for Export/Import Manager

This module contains tests for exporting and importing station lists.
"""

import unittest
import tempfile
import os
from pathlib import Path

from webradio.export_import import ExportImportManager


class TestExportImportManager(unittest.TestCase):
    """Tests for Export/Import Manager"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = ExportImportManager()
        self.test_stations = [
            {
                'name': 'Test Station 1',
                'url': 'http://stream1.example.com',
                'url_resolved': 'http://stream1.example.com',
                'homepage': 'http://station1.example.com',
                'favicon': 'http://station1.example.com/icon.png',
                'tags': 'rock,alternative',
                'country': 'Germany',
                'language': 'German'
            },
            {
                'name': 'Test Station 2',
                'url': 'http://stream2.example.com',
                'url_resolved': 'http://stream2.example.com',
                'tags': 'jazz',
                'country': 'USA'
            }
        ]

    def test_export_to_opml(self):
        """Test exporting stations to OPML format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            temp_file = f.name

        try:
            # Export
            success = self.manager.export_to_opml(self.test_stations, temp_file)
            self.assertTrue(success)

            # Verify file exists and has content
            self.assertTrue(os.path.exists(temp_file))
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('<?xml', content)
                self.assertIn('<opml', content)
                self.assertIn('Test Station 1', content)
                self.assertIn('Test Station 2', content)

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_export_to_m3u(self):
        """Test exporting stations to M3U format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.m3u', delete=False) as f:
            temp_file = f.name

        try:
            # Export
            success = self.manager.export_to_m3u(self.test_stations, temp_file)
            self.assertTrue(success)

            # Verify file exists and has content
            self.assertTrue(os.path.exists(temp_file))
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('#EXTM3U', content)
                self.assertIn('#EXTINF:', content)
                self.assertIn('Test Station 1', content)
                self.assertIn('http://stream1.example.com', content)

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_import_from_opml(self):
        """Test importing stations from OPML format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            temp_file = f.name

        try:
            # First export
            self.manager.export_to_opml(self.test_stations, temp_file)

            # Then import
            imported = self.manager.import_from_opml(temp_file)

            # Verify
            self.assertIsNotNone(imported)
            self.assertEqual(len(imported), 2)
            self.assertEqual(imported[0]['name'], 'Test Station 1')
            self.assertEqual(imported[1]['name'], 'Test Station 2')

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_import_from_m3u(self):
        """Test importing stations from M3U format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.m3u', delete=False) as f:
            temp_file = f.name

        try:
            # First export
            self.manager.export_to_m3u(self.test_stations, temp_file)

            # Then import
            imported = self.manager.import_from_m3u(temp_file)

            # Verify
            self.assertIsNotNone(imported)
            self.assertEqual(len(imported), 2)
            self.assertEqual(imported[0]['name'], 'Test Station 1')
            self.assertEqual(imported[1]['name'], 'Test Station 2')

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_import_invalid_file(self):
        """Test importing from non-existent file"""
        imported = self.manager.import_from_opml('/nonexistent/file.opml')
        self.assertIsNone(imported)

    def test_export_empty_list(self):
        """Test exporting empty station list"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.opml', delete=False) as f:
            temp_file = f.name

        try:
            success = self.manager.export_to_opml([], temp_file)
            self.assertTrue(success)

            # Should create valid but empty OPML
            imported = self.manager.import_from_opml(temp_file)
            self.assertIsNotNone(imported)
            self.assertEqual(len(imported), 0)

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()
