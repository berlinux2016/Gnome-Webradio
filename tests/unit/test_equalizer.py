"""Unit tests for equalizer manager"""

import unittest
from unittest.mock import MagicMock, patch
from webradio.equalizer import EqualizerManager, EqualizerPreset


class TestEqualizerManager(unittest.TestCase):
    """Test equalizer management"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_player = MagicMock()
        self.mock_settings = None
        self.manager = EqualizerManager(self.mock_player, self.mock_settings)

    def test_initialization(self):
        """Test equalizer manager initialization"""
        self.assertEqual(self.manager.current_preset, 'flat')
        self.assertFalse(self.manager.enabled)
        self.assertEqual(len(self.manager.custom_gains), 10)

    def test_get_presets(self):
        """Test getting available presets"""
        presets = self.manager.get_presets()
        self.assertIsInstance(presets, list)
        self.assertIn('flat', presets)
        self.assertIn('rock', presets)
        self.assertIn('pop', presets)
        self.assertIn('jazz', presets)

    def test_apply_preset(self):
        """Test applying a preset"""
        self.manager.enabled = True
        self.mock_player.set_equalizer_band = MagicMock(return_value=True)

        result = self.manager.apply_preset('rock')

        self.assertTrue(result)
        self.assertEqual(self.manager.current_preset, 'rock')
        # Should have called set_equalizer_band for each of 10 bands
        self.assertEqual(self.mock_player.set_equalizer_band.call_count, 10)

    def test_apply_unknown_preset(self):
        """Test applying unknown preset"""
        result = self.manager.apply_preset('unknown_preset')
        self.assertFalse(result)

    def test_set_band(self):
        """Test setting individual band"""
        self.manager.enabled = True
        self.mock_player.set_equalizer_band = MagicMock(return_value=True)

        result = self.manager.set_band(0, 5.0)

        self.assertTrue(result)
        self.assertEqual(self.manager.custom_gains[0], 5.0)
        self.assertEqual(self.manager.current_preset, 'custom')

    def test_set_band_clamps_gain(self):
        """Test that set_band clamps gain values"""
        self.manager.enabled = True
        self.mock_player.set_equalizer_band = MagicMock(return_value=True)

        # Try to set beyond max
        self.manager.set_band(0, 50.0)
        self.assertEqual(self.manager.custom_gains[0], 12.0)

        # Try to set below min
        self.manager.set_band(1, -50.0)
        self.assertEqual(self.manager.custom_gains[1], -24.0)

    def test_set_band_invalid_index(self):
        """Test setting band with invalid index"""
        result = self.manager.set_band(20, 5.0)
        self.assertFalse(result)

    def test_get_band(self):
        """Test getting band gain"""
        self.manager.custom_gains[0] = 5.0
        self.manager.current_preset = 'custom'
        # Mock the player's get_equalizer_band to return the value
        self.mock_player.get_equalizer_band.return_value = 5.0

        gain = self.manager.get_band(0)
        self.assertEqual(gain, 5.0)

    def test_reset_to_flat(self):
        """Test resetting to flat preset"""
        self.manager.current_preset = 'rock'
        result = self.manager.reset_to_flat()

        self.assertTrue(result)
        self.assertEqual(self.manager.current_preset, 'flat')

    def test_get_band_frequency(self):
        """Test getting band frequency"""
        freq = self.manager.get_band_frequency(0)
        self.assertEqual(freq, 31)

        freq = self.manager.get_band_frequency(9)
        self.assertEqual(freq, 16000)

    def test_get_band_label(self):
        """Test getting band label"""
        label = self.manager.get_band_label(0)
        self.assertEqual(label, '31 Hz')

        label = self.manager.get_band_label(9)
        self.assertEqual(label, '16 kHz')

    def test_equalizer_preset_definitions(self):
        """Test that all presets have required fields"""
        for preset_key, preset_data in EqualizerPreset.PRESETS.items():
            self.assertIn('name', preset_data)
            self.assertIn('name_de', preset_data)
            self.assertIn('gains', preset_data)
            self.assertEqual(len(preset_data['gains']), 10)

    def test_get_state(self):
        """Test getting equalizer state"""
        self.manager.enabled = True
        self.manager.current_preset = 'rock'

        state = self.manager.get_state()

        self.assertIsInstance(state, dict)
        self.assertIn('enabled', state)
        self.assertIn('preset', state)
        self.assertIn('bands', state)
        self.assertEqual(state['enabled'], True)
        self.assertEqual(state['preset'], 'rock')


if __name__ == '__main__':
    unittest.main()
