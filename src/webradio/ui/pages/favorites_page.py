"""
Favorites Page Component for Gnome Web Radio

This module contains the FavoritesPage component for managing favorite stations.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from webradio.logger import get_logger
from webradio.i18n import _

logger = get_logger(__name__)


class FavoritesPage(Gtk.Box):
    """
    Favorites page component for displaying and managing favorite stations.

    This component provides:
    - List of favorite stations
    - Activation callback for playing favorites
    - Placeholder for empty state
    """

    def __init__(self, on_station_activated, on_load_favorites, on_export=None, on_import=None):
        """
        Initialize the FavoritesPage component.

        Args:
            on_station_activated: Callback when a favorite station is activated
            on_load_favorites: Callback to load favorites on initialization
            on_export: Callback for exporting favorites (optional)
            on_import: Callback for importing favorites (optional)
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        logger.info("Initializing FavoritesPage component")

        # Store callbacks
        self._on_station_activated = on_station_activated
        self._on_load_favorites = on_load_favorites
        self._on_export = on_export
        self._on_import = on_import

        # Setup UI
        self.set_margin_start(18)
        self.set_margin_end(18)
        self.set_margin_top(18)
        self.set_margin_bottom(18)
        self.add_css_class('content-page')

        self._build_ui()

        # Note: Don't load favorites here - let the window load them after UI is ready

    def _build_ui(self):
        """Build the UI components"""
        # Header with export/import buttons (only if callbacks provided)
        if self._on_export or self._on_import:
            header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            header_box.set_margin_bottom(12)

            title_label = Gtk.Label(label=_("Favorites"))
            title_label.set_xalign(0)
            title_label.set_hexpand(True)
            title_label.add_css_class('title-2')
            header_box.append(title_label)

            # Import/Export button box
            button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            button_box.add_css_class('linked')

            if self._on_import:
                import_button = Gtk.Button()
                import_button.set_icon_name('document-open-symbolic')
                import_button.set_tooltip_text(_('Import favorites from OPML/M3U'))
                import_button.connect('clicked', lambda b: self._on_import())
                button_box.append(import_button)

            if self._on_export:
                export_button = Gtk.Button()
                export_button.set_icon_name('document-save-symbolic')
                export_button.set_tooltip_text(_('Export favorites to OPML/M3U'))
                export_button.connect('clicked', lambda b: self._on_export())
                button_box.append(export_button)

            header_box.append(button_box)
            self.append(header_box)

        # Favorites list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        self.favorites_listbox = Gtk.ListBox()
        self.favorites_listbox.connect('row-activated', self._on_station_activated)

        # Status page placeholder
        favorites_placeholder = Adw.StatusPage()
        favorites_placeholder.set_icon_name('starred-symbolic')
        favorites_placeholder.set_title(_('No Favorites'))
        favorites_placeholder.set_description(_('Click the star icon on a station to add it to favorites'))
        self.favorites_listbox.set_placeholder(favorites_placeholder)

        scrolled.set_child(self.favorites_listbox)
        self.append(scrolled)

    def get_listbox(self):
        """Get the favorites listbox widget for external access"""
        return self.favorites_listbox

    def clear(self):
        """Clear all items from the favorites list"""
        child = self.favorites_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.favorites_listbox.remove(child)
            child = next_child
        logger.debug("Favorites list cleared")

    def add_station_row(self, row):
        """
        Add a station row to the favorites list.

        Args:
            row: Gtk.ListBoxRow to add
        """
        self.favorites_listbox.append(row)

    def get_row_count(self):
        """Get the number of favorite stations"""
        count = 0
        child = self.favorites_listbox.get_first_child()
        while child:
            count += 1
            child = child.get_next_sibling()
        return count
