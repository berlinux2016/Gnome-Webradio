"""GNOME Session inhibitor to prevent suspend while playing"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GLib


class SessionInhibitor:
    """Manages GNOME session inhibitor to prevent suspend during playback"""

    def __init__(self, window):
        """
        Initialize the session inhibitor

        Args:
            window: The main application window (needed for inhibit/uninhibit)
        """
        self.window = window
        self.inhibit_cookie = None
        self._is_inhibited = False

        # Try to get the session manager proxy
        self.session_manager = None
        self._init_session_manager()

    def _init_session_manager(self):
        """Initialize connection to GNOME Session Manager via D-Bus"""
        try:
            # Connect to GNOME Session Manager
            self.session_manager = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION,
                Gio.DBusProxyFlags.NONE,
                None,
                'org.gnome.SessionManager',
                '/org/gnome/SessionManager',
                'org.gnome.SessionManager',
                None
            )
            print("Session inhibitor initialized successfully")
        except Exception as e:
            print(f"Could not initialize session manager: {e}")
            self.session_manager = None

    def inhibit(self):
        """
        Inhibit suspend/idle while audio is playing
        This prevents the system from going to sleep while streaming
        """
        if self._is_inhibited:
            return

        if not self.session_manager:
            print("Session manager not available, cannot inhibit suspend")
            return

        try:
            # Inhibit flags:
            # 4 = Inhibit suspending the session or computer
            # 8 = Inhibit the session being marked as idle
            flags = 4 | 8

            # Get application ID
            app = self.window.get_application()
            app_id = app.get_application_id() if app else "org.webradio.Player"

            # Call Inhibit method
            result = self.session_manager.call_sync(
                'Inhibit',
                GLib.Variant('(susu)', (
                    app_id,                           # app_id
                    0,                                # toplevel_xid (0 for none)
                    'Audio playback in progress',     # reason
                    flags                             # flags
                )),
                Gio.DBusCallFlags.NONE,
                -1,  # timeout
                None
            )

            # Extract the inhibit cookie from result
            if result:
                self.inhibit_cookie = result.unpack()[0]
                self._is_inhibited = True
                print(f"System suspend inhibited (cookie: {self.inhibit_cookie})")

        except Exception as e:
            print(f"Failed to inhibit suspend: {e}")

    def uninhibit(self):
        """
        Remove suspend/idle inhibition when audio stops
        Allows the system to suspend normally again
        """
        if not self._is_inhibited:
            return

        if not self.session_manager or self.inhibit_cookie is None:
            return

        try:
            # Call Uninhibit method with the cookie
            self.session_manager.call_sync(
                'Uninhibit',
                GLib.Variant('(u)', (self.inhibit_cookie,)),
                Gio.DBusCallFlags.NONE,
                -1,  # timeout
                None
            )

            print(f"System suspend uninhibited (cookie: {self.inhibit_cookie})")
            self.inhibit_cookie = None
            self._is_inhibited = False

        except Exception as e:
            print(f"Failed to uninhibit suspend: {e}")

    def is_inhibited(self):
        """Check if suspend is currently inhibited"""
        return self._is_inhibited

    def cleanup(self):
        """Clean up on application shutdown"""
        if self._is_inhibited:
            self.uninhibit()
