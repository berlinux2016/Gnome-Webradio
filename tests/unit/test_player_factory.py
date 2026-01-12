"""Unit tests for player factory"""

import unittest
from unittest.mock import patch, MagicMock
from webradio.player_factory import create_player


class TestPlayerFactory(unittest.TestCase):
    """Test player factory functionality"""

    @patch('webradio.player_advanced.AdvancedAudioPlayer')
    def test_create_advanced_player(self, mock_advanced):
        """Test creating advanced player"""
        mock_instance = MagicMock()
        mock_advanced.return_value = mock_instance

        player = create_player(use_advanced=True)

        # Should create AdvancedAudioPlayer
        mock_advanced.assert_called_once()
        self.assertEqual(player, mock_instance)

    @patch('webradio.player.AudioPlayer')
    @patch('webradio.player_advanced.AdvancedAudioPlayer')
    def test_fallback_to_simple_player(self, mock_advanced, mock_simple):
        """Test falling back to simple player when advanced fails"""
        # Make advanced player raise exception
        mock_advanced.side_effect = Exception("Advanced player not available")

        mock_simple_instance = MagicMock()
        mock_simple.return_value = mock_simple_instance

        player = create_player(use_advanced=True)

        # Should fallback to AudioPlayer
        mock_simple.assert_called_once()
        self.assertEqual(player, mock_simple_instance)

    @patch('webradio.player.AudioPlayer')
    def test_create_simple_player_directly(self, mock_simple):
        """Test creating simple player directly"""
        mock_instance = MagicMock()
        mock_simple.return_value = mock_instance

        player = create_player(use_advanced=False)

        # Should create AudioPlayer directly
        mock_simple.assert_called_once()
        self.assertEqual(player, mock_instance)


if __name__ == '__main__':
    unittest.main()
