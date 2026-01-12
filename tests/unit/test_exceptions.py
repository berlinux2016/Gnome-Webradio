"""Unit tests for exceptions module"""

import unittest
from webradio.exceptions import (
    WebRadioException,
    PlayerException,
    PlaybackException,
    StreamNotFoundException,
    RecordingException,
    RecordingAlreadyActiveException,
    NetworkException,
    APIException,
    YouTubeException
)


class TestExceptions(unittest.TestCase):
    """Test custom exceptions"""

    def test_base_exception(self):
        """Test base WebRadioException"""
        with self.assertRaises(WebRadioException):
            raise WebRadioException("Test error")

    def test_player_exception_hierarchy(self):
        """Test player exception hierarchy"""
        # PlaybackException should be a PlayerException
        self.assertTrue(issubclass(PlaybackException, PlayerException))

        # PlayerException should be a WebRadioException
        self.assertTrue(issubclass(PlayerException, WebRadioException))

        # StreamNotFoundException should be a PlaybackException
        self.assertTrue(issubclass(StreamNotFoundException, PlaybackException))

    def test_recording_exception_hierarchy(self):
        """Test recording exception hierarchy"""
        # RecordingAlreadyActiveException should be a RecordingException
        self.assertTrue(issubclass(RecordingAlreadyActiveException, RecordingException))

        # RecordingException should be a WebRadioException
        self.assertTrue(issubclass(RecordingException, WebRadioException))

    def test_network_exception_hierarchy(self):
        """Test network exception hierarchy"""
        # APIException should be a NetworkException
        self.assertTrue(issubclass(APIException, NetworkException))

        # NetworkException should be a WebRadioException
        self.assertTrue(issubclass(NetworkException, WebRadioException))

    def test_youtube_exception_hierarchy(self):
        """Test YouTube exception hierarchy"""
        # YouTubeException should be a WebRadioException
        self.assertTrue(issubclass(YouTubeException, WebRadioException))

    def test_exception_messages(self):
        """Test exception messages"""
        error_msg = "Custom error message"

        try:
            raise PlaybackException(error_msg)
        except PlaybackException as e:
            self.assertEqual(str(e), error_msg)


if __name__ == '__main__':
    unittest.main()
