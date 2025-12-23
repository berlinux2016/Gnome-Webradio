"""Stream recorder for saving radio streams to files"""

from typing import Optional
from pathlib import Path
from datetime import datetime
import os
from gi.repository import Gio, GObject


class RecordingFormat:
    """Recording format definitions"""

    FORMATS = {
        'wav': {
            'name': 'WAV (Uncompressed)',
            'extension': 'wav',
            'encoder': 'wavenc',
            'quality': 'lossless',
            'description': 'Uncompressed audio, large files'
        },
        'mp3': {
            'name': 'MP3 (320 kbps)',
            'extension': 'mp3',
            'encoder': 'lamemp3enc',
            'quality': 'high',
            'description': 'Compressed, good quality, smaller files'
        },
        'flac': {
            'name': 'FLAC (Lossless)',
            'extension': 'flac',
            'encoder': 'flacenc',
            'quality': 'lossless',
            'description': 'Lossless compression, medium file size'
        },
        'ogg': {
            'name': 'OGG Vorbis (Quality 6)',
            'extension': 'ogg',
            'encoder': 'vorbisenc',
            'quality': 'high',
            'description': 'Open format, good quality'
        }
    }


class StreamRecorder(GObject.Object):
    """Manage stream recording"""

    __gsignals__ = {
        'recording-started': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'recording-stopped': (GObject.SignalFlags.RUN_FIRST, None, (str, int)),  # path, duration
        'recording-error': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, player=None, settings: Optional[Gio.Settings] = None):
        super().__init__()
        self.player = player
        self.settings = settings

        # Recording state
        self.is_recording = False
        self.current_file = None
        self.start_time = None
        self.station_info = None

        # Settings
        self.output_format = 'mp3'
        self.output_directory = self._get_default_directory()
        self.filename_template = '{station}_{date}_{time}'
        self.auto_start = False

        # Load settings
        if self.settings:
            self._load_settings()

    def _load_settings(self):
        """Load recorder settings from GSettings"""
        if not self.settings:
            return

        try:
            self.output_format = self.settings.get_string('recording-format')
            self.filename_template = self.settings.get_string('recording-filename-template')
            self.auto_start = self.settings.get_boolean('recording-auto-start')

            # Get output directory (empty = default)
            dir_path = self.settings.get_string('recording-directory')
            if dir_path:
                self.output_directory = Path(dir_path)
            else:
                self.output_directory = self._get_default_directory()

        except Exception as e:
            print(f"Error loading recorder settings: {e}")

    def _save_settings(self):
        """Save recorder settings to GSettings"""
        if not self.settings:
            return

        try:
            self.settings.set_string('recording-format', self.output_format)
            self.settings.set_string('recording-filename-template', self.filename_template)
            self.settings.set_string('recording-directory', str(self.output_directory))
            self.settings.set_boolean('recording-auto-start', self.auto_start)

        except Exception as e:
            print(f"Error saving recorder settings: {e}")

    def _get_default_directory(self) -> Path:
        """Get default recording directory"""
        # Try to get user's Music directory
        music_dir = Path.home() / 'Music'

        # Create Recordings subdirectory
        recordings_dir = music_dir / 'Recordings'

        return recordings_dir

    def _ensure_output_directory(self) -> bool:
        """Ensure output directory exists"""
        try:
            self.output_directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating output directory: {e}")
            return False

    def set_output_directory(self, directory: str) -> bool:
        """Set output directory for recordings"""
        try:
            path = Path(directory)
            self.output_directory = path
            self._save_settings()
            return True
        except Exception as e:
            print(f"Error setting output directory: {e}")
            return False

    def get_output_directory(self) -> str:
        """Get current output directory"""
        return str(self.output_directory)

    def set_format(self, format_key: str) -> bool:
        """Set recording format"""
        if format_key not in RecordingFormat.FORMATS:
            print(f"Unknown format: {format_key}")
            return False

        self.output_format = format_key
        self._save_settings()
        return True

    def get_format(self) -> str:
        """Get current recording format"""
        return self.output_format

    def get_available_formats(self):
        """Get list of available formats"""
        return RecordingFormat.FORMATS

    def _generate_filename(self, station_info: dict, metadata: dict = None) -> str:
        """Generate filename from template"""
        now = datetime.now()

        # Sanitize station name
        station_name = station_info.get('name', 'Unknown Station')
        station_name = self._sanitize_filename(station_name)

        # Get metadata if available
        title = ''
        artist = ''
        if metadata:
            title = self._sanitize_filename(metadata.get('title', ''))
            artist = self._sanitize_filename(metadata.get('artist', ''))

        # Build filename from template
        filename = self.filename_template
        filename = filename.replace('{station}', station_name)
        filename = filename.replace('{date}', now.strftime('%Y-%m-%d'))
        filename = filename.replace('{time}', now.strftime('%H-%M-%S'))
        filename = filename.replace('{title}', title)
        filename = filename.replace('{artist}', artist)

        # Add extension
        extension = RecordingFormat.FORMATS[self.output_format]['extension']
        filename = f"{filename}.{extension}"

        return filename

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename by removing invalid characters"""
        # Remove or replace invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r']
        sanitized = name

        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')

        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip('. ')

        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]

        return sanitized or 'recording'

    def start_recording(self, station_info: dict, metadata: dict = None) -> bool:
        """Start recording current stream"""
        if self.is_recording:
            print("Already recording")
            return False

        if not self.player or not self.player.is_playing():
            error = "Cannot record when not playing"
            print(error)
            self.emit('recording-error', error)
            return False

        # Ensure output directory exists
        if not self._ensure_output_directory():
            error = "Could not create output directory"
            self.emit('recording-error', error)
            return False

        try:
            # Generate filename
            filename = self._generate_filename(station_info, metadata)
            file_path = self.output_directory / filename

            # Make sure file doesn't exist (add number if it does)
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                extension = original_path.suffix
                file_path = original_path.parent / f"{stem}_{counter}{extension}"
                counter += 1

            # Start recording in player
            success = self.player.start_recording(str(file_path))

            if success:
                self.is_recording = True
                self.current_file = str(file_path)
                self.start_time = datetime.now()
                self.station_info = station_info

                self.emit('recording-started', self.current_file)
                print(f"Recording started: {self.current_file}")
                return True
            else:
                error = "Player failed to start recording"
                self.emit('recording-error', error)
                return False

        except Exception as e:
            error = f"Error starting recording: {e}"
            print(error)
            self.emit('recording-error', error)
            return False

    def stop_recording(self) -> bool:
        """Stop current recording"""
        if not self.is_recording:
            print("Not recording")
            return False

        try:
            # Stop recording in player
            success = self.player.stop_recording()

            if success:
                # Calculate duration
                duration = 0
                if self.start_time:
                    duration = int((datetime.now() - self.start_time).total_seconds())

                file_path = self.current_file

                self.is_recording = False
                self.current_file = None
                self.start_time = None
                self.station_info = None

                self.emit('recording-stopped', file_path, duration)
                print(f"Recording stopped: {file_path} ({duration}s)")
                return True
            else:
                error = "Player failed to stop recording"
                self.emit('recording-error', error)
                return False

        except Exception as e:
            error = f"Error stopping recording: {e}"
            print(error)
            self.emit('recording-error', error)
            return False

    def toggle_recording(self, station_info: dict = None, metadata: dict = None) -> bool:
        """Toggle recording on/off"""
        if self.is_recording:
            return self.stop_recording()
        else:
            if not station_info and self.player:
                station_info = self.player.get_current_station()
            if not metadata and self.player:
                metadata = self.player.get_current_tags()

            return self.start_recording(station_info or {}, metadata or {})

    def get_recording_duration(self) -> int:
        """Get current recording duration in seconds"""
        if not self.is_recording or not self.start_time:
            return 0

        return int((datetime.now() - self.start_time).total_seconds())

    def get_current_file(self) -> Optional[str]:
        """Get path of current recording file"""
        return self.current_file

    def is_recording_active(self) -> bool:
        """Check if currently recording"""
        return self.is_recording

    def set_filename_template(self, template: str) -> bool:
        """Set filename template"""
        self.filename_template = template
        self._save_settings()
        return True

    def get_filename_template(self) -> str:
        """Get filename template"""
        return self.filename_template

    def set_auto_start(self, enabled: bool) -> bool:
        """Set auto-start recording"""
        self.auto_start = enabled
        self._save_settings()
        return True

    def get_auto_start(self) -> bool:
        """Get auto-start setting"""
        return self.auto_start
