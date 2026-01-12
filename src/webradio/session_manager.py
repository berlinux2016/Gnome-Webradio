"""
Session Manager for Gnome Web Radio

This module manages session state persistence for resume functionality.
"""

import json
import os
from typing import Optional, Dict
from pathlib import Path

from webradio.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """
    Manages session state for resuming playback.

    Stores the last played station, volume, and playback state
    to enable seamless resume on application restart.
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize session manager.

        Args:
            config_dir: Configuration directory path (default: ~/.config/webradio/)
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'webradio')

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.session_file = self.config_dir / 'session.json'

        logger.info(f"Session manager initialized: {self.session_file}")

    def save_session(self, station: Optional[Dict], volume: float, was_playing: bool):
        """
        Save current session state.

        Args:
            station: Current station dict (or None if stopped)
            volume: Current volume (0.0-1.0)
            was_playing: Whether the player was active
        """
        session_data = {
            'station': station,
            'volume': volume,
            'was_playing': was_playing
        }

        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Session saved: {station.get('name') if station else 'No station'}, "
                       f"volume={volume:.2f}, playing={was_playing}")

        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    def load_session(self) -> Optional[Dict]:
        """
        Load saved session state.

        Returns:
            dict: Session data with 'station', 'volume', 'was_playing' keys
                  or None if no session exists
        """
        if not self.session_file.exists():
            logger.info("No saved session found")
            return None

        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            logger.info(f"Session loaded: {session_data.get('station', {}).get('name', 'No station')}, "
                       f"volume={session_data.get('volume', 1.0):.2f}, "
                       f"was_playing={session_data.get('was_playing', False)}")

            return session_data

        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    def clear_session(self):
        """Clear saved session"""
        if self.session_file.exists():
            try:
                self.session_file.unlink()
                logger.info("Session cleared")
            except Exception as e:
                logger.error(f"Failed to clear session: {e}")

    def has_saved_session(self) -> bool:
        """
        Check if a saved session exists.

        Returns:
            bool: True if session file exists
        """
        return self.session_file.exists()


def create_session_manager(config_dir: Optional[str] = None) -> SessionManager:
    """
    Factory function to create a session manager.

    Args:
        config_dir: Configuration directory path

    Returns:
        SessionManager: Configured session manager
    """
    return SessionManager(config_dir)
