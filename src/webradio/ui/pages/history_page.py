"""
History Page Component for Gnome Web Radio

This module contains the HistoryPage component for displaying recently played stations.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from webradio.logger import get_logger
from webradio.i18n import _

logger = get_logger(__name__)


class HistoryPage(Gtk.Box):
    """
    History page component for displaying recently played stations.

    This component provides:
    - List of recently played stations
    - Clear history button
    - Activation callback for replaying stations
    - Placeholder for empty state
    """

    def __init__(self, on_station_activated, on_clear_history, on_load_history):
        """
        Initialize the HistoryPage component.

        Args:
            on_station_activated: Callback when a history station is activated
            on_clear_history: Callback when clear history button is clicked
            on_load_history: Callback to load history on initialization
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        logger.info("Initializing HistoryPage component")

        # Store callbacks
        self._on_station_activated = on_station_activated
        self._on_clear_history = on_clear_history
        self._on_load_history = on_load_history

        # Setup UI
        self.set_margin_start(18)
        self.set_margin_end(18)
        self.set_margin_top(18)
        self.set_margin_bottom(18)
        self.add_css_class('content-page')

        self._build_ui()

        # Note: Don't load history here - let the window load it after UI is ready

    def _build_ui(self):
        """Build the UI components"""
        # Header with clear button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        title_label = Gtk.Label(label=_("Recently Played"))
        title_label.set_xalign(0)
        title_label.set_hexpand(True)
        title_label.add_css_class('title-2')
        header_box.append(title_label)

        clear_button = Gtk.Button(label=_("Clear History"))
        clear_button.add_css_class('pill')
        clear_button.connect('clicked', self._on_clear_history)
        header_box.append(clear_button)

        self.append(header_box)

        # History list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        self.history_listbox = Gtk.ListBox()
        self.history_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.history_listbox.connect('row-activated', self._on_station_activated)

        # Placeholder for empty history
        placeholder = Adw.StatusPage()
        placeholder.set_icon_name('document-open-recent-symbolic')
        placeholder.set_title(_("No History"))
        placeholder.set_description(_("Stations you play will appear here"))
        self.history_listbox.set_placeholder(placeholder)

        scrolled.set_child(self.history_listbox)
        self.append(scrolled)

    def get_listbox(self):
        """Get the history listbox widget for external access"""
        return self.history_listbox

    def clear(self):
        """Clear all items from the history list"""
        child = self.history_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.history_listbox.remove(child)
            child = next_child
        logger.debug("History list cleared")

    def add_station_row(self, row):
        """
        Add a station row to the history list.

        Args:
            row: Gtk.ListBoxRow to add
        """
        self.history_listbox.append(row)

    def get_row_count(self):
        """Get the number of history items"""
        count = 0
        child = self.history_listbox.get_first_child()
        while child:
            count += 1
            child = child.get_next_sibling()
        return count
