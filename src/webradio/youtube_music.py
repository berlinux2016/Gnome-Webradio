"""YouTube integration using yt-dlp"""

import subprocess
import json
from typing import List, Dict, Optional


class YouTubeMusic:
    """YouTube search and streaming handler"""

    def __init__(self):
        """Initialize YouTube handler"""
        self.ytdlp_available = self._check_ytdlp()

    def _check_ytdlp(self) -> bool:
        """Check if yt-dlp is available"""
        try:
            result = subprocess.run(
                ['yt-dlp', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Search YouTube for videos

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of video dictionaries with title, url, duration, thumbnail, etc.
        """
        if not self.ytdlp_available:
            print("yt-dlp is not available")
            return []

        try:
            # Use ytsearch to search YouTube
            search_query = f"ytsearch{max_results}:{query} music"
            print(f"YouTube search query: {search_query}")

            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-playlist',
                '--flat-playlist',
                '--skip-download',
                '--no-warnings',
                search_query
            ]

            print(f"Running command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            print(f"yt-dlp returncode: {result.returncode}")

            if result.returncode != 0:
                print(f"yt-dlp search failed: {result.stderr}")
                return []

            # Parse JSON output (one JSON object per line)
            videos = []
            lines = result.stdout.strip().split('\n')
            print(f"Got {len(lines)} lines of output")

            for line in lines:
                if line:
                    try:
                        video_data = json.loads(line)
                        video_id = video_data.get('id', '')

                        if not video_id:
                            print(f"Warning: No video ID found in: {line[:100]}")
                            continue

                        # Always construct thumbnail URL from video ID for consistency
                        # YouTube provides multiple thumbnail sizes:
                        # - hqdefault.jpg = 480x360 (high quality)
                        # - mqdefault.jpg = 320x180 (medium quality)
                        # - sddefault.jpg = 640x480 (standard definition)
                        # - maxresdefault.jpg = 1920x1080 (maximum resolution, may not exist)
                        # Use sddefault for better quality (640x480)
                        thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg"

                        video_info = {
                            'id': video_id,
                            'title': video_data.get('title', 'Unknown'),
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'duration': video_data.get('duration', 0),
                            'thumbnail': thumbnail_url,
                            'channel': video_data.get('uploader', 'Unknown'),
                            'view_count': video_data.get('view_count', 0),
                        }
                        videos.append(video_info)
                        print(f"Added video: {video_info['title']}")

                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e} for line: {line[:100]}")
                        continue

            print(f"Returning {len(videos)} videos")
            return videos

        except subprocess.TimeoutExpired:
            print("yt-dlp search timed out")
            return []
        except Exception as e:
            print(f"YouTube search error: {e}")
            return []

    def get_audio_url(self, video_url: str) -> Optional[str]:
        """
        Get direct audio stream URL from YouTube video

        Args:
            video_url: YouTube video URL

        Returns:
            Direct audio stream URL or None if failed
        """
        if not self.ytdlp_available:
            return None

        try:
            cmd = [
                'yt-dlp',
                '--format', 'bestaudio/best',
                '--get-url',
                '--no-playlist',
                '--no-warnings',
                video_url
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                audio_url = result.stdout.strip()
                return audio_url if audio_url else None
            else:
                print(f"Failed to get audio URL: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("yt-dlp get-url timed out")
            return None
        except Exception as e:
            print(f"Error getting audio URL: {e}")
            return None

    def get_video_info(self, video_url: str) -> Optional[Dict]:
        """
        Get detailed information about a YouTube video

        Args:
            video_url: YouTube video URL

        Returns:
            Dictionary with video information or None
        """
        if not self.ytdlp_available:
            return None

        try:
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-playlist',
                '--no-warnings',
                video_url
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                video_data = json.loads(result.stdout)
                return {
                    'id': video_data.get('id', ''),
                    'title': video_data.get('title', 'Unknown'),
                    'url': video_url,
                    'duration': video_data.get('duration', 0),
                    'thumbnail': video_data.get('thumbnail', ''),
                    'channel': video_data.get('uploader', 'Unknown'),
                    'description': video_data.get('description', ''),
                    'view_count': video_data.get('view_count', 0),
                }
            else:
                return None

        except Exception as e:
            print(f"Error getting video info: {e}")
            return None

    def format_duration(self, seconds: int) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS"""
        if seconds < 0:
            return "0:00"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"

    def is_available(self) -> bool:
        """Check if YouTube functionality is available"""
        return self.ytdlp_available
