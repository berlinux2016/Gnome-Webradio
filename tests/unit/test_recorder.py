"""Unit tests for stream recorder"""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import shutil
from webradio.recorder import StreamRecorder, RecordingFormat


class TestStreamRecorder(unittest.TestCase):
    """Test stream recorder"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_player = MagicMock()
        self.mock_settings = None
        self.recorder = StreamRecorder(self.mock_player, self.mock_settings)

        # Use temp directory for tests
        self.test_dir = Path(tempfile.mkdtemp())
        self.recorder.output_directory = self.test_dir

    def tearDown(self):
        """Clean up after tests"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """Test recorder initialization"""
        self.assertFalse(self.recorder.is_recording)
        self.assertIsNone(self.recorder.current_file)
        self.assertEqual(self.recorder.output_format, 'mp3')

    def test_get_available_formats(self):
        """Test getting available recording formats"""
        formats = self.recorder.get_available_formats()
        self.assertIsInstance(formats, dict)
        self.assertIn('mp3', formats)
        self.assertIn('flac', formats)
        self.assertIn('wav', formats)
        self.assertIn('ogg', formats)

    def test_set_format(self):
        """Test setting recording format"""
        result = self.recorder.set_format('flac')
        self.assertTrue(result)
        self.assertEqual(self.recorder.get_format(), 'flac')

    def test_set_invalid_format(self):
        """Test setting invalid format"""
        result = self.recorder.set_format('unknown_format')
        self.assertFalse(result)
        # Format should remain unchanged
        self.assertEqual(self.recorder.get_format(), 'mp3')

    def test_set_output_directory(self):
        """Test setting output directory"""
        new_dir = self.test_dir / 'recordings'
        result = self.recorder.set_output_directory(str(new_dir))

        self.assertTrue(result)
        self.assertEqual(self.recorder.get_output_directory(), str(new_dir))

    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Test with invalid characters
        result = self.recorder._sanitize_filename('Station/Name:Test*')
        self.assertNotIn('/', result)
        self.assertNotIn(':', result)
        self.assertNotIn('*', result)

        # Test with long name
        long_name = 'A' * 150
        result = self.recorder._sanitize_filename(long_name)
        self.assertLessEqual(len(result), 100)

    def test_generate_filename(self):
        """Test filename generation"""
        station = {
            'name': 'Test Station',
            'country': 'Germany'
        }

        filename = self.recorder._generate_filename(station)

        # Should contain station name (with underscores) and have correct extension
        # Note: sanitize preserves spaces, not converts them to underscores
        self.assertIn('Test Station', filename)
        self.assertTrue(filename.endswith('.mp3'))

    def test_start_recording_when_not_playing(self):
        """Test that recording fails when not playing"""
        self.mock_player.is_playing.return_value = False

        station = {'name': 'Test'}
        result = self.recorder.start_recording(station)

        self.assertFalse(result)
        self.assertFalse(self.recorder.is_recording)

    def test_start_recording_already_recording(self):
        """Test that recording fails when already recording"""
        self.recorder.is_recording = True

        station = {'name': 'Test'}
        result = self.recorder.start_recording(station)

        self.assertFalse(result)

    def test_stop_recording_when_not_recording(self):
        """Test that stop fails when not recording"""
        result = self.recorder.stop_recording()
        self.assertFalse(result)

    def test_is_recording_active(self):
        """Test recording status check"""
        self.assertFalse(self.recorder.is_recording_active())

        self.recorder.is_recording = True
        self.assertTrue(self.recorder.is_recording_active())

    def test_set_filename_template(self):
        """Test setting filename template"""
        template = '{station}_{date}'
        result = self.recorder.set_filename_template(template)

        self.assertTrue(result)
        self.assertEqual(self.recorder.get_filename_template(), template)

    def test_recording_format_definitions(self):
        """Test that all formats have required fields"""
        for format_key, format_data in RecordingFormat.FORMATS.items():
            self.assertIn('name', format_data)
            self.assertIn('extension', format_data)
            self.assertIn('encoder', format_data)
            self.assertIn('quality', format_data)


if __name__ == '__main__':
    unittest.main()
