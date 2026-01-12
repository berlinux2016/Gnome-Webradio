"""Custom exceptions for WebRadio Player"""


class WebRadioException(Exception):
    """Base exception for all WebRadio errors"""
    pass


class PlayerException(WebRadioException):
    """Base exception for player-related errors"""
    pass


class PlaybackException(PlayerException):
    """Exception raised when playback fails"""
    pass


class StreamNotFoundException(PlaybackException):
    """Exception raised when stream URL is not found or invalid"""
    pass


class AudioDeviceException(PlayerException):
    """Exception raised when audio device is not available"""
    pass


class EqualizerException(PlayerException):
    """Exception raised when equalizer operation fails"""
    pass


class RecordingException(WebRadioException):
    """Base exception for recording-related errors"""
    pass


class RecordingAlreadyActiveException(RecordingException):
    """Exception raised when trying to start recording while already recording"""
    pass


class RecordingNotActiveException(RecordingException):
    """Exception raised when trying to stop recording when not recording"""
    pass


class RecordingFormatException(RecordingException):
    """Exception raised when recording format is not supported"""
    pass


class RecordingFileException(RecordingException):
    """Exception raised when recording file cannot be created or written"""
    pass


class NetworkException(WebRadioException):
    """Exception raised for network-related errors"""
    pass


class APIException(NetworkException):
    """Exception raised when API request fails"""
    pass


class StationNotFoundException(APIException):
    """Exception raised when station is not found"""
    pass


class FavoritesException(WebRadioException):
    """Exception raised for favorites management errors"""
    pass


class HistoryException(WebRadioException):
    """Exception raised for history management errors"""
    pass


class ConfigurationException(WebRadioException):
    """Exception raised for configuration errors"""
    pass


class YouTubeException(WebRadioException):
    """Exception raised for YouTube-related errors"""
    pass


class YouTubeNotAvailableException(YouTubeException):
    """Exception raised when yt-dlp is not available"""
    pass


class YouTubeSearchException(YouTubeException):
    """Exception raised when YouTube search fails"""
    pass


class YouTubeStreamException(YouTubeException):
    """Exception raised when YouTube stream URL cannot be obtained"""
    pass
