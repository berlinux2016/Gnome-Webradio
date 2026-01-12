"""Simplified main window for WebRadio Player - guaranteed to show content"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gst', '1.0')

from gi.repository import Gtk, Adw, GLib, Gdk, GdkPixbuf, Gio, Gst
import threading
import requests
from io import BytesIO

from webradio.player import AudioPlayer, PlayerState
from webradio.player_factory import create_player
from webradio.logger import get_logger
from webradio.ui.components.station_row import StationRow, MusicTrackRow, YouTubeVideoRow
from webradio.ui.pages import DiscoverPage, FavoritesPage, HistoryPage, YouTubePage
from webradio.keyboard_shortcuts import create_shortcuts_manager
from webradio.session_manager import create_session_manager
from webradio.notifications import create_notification_manager
from webradio.export_import import create_export_import_manager

logger = get_logger(__name__)
from webradio.radio_api import RadioBrowserAPI
from webradio.favorites import FavoritesManager
from webradio.history import HistoryManager
from webradio.equalizer import EqualizerManager
from webradio.recorder import StreamRecorder
from webradio.sleep_timer import SleepTimer
from webradio.tray_icon import TrayIcon
from webradio.music_library import MusicLibrary
from webradio.youtube_music import YouTubeMusic
from webradio.inhibitor import SessionInhibitor
from webradio.i18n import _

# MPRIS import with fallback
try:
    from webradio.mpris import MPRISInterface
    MPRIS_AVAILABLE = True
except ImportError as e:
    print(f"MPRIS not available: {e}")
    MPRIS_AVAILABLE = False


class WebRadioWindow(Adw.ApplicationWindow):
    """Main application window"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        logger.info("Initializing WebRadio Window...")

        # Get application and settings
        app = self.get_application()
        self.settings = app.settings if app else None

        # Initialize components - use advanced player with equalizer and recording
        self.player = create_player(use_advanced=True)
        self.api = RadioBrowserAPI()
        self.favorites_manager = FavoritesManager()
        self.history_manager = HistoryManager()
        self.music_library = MusicLibrary()
        self.youtube_music = YouTubeMusic()
        self.session_manager = create_session_manager()
        self.notification_manager = create_notification_manager(app)
        self.export_import_manager = create_export_import_manager()

        # Initialize managers with settings
        self.equalizer_manager = EqualizerManager(self.player, self.settings)
        self.recorder = StreamRecorder(self.player, self.settings)
        self.sleep_timer = SleepTimer(self.player, app, self.settings)

        # Flag to prevent recursive navigation button toggling
        self._updating_nav_buttons = False

        # YouTube state for infinite scrolling
        self.youtube_current_query = ""
        self.youtube_current_offset = 0
        self.youtube_all_videos = []  # Store all fetched videos
        self.youtube_loading = False

        # Seek bar state
        self.seeking = False  # Prevent update loop during seek
        self.is_seekable = False  # Whether current stream is seekable
        self.position_update_timer = None

        # Connect player signals
        self.player.connect('state-changed', self._on_player_state_changed)
        self.player.connect('error', self._on_player_error)
        self.player.connect('tags-changed', self._on_tags_updated)

        # Connect recorder signals
        self.recorder.connect('recording-started', self._on_recording_started)
        self.recorder.connect('recording-stopped', self._on_recording_stopped)

        # Connect sleep timer signals
        self.sleep_timer.connect('timer-expired', self._on_sleep_timer_expired)

        # Connect settings signals for live updates
        if self.settings:
            self.settings.connect('changed::spectrum-style', self._on_spectrum_style_changed)

        print(f"Managers initialized - Equalizer: {self.equalizer_manager is not None}, Recorder: {self.recorder is not None}")

        # Setup actions
        self._setup_actions()

        # Window settings - fixed size for media player
        self.set_default_size(1100, 650)
        self.set_title('WebRadio Player')

        # Current state
        self.current_stations = []
        self.spectrum_timeout_id = None

        # Minimize to tray behavior
        self.minimize_to_tray = True  # Enable minimize to tray when playing

        # Build UI immediately
        print("Building UI...")
        self._build_ui()

        print("UI built successfully")

        # Setup system tray
        self.tray_icon = TrayIcon(self.get_application(), self)

        # Setup session inhibitor (prevent suspend while playing)
        self.session_inhibitor = SessionInhibitor(self)

        # Setup MPRIS (GNOME media controls)
        if MPRIS_AVAILABLE:
            try:
                self.mpris = MPRISInterface(self)
                print("MPRIS media controls enabled")
            except Exception as e:
                print(f"Failed to setup MPRIS: {e}")
                self.mpris = None
        else:
            self.mpris = None

        # Connect close request signal
        self.connect('close-request', self._on_close_request)

        # Setup keyboard shortcuts
        self.shortcuts_manager = create_shortcuts_manager(self)
        self._register_keyboard_shortcuts()
        logger.info("Keyboard shortcuts enabled")

        # Load stations after a short delay
        GLib.timeout_add(500, self._start_loading_stations)

        # Load favorites and history after UI is ready
        GLib.timeout_add(600, self._load_favorites)
        GLib.timeout_add(650, self._load_history)

        # Resume previous session if enabled
        GLib.timeout_add(1000, self._resume_session)

    def _build_ui(self):
        """Build Spotify-style interface with sidebar navigation"""
        # Main container: vertical box (sidebar + content on top, player at bottom)
        main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Top section: Sidebar + Content (horizontal split)
        content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        content_paned.set_vexpand(True)

        # Create content area first (needed before sidebar)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header bar (minimal, just app menu)
        header = Adw.HeaderBar()
        header.add_css_class('flat')

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name('open-menu-symbolic')
        menu = Gio.Menu()
        menu.append(_('menu_preferences'), 'app.preferences')
        menu.append("Keyboard Shortcuts", 'win.show-shortcuts')
        menu.append(_('menu_about'), 'app.about')
        menu.append(_('menu_quit'), 'app.quit')
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        content_box.append(header)

        # Content area with pages
        self.view_stack = Adw.ViewStack()
        self.view_stack.set_vexpand(True)

        # HOME Section Pages
        home_page = self._create_home_page()
        self.view_stack.add_named(home_page, "home")

        now_playing_page = self._create_now_playing_page()
        self.view_stack.add_named(now_playing_page, "now_playing")

        search_page = self._create_search_page()
        self.view_stack.add_named(search_page, "search")

        # LIBRARY Section Pages
        playlists_page = self._create_playlists_page()
        self.view_stack.add_named(playlists_page, "playlists")

        local_music_page = self._create_local_music_page()
        self.view_stack.add_named(local_music_page, "local_music")

        artists_page = self._create_artists_page()
        self.view_stack.add_named(artists_page, "artists")

        albums_page = self._create_albums_page()
        self.view_stack.add_named(albums_page, "albums")

        # ONLINE Section Pages
        # Create discover page (used for both Internet Radio and Discover)
        discover_page = self._create_discover_page()
        self.view_stack.add_named(discover_page, "discover")

        youtube_page = self._create_youtube_page()
        self.view_stack.add_named(youtube_page, "youtube")

        favorites_page = self._create_favorites_page()
        self.view_stack.add_named(favorites_page, "favorites")

        history_page = self._create_history_page()
        self.view_stack.add_named(history_page, "history")

        content_box.append(self.view_stack)

        # Now create sidebar (after view_stack exists)
        sidebar = self._create_sidebar()
        content_paned.set_start_child(sidebar)
        content_paned.set_resize_start_child(False)
        content_paned.set_shrink_start_child(False)

        content_paned.set_end_child(content_box)

        main_container.append(content_paned)

        # BOTTOM: Player bar (always visible, Spotify-style)
        player_bar = self._create_player_controls()
        main_container.append(player_bar)

        self.set_content(main_container)

        # Set home page as initial view
        self.view_stack.set_visible_child_name("home")

        print("Spotify-style UI created")

    def _create_sidebar(self):
        """Create professional sidebar with sections like Spotify"""
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.set_size_request(220, -1)
        sidebar.add_css_class('sidebar')

        # Scrollable container for navigation
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        nav_box.set_margin_start(8)
        nav_box.set_margin_end(8)
        nav_box.set_margin_top(8)

        # === HOME SECTION ===
        self._add_section_label(nav_box, _('section_home'))

        self.nav_home = self._create_nav_button('go-home-symbolic', _('Home'), 'home')
        self.nav_now_playing = self._create_nav_button('multimedia-player-symbolic', _('Now Playing'), 'now_playing')
        self.nav_search = self._create_nav_button('system-search-symbolic', _('Search'), 'search')

        nav_box.append(self.nav_home)
        nav_box.append(self.nav_now_playing)
        nav_box.append(self.nav_search)

        # === YOUR LIBRARY SECTION ===
        self._add_section_separator(nav_box)
        self._add_section_label(nav_box, _('section_library'))

        self.nav_playlists = self._create_nav_button('view-list-symbolic', _('Playlists'), 'playlists')
        self.nav_local_music = self._create_nav_button('folder-music-symbolic', _('Local Music'), 'local_music')
        self.nav_artists = self._create_nav_button('system-users-symbolic', _('Artists'), 'artists')
        self.nav_albums = self._create_nav_button('media-optical-symbolic', _('Albums'), 'albums')

        nav_box.append(self.nav_playlists)
        nav_box.append(self.nav_local_music)
        nav_box.append(self.nav_artists)
        nav_box.append(self.nav_albums)

        # === ONLINE SECTION ===
        self._add_section_separator(nav_box)
        self._add_section_label(nav_box, _('section_online'))

        self.nav_radio = self._create_nav_button('radio-symbolic', _('Internet Radio'), 'discover')
        self.nav_youtube = self._create_nav_button('multimedia-player-symbolic', _('YouTube Search'), 'youtube')
        self.nav_favorites = self._create_nav_button('starred-symbolic', _('Favorites'), 'favorites')
        self.nav_history = self._create_nav_button('document-open-recent-symbolic', _('History'), 'history')

        nav_box.append(self.nav_radio)
        nav_box.append(self.nav_youtube)
        nav_box.append(self.nav_favorites)
        nav_box.append(self.nav_history)

        scrolled.set_child(nav_box)
        sidebar.append(scrolled)

        # Set initial active state - start with Home page
        self.nav_home.set_active(True)

        return sidebar

    def _add_section_label(self, container, text):
        """Add a section header label"""
        label = Gtk.Label(label=text)
        label.set_xalign(0)
        label.set_margin_start(16)
        label.set_margin_end(16)
        label.set_margin_top(16)
        label.set_margin_bottom(8)
        label.add_css_class('sidebar-section-label')
        label.add_css_class('caption-heading')
        container.append(label)

    def _add_section_separator(self, container):
        """Add a separator between sections"""
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(12)
        separator.set_margin_bottom(4)
        container.append(separator)

    def _create_nav_button(self, icon_name, label, page_name):
        """Create a sidebar navigation button"""
        button = Gtk.ToggleButton()
        button.set_has_frame(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(20)
        box.append(icon)

        label_widget = Gtk.Label(label=label)
        label_widget.set_xalign(0)
        label_widget.set_hexpand(True)
        box.append(label_widget)

        button.set_child(box)
        button.connect('toggled', self._on_nav_button_toggled, page_name)

        return button

    def _on_nav_button_toggled(self, button, page_name):
        """Handle sidebar navigation button toggle"""
        # Prevent recursive calls
        if self._updating_nav_buttons:
            return

        if button.get_active():
            self._updating_nav_buttons = True
            try:
                # Deactivate other buttons
                all_nav_buttons = [
                    self.nav_home, self.nav_now_playing, self.nav_search,
                    self.nav_playlists, self.nav_local_music, self.nav_artists, self.nav_albums,
                    self.nav_radio, self.nav_youtube, self.nav_favorites, self.nav_history
                ]
                for nav_button in all_nav_buttons:
                    if nav_button != button and nav_button.get_active():
                        nav_button.set_active(False)

                # Switch page
                self.view_stack.set_visible_child_name(page_name)
            finally:
                self._updating_nav_buttons = False
        else:
            # Don't allow deselecting the active button
            self._updating_nav_buttons = True
            try:
                button.set_active(True)
            finally:
                self._updating_nav_buttons = False

    def _create_discover_page(self):
        """Create discover page using DiscoverPage component"""
        page = DiscoverPage(
            on_search_activate=self._on_search,
            on_search_changed=self._on_search_changed,
            on_country_changed=self._on_country_changed,
            on_load_top_stations=self._load_top_stations,
            on_load_by_tag=self._load_by_tag,
            on_station_scroll=self._on_station_scroll,
            on_station_activated=self._on_station_activated
        )

        # Store references for backwards compatibility
        self.search_entry = page.get_search_entry()
        self.station_listbox = page.get_station_listbox()
        self.country_dropdown = page.get_country_dropdown()
        self.country_store = page.get_country_store()
        self.station_scrolled = page.station_scrolled

        # Store search state references
        self.search_timeout_id = None
        self.global_search_timeout_id = None

        # Store pagination state references (delegate to page)
        self.discover_page = page
        self.country_names = page.country_names

        return page

    # Pagination properties delegated to discover_page
    @property
    def current_offset(self):
        return self.discover_page.current_offset if hasattr(self, 'discover_page') else 0

    @current_offset.setter
    def current_offset(self, value):
        if hasattr(self, 'discover_page'):
            self.discover_page.current_offset = value

    @property
    def stations_per_page(self):
        return self.discover_page.stations_per_page if hasattr(self, 'discover_page') else 50

    @stations_per_page.setter
    def stations_per_page(self, value):
        if hasattr(self, 'discover_page'):
            self.discover_page.stations_per_page = value

    @property
    def is_loading_more(self):
        return self.discover_page.is_loading_more if hasattr(self, 'discover_page') else False

    @is_loading_more.setter
    def is_loading_more(self, value):
        if hasattr(self, 'discover_page'):
            self.discover_page.is_loading_more = value

    @property
    def has_more_stations(self):
        return self.discover_page.has_more_stations if hasattr(self, 'discover_page') else True

    @has_more_stations.setter
    def has_more_stations(self, value):
        if hasattr(self, 'discover_page'):
            self.discover_page.has_more_stations = value

    @property
    def current_filter_type(self):
        return self.discover_page.current_filter_type if hasattr(self, 'discover_page') else None

    @current_filter_type.setter
    def current_filter_type(self, value):
        if hasattr(self, 'discover_page'):
            self.discover_page.current_filter_type = value

    @property
    def current_filter_value(self):
        return self.discover_page.current_filter_value if hasattr(self, 'discover_page') else None

    @current_filter_value.setter
    def current_filter_value(self, value):
        if hasattr(self, 'discover_page'):
            self.discover_page.current_filter_value = value

    def _create_favorites_page(self):
        """Create favorites page using FavoritesPage component"""
        page = FavoritesPage(
            on_station_activated=self._on_station_activated,
            on_load_favorites=self._load_favorites,
            on_export=self._on_export_favorites,
            on_import=self._on_import_favorites
        )

        # Store references for backwards compatibility
        self.favorites_listbox = page.get_listbox()

        return page

    def _create_local_music_page(self):
        """Create local music library page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(18)
        page.set_margin_end(18)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.add_css_class('content-page')

        # Header with buttons
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        title_label = Gtk.Label(label=_("local_music_title"))
        title_label.set_xalign(0)
        title_label.set_hexpand(True)
        title_label.add_css_class('title-2')
        header_box.append(title_label)

        # Add folder button
        add_folder_btn = Gtk.Button(label=_("add_music_folder"))
        add_folder_btn.set_icon_name('folder-new-symbolic')
        add_folder_btn.add_css_class('pill')
        add_folder_btn.connect('clicked', self._on_add_music_folder)
        header_box.append(add_folder_btn)

        # Scan button
        self.scan_button = Gtk.Button(label=_("scan_library"))
        self.scan_button.set_icon_name('view-refresh-symbolic')
        self.scan_button.add_css_class('pill')
        self.scan_button.connect('clicked', self._on_scan_library)
        header_box.append(self.scan_button)

        page.append(header_box)

        # Status label (shows track count or scanning status)
        self.library_status_label = Gtk.Label(label='')
        self.library_status_label.set_xalign(0)
        self.library_status_label.set_opacity(0.7)
        page.append(self.library_status_label)

        # Track list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        self.music_listbox = Gtk.ListBox()
        self.music_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.music_listbox.connect('row-activated', self._on_local_track_activated)

        # Placeholder
        placeholder = Adw.StatusPage()
        placeholder.set_icon_name('folder-music-symbolic')
        placeholder.set_title(_("no_music_folders"))
        placeholder.set_description(_("add_folder_hint"))
        self.music_listbox.set_placeholder(placeholder)

        scrolled.set_child(self.music_listbox)
        page.append(scrolled)

        # Load existing tracks
        self._load_local_tracks()

        return page

    def _create_history_page(self):
        """Create history page using HistoryPage component"""
        page = HistoryPage(
            on_station_activated=self._on_history_station_activated,
            on_clear_history=self._on_clear_history,
            on_load_history=self._load_history
        )

        # Store references for backwards compatibility
        self.history_listbox = page.get_listbox()

        return page

    def _create_now_playing_page(self):
        """Create now playing page with large artwork and metadata"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        page.set_margin_start(18)
        page.set_margin_end(18)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.set_valign(Gtk.Align.CENTER)
        page.set_halign(Gtk.Align.CENTER)
        page.add_css_class('content-page')

        # Large station logo
        self.np_logo = Gtk.Image()
        self.np_logo.set_pixel_size(256)
        self.np_logo.set_from_icon_name('audio-x-generic')
        page.append(self.np_logo)

        # Station name (large, bold)
        self.np_station_label = Gtk.Label(label=_("No Station Playing"))
        self.np_station_label.add_css_class('title-1')
        self.np_station_label.set_wrap(True)
        self.np_station_label.set_justify(Gtk.Justification.CENTER)
        page.append(self.np_station_label)

        # Now playing track info (large)
        self.np_track_label = Gtk.Label(label='')
        self.np_track_label.add_css_class('title-3')
        self.np_track_label.set_wrap(True)
        self.np_track_label.set_justify(Gtk.Justification.CENTER)
        self.np_track_label.set_opacity(0.7)
        page.append(self.np_track_label)

        # Station details
        self.np_details_label = Gtk.Label(label='')
        self.np_details_label.set_wrap(True)
        self.np_details_label.set_justify(Gtk.Justification.CENTER)
        self.np_details_label.set_opacity(0.5)
        page.append(self.np_details_label)

        # Spectrum visualizer
        from webradio.spectrum import SpectrumVisualizer

        spectrum_frame = Gtk.Frame()
        spectrum_frame.set_size_request(600, 200)

        self.spectrum_visualizer = SpectrumVisualizer()
        self.spectrum_visualizer.set_size_request(600, 200)

        # Load spectrum style from settings
        if self.settings:
            style = self.settings.get_string('spectrum-style')
            self.spectrum_visualizer.set_style(style)

        spectrum_frame.set_child(self.spectrum_visualizer)
        page.append(spectrum_frame)

        return page

    def _create_home_page(self):
        """Create professional home/dashboard page"""
        # Create scrolled window for the home page
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(12)
        page.set_margin_bottom(12)
        page.add_css_class('content-page')

        # Hero Section with icon and welcome - compact
        hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hero_box.set_halign(Gtk.Align.CENTER)
        hero_box.set_margin_bottom(8)

        # App icon - small
        hero_icon = Gtk.Image()
        hero_icon.set_from_icon_name('multimedia-player-symbolic')
        hero_icon.set_pixel_size(48)
        hero_icon.set_opacity(0.9)
        hero_box.append(hero_icon)

        # Welcome text
        welcome_label = Gtk.Label(label="WebRadio Player")
        welcome_label.add_css_class('title-3')
        hero_box.append(welcome_label)

        tagline = Gtk.Label(label="Entdecke Tausende Radiosender & YouTube Suche")
        tagline.add_css_class('caption')
        tagline.set_opacity(0.7)
        hero_box.append(tagline)

        page.append(hero_box)

        # Quick Actions - 3 cards in a row
        actions_label = Gtk.Label(label="Schnellzugriff")
        actions_label.add_css_class('heading')
        actions_label.set_xalign(0)
        actions_label.set_margin_bottom(6)
        page.append(actions_label)

        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        actions_box.set_homogeneous(True)

        # Card 1: Top Stations
        top_stations_card = self._create_action_card(
            'emblem-favorite-symbolic',
            'Top Radiosender',
            'Beliebteste Sender weltweit',
            lambda: self._navigate_to('discover')
        )
        actions_box.append(top_stations_card)

        # Card 2: YouTube Search
        youtube_card = self._create_action_card(
            'multimedia-player-symbolic',
            'YouTube Suche',
            'Millionen von Videos',
            lambda: self._navigate_to('youtube')
        )
        actions_box.append(youtube_card)

        # Card 3: Favorites
        favorites_card = self._create_action_card(
            'starred-symbolic',
            'Favoriten',
            f'{len(self.favorites_manager.get_favorites())} gespeichert',
            lambda: self._navigate_to('favorites')
        )
        actions_box.append(favorites_card)

        page.append(actions_box)

        # Stats Section
        stats_label = Gtk.Label(label="Statistiken")
        stats_label.add_css_class('heading')
        stats_label.set_xalign(0)
        stats_label.set_margin_top(8)
        stats_label.set_margin_bottom(6)
        page.append(stats_label)

        stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        stats_box.set_homogeneous(True)

        # Stat 1: Total Stations Available
        stat1 = self._create_stat_box('radio-symbolic', '70,000+', 'Radiosender verfügbar')
        stats_box.append(stat1)

        # Stat 2: Favorites Count
        favorites_count = len(self.favorites_manager.get_favorites())
        stat2 = self._create_stat_box('starred-symbolic', str(favorites_count), 'Deine Favoriten')
        stats_box.append(stat2)

        # Stat 3: History Count
        history_count = len(self.history_manager.get_all())
        stat3 = self._create_stat_box('document-open-recent-symbolic', str(history_count), 'Verlauf')
        stats_box.append(stat3)

        page.append(stats_box)

        # Recently Played Section
        if history_count > 0:
            recent_label = Gtk.Label(label="Zuletzt gespielt")
            recent_label.add_css_class('heading')
            recent_label.set_xalign(0)
            recent_label.set_margin_top(8)
            recent_label.set_margin_bottom(6)
            page.append(recent_label)

            # Get recent stations - limit to 3 for compactness
            recent_stations = self.history_manager.get_all()[:3]

            recent_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

            for station in recent_stations:
                recent_row = self._create_compact_station_row(station)
                recent_box.append(recent_row)

            page.append(recent_box)

        scrolled.set_child(page)
        return scrolled

    def _create_action_card(self, icon_name, title, subtitle, on_click):
        """Create a clickable action card"""
        button = Gtk.Button()
        button.add_css_class('card')
        button.set_has_frame(False)
        button.connect('clicked', lambda b: on_click())

        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_box.set_margin_start(24)
        card_box.set_margin_end(24)
        card_box.set_margin_top(24)
        card_box.set_margin_bottom(24)

        # Icon
        icon = Gtk.Image()
        icon.set_from_icon_name(icon_name)
        icon.set_pixel_size(48)
        icon.set_opacity(0.8)
        card_box.append(icon)

        # Title
        title_label = Gtk.Label(label=title)
        title_label.add_css_class('title-3')
        card_box.append(title_label)

        # Subtitle
        subtitle_label = Gtk.Label(label=subtitle)
        subtitle_label.set_opacity(0.6)
        card_box.append(subtitle_label)

        button.set_child(card_box)
        return button

    def _create_stat_box(self, icon_name, number, label):
        """Create a statistics display box"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class('card')
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)

        # Icon
        icon = Gtk.Image()
        icon.set_from_icon_name(icon_name)
        icon.set_pixel_size(32)
        icon.set_opacity(0.7)
        box.append(icon)

        # Number
        number_label = Gtk.Label(label=number)
        number_label.add_css_class('title-2')
        box.append(number_label)

        # Label
        text_label = Gtk.Label(label=label)
        text_label.set_opacity(0.6)
        box.append(text_label)

        return box

    def _create_compact_station_row(self, station):
        """Create a compact clickable station row for recent stations"""
        button = Gtk.Button()
        button.set_has_frame(False)
        button.connect('clicked', lambda b: self._play_station_from_home(station))

        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row_box.set_margin_start(8)
        row_box.set_margin_end(8)
        row_box.set_margin_top(4)
        row_box.set_margin_bottom(4)

        # Small icon
        icon = Gtk.Image()
        icon.set_from_icon_name('audio-x-generic')
        icon.set_pixel_size(32)
        row_box.append(icon)

        # Station name
        name_label = Gtk.Label(label=station.get('name', 'Unknown Station'))
        name_label.set_xalign(0)
        name_label.set_ellipsize(3)
        name_label.set_hexpand(True)
        row_box.append(name_label)

        # Play icon
        play_icon = Gtk.Image()
        play_icon.set_from_icon_name('media-playback-start-symbolic')
        play_icon.set_pixel_size(16)
        play_icon.set_opacity(0.5)
        row_box.append(play_icon)

        button.set_child(row_box)
        return button

    def _navigate_to(self, page_name):
        """Navigate to a specific page"""
        self.view_stack.set_visible_child_name(page_name)

        # Update navigation buttons
        nav_map = {
            'discover': self.nav_radio,
            'youtube': self.nav_youtube,
            'favorites': self.nav_favorites
        }

        if page_name in nav_map:
            nav_map[page_name].set_active(True)

    def _play_station_from_home(self, station):
        """Play a station from the home page recent list"""
        url = station.get('url_resolved') or station.get('url')
        if url:
            self.player.play(url, station)
            self._update_now_playing_page()

    def _create_search_page(self):
        """Create global search page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(18)
        page.set_margin_end(18)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.add_css_class('content-page')

        # Title
        title = Gtk.Label(label=_("Search"))
        title.add_css_class('title-2')
        title.set_xalign(0)
        page.append(title)

        # Search box
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.global_search_entry = Gtk.Entry()
        self.global_search_entry.set_placeholder_text(_('search_placeholder'))
        self.global_search_entry.set_hexpand(True)
        self.global_search_entry.connect('activate', self._on_global_search)
        self.global_search_entry.connect('changed', self._on_global_search_changed)
        search_box.append(self.global_search_entry)

        search_btn = Gtk.Button(label=_('search_button'))
        search_btn.add_css_class('pill')
        search_btn.add_css_class('suggested-action')
        search_btn.connect('clicked', self._on_global_search)
        search_box.append(search_btn)

        page.append(search_box)

        # Results area with scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        self.global_search_listbox = Gtk.ListBox()
        self.global_search_listbox.add_css_class('boxed-list')
        self.global_search_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.global_search_listbox.connect('row-activated', self._on_global_search_station_activated)
        scrolled.set_child(self.global_search_listbox)

        page.append(scrolled)

        # Initial status page
        self.global_search_status = Adw.StatusPage()
        self.global_search_status.set_icon_name('system-search-symbolic')
        self.global_search_status.set_title(_("Search"))
        self.global_search_status.set_description(_("search_description"))
        self.global_search_listbox.append(self.global_search_status)

        return page

    def _create_playlists_page(self):
        """Create playlists page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(18)
        page.set_margin_end(18)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.add_css_class('content-page')

        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        title = Gtk.Label(label=_("playlists_title"))
        title.add_css_class('title-2')
        title.set_xalign(0)
        title.set_hexpand(True)
        header_box.append(title)

        create_btn = Gtk.Button(label=_("create_playlist"))
        create_btn.add_css_class('pill')
        create_btn.set_icon_name('list-add-symbolic')
        header_box.append(create_btn)

        page.append(header_box)

        # Playlist list (to be implemented)
        status_page = Adw.StatusPage()
        status_page.set_icon_name('view-list-symbolic')
        status_page.set_title(_("no_playlists"))
        status_page.set_description(_("create_playlist_hint"))
        page.append(status_page)

        return page

    def _create_artists_page(self):
        """Create artists page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(18)
        page.set_margin_end(18)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.add_css_class('content-page')

        # Title
        title = Gtk.Label(label=_("artists_title"))
        title.add_css_class('title-2')
        title.set_xalign(0)
        page.append(title)

        # Artists list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        self.artists_listbox = Gtk.ListBox()
        self.artists_listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        # Placeholder
        placeholder = Adw.StatusPage()
        placeholder.set_icon_name('system-users-symbolic')
        placeholder.set_title(_("no_artists"))
        placeholder.set_description(_("add_folder_hint"))
        self.artists_listbox.set_placeholder(placeholder)

        scrolled.set_child(self.artists_listbox)
        page.append(scrolled)

        # Load artists
        self._load_artists()

        return page

    def _create_albums_page(self):
        """Create albums page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(18)
        page.set_margin_end(18)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.add_css_class('content-page')

        # Title
        title = Gtk.Label(label=_("albums_title"))
        title.add_css_class('title-2')
        title.set_xalign(0)
        page.append(title)

        # Albums grid
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        self.albums_listbox = Gtk.ListBox()
        self.albums_listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        # Placeholder
        placeholder = Adw.StatusPage()
        placeholder.set_icon_name('media-optical-symbolic')
        placeholder.set_title(_("no_albums"))
        placeholder.set_description(_("add_folder_hint"))
        self.albums_listbox.set_placeholder(placeholder)

        scrolled.set_child(self.albums_listbox)
        page.append(scrolled)

        # Load albums
        self._load_albums()

        return page

    def _create_youtube_page(self):
        """Create YouTube page using YouTubePage component"""
        page = YouTubePage(
            youtube_music=self.youtube_music,
            on_search=self._on_youtube_search,
            on_filter_changed=self._on_youtube_filter_changed,
            on_scroll=self._on_youtube_scroll,
            on_video_activated=self._on_youtube_video_activated
        )

        # Store references for backwards compatibility
        if page.is_available():
            self.youtube_search_entry = page.get_search_entry()
            self.youtube_duration_filter = page.get_duration_filter()
            self.youtube_listbox = page.get_listbox()
        else:
            # yt-dlp not available, set dummy references
            self.youtube_search_entry = None
            self.youtube_duration_filter = None
            self.youtube_listbox = None

        return page

    def _load_artists(self):
        """Load artists from music library"""
        artists = self.music_library.get_all_artists()

        # Clear existing
        child = self.artists_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.artists_listbox.remove(child)
            child = next_child

        # Add artist rows
        for artist in artists:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=artist)
            label.set_xalign(0)
            label.set_margin_start(12)
            label.set_margin_end(12)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            row.set_child(label)
            self.artists_listbox.append(row)

    def _load_albums(self):
        """Load albums from music library"""
        albums = self.music_library.get_all_albums()

        # Clear existing
        child = self.albums_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.albums_listbox.remove(child)
            child = next_child

        # Add album rows
        for album in albums:
            row = Gtk.ListBoxRow()

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.set_margin_start(12)
            box.set_margin_end(12)
            box.set_margin_top(8)
            box.set_margin_bottom(8)

            album_label = Gtk.Label(label=album['album'])
            album_label.set_xalign(0)
            box.append(album_label)

            artist_label = Gtk.Label(label=album['artist'])
            artist_label.set_xalign(0)
            artist_label.set_opacity(0.7)
            box.append(artist_label)

            row.set_child(box)
            self.albums_listbox.append(row)

    def _create_player_controls(self):
        """Create player control bar with 3 logical groups - Spotify style"""
        # Main container with separator
        main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_container.add_css_class('player-bar')

        # No clamp - full width like Spotify
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        bar.set_margin_start(18)
        bar.set_margin_end(18)
        bar.set_margin_top(12)
        bar.set_margin_bottom(12)

        # GROUP 1: Station Info (left side, expanding)
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        info_box.set_hexpand(True)

        # Logo (48px instead of 64px)
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
        bar.append(info_box)

        # Seek bar (timeline) - between info and controls
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
        # Use change-value instead of value-changed to control when to seek
        self.seek_scale.connect('change-value', self._on_seek_changed)
        self.seek_scale.set_sensitive(False)

        seek_box.append(self.seek_scale)
        seek_box.append(time_box)
        bar.append(seek_box)

        # GROUP 2: Playback Controls (center)
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls_box.add_css_class('linked')

        # Favorite button (before play)
        self.fav_button = Gtk.ToggleButton()
        self.fav_button.set_icon_name('starred-symbolic')
        self.fav_button.set_tooltip_text(_('Add to favorites'))
        self.fav_button.connect('toggled', self._on_favorite_toggled)
        self.fav_button.set_sensitive(False)
        controls_box.append(self.fav_button)

        # Play/Pause (suggested-action + circular)
        self.play_button = Gtk.Button()
        self.play_button.set_icon_name('media-playback-start-symbolic')
        self.play_button.set_tooltip_text(_('Play/Pause'))
        self.play_button.connect('clicked', self._on_play_pause)
        self.play_button.add_css_class('suggested-action')
        self.play_button.add_css_class('circular')
        self.play_button.set_sensitive(False)
        controls_box.append(self.play_button)

        # Stop button
        self.stop_button = Gtk.Button()
        self.stop_button.set_icon_name('media-playback-stop-symbolic')
        self.stop_button.set_tooltip_text(_('Stop'))
        self.stop_button.connect('clicked', self._on_stop)
        self.stop_button.set_sensitive(False)
        controls_box.append(self.stop_button)

        bar.append(controls_box)

        # GROUP 3: Features + Volume (right side)
        features_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Record button
        self.record_button = Gtk.ToggleButton()
        self.record_button.set_icon_name('media-record-symbolic')
        self.record_button.set_tooltip_text(_('Record Stream'))
        self.record_button.connect('toggled', self._on_record_toggled)
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
        sleep_menu = Gio.Menu()
        for minutes in self.sleep_timer.get_presets():
            sleep_menu.append(f"{minutes} min", f"win.sleep-timer::{minutes}")
        sleep_menu.append(_("Stop Timer"), "win.sleep-timer-stop")

        self.sleep_button.set_menu_model(sleep_menu)
        features_box.append(self.sleep_button)

        # Volume button (Gtk.VolumeButton instead of Scale!)
        self.volume_button = Gtk.VolumeButton()
        self.volume_button.set_value(1.0)
        self.volume_button.connect('value-changed', self._on_volume_button_changed)
        features_box.append(self.volume_button)

        bar.append(features_box)

        main_container.append(bar)
        return main_container

    def _setup_actions(self):
        """Setup window actions"""
        # Sleep timer action with parameter (minutes)
        sleep_timer_action = Gio.SimpleAction.new_stateful(
            "sleep-timer",
            GLib.VariantType.new("s"),
            GLib.Variant("s", "0")
        )
        sleep_timer_action.connect("activate", self._on_sleep_timer_action)
        self.add_action(sleep_timer_action)

        # Stop sleep timer action
        stop_timer_action = Gio.SimpleAction.new("sleep-timer-stop", None)
        stop_timer_action.connect("activate", self._on_sleep_timer_stop)
        self.add_action(stop_timer_action)

        # Show keyboard shortcuts action
        shortcuts_action = Gio.SimpleAction.new("show-shortcuts", None)
        shortcuts_action.connect("activate", lambda a, p: self._show_shortcuts_dialog())
        self.add_action(shortcuts_action)

    def _start_loading_stations(self):
        """Start loading stations"""
        print("Starting to load stations...")
        self._load_top_stations()
        # Load countries for dropdown
        self._load_countries()
        return False

    def _on_station_scroll(self, adjustment):
        """Handle scrolling to load more stations"""
        # Check if we're near the bottom (within 200 pixels)
        value = adjustment.get_value()
        upper = adjustment.get_upper()
        page_size = adjustment.get_page_size()

        if value + page_size >= upper - 200:
            # Near bottom, load more if available
            if not self.is_loading_more and self.has_more_stations:
                self._load_more_stations()

    def _load_more_stations(self):
        """Load the next batch of stations"""
        if self.is_loading_more or not self.has_more_stations:
            return

        self.is_loading_more = True
        self.current_offset += self.stations_per_page

        print(f"Loading more stations (offset: {self.current_offset})...")

        # Load based on current filter type
        if self.current_filter_type == 'top':
            self._load_top_stations_paged(append=True)
        elif self.current_filter_type == 'tag':
            self._load_by_tag_paged(self.current_filter_value, append=True)
        elif self.current_filter_type == 'search':
            self._on_search_paged(append=True)

    def _load_top_stations(self):
        """Load top voted stations (reset pagination)"""
        self.current_offset = 0
        self.has_more_stations = True
        self.current_filter_type = 'top'
        self.current_filter_value = None
        self._load_top_stations_paged(append=False)

    def _load_top_stations_paged(self, append=False):
        """Load top voted stations with pagination"""
        print(f"Loading top stations (offset: {self.current_offset})...")

        def load():
            try:
                stations = self.api.get_top_stations(self.stations_per_page, offset=self.current_offset)
                print(f"Loaded {len(stations)} stations")

                if len(stations) < self.stations_per_page:
                    self.has_more_stations = False

                GLib.idle_add(self._display_stations, stations, append)
                self.is_loading_more = False
            except Exception as e:
                print(f"Error loading stations: {e}")
                import traceback
                traceback.print_exc()
                self.is_loading_more = False

        threading.Thread(target=load, daemon=True).start()

    def _load_by_tag(self, tag: str):
        """Load stations by tag (reset pagination)"""
        self.current_offset = 0
        self.has_more_stations = True
        self.current_filter_type = 'tag'
        self.current_filter_value = tag
        self._load_by_tag_paged(tag, append=False)

    def _load_by_tag_paged(self, tag: str, append=False):
        """Load stations by tag with pagination"""
        print(f"Loading stations with tag: {tag} (offset: {self.current_offset})")

        def load():
            try:
                stations = self.api.search_by_tag(tag, self.stations_per_page, offset=self.current_offset)
                print(f"Loaded {len(stations)} stations for tag {tag}")

                if len(stations) < self.stations_per_page:
                    self.has_more_stations = False

                GLib.idle_add(self._display_stations, stations, append)
                self.is_loading_more = False
            except Exception as e:
                print(f"Error loading stations: {e}")
                self.is_loading_more = False

        threading.Thread(target=load, daemon=True).start()

    def _load_countries(self):
        """Load available countries in background"""
        def load():
            try:
                countries = self.api.get_countries(300)
                # Sort by station count (descending)
                countries_sorted = sorted(countries, key=lambda x: x.get('stationcount', 0), reverse=True)

                # Take top 50 countries with most stations
                top_countries = countries_sorted[:50]

                def update_ui():
                    for country in top_countries:
                        name = country.get('name', '')
                        count = country.get('stationcount', 0)
                        if name and count > 0:
                            self.country_store.append(f"{name} ({count})")
                            self.country_names.append(name)

                GLib.idle_add(update_ui)
            except Exception as e:
                print(f"Error loading countries: {e}")

        threading.Thread(target=load, daemon=True).start()

    def _on_country_changed(self, dropdown, param):
        """Handle country filter change"""
        selected = dropdown.get_selected()
        if selected >= len(self.country_names):
            return

        country = self.country_names[selected]

        if country:  # Not "All Countries"
            print(f"Filtering by country: {country}")
            self._load_by_country(country)
        else:
            # Load top stations when "All Countries" is selected
            self._load_top_stations()

    def _load_by_country(self, country: str):
        """Load stations by country"""
        print(f"Loading stations for country: {country}")

        def load():
            try:
                stations = self.api.search_by_country(country, 100)
                print(f"Loaded {len(stations)} stations for {country}")
                GLib.idle_add(self._display_stations, stations)
            except Exception as e:
                print(f"Error loading stations: {e}")

        threading.Thread(target=load, daemon=True).start()

    def _on_search(self, widget):
        """Handle search (reset pagination)"""
        query = self.search_entry.get_text().strip()
        if not query:
            self._load_top_stations()
            return

        self.current_offset = 0
        self.has_more_stations = True
        self.current_filter_type = 'search'
        self.current_filter_value = query
        self._on_search_paged(append=False)

    def _on_search_paged(self, append=False):
        """Handle search with pagination"""
        query = self.current_filter_value if append else self.search_entry.get_text().strip()

        print(f"Searching for: {query} (offset: {self.current_offset})")

        def search():
            try:
                stations = self.api.search_stations(query, self.stations_per_page, offset=self.current_offset)
                print(f"Found {len(stations)} stations")

                if len(stations) < self.stations_per_page:
                    self.has_more_stations = False

                GLib.idle_add(self._display_stations, stations, append)
                self.is_loading_more = False
            except Exception as e:
                print(f"Error searching: {e}")
                self.is_loading_more = False

        threading.Thread(target=search, daemon=True).start()

    def _display_stations(self, stations, append=False):
        """Display stations in list"""
        print(f"Displaying {len(stations)} stations (append={append})...")

        if append:
            # Append to existing stations
            if not hasattr(self, 'current_stations'):
                self.current_stations = []
            self.current_stations.extend(stations)
        else:
            # Replace all stations
            self.current_stations = stations

            # Clear existing rows
            child = self.station_listbox.get_first_child()
            while child:
                next_child = child.get_next_sibling()
                self.station_listbox.remove(child)
                child = next_child

        # Add new rows (either all or just the new ones for append)
        for station in stations:
            is_fav = self.favorites_manager.is_favorite(station.get('stationuuid', ''))
            row = StationRow(station, is_fav)
            self.station_listbox.append(row)

        print(f"Added {len(stations)} stations to UI (total: {len(self.current_stations)})")

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

        # Add with delete callback
        for station in favorites:
            row = StationRow(station, True, on_delete_favorite=self._on_delete_favorite)
            self.favorites_listbox.append(row)

        return False  # Don't repeat timeout

    def _on_station_activated(self, listbox, row):
        """Play selected station"""
        if isinstance(row, StationRow):
            station = row.station
            print(f"Playing: {station.get('name')}")

            url = station.get('url_resolved') or station.get('url')
            if url:
                self.player.play(url, station)

                # Add to history
                self.history_manager.add_entry(station)
                self._load_history()  # Refresh history page

                # Update station info
                self.station_label.set_text(station.get('name', 'Unknown'))

                # Update station details
                # Details are shown in Now Playing page (removed from player bar for cleaner UI)
                self.metadata_label.set_text('')  # Clear until we get metadata

                # Update logo
                self._update_playing_logo(station.get('favicon', ''))

                # Update Now Playing page
                self._update_now_playing_page()

                # Enable buttons
                self.play_button.set_sensitive(True)
                self.stop_button.set_sensitive(True)
                self.fav_button.set_sensitive(True)
                self.record_button.set_sensitive(True)
                self._update_fav_button()

                # Update MPRIS metadata
                if self.mpris:
                    self.mpris.update_metadata()

                # Register click
                uuid = station.get('stationuuid')
                if uuid:
                    threading.Thread(target=lambda: self.api.register_click(uuid), daemon=True).start()

    def _register_keyboard_shortcuts(self):
        """Register all keyboard shortcut handlers"""
        # Playback controls
        self.shortcuts_manager.register_handler('play_pause', lambda: self._on_play_pause(None))
        self.shortcuts_manager.register_handler('stop', lambda: self._on_stop(None))
        self.shortcuts_manager.register_handler('volume_up', self._shortcut_volume_up)
        self.shortcuts_manager.register_handler('volume_down', self._shortcut_volume_down)
        self.shortcuts_manager.register_handler('mute', self._shortcut_mute)

        # Navigation
        self.shortcuts_manager.register_handler('focus_search', self._shortcut_focus_search)
        self.shortcuts_manager.register_handler('show_favorites', lambda: self._navigate_to('favorites'))
        self.shortcuts_manager.register_handler('show_history', lambda: self._navigate_to('history'))

        # Window controls
        self.shortcuts_manager.register_handler('quit', lambda: self.close())
        self.shortcuts_manager.register_handler('show_shortcuts', self._show_shortcuts_dialog)

        # Recording
        self.shortcuts_manager.register_handler('toggle_recording', self._shortcut_toggle_recording)

        # Favorites
        self.shortcuts_manager.register_handler('add_to_favorites', self._shortcut_add_to_favorites)

        logger.info("Registered all keyboard shortcut handlers")

    def _shortcut_volume_up(self):
        """Increase volume by 10%"""
        current = self.player.get_volume()
        new_volume = min(1.0, current + 0.1)
        self.player.set_volume(new_volume)
        self.volume_button.set_value(new_volume)
        logger.debug(f"Volume up: {new_volume:.1f}")

    def _shortcut_volume_down(self):
        """Decrease volume by 10%"""
        current = self.player.get_volume()
        new_volume = max(0.0, current - 0.1)
        self.player.set_volume(new_volume)
        self.volume_button.set_value(new_volume)
        logger.debug(f"Volume down: {new_volume:.1f}")

    def _shortcut_mute(self):
        """Toggle mute"""
        if not hasattr(self, '_muted'):
            self._muted = False
            self._volume_before_mute = 1.0

        if self._muted:
            # Unmute
            self.player.set_volume(self._volume_before_mute)
            self.volume_button.set_value(self._volume_before_mute)
            self._muted = False
            logger.debug("Unmuted")
        else:
            # Mute
            self._volume_before_mute = self.player.get_volume()
            self.player.set_volume(0.0)
            self.volume_button.set_value(0.0)
            self._muted = True
            logger.debug("Muted")

    def _shortcut_focus_search(self):
        """Focus the search entry"""
        if hasattr(self, 'search_entry') and self.search_entry:
            self.view_stack.set_visible_child_name('discover')
            self.search_entry.grab_focus()
            logger.debug("Focused search entry")

    def _shortcut_toggle_recording(self):
        """Toggle recording on/off"""
        if hasattr(self, 'record_button') and self.record_button:
            current_state = self.record_button.get_active()
            self.record_button.set_active(not current_state)
            logger.debug(f"Recording toggled: {not current_state}")

    def _shortcut_add_to_favorites(self):
        """Add current station to favorites"""
        station = self.player.get_current_station()
        if station:
            uuid = station.get('stationuuid')
            if uuid and not self.favorites_manager.is_favorite(uuid):
                self.favorites_manager.add_favorite(station)
                if hasattr(self, 'fav_button'):
                    self.fav_button.set_active(True)
                toast = Adw.Toast.new(_("Added to favorites"))
                toast.set_timeout(2)
                self.add_toast(toast)
                logger.info(f"Added station to favorites via shortcut: {station.get('name')}")

    def _show_shortcuts_dialog(self):
        """Show keyboard shortcuts help dialog"""
        if hasattr(self, 'shortcuts_manager'):
            self.shortcuts_manager.show_shortcuts_dialog()

    def _on_play_pause(self, button):
        """Toggle play/pause"""
        if self.player.is_playing():
            self.player.pause()
        else:
            self.player.resume()

    def _on_stop(self, button):
        """Stop playback"""
        self.player.stop()
        self.station_label.set_text(_('no_station_playing'))
        self.metadata_label.set_text('')
        self.playing_logo.set_from_icon_name('audio-x-generic')
        self.play_button.set_sensitive(False)
        self.stop_button.set_sensitive(False)
        self.fav_button.set_sensitive(False)

    def _on_volume_changed(self, scale):
        """Change volume (legacy scale handler)"""
        volume = scale.get_value() / 100.0
        self.player.set_volume(volume)

    def _on_volume_button_changed(self, button, value):
        """Change volume using VolumeButton"""
        self.player.set_volume(value)

    def _on_favorite_clicked(self, button):
        """Toggle favorite (legacy button handler)"""
        station = self.player.get_current_station()
        if not station:
            return

    def _on_favorite_toggled(self, toggle_button):
        """Toggle favorite using ToggleButton"""
        station = self.player.get_current_station()
        if not station:
            return

        uuid = station.get('stationuuid')
        if not uuid:
            return

        # Toggle based on button state
        if toggle_button.get_active():
            # Button is now active -> add to favorites
            self.favorites_manager.add_favorite(station)
        else:
            # Button is now inactive -> remove from favorites
            self.favorites_manager.remove_favorite(uuid)

        self._load_favorites()

    def _on_delete_favorite(self, station):
        """Handle delete favorite from context menu"""
        uuid = station.get('stationuuid')
        if uuid:
            self.favorites_manager.remove_favorite(uuid)
            self._load_favorites()
            self._update_fav_button()
            print(f"Deleted from favorites: {station.get('name')}")

    def _update_fav_button(self):
        """Update favorite button state"""
        station = self.player.get_current_station()
        if station:
            uuid = station.get('stationuuid', '')
            is_fav = self.favorites_manager.is_favorite(uuid)
            # Block handler to prevent recursive calls
            self.fav_button.handler_block_by_func(self._on_favorite_toggled)
            self.fav_button.set_active(is_fav)
            self.fav_button.handler_unblock_by_func(self._on_favorite_toggled)
            # Update icon based on state
            if is_fav:
                self.fav_button.set_icon_name('starred')
                self.fav_button.add_css_class('accent')
            else:
                self.fav_button.set_icon_name('starred-symbolic')
                self.fav_button.remove_css_class('accent')

    def _on_export_favorites(self):
        """Handle export favorites button click"""
        # Create file chooser dialog
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Export Favorites"))
        dialog.set_initial_name("webradio-favorites")

        # Set file filters for OPML and M3U
        filters = Gio.ListStore.new(Gtk.FileFilter)

        opml_filter = Gtk.FileFilter()
        opml_filter.set_name(_("OPML Files (*.opml)"))
        opml_filter.add_pattern("*.opml")
        filters.append(opml_filter)

        m3u_filter = Gtk.FileFilter()
        m3u_filter.set_name(_("M3U Playlists (*.m3u)"))
        m3u_filter.add_pattern("*.m3u")
        filters.append(m3u_filter)

        all_filter = Gtk.FileFilter()
        all_filter.set_name(_("All Files"))
        all_filter.add_pattern("*")
        filters.append(all_filter)

        dialog.set_filters(filters)
        dialog.set_default_filter(opml_filter)

        # Show save dialog
        dialog.save(self, None, self._on_export_favorites_done)

    def _on_export_favorites_done(self, dialog, result):
        """Handle export favorites file selection"""
        try:
            file = dialog.save_finish(result)
            if file:
                file_path = file.get_path()

                # Get favorites
                favorites = self.favorites_manager.get_favorites()

                # Determine format from extension
                if file_path.endswith('.m3u'):
                    success = self.export_import_manager.export_to_m3u(favorites, file_path)
                    format_name = "M3U"
                else:
                    # Default to OPML, add extension if missing
                    if not file_path.endswith('.opml'):
                        file_path += '.opml'
                    success = self.export_import_manager.export_to_opml(favorites, file_path)
                    format_name = "OPML"

                # Show toast notification
                if success:
                    toast = Adw.Toast.new(_("Exported {count} favorites to {format}").format(
                        count=len(favorites), format=format_name))
                    toast.set_timeout(3)
                    self.toast_overlay.add_toast(toast)
                else:
                    toast = Adw.Toast.new(_("Failed to export favorites"))
                    toast.set_timeout(3)
                    self.toast_overlay.add_toast(toast)

        except Exception as e:
            logger.error(f"Export favorites error: {e}")

    def _on_import_favorites(self):
        """Handle import favorites button click"""
        # Create file chooser dialog
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Import Favorites"))

        # Set file filters for OPML and M3U
        filters = Gio.ListStore.new(Gtk.FileFilter)

        opml_filter = Gtk.FileFilter()
        opml_filter.set_name(_("OPML Files (*.opml)"))
        opml_filter.add_pattern("*.opml")
        filters.append(opml_filter)

        m3u_filter = Gtk.FileFilter()
        m3u_filter.set_name(_("M3U Playlists (*.m3u)"))
        m3u_filter.add_pattern("*.m3u")
        filters.append(m3u_filter)

        all_filter = Gtk.FileFilter()
        all_filter.set_name(_("All Files"))
        all_filter.add_pattern("*")
        filters.append(all_filter)

        dialog.set_filters(filters)

        # Show open dialog
        dialog.open(self, None, self._on_import_favorites_done)

    def _on_import_favorites_done(self, dialog, result):
        """Handle import favorites file selection"""
        try:
            file = dialog.open_finish(result)
            if file:
                file_path = file.get_path()

                # Determine format from extension
                if file_path.endswith('.m3u'):
                    stations = self.export_import_manager.import_from_m3u(file_path)
                    format_name = "M3U"
                else:
                    stations = self.export_import_manager.import_from_opml(file_path)
                    format_name = "OPML"

                if stations:
                    # Add imported stations to favorites
                    added_count = 0
                    for station in stations:
                        # Generate a UUID if not present
                        if 'stationuuid' not in station:
                            import uuid
                            station['stationuuid'] = str(uuid.uuid4())

                        # Add to favorites (skip duplicates)
                        if not self.favorites_manager.is_favorite(station['stationuuid']):
                            self.favorites_manager.add_favorite(station)
                            added_count += 1

                    # Reload favorites list
                    self._load_favorites()

                    # Show toast notification
                    toast = Adw.Toast.new(_("Imported {added} of {total} stations from {format}").format(
                        added=added_count, total=len(stations), format=format_name))
                    toast.set_timeout(3)
                    self.toast_overlay.add_toast(toast)
                else:
                    toast = Adw.Toast.new(_("Failed to import favorites"))
                    toast.set_timeout(3)
                    self.toast_overlay.add_toast(toast)

        except Exception as e:
            logger.error(f"Import favorites error: {e}")

    def _on_player_state_changed(self, player, state):
        """Handle player state change"""
        if state == PlayerState.PLAYING.value:
            self.play_button.set_icon_name('media-playback-pause-symbolic')
            # Activate spectrum visualizer
            if hasattr(self, 'spectrum_visualizer'):
                self.spectrum_visualizer.set_active(True)
                self._start_spectrum_animation()
            # Start position update timer
            self._start_position_updates()
            # Inhibit suspend while playing
            if hasattr(self, 'session_inhibitor'):
                self.session_inhibitor.inhibit()
        else:
            self.play_button.set_icon_name('media-playback-start-symbolic')
            # Deactivate spectrum visualizer
            if hasattr(self, 'spectrum_visualizer'):
                self.spectrum_visualizer.set_active(False)
                self._stop_spectrum_animation()
            # Stop position update timer
            self._stop_position_updates()
            # Uninhibit suspend when not playing
            if hasattr(self, 'session_inhibitor'):
                self.session_inhibitor.uninhibit()

        # Update MPRIS
        if self.mpris:
            self.mpris.update_playback_status()

    def _on_player_error(self, player, error_msg):
        """Handle player error"""
        print(f"Player error: {error_msg}")

    def _on_tags_updated(self, player, tags):
        """Handle metadata tags"""
        title = tags.get('title', '')
        artist = tags.get('artist', '')
        organization = tags.get('organization', '')

        # Make sure station name is displayed in player bar
        if self.player.current_station:
            station_name = self.player.current_station.get('name', 'Unknown')
            self.station_label.set_text(station_name)

        # Update metadata label (song/artist info)
        if title and artist:
            self.metadata_label.set_text(f'{artist} - {title}')
        elif title:
            self.metadata_label.set_text(f'{title}')
        elif organization:
            self.metadata_label.set_text(organization)

        # Send notification for track change
        if title and self.notification_manager:
            station_name = self.player.current_station.get('name', 'Radio') if self.player.current_station else 'Radio'
            self.notification_manager.notify_track_change(station_name, title, artist)

        # Update Now Playing page
        self._update_now_playing_page()

        # Update MPRIS metadata
        if self.mpris:
            self.mpris.update_metadata()

    def _update_playing_logo(self, favicon_url: str):
        """Update the now playing logo"""
        if not favicon_url:
            self.playing_logo.set_from_icon_name('audio-x-generic')
            return

        def load_logo():
            try:
                response = requests.get(favicon_url, timeout=5)
                if response.status_code == 200:
                    GLib.idle_add(self._set_playing_logo_from_data, response.content)
            except:
                pass

        threading.Thread(target=load_logo, daemon=True).start()

    def _set_playing_logo_from_data(self, image_data: bytes):
        """Set the playing logo from image data"""
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(image_data)
            loader.close()

            pixbuf = loader.get_pixbuf()
            if pixbuf:
                # Scale to 64x64 for the player bar
                scaled = pixbuf.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)
                texture = Gdk.Texture.new_for_pixbuf(scaled)
                self.playing_logo.set_from_paintable(texture)
        except Exception as e:
            print(f"Failed to load playing logo: {e}")

    def _on_search_changed(self, entry):
        """Handle search text changed - real-time search with debounce"""
        # Cancel previous timeout
        if self.search_timeout_id:
            GLib.source_remove(self.search_timeout_id)
            self.search_timeout_id = None

        query = entry.get_text().strip()

        # If empty, load top stations after a delay
        if not query:
            self.search_timeout_id = GLib.timeout_add(500, self._delayed_load_top_stations)
            return

        # Start search after 500ms of no typing
        self.search_timeout_id = GLib.timeout_add(500, self._delayed_search, query)

    def _delayed_search(self, query):
        """Execute delayed search"""
        self.search_timeout_id = None
        if query:
            print(f"Real-time search for: {query}")

            def search():
                try:
                    stations = self.api.search_stations(query, 50)
                    print(f"Found {len(stations)} stations")
                    GLib.idle_add(self._display_stations, stations)
                except Exception as e:
                    print(f"Error searching: {e}")

            threading.Thread(target=search, daemon=True).start()
        return False

    def _delayed_load_top_stations(self):
        """Load top stations after delay"""
        self.search_timeout_id = None
        self._load_top_stations()
        return False

    def _on_global_search(self, widget):
        """Handle global search"""
        query = self.global_search_entry.get_text().strip()
        if not query:
            return

        print(f"Global search for: {query}")

        # Clear previous results
        child = self.global_search_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.global_search_listbox.remove(child)
            child = next_child

        # Show loading status
        loading_status = Adw.StatusPage()
        loading_status.set_icon_name('content-loading-symbolic')
        loading_status.set_title(_("placeholder_loading"))
        self.global_search_listbox.append(loading_status)

        def search():
            try:
                stations = self.api.search_stations(query, 100)
                print(f"Global search found {len(stations)} stations")
                GLib.idle_add(self._display_global_search_results, stations)
            except Exception as e:
                print(f"Error in global search: {e}")
                GLib.idle_add(self._show_global_search_error, str(e))

        threading.Thread(target=search, daemon=True).start()

    def _on_global_search_changed(self, entry):
        """Handle global search text changed - real-time search with debounce"""
        # Cancel previous timeout
        if hasattr(self, 'global_search_timeout_id') and self.global_search_timeout_id:
            GLib.source_remove(self.global_search_timeout_id)
            self.global_search_timeout_id = None

        query = entry.get_text().strip()

        # If empty, show initial status
        if not query:
            child = self.global_search_listbox.get_first_child()
            while child:
                next_child = child.get_next_sibling()
                self.global_search_listbox.remove(child)
                child = next_child
            self.global_search_listbox.append(self.global_search_status)
            return

        # Start search after 500ms of no typing
        self.global_search_timeout_id = GLib.timeout_add(500, self._delayed_global_search, query)

    def _delayed_global_search(self, query):
        """Execute delayed global search"""
        self.global_search_timeout_id = None
        if query:
            self._on_global_search(None)
        return False

    def _display_global_search_results(self, stations):
        """Display global search results"""
        # Clear previous results
        child = self.global_search_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.global_search_listbox.remove(child)
            child = next_child

        if not stations:
            # No results
            no_results = Adw.StatusPage()
            no_results.set_icon_name('edit-find-symbolic')
            no_results.set_title(_("No Stations Found"))
            no_results.set_description(_("Try a different search term"))
            self.global_search_listbox.append(no_results)
            return

        # Add station rows
        for station in stations:
            is_fav = self.favorites_manager.is_favorite(station.get('stationuuid', ''))
            row = StationRow(station, is_fav)
            self.global_search_listbox.append(row)

    def _show_global_search_error(self, error_msg):
        """Show global search error"""
        # Clear previous results
        child = self.global_search_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.global_search_listbox.remove(child)
            child = next_child

        error_status = Adw.StatusPage()
        error_status.set_icon_name('dialog-error-symbolic')
        error_status.set_title(_("Search Error"))
        error_status.set_description(error_msg)
        self.global_search_listbox.append(error_status)

    def _on_global_search_station_activated(self, listbox, row):
        """Handle global search station activation"""
        if not isinstance(row, StationRow):
            return

        station = row.station
        url = station.get('url_resolved') or station.get('url')
        if url:
            self.player.play(url, station)
            self._update_now_playing_page()

    def _on_info_clicked(self, button):
        """Show Now Playing information dialog"""
        station = self.player.get_current_station()
        if not station:
            return

        # Get current metadata
        tags = self.player.get_current_tags() if hasattr(self.player, 'get_current_tags') else {}

        # Create info dialog
        dialog = Adw.Window()
        dialog.set_default_size(500, 600)
        dialog.set_title('Now Playing Information')
        dialog.set_modal(True)
        dialog.set_transient_for(self)

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header
        header = Adw.HeaderBar()
        main_box.append(header)

        # Scrolled content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)

        # Station Logo (larger)
        logo_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        logo_box.set_halign(Gtk.Align.CENTER)

        station_logo = Gtk.Image()
        station_logo.set_pixel_size(128)
        station_logo.set_from_icon_name('audio-x-generic')

        # Load station logo
        favicon_url = station.get('favicon')
        if favicon_url:
            threading.Thread(
                target=self._load_info_dialog_logo,
                args=(favicon_url, station_logo),
                daemon=True
            ).start()

        logo_box.append(station_logo)
        content_box.append(logo_box)

        # Station Name (large, bold)
        station_name = Gtk.Label()
        station_name.set_markup(f'<span size="x-large" weight="bold">{station.get("name", "Unknown Station")}</span>')
        station_name.set_wrap(True)
        station_name.set_justify(Gtk.Justification.CENTER)
        station_name.set_margin_bottom(12)
        content_box.append(station_name)

        # Now Playing Section
        if tags.get('title') or tags.get('artist'):
            now_playing_group = Adw.PreferencesGroup()
            now_playing_group.set_title('🎵 Currently Playing')
            now_playing_group.set_margin_bottom(12)

            if tags.get('title'):
                title_row = Adw.ActionRow()
                title_row.set_title('Title')
                title_row.set_subtitle(tags['title'])
                now_playing_group.add(title_row)

            if tags.get('artist'):
                artist_row = Adw.ActionRow()
                artist_row.set_title('Artist')
                artist_row.set_subtitle(tags['artist'])
                now_playing_group.add(artist_row)

            if tags.get('album'):
                album_row = Adw.ActionRow()
                album_row.set_title('Album')
                album_row.set_subtitle(tags['album'])
                now_playing_group.add(album_row)

            content_box.append(now_playing_group)

        # Station Information
        station_group = Adw.PreferencesGroup()
        station_group.set_title('📻 Station Information')
        station_group.set_margin_bottom(12)

        if station.get('country'):
            country_row = Adw.ActionRow()
            country_row.set_title('Country')
            country_row.set_subtitle(station['country'])
            station_group.add(country_row)

        if station.get('state'):
            state_row = Adw.ActionRow()
            state_row.set_title('State/Region')
            state_row.set_subtitle(station['state'])
            station_group.add(state_row)

        if station.get('language'):
            lang_row = Adw.ActionRow()
            lang_row.set_title('Language')
            lang_row.set_subtitle(', '.join(station['language']) if isinstance(station['language'], list) else station['language'])
            station_group.add(lang_row)

        if station.get('tags'):
            tags_text = ', '.join(station['tags']) if isinstance(station['tags'], list) else station['tags']
            if tags_text:
                tags_row = Adw.ActionRow()
                tags_row.set_title('Tags')
                tags_row.set_subtitle(tags_text)
                station_group.add(tags_row)

        content_box.append(station_group)

        # Technical Information
        tech_group = Adw.PreferencesGroup()
        tech_group.set_title('🔧 Technical Details')
        tech_group.set_margin_bottom(12)

        if station.get('codec'):
            codec_row = Adw.ActionRow()
            codec_row.set_title('Codec')
            codec_row.set_subtitle(station['codec'].upper())
            tech_group.add(codec_row)

        if station.get('bitrate'):
            bitrate_row = Adw.ActionRow()
            bitrate_row.set_title('Bitrate')
            bitrate_row.set_subtitle(f"{station['bitrate']} kbps")
            tech_group.add(bitrate_row)

        if station.get('homepage'):
            homepage_row = Adw.ActionRow()
            homepage_row.set_title('Homepage')
            homepage_row.set_subtitle(station['homepage'])

            # Copy button
            copy_btn = Gtk.Button()
            copy_btn.set_icon_name('edit-copy-symbolic')
            copy_btn.set_valign(Gtk.Align.CENTER)
            copy_btn.set_tooltip_text('Copy URL')
            copy_btn.connect('clicked', lambda b: self._copy_to_clipboard(station['homepage']))
            homepage_row.add_suffix(copy_btn)

            tech_group.add(homepage_row)

        if station.get('url_resolved') or station.get('url'):
            stream_url = station.get('url_resolved') or station.get('url')
            stream_row = Adw.ActionRow()
            stream_row.set_title('Stream URL')
            stream_row.set_subtitle(stream_url[:60] + '...' if len(stream_url) > 60 else stream_url)

            # Copy button
            copy_btn = Gtk.Button()
            copy_btn.set_icon_name('edit-copy-symbolic')
            copy_btn.set_valign(Gtk.Align.CENTER)
            copy_btn.set_tooltip_text('Copy URL')
            copy_btn.connect('clicked', lambda b: self._copy_to_clipboard(stream_url))
            stream_row.add_suffix(copy_btn)

            tech_group.add(stream_row)

        content_box.append(tech_group)

        # Statistics
        if station.get('votes') or station.get('clickcount'):
            stats_group = Adw.PreferencesGroup()
            stats_group.set_title('📊 Statistics')

            if station.get('votes'):
                votes_row = Adw.ActionRow()
                votes_row.set_title('Votes')
                votes_row.set_subtitle(str(station['votes']))
                stats_group.add(votes_row)

            if station.get('clickcount'):
                clicks_row = Adw.ActionRow()
                clicks_row.set_title('Total Clicks')
                clicks_row.set_subtitle(str(station['clickcount']))
                stats_group.add(clicks_row)

            content_box.append(stats_group)

        scrolled.set_child(content_box)
        main_box.append(scrolled)

        dialog.set_content(main_box)
        dialog.present()

    def _load_info_dialog_logo(self, url: str, image_widget: Gtk.Image):
        """Load logo for info dialog"""
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                GLib.idle_add(self._set_info_dialog_logo, image_widget, response.content)
        except:
            pass

    def _set_info_dialog_logo(self, image_widget: Gtk.Image, image_data: bytes):
        """Set logo in info dialog"""
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(image_data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf:
                scaled = pixbuf.scale_simple(128, 128, GdkPixbuf.InterpType.BILINEAR)
                texture = Gdk.Texture.new_for_pixbuf(scaled)
                image_widget.set_from_paintable(texture)
        except:
            pass

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard"""
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)

    def _load_history(self):
        """Load and display history"""
        # Clear existing items
        while True:
            row = self.history_listbox.get_row_at_index(0)
            if row is None:
                break
            self.history_listbox.remove(row)

        # Get recent history
        recent = self.history_manager.get_recent(limit=50)

        for entry in recent:
            # Entry contains all station data directly
            row = self._create_history_row(entry, entry)
            self.history_listbox.append(row)

        return False  # Don't repeat timeout

    def _create_history_row(self, station: dict, entry: dict):
        """Create a history list row"""
        row = Gtk.ListBoxRow()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Station logo
        logo = Gtk.Image()
        logo.set_pixel_size(48)
        logo.set_from_icon_name('audio-x-generic-symbolic')

        # Load favicon if available
        favicon_url = station.get('favicon')
        if favicon_url:
            self._load_history_logo(favicon_url, logo)

        box.append(logo)

        # Station info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_hexpand(True)

        name_label = Gtk.Label(label=station.get('name', 'Unknown'))
        name_label.set_xalign(0)
        name_label.add_css_class('heading')
        info_box.append(name_label)

        # Last played time
        import datetime
        timestamp = entry.get('timestamp')
        if timestamp:
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                time_ago = self._format_time_ago(dt)
                time_label = Gtk.Label(label=time_ago)
                time_label.set_xalign(0)
                time_label.set_opacity(0.7)
                info_box.append(time_label)
            except:
                pass

        box.append(info_box)

        # Play count badge
        play_count = entry.get('play_count', 1)
        if play_count > 1:
            count_label = Gtk.Label(label=f"×{play_count}")
            count_label.add_css_class('dim-label')
            count_label.set_margin_end(12)
            box.append(count_label)

        row.set_child(box)
        row.station_data = station
        return row

    def _load_history_logo(self, url: str, image_widget: Gtk.Image):
        """Load logo for history list"""
        def load_in_thread():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    GLib.idle_add(self._set_history_logo, image_widget, response.content)
            except:
                pass

        import threading
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()

    def _set_history_logo(self, image_widget: Gtk.Image, image_data: bytes):
        """Set logo in history row"""
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(image_data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf:
                scaled = pixbuf.scale_simple(48, 48, GdkPixbuf.InterpType.BILINEAR)
                texture = Gdk.Texture.new_for_pixbuf(scaled)
                image_widget.set_from_paintable(texture)
        except:
            pass

    def _format_time_ago(self, dt):
        """Format datetime as 'time ago' string"""
        import datetime
        now = datetime.datetime.now()
        diff = now - dt

        if diff.days > 0:
            unit = _('time_day') if diff.days == 1 else _('time_days')
            return f"{_('time_ago')} {diff.days} {unit}"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            unit = _('time_hour') if hours == 1 else _('time_hours')
            return f"{_('time_ago')} {hours} {unit}"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            unit = _('time_minute') if minutes == 1 else _('time_minutes')
            return f"{_('time_ago')} {minutes} {unit}"
        else:
            return _('time_just_now')

    def _on_clear_history(self, button):
        """Clear all history"""
        dialog = Adw.MessageDialog.new(self)
        dialog.set_heading(_("Clear History?"))
        dialog.set_body(_("This will remove all stations from your history. This action cannot be undone."))
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("clear", _("Clear"))
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_clear_history_response)
        dialog.present()

    def _on_clear_history_response(self, dialog, response):
        """Handle clear history dialog response"""
        if response == "clear":
            self.history_manager.clear_history()
            self._load_history()

    def _on_history_station_activated(self, listbox, row):
        """Handle history station activation"""
        if hasattr(row, 'station_data'):
            station = row.station_data
            print(f"Playing from history: {station.get('name')}")

            url = station.get('url_resolved') or station.get('url')
            if url:
                self.player.play(url, station)

                # Add to history
                self.history_manager.add_entry(station)
                self._load_history()  # Refresh history page

                # Update station info
                self.station_label.set_text(station.get('name', 'Unknown'))

                # Details are shown in Now Playing page (removed from player bar for cleaner UI)

                # Update now playing page
                self._update_now_playing_page()

                # Register click with API
                if station.get('stationuuid'):
                    import threading
                    threading.Thread(
                        target=self.api.register_click,
                        args=(station['stationuuid'],),
                        daemon=True
                    ).start()

    def _update_now_playing_page(self):
        """Update now playing page with current station info"""
        if self.player.is_playing() and self.player.current_station:
            station = self.player.current_station

            # Update station name
            self.np_station_label.set_label(station.get('name', 'Unknown Station'))

            # Update metadata
            tags = self.player.get_current_tags()
            if tags.get('title'):
                track_text = tags.get('title', '')
                if tags.get('artist'):
                    track_text = f"{tags.get('artist')} - {track_text}"
                self.np_track_label.set_label(track_text)
            else:
                self.np_track_label.set_label('')

            # Update details
            details = []
            if station.get('country'):
                details.append(station['country'])
            if station.get('bitrate'):
                details.append(f"{station['bitrate']} kbps")
            if station.get('codec'):
                details.append(station['codec'].upper())

            self.np_details_label.set_label(' • '.join(details))

            # Update logo
            if station.get('favicon'):
                self._load_np_logo(station['favicon'])
        else:
            self.np_station_label.set_label(_("No Station Playing"))
            self.np_track_label.set_label('')
            self.np_details_label.set_label('')
            self.np_logo.set_from_icon_name('audio-x-generic')

    def _load_np_logo(self, url: str):
        """Load logo for now playing page"""
        def load_in_thread():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    GLib.idle_add(self._set_np_logo, response.content)
            except:
                pass

        import threading
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()

    def _set_np_logo(self, image_data: bytes):
        """Set logo on now playing page"""
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(image_data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf:
                scaled = pixbuf.scale_simple(256, 256, GdkPixbuf.InterpType.BILINEAR)
                texture = Gdk.Texture.new_for_pixbuf(scaled)
                self.np_logo.set_from_paintable(texture)
        except:
            pass

    def _start_spectrum_animation(self):
        """Start spectrum animation with simulated data"""
        import random
        import math

        # Store previous values for smoother animation
        self.spectrum_phase = 0

        def update_spectrum():
            if not hasattr(self, 'spectrum_visualizer') or not self.spectrum_visualizer.is_active:
                return False

            # Generate more dynamic spectrum data with wave patterns
            magnitudes = []
            self.spectrum_phase += 0.15

            for i in range(80):  # Match num_bands
                # Create more realistic spectrum with bass emphasis
                # Low frequencies (bass) are typically louder
                freq_position = i / 80.0

                # Base level decreases with frequency
                base = -60 - (freq_position * 25)

                # Add wave patterns for visual interest
                wave1 = math.sin(self.spectrum_phase + i * 0.15) * 12
                wave2 = math.sin(self.spectrum_phase * 0.7 + i * 0.08) * 8
                wave3 = math.cos(self.spectrum_phase * 1.3 + i * 0.2) * 6

                # Random variation for natural feel
                variation = random.uniform(-8, 3)

                # Combine all components
                magnitude = base + wave1 + wave2 + wave3 + variation

                # Occasional peaks for dynamics
                if random.random() > 0.95:
                    magnitude += random.uniform(10, 20)

                magnitude = min(0, max(-80, magnitude))
                magnitudes.append(magnitude)

            self.spectrum_visualizer.set_spectrum_data(magnitudes)
            return True  # Continue animation

        # Update spectrum at ~30 FPS
        self.spectrum_timeout_id = GLib.timeout_add(33, update_spectrum)

    def _stop_spectrum_animation(self):
        """Stop spectrum animation"""
        if hasattr(self, 'spectrum_timeout_id') and self.spectrum_timeout_id:
            GLib.source_remove(self.spectrum_timeout_id)
            self.spectrum_timeout_id = None

    def _on_close_request(self, window):
        """Handle window close request"""
        # Save session state before closing
        self._save_session()

        # Check if player is playing
        if self.player.is_playing() and self.minimize_to_tray:
            # Hide window instead of closing - let app run in background
            print("Minimizing to background (player is running)")
            self.hide()

            # Update tray icon tooltip if available
            station = self.player.get_current_station()
            station_name = station.get('name', 'Radio') if station else 'Radio'
            if self.tray_icon.enabled:
                self.tray_icon.update_tooltip(f"WebRadio - {station_name}")

            # Return True to prevent window destruction
            return True
        else:
            # Allow window to close (will quit application)
            print("Closing window (no playback)")
            return False

    def _save_session(self):
        """Save current session state"""
        try:
            station = self.player.get_current_station()
            volume = self.player.get_volume()
            was_playing = self.player.is_playing()

            self.session_manager.save_session(station, volume, was_playing)
            logger.info("Session state saved")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    def _resume_session(self):
        """Resume previous session if available"""
        try:
            session = self.session_manager.load_session()

            if not session:
                logger.info("No session to resume")
                return False

            # Restore volume
            volume = session.get('volume', 1.0)
            self.player.set_volume(volume)
            if hasattr(self, 'volume_button'):
                self.volume_button.set_value(volume)

            # Restore station and playback if it was playing
            station = session.get('station')
            was_playing = session.get('was_playing', False)

            if station and was_playing:
                logger.info(f"Resuming station: {station.get('name')}")
                # Play the station
                self._play_station(station)

                toast = Adw.Toast.new(f"Resumed: {station.get('name', 'station')}")
                toast.set_timeout(3)
                self.add_toast(toast)

            elif station:
                # Just set up the UI without playing
                logger.info(f"Restoring station info (not playing): {station.get('name')}")
                self.player.set_current_station(station)
                self._update_now_playing_ui(station)

        except Exception as e:
            logger.error(f"Failed to resume session: {e}")

        return False  # Don't repeat this timeout

    def _update_now_playing_ui(self, station: dict):
        """Update UI with station info without playing"""
        if not station:
            return

        name = station.get('name', 'Unknown Station')
        self.station_label.set_text(name)

        # Update buttons
        if hasattr(self, 'play_button'):
            self.play_button.set_sensitive(True)

        if hasattr(self, 'fav_button'):
            uuid = station.get('stationuuid')
            if uuid:
                is_fav = self.favorites_manager.is_favorite(uuid)
                self.fav_button.set_active(is_fav)
                self.fav_button.set_sensitive(True)

        # Load favicon if available
        favicon = station.get('favicon')
        if favicon:
            self._load_favicon(favicon, lambda pixbuf: self.playing_logo.set_from_pixbuf(pixbuf))

    def _show_tray_unavailable_dialog(self):
        """Show dialog when tray is not available"""
        dialog = Adw.MessageDialog.new(self)
        dialog.set_heading("System Tray nicht verfügbar")

        # Check desktop environment
        import os
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()

        if 'gnome' in desktop:
            message = (
                "Unter GNOME benötigen Sie die AppIndicator Extension.\n\n"
                "Installation:\n"
                "1. Extension installieren:\n"
                "   sudo dnf install gnome-shell-extension-appindicator\n\n"
                "2. Extension aktivieren:\n"
                "   gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com\n\n"
                "3. GNOME neu starten (Alt+F2, dann 'r' eingeben)\n\n"
                "Ohne System Tray wird die App beim Schließen beendet.\n"
                "Möchten Sie jetzt schließen?"
            )
        else:
            message = (
                "Das System Tray ist auf Ihrem System nicht verfügbar.\n\n"
                "Benötigte Pakete:\n"
                "• libappindicator-gtk3\n"
                "• gir1.2-ayatanaappindicator3-0.1\n\n"
                "Ohne System Tray wird die App beim Schließen beendet.\n"
                "Möchten Sie jetzt schließen?"
            )

        dialog.set_body(message)
        dialog.add_response("cancel", "Abbrechen")
        dialog.add_response("close", "Schließen")
        dialog.set_response_appearance("close", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        dialog.connect("response", self._on_tray_dialog_response)
        dialog.present()

    def _on_tray_dialog_response(self, dialog, response):
        """Handle tray unavailable dialog response"""
        if response == "close":
            # User wants to close, stop playback and quit
            self.player.stop()
            self.get_application().quit()
        # If cancelled, do nothing (window stays open)

    # Manager signal handlers

    def _on_recording_started(self, recorder, file_path):
        """Handle recording started"""
        logger.info(f"Recording started: {file_path}")

        # Show toast notification
        toast = Adw.Toast.new(f"🔴 Recording started")
        toast.set_timeout(3)
        if hasattr(self, 'toast_overlay'):
            self.toast_overlay.add_toast(toast)

        # Send desktop notification
        if self.notification_manager:
            self.notification_manager.notify_recording_started(file_path)

        # Update record button icon to show recording state
        if hasattr(self, 'record_button'):
            self.record_button.set_icon_name('media-playback-stop-symbolic')
            self.record_button.add_css_class('recording-active')

    def _on_recording_stopped(self, recorder, file_path, duration):
        """Handle recording stopped"""
        logger.info(f"Recording stopped: {file_path} ({duration}s)")

        # Format duration
        mins = duration // 60
        secs = duration % 60
        duration_str = f"{mins}:{secs:02d}" if mins > 0 else f"{secs}s"

        # Show toast notification
        toast = Adw.Toast.new(f"⏹️ Recording saved ({duration_str})")
        toast.set_timeout(5)
        if hasattr(self, 'toast_overlay'):
            self.toast_overlay.add_toast(toast)

        # Send desktop notification
        if self.notification_manager:
            self.notification_manager.notify_recording_stopped(file_path, duration_str)

        # Update record button icon back to normal
        if hasattr(self, 'record_button'):
            self.record_button.set_icon_name('media-record-symbolic')
            self.record_button.remove_css_class('recording-active')

    def _on_sleep_timer_expired(self, timer):
        """Handle sleep timer expiration"""
        print("Sleep timer expired")
        # Timer handles the action automatically (stop/pause/quit)

    def _on_sleep_timer_action(self, action, parameter):
        """Handle sleep timer action"""
        minutes_str = parameter.get_string()
        minutes = int(minutes_str)

        if minutes > 0:
            self.sleep_timer.start(minutes)

            # Show toast notification
            toast = Adw.Toast.new(f"Sleep timer set for {minutes} minutes")
            toast.set_timeout(3)

            # Get toast overlay (assuming we're inside a window)
            if hasattr(self, 'toast_overlay'):
                self.toast_overlay.add_toast(toast)
            else:
                print(f"Sleep timer started: {minutes} minutes")

    def _on_sleep_timer_stop(self, action, parameter):
        """Stop sleep timer"""
        if self.sleep_timer.is_running():
            self.sleep_timer.stop()

            toast = Adw.Toast.new("Sleep timer stopped")
            toast.set_timeout(2)

            if hasattr(self, 'toast_overlay'):
                self.toast_overlay.add_toast(toast)
            else:
                print("Sleep timer stopped")

    def _on_spectrum_style_changed(self, settings, key):
        """Handle spectrum style change from settings"""
        if not hasattr(self, 'spectrum_visualizer'):
            return

        style = settings.get_string('spectrum-style')
        print(f"Spectrum style changed to: {style}")
        self.spectrum_visualizer.set_style(style)

    def _on_record_toggled(self, button):
        """Handle record button toggle"""
        if button.get_active():
            # Start recording
            if self.player.is_playing() and self.player.current_station:
                station = self.player.current_station
                tags = self.player.get_current_tags()

                # Note: recording will be implemented later with proper pipeline
                # For now, just show it's "recording"
                self.recording_label.set_label('REC')
                self.recording_label.set_visible(True)
                button.set_tooltip_text(_('Stop Recording'))

                print(f"Recording started (placeholder): {station.get('name')}")
        else:
            # Stop recording
            self.recording_label.set_visible(False)
            button.set_tooltip_text(_('Start Recording'))

            print("Recording stopped (placeholder)")

    def _on_recording_started(self, recorder, file_path):
        """Handle recording started"""
        self.record_button.set_active(True)
        self.recording_label.set_label('REC')
        self.recording_label.set_visible(True)

        print(f"Recording to: {file_path}")

    def _on_recording_stopped(self, recorder, file_path, duration):
        """Handle recording stopped"""
        self.record_button.set_active(False)
        self.recording_label.set_visible(False)

        # Show notification
        toast = Adw.Toast.new(f"Recording saved: {duration}s")
        toast.set_timeout(5)

        if hasattr(self, 'toast_overlay'):
            self.toast_overlay.add_toast(toast)

        print(f"Recording saved: {file_path} ({duration}s)")

    def _on_play_station(self, station):
        """Play a station and add to history"""
        # Call existing play functionality
        self._play_station(station)

        # Add to history
        tags = self.player.get_current_tags()
        self.history_manager.add_entry(station, tags)

    # Local Music Handlers

    def _load_local_tracks(self):
        """Load and display local music tracks"""
        tracks = self.music_library.get_all_tracks()

        # Clear existing rows
        child = self.music_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.music_listbox.remove(child)
            child = next_child

        # Add tracks
        for track in tracks:
            row = MusicTrackRow(track)
            self.music_listbox.append(row)

        # Update status
        if tracks:
            self.library_status_label.set_label(_('tracks_found', count=len(tracks)))
        else:
            self.library_status_label.set_label('')

    def _on_add_music_folder(self, button):
        """Handle add music folder button"""
        dialog = Gtk.FileDialog()
        dialog.set_title(_("add_music_folder"))
        dialog.select_folder(self, None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        """Handle folder selection"""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                print(f"Adding music folder: {path}")
                self.music_library.add_music_path(path)

                # Automatically scan after adding
                self._on_scan_library(None)
        except Exception as e:
            print(f"Folder selection error: {e}")

    def _on_scan_library(self, button):
        """Start library scan"""
        if self.music_library.is_scanning:
            print("Scan already in progress")
            return

        # Update UI
        if button:
            self.scan_button.set_sensitive(False)
        self.library_status_label.set_label(_('scanning_library'))

        # Start scan with callback
        def scan_callback(count, done=False):
            if done:
                GLib.idle_add(self._on_scan_complete, count)
            else:
                GLib.idle_add(self.library_status_label.set_label, _('scanning_library') + f" ({count})")

        self.music_library.scan_library(callback=scan_callback)

    def _on_scan_complete(self, count):
        """Handle scan completion"""
        print(f"Scan complete: {count} tracks")
        self.scan_button.set_sensitive(True)
        self.library_status_label.set_label(_('tracks_found', count=count))

        # Reload track list
        self._load_local_tracks()

    def _on_local_track_activated(self, listbox, row):
        """Play selected local track"""
        if isinstance(row, MusicTrackRow):
            track = row.track
            file_uri = f"file://{track['path']}"

            # Create station-like info for player
            station_info = {
                'name': track['title'],
                'artist': track['artist'],
                'album': track['album']
            }

            print(f"Playing local track: {track['title']} - {track['artist']}")
            self.player.play(file_uri, station_info)

            # Update now playing UI
            self._update_now_playing_page()

    # YouTube Search Handlers

    def _on_youtube_search(self, widget):
        """Handle YouTube search"""
        query = self.youtube_search_entry.get_text().strip()
        if not query:
            return

        print(f"Searching YouTube: {query}")

        # Reset for new search
        self.youtube_current_query = query
        self.youtube_current_offset = 0
        self.youtube_all_videos = []

        # Clear existing results
        child = self.youtube_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.youtube_listbox.remove(child)
            child = next_child

        # Show loading indicator
        loading_row = Gtk.ListBoxRow()
        loading_label = Gtk.Label(label="Suche läuft...")
        loading_label.set_margin_start(12)
        loading_label.set_margin_end(12)
        loading_label.set_margin_top(12)
        loading_label.set_margin_bottom(12)
        loading_row.set_child(loading_label)
        self.youtube_listbox.append(loading_row)

        # Search in background thread
        self._load_more_youtube_results()

    def _load_more_youtube_results(self):
        """Load more YouTube results in background"""
        if self.youtube_loading or not self.youtube_current_query:
            return

        self.youtube_loading = True

        def search_thread():
            # Fetch next batch
            videos = self.youtube_music.search(self.youtube_current_query, max_results=20)
            GLib.idle_add(self._append_youtube_results, videos)

        threading.Thread(target=search_thread, daemon=True).start()

    def _append_youtube_results(self, new_videos):
        """Append new YouTube results to the list"""
        # Remove loading indicator if present
        child = self.youtube_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            if isinstance(child.get_child(), Gtk.Label):
                label = child.get_child()
                if label.get_label() in ["Suche läuft...", "Lade mehr..."]:
                    self.youtube_listbox.remove(child)
                    break
            child = next_child

        # Store all videos
        self.youtube_all_videos.extend(new_videos)

        # Apply duration filter and add rows
        filtered_videos = self._filter_youtube_videos(new_videos)
        for video in filtered_videos:
            row = YouTubeVideoRow(video)
            self.youtube_listbox.append(row)

        print(f"Appended {len(filtered_videos)} YouTube videos (total: {len(self.youtube_all_videos)})")

        self.youtube_loading = False
        return False

    def _filter_youtube_videos(self, videos):
        """Filter videos by minimum duration"""
        selected = self.youtube_duration_filter.get_selected()

        # Map selection to minimum seconds
        min_duration = {
            0: 0,      # Alle
            1: 300,    # 5 min
            2: 600,    # 10 min
            3: 1200,   # 20 min
            4: 1800    # 30 min
        }.get(selected, 0)

        if min_duration == 0:
            return videos

        return [v for v in videos if v.get('duration', 0) >= min_duration]

    def _on_youtube_filter_changed(self, dropdown, param):
        """Handle duration filter change - refilter existing results"""
        # Clear displayed results
        child = self.youtube_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.youtube_listbox.remove(child)
            child = next_child

        # Reapply filter to all videos
        filtered_videos = self._filter_youtube_videos(self.youtube_all_videos)
        for video in filtered_videos:
            row = YouTubeVideoRow(video)
            self.youtube_listbox.append(row)

        print(f"Filtered to {len(filtered_videos)} videos")

    def _on_youtube_scroll(self, adjustment):
        """Handle scroll event for infinite scrolling"""
        value = adjustment.get_value()
        upper = adjustment.get_upper()
        page_size = adjustment.get_page_size()

        # Load more when scrolled to 80% of content
        if value + page_size >= upper * 0.8:
            if not self.youtube_loading and self.youtube_current_query:
                print("Near bottom, loading more YouTube results...")

                # Add loading indicator
                loading_row = Gtk.ListBoxRow()
                loading_label = Gtk.Label(label="Lade mehr...")
                loading_label.set_margin_start(12)
                loading_label.set_margin_end(12)
                loading_label.set_margin_top(12)
                loading_label.set_margin_bottom(12)
                loading_row.set_child(loading_label)
                self.youtube_listbox.append(loading_row)

                self._load_more_youtube_results()

    def _display_youtube_results(self, videos):
        """Display YouTube search results (deprecated - use _append_youtube_results)"""
        # This function is kept for compatibility but shouldn't be used anymore
        self._append_youtube_results(videos)

    def _on_youtube_video_activated(self, listbox, row):
        """Play selected YouTube video"""
        if isinstance(row, YouTubeVideoRow):
            video = row.video
            video_url = video.get('url', '')

            print(f"Getting audio stream for: {video['title']}")

            # Show loading indicator in now playing
            GLib.idle_add(self.station_label.set_label, "Loading YouTube audio...")

            # Disable UI to prevent multiple clicks
            GLib.idle_add(self.youtube_listbox.set_sensitive, False)

            # Get audio URL in background thread
            def get_audio_thread():
                try:
                    print(f"Fetching audio URL for: {video_url}")
                    audio_url = self.youtube_music.get_audio_url(video_url)

                    if audio_url:
                        # Create station-like info for player with YouTube thumbnail
                        station_info = {
                            'name': video['title'],
                            'artist': video.get('channel', 'YouTube'),
                            'url': video_url,  # Original YouTube watch URL for recording
                            'favicon': video.get('thumbnail', ''),  # Add thumbnail for MPRIS
                            'is_youtube': True  # Flag for YouTube recording
                        }

                        print(f"Got audio URL, playing: {video['title']}")

                        # Play in main thread
                        def play_audio():
                            self.player.play(audio_url, station_info)
                            self._update_now_playing_page()

                            # Enable player controls (including recording for YouTube!)
                            self.play_button.set_sensitive(True)
                            self.stop_button.set_sensitive(True)
                            self.fav_button.set_sensitive(False)  # No favorites for YouTube
                            self.record_button.set_sensitive(True)  # Enable recording for YouTube

                            # Re-enable YouTube list
                            self.youtube_listbox.set_sensitive(True)

                            # Update station and metadata labels
                            self.station_label.set_text(video['title'])
                            self.metadata_label.set_text(video.get('channel', 'YouTube'))

                            # Update "Now Playing" page with YouTube thumbnail
                            self.np_station_label.set_text(video['title'])
                            self.np_track_label.set_text(video.get('channel', 'YouTube'))

                            # Load YouTube thumbnail for "Now Playing" page AND player bar
                            thumbnail_url = video.get('thumbnail', '')
                            if thumbnail_url:
                                self._load_youtube_thumbnail_for_now_playing(thumbnail_url)
                                self._load_youtube_thumbnail_for_player_bar(thumbnail_url)
                            else:
                                self.np_logo.set_from_icon_name('multimedia-player-symbolic')
                                self.logo_image.set_from_icon_name('multimedia-player-symbolic')

                            # Update MPRIS metadata with YouTube thumbnail
                            if self.mpris:
                                self.mpris.update_metadata()

                            return False

                        GLib.idle_add(play_audio)
                    else:
                        print("Failed to get audio URL")
                        def show_error():
                            self.station_label.set_label("Failed to load YouTube audio")
                            self.youtube_listbox.set_sensitive(True)
                            return False
                        GLib.idle_add(show_error)
                except Exception as e:
                    print(f"Error in YouTube playback: {e}")
                    def show_error():
                        self.station_label.set_label(f"Error: {str(e)}")
                        self.youtube_listbox.set_sensitive(True)
                        return False
                    GLib.idle_add(show_error)

            threading.Thread(target=get_audio_thread, daemon=True).start()

    def _load_youtube_thumbnail_for_now_playing(self, url: str):
        """Load YouTube thumbnail for the Now Playing page"""
        import threading
        import urllib.request
        from gi.repository import GdkPixbuf, Gio

        def download_and_set():
            try:
                print(f"Loading Now Playing thumbnail from: {url}")

                # Download thumbnail
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                response = urllib.request.urlopen(req, timeout=10)
                data = response.read()

                print(f"Downloaded {len(data)} bytes for Now Playing thumbnail")

                # Load into pixbuf
                input_stream = Gio.MemoryInputStream.new_from_data(data, None)
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream(input_stream, None)

                print(f"Loaded Now Playing pixbuf: {pixbuf.get_width()}x{pixbuf.get_height()}")

                # Scale to fit the Now Playing logo size (256x256)
                target_size = 256

                orig_width = pixbuf.get_width()
                orig_height = pixbuf.get_height()

                # Scale to fit within 256x256 while maintaining aspect ratio
                scale = min(target_size / orig_width, target_size / orig_height)
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)

                scaled_pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)

                print(f"Scaled Now Playing thumbnail from {orig_width}x{orig_height} to {new_width}x{new_height}")

                # Set image in main thread using Gdk.Texture (GTK4 way)
                def set_thumbnail():
                    texture = Gdk.Texture.new_for_pixbuf(scaled_pixbuf)
                    self.np_logo.set_from_paintable(texture)
                    print(f"Now Playing thumbnail applied: {new_width}x{new_height}")
                    return False

                GLib.idle_add(set_thumbnail)
                print("Now Playing thumbnail set successfully")

            except Exception as e:
                print(f"Failed to load Now Playing thumbnail from {url}: {e}")
                # Fallback to icon
                def set_fallback():
                    self.np_logo.set_from_icon_name('multimedia-player-symbolic')
                    self.np_logo.set_pixel_size(256)
                    return False
                GLib.idle_add(set_fallback)

        threading.Thread(target=download_and_set, daemon=True).start()

    def _load_youtube_thumbnail_for_player_bar(self, url: str):
        """Load YouTube thumbnail for the player bar (bottom left logo)"""
        import threading
        import urllib.request
        from gi.repository import GdkPixbuf, Gio

        def download_and_set():
            try:
                print(f"Loading player bar thumbnail from: {url}")

                # Download thumbnail
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                response = urllib.request.urlopen(req, timeout=10)
                data = response.read()

                print(f"Downloaded {len(data)} bytes for player bar thumbnail")

                # Load into pixbuf
                input_stream = Gio.MemoryInputStream.new_from_data(data, None)
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream(input_stream, None)

                print(f"Loaded player bar pixbuf: {pixbuf.get_width()}x{pixbuf.get_height()}")

                # Scale to fit the player bar logo size (48x48)
                target_size = 48

                orig_width = pixbuf.get_width()
                orig_height = pixbuf.get_height()

                # Scale to fit within 48x48 while maintaining aspect ratio
                scale = min(target_size / orig_width, target_size / orig_height)
                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)

                scaled_pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)

                print(f"Scaled player bar thumbnail from {orig_width}x{orig_height} to {new_width}x{new_height}")

                # Set image in main thread using Gdk.Texture (GTK4 way)
                def set_thumbnail():
                    if hasattr(self, 'logo_image'):
                        texture = Gdk.Texture.new_for_pixbuf(scaled_pixbuf)
                        self.logo_image.set_from_paintable(texture)
                        print(f"Player bar thumbnail applied: {new_width}x{new_height}")
                    return False

                GLib.idle_add(set_thumbnail)
                print("Player bar thumbnail set successfully")

            except Exception as e:
                print(f"Failed to load player bar thumbnail from {url}: {e}")
                # Fallback to icon
                def set_fallback():
                    if hasattr(self, 'logo_image'):
                        self.logo_image.set_from_icon_name('multimedia-player-symbolic')
                        self.logo_image.set_pixel_size(48)
                    return False
                GLib.idle_add(set_fallback)

        threading.Thread(target=download_and_set, daemon=True).start()

    # Seek bar functions

    def _on_seek_changed(self, scale, scroll_type, value):
        """Handle seek bar value change - only when user interacts"""
        if not self.is_seekable:
            return False

        print(f"Seeking to position: {value}%")

        # Convert percentage to nanoseconds
        if hasattr(self.player, 'playbin'):
            success, duration = self.player.playbin.query_duration(Gst.Format.TIME)
            if success and duration > 0:
                position = int((value / 100.0) * duration)
                self.player.playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, position)

        return False  # Allow default handler to update the scale

    def _start_position_updates(self):
        """Start timer to update seek bar position"""
        if self.position_update_timer:
            return  # Already running

        def update_position():
            if not hasattr(self.player, 'playbin'):
                return False

            # Query duration and position
            success_dur, duration = self.player.playbin.query_duration(Gst.Format.TIME)
            success_pos, position = self.player.playbin.query_position(Gst.Format.TIME)

            if success_dur and duration > 0:
                # Stream is seekable
                self.is_seekable = True
                self.seek_scale.set_sensitive(True)

                # Update total time
                total_seconds = duration // Gst.SECOND
                total_mins = total_seconds // 60
                total_secs = total_seconds % 60
                self.total_time_label.set_text(f"{total_mins}:{total_secs:02d}")

                if success_pos:
                    # Update current time
                    current_seconds = position // Gst.SECOND
                    current_mins = current_seconds // 60
                    current_secs = current_seconds % 60
                    self.current_time_label.set_text(f"{current_mins}:{current_secs:02d}")

                    # Update seek bar position (change-value won't trigger on set_value)
                    percentage = (position / duration) * 100
                    self.seek_scale.set_value(percentage)
            else:
                # Stream is not seekable (live radio)
                self.is_seekable = False
                self.seek_scale.set_sensitive(False)
                self.current_time_label.set_text("Live")
                self.total_time_label.set_text("")

            return True  # Keep timer running

        # Update every 500ms
        self.position_update_timer = GLib.timeout_add(500, update_position)

    def _stop_position_updates(self):
        """Stop position update timer"""
        if self.position_update_timer:
            try:
                GLib.source_remove(self.position_update_timer)
            except:
                pass  # Timer was already removed
            self.position_update_timer = None

        # Reset UI
        self.seek_scale.set_value(0)
        self.seek_scale.set_sensitive(False)
        self.current_time_label.set_text("0:00")
        self.total_time_label.set_text("0:00")
        self.is_seekable = False
