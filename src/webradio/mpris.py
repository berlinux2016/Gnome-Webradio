"""MPRIS2 Integration for WebRadio Player - GNOME Media Controls"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, GLib

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from .player import PlayerState


class MPRISInterface(dbus.service.Object):
    """
    MPRIS2 Interface for WebRadio Player

    Integrates with GNOME's media controls in the notification area.
    Shows station logo, track info, and playback controls.
    """

    MPRIS_IFACE = 'org.mpris.MediaPlayer2'
    MPRIS_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
    MPRIS_RATINGS_IFACE = 'org.mpris.MediaPlayer2.ExtensionSetRating'

    def __init__(self, window):
        """Initialize MPRIS interface"""
        self.window = window
        self.player = window.player

        # Initialize DBus
        DBusGMainLoop(set_as_default=True)

        try:
            # Get session bus
            self.session_bus = dbus.SessionBus()

            # Request bus name
            self.bus_name = dbus.service.BusName(
                'org.mpris.MediaPlayer2.webradio',
                bus=self.session_bus
            )

            # Register object
            dbus.service.Object.__init__(
                self,
                self.session_bus,
                '/org/mpris/MediaPlayer2'
            )

            print("MPRIS interface initialized successfully")
            self.enabled = True

        except Exception as e:
            print(f"Failed to initialize MPRIS: {e}")
            self.enabled = False

    # Root Interface Properties
    @dbus.service.method(dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        """Get property value"""
        return self.GetAll(interface)[prop]

    @dbus.service.method(dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        """Get all properties"""
        if interface == self.MPRIS_IFACE:
            return self._get_root_properties()
        elif interface == self.MPRIS_PLAYER_IFACE:
            return self._get_player_properties()
        return {}

    @dbus.service.signal(dbus.PROPERTIES_IFACE,
                        signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed_properties,
                         invalidated_properties):
        """Signal when properties change"""
        pass

    def _get_root_properties(self):
        """Get root interface properties"""
        return {
            'CanQuit': True,
            'CanRaise': True,
            'HasTrackList': False,
            'Identity': 'WebRadio Player',
            'DesktopEntry': 'webradio',
            'SupportedUriSchemes': dbus.Array(['http', 'https'], signature='s'),
            'SupportedMimeTypes': dbus.Array([
                'audio/mpeg',
                'audio/aac',
                'audio/ogg',
                'application/ogg'
            ], signature='s'),
        }

    def _get_player_properties(self):
        """Get player interface properties"""
        station = self.player.get_current_station()
        tags = self.player.get_current_tags()

        # Build metadata
        metadata = self._build_metadata(station, tags)

        # Playback status
        if self.player.is_playing():
            status = 'Playing'
        elif self.player.state.value == 2:  # PAUSED
            status = 'Paused'
        else:
            status = 'Stopped'

        return {
            'PlaybackStatus': status,
            'LoopStatus': 'None',
            'Rate': 1.0,
            'Shuffle': False,
            'Metadata': dbus.Dictionary(metadata, signature='sv'),
            'Volume': self.player.get_volume(),
            'Position': dbus.Int64(0),
            'MinimumRate': 1.0,
            'MaximumRate': 1.0,
            'CanGoNext': False,
            'CanGoPrevious': False,
            'CanPlay': True,
            'CanPause': True,
            'CanSeek': False,
            'CanControl': True,
        }

    def _build_metadata(self, station, tags):
        """Build metadata dictionary"""
        metadata = {}

        if station:
            # Track ID (required)
            # D-Bus object paths don't allow hyphens, so remove them from UUID
            station_uuid = station.get('stationuuid', 'unknown')
            # Replace hyphens with underscores to make valid D-Bus object path
            safe_uuid = station_uuid.replace('-', '_')
            metadata['mpris:trackid'] = dbus.ObjectPath(
                f'/org/mpris/MediaPlayer2/Track/{safe_uuid}'
            )

            # Cover art (station logo)
            if station.get('favicon'):
                metadata['mpris:artUrl'] = station['favicon']

            # Stream URL
            url = station.get('url_resolved') or station.get('url')
            if url:
                metadata['xesam:url'] = url

        # GNOME shows: Top (bold) = xesam:artist, Bottom = xesam:title
        # So we set: Artist = Station/Artist name, Title = Song title

        if tags:
            # If we have tags with artist and title
            if tags.get('artist') and tags.get('title'):
                # Artist name on top (bold)
                metadata['xesam:artist'] = dbus.Array([tags['artist']], signature='s')
                # Song title below
                metadata['xesam:title'] = tags['title']
            elif tags.get('title'):
                # Only title available - show station name on top
                if station:
                    metadata['xesam:artist'] = dbus.Array([station.get('name', 'Radio')], signature='s')
                metadata['xesam:title'] = tags['title']
            elif tags.get('artist'):
                # Only artist available
                metadata['xesam:artist'] = dbus.Array([tags['artist']], signature='s')
                if station:
                    metadata['xesam:title'] = station.get('name', 'Live Radio')

            # Album metadata
            if tags.get('album'):
                metadata['xesam:album'] = tags['album']
            elif station:
                metadata['xesam:album'] = station.get('name', 'Unknown Station')
        else:
            # No tags - show station name
            if station:
                metadata['xesam:artist'] = dbus.Array([station.get('name', 'Radio')], signature='s')
                metadata['xesam:title'] = 'Live Radio'
                metadata['xesam:album'] = station.get('name', 'Unknown Station')

        # Ensure we always have artist and title
        if 'xesam:artist' not in metadata:
            metadata['xesam:artist'] = dbus.Array(['Radio'], signature='s')
        if 'xesam:title' not in metadata:
            metadata['xesam:title'] = 'Live Stream'

        return metadata

    # Root Interface Methods
    @dbus.service.method(MPRIS_IFACE)
    def Raise(self):
        """Raise/show the window"""
        print("MPRIS: Raise window")
        GLib.idle_add(self.window.present)

    @dbus.service.method(MPRIS_IFACE)
    def Quit(self):
        """Quit the application"""
        print("MPRIS: Quit application")
        GLib.idle_add(self._quit_app)

    def _quit_app(self):
        """Quit the application (called from main thread)"""
        self.player.stop()
        self.window.get_application().quit()

    # Player Interface Methods
    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def Next(self):
        """Next track (not supported for radio)"""
        pass

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def Previous(self):
        """Previous track (not supported for radio)"""
        pass

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def Pause(self):
        """Pause playback"""
        print("MPRIS: Pause")
        GLib.idle_add(self.player.pause)
        GLib.idle_add(self.update_properties)

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def PlayPause(self):
        """Toggle play/pause"""
        print("MPRIS: PlayPause")

        def do_playpause():
            if self.player.is_playing():
                self.player.pause()
            else:
                # If paused, just resume
                if self.player.state == PlayerState.PAUSED:
                    self.player.resume()
                # If stopped or error, restart the stream
                elif self.player.current_uri and self.player.current_station:
                    print(f"MPRIS: Restarting stream {self.player.current_uri}")
                    self.player.play(self.player.current_uri, self.player.current_station)
                # Otherwise try to resume anyway
                else:
                    self.player.resume()
            self.update_properties()
            return False

        GLib.idle_add(do_playpause)

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def Play(self):
        """Resume playback or restart stream"""
        print("MPRIS: Play")

        def do_play():
            # If paused, just resume
            if self.player.state == PlayerState.PAUSED:
                self.player.resume()
            # If stopped or error, restart the stream
            elif self.player.current_uri and self.player.current_station:
                print(f"MPRIS: Restarting stream {self.player.current_uri}")
                self.player.play(self.player.current_uri, self.player.current_station)
            # Otherwise try to resume anyway
            else:
                self.player.resume()
            self.update_properties()
            return False

        GLib.idle_add(do_play)

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def Stop(self):
        """Stop playback"""
        print("MPRIS: Stop")
        GLib.idle_add(self.player.stop)
        GLib.idle_add(self.update_properties)

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def Seek(self, offset):
        """Seek (not supported for radio)"""
        pass

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def SetPosition(self, track_id, position):
        """Set position (not supported for radio)"""
        pass

    @dbus.service.method(MPRIS_PLAYER_IFACE)
    def OpenUri(self, uri):
        """Open URI (not supported)"""
        pass

    # Update methods
    def update_properties(self):
        """Notify that properties changed"""
        if not self.enabled:
            return

        try:
            properties = self._get_player_properties()
            self.PropertiesChanged(
                self.MPRIS_PLAYER_IFACE,
                properties,
                []
            )
        except Exception as e:
            print(f"Failed to update MPRIS properties: {e}")

    def update_metadata(self):
        """Update metadata (called when track changes)"""
        self.update_properties()

    def update_playback_status(self):
        """Update playback status"""
        self.update_properties()
