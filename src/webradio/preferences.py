"""Preferences dialog for WebRadio Player"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib
from pathlib import Path
from webradio.equalizer import EqualizerPreset
from webradio.recorder import RecordingFormat


class PreferencesWindow(Adw.PreferencesWindow):
    """Main preferences window"""

    def __init__(self, parent, settings, equalizer_manager=None, recorder=None):
        super().__init__()

        self.parent_window = parent
        self.settings = settings
        self.equalizer_manager = equalizer_manager
        self.recorder = recorder

        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(600, 700)

        # Create pages
        self._create_general_page()
        self._create_audio_page()
        self._create_equalizer_page()
        self._create_recording_page()
        self._create_discovery_page()

    def _create_general_page(self):
        """Create General preferences page"""
        page = Adw.PreferencesPage()
        page.set_title("General")
        page.set_icon_name("preferences-system-symbolic")

        # UI Group
        ui_group = Adw.PreferencesGroup()
        ui_group.set_title("User Interface")

        # Language selection
        language_row = Adw.ComboRow()
        language_row.set_title("Language")
        language_row.set_subtitle("Interface language")

        languages = Gtk.StringList()
        languages.append("Auto-detect")
        languages.append("English")
        languages.append("Deutsch")

        language_row.set_model(languages)

        # Map current language to index
        current_lang = self.settings.get_string('language') if self.settings else 'auto'
        lang_index = {'auto': 0, 'en': 1, 'de': 2}.get(current_lang, 0)
        language_row.set_selected(lang_index)

        language_row.connect('notify::selected', self._on_language_changed)
        ui_group.add(language_row)

        # Minimize to tray
        tray_row = Adw.SwitchRow()
        tray_row.set_title("Minimize to System Tray")
        tray_row.set_subtitle("When playing, minimize to tray instead of closing")

        if self.settings:
            self.settings.bind('minimize-to-tray', tray_row, 'active', Gio.SettingsBindFlags.DEFAULT)

        ui_group.add(tray_row)

        # Show spectrum
        spectrum_row = Adw.SwitchRow()
        spectrum_row.set_title("Show Spectrum Visualizer")
        spectrum_row.set_subtitle("Display audio spectrum on Now Playing page")

        if self.settings:
            self.settings.bind('show-spectrum', spectrum_row, 'active', Gio.SettingsBindFlags.DEFAULT)

        ui_group.add(spectrum_row)

        # Spectrum style
        spectrum_style_row = Adw.ComboRow()
        spectrum_style_row.set_title("Spectrum Style")
        spectrum_style_row.set_subtitle("Visualization style")

        styles = Gtk.StringList()
        styles.append("Bars")
        styles.append("Line")
        styles.append("Gradient")

        spectrum_style_row.set_model(styles)

        current_style = self.settings.get_string('spectrum-style') if self.settings else 'bars'
        style_index = {'bars': 0, 'line': 1, 'gradient': 2}.get(current_style, 0)
        spectrum_style_row.set_selected(style_index)

        spectrum_style_row.connect('notify::selected', self._on_spectrum_style_changed)
        ui_group.add(spectrum_style_row)

        page.add(ui_group)

        # Behavior Group
        behavior_group = Adw.PreferencesGroup()
        behavior_group.set_title("Behavior")

        # Remember last station
        remember_row = Adw.SwitchRow()
        remember_row.set_title("Remember Last Station")
        remember_row.set_subtitle("Automatically load last played station on startup")

        if self.settings:
            self.settings.bind('remember-last-station', remember_row, 'active', Gio.SettingsBindFlags.DEFAULT)

        behavior_group.add(remember_row)

        page.add(behavior_group)

        self.add(page)

    def _create_audio_page(self):
        """Create Audio preferences page"""
        page = Adw.PreferencesPage()
        page.set_title("Audio")
        page.set_icon_name("audio-speakers-symbolic")

        # Audio Settings Group
        audio_group = Adw.PreferencesGroup()
        audio_group.set_title("Audio Settings")

        # Volume normalization
        normalize_row = Adw.SwitchRow()
        normalize_row.set_title("Volume Normalization")
        normalize_row.set_subtitle("Automatically normalize volume across different streams")

        if self.settings:
            self.settings.bind('normalize-volume', normalize_row, 'active', Gio.SettingsBindFlags.DEFAULT)

        audio_group.add(normalize_row)

        # Buffer size
        buffer_row = Adw.SpinRow.new_with_range(50000, 500000, 10000)
        buffer_row.set_title("Network Buffer Size")
        buffer_row.set_subtitle("Larger buffer = more stable but higher latency (bytes)")

        if self.settings:
            buffer_row.set_value(self.settings.get_int('buffer-size'))
            buffer_row.connect('changed', self._on_buffer_size_changed)

        audio_group.add(buffer_row)

        page.add(audio_group)

        self.add(page)

    def _create_equalizer_page(self):
        """Create Equalizer preferences page"""
        page = Adw.PreferencesPage()
        page.set_title("Equalizer")
        page.set_icon_name("multimedia-volume-control-symbolic")

        # Enable/Disable Group
        enable_group = Adw.PreferencesGroup()
        enable_group.set_title("Equalizer")

        # Enable switch
        enable_row = Adw.SwitchRow()
        enable_row.set_title("Enable Equalizer")
        enable_row.set_subtitle("10-band audio equalizer")

        if self.settings:
            self.settings.bind('equalizer-enabled', enable_row, 'active', Gio.SettingsBindFlags.DEFAULT)

        enable_group.add(enable_row)

        # Preset selection
        preset_row = Adw.ComboRow()
        preset_row.set_title("Preset")
        preset_row.set_subtitle("Choose equalizer preset")

        presets = Gtk.StringList()
        preset_keys = list(EqualizerPreset.PRESETS.keys())
        for key in preset_keys:
            preset = EqualizerPreset.PRESETS[key]
            presets.append(preset['name'])

        preset_row.set_model(presets)

        # Set current preset
        if self.settings:
            current_preset = self.settings.get_string('equalizer-preset')
            try:
                preset_index = preset_keys.index(current_preset)
                preset_row.set_selected(preset_index)
            except ValueError:
                preset_row.set_selected(0)

        preset_row.connect('notify::selected', lambda row, _: self._on_preset_changed(row, preset_keys))
        enable_group.add(preset_row)

        # Reset button
        reset_row = Adw.ActionRow()
        reset_row.set_title("Reset to Flat")
        reset_row.set_subtitle("Reset all bands to 0 dB")

        reset_button = Gtk.Button()
        reset_button.set_label("Reset")
        reset_button.set_valign(Gtk.Align.CENTER)
        reset_button.add_css_class('destructive-action')
        reset_button.connect('clicked', self._on_reset_equalizer)
        reset_row.add_suffix(reset_button)

        enable_group.add(reset_row)

        page.add(enable_group)

        # Custom EQ Group
        custom_group = Adw.PreferencesGroup()
        custom_group.set_title("Custom Equalizer")
        custom_group.set_description("Adjust individual frequency bands (-24 to +12 dB)")

        # Create sliders for all 10 bands
        self.eq_scales = []
        for i in range(10):
            freq_label = EqualizerPreset.BAND_LABELS[i]

            scale_row = Adw.ActionRow()
            scale_row.set_title(freq_label)

            # Create scale
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -24.0, 12.0, 0.5)
            scale.set_draw_value(True)
            scale.set_value_pos(Gtk.PositionType.RIGHT)
            scale.set_hexpand(True)
            scale.set_size_request(200, -1)

            # Add marks
            scale.add_mark(0.0, Gtk.PositionType.BOTTOM, "0")

            # Load current value
            if self.settings:
                current_value = self.settings.get_double(f'equalizer-band{i}')
                scale.set_value(current_value)

            # Connect signal
            scale.connect('value-changed', lambda s, band=i: self._on_eq_band_changed(band, s.get_value()))

            self.eq_scales.append(scale)
            scale_row.add_suffix(scale)
            custom_group.add(scale_row)

        page.add(custom_group)

        self.add(page)

    def _create_recording_page(self):
        """Create Recording preferences page"""
        page = Adw.PreferencesPage()
        page.set_title("Recording")
        page.set_icon_name("media-record-symbolic")

        # Recording Settings Group
        recording_group = Adw.PreferencesGroup()
        recording_group.set_title("Recording Settings")

        # Output format
        format_row = Adw.ComboRow()
        format_row.set_title("Output Format")
        format_row.set_subtitle("Audio format for recordings")

        formats = Gtk.StringList()
        format_keys = list(RecordingFormat.FORMATS.keys())
        for key in format_keys:
            fmt = RecordingFormat.FORMATS[key]
            formats.append(fmt['name'])

        format_row.set_model(formats)

        # Set current format
        if self.settings:
            current_format = self.settings.get_string('recording-format')
            try:
                format_index = format_keys.index(current_format)
                format_row.set_selected(format_index)
            except ValueError:
                format_row.set_selected(1)  # Default to MP3

        format_row.connect('notify::selected', lambda row, _: self._on_format_changed(row, format_keys))
        recording_group.add(format_row)

        # Output directory
        dir_row = Adw.ActionRow()
        dir_row.set_title("Output Directory")
        dir_row.set_subtitle("Where to save recordings")

        dir_button = Gtk.Button()
        dir_button.set_label("Choose Folder")
        dir_button.set_valign(Gtk.Align.CENTER)
        dir_button.connect('clicked', self._on_choose_directory)
        dir_row.add_suffix(dir_button)

        recording_group.add(dir_row)

        # Show current directory
        current_dir = self.settings.get_string('recording-directory') if self.settings else ''
        if not current_dir:
            current_dir = str(Path.home() / 'Music' / 'Recordings')

        dir_label_row = Adw.ActionRow()
        dir_label_row.set_title("Current Directory")
        dir_label_row.set_subtitle(current_dir)
        self.dir_label_row = dir_label_row
        recording_group.add(dir_label_row)

        # Filename template
        template_row = Adw.EntryRow()
        template_row.set_title("Filename Template")

        if self.settings:
            template_row.set_text(self.settings.get_string('recording-filename-template'))

        template_row.connect('changed', self._on_template_changed)
        recording_group.add(template_row)

        # Template help
        help_row = Adw.ActionRow()
        help_row.set_title("Available Variables")
        help_row.set_subtitle("{station}, {date}, {time}, {title}, {artist}")
        recording_group.add(help_row)

        # Auto-start recording
        auto_row = Adw.SwitchRow()
        auto_row.set_title("Auto-Start Recording")
        auto_row.set_subtitle("Automatically start recording when playback begins")

        if self.settings:
            self.settings.bind('recording-auto-start', auto_row, 'active', Gio.SettingsBindFlags.DEFAULT)

        recording_group.add(auto_row)

        page.add(recording_group)

        self.add(page)

    def _create_discovery_page(self):
        """Create Discovery preferences page"""
        page = Adw.PreferencesPage()
        page.set_title("Discovery")
        page.set_icon_name("system-search-symbolic")

        # Filter Settings Group
        filter_group = Adw.PreferencesGroup()
        filter_group.set_title("Default Filters")

        # Minimum bitrate
        bitrate_row = Adw.ComboRow()
        bitrate_row.set_title("Minimum Bitrate")
        bitrate_row.set_subtitle("Filter stations by minimum quality")

        bitrates = Gtk.StringList()
        bitrate_values = [0, 64, 128, 192, 256, 320]
        for br in bitrate_values:
            if br == 0:
                bitrates.append("All Bitrates")
            else:
                bitrates.append(f"{br} kbps+")

        bitrate_row.set_model(bitrates)

        # Set current bitrate
        if self.settings:
            current_br = self.settings.get_int('quality-filter-min-bitrate')
            try:
                br_index = bitrate_values.index(current_br)
                bitrate_row.set_selected(br_index)
            except ValueError:
                bitrate_row.set_selected(0)

        bitrate_row.connect('notify::selected', lambda row, _: self._on_bitrate_changed(row, bitrate_values))
        filter_group.add(bitrate_row)

        # Default country
        country_row = Adw.EntryRow()
        country_row.set_title("Default Country")

        if self.settings:
            country_row.set_text(self.settings.get_string('default-country'))

        country_row.connect('changed', self._on_country_changed)
        filter_group.add(country_row)

        # Sort order
        order_row = Adw.ComboRow()
        order_row.set_title("Default Sort Order")
        order_row.set_subtitle("How to order station lists")

        orders = Gtk.StringList()
        order_keys = ['votes', 'clickcount', 'bitrate', 'name']
        order_names = ['Most Voted', 'Most Popular', 'Highest Bitrate', 'Name']

        for name in order_names:
            orders.append(name)

        order_row.set_model(orders)

        # Set current order
        if self.settings:
            current_order = self.settings.get_string('order-by')
            try:
                order_index = order_keys.index(current_order)
                order_row.set_selected(order_index)
            except ValueError:
                order_row.set_selected(0)

        order_row.connect('notify::selected', lambda row, _: self._on_order_changed(row, order_keys))
        filter_group.add(order_row)

        page.add(filter_group)

        self.add(page)

    # Signal handlers

    def _on_language_changed(self, combo_row, _):
        """Handle language change"""
        if not self.settings:
            return

        selected = combo_row.get_selected()
        lang_map = {0: 'auto', 1: 'en', 2: 'de'}
        lang = lang_map.get(selected, 'auto')

        self.settings.set_string('language', lang)
        print(f"Language changed to: {lang}")

    def _on_spectrum_style_changed(self, combo_row, _):
        """Handle spectrum style change"""
        if not self.settings:
            return

        selected = combo_row.get_selected()
        style_map = {0: 'bars', 1: 'line', 2: 'gradient'}
        style = style_map.get(selected, 'bars')

        self.settings.set_string('spectrum-style', style)
        print(f"Spectrum style changed to: {style}")

    def _on_buffer_size_changed(self, spin_row):
        """Handle buffer size change"""
        if not self.settings:
            return

        value = int(spin_row.get_value())
        self.settings.set_int('buffer-size', value)
        print(f"Buffer size changed to: {value}")

    def _on_preset_changed(self, combo_row, preset_keys):
        """Handle equalizer preset change"""
        if not self.settings:
            return

        selected = combo_row.get_selected()
        if 0 <= selected < len(preset_keys):
            preset = preset_keys[selected]
            self.settings.set_string('equalizer-preset', preset)

            # Update sliders if not custom preset
            if preset != 'custom':
                gains = EqualizerPreset.PRESETS[preset]['gains']
                for i, scale in enumerate(self.eq_scales):
                    scale.set_value(gains[i])

            print(f"Equalizer preset changed to: {preset}")

    def _on_reset_equalizer(self, button):
        """Reset equalizer to flat"""
        if not self.settings:
            return

        # Set all bands to 0
        for i in range(10):
            self.settings.set_double(f'equalizer-band{i}', 0.0)
            if i < len(self.eq_scales):
                self.eq_scales[i].set_value(0.0)

        # Set preset to flat
        self.settings.set_string('equalizer-preset', 'flat')
        print("Equalizer reset to flat")

    def _on_eq_band_changed(self, band, value):
        """Handle equalizer band change"""
        if not self.settings:
            return

        self.settings.set_double(f'equalizer-band{band}', value)
        # Switch to custom preset when manually adjusting
        self.settings.set_string('equalizer-preset', 'custom')

    def _on_format_changed(self, combo_row, format_keys):
        """Handle recording format change"""
        if not self.settings:
            return

        selected = combo_row.get_selected()
        if 0 <= selected < len(format_keys):
            fmt = format_keys[selected]
            self.settings.set_string('recording-format', fmt)
            print(f"Recording format changed to: {fmt}")

    def _on_choose_directory(self, button):
        """Show directory chooser dialog"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Choose Recording Directory")
        dialog.set_modal(True)

        dialog.select_folder(self, None, self._on_directory_selected)

    def _on_directory_selected(self, dialog, result):
        """Handle directory selection"""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                if self.settings:
                    self.settings.set_string('recording-directory', path)
                    self.dir_label_row.set_subtitle(path)
                    print(f"Recording directory changed to: {path}")
        except Exception as e:
            print(f"Directory selection cancelled or failed: {e}")

    def _on_template_changed(self, entry_row):
        """Handle filename template change"""
        if not self.settings:
            return

        template = entry_row.get_text()
        self.settings.set_string('recording-filename-template', template)

    def _on_bitrate_changed(self, combo_row, bitrate_values):
        """Handle bitrate filter change"""
        if not self.settings:
            return

        selected = combo_row.get_selected()
        if 0 <= selected < len(bitrate_values):
            bitrate = bitrate_values[selected]
            self.settings.set_int('quality-filter-min-bitrate', bitrate)
            print(f"Minimum bitrate changed to: {bitrate}")

    def _on_country_changed(self, entry_row):
        """Handle default country change"""
        if not self.settings:
            return

        country = entry_row.get_text()
        self.settings.set_string('default-country', country)

    def _on_order_changed(self, combo_row, order_keys):
        """Handle sort order change"""
        if not self.settings:
            return

        selected = combo_row.get_selected()
        if 0 <= selected < len(order_keys):
            order = order_keys[selected]
            self.settings.set_string('order-by', order)
            print(f"Sort order changed to: {order}")
