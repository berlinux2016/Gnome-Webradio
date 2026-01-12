"""
Desktop Notifications Manager for Gnome Web Radio

This module provides desktop notification functionality for track changes and events.
"""

import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

from webradio.logger import get_logger

logger = get_logger(__name__)


class NotificationManager:
    """
    Manages desktop notifications for the application.

    Provides notifications for track changes, station switches,
    and other important events using GNotification.
    """

    def __init__(self, application):
        """
        Initialize notification manager.

        Args:
            application: The Gtk.Application instance
        """
        self.application = application
        self.enabled = True
        self.show_track_changes = True
        self.last_notification_id = None

        logger.info("Notification manager initialized")

    def set_enabled(self, enabled: bool):
        """
        Enable or disable notifications.

        Args:
            enabled: True to enable notifications
        """
        self.enabled = enabled
        logger.info(f"Notifications {'enabled' if enabled else 'disabled'}")

    def set_track_change_notifications(self, enabled: bool):
        """
        Enable or disable track change notifications.

        Args:
            enabled: True to show track change notifications
        """
        self.show_track_changes = enabled
        logger.debug(f"Track change notifications {'enabled' if enabled else 'disabled'}")

    def notify_track_change(self, station_name: str, title: str, artist: str = None):
        """
        Show notification for track change.

        Args:
            station_name: Name of the radio station
            title: Track title
            artist: Track artist (optional)
        """
        if not self.enabled or not self.show_track_changes:
            return

        try:
            # Format notification body
            if artist:
                body = f"{artist} - {title}"
            else:
                body = title

            # Create notification
            notification = Gio.Notification.new(station_name)
            notification.set_body(body)
            notification.set_priority(Gio.NotificationPriority.LOW)

            # Add playback action
            notification.add_button("Show", "app.show-window")

            # Send notification
            notification_id = "track-change"
            self.application.send_notification(notification_id, notification)
            self.last_notification_id = notification_id

            logger.info(f"Track change notification: {station_name} - {body}")

        except Exception as e:
            logger.error(f"Failed to send track change notification: {e}")

    def notify_station_change(self, station_name: str, genre: str = None):
        """
        Show notification for station change.

        Args:
            station_name: Name of the new station
            genre: Station genre (optional)
        """
        if not self.enabled:
            return

        try:
            # Format notification body
            if genre:
                body = f"Genre: {genre}"
            else:
                body = "Now playing"

            # Create notification
            notification = Gio.Notification.new(f"🎵 {station_name}")
            notification.set_body(body)
            notification.set_priority(Gio.NotificationPriority.NORMAL)

            # Send notification
            notification_id = "station-change"
            self.application.send_notification(notification_id, notification)
            self.last_notification_id = notification_id

            logger.info(f"Station change notification: {station_name}")

        except Exception as e:
            logger.error(f"Failed to send station change notification: {e}")

    def notify_recording_started(self, file_path: str):
        """
        Show notification that recording has started.

        Args:
            file_path: Path where recording is being saved
        """
        if not self.enabled:
            return

        try:
            import os
            filename = os.path.basename(file_path)

            notification = Gio.Notification.new("🔴 Recording Started")
            notification.set_body(f"Saving to: {filename}")
            notification.set_priority(Gio.NotificationPriority.NORMAL)

            # Send notification
            notification_id = "recording-started"
            self.application.send_notification(notification_id, notification)

            logger.info(f"Recording started notification: {filename}")

        except Exception as e:
            logger.error(f"Failed to send recording notification: {e}")

    def notify_recording_stopped(self, file_path: str, duration: str = None):
        """
        Show notification that recording has stopped.

        Args:
            file_path: Path where recording was saved
            duration: Recording duration (optional)
        """
        if not self.enabled:
            return

        try:
            import os
            filename = os.path.basename(file_path)

            body = f"Saved: {filename}"
            if duration:
                body += f"\nDuration: {duration}"

            notification = Gio.Notification.new("⏹️  Recording Stopped")
            notification.set_body(body)
            notification.set_priority(Gio.NotificationPriority.NORMAL)

            # Add action to open file location
            notification.add_button("Open Folder", "app.open-recordings")

            # Send notification
            notification_id = "recording-stopped"
            self.application.send_notification(notification_id, notification)

            logger.info(f"Recording stopped notification: {filename}")

        except Exception as e:
            logger.error(f"Failed to send recording stopped notification: {e}")

    def notify_error(self, title: str, message: str):
        """
        Show error notification.

        Args:
            title: Error title
            message: Error message
        """
        if not self.enabled:
            return

        try:
            notification = Gio.Notification.new(f"❌ {title}")
            notification.set_body(message)
            notification.set_priority(Gio.NotificationPriority.HIGH)

            # Send notification
            notification_id = "error"
            self.application.send_notification(notification_id, notification)

            logger.warning(f"Error notification: {title} - {message}")

        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")

    def notify_connection_lost(self, station_name: str):
        """
        Show notification that connection to station was lost.

        Args:
            station_name: Name of the station
        """
        if not self.enabled:
            return

        try:
            notification = Gio.Notification.new("Connection Lost")
            notification.set_body(f"Lost connection to {station_name}")
            notification.set_priority(Gio.NotificationPriority.NORMAL)

            # Send notification
            notification_id = "connection-lost"
            self.application.send_notification(notification_id, notification)

            logger.info(f"Connection lost notification: {station_name}")

        except Exception as e:
            logger.error(f"Failed to send connection lost notification: {e}")

    def clear_notifications(self):
        """Clear all notifications"""
        if self.last_notification_id:
            try:
                self.application.withdraw_notification(self.last_notification_id)
                self.last_notification_id = None
                logger.debug("Cleared notifications")
            except Exception as e:
                logger.error(f"Failed to clear notifications: {e}")


def create_notification_manager(application) -> NotificationManager:
    """
    Factory function to create a notification manager.

    Args:
        application: The Gtk.Application instance

    Returns:
        NotificationManager: Configured notification manager
    """
    return NotificationManager(application)
