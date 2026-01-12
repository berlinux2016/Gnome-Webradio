"""
Keyboard Shortcuts Manager for Gnome Web Radio

This module provides centralized keyboard shortcut handling for the application.
"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk

from webradio.logger import get_logger

logger = get_logger(__name__)


class KeyboardShortcuts:
    """
    Manages keyboard shortcuts for the application.

    Provides a centralized system for registering and handling keyboard shortcuts
    with customizable bindings and conflict detection.
    """

    # Default keyboard shortcuts
    DEFAULT_SHORTCUTS = {
        # Playback controls
        'play_pause': '<space>',
        'stop': '<Control>period',
        'volume_up': '<Control>Up',
        'volume_down': '<Control>Down',
        'mute': 'm',

        # Navigation
        'next_station': '<Control>Right',
        'previous_station': '<Control>Left',
        'focus_search': '<Control>f',
        'show_favorites': '<Control>b',
        'show_history': '<Control>h',

        # Window controls
        'quit': '<Control>q',
        'close_window': '<Control>w',
        'fullscreen': 'F11',
        'show_shortcuts': '<Control>question',

        # Recording
        'toggle_recording': '<Control>r',

        # Favorites
        'add_to_favorites': '<Control>d',
    }

    def __init__(self, window):
        """
        Initialize keyboard shortcuts manager.

        Args:
            window: The main application window
        """
        self.window = window
        self.shortcuts = self.DEFAULT_SHORTCUTS.copy()
        self.handlers = {}

        logger.info("Keyboard shortcuts manager initialized")

    def register_handler(self, action: str, callback):
        """
        Register a callback handler for a keyboard shortcut action.

        Args:
            action: The action name (e.g., 'play_pause')
            callback: The callback function to execute
        """
        if action not in self.DEFAULT_SHORTCUTS:
            logger.warning(f"Unknown shortcut action: {action}")
            return

        self.handlers[action] = callback
        logger.debug(f"Registered handler for action: {action}")

    def setup_shortcuts(self):
        """Setup keyboard shortcuts for the window"""
        # Create event controller for key press
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect('key-pressed', self._on_key_pressed)
        self.window.add_controller(key_controller)

        logger.info("Keyboard shortcuts activated")

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """
        Handle key press events.

        Args:
            controller: The event controller
            keyval: The key value
            keycode: The hardware key code
            state: Modifier state (Ctrl, Shift, etc.)

        Returns:
            bool: True if event was handled, False otherwise
        """
        # Get the accelerator string for this key combination
        accel = Gtk.accelerator_name(keyval, state)

        # Check if this matches any registered shortcut
        for action, shortcut in self.shortcuts.items():
            if self._match_accelerator(accel, shortcut):
                if action in self.handlers:
                    logger.debug(f"Executing shortcut action: {action} ({accel})")
                    try:
                        self.handlers[action]()
                        return True
                    except Exception as e:
                        logger.error(f"Error executing shortcut {action}: {e}")
                        return False

        return False

    def _match_accelerator(self, pressed: str, shortcut: str) -> bool:
        """
        Check if pressed accelerator matches shortcut definition.

        Args:
            pressed: The pressed accelerator (e.g., '<Control>f')
            shortcut: The shortcut definition

        Returns:
            bool: True if they match
        """
        # Normalize accelerator strings for comparison
        pressed_normalized = pressed.lower().replace('_l', '').replace('_r', '')
        shortcut_normalized = shortcut.lower().replace('_l', '').replace('_r', '')

        return pressed_normalized == shortcut_normalized

    def get_shortcut_display(self, action: str) -> str:
        """
        Get human-readable display string for a shortcut.

        Args:
            action: The action name

        Returns:
            str: Display string (e.g., "Ctrl+F")
        """
        if action not in self.shortcuts:
            return ""

        accel = self.shortcuts[action]

        # Convert GTK accelerator to human-readable format
        replacements = {
            '<Control>': 'Ctrl+',
            '<Shift>': 'Shift+',
            '<Alt>': 'Alt+',
            '<Super>': 'Super+',
            '<space>': 'Space',
            'question': '?',
            'period': '.',
        }

        display = accel
        for old, new in replacements.items():
            display = display.replace(old, new)

        # Capitalize single letters
        if len(display) == 1:
            display = display.upper()

        return display

    def get_all_shortcuts(self) -> dict:
        """
        Get all registered shortcuts with their display strings.

        Returns:
            dict: Mapping of action names to display strings
        """
        return {
            action: self.get_shortcut_display(action)
            for action in self.shortcuts.keys()
        }

    def show_shortcuts_dialog(self):
        """Show a dialog with all keyboard shortcuts"""
        dialog = Gtk.Window()
        dialog.set_transient_for(self.window)
        dialog.set_modal(True)
        dialog.set_title("Keyboard Shortcuts")
        dialog.set_default_size(500, 600)

        # Create scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        # Create list box with shortcuts
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        # Group shortcuts by category
        categories = {
            "Playback": ['play_pause', 'stop', 'volume_up', 'volume_down', 'mute'],
            "Navigation": ['next_station', 'previous_station', 'focus_search', 'show_favorites', 'show_history'],
            "Window": ['quit', 'close_window', 'fullscreen', 'show_shortcuts'],
            "Features": ['toggle_recording', 'add_to_favorites']
        }

        for category, actions in categories.items():
            # Add category header
            header = Gtk.Label()
            header.set_markup(f"<b>{category}</b>")
            header.set_xalign(0)
            header.set_margin_start(12)
            header.set_margin_top(12)
            header.set_margin_bottom(6)

            header_row = Gtk.ListBoxRow()
            header_row.set_child(header)
            header_row.set_activatable(False)
            listbox.append(header_row)

            # Add shortcuts in this category
            for action in actions:
                if action not in self.shortcuts:
                    continue

                row = Gtk.ListBoxRow()
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                box.set_margin_start(24)
                box.set_margin_end(12)
                box.set_margin_top(8)
                box.set_margin_bottom(8)

                # Action name
                action_label = Gtk.Label()
                action_label.set_text(action.replace('_', ' ').title())
                action_label.set_xalign(0)
                action_label.set_hexpand(True)
                box.append(action_label)

                # Shortcut key
                shortcut_label = Gtk.Label()
                shortcut_label.set_text(self.get_shortcut_display(action))
                shortcut_label.add_css_class('monospace')
                shortcut_label.add_css_class('dim-label')
                box.append(shortcut_label)

                row.set_child(box)
                row.set_activatable(False)
                listbox.append(row)

        scrolled.set_child(listbox)
        dialog.set_child(scrolled)
        dialog.present()

        logger.info("Showing keyboard shortcuts dialog")


def create_shortcuts_manager(window) -> KeyboardShortcuts:
    """
    Factory function to create and setup keyboard shortcuts manager.

    Args:
        window: The main application window

    Returns:
        KeyboardShortcuts: Configured shortcuts manager
    """
    manager = KeyboardShortcuts(window)
    manager.setup_shortcuts()
    return manager
