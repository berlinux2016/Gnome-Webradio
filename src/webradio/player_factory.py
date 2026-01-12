"""Player factory to choose between simple and advanced player"""

from webradio.logger import get_logger

logger = get_logger(__name__)


def create_player(use_advanced=True):
    """
    Create appropriate player instance

    Args:
        use_advanced: If True, try to use advanced player with equalizer/recording
                     If False or if advanced fails, use simple player

    Returns:
        Player instance (AdvancedAudioPlayer or AudioPlayer)
    """
    if use_advanced:
        try:
            from webradio.player_advanced import AdvancedAudioPlayer
            logger.info("Using advanced player with equalizer and recording support")
            return AdvancedAudioPlayer()
        except Exception as e:
            logger.warning(f"Failed to create advanced player, falling back to simple player: {e}")

    # Fallback to simple player
    from webradio.player import AudioPlayer
    logger.info("Using simple player (no equalizer/recording)")
    return AudioPlayer()
