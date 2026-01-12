"""
Discover Page Component for Gnome Web Radio

This module contains the DiscoverPage component for browsing and searching radio stations.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from webradio.logger import get_logger
from webradio.i18n import _

logger = get_logger(__name__)


class DiscoverPage(Gtk.Box):
    """
    Discover page component for browsing and searching radio stations.

    This component provides:
    - Search functionality for stations
    - Country filter dropdown
    - Quick filter buttons (Top Voted, Rock, Pop, Jazz)
    - Infinite scrolling station list
    """

    def __init__(
        self,
        on_search_activate,
        on_search_changed,
        on_country_changed,
        on_load_top_stations,
        on_load_by_tag,
        on_station_scroll,
        on_station_activated
    ):
        """
        Initialize the DiscoverPage component.

        Args:
            on_search_activate: Callback when search is activated (entry or button)
            on_search_changed: Callback when search text changes
            on_country_changed: Callback when country filter changes
            on_load_top_stations: Callback to load top voted stations
            on_load_by_tag: Callback to load stations by tag (tag parameter)
            on_station_scroll: Callback for infinite scrolling
            on_station_activated: Callback when station row is activated
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        logger.info("Initializing DiscoverPage component")

        # Store callbacks
        self._on_search_activate = on_search_activate
        self._on_search_changed = on_search_changed
        self._on_country_changed = on_country_changed
        self._on_load_top_stations = on_load_top_stations
        self._on_load_by_tag = on_load_by_tag
        self._on_station_scroll = on_station_scroll
        self._on_station_activated = on_station_activated

        # Search state
        self.search_timeout_id = None
        self.global_search_timeout_id = None

        # Infinite scrolling state
        self.current_offset = 0
        self.stations_per_page = 50
        self.is_loading_more = False
        self.has_more_stations = True
        self.current_filter_type = None  # 'top', 'tag', 'search', etc.
        self.current_filter_value = None

        # Store country names for filtering
        self.country_names = [""]  # Empty string for "All Countries"

        # Setup UI
        self.set_margin_start(18)
        self.set_margin_end(18)
        self.set_margin_top(18)
        self.set_margin_bottom(18)
        self.add_css_class('content-page')

        self._build_ui()

    def _build_ui(self):
        """Build the UI components"""
        # Search box
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text(_('search_placeholder'))
        self.search_entry.set_hexpand(True)
        self.search_entry.connect('activate', self._on_search_activate)
        self.search_entry.connect('changed', self._on_search_changed)
        search_box.append(self.search_entry)

        search_btn = Gtk.Button(label=_('search_button'))
        search_btn.add_css_class('pill')
        search_btn.connect('clicked', self._on_search_activate)
        search_box.append(search_btn)

        self.append(search_box)

        # Country filter dropdown
        country_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        country_label = Gtk.Label(label=_("Country:"))
        country_box.append(country_label)

        # Create country dropdown
        self.country_store = Gtk.StringList()
        self.country_store.append(_("All Countries"))

        self.country_dropdown = Gtk.DropDown()
        self.country_dropdown.set_model(self.country_store)
        self.country_dropdown.set_hexpand(True)
        self.country_dropdown.connect('notify::selected', self._on_country_changed)
        country_box.append(self.country_dropdown)

        self.append(country_box)

        # Filter buttons
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        filters = [
            (_('filter_top_voted'), self._on_load_top_stations),
            (_('filter_rock'), lambda b: self._on_load_by_tag('rock')),
            (_('filter_pop'), lambda b: self._on_load_by_tag('pop')),
            (_('filter_jazz'), lambda b: self._on_load_by_tag('jazz')),
        ]

        for label, callback in filters:
            btn = Gtk.Button(label=label)
            btn.add_css_class('pill')
            btn.connect('clicked', callback)
            filter_box.append(btn)

        self.append(filter_box)

        # Station list with infinite scrolling
        self.station_scrolled = Gtk.ScrolledWindow()
        self.station_scrolled.set_vexpand(True)
        self.station_scrolled.set_min_content_height(300)

        # Connect to scroll event for infinite scrolling
        vadjustment = self.station_scrolled.get_vadjustment()
        vadjustment.connect('value-changed', self._on_station_scroll)

        self.station_listbox = Gtk.ListBox()
        self.station_listbox.connect('row-activated', self._on_station_activated)

        # Status page placeholder
        discover_placeholder = Adw.StatusPage()
        discover_placeholder.set_icon_name('radio-symbolic')
        discover_placeholder.set_title(_('No Stations Loaded'))
        discover_placeholder.set_description(_('Click "Top Voted" to browse popular stations'))
        self.station_listbox.set_placeholder(discover_placeholder)

        self.station_scrolled.set_child(self.station_listbox)
        self.append(self.station_scrolled)

    def _on_load_top_stations(self, widget):
        """Wrapper for top stations callback"""
        self._on_load_top_stations()

    def get_station_listbox(self):
        """Get the station listbox widget for external access"""
        return self.station_listbox

    def get_search_entry(self):
        """Get the search entry widget for external access"""
        return self.search_entry

    def get_country_dropdown(self):
        """Get the country dropdown widget for external access"""
        return self.country_dropdown

    def get_country_store(self):
        """Get the country store for external access"""
        return self.country_store

    def add_country(self, country_name: str):
        """Add a country to the dropdown"""
        self.country_store.append(country_name)
        self.country_names.append(country_name)

    def clear_countries(self):
        """Clear all countries from dropdown (except 'All Countries')"""
        # Remove all but the first item
        while self.country_store.get_n_items() > 1:
            self.country_store.remove(1)
        self.country_names = [""]

    def reset_pagination(self):
        """Reset pagination state"""
        self.current_offset = 0
        self.has_more_stations = True
        self.is_loading_more = False

    def set_filter_state(self, filter_type: str, filter_value=None):
        """
        Set the current filter state for pagination.

        Args:
            filter_type: Type of filter ('top', 'tag', 'search')
            filter_value: Optional value (e.g., tag name for 'tag' filter)
        """
        self.current_filter_type = filter_type
        self.current_filter_value = filter_value
        logger.debug(f"Filter state set to: {filter_type} = {filter_value}")

    def increment_offset(self):
        """Increment pagination offset"""
        self.current_offset += self.stations_per_page

    def set_loading_state(self, is_loading: bool):
        """Set loading state for infinite scroll"""
        self.is_loading_more = is_loading

    def set_has_more(self, has_more: bool):
        """Set whether more stations are available"""
        self.has_more_stations = has_more
