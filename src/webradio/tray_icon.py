"""System tray integration for WebRadio Player - GTK4 compatible"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, GLib, Gtk

# Try different AppIndicator implementations
TRAY_AVAILABLE = False
AppIndicator = None

# Try AyatanaAppIndicator3 first (modern, actively maintained)
try:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
    TRAY_AVAILABLE = True
    print("Using AyatanaAppIndicator3 for system tray")
except (ImportError, ValueError):
    # Try legacy AppIndicator3
    try:
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3 as AppIndicator
        TRAY_AVAILABLE = True
        print("Using AppIndicator3 for system tray")
    except (ImportError, ValueError):
        print("No AppIndicator available - system tray disabled")
        TRAY_AVAILABLE = False


class TrayIcon:
    """System tray icon for WebRadio"""

    def __init__(self, application, window):
        self.application = application
        self.window = window
        self.enabled = False
        self.indicator = None

        if TRAY_AVAILABLE:
            self._setup_tray()
        else:
            print("System tray not available on this system")

    def _setup_tray(self):
        """Setup system tray icon"""
        try:
            # Create indicator
            self.indicator = AppIndicator.Indicator.new(
                "webradio-player",
                "audio-x-generic",  # Fallback icon
                AppIndicator.IndicatorCategory.APPLICATION_STATUS
            )

            # Try to set custom icon
            self.indicator.set_icon_full("webradio", "WebRadio Player")

            # Set status
            self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            self.indicator.set_title("WebRadio Player")

            # Create GTK3-style menu for AppIndicator
            # Note: We need to use GTK3 menu for AppIndicator compatibility
            menu = self._create_gtk3_menu()
            self.indicator.set_menu(menu)

            # Setup application actions
            self._setup_actions()

            self.enabled = True
            print("System tray icon enabled")

        except Exception as e:
            print(f"Failed to setup tray icon: {e}")
            self.enabled = False

    def _create_gtk3_menu(self):
        """Create GTK3 menu for AppIndicator (workaround for GTK4)"""
        try:
            # We need to use GTK3 for AppIndicator menu
            gi.require_version('Gtk', '3.0')
            from gi.repository import Gtk as Gtk3

            menu = Gtk3.Menu()

            # Show/Hide Window
            show_item = Gtk3.MenuItem(label="Show/Hide Window")
            show_item.connect("activate", lambda w: self._on_show_window(None, None))
            menu.append(show_item)

            # Separator
            menu.append(Gtk3.SeparatorMenuItem())

            # Play/Pause
            play_item = Gtk3.MenuItem(label="Play/Pause")
            play_item.connect("activate", lambda w: self._on_play_pause(None, None))
            menu.append(play_item)

            # Stop
            stop_item = Gtk3.MenuItem(label="Stop")
            stop_item.connect("activate", lambda w: self._on_stop(None, None))
            menu.append(stop_item)

            # Separator
            menu.append(Gtk3.SeparatorMenuItem())

            # Quit Application
            quit_item = Gtk3.MenuItem(label="Quit WebRadio")
            quit_item.connect("activate", lambda w: self._on_quit_app(None, None))
            menu.append(quit_item)

            menu.show_all()
            return menu
        except Exception as e:
            print(f"Failed to create GTK3 menu: {e}")
            # Fallback to empty menu
            return None

    def _create_menu_model(self):
        """Create menu model (for future GTK4 support)"""
        menu = Gio.Menu()

        # Show/Hide
        menu.append("Show Window", "app.show-window")

        # Playback controls
        playback_menu = Gio.Menu()
        playback_menu.append("Play/Pause", "app.play-pause")
        playback_menu.append("Stop", "app.stop")
        menu.append_section(None, playback_menu)

        # Quit
        menu.append("Quit", "app.quit")

        return menu

    def _setup_actions(self):
        """Setup application actions"""
        # Show window action
        show_action = Gio.SimpleAction.new("show-window", None)
        show_action.connect("activate", self._on_show_window)
        self.application.add_action(show_action)

        # Play/Pause action
        play_pause_action = Gio.SimpleAction.new("play-pause", None)
        play_pause_action.connect("activate", self._on_play_pause)
        self.application.add_action(play_pause_action)

        # Stop action
        stop_action = Gio.SimpleAction.new("stop", None)
        stop_action.connect("activate", self._on_stop)
        self.application.add_action(stop_action)

    def _on_show_window(self, action, param):
        """Show/hide window"""
        if self.window.is_visible():
            self.window.hide()
        else:
            self.window.present()

    def _on_play_pause(self, action, param):
        """Toggle playback"""
        if hasattr(self.window, '_on_play_pause'):
            self.window._on_play_pause(None)

    def _on_stop(self, action, param):
        """Stop playback"""
        if hasattr(self.window, '_on_stop'):
            self.window._on_stop(None)

    def _on_quit_app(self, action, param):
        """Quit application completely"""
        # Stop playback first
        if hasattr(self.window, '_on_stop'):
            self.window._on_stop(None)
        # Quit application
        self.application.quit()

    def update_tooltip(self, text: str):
        """Update tray icon tooltip"""
        if self.enabled and self.indicator:
            self.indicator.set_title(text)

    def show_notification(self, title: str, message: str):
        """Show desktop notification"""
        notification = Gio.Notification.new(title)
        notification.set_body(message)
        notification.set_priority(Gio.NotificationPriority.NORMAL)
        self.application.send_notification(None, notification)

    def set_icon(self, icon_name: str):
        """Set tray icon"""
        if self.enabled and self.indicator:
            self.indicator.set_icon_full(icon_name, "WebRadio Player")
