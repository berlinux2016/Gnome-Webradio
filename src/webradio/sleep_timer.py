"""Sleep timer for automatic shutdown"""

from gi.repository import GLib, GObject, Gio
from typing import Optional, Callable
from datetime import datetime, timedelta


class SleepTimer(GObject.Object):
    """Sleep timer to stop playback after specified time"""

    __gsignals__ = {
        'timer-started': (GObject.SignalFlags.RUN_FIRST, None, (int,)),  # minutes
        'timer-stopped': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'timer-tick': (GObject.SignalFlags.RUN_FIRST, None, (int,)),  # remaining seconds
        'timer-expired': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'timer-warning': (GObject.SignalFlags.RUN_FIRST, None, (int,)),  # minutes remaining for warning
    }

    # Preset durations in minutes
    PRESETS = [15, 30, 45, 60, 90, 120]

    # Actions when timer expires
    ACTIONS = {
        'stop': 'Stop Playback',
        'pause': 'Pause Playback',
        'quit': 'Quit Application',
    }

    def __init__(self, player=None, application=None, settings: Optional[Gio.Settings] = None):
        super().__init__()

        self.player = player
        self.application = application
        self.settings = settings

        # Timer state
        self.is_active = False
        self.duration_minutes = 30
        self.remaining_seconds = 0
        self.end_time = None
        self.action = 'stop'

        # GLib timeout source
        self.timeout_id = None

        # Warning threshold (show notification X minutes before expiry)
        self.warning_threshold_minutes = 5
        self.warning_shown = False

        # Load settings
        if self.settings:
            self._load_settings()

    def _load_settings(self):
        """Load timer settings from GSettings"""
        if not self.settings:
            return

        try:
            self.duration_minutes = self.settings.get_int('sleep-timer-minutes')
            self.action = self.settings.get_string('sleep-timer-action')

            # Validate action
            if self.action not in self.ACTIONS:
                self.action = 'stop'

        except Exception as e:
            print(f"Error loading sleep timer settings: {e}")

    def _save_settings(self):
        """Save timer settings to GSettings"""
        if not self.settings:
            return

        try:
            self.settings.set_int('sleep-timer-minutes', self.duration_minutes)
            self.settings.set_string('sleep-timer-action', self.action)

        except Exception as e:
            print(f"Error saving sleep timer settings: {e}")

    def start(self, minutes: int = None, action: str = None) -> bool:
        """Start the sleep timer"""
        if self.is_active:
            print("Timer already active")
            return False

        # Set duration
        if minutes is not None:
            self.duration_minutes = max(1, min(480, minutes))  # 1-480 minutes (8 hours)
        else:
            self.duration_minutes = max(1, self.duration_minutes)

        # Set action
        if action and action in self.ACTIONS:
            self.action = action

        # Calculate end time
        self.remaining_seconds = self.duration_minutes * 60
        self.end_time = datetime.now() + timedelta(seconds=self.remaining_seconds)

        # Start countdown
        self.is_active = True
        self.warning_shown = False

        # Start tick timer (update every second)
        self.timeout_id = GLib.timeout_add_seconds(1, self._on_tick)

        # Save settings
        self._save_settings()

        # Emit signal
        self.emit('timer-started', self.duration_minutes)

        print(f"Sleep timer started: {self.duration_minutes} minutes, action: {self.action}")
        return True

    def stop(self) -> bool:
        """Stop the sleep timer"""
        if not self.is_active:
            return False

        # Remove timeout
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None

        # Reset state
        self.is_active = False
        self.remaining_seconds = 0
        self.end_time = None
        self.warning_shown = False

        # Emit signal
        self.emit('timer-stopped')

        print("Sleep timer stopped")
        return True

    def _on_tick(self) -> bool:
        """Called every second to update countdown"""
        if not self.is_active:
            return False  # Stop the timeout

        # Calculate remaining time
        now = datetime.now()
        remaining = (self.end_time - now).total_seconds()
        self.remaining_seconds = max(0, int(remaining))

        # Check for warning threshold (5 minutes before expiry)
        minutes_remaining = self.remaining_seconds // 60
        if (not self.warning_shown and
            minutes_remaining <= self.warning_threshold_minutes and
            minutes_remaining > 0):
            self.warning_shown = True
            self.emit('timer-warning', minutes_remaining)

        # Emit tick signal
        self.emit('timer-tick', self.remaining_seconds)

        # Check if expired
        if self.remaining_seconds <= 0:
            self._on_expired()
            return False  # Stop the timeout

        return True  # Continue timeout

    def _on_expired(self):
        """Called when timer expires"""
        print(f"Sleep timer expired, action: {self.action}")

        # Stop timer
        self.is_active = False
        self.timeout_id = None

        # Emit signal
        self.emit('timer-expired')

        # Perform action
        GLib.idle_add(self._execute_action)

    def _execute_action(self):
        """Execute the configured action"""
        if self.action == 'stop':
            if self.player and self.player.is_playing():
                print("Stopping playback (sleep timer)")
                self.player.stop()

        elif self.action == 'pause':
            if self.player and self.player.is_playing():
                print("Pausing playback (sleep timer)")
                self.player.pause()

        elif self.action == 'quit':
            if self.application:
                print("Quitting application (sleep timer)")
                self.application.quit()

        return False  # Don't repeat

    def get_remaining_time(self) -> int:
        """Get remaining time in seconds"""
        return self.remaining_seconds

    def get_remaining_formatted(self) -> str:
        """Get remaining time as formatted string (MM:SS)"""
        if not self.is_active:
            return "00:00"

        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def get_remaining_display(self) -> str:
        """Get remaining time for display (e.g., '25 minutes')"""
        if not self.is_active:
            return "Inactive"

        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60

        if minutes > 0:
            if seconds > 30:
                return f"{minutes + 1} minutes"
            else:
                return f"{minutes} minutes" if minutes != 1 else "1 minute"
        else:
            return f"{seconds} seconds"

    def set_duration(self, minutes: int) -> bool:
        """Set timer duration (only works when not active)"""
        if self.is_active:
            return False

        self.duration_minutes = max(1, min(480, minutes))
        self._save_settings()
        return True

    def get_duration(self) -> int:
        """Get configured duration in minutes"""
        return self.duration_minutes

    def set_action(self, action: str) -> bool:
        """Set action to perform when timer expires"""
        if action not in self.ACTIONS:
            return False

        self.action = action
        self._save_settings()
        return True

    def get_action(self) -> str:
        """Get configured action"""
        return self.action

    def get_actions(self) -> dict:
        """Get available actions"""
        return self.ACTIONS.copy()

    def get_presets(self) -> list:
        """Get preset durations"""
        return self.PRESETS.copy()

    def is_running(self) -> bool:
        """Check if timer is currently running"""
        return self.is_active

    def add_time(self, minutes: int) -> bool:
        """Add time to running timer"""
        if not self.is_active:
            return False

        # Add to end time
        self.end_time += timedelta(minutes=minutes)

        # Recalculate remaining time
        now = datetime.now()
        remaining = (self.end_time - now).total_seconds()
        self.remaining_seconds = max(0, int(remaining))

        # Reset warning if we added significant time
        if minutes >= self.warning_threshold_minutes:
            self.warning_shown = False

        print(f"Added {minutes} minutes to sleep timer")
        return True

    def subtract_time(self, minutes: int) -> bool:
        """Subtract time from running timer"""
        if not self.is_active:
            return False

        # Subtract from end time (but not less than 1 minute remaining)
        min_end_time = datetime.now() + timedelta(minutes=1)
        new_end_time = self.end_time - timedelta(minutes=minutes)

        if new_end_time < min_end_time:
            self.end_time = min_end_time
        else:
            self.end_time = new_end_time

        # Recalculate remaining time
        now = datetime.now()
        remaining = (self.end_time - now).total_seconds()
        self.remaining_seconds = max(0, int(remaining))

        print(f"Subtracted {minutes} minutes from sleep timer")
        return True
