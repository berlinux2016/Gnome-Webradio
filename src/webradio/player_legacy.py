"""Audio player using GStreamer"""

import gi
gi.require_version('Gst', '1.0')

from gi.repository import Gst, GLib, GObject
from enum import Enum


class PlayerState(Enum):
    """Player states"""
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2
    BUFFERING = 3
    ERROR = 4


class AudioPlayer(GObject.Object):
    """GStreamer-based audio player for streaming radio"""

    __gsignals__ = {
        'state-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'error': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'tags-updated': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'volume-changed': (GObject.SignalFlags.RUN_FIRST, None, (float,)),
    }

    def __init__(self):
        super().__init__()
        Gst.init(None)

        # Create pipeline
        self.playbin = Gst.ElementFactory.make('playbin', 'player')
        if not self.playbin:
            raise RuntimeError("Could not create GStreamer playbin")

        # Set up audio sink with volume control
        self.audio_sink = Gst.ElementFactory.make('autoaudiosink', 'audio-sink')

        if self.audio_sink:
            self.playbin.set_property('audio-sink', self.audio_sink)

        # Connect to bus messages
        self.bus = self.playbin.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self._on_bus_message)

        # Player state
        self.state = PlayerState.STOPPED
        self.current_uri = None
        self.current_station = None
        self._volume = 1.0
        self.current_tags = {}

        # Set initial volume
        self.playbin.set_property('volume', self._volume)

    def play(self, uri: str, station_info: dict = None):
        """Play a radio stream"""
        if not uri:
            return False

        # Stop current playback
        self.stop()

        self.current_uri = uri
        self.current_station = station_info

        # Set URI and play
        self.playbin.set_property('uri', uri)
        result = self.playbin.set_state(Gst.State.PLAYING)

        if result == Gst.StateChangeReturn.FAILURE:
            self.emit('error', 'Failed to start playback')
            self.state = PlayerState.ERROR
            return False

        self._set_state(PlayerState.PLAYING)
        return True

    def pause(self):
        """Pause playback"""
        if self.state == PlayerState.PLAYING:
            self.playbin.set_state(Gst.State.PAUSED)
            self._set_state(PlayerState.PAUSED)

    def resume(self):
        """Resume playback"""
        if self.state == PlayerState.PAUSED:
            self.playbin.set_state(Gst.State.PLAYING)
            self._set_state(PlayerState.PLAYING)

    def stop(self):
        """Stop playback"""
        self.playbin.set_state(Gst.State.NULL)
        self._set_state(PlayerState.STOPPED)
        self.current_uri = None
        self.current_station = None
        self.current_tags = {}

    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)"""
        volume = max(0.0, min(1.0, volume))
        self._volume = volume
        self.playbin.set_property('volume', volume)
        self.emit('volume-changed', volume)

    def get_volume(self) -> float:
        """Get current volume"""
        return self._volume

    def is_playing(self) -> bool:
        """Check if player is playing"""
        return self.state == PlayerState.PLAYING

    def get_current_station(self):
        """Get currently playing station info"""
        return self.current_station

    def get_current_tags(self):
        """Get currently playing metadata tags"""
        return self.current_tags

    def _set_state(self, new_state: PlayerState):
        """Set player state and emit signal"""
        if self.state != new_state:
            self.state = new_state
            self.emit('state-changed', new_state.value)

    def _on_bus_message(self, bus, message):
        """Handle GStreamer bus messages"""
        msg_type = message.type

        if msg_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            error_msg = f"Playback error: {err.message}"
            print(f"GStreamer Error: {error_msg}")
            print(f"Debug info: {debug}")
            self.emit('error', error_msg)
            self._set_state(PlayerState.ERROR)

        elif msg_type == Gst.MessageType.EOS:
            # End of stream (shouldn't happen with radio, but handle it)
            print("End of stream reached")
            self.stop()

        elif msg_type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.playbin:
                old_state, new_state, pending = message.parse_state_changed()

                if new_state == Gst.State.PLAYING:
                    if self.state != PlayerState.PLAYING:
                        self._set_state(PlayerState.PLAYING)

                elif new_state == Gst.State.PAUSED:
                    if self.state != PlayerState.PAUSED:
                        self._set_state(PlayerState.PAUSED)

        elif msg_type == Gst.MessageType.BUFFERING:
            percent = message.parse_buffering()
            if percent < 100:
                self.playbin.set_state(Gst.State.PAUSED)
                self._set_state(PlayerState.BUFFERING)
            else:
                self.playbin.set_state(Gst.State.PLAYING)
                self._set_state(PlayerState.PLAYING)

        elif msg_type == Gst.MessageType.TAG:
            # Handle metadata tags
            taglist = message.parse_tag()
            tags = {}

            for i in range(taglist.n_tags()):
                tag_name = taglist.nth_tag_name(i)
                tag_value = taglist.get_value_index(tag_name, 0)
                tags[tag_name] = tag_value

            # Update current tags (merge with existing)
            self.current_tags.update(tags)

            self.emit('tags-updated', tags)

        return True

    def cleanup(self):
        """Clean up resources"""
        self.stop()
        if self.bus:
            self.bus.remove_signal_watch()
