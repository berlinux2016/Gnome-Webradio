"""
YouTube Page Component for Gnome Web Radio

This module contains the YouTubePage component for searching and playing YouTube videos.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from webradio.logger import get_logger
from webradio.i18n import _

logger = get_logger(__name__)


class YouTubePage(Gtk.Box):
    """
    YouTube page component for searching and playing YouTube videos.

    This component provides:
    - YouTube search functionality
    - Duration filter dropdown
    - Infinite scrolling results list
    - Error handling for missing yt-dlp
    """

    def __init__(
        self,
        youtube_music,
        on_search,
        on_filter_changed,
        on_scroll,
        on_video_activated
    ):
        """
        Initialize the YouTubePage component.

        Args:
            youtube_music: YouTubeMusic instance for checking availability
            on_search: Callback when search is activated
            on_filter_changed: Callback when duration filter changes
            on_scroll: Callback for infinite scrolling
            on_video_activated: Callback when video row is activated
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        logger.info("Initializing YouTubePage component")

        # Store references
        self.youtube_music = youtube_music
        self._on_search = on_search
        self._on_filter_changed = on_filter_changed
        self._on_scroll = on_scroll
        self._on_video_activated = on_video_activated

        # Setup UI
        self.set_margin_start(18)
        self.set_margin_end(18)
        self.set_margin_top(18)
        self.set_margin_bottom(18)
        self.add_css_class('content-page')

        self._build_ui()

    def _build_ui(self):
        """Build the UI components"""
        # Title
        title = Gtk.Label(label=_("youtube_title"))
        title.add_css_class('title-2')
        title.set_xalign(0)
        self.append(title)

        # Check if yt-dlp is available
        if not self.youtube_music.is_available():
            # Show error message if yt-dlp is not installed
            status_page = Adw.StatusPage()
            status_page.set_icon_name('dialog-error-symbolic')
            status_page.set_title("yt-dlp not found")
            status_page.set_description("Please install yt-dlp to use YouTube Search:\npip install yt-dlp")
            self.append(status_page)
            return

        # Search box
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.youtube_search_entry = Gtk.Entry()
        self.youtube_search_entry.set_placeholder_text(_('youtube_search'))
        self.youtube_search_entry.set_hexpand(True)
        self.youtube_search_entry.connect('activate', self._on_search)
        search_box.append(self.youtube_search_entry)

        search_btn = Gtk.Button(label=_('search_button'))
        search_btn.add_css_class('pill')
        search_btn.connect('clicked', self._on_search)
        search_box.append(search_btn)

        self.append(search_box)

        # Filter box for minimum duration
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        filter_box.set_margin_top(6)

        filter_label = Gtk.Label(label="Mindestlänge:")
        filter_box.append(filter_label)

        # Dropdown for duration filter
        self.youtube_duration_filter = Gtk.DropDown()
        duration_options = Gtk.StringList()
        duration_options.append("Alle")
        duration_options.append("Min. 5 Minuten")
        duration_options.append("Min. 10 Minuten")
        duration_options.append("Min. 20 Minuten")
        duration_options.append("Min. 30 Minuten")
        self.youtube_duration_filter.set_model(duration_options)
        self.youtube_duration_filter.set_selected(0)
        self.youtube_duration_filter.connect('notify::selected', self._on_filter_changed)
        filter_box.append(self.youtube_duration_filter)

        self.append(filter_box)

        # Column headers (like Excel) - match radio station layout
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_start(12)
        header_box.set_margin_end(12)
        header_box.set_margin_top(8)
        header_box.set_margin_bottom(4)

        # Thumbnail column header (48px like radio logos)
        thumbnail_header = Gtk.Label(label="")
        thumbnail_header.set_xalign(0)
        thumbnail_header.set_size_request(48, -1)
        header_box.append(thumbnail_header)

        # Title column header
        title_header = Gtk.Label(label="Titel")
        title_header.set_xalign(0)
        title_header.set_hexpand(True)
        title_header.add_css_class('heading')
        header_box.append(title_header)

        # Duration column header
        duration_header = Gtk.Label(label="Dauer")
        duration_header.set_xalign(0)
        duration_header.set_size_request(60, -1)
        duration_header.add_css_class('heading')
        header_box.append(duration_header)

        self.append(header_box)

        # Results list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        # Connect to scroll event for infinite scrolling
        vadj = scrolled.get_vadjustment()
        vadj.connect('value-changed', self._on_scroll)

        self.youtube_listbox = Gtk.ListBox()
        self.youtube_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.youtube_listbox.connect('row-activated', self._on_video_activated)

        # Placeholder
        placeholder = Adw.StatusPage()
        placeholder.set_icon_name('multimedia-player-symbolic')
        placeholder.set_title(_("youtube_title"))
        placeholder.set_description(_("youtube_search"))
        self.youtube_listbox.set_placeholder(placeholder)

        scrolled.set_child(self.youtube_listbox)
        self.append(scrolled)

    def get_listbox(self):
        """Get the YouTube listbox widget for external access"""
        return self.youtube_listbox

    def get_search_entry(self):
        """Get the search entry widget for external access"""
        return self.youtube_search_entry

    def get_duration_filter(self):
        """Get the duration filter dropdown for external access"""
        return self.youtube_duration_filter

    def clear(self):
        """Clear all items from the YouTube results list"""
        child = self.youtube_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.youtube_listbox.remove(child)
            child = next_child
        logger.debug("YouTube results list cleared")

    def add_video_row(self, row):
        """
        Add a video row to the results list.

        Args:
            row: Gtk.ListBoxRow to add
        """
        self.youtube_listbox.append(row)

    def get_row_count(self):
        """Get the number of video results"""
        count = 0
        child = self.youtube_listbox.get_first_child()
        while child:
            count += 1
            child = child.get_next_sibling()
        return count

    def is_available(self):
        """Check if YouTube functionality is available"""
        return self.youtube_music.is_available()
