"""Station and media row components for WebRadio Player"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GdkPixbuf', '2.0')

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio
import threading
import requests
from typing import Dict, Optional, Callable
from webradio.logger import get_logger
from webradio.i18n import _

logger = get_logger(__name__)


class MusicTrackRow(Gtk.ListBoxRow):
    """Custom row for displaying a music track"""

    def __init__(self, track: Dict[str, any]):
        super().__init__()
        self.track = track

        # Main container
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Artist/Title
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_hexpand(True)

        # Track title
        title_label = Gtk.Label(label=track.get('title', 'Unknown'))
        title_label.set_xalign(0)
        title_label.set_wrap(False)
        title_label.set_ellipsize(3)  # ELLIPSIZE_END
        info_box.append(title_label)

        # Artist - Album
        artist_album = f"{track.get('artist', 'Unknown')} • {track.get('album', 'Unknown')}"
        details_label = Gtk.Label(label=artist_album)
        details_label.set_xalign(0)
        details_label.set_opacity(0.7)
        info_box.append(details_label)

        box.append(info_box)

        # Duration
        duration = track.get('duration', 0)
        mins = duration // 60
        secs = duration % 60
        duration_label = Gtk.Label(label=f"{mins}:{secs:02d}")
        duration_label.set_opacity(0.7)
        box.append(duration_label)

        self.set_child(box)


class YouTubeVideoRow(Gtk.ListBoxRow):
    """Custom row for displaying a YouTube video"""

    def __init__(self, video: Dict[str, any]):
        super().__init__()
        self.video = video

        # Main container - same spacing as radio stations
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Thumbnail - same size as radio station logo (48px)
        self.thumbnail = Gtk.Image()
        self.thumbnail.set_pixel_size(48)
        self.thumbnail.set_from_icon_name('multimedia-player-symbolic')
        box.append(self.thumbnail)

        # Load thumbnail asynchronously if URL is available
        thumbnail_url = video.get('thumbnail', '')
        if thumbnail_url:
            self._load_thumbnail_async(thumbnail_url)

        # Video info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_hexpand(True)

        # Title
        title_label = Gtk.Label(label=video.get('title', 'Unknown'))
        title_label.set_xalign(0)
        title_label.set_wrap(False)
        title_label.set_ellipsize(3)  # ELLIPSIZE_END
        info_box.append(title_label)

        # Channel
        channel_label = Gtk.Label(label=video.get('channel', 'Unknown'))
        channel_label.set_xalign(0)
        channel_label.set_opacity(0.7)
        info_box.append(channel_label)

        box.append(info_box)

        # Duration - fixed width to align with header
        duration = int(video.get('duration', 0))
        duration_label = Gtk.Label()
        duration_label.set_xalign(0)
        duration_label.set_opacity(0.7)
        duration_label.set_size_request(60, -1)
        if duration > 0:
            mins = duration // 60
            secs = duration % 60
            duration_label.set_label(f"{mins}:{secs:02d}")
        else:
            duration_label.set_label("")
        box.append(duration_label)

        self.set_child(box)

    def _load_thumbnail_async(self, url: str):
        """Load thumbnail image asynchronously from URL"""
        import urllib.request

        def download_and_set():
            try:
                logger.debug(f"Loading YouTube thumbnail from: {url}")

                # Download thumbnail with user agent to avoid blocks
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                response = urllib.request.urlopen(req, timeout=10)
                data = response.read()

                logger.debug(f"Downloaded {len(data)} bytes for YouTube thumbnail")

                # Load into pixbuf
                input_stream = Gio.MemoryInputStream.new_from_data(data, None)
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream(input_stream, None)

                # Scale thumbnail to 48x48 to match radio station logos
                target_size = 48

                orig_width = pixbuf.get_width()
                orig_height = pixbuf.get_height()

                # Calculate scale to fit within 48x48 while maintaining aspect ratio
                scale = min(target_size / orig_width, target_size / orig_height)
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)

                scaled_pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)

                logger.debug(f"Scaled YouTube thumbnail from {orig_width}x{orig_height} to {new_width}x{new_height}")

                # Set image in main thread using Gdk.Texture (GTK4 way)
                def set_thumbnail():
                    texture = Gdk.Texture.new_for_pixbuf(scaled_pixbuf)
                    self.thumbnail.set_from_paintable(texture)
                    return False

                GLib.idle_add(set_thumbnail)

            except Exception as e:
                logger.warning(f"Failed to load YouTube thumbnail from {url}: {e}")
                # Keep default icon on error

        threading.Thread(target=download_and_set, daemon=True).start()


class StationRow(Gtk.ListBoxRow):
    """Custom row for displaying a radio station"""

    def __init__(
        self,
        station: Dict[str, any],
        is_favorite: bool = False,
        on_delete_favorite: Optional[Callable] = None
    ):
        super().__init__()
        self.station = station
        self.is_favorite = is_favorite
        self.on_delete_favorite = on_delete_favorite

        # Setup right-click menu for favorites
        if is_favorite and on_delete_favorite:
            self._setup_context_menu()

        # Main container
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Station logo
        self.logo_image = Gtk.Image()
        self.logo_image.set_pixel_size(48)
        self.logo_image.set_from_icon_name('audio-x-generic')
        box.append(self.logo_image)

        # Station info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_hexpand(True)

        # Station name
        name_label = Gtk.Label(label=station.get('name', 'Unknown'))
        name_label.set_xalign(0)
        name_label.set_wrap(False)
        name_label.set_ellipsize(3)  # ELLIPSIZE_END
        info_box.append(name_label)

        # Station details
        details = []
        if station.get('country'):
            details.append(station['country'])
        if station.get('codec'):
            details.append(station['codec'].upper())
        if station.get('bitrate'):
            details.append(f"{station['bitrate']}kbps")

        if details:
            details_label = Gtk.Label(label=' • '.join(details))
            details_label.set_xalign(0)
            details_label.set_opacity(0.7)
            info_box.append(details_label)

        box.append(info_box)

        # Favorite indicator
        if is_favorite:
            fav_icon = Gtk.Image.new_from_icon_name('starred')
            fav_icon.add_css_class('accent')
            box.append(fav_icon)

        self.set_child(box)

        # Load station logo asynchronously
        if station.get('favicon'):
            threading.Thread(target=self._load_logo, args=(station['favicon'],), daemon=True).start()

    def _load_logo(self, url: str):
        """Load station logo from URL"""
        try:
            logger.debug(f"Loading station logo from: {url}")
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                GLib.idle_add(self._set_logo_from_data, response.content)
        except Exception as e:
            logger.debug(f"Failed to load station logo: {e}")

    def _set_logo_from_data(self, image_data: bytes):
        """Set logo from image data"""
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(image_data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf:
                scaled = pixbuf.scale_simple(48, 48, GdkPixbuf.InterpType.BILINEAR)
                texture = Gdk.Texture.new_for_pixbuf(scaled)
                self.logo_image.set_from_paintable(texture)
                logger.debug("Station logo loaded successfully")
        except Exception as e:
            logger.debug(f"Failed to set station logo: {e}")

    def _setup_context_menu(self):
        """Setup right-click context menu for favorites"""
        # Create gesture for right-click
        gesture = Gtk.GestureClick.new()
        gesture.set_button(3)  # Right mouse button
        gesture.connect("pressed", self._on_right_click)
        self.add_controller(gesture)

    def _on_right_click(self, gesture, n_press: int, x: float, y: float):
        """Handle right-click on favorite station"""
        # Create popover menu
        menu = Gio.Menu()
        menu.append(_('context_delete_favorite'), "row.delete")

        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        popover.set_parent(self)
        popover.set_pointing_to(Gdk.Rectangle())
        popover.set_has_arrow(True)

        # Create action
        delete_action = Gio.SimpleAction.new("delete", None)
        delete_action.connect("activate", lambda a, p: self._delete_favorite())

        action_group = Gio.SimpleActionGroup()
        action_group.add_action(delete_action)
        self.insert_action_group("row", action_group)

        popover.popup()

    def _delete_favorite(self):
        """Delete this favorite station"""
        if self.on_delete_favorite:
            logger.info(f"Deleting favorite station: {self.station.get('name')}")
            self.on_delete_favorite(self.station)
