"""Local music library manager for WebRadio Player"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
import threading
from mutagen import File as MutagenFile
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4


class MusicLibrary:
    """Manages local music files and metadata"""

    SUPPORTED_FORMATS = {'.mp3', '.flac', '.ogg', '.oga', '.m4a', '.aac', '.opus', '.wav'}

    def __init__(self, config_dir: str = None):
        """Initialize music library"""
        if config_dir is None:
            config_dir = os.path.join(Path.home(), '.config', 'webradio')

        self.config_dir = config_dir
        self.library_file = os.path.join(config_dir, 'music_library.json')
        self.music_paths = []
        self.tracks = []
        self.is_scanning = False
        self._load_library()

    def _load_library(self):
        """Load library from cache file"""
        if os.path.exists(self.library_file):
            try:
                with open(self.library_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.music_paths = data.get('paths', [])
                    self.tracks = data.get('tracks', [])
                    print(f"Loaded {len(self.tracks)} tracks from library")
            except Exception as e:
                print(f"Error loading library: {e}")

    def _save_library(self):
        """Save library to cache file"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            data = {
                'paths': self.music_paths,
                'tracks': self.tracks
            }
            with open(self.library_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(self.tracks)} tracks to library")
        except Exception as e:
            print(f"Error saving library: {e}")

    def add_music_path(self, path: str):
        """Add a directory to scan for music"""
        if path not in self.music_paths:
            self.music_paths.append(path)
            self._save_library()

    def remove_music_path(self, path: str):
        """Remove a directory from the library"""
        if path in self.music_paths:
            self.music_paths.remove(path)
            # Remove tracks from this path
            self.tracks = [t for t in self.tracks if not t['path'].startswith(path)]
            self._save_library()

    def scan_library(self, callback=None):
        """Scan all music paths for files"""
        if self.is_scanning:
            print("Scan already in progress")
            return

        def scan():
            self.is_scanning = True
            self.tracks = []
            total_files = 0

            try:
                for music_path in self.music_paths:
                    if not os.path.exists(music_path):
                        print(f"Path does not exist: {music_path}")
                        continue

                    print(f"Scanning: {music_path}")

                    for root, dirs, files in os.walk(music_path):
                        for file in files:
                            if Path(file).suffix.lower() in self.SUPPORTED_FORMATS:
                                file_path = os.path.join(root, file)
                                track = self._extract_metadata(file_path)
                                if track:
                                    self.tracks.append(track)
                                    total_files += 1

                                    if callback and total_files % 10 == 0:
                                        callback(total_files)

                print(f"Scan complete: {total_files} tracks found")
                self._save_library()

                if callback:
                    callback(total_files, done=True)

            except Exception as e:
                print(f"Error during scan: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.is_scanning = False

        threading.Thread(target=scan, daemon=True).start()

    def _extract_metadata(self, file_path: str) -> Optional[Dict]:
        """Extract metadata from audio file"""
        try:
            audio = MutagenFile(file_path, easy=True)
            if audio is None:
                return None

            # Get file stats
            stats = os.stat(file_path)
            duration = getattr(audio.info, 'length', 0)

            # Extract tags
            def get_tag(key, default='Unknown'):
                value = audio.get(key, [default])
                return value[0] if isinstance(value, list) else value

            track = {
                'path': file_path,
                'filename': os.path.basename(file_path),
                'title': get_tag('title', os.path.splitext(os.path.basename(file_path))[0]),
                'artist': get_tag('artist', 'Unknown Artist'),
                'album': get_tag('album', 'Unknown Album'),
                'album_artist': get_tag('albumartist', get_tag('artist', 'Unknown Artist')),
                'genre': get_tag('genre', ''),
                'date': get_tag('date', ''),
                'track_number': get_tag('tracknumber', ''),
                'duration': int(duration),
                'bitrate': getattr(audio.info, 'bitrate', 0),
                'file_size': stats.st_size,
                'modified': stats.st_mtime
            }

            return track

        except Exception as e:
            print(f"Error reading metadata from {file_path}: {e}")
            return None

    def get_all_tracks(self) -> List[Dict]:
        """Get all tracks in library"""
        return self.tracks

    def get_tracks_by_artist(self, artist: str) -> List[Dict]:
        """Get tracks by artist"""
        return [t for t in self.tracks if t['artist'].lower() == artist.lower()]

    def get_tracks_by_album(self, album: str) -> List[Dict]:
        """Get tracks by album"""
        return [t for t in self.tracks if t['album'].lower() == album.lower()]

    def get_all_artists(self) -> List[str]:
        """Get list of all artists"""
        artists = set(t['artist'] for t in self.tracks)
        return sorted(list(artists))

    def get_all_albums(self) -> List[Dict]:
        """Get list of all albums with metadata"""
        albums = {}
        for track in self.tracks:
            album_key = (track['album'], track['album_artist'])
            if album_key not in albums:
                albums[album_key] = {
                    'album': track['album'],
                    'artist': track['album_artist'],
                    'date': track['date'],
                    'tracks': []
                }
            albums[album_key]['tracks'].append(track)

        # Sort albums by name
        return sorted(albums.values(), key=lambda x: x['album'].lower())

    def search_tracks(self, query: str) -> List[Dict]:
        """Search tracks by title, artist, or album"""
        query_lower = query.lower()
        results = []

        for track in self.tracks:
            if (query_lower in track['title'].lower() or
                query_lower in track['artist'].lower() or
                query_lower in track['album'].lower()):
                results.append(track)

        return results

    def get_track_count(self) -> int:
        """Get total number of tracks"""
        return len(self.tracks)

    def get_library_stats(self) -> Dict:
        """Get library statistics"""
        if not self.tracks:
            return {
                'total_tracks': 0,
                'total_artists': 0,
                'total_albums': 0,
                'total_duration': 0,
                'total_size': 0
            }

        return {
            'total_tracks': len(self.tracks),
            'total_artists': len(self.get_all_artists()),
            'total_albums': len(self.get_all_albums()),
            'total_duration': sum(t['duration'] for t in self.tracks),
            'total_size': sum(t['file_size'] for t in self.tracks)
        }
