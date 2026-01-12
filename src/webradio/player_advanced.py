"""Advanced audio player with Equalizer and Recording support using GStreamer"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib
from enum import Enum
from typing import Optional, Dict
from webradio.logger import get_logger

# Initialize GStreamer
Gst.init(None)

logger = get_logger(__name__)


class PlayerState(Enum):
    """Player state enumeration"""
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2
    BUFFERING = 3
    ERROR = 4


class AdvancedAudioPlayer(GObject.Object):
    """Advanced audio player with Equalizer and Recording support"""

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

        # Auto-reconnect settings
        self._auto_reconnect = True
        self._reconnect_timeout_id = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 15
        self._base_reconnect_delay = 500
        self._max_reconnect_delay = 10000

        # Recording state
        self._is_recording = False
        self._recording_file = None

        # Build custom pipeline with equalizer and recording support
        self._build_pipeline()

        logger.info("Advanced pipeline created with equalizer and recording support")

    def _build_pipeline(self):
        """Build custom GStreamer pipeline"""
        try:
            # Create pipeline
            self.pipeline = Gst.Pipeline.new('player-pipeline')

            # Create elements
            self.source = Gst.ElementFactory.make('uridecodebin', 'source')
            self.audioconvert = Gst.ElementFactory.make('audioconvert', 'convert')
            self.audioresample = Gst.ElementFactory.make('audioresample', 'resample')
            self.equalizer = Gst.ElementFactory.make('equalizer-10bands', 'equalizer')
            self.tee = Gst.ElementFactory.make('tee', 'tee')
            self.queue_play = Gst.ElementFactory.make('queue', 'queue-play')
            self.queue_record = Gst.ElementFactory.make('queue', 'queue-record')
            self.volume_elem = Gst.ElementFactory.make('volume', 'volume')
            self.audiosink = Gst.ElementFactory.make('autoaudiosink', 'sink')

            # Fake video sink to discard video
            self.fakesink = Gst.ElementFactory.make('fakesink', 'fakevideo')

            if not all([self.source, self.audioconvert, self.audioresample,
                       self.equalizer, self.tee, self.queue_play, self.queue_record,
                       self.volume_elem, self.audiosink, self.fakesink]):
                raise RuntimeError("Could not create all pipeline elements")

            # Configure source
            self.source.connect('pad-added', self._on_pad_added)
            self.source.connect('no-more-pads', self._on_no_more_pads)

            # Configure fakesink for video
            self.fakesink.set_property('sync', False)
            self.fakesink.set_property('async', False)

            # Add elements to pipeline
            self.pipeline.add(self.source)
            self.pipeline.add(self.audioconvert)
            self.pipeline.add(self.audioresample)
            self.pipeline.add(self.equalizer)
            self.pipeline.add(self.tee)
            self.pipeline.add(self.queue_play)
            self.pipeline.add(self.queue_record)
            self.pipeline.add(self.volume_elem)
            self.pipeline.add(self.audiosink)
            self.pipeline.add(self.fakesink)

            # Link audio chain (will be linked dynamically from uridecodebin)
            # audioconvert -> audioresample -> equalizer -> tee
            if not self.audioconvert.link(self.audioresample):
                raise RuntimeError("Could not link audioconvert to audioresample")
            if not self.audioresample.link(self.equalizer):
                raise RuntimeError("Could not link audioresample to equalizer")
            if not self.equalizer.link(self.tee):
                raise RuntimeError("Could not link equalizer to tee")

            # Link playback branch: tee -> queue -> volume -> sink
            tee_src_pad = self.tee.get_request_pad('src_%u')
            queue_play_sink_pad = self.queue_play.get_static_pad('sink')
            if tee_src_pad.link(queue_play_sink_pad) != Gst.PadLinkReturn.OK:
                raise RuntimeError("Could not link tee to playback queue")

            if not self.queue_play.link(self.volume_elem):
                raise RuntimeError("Could not link queue to volume")
            if not self.volume_elem.link(self.audiosink):
                raise RuntimeError("Could not link volume to sink")

            # Set up bus for messages
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect('message', self._on_bus_message)

            # Set initial volume
            self.volume_elem.set_property('volume', self._volume)

            # Initialize equalizer to flat (0 dB on all bands)
            self._equalizer_enabled = False
            for i in range(10):
                self.equalizer.set_property(f'band{i}', 0.0)

            logger.debug("Pipeline built successfully")

        except Exception as e:
            logger.error(f"Failed to build pipeline: {e}")
            raise

    def _on_pad_added(self, element, pad):
        """Handle new pad from uridecodebin"""
        caps = pad.get_current_caps()
        if not caps:
            return

        structure = caps.get_structure(0)
        name = structure.get_name()

        logger.debug(f"New pad added: {name}")

        if name.startswith('audio/'):
            # Link to audio chain
            sink_pad = self.audioconvert.get_static_pad('sink')
            if not sink_pad.is_linked():
                if pad.link(sink_pad) == Gst.PadLinkReturn.OK:
                    logger.debug("Audio pad linked successfully")
                else:
                    logger.error("Failed to link audio pad")
        elif name.startswith('video/'):
            # Link to fakesink to discard video
            sink_pad = self.fakesink.get_static_pad('sink')
            if not sink_pad.is_linked():
                if pad.link(sink_pad) == Gst.PadLinkReturn.OK:
                    logger.debug("Video pad linked to fakesink")

    def _on_no_more_pads(self, element):
        """Called when uridecodebin has finished adding pads"""
        logger.debug("No more pads from uridecodebin")

    def play(self, uri: str, station_info: dict = None):
        """Play a radio stream"""
        if not uri:
            return False

        # Stop current playback
        self.stop()

        self.current_uri = uri
        self.current_station = station_info

        # Reset reconnect counter on manual play
        self._reconnect_attempts = 0

        # Set URI
        self.source.set_property('uri', uri)

        # Start playback
        result = self.pipeline.set_state(Gst.State.PLAYING)

        if result == Gst.StateChangeReturn.FAILURE:
            self.emit('error', 'Failed to start playback')
            self.state = PlayerState.ERROR
            return False

        self._set_state(PlayerState.PLAYING)
        logger.info(f"Playing: {uri}")
        return True

    def pause(self):
        """Pause playback"""
        if self.state == PlayerState.PLAYING:
            self.pipeline.set_state(Gst.State.PAUSED)
            self._set_state(PlayerState.PAUSED)
            logger.debug("Playback paused")

    def resume(self):
        """Resume playback"""
        if self.state == PlayerState.PAUSED:
            self.pipeline.set_state(Gst.State.PLAYING)
            self._set_state(PlayerState.PLAYING)
            logger.debug("Playback resumed")

    def stop(self):
        """Stop playback"""
        # Stop recording if active
        if self._is_recording:
            self.stop_recording()

        # Cancel any pending reconnect
        self._cancel_reconnect()

        if self.state != PlayerState.STOPPED:
            self.pipeline.set_state(Gst.State.NULL)
            self._set_state(PlayerState.STOPPED)
            self.current_uri = None
            self._tags = {}
            logger.debug("Playback stopped")

    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self.state == PlayerState.PLAYING

    def is_paused(self) -> bool:
        """Check if currently paused"""
        return self.state == PlayerState.PAUSED

    def set_volume(self, volume: float):
        """Set playback volume (0.0 - 1.0)"""
        self._volume = max(0.0, min(1.0, volume))
        self.volume_elem.set_property('volume', self._volume)

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

    def set_auto_reconnect(self, enabled: bool):
        """Enable or disable automatic reconnection on network errors"""
        self._auto_reconnect = enabled
        logger.info(f"Auto-reconnect {'enabled' if enabled else 'disabled'}")

    # ===== EQUALIZER METHODS =====

    def set_equalizer_enabled(self, enabled: bool) -> bool:
        """Enable or disable equalizer"""
        self._equalizer_enabled = enabled
        # If disabling, reset all bands to 0
        if not enabled:
            for i in range(10):
                self.equalizer.set_property(f'band{i}', 0.0)
        logger.info(f"Equalizer {'enabled' if enabled else 'disabled'}")
        return True

    def set_equalizer_band(self, band: int, gain: float) -> bool:
        """Set equalizer band gain (-24.0 to +12.0 dB)"""
        if not 0 <= band < 10:
            logger.warning(f"Invalid equalizer band: {band}")
            return False

        # Clamp gain
        gain = max(-24.0, min(12.0, gain))

        try:
            self.equalizer.set_property(f'band{band}', gain)
            logger.debug(f"Equalizer band {band} set to {gain} dB")
            return True
        except Exception as e:
            logger.error(f"Failed to set equalizer band {band}: {e}")
            return False

    def get_equalizer_band(self, band: int) -> float:
        """Get equalizer band gain"""
        if not 0 <= band < 10:
            return 0.0

        try:
            return self.equalizer.get_property(f'band{band}')
        except Exception as e:
            logger.error(f"Failed to get equalizer band {band}: {e}")
            return 0.0

    # ===== RECORDING METHODS =====

    def start_recording(self, file_path: str) -> bool:
        """Start recording stream to file"""
        if self._is_recording:
            logger.warning("Already recording")
            return False

        if not self.is_playing():
            logger.error("Cannot record when not playing")
            return False

        try:
            # Create recording bin
            self.recording_bin = Gst.Bin.new('recording-bin')

            # Create encoder based on file extension
            if file_path.endswith('.mp3'):
                encoder = Gst.ElementFactory.make('lamemp3enc', 'encoder')
                if encoder:
                    encoder.set_property('target', 1)  # bitrate
                    encoder.set_property('bitrate', 320)  # 320 kbps
            elif file_path.endswith('.flac'):
                encoder = Gst.ElementFactory.make('flacenc', 'encoder')
            elif file_path.endswith('.ogg'):
                encoder = Gst.ElementFactory.make('vorbisenc', 'encoder')
                muxer = Gst.ElementFactory.make('oggmux', 'muxer')
            elif file_path.endswith('.wav'):
                encoder = Gst.ElementFactory.make('wavenc', 'encoder')
            else:
                # Default to MP3
                encoder = Gst.ElementFactory.make('lamemp3enc', 'encoder')
                if encoder:
                    encoder.set_property('target', 1)
                    encoder.set_property('bitrate', 320)

            filesink = Gst.ElementFactory.make('filesink', 'filesink')

            if not encoder or not filesink:
                logger.error("Could not create recording elements")
                return False

            filesink.set_property('location', file_path)

            # Add elements to bin
            self.recording_bin.add(encoder)
            self.recording_bin.add(filesink)

            # Add muxer for OGG
            if file_path.endswith('.ogg') and muxer:
                self.recording_bin.add(muxer)
                encoder.link(muxer)
                muxer.link(filesink)
            else:
                encoder.link(filesink)

            # Create ghost pad for bin
            encoder_sink_pad = encoder.get_static_pad('sink')
            ghost_pad = Gst.GhostPad.new('sink', encoder_sink_pad)
            self.recording_bin.add_pad(ghost_pad)

            # Add bin to pipeline
            self.pipeline.add(self.recording_bin)

            # Link tee to recording bin
            tee_src_pad = self.tee.get_request_pad('src_%u')
            queue_record_sink_pad = self.queue_record.get_static_pad('sink')

            if tee_src_pad.link(queue_record_sink_pad) != Gst.PadLinkReturn.OK:
                logger.error("Could not link tee to recording queue")
                return False

            queue_record_src_pad = self.queue_record.get_static_pad('src')
            bin_sink_pad = self.recording_bin.get_static_pad('sink')

            if queue_record_src_pad.link(bin_sink_pad) != Gst.PadLinkReturn.OK:
                logger.error("Could not link queue to recording bin")
                return False

            # Sync bin state with pipeline
            self.recording_bin.sync_state_with_parent()

            self._is_recording = True
            self._recording_file = file_path
            logger.info(f"Recording started: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False

    def stop_recording(self) -> bool:
        """Stop recording stream"""
        if not self._is_recording:
            logger.warning("Not currently recording")
            return False

        try:
            # Send EOS to recording bin
            self.recording_bin.send_event(Gst.Event.new_eos())

            # Wait a moment for EOS to process
            GLib.timeout_add(100, self._cleanup_recording_bin)

            self._is_recording = False
            file_path = self._recording_file
            self._recording_file = None

            logger.info(f"Recording stopped: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            return False

    def _cleanup_recording_bin(self):
        """Clean up recording bin after stopping"""
        try:
            if hasattr(self, 'recording_bin'):
                self.recording_bin.set_state(Gst.State.NULL)
                self.pipeline.remove(self.recording_bin)
                self.recording_bin = None
        except Exception as e:
            logger.error(f"Error cleaning up recording bin: {e}")
        return False

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
            logger.error(error_msg)
            if debug:
                logger.debug(f"Debug info: {debug}")

            # Try to reconnect automatically if enabled and we have a URI
            if self._auto_reconnect and self.current_uri and self._reconnect_attempts < self._max_reconnect_attempts:
                self._reconnect_attempts += 1

                # Calculate delay message
                if self._reconnect_attempts == 1:
                    delay_msg = "sofort"
                elif self._reconnect_attempts == 2:
                    delay_msg = "in 0.5s"
                else:
                    delay_sec = min(
                        self._base_reconnect_delay * (2 ** (self._reconnect_attempts - 2)) / 1000,
                        self._max_reconnect_delay / 1000
                    )
                    delay_msg = f"in {delay_sec:.1f}s"

                logger.warning(f"Network error. Reconnect attempt {self._reconnect_attempts}/{self._max_reconnect_attempts} {delay_msg}...")
                self.emit('error', f"Verbindung unterbrochen. Reconnect {delay_msg}... ({self._reconnect_attempts}/{self._max_reconnect_attempts})")

                # Set to NULL state first
                self.pipeline.set_state(Gst.State.NULL)

                # Schedule reconnect
                self._schedule_reconnect()
            else:
                # No reconnect - emit error and stop
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    self.emit('error', f"Failed to reconnect after {self._max_reconnect_attempts} attempts")
                else:
                    self.emit('error', error_msg)
                self.stop()

        elif t == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"GStreamer warning: {warn}")

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

    def _schedule_reconnect(self):
        """Schedule a reconnect attempt with exponential backoff"""
        self._cancel_reconnect()

        # Calculate delay
        if self._reconnect_attempts == 1:
            delay = 50
        elif self._reconnect_attempts == 2:
            delay = self._base_reconnect_delay
        else:
            delay = min(
                self._base_reconnect_delay * (2 ** (self._reconnect_attempts - 2)),
                self._max_reconnect_delay
            )

        logger.debug(f"Scheduling reconnect in {delay}ms")

        self._reconnect_timeout_id = GLib.timeout_add(
            delay,
            self._do_reconnect
        )

    def _cancel_reconnect(self):
        """Cancel pending reconnect"""
        if self._reconnect_timeout_id:
            GLib.source_remove(self._reconnect_timeout_id)
            self._reconnect_timeout_id = None

    def _do_reconnect(self):
        """Perform the actual reconnect"""
        self._reconnect_timeout_id = None

        if not self.current_uri:
            return False

        logger.info(f"Reconnecting to: {self.current_uri}")

        # Set URI again
        self.source.set_property('uri', self.current_uri)

        # Try to start playback
        result = self.pipeline.set_state(Gst.State.PLAYING)

        if result != Gst.StateChangeReturn.FAILURE:
            self._set_state(PlayerState.PLAYING)
            logger.info("Reconnect successful!")
            # Reset counter on successful reconnect
            self._reconnect_attempts = 0
        else:
            logger.error("Reconnect failed")

        return False

    def cleanup(self):
        """Clean up resources"""
        # Cancel any pending reconnects
        self._cancel_reconnect()

        # Stop recording if active
        if self._is_recording:
            self.stop_recording()

        self.stop()

        if self.bus:
            self.bus.remove_signal_watch()

        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
