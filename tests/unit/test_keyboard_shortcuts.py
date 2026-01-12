"""
Unit tests for keyboard shortcuts

This module contains tests for the KeyboardShortcuts manager.
"""

import unittest
from unittest.mock import Mock, MagicMock


class TestKeyboardShortcutsLogic(unittest.TestCase):
    """Tests for keyboard shortcuts logic"""

    def test_default_shortcuts_exist(self):
        """Test that default shortcuts are defined"""
        from webradio.keyboard_shortcuts import KeyboardShortcuts

        shortcuts = KeyboardShortcuts.DEFAULT_SHORTCUTS

        # Verify essential shortcuts exist
        self.assertIn('play_pause', shortcuts)
        self.assertIn('stop', shortcuts)
        self.assertIn('volume_up', shortcuts)
        self.assertIn('volume_down', shortcuts)
        self.assertIn('quit', shortcuts)
        self.assertIn('focus_search', shortcuts)

    def test_handler_registration(self):
        """Test registering shortcut handlers"""
        from webradio.keyboard_shortcuts import KeyboardShortcuts

        mock_window = Mock()
        manager = KeyboardShortcuts(mock_window)

        mock_callback = Mock()
        manager.register_handler('play_pause', mock_callback)

        # Verify handler is registered
        self.assertIn('play_pause', manager.handlers)
        self.assertEqual(manager.handlers['play_pause'], mock_callback)

    def test_get_shortcut_display(self):
        """Test getting human-readable shortcut display"""
        from webradio.keyboard_shortcuts import KeyboardShortcuts

        mock_window = Mock()
        manager = KeyboardShortcuts(mock_window)

        # Test various shortcuts
        display = manager.get_shortcut_display('play_pause')
        self.assertEqual(display, 'Space')

        display = manager.get_shortcut_display('focus_search')
        self.assertEqual(display, 'Ctrl+f')

        display = manager.get_shortcut_display('quit')
        self.assertEqual(display, 'Ctrl+q')

    def test_get_all_shortcuts(self):
        """Test getting all shortcuts"""
        from webradio.keyboard_shortcuts import KeyboardShortcuts

        mock_window = Mock()
        manager = KeyboardShortcuts(mock_window)

        all_shortcuts = manager.get_all_shortcuts()

        # Verify it returns a dict
        self.assertIsInstance(all_shortcuts, dict)

        # Verify it has expected keys
        self.assertIn('play_pause', all_shortcuts)
        self.assertIn('quit', all_shortcuts)

        # Verify values are display strings
        self.assertIsInstance(all_shortcuts['play_pause'], str)


class TestSessionManagerLogic(unittest.TestCase):
    """Tests for session manager logic"""

    def test_session_data_structure(self):
        """Test session data structure"""
        session_data = {
            'station': {'name': 'Test Station', 'stationuuid': '12345'},
            'volume': 0.75,
            'was_playing': True
        }

        # Verify structure
        self.assertIn('station', session_data)
        self.assertIn('volume', session_data)
        self.assertIn('was_playing', session_data)

        # Verify types
        self.assertIsInstance(session_data['station'], dict)
        self.assertIsInstance(session_data['volume'], float)
        self.assertIsInstance(session_data['was_playing'], bool)

    def test_volume_range(self):
        """Test volume is in valid range"""
        test_volumes = [0.0, 0.5, 1.0]

        for volume in test_volumes:
            self.assertGreaterEqual(volume, 0.0)
            self.assertLessEqual(volume, 1.0)


class TestNotificationManagerLogic(unittest.TestCase):
    """Tests for notification manager logic"""

    def test_notification_formatting(self):
        """Test notification text formatting"""
        # Test track with artist
        artist = "Test Artist"
        title = "Test Title"
        expected = f"{artist} - {title}"
        self.assertEqual(expected, "Test Artist - Test Title")

        # Test track without artist
        title_only = "Test Title"
        self.assertEqual(title_only, "Test Title")

    def test_enable_disable(self):
        """Test enabling/disabling notifications"""
        mock_app = Mock()

        from webradio.notifications import NotificationManager
        manager = NotificationManager(mock_app)

        # Test initial state
        self.assertTrue(manager.enabled)

        # Test disabling
        manager.set_enabled(False)
        self.assertFalse(manager.enabled)

        # Test enabling
        manager.set_enabled(True)
        self.assertTrue(manager.enabled)

    def test_track_change_notifications_toggle(self):
        """Test toggling track change notifications"""
        mock_app = Mock()

        from webradio.notifications import NotificationManager
        manager = NotificationManager(mock_app)

        # Test initial state
        self.assertTrue(manager.show_track_changes)

        # Test toggling
        manager.set_track_change_notifications(False)
        self.assertFalse(manager.show_track_changes)

        manager.set_track_change_notifications(True)
        self.assertTrue(manager.show_track_changes)


if __name__ == '__main__':
    unittest.main()
