"""Equalizer manager for audio control"""

from typing import Dict, List, Optional
from gi.repository import Gio
from webradio.logger import get_logger

logger = get_logger(__name__)


class EqualizerPreset:
    """Equalizer preset definitions"""

    # Frequency bands: 31Hz, 62Hz, 125Hz, 250Hz, 500Hz, 1kHz, 2kHz, 4kHz, 8kHz, 16kHz
    PRESETS = {
        'flat': {
            'name': 'Flat',
            'name_de': 'Flach',
            'gains': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        },
        'rock': {
            'name': 'Rock',
            'name_de': 'Rock',
            'gains': [4.0, 3.0, -2.0, -3.0, -1.0, 2.0, 4.0, 5.0, 5.0, 5.0]
        },
        'pop': {
            'name': 'Pop',
            'name_de': 'Pop',
            'gains': [-1.0, -1.0, 0.0, 2.0, 4.0, 4.0, 2.0, 0.0, -1.0, -1.0]
        },
        'jazz': {
            'name': 'Jazz',
            'name_de': 'Jazz',
            'gains': [3.0, 2.0, 1.0, 2.0, -1.0, -1.0, 0.0, 1.0, 2.0, 3.0]
        },
        'classical': {
            'name': 'Classical',
            'name_de': 'Klassisch',
            'gains': [4.0, 3.0, 2.0, 0.0, -1.0, -1.0, 0.0, 2.0, 3.0, 4.0]
        },
        'speech': {
            'name': 'Speech',
            'name_de': 'Sprache',
            'gains': [-3.0, -2.0, -1.0, 1.0, 3.0, 4.0, 4.0, 3.0, 1.0, 0.0]
        },
        'bass-boost': {
            'name': 'Bass Boost',
            'name_de': 'Bass Boost',
            'gains': [6.0, 5.0, 4.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        },
        'treble-boost': {
            'name': 'Treble Boost',
            'name_de': 'Höhen Boost',
            'gains': [0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 4.0, 5.0, 6.0, 6.0]
        },
        'custom': {
            'name': 'Custom',
            'name_de': 'Benutzerdefiniert',
            'gains': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        },
    }

    BAND_FREQUENCIES = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    BAND_LABELS = ['31 Hz', '62 Hz', '125 Hz', '250 Hz', '500 Hz', '1 kHz', '2 kHz', '4 kHz', '8 kHz', '16 kHz']


class EqualizerManager:
    """Manage equalizer settings and presets"""

    def __init__(self, player=None, settings: Optional[Gio.Settings] = None):
        self.player = player
        self.settings = settings
        self.current_preset = 'flat'
        self.enabled = False
        self.custom_gains = [0.0] * 10

        # Load from settings
        if self.settings:
            self._load_from_settings()

    def _load_from_settings(self):
        """Load equalizer state from GSettings"""
        if not self.settings:
            return

        try:
            self.enabled = self.settings.get_boolean('equalizer-enabled')
            self.current_preset = self.settings.get_string('equalizer-preset')

            # Load custom preset bands
            for i in range(10):
                self.custom_gains[i] = self.settings.get_double(f'equalizer-band{i}')

        except Exception as e:
            logger.error(f"Error loading equalizer settings: {e}")

    def _save_to_settings(self):
        """Save equalizer state to GSettings"""
        if not self.settings:
            return

        try:
            self.settings.set_boolean('equalizer-enabled', self.enabled)
            self.settings.set_string('equalizer-preset', self.current_preset)

            # Save custom preset bands
            for i in range(10):
                self.settings.set_double(f'equalizer-band{i}', self.custom_gains[i])

        except Exception as e:
            logger.error(f"Error saving equalizer settings: {e}")

    def set_enabled(self, enabled: bool) -> bool:
        """Enable or disable equalizer"""
        self.enabled = enabled

        if self.player:
            success = self.player.set_equalizer_enabled(enabled)
            if success and enabled:
                # Apply current preset when enabling
                self.apply_preset(self.current_preset)
        else:
            success = True

        if success:
            self._save_to_settings()

        return success

    def is_enabled(self) -> bool:
        """Check if equalizer is enabled"""
        return self.enabled

    def get_presets(self) -> List[str]:
        """Get list of available preset names"""
        return list(EqualizerPreset.PRESETS.keys())

    def get_preset_display_name(self, preset_key: str, language: str = 'en') -> str:
        """Get localized display name for preset"""
        if preset_key not in EqualizerPreset.PRESETS:
            return preset_key

        preset = EqualizerPreset.PRESETS[preset_key]
        if language == 'de':
            return preset.get('name_de', preset['name'])
        return preset['name']

    def apply_preset(self, preset_key: str) -> bool:
        """Apply an equalizer preset"""
        if preset_key not in EqualizerPreset.PRESETS:
            logger.warning(f"Unknown preset: {preset_key}")
            return False

        preset = EqualizerPreset.PRESETS[preset_key]
        gains = preset['gains']

        # If custom preset, use saved custom gains
        if preset_key == 'custom':
            gains = self.custom_gains

        # Apply to player
        if self.player and self.enabled:
            for i, gain in enumerate(gains):
                self.player.set_equalizer_band(i, gain)

        self.current_preset = preset_key
        self._save_to_settings()

        logger.info(f"Applied equalizer preset: {preset_key}")
        return True

    def get_current_preset(self) -> str:
        """Get currently active preset"""
        return self.current_preset

    def set_band(self, band: int, gain: float) -> bool:
        """Set individual band gain (-24.0 to +12.0 dB)"""
        if not 0 <= band < 10:
            return False

        # Clamp gain
        gain = max(-24.0, min(12.0, gain))

        # Update custom gains
        self.custom_gains[band] = gain

        # Apply to player
        if self.player and self.enabled:
            success = self.player.set_equalizer_band(band, gain)
        else:
            success = True

        # If we modified a band, switch to custom preset
        if success and self.current_preset != 'custom':
            self.current_preset = 'custom'

        self._save_to_settings()
        return success

    def get_band(self, band: int) -> float:
        """Get individual band gain"""
        if not 0 <= band < 10:
            return 0.0

        if self.player:
            return self.player.get_equalizer_band(band)

        # Fallback to saved value
        if self.current_preset == 'custom':
            return self.custom_gains[band]
        else:
            preset = EqualizerPreset.PRESETS.get(self.current_preset, EqualizerPreset.PRESETS['flat'])
            return preset['gains'][band]

    def get_all_bands(self) -> List[float]:
        """Get all band gains"""
        return [self.get_band(i) for i in range(10)]

    def reset_to_flat(self) -> bool:
        """Reset all bands to flat (0 dB)"""
        return self.apply_preset('flat')

    def save_custom_preset(self) -> bool:
        """Save current bands as custom preset"""
        if self.player:
            # Read current values from player
            for i in range(10):
                self.custom_gains[i] = self.player.get_equalizer_band(i)

        self.current_preset = 'custom'
        self._save_to_settings()
        logger.info("Saved custom equalizer preset")
        return True

    def get_band_frequency(self, band: int) -> int:
        """Get frequency for band index"""
        if 0 <= band < 10:
            return EqualizerPreset.BAND_FREQUENCIES[band]
        return 0

    def get_band_label(self, band: int) -> str:
        """Get label for band index"""
        if 0 <= band < 10:
            return EqualizerPreset.BAND_LABELS[band]
        return ''

    def get_state(self) -> Dict:
        """Get complete equalizer state"""
        return {
            'enabled': self.enabled,
            'preset': self.current_preset,
            'bands': self.get_all_bands(),
            'custom_gains': self.custom_gains.copy()
        }

    def set_state(self, state: Dict) -> bool:
        """Restore equalizer state"""
        try:
            if 'enabled' in state:
                self.set_enabled(state['enabled'])

            if 'preset' in state:
                self.apply_preset(state['preset'])

            if 'custom_gains' in state:
                self.custom_gains = state['custom_gains'].copy()

            return True

        except Exception as e:
            logger.error(f"Error restoring equalizer state: {e}")
            return False
