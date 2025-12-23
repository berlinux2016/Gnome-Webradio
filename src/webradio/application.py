"""Main application class for WebRadio Player"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk
from webradio.window import WebRadioWindow


class WebRadioApplication(Adw.Application):
    """Main application class"""

    def __init__(self):
        super().__init__(
            application_id='org.webradio.Player',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        )

        # Initialize GSettings
        try:
            self.settings = Gio.Settings.new('org.webradio.Player')
            print("GSettings initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize GSettings: {e}")
            print("The app will still work, but preferences won't persist")
            self.settings = None

        self.create_action('quit', self.on_quit, ['<primary>q'])
        self.create_action('about', self.on_about)
        self.create_action('preferences', self.on_preferences)
        self.create_action('show-window', self.on_show_window)

        # Add command line options
        self.add_main_option(
            'quit',
            ord('q'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            'Quit the running application',
            None
        )

    def do_activate(self):
        """Called when the application is activated"""
        # Setup icon theme search path for development
        self._setup_icon_theme()

        # Load custom CSS
        self._load_css()

        win = self.props.active_window
        if not win:
            win = WebRadioWindow(application=self)
        win.present()

    def _setup_icon_theme(self):
        """Setup icon theme to include local icons for development"""
        import os

        # Get the project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        icon_dir = os.path.join(project_root, 'data', 'icons')

        # Check if running from source directory
        if os.path.exists(icon_dir):
            # Add local icon directory to search path
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            icon_theme.add_search_path(icon_dir)
            print(f"Added icon search path: {icon_dir}")

    def _load_css(self):
        """Load custom CSS stylesheet"""
        try:
            import os
            css_provider = Gtk.CssProvider()

            # Try different paths for CSS file
            css_paths = [
                'data/webradio.css',
                '/usr/share/webradio/webradio.css',
                os.path.join(os.path.dirname(__file__), '../../data/webradio.css'),
            ]

            css_loaded = False
            for css_path in css_paths:
                if os.path.exists(css_path):
                    css_provider.load_from_path(css_path)
                    Gtk.StyleContext.add_provider_for_display(
                        Gdk.Display.get_default(),
                        css_provider,
                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                    )
                    print(f"Custom CSS loaded from: {css_path}")
                    css_loaded = True
                    break

            if not css_loaded:
                print("Warning: Could not find custom CSS file")

        except Exception as e:
            print(f"Warning: Could not load custom CSS: {e}")

    def do_command_line(self, command_line):
        """Handle command line arguments"""
        options = command_line.get_options_dict()
        options = options.end().unpack()

        if 'quit' in options:
            # Quit the running instance
            self.quit()
            return 0

        # Activate the application (show window)
        self.activate()
        return 0

    def create_action(self, name, callback, shortcuts=None):
        """Create an application action"""
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f'app.{name}', shortcuts)

    def on_quit(self, action, param):
        """Quit the application"""
        self.quit()

    def on_about(self, action, param):
        """Show about dialog"""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name='WebRadio Player',
            application_icon='webradio',
            developer_name='DaHooL',
            version='1.1.0',
            developers=['DaHooL <089mobil@gmail.com>'],
            copyright='© 2025 DaHooL',
            license_type=Gtk.License.GPL_3_0,
            website='https://github.com/dahool/webradio-player',
            issue_url='https://github.com/dahool/webradio-player/issues',
        )
        about.present()

    def on_preferences(self, action, param):
        """Show preferences dialog"""
        from webradio.preferences import PreferencesWindow

        win = self.props.active_window
        if not win:
            return

        # Get managers from window if available
        equalizer_manager = getattr(win, 'equalizer_manager', None)
        recorder = getattr(win, 'recorder', None)

        prefs = PreferencesWindow(win, self.settings, equalizer_manager, recorder)
        prefs.present()

    def on_show_window(self, action, param):
        """Show the main window"""
        win = self.props.active_window
        if win:
            win.present()
        else:
            # Create new window if none exists
            win = WebRadioWindow(application=self)
            win.present()
