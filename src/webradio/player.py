"""Audio player using GStreamer with playbin"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib
from enum import Enum
from typing import Optional, Callable

# Initialize GStreamer
Gst.init(None)


class PlayerState(Enum):
    """Player state enumeration"""
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2
    BUFFERING = 3
    ERROR = 4


class AudioPlayer(GObject.Object):
    """Simple audio player using GStreamer playbin"""

    __gsignals__ = {
        'state-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'error': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'buffering': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'tags-changed': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self):
        super().__init__()

        self.state = PlayerState.STOPPED
        self.current_uri = None
        self.current_station = None
        self._volume = 1.0
        self._tags = {}

        # Create simple playbin pipeline
        self.pipeline = Gst.ElementFactory.make('playbin', 'player')
        if not self.pipeline:
            raise RuntimeError("Could not create playbin element")

        # Disable video completely - we only want audio
        # Use fakesink to discard any video data without processing it
        fakesink = Gst.ElementFactory.make('fakesink', 'fakesink')
        if fakesink:
            fakesink.set_property('sync', False)  # Don't sync to clock
            fakesink.set_property('async', False)  # Don't block
            self.pipeline.set_property('video-sink', fakesink)

        # Disable video and text stream selection in playbin flags
        flags = self.pipeline.get_property('flags')
        flags &= ~0x00000001  # Disable video flag (GST_PLAY_FLAG_VIDEO)
        flags &= ~0x00000004  # Disable text flag (GST_PLAY_FLAG_TEXT)
        self.pipeline.set_property('flags', flags)

        # Set up bus for messages
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self._on_bus_message)

        # Set initial volume
        self.pipeline.set_property('volume', self._volume)

        # Store references (for compatibility)
        self.playbin = self.pipeline

        print("Simple playbin pipeline created successfully")

    def play(self, uri: str, station_info: dict = None):
        """Play a radio stream"""
        if not uri:
            return False

        # Stop current playback
        self.stop()

        self.current_uri = uri
        self.current_station = station_info

        # Set URI
        self.pipeline.set_property('uri', uri)

        # Start playback
        result = self.pipeline.set_state(Gst.State.PLAYING)

        if result == Gst.StateChangeReturn.FAILURE:
            self.emit('error', 'Failed to start playback')
            self.state = PlayerState.ERROR
            return False

        self._set_state(PlayerState.PLAYING)
        return True

    def pause(self):
        """Pause playback"""
        if self.state == PlayerState.PLAYING:
            self.pipeline.set_state(Gst.State.PAUSED)
            self._set_state(PlayerState.PAUSED)

    def resume(self):
        """Resume playback"""
        if self.state == PlayerState.PAUSED:
            self.pipeline.set_state(Gst.State.PLAYING)
            self._set_state(PlayerState.PLAYING)

    def stop(self):
        """Stop playback"""
        if self.state != PlayerState.STOPPED:
            self.pipeline.set_state(Gst.State.NULL)
            self._set_state(PlayerState.STOPPED)
            self.current_uri = None
            self._tags = {}

    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self.state == PlayerState.PLAYING

    def is_paused(self) -> bool:
        """Check if currently paused"""
        return self.state == PlayerState.PAUSED

    def set_volume(self, volume: float):
        """Set playback volume (0.0 - 1.0)"""
        self._volume = max(0.0, min(1.0, volume))
        self.pipeline.set_property('volume', self._volume)

    def get_volume(self) -> float:
        """Get current volume"""
        return self._volume

    def get_state(self) -> PlayerState:
        """Get current player state"""
        return self.state

    def get_current_uri(self) -> Optional[str]:
        """Get currently playing URI"""
        return self.current_uri

    def get_current_station(self) -> Optional[dict]:
        """Get currently playing station info"""
        return self.current_station

    def get_current_tags(self) -> dict:
        """Get current stream tags/metadata"""
        return self._tags.copy()

    def _set_state(self, new_state: PlayerState):
        """Update player state and emit signal"""
        if self.state != new_state:
            self.state = new_state
            self.emit('state-changed', new_state.value)

    def _on_bus_message(self, bus, message):
        """Handle GStreamer bus messages"""
        t = message.type

        if t == Gst.MessageType.EOS:
            # End of stream
            self.stop()

        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            error_msg = f"Playback error: {err}"
            print(f"ERROR: {error_msg}")
            if debug:
                print(f"DEBUG: {debug}")
            self.emit('error', error_msg)
            self.stop()

        elif t == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            print(f"WARNING: {warn}")

        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending = message.parse_state_changed()

                if new_state == Gst.State.PLAYING:
                    if self.state != PlayerState.PLAYING:
                        self._set_state(PlayerState.PLAYING)

                elif new_state == Gst.State.PAUSED:
                    if self.state != PlayerState.PAUSED:
                        self._set_state(PlayerState.PAUSED)

                elif new_state == Gst.State.NULL or new_state == Gst.State.READY:
                    if self.state != PlayerState.STOPPED:
                        self._set_state(PlayerState.STOPPED)

        elif t == Gst.MessageType.BUFFERING:
            percent = message.parse_buffering()
            self.emit('buffering', percent)

            if percent < 100:
                if self.state != PlayerState.BUFFERING:
                    self._set_state(PlayerState.BUFFERING)
            else:
                if self.state == PlayerState.BUFFERING:
                    self._set_state(PlayerState.PLAYING)

        elif t == Gst.MessageType.TAG:
            taglist = message.parse_tag()
            tags = {}

            for i in range(taglist.n_tags()):
                tag_name = taglist.nth_tag_name(i)
                value = taglist.get_value_index(tag_name, 0)

                if tag_name in ['title', 'artist', 'album', 'organization', 'genre']:
                    tags[tag_name] = str(value)

            if tags:
                self._tags.update(tags)
                self.emit('tags-changed', self._tags.copy())

        return True

    def cleanup(self):
        """Clean up resources"""
        self.stop()

        if self.bus:
            self.bus.remove_signal_watch()

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)

    # Placeholder methods for advanced features (to be implemented later)
    def set_equalizer_band(self, band: int, gain: float) -> bool:
        """Set equalizer band gain (not implemented in simple playbin)"""
        return False

    def start_recording(self, file_path: str) -> bool:
        """Start recording stream (not implemented in simple playbin)"""
        return False

    def stop_recording(self) -> bool:
        """Stop recording stream (not implemented in simple playbin)"""
        return False
