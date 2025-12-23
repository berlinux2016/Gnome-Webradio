"""Simplified main window for WebRadio Player - guaranteed to show content"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gdk, GdkPixbuf, Gio
import threading
import requests
from io import BytesIO

from webradio.player import AudioPlayer, PlayerState
from webradio.radio_api import RadioBrowserAPI
from webradio.favorites import FavoritesManager


class StationRow(Gtk.ListBoxRow):
    """Custom row for displaying a radio station"""

    def __init__(self, station: dict, is_favorite: bool = False):
        super().__init__()
        self.station = station

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
            fav_icon = Gtk.Image.new_from_icon_name('emblem-favorite')
            box.append(fav_icon)

        self.set_child(box)

        # Load station logo asynchronously
        if station.get('favicon'):
            threading.Thread(target=self._load_logo, args=(station['favicon'],), daemon=True).start()

    def _load_logo(self, url: str):
        """Load station logo from URL"""
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                GLib.idle_add(self._set_logo_from_data, response.content)
        except:
            pass

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
        except:
            pass


class WebRadioWindow(Adw.ApplicationWindow):
    """Main application window"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        print("Initializing WebRadio Window...")

        # Initialize components
        self.player = AudioPlayer()
        self.api = RadioBrowserAPI()
        self.favorites_manager = FavoritesManager()

        # Connect player signals
        self.player.connect('state-changed', self._on_player_state_changed)
        self.player.connect('error', self._on_player_error)
        self.player.connect('tags-updated', self._on_tags_updated)

        # Window settings
        self.set_default_size(900, 700)
        self.set_title('WebRadio Player')

        # Current state
        self.current_stations = []

        # Build UI immediately
        print("Building UI...")
        self._build_ui()

        print("UI built successfully")

        # Load stations after a short delay
        GLib.timeout_add(500, self._start_loading_stations)

    def _build_ui(self):
        """Build the user interface"""
        # Main vertical box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header
        header = Adw.HeaderBar()

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name('open-menu-symbolic')
        menu = Gio.Menu()
        menu.append('About', 'app.about')
        menu.append('Quit', 'app.quit')
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        main_box.append(header)

        # Content area with notebook/tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_vexpand(True)

        # Page 1: Discover
        discover_page = self._create_discover_page()
        self.notebook.append_page(discover_page, Gtk.Label(label="Discover"))

        # Page 2: Favorites
        favorites_page = self._create_favorites_page()
        self.notebook.append_page(favorites_page, Gtk.Label(label="Favorites"))

        main_box.append(self.notebook)

        # Player controls at bottom
        player_box = self._create_player_controls()
        main_box.append(player_box)

        self.set_content(main_box)
        print("Main UI structure created")

    def _create_discover_page(self):
        """Create discover page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_margin_start(12)
        page.set_margin_end(12)
        page.set_margin_top(12)
        page.set_margin_bottom(12)

        # Search box
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text('Search stations...')
        self.search_entry.set_hexpand(True)
        self.search_entry.connect('activate', self._on_search)
        search_box.append(self.search_entry)

        search_btn = Gtk.Button(label='Search')
        search_btn.connect('clicked', self._on_search)
        search_box.append(search_btn)

        page.append(search_box)

        # Filter buttons
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        filters = [
            ('Top Voted', self._load_top_stations),
            ('Rock', lambda: self._load_by_tag('rock')),
            ('Pop', lambda: self._load_by_tag('pop')),
            ('Jazz', lambda: self._load_by_tag('jazz')),
        ]

        for label, callback in filters:
            btn = Gtk.Button(label=label)
            btn.connect('clicked', lambda b, cb=callback: cb())
            filter_box.append(btn)

        page.append(filter_box)

        # Station list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(300)

        self.station_listbox = Gtk.ListBox()
        self.station_listbox.connect('row-activated', self._on_station_activated)

        # Important: Set placeholder
        placeholder_label = Gtk.Label(label="Click 'Top Voted' to load stations")
        placeholder_label.set_margin_top(24)
        placeholder_label.set_margin_bottom(24)
        self.station_listbox.set_placeholder(placeholder_label)

        scrolled.set_child(self.station_listbox)
        page.append(scrolled)

        return page

    def _create_favorites_page(self):
        """Create favorites page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_margin_start(12)
        page.set_margin_end(12)
        page.set_margin_top(12)
        page.set_margin_bottom(12)

        # Favorites list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        self.favorites_listbox = Gtk.ListBox()
        self.favorites_listbox.connect('row-activated', self._on_station_activated)

        placeholder_label = Gtk.Label(label="No favorites yet\nClick ♥ to add stations")
        placeholder_label.set_justify(Gtk.Justification.CENTER)
        placeholder_label.set_margin_top(24)
        placeholder_label.set_margin_bottom(24)
        self.favorites_listbox.set_placeholder(placeholder_label)

        scrolled.set_child(self.favorites_listbox)
        page.append(scrolled)

        # Load favorites
        self._load_favorites()

        return page

    def _create_player_controls(self):
        """Create player control bar"""
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar.set_margin_start(12)
        bar.set_margin_end(12)
        bar.set_margin_top(6)
        bar.set_margin_bottom(6)

        # Station info
        self.station_label = Gtk.Label(label='No station playing')
        self.station_label.set_xalign(0)
        self.station_label.set_hexpand(True)
        bar.append(self.station_label)

        # Favorite button
        self.fav_button = Gtk.Button()
        self.fav_button.set_icon_name('emblem-favorite-symbolic')
        self.fav_button.connect('clicked', self._on_favorite_clicked)
        self.fav_button.set_sensitive(False)
        bar.append(self.fav_button)

        # Play button
        self.play_button = Gtk.Button()
        self.play_button.set_icon_name('media-playback-start-symbolic')
        self.play_button.connect('clicked', self._on_play_pause)
        self.play_button.set_sensitive(False)
        bar.append(self.play_button)

        # Stop button
        self.stop_button = Gtk.Button()
        self.stop_button.set_icon_name('media-playback-stop-symbolic')
        self.stop_button.connect('clicked', self._on_stop)
        self.stop_button.set_sensitive(False)
        bar.append(self.stop_button)

        # Volume
        self.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.volume_scale.set_value(100)
        self.volume_scale.set_size_request(100, -1)
        self.volume_scale.connect('value-changed', self._on_volume_changed)
        bar.append(self.volume_scale)

        return bar

    def _start_loading_stations(self):
        """Start loading stations"""
        print("Starting to load stations...")
        self._load_top_stations()
        return False

    def _load_top_stations(self):
        """Load top voted stations"""
        print("Loading top stations...")

        def load():
            try:
                stations = self.api.get_top_stations(50)
                print(f"Loaded {len(stations)} stations")
                GLib.idle_add(self._display_stations, stations)
            except Exception as e:
                print(f"Error loading stations: {e}")
                import traceback
                traceback.print_exc()

        threading.Thread(target=load, daemon=True).start()

    def _load_by_tag(self, tag: str):
        """Load stations by tag"""
        print(f"Loading stations with tag: {tag}")

        def load():
            try:
                stations = self.api.search_by_tag(tag, 50)
                print(f"Loaded {len(stations)} stations for tag {tag}")
                GLib.idle_add(self._display_stations, stations)
            except Exception as e:
                print(f"Error loading stations: {e}")

        threading.Thread(target=load, daemon=True).start()

    def _on_search(self, widget):
        """Handle search"""
        query = self.search_entry.get_text().strip()
        if not query:
            self._load_top_stations()
            return

        print(f"Searching for: {query}")

        def search():
            try:
                stations = self.api.search_stations(query, 50)
                print(f"Found {len(stations)} stations")
                GLib.idle_add(self._display_stations, stations)
            except Exception as e:
                print(f"Error searching: {e}")

        threading.Thread(target=search, daemon=True).start()

    def _display_stations(self, stations):
        """Display stations in list"""
        print(f"Displaying {len(stations)} stations...")
        self.current_stations = stations

        # Clear existing rows
        child = self.station_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.station_listbox.remove(child)
            child = next_child

        # Add new rows
        for station in stations:
            is_fav = self.favorites_manager.is_favorite(station.get('stationuuid', ''))
            row = StationRow(station, is_fav)
            self.station_listbox.append(row)

        print(f"Added {len(stations)} stations to UI")

    def _load_favorites(self):
        """Load favorites"""
        favorites = self.favorites_manager.get_favorites()
        print(f"Loading {len(favorites)} favorites")

        # Clear
        child = self.favorites_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.favorites_listbox.remove(child)
            child = next_child

        # Add
        for station in favorites:
            row = StationRow(station, True)
            self.favorites_listbox.append(row)

    def _on_station_activated(self, listbox, row):
        """Play selected station"""
        if isinstance(row, StationRow):
            station = row.station
            print(f"Playing: {station.get('name')}")

            url = station.get('url_resolved') or station.get('url')
            if url:
                self.player.play(url, station)
                self.station_label.set_text(station.get('name', 'Unknown'))
                self.play_button.set_sensitive(True)
                self.stop_button.set_sensitive(True)
                self.fav_button.set_sensitive(True)
                self._update_fav_button()

                # Register click
                uuid = station.get('stationuuid')
                if uuid:
                    threading.Thread(target=lambda: self.api.register_click(uuid), daemon=True).start()

    def _on_play_pause(self, button):
        """Toggle play/pause"""
        if self.player.is_playing():
            self.player.pause()
        else:
            self.player.resume()

    def _on_stop(self, button):
        """Stop playback"""
        self.player.stop()
        self.station_label.set_text('No station playing')
        self.play_button.set_sensitive(False)
        self.stop_button.set_sensitive(False)
        self.fav_button.set_sensitive(False)

    def _on_volume_changed(self, scale):
        """Change volume"""
        volume = scale.get_value() / 100.0
        self.player.set_volume(volume)

    def _on_favorite_clicked(self, button):
        """Toggle favorite"""
        station = self.player.get_current_station()
        if not station:
            return

        uuid = station.get('stationuuid')
        if not uuid:
            return

        if self.favorites_manager.is_favorite(uuid):
            self.favorites_manager.remove_favorite(uuid)
        else:
            self.favorites_manager.add_favorite(station)

        self._update_fav_button()
        self._load_favorites()

    def _update_fav_button(self):
        """Update favorite button icon"""
        station = self.player.get_current_station()
        if station:
            uuid = station.get('stationuuid', '')
            if self.favorites_manager.is_favorite(uuid):
                self.fav_button.set_icon_name('emblem-favorite')
            else:
                self.fav_button.set_icon_name('emblem-favorite-symbolic')

    def _on_player_state_changed(self, player, state):
        """Handle player state change"""
        if state == PlayerState.PLAYING.value:
            self.play_button.set_icon_name('media-playback-pause-symbolic')
        else:
            self.play_button.set_icon_name('media-playback-start-symbolic')

    def _on_player_error(self, player, error_msg):
        """Handle player error"""
        print(f"Player error: {error_msg}")

    def _on_tags_updated(self, player, tags):
        """Handle metadata tags"""
        title = tags.get('title', '')
        artist = tags.get('artist', '')

        if title and artist:
            self.station_label.set_text(f'{artist} - {title}')
        elif title:
            self.station_label.set_text(title)
