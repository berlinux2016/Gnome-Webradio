"""Player control bar component for WebRadio Player"""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk, Gio, GLib
from typing import Callable, Optional
from webradio.logger import get_logger
from webradio.i18n import _

logger = get_logger(__name__)


class PlayerBar(Gtk.Box):
    """Player control bar with station info, playback controls, and features"""

    def __init__(
        self,
        on_play_pause: Callable,
        on_stop: Callable,
        on_favorite_toggled: Callable,
        on_record_toggled: Callable,
        on_volume_changed: Callable,
        on_seek_changed: Callable,
        sleep_timer_presets: list,
        parent_window: Optional[Gtk.Window] = None
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.on_play_pause = on_play_pause
        self.on_stop = on_stop
        self.on_favorite_toggled = on_favorite_toggled
        self.on_record_toggled = on_record_toggled
        self.on_volume_changed = on_volume_changed
        self.on_seek_changed = on_seek_changed
        self.sleep_timer_presets = sleep_timer_presets
        self.parent_window = parent_window

        self.add_css_class('player-bar')
        self._build_ui()

        logger.debug("PlayerBar initialized")

    def _build_ui(self):
        """Build the player bar UI - Spotify style with 3 groups"""
        # No clamp - full width like Spotify
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        bar.set_margin_start(18)
        bar.set_margin_end(18)
        bar.set_margin_top(12)
        bar.set_margin_bottom(12)

        # GROUP 1: Station Info (left side, expanding)
        info_box = self._create_info_section()
        bar.append(info_box)

        # Seek bar (timeline) - between info and controls
        seek_box = self._create_seek_section()
        bar.append(seek_box)

        # GROUP 2: Playback Controls (center)
        controls_box = self._create_controls_section()
        bar.append(controls_box)

        # GROUP 3: Features + Volume (right side)
        features_box = self._create_features_section()
        bar.append(features_box)

        self.append(bar)

    def _create_info_section(self) -> Gtk.Box:
        """Create station info section (left side)"""
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        info_box.set_hexpand(True)

        # Logo (48px)
        self.playing_logo = Gtk.Image()
        self.playing_logo.set_pixel_size(48)
        self.playing_logo.set_from_icon_name('audio-x-generic')
        info_box.append(self.playing_logo)

        # Station Name + Metadata (vertical)
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        text_box.set_valign(Gtk.Align.CENTER)

        self.station_label = Gtk.Label(label=_('no_station_playing'))
        self.station_label.set_xalign(0)
        self.station_label.set_ellipsize(3)  # ELLIPSIZE_END
        self.station_label.add_css_class('heading')
        text_box.append(self.station_label)

        self.metadata_label = Gtk.Label(label='')
        self.metadata_label.set_xalign(0)
        self.metadata_label.set_ellipsize(3)
        self.metadata_label.set_opacity(0.5)
        text_box.append(self.metadata_label)

        info_box.append(text_box)
        return info_box

    def _create_seek_section(self) -> Gtk.Box:
        """Create seek bar section (timeline)"""
        seek_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        seek_box.set_hexpand(True)

        # Time labels container
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.current_time_label = Gtk.Label(label="0:00")
        self.current_time_label.set_xalign(0)
        self.current_time_label.set_opacity(0.7)
        time_box.append(self.current_time_label)

        # Spacer
        spacer = Gtk.Label()
        spacer.set_hexpand(True)
        time_box.append(spacer)

        self.total_time_label = Gtk.Label(label="0:00")
        self.total_time_label.set_xalign(1)
        self.total_time_label.set_opacity(0.7)
        time_box.append(self.total_time_label)

        # Seek scale
        self.seek_scale = Gtk.Scale()
        self.seek_scale.set_range(0, 100)
        self.seek_scale.set_value(0)
        self.seek_scale.set_draw_value(False)
        self.seek_scale.set_hexpand(True)
        self.seek_scale.connect('change-value', self._on_seek_internal)
        self.seek_scale.set_sensitive(False)

        seek_box.append(self.seek_scale)
        seek_box.append(time_box)
        return seek_box

    def _create_controls_section(self) -> Gtk.Box:
        """Create playback controls section (center)"""
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls_box.add_css_class('linked')

        # Favorite button
        self.fav_button = Gtk.ToggleButton()
        self.fav_button.set_icon_name('starred-symbolic')
        self.fav_button.set_tooltip_text(_('Add to favorites'))
        self.fav_button.connect('toggled', self._on_favorite_internal)
        self.fav_button.set_sensitive(False)
        controls_box.append(self.fav_button)

        # Play/Pause (suggested-action + circular)
        self.play_button = Gtk.Button()
        self.play_button.set_icon_name('media-playback-start-symbolic')
        self.play_button.set_tooltip_text(_('Play/Pause'))
        self.play_button.connect('clicked', self._on_play_pause_internal)
        self.play_button.add_css_class('suggested-action')
        self.play_button.add_css_class('circular')
        self.play_button.set_sensitive(False)
        controls_box.append(self.play_button)

        # Stop button
        self.stop_button = Gtk.Button()
        self.stop_button.set_icon_name('media-playback-stop-symbolic')
        self.stop_button.set_tooltip_text(_('Stop'))
        self.stop_button.connect('clicked', self._on_stop_internal)
        self.stop_button.set_sensitive(False)
        controls_box.append(self.stop_button)

        return controls_box

    def _create_features_section(self) -> Gtk.Box:
        """Create features section (right side) - record, sleep timer, volume"""
        features_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Record button
        self.record_button = Gtk.ToggleButton()
        self.record_button.set_icon_name('media-record-symbolic')
        self.record_button.set_tooltip_text(_('Record Stream'))
        self.record_button.connect('toggled', self._on_record_internal)
        self.record_button.set_sensitive(False)
        features_box.append(self.record_button)

        # Recording label (dynamically hidden)
        self.recording_label = Gtk.Label(label='')
        self.recording_label.add_css_class('error')
        self.recording_label.set_visible(False)
        features_box.append(self.recording_label)

        # Sleep timer
        self.sleep_button = Gtk.MenuButton()
        self.sleep_button.set_icon_name('alarm-symbolic')
        self.sleep_button.set_tooltip_text(_('Sleep Timer'))

        # Create sleep timer menu
        if self.parent_window:
            sleep_menu = Gio.Menu()
            for minutes in self.sleep_timer_presets:
                sleep_menu.append(f"{minutes} min", f"win.sleep-timer::{minutes}")
            sleep_menu.append(_("Stop Timer"), "win.sleep-timer-stop")
            self.sleep_button.set_menu_model(sleep_menu)

        features_box.append(self.sleep_button)

        # Volume button
        self.volume_button = Gtk.VolumeButton()
        self.volume_button.set_value(1.0)
        self.volume_button.connect('value-changed', self._on_volume_internal)
        features_box.append(self.volume_button)

        return features_box

    # Internal signal handlers that delegate to callbacks
    def _on_play_pause_internal(self, button):
        """Internal play/pause handler"""
        if self.on_play_pause:
            self.on_play_pause(button)

    def _on_stop_internal(self, button):
        """Internal stop handler"""
        if self.on_stop:
            self.on_stop(button)

    def _on_favorite_internal(self, button):
        """Internal favorite toggle handler"""
        if self.on_favorite_toggled:
            self.on_favorite_toggled(button)

    def _on_record_internal(self, button):
        """Internal record toggle handler"""
        if self.on_record_toggled:
            self.on_record_toggled(button)

    def _on_volume_internal(self, button, value):
        """Internal volume change handler"""
        if self.on_volume_changed:
            self.on_volume_changed(button, value)

    def _on_seek_internal(self, scale, scroll_type, value):
        """Internal seek change handler"""
        if self.on_seek_changed:
            return self.on_seek_changed(scale, scroll_type, value)
        return False

    # Public API for updating the player bar
    def set_station_info(self, station_name: str, metadata: str = ""):
        """Update station name and metadata"""
        self.station_label.set_label(station_name)
        self.metadata_label.set_label(metadata)
        self.metadata_label.set_visible(bool(metadata))

    def set_logo(self, pixbuf=None, icon_name: str = 'audio-x-generic'):
        """Update station logo"""
        if pixbuf:
            from gi.repository import Gdk
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            self.playing_logo.set_from_paintable(texture)
        else:
            self.playing_logo.set_from_icon_name(icon_name)

    def set_playing(self, is_playing: bool):
        """Update play button state"""
        if is_playing:
            self.play_button.set_icon_name('media-playback-pause-symbolic')
        else:
            self.play_button.set_icon_name('media-playback-start-symbolic')

    def set_controls_sensitive(self, sensitive: bool):
        """Enable/disable playback controls"""
        self.play_button.set_sensitive(sensitive)
        self.stop_button.set_sensitive(sensitive)
        self.fav_button.set_sensitive(sensitive)
        self.record_button.set_sensitive(sensitive)

    def set_favorite_state(self, is_favorite: bool):
        """Update favorite button state"""
        self.fav_button.set_active(is_favorite)

    def set_recording_state(self, is_recording: bool, duration_text: str = ""):
        """Update recording state"""
        self.record_button.set_active(is_recording)
        if is_recording:
            self.recording_label.set_label(f"● {duration_text}" if duration_text else "● REC")
            self.recording_label.set_visible(True)
        else:
            self.recording_label.set_visible(False)

    def set_volume(self, volume: float):
        """Set volume (0.0 - 1.0)"""
        self.volume_button.set_value(volume)

    def set_seek_position(self, position: float, duration: float):
        """Update seek bar position (for seekable streams like YouTube)"""
        if duration > 0:
            self.seek_scale.set_sensitive(True)
            self.seek_scale.set_range(0, duration)
            self.seek_scale.set_value(position)

            # Update time labels
            self.current_time_label.set_label(self._format_time(position))
            self.total_time_label.set_label(self._format_time(duration))
        else:
            self.seek_scale.set_sensitive(False)
            self.seek_scale.set_value(0)
            self.current_time_label.set_label("0:00")
            self.total_time_label.set_label("0:00")

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS or HH:MM:SS"""
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
